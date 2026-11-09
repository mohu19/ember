# -*- coding: utf-8 -*-
"""ember 文档工具（纯标准库，Win7 可用）

不用 python-docx / openpyxl 那套的原因：
  * 它们要先装包（学校机器可能没网、没管理员权限）
  * python-docx / python-pptx 依赖 lxml（C 扩展），32 位老机器上很容易缺
  * 这些格式本来就是 zip + XML，标准库 zipfile + ElementTree 足够读写常见需求

能干什么（agent 通过 doc_read / doc_write / docx_replace / xlsx_set / office_convert 调用）：
  doc_read      .docx .xlsx .pptx .pdf .txt .csv .md   -> 纯文本
  doc_write     .docx .xlsx .csv .md .txt              -> 新建文件
  docx_replace  改现有 Word 的文字（查找替换，另存一份）
  xlsx_set      改现有 Excel 的单元格（保留其它内容与格式）
  office_convert 借本机 Office/WPS 转格式（.doc->.docx、.docx->.pdf、.xlsx->.csv）

已知边界（写清楚，免得 agent 瞎猜）：
  * .doc / .xls / .ppt（97-2003 老格式）读不了，只能用 office_convert 转新格式
  * PDF 只提文本层：扫描件（纯图片）没有文字层，提不出来
  * docx_replace 按"整段文本"匹配；同一段被 Word 拆成好几截的，可能匹配不到
"""
import io
import os
import re
import shutil
import subprocess
import time
import zipfile
import zlib

from xml.etree import ElementTree as ET

W = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
R = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
PKG_REL = "http://schemas.openxmlformats.org/package/2006/relationships"
CT = "http://schemas.openxmlformats.org/package/2006/content-types"

NS_W = "{%s}" % W
NS_R = "{%s}" % R


# --------------------------------------------------------------------------- #
# 共用小工具
# --------------------------------------------------------------------------- #
MAX_PART_BYTES = 64 * 1024 * 1024      # 单个部件解压后上限
MAX_TOTAL_BYTES = 160 * 1024 * 1024   # 整个文档解压后上限
MAX_PDF_BYTES = 80 * 1024 * 1024


def _zip_guard(zf):
    """挡住解压炸弹：单个部件/总量都有上限（审计报告 P1-C4）。"""
    total = 0
    for info in zf.infolist():
        if info.file_size > MAX_PART_BYTES:
            raise ValueError("文档里有部件解压后超过 %d MB，不处理（可能是压缩炸弹）"
                             % (MAX_PART_BYTES // 1048576))
        total += info.file_size
    if total > MAX_TOTAL_BYTES:
        raise ValueError("文档解压后总共超过 %d MB，不处理"
                         % (MAX_TOTAL_BYTES // 1048576))


def _xml_guard(blob, name="XML"):
    """拒绝带 DTD/实体声明的部件（XXE / 实体膨胀）。"""
    head = blob[:4096].lower()
    if b"<!doctype" in head or b"<!entity" in head:
        raise ValueError("%s 里带 DTD/实体声明，出于安全不解析这个文档" % name)
    return blob


def _read(path):
    with open(path, "rb") as fh:
        return fh.read()


def _fmt_size(n):
    return "%.1f KB" % (n / 1024.0) if n < 1048576 else "%.1f MB" % (n / 1048576.0)


def kind_of(path):
    ext = os.path.splitext(str(path))[1].lower()
    return {
        ".docx": "docx", ".doc": "doc", ".rtf": "rtf",
        ".xlsx": "xlsx", ".xlsm": "xlsx", ".xls": "xls", ".csv": "csv",
        ".pptx": "pptx", ".ppt": "ppt",
        ".pdf": "pdf", ".txt": "text", ".md": "text", ".log": "text",
        ".json": "text", ".ini": "text", ".cfg": "text", ".py": "text",
    }.get(ext, "text")


def _safe_replace(src, dst, tries=4):
    """Windows 上偶尔会被杀软/索引锁一下，重试几次再放弃。"""
    last = None
    for i in range(tries):
        try:
            os.replace(src, dst)
            return True
        except OSError as exc:
            last = exc
            time.sleep(0.2 * (i + 1))
    try:
        if os.path.exists(dst):
            os.remove(dst)
        os.replace(src, dst)
        return True
    except OSError:
        raise ValueError("写回失败（文件可能正被 Word/Excel 打开）：%s" % last)


def _need(path):
    if not os.path.exists(path):
        raise ValueError("文件不存在：%s" % path)


# --------------------------------------------------------------------------- #
# Word 读
# --------------------------------------------------------------------------- #
def _w_text(node):
    """把一段 w:p / w:tbl 里的文字抽出来（w:t 直接拼，w:tab 变 \\t）。"""
    out = []
    for el in node.iter():
        tag = el.tag
        if tag == NS_W + "t":
            out.append(el.text or "")
        elif tag == NS_W + "tab":
            out.append("\t")
        elif tag == NS_W + "br":
            out.append("\n")
    return "".join(out)


def _paragraph_style(p):
    ppr = p.find(NS_W + "pPr")
    if ppr is None:
        return ""
    st = ppr.find(NS_W + "pStyle")
    return (st.get(NS_W + "val") if st is not None else "") or ""


def _heading_level(style):
    m = re.match(r"^Heading(\d)$", style or "", re.I)
    if m:
        return int(m.group(1))
    m = re.match(r"^标题\s*(\d)$", style or "")
    if m:
        return int(m.group(1))
    return 0


def read_docx(path):
    data = _read(path)
    with zipfile.ZipFile(io.BytesIO(data)) as zf:
        names = zf.namelist()
        _zip_guard(zf)
        if "word/document.xml" not in names:
            raise ValueError("不像 .docx（缺 word/document.xml）；如果是 .doc 请先转格式")
        root = ET.fromstring(_xml_guard(zf.read("word/document.xml"), "word/document.xml"))
    body = root.find(NS_W + "body")
    if body is None:
        return ""
    lines = []
    for el in list(body):
        tag = el.tag
        if tag == NS_W + "p":
            txt = _w_text(el).rstrip()
            style = _paragraph_style(el)
            lvl = _heading_level(style)
            if lvl and txt:
                lines.append("#" * min(lvl, 6) + " " + txt)
            elif style.startswith("ListBullet") and txt:
                lines.append("- " + txt)
            elif style.startswith("Quote") and txt:
                lines.append("> " + txt)
            elif style.startswith("Code"):
                lines.append(txt)
            else:
                lines.append(txt)
        elif tag == NS_W + "tbl":
            rows = []
            for tr in el.findall(NS_W + "tr"):
                cells = []
                for tc in tr.findall(NS_W + "tc"):
                    cells.append(" ".join(_w_text(p).strip()
                                          for p in tc.findall(NS_W + "p")).strip())
                rows.append("| " + " | ".join(cells) + " |")
            if rows:
                head = rows[0]
                sep = "| " + " | ".join("---" for _ in range(head.count("|") - 1)) + " |"
                lines.append(head)
                lines.append(sep)
                lines.extend(rows[1:])
            lines.append("")
    return "\n".join(lines).strip() + "\n"


# --------------------------------------------------------------------------- #
# Excel 读
# --------------------------------------------------------------------------- #
def _col_to_idx(ref):
    m = re.match(r"([A-Z]+)(\d+)?", ref or "")
    if not m:
        return 0, 0
    col = 0
    for ch in m.group(1):
        col = col * 26 + (ord(ch) - 64)
    return col, int(m.group(2) or 0)


def _xlsx_strings(zf):
    if "xl/sharedStrings.xml" not in zf.namelist():
        return []
    root = ET.fromstring(zf.read("xl/sharedStrings.xml"))
    out = []
    for si in root.findall("{http://schemas.openxmlformats.org/spreadsheetml/2006/main}si"):
        out.append("".join(t.text or "" for t in si.iter(
            "{http://schemas.openxmlformats.org/spreadsheetml/2006/main}t")))
    return out


def _xlsx_sheets(zf):
    """[(名字, 内部路径)]，按 workbook.xml 顺序。"""
    base = "http://schemas.openxmlformats.org/spreadsheetml/2006/main"
    rel_ns = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
    wb = ET.fromstring(zf.read("xl/workbook.xml"))
    rels = {}
    if "xl/_rels/workbook.xml.rels" in zf.namelist():
        rr = ET.fromstring(zf.read("xl/_rels/workbook.xml.rels"))
        for rel in rr:
            rels[rel.get("Id")] = rel.get("Target")
    out = []
    for sh in wb.iter("{%s}sheet" % base):
        name = sh.get("name")
        rid = sh.get("{%s}id" % rel_ns)
        target = rels.get(rid, "")
        if target.startswith("/"):
            target = target[1:]
        elif not target.startswith("xl/"):
            target = "xl/" + target
        out.append((name, target))
    return out


def _xlsx_cell_text(c, shared):
    t = c.get("t")
    v = c.find("{http://schemas.openxmlformats.org/spreadsheetml/2006/main}v")
    is_ = c.find("{http://schemas.openxmlformats.org/spreadsheetml/2006/main}is")
    if t == "s" and v is not None:
        try:
            return shared[int(v.text or "0")]
        except (ValueError, IndexError):
            return ""
    if t == "inlineStr" and is_ is not None:
        return "".join(x.text or "" for x in is_.iter(
            "{http://schemas.openxmlformats.org/spreadsheetml/2006/main}t"))
    if v is not None:
        return v.text or ""
    return ""


def read_xlsx(path):
    data = _read(path)
    ns = "{http://schemas.openxmlformats.org/spreadsheetml/2006/main}"
    with zipfile.ZipFile(io.BytesIO(data)) as zf:
        _zip_guard(zf)
        shared = _xlsx_strings(zf)
        chunks = []
        for name, target in _xlsx_sheets(zf):
            if target not in zf.namelist():
                continue
            root = ET.fromstring(zf.read(target))
            chunks.append("## 工作表：%s" % name)
            for row in root.iter(ns + "row"):
                cells = {}
                width = 0
                for c in row.findall(ns + "c"):
                    col, _row = _col_to_idx(c.get("r"))
                    if col > width:
                        width = col
                    cells[col] = _xlsx_cell_text(c, shared)
                if not cells:
                    chunks.append("")
                    continue
                vals = [cells.get(i + 1, "") for i in range(width)]
                while vals and vals[-1] == "":
                    vals.pop()
                chunks.append("\t".join(vals))
            chunks.append("")
    return "\n".join(chunks).strip() + "\n"


# --------------------------------------------------------------------------- #
# PPT 读
# --------------------------------------------------------------------------- #
def read_pptx(path):
    data = _read(path)
    with zipfile.ZipFile(io.BytesIO(data)) as zf:
        _zip_guard(zf)
        slides = sorted([n for n in zf.namelist()
                         if re.match(r"^ppt/slides/slide\d+\.xml$", n)],
                        key=lambda n: int(re.findall(r"\d+", n)[-1]))
        if not slides:
            raise ValueError("不像 .pptx（没有 ppt/slides/slideN.xml）")
        out = []
        for i, name in enumerate(slides, 1):
            root = ET.fromstring(zf.read(name))
            texts = [t.text or "" for t in root.iter(
                "{http://schemas.openxmlformats.org/drawingml/2006/main}t")]
            out.append("## 第 %d 页" % i)
            out.extend(texts)
            out.append("")
    return "\n".join(out).strip() + "\n"


# --------------------------------------------------------------------------- #
# PDF 读（只提文本层；扫描件没有文字层）
# --------------------------------------------------------------------------- #
_OBJ_RE = re.compile(rb"(\d+)\s+(\d+)\s+obj(.*?)endobj", re.S)


def _pdf_objects(data):
    objs = {}
    for m in _OBJ_RE.finditer(data):
        num = int(m.group(1))
        body = m.group(3)
        objs[num] = body
    return objs


def _pdf_stream(body):
    i = body.find(b"stream")
    if i < 0:
        return None
    j = i + 6
    if body[j:j + 2] == b"\r\n":
        j += 2
    elif body[j:j + 1] in (b"\n", b"\r"):
        j += 1
    k = body.find(b"endstream", j)
    raw = body[j:k if k >= 0 else len(body)]
    if b"/FlateDecode" in body[:i]:
        try:
            raw = zlib.decompress(raw)
        except zlib.error:
            try:
                raw = zlib.decompressobj().decompress(raw)
            except zlib.error:
                return None
    return raw


def _balanced_dict(buf, start):
    """从 << 开始做括号配对，返回完整字典（含 << >>）。"""
    depth, i = 0, start
    while i < len(buf) - 1:
        two = buf[i:i + 2]
        if two == b"<<":
            depth += 1
            i += 2
            continue
        if two == b">>":
            depth -= 1
            i += 2
            if depth == 0:
                return buf[start:i]
            continue
        i += 1
    return buf[start:]


def _deref_dict(objs, body, key):
    """取 /key 指向的字典：内联 <<...>> 或 引用 12 0 R 都认（v2.3.2）。"""
    if not body:
        return b""
    m = re.search(rb"/" + key + rb"\s*(<<|(\d+)\s+\d+\s+R)", body)
    if not m:
        return b""
    if m.group(1) == b"<<":
        return _balanced_dict(body, m.start(1))
    return objs.get(int(m.group(2)), b"")


def _pdf_objstm_objects(objs):
    """解出压缩在 /ObjStm 里的对象（PDF 1.5+ 很常见）。"""
    extra = {}
    for _num, body in objs.items():
        if b"/ObjStm" not in body[:400]:
            continue
        stream = _pdf_stream(body)
        if not stream:
            continue
        m = re.search(rb"/First\s+(\d+)", body)
        first = int(m.group(1)) if m else 0
        head = stream[:first].split()
        pairs = []
        for i in range(0, len(head) - 1, 2):
            try:
                pairs.append((int(head[i]), int(head[i + 1])))
            except ValueError:
                break
        for i, (onum, off) in enumerate(pairs):
            end = first + pairs[i + 1][1] if i + 1 < len(pairs) else len(stream)
            if onum and onum not in extra:
                extra[onum] = stream[first + off:end]
    return extra


def _pdf_dict_int(body, key):
    m = re.search(rb"/" + key + rb"\s+(\d+)", body)
    return int(m.group(1)) if m else None


def _pdf_refs(body, key):
    m = re.search(rb"/" + key + rb"\s*(\[[^\]]*\]|\d+\s+\d+\s+R)", body, re.S)
    if not m:
        return []
    chunk = m.group(1)
    if chunk.startswith(b"["):
        return [int(x) for x in re.findall(rb"(\d+)\s+\d+\s+R", chunk)]
    nums = re.findall(rb"(\d+)\s+\d+\s+R", chunk)
    return [int(nums[0])] if nums else []


def _parse_tounicode(stream):
    """CMap -> {code:int -> str}；支持 bfchar / bfrange。"""
    table = {}
    if not stream:
        return table
    for block in re.findall(rb"beginbfchar(.*?)endbfchar", stream, re.S):
        for src, dst in re.findall(rb"<([0-9A-Fa-f]+)>\s*<([0-9A-Fa-f]+)>", block):
            try:
                table[int(src, 16)] = bytes.fromhex(dst.decode()).decode("utf-16-be", "replace")
            except Exception:
                pass
    for block in re.findall(rb"beginbfrange(.*?)endbfrange", stream, re.S):
        # 形式 2：<lo> <hi> [<u1> <u2> ...]（Word 导出的 PDF 常用这个）
        for lo, hi, arr in re.findall(
                rb"<([0-9A-Fa-f]+)>\s*<([0-9A-Fa-f]+)>\s*\[([^\]]*)\]", block, re.S):
            try:
                a = int(lo, 16)
                for k, u in enumerate(re.findall(rb"<([0-9A-Fa-f]+)>", arr)):
                    digits = u.decode()
                    if len(digits) % 4:
                        digits = digits.zfill(((len(digits) // 4) + 1) * 4)
                    table[a + k] = bytes.fromhex(digits).decode("utf-16-be", "replace")
            except Exception:
                pass
        # 形式 1：<lo> <hi> <dst>（先把数组形式的段落剔掉，免得串味）
        rest = re.sub(rb"<[0-9A-Fa-f]+>\s*<[0-9A-Fa-f]+>\s*\[[^\]]*\]", b" ", block)
        for lo, hi, dst in re.findall(
                rb"<([0-9A-Fa-f]+)>\s*<([0-9A-Fa-f]+)>\s*<([0-9A-Fa-f]+)>", rest):
            try:
                a, b = int(lo, 16), int(hi, 16)
                base = int(dst, 16)
                for k in range(a, min(b, a + 512) + 1):
                    table[k] = chr(base + (k - a))
            except Exception:
                pass
    return table


def _pdf_font_maps(objs, page_body):
    """资源里每个字体名 -> (ToUnicode 表, 几字节编码)"""
    maps = {}
    res = _deref_dict(objs, page_body, b"Resources") or page_body
    font_dict = _deref_dict(objs, res, b"Font")
    if not font_dict:
        m = re.search(rb"/Font\s*<<", res)
        font_dict = _balanced_dict(res, m.end() - 2) if m else b""
    if not font_dict:
        return maps
    for name, num in re.findall(rb"/([A-Za-z0-9_.+-]+)\s+(\d+)\s+\d+\s+R", font_dict):
        body = objs.get(int(num)) or b""
        tu = _pdf_refs(body, b"ToUnicode")
        table = {}
        if tu:
            st = _pdf_stream(objs.get(tu[0]) or b"")
            table = _parse_tounicode(st)
        two = b"/Type0" in body or b"Identity-H" in body
        maps[name.decode("latin-1")] = (table, two)
    return maps


def _pdf_decode_string(raw, font):
    table, two = font if font else ({}, False)
    if table:
        codes = []
        if two:
            codes = [int.from_bytes(raw[i:i + 2], "big") for i in range(0, len(raw) - 1, 2)]
        else:
            codes = list(raw)
        if codes:
            out = "".join(table.get(c, "") for c in codes)
            if out.strip():
                return out
    try:
        return raw.decode("cp1252")
    except UnicodeDecodeError:
        return raw.decode("latin-1")


_PDF_TOKEN = re.compile(rb"""
    (?P<hex><[0-9A-Fa-f\s]*>)
  | (?P<lit>\((?:\\.|[^\\()])*\))
  | (?P<name>/[^\s/\[\]<>()]+)
  | (?P<num>-?\d*\.?\d+)
  | (?P<op>[A-Za-z'"*]+)
  | (?P<arr>[\[\]])
  | \s+
""", re.X | re.S)


def _pdf_page_text(content, fonts):
    """按坐标还原文行：同一 y 的片段拼一行，y 变了才换行。"""
    if not content:
        return ""
    out = []
    cur_font = None
    stack = []
    last_y = None
    last_x = None
    last_dx = None

    def newline():
        if out and not "".join(out[-1:]).endswith("\n"):
            out.append("\n")

    def space():
        if out and not "".join(out[-1:]).endswith((" ", "\n")):
            out.append(" ")

    for m in _PDF_TOKEN.finditer(content):
        g = m.group
        if g("name"):
            stack.append(("name", g("name")[1:].decode("latin-1")))
            continue
        if g("hex") is not None:
            h = re.sub(rb"\s", b"", g("hex")[1:-1])
            if len(h) % 2:
                h += b"0"
            try:
                stack.append(("str", bytes.fromhex(h.decode())))
            except ValueError:
                stack.append(("str", b""))
            continue
        if g("lit") is not None:
            raw = g("lit")[1:-1]
            raw = re.sub(rb"\\([nrtbf()\\])", lambda mm: {
                b"n": b"\n", b"r": b"\r", b"t": b"\t", b"b": b"\b", b"f": b"\f",
                b"(": b"(", b")": b")", b"\\": b"\\"}[mm.group(1)], raw)
            stack.append(("str", raw))
            continue
        if g("num"):
            stack.append(("num", g("num")))
            continue
        if g("arr"):
            stack.append(("arr", g("arr")))
            continue
        op = g("op")
        if op is None:
            continue
        op = op.decode("latin-1")
        if op == "Tf":
            names = [v for k, v in stack if k == "name"]
            if names:
                cur_font = fonts.get(names[-1])
        elif op in ("Tj", "'", '"'):
            strs = [v for k, v in stack if k == "str"]
            if strs:
                if op != "Tj":
                    newline()
                out.append(_pdf_decode_string(strs[-1], cur_font))
        elif op == "TJ":
            parts = []
            for k, v in stack:
                if k == "str":
                    parts.append(_pdf_decode_string(v, cur_font))
                elif k == "num":
                    try:
                        if float(v) < -150:
                            parts.append(" ")
                    except (TypeError, ValueError):
                        pass
            out.append("".join(parts))
        elif op == "Tm":
            nums = []
            for k, v in stack:
                if k == "num":
                    try:
                        nums.append(float(v))
                    except ValueError:
                        pass
            if len(nums) >= 6:
                nx, ny = nums[-2], nums[-1]
                if last_y is not None:
                    if abs(ny - last_y) > 2.0:
                        newline()
                    elif last_x is not None and nx - last_x > 2.5:
                        space()
                last_y, last_x = ny, nx
        elif op in ("Td", "TD"):
            nums = []
            for k, v in stack:
                if k == "num":
                    try:
                        nums.append(float(v))
                    except ValueError:
                        pass
            if len(nums) >= 2:
                dx, dy = nums[-2], nums[-1]
                # 逐字定位的 PDF 里，字间距也常有 2~8 个用户单位；
                # 用"比上一个步长大一倍以上"才算词间距，别把单词拆开
                thr = 2.5 if last_dx is None else max(2.5, abs(last_dx) * 1.6)
                if abs(dy) > 2.0:
                    newline()
                elif abs(dx) > thr:
                    space()
                if abs(dx) > 0.01:
                    last_dx = dx
                if last_y is not None:
                    last_y = last_y + dy
                if last_x is not None:
                    last_x = last_x + dx
        elif op == "T*":
            newline()
        stack = []
    text = "".join(out)
    text = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f]", "", text)
    text = re.sub(r"[ \t]+\n", "\n", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def read_pdf(path, pages=None, max_chars=80000):
    data = _read(path)
    if not data.startswith(b"%PDF"):
        raise ValueError("不像 PDF（开头不是 %%PDF）")
    if len(data) > MAX_PDF_BYTES:
        raise ValueError("这个 PDF 有 %.0f MB，超过 %d MB 上限，先拆分再读"
                         % (len(data) / 1048576.0, MAX_PDF_BYTES // 1048576))
    objs = _pdf_objects(data)
    for num, body in _pdf_objstm_objects(objs).items():
        objs.setdefault(num, body)
    page_nums = sorted(n for n, b in objs.items()
                       if re.search(rb"/Type\s*/Page[^s]", b))
    if not page_nums:
        kids = []
        for b in objs.values():
            if re.search(rb"/Type\s*/Pages", b):
                kids.extend(int(x) for x in re.findall(rb"(\d+)\s+\d+\s+R", b))
        page_nums = [k for k in kids if k in objs]
    if not page_nums:
        return ("（读不出来：这个 PDF 的页结构解析不了，可能用了加密或特殊压缩。\n"
                " 建议：用 Word/WPS/浏览器打开后另存为 .docx 或 .txt 再读。）")
    if pages:
        lo, hi = pages
        page_nums = page_nums[max(0, lo - 1):hi]
    out = []
    used = 0
    for i, num in enumerate(page_nums, 1):
        body = objs[num]
        fonts = _pdf_font_maps(objs, body)
        content = b""
        for cnum in _pdf_refs(body, b"Contents"):
            content += (_pdf_stream(objs.get(cnum) or b"") or b"")
        if not content:
            m = re.search(rb"/Contents\s*\[([^\]]*)\]", body, re.S)
            if m:
                for cnum in [int(x) for x in re.findall(rb"(\d+)\s+\d+\s+R", m.group(1))]:
                    content += (_pdf_stream(objs.get(cnum) or b"") or b"")
        text = _pdf_page_text(content, fonts)
        block = "\n--- 第 %d 页 ---\n%s" % (i, text) if text else "\n--- 第 %d 页（没有文字层）---" % i
        out.append(block)
        used += len(block)
        if used > max_chars:
            out.append("\n（后面还有内容，已截断；用 pages=[起始页, 结束页] 分段读）")
            break
    text = "\n".join(out).strip() + "\n"
    body = text
    bad = sum(1 for ch in body if ord(ch) < 32 and ch not in "\n\t")
    total = max(1, len(body))
    if bad / total > 0.15:
        return ("（提取失败：这个 PDF 的字体编码解不出来，约 %d%% 的字符是乱码。\n"
                " 建议：用 Word/WPS 打开后另存为 .docx 或 .txt 再读；"
                "如果是扫描件，需要 OCR，本工具做不到。）" % int(bad * 100 / total))
    if b"/ObjStm" in data and not page_nums:
        text = "（注意：这个 PDF 用了对象流，可能只解析出一部分内容）\n" + text
    return text


# --------------------------------------------------------------------------- #
# 统一读
# --------------------------------------------------------------------------- #
def doc_read(path, pages=None, max_chars=80000):
    _need(path)
    kind = kind_of(path)
    if kind == "docx":
        return read_docx(path)
    if kind == "xlsx":
        return read_xlsx(path)
    if kind == "pptx":
        return read_pptx(path)
    if kind == "pdf":
        return read_pdf(path, pages=pages, max_chars=max_chars)
    if kind in ("doc", "xls", "ppt", "rtf"):
        raise ValueError("这是老格式（.%s），本工具读不了。先让我用 office_convert 转成 .%s 再读。"
                         % (kind, {"doc": "docx", "xls": "xlsx", "ppt": "pptx",
                                   "rtf": "docx"}[kind]))
    # 纯文本：自动认编码
    raw = _read(path)
    for enc in ("utf-8-sig", "utf-8", "gbk"):
        try:
            return raw.decode(enc)
        except UnicodeDecodeError:
            continue
    return raw.decode("utf-8", "replace")


# --------------------------------------------------------------------------- #
# Word 写（Markdown 子集 -> docx）
# --------------------------------------------------------------------------- #
_BAD_XML = re.compile("[\x00-\x08\x0b\x0c\x0e-\x1f\ufffe\uffff]")


def _clean_xml_text(s):
    """XML 1.0 不允许的控制字符会被 Word/Excel 拒绝，直接抹掉。"""
    s = _BAD_XML.sub("", str(s))
    return "".join(ch for ch in s if not (0xD800 <= ord(ch) <= 0xDFFF))


def _x(s):
    return (_clean_xml_text(s).replace("&", "&amp;").replace("<", "&lt;")
            .replace(">", "&gt;").replace('"', "&quot;"))


def _runs_xml(text, bold=False, mono=False):
    """把 **粗体** 和 `等宽` 拆成多个 run。"""
    parts = re.split(r"(\*\*[^*]+\*\*|`[^`]+`)", text)
    out = []
    for p in parts:
        if not p:
            continue
        b = bold
        m = mono
        if p.startswith("**") and p.endswith("**") and len(p) > 4:
            p = p[2:-2]
            b = True
        elif p.startswith("`") and p.endswith("`") and len(p) > 2:
            p = p[1:-1]
            m = True
        rpr = ""
        if b:
            rpr += "<w:b/>"
        if m:
            rpr += '<w:rFonts w:ascii="Consolas" w:hAnsi="Consolas"/>'
        out.append('<w:r>%s<w:t xml:space="preserve">%s</w:t></w:r>'
                   % ("<w:rPr>%s</w:rPr>" % rpr if rpr else "", _x(p)))
    return "".join(out) or '<w:r><w:t xml:space="preserve"></w:t></w:r>'


def _para_xml(text, style=None, bold=False, mono=False, indent=0):
    ppr = ""
    if style:
        ppr += '<w:pStyle w:val="%s"/>' % style
    if indent:
        ppr += '<w:ind w:left="%d"/>' % (indent * 360)
    return "<w:p>%s%s</w:p>" % ("<w:pPr>%s</w:pPr>" % ppr if ppr else "",
                               _runs_xml(text, bold=bold, mono=mono))


def _table_xml(rows):
    if not rows:
        return ""
    width = max(len(r) for r in rows)
    out = ['<w:tbl><w:tblPr><w:tblStyle w:val="TableGrid"/><w:tblW w:type="auto" w:w="0"/>'
           '</w:tblPr><w:tblGrid>']
    out.append("<w:gridCol/>" * width)
    out.append("</w:tblGrid>")
    for ri, row in enumerate(rows):
        out.append("<w:tr>")
        for ci in range(width):
            cell = row[ci] if ci < len(row) else ""
            out.append("<w:tc><w:tcPr><w:tcW w:type=\"auto\" w:w=\"0\"/></w:tcPr>"
                       + _para_xml(cell, bold=(ri == 0)) + "</w:tc>")
        out.append("</w:tr>")
    out.append("</w:tbl>")
    return "".join(out)


def _split_table_row(line):
    s = line.strip()
    if s.startswith("|"):
        s = s[1:]
    if s.endswith("|"):
        s = s[:-1]
    return [c.strip() for c in s.split("|")]


def md_to_docx_body(text):
    lines = text.replace("\r\n", "\n").replace("\r", "\n").split("\n")
    body = []
    i = 0
    n = len(lines)
    while i < n:
        line = lines[i]
        stripped = line.strip()
        if stripped.startswith("```"):
            i += 1
            code = []
            while i < n and not lines[i].strip().startswith("```"):
                code.append(lines[i])
                i += 1
            i += 1
            for c in code:
                body.append(_para_xml(c if c else " ", style="Code", mono=True))
            body.append(_para_xml(""))
            continue
        if stripped.startswith("|") and stripped.count("|") >= 2:
            rows = []
            while i < n and lines[i].strip().startswith("|"):
                cells = _split_table_row(lines[i])
                if not all(re.match(r"^:?-{2,}:?$", c) for c in cells if c):
                    rows.append(cells)
                i += 1
            body.append(_table_xml(rows))
            body.append(_para_xml(""))
            continue
        if not stripped:
            body.append(_para_xml(""))
            i += 1
            continue
        m = re.match(r"^(#{1,6})\s+(.*)$", stripped)
        if m:
            lvl = min(len(m.group(1)), 6)
            body.append(_para_xml(m.group(2), style="Heading%d" % lvl))
            i += 1
            continue
        m = re.match(r"^[-*+]\s+(.*)$", stripped)
        if m:
            body.append(_para_xml(m.group(1), style="ListBullet"))
            i += 1
            continue
        m = re.match(r"^(\d+)[.)]\s+(.*)$", stripped)
        if m:
            body.append(_para_xml("%s. %s" % (m.group(1), m.group(2)), style="ListNumber"))
            i += 1
            continue
        if stripped.startswith("> "):
            body.append(_para_xml(stripped[2:], style="Quote"))
            i += 1
            continue
        if stripped in ("---", "***", "___"):
            body.append('<w:p><w:pPr><w:pBdr><w:bottom w:val="single" w:sz="6" '
                        'w:space="1" w:color="auto"/></w:pBdr></w:pPr></w:p>')
            i += 1
            continue
        body.append(_para_xml(stripped))
        i += 1
    return "".join(body)


STYLES_XML = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<w:styles xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">
<w:docDefaults><w:rPrDefault><w:rPr><w:rFonts w:ascii="Calibri" w:hAnsi="Calibri"
 w:eastAsia="宋体"/><w:sz w:val="22"/></w:rPr></w:rPrDefault>
 <w:pPrDefault><w:pPr><w:spacing w:after="120"/></w:pPr></w:pPrDefault></w:docDefaults>
<w:style w:type="paragraph" w:default="1" w:styleId="Normal"><w:name w:val="Normal"/></w:style>
<w:style w:type="paragraph" w:styleId="Heading1"><w:name w:val="heading 1"/>
 <w:basedOn w:val="Normal"/><w:pPr><w:keepNext/><w:spacing w:before="240" w:after="120"/>
 <w:outlineLvl w:val="0"/></w:pPr><w:rPr><w:b/><w:sz w:val="36"/></w:rPr></w:style>
<w:style w:type="paragraph" w:styleId="Heading2"><w:name w:val="heading 2"/>
 <w:basedOn w:val="Normal"/><w:pPr><w:keepNext/><w:spacing w:before="200" w:after="100"/>
 <w:outlineLvl w:val="1"/></w:pPr><w:rPr><w:b/><w:sz w:val="30"/></w:rPr></w:style>
<w:style w:type="paragraph" w:styleId="Heading3"><w:name w:val="heading 3"/>
 <w:basedOn w:val="Normal"/><w:pPr><w:keepNext/><w:spacing w:before="160" w:after="80"/>
 <w:outlineLvl w:val="2"/></w:pPr><w:rPr><w:b/><w:sz w:val="26"/></w:rPr></w:style>
<w:style w:type="paragraph" w:styleId="Heading4"><w:name w:val="heading 4"/>
 <w:basedOn w:val="Normal"/><w:pPr><w:outlineLvl w:val="3"/></w:pPr>
 <w:rPr><w:b/><w:sz w:val="24"/></w:rPr></w:style>
<w:style w:type="paragraph" w:styleId="Heading5"><w:name w:val="heading 5"/>
 <w:basedOn w:val="Normal"/><w:pPr><w:outlineLvl w:val="4"/></w:pPr><w:rPr><w:b/></w:rPr></w:style>
<w:style w:type="paragraph" w:styleId="Heading6"><w:name w:val="heading 6"/>
 <w:basedOn w:val="Normal"/><w:pPr><w:outlineLvl w:val="5"/></w:pPr><w:rPr><w:b/></w:rPr></w:style>
<w:style w:type="paragraph" w:styleId="ListBullet"><w:name w:val="List Bullet"/>
 <w:basedOn w:val="Normal"/><w:pPr><w:numPr><w:ilvl w:val="0"/><w:numId w:val="1"/></w:numPr></w:pPr></w:style>
<w:style w:type="paragraph" w:styleId="ListNumber"><w:name w:val="List Number"/>
 <w:basedOn w:val="Normal"/></w:style>
<w:style w:type="paragraph" w:styleId="Quote"><w:name w:val="Quote"/>
 <w:basedOn w:val="Normal"/><w:pPr><w:ind w:left="567"/></w:pPr>
 <w:rPr><w:i/><w:color w:val="555555"/></w:rPr></w:style>
<w:style w:type="paragraph" w:styleId="Code"><w:name w:val="Code"/>
 <w:basedOn w:val="Normal"/><w:pPr><w:spacing w:after="0"/></w:pPr>
 <w:rPr><w:rFonts w:ascii="Consolas" w:hAnsi="Consolas"/><w:sz w:val="18"/></w:rPr></w:style>
<w:style w:type="table" w:styleId="TableGrid"><w:name w:val="Table Grid"/>
 <w:tblPr><w:tblBorders>
  <w:top w:val="single" w:sz="4"/><w:left w:val="single" w:sz="4"/>
  <w:bottom w:val="single" w:sz="4"/><w:right w:val="single" w:sz="4"/>
  <w:insideH w:val="single" w:sz="4"/><w:insideV w:val="single" w:sz="4"/>
 </w:tblBorders></w:tblPr></w:style>
</w:styles>"""

NUMBERING_XML = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<w:numbering xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">
<w:abstractNum w:abstractNumId="0"><w:lvl w:ilvl="0"><w:start w:val="1"/>
 <w:numFmt w:val="bullet"/><w:lvlText w:val="\u2022"/><w:lvlJc w:val="left"/>
 <w:pPr><w:ind w:left="720" w:hanging="360"/></w:pPr></w:lvl></w:abstractNum>
<w:num w:numId="1"><w:abstractNumId w:val="0"/></w:num>
</w:numbering>"""

CONTENT_TYPES = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>
<Default Extension="xml" ContentType="application/xml"/>
<Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/>
<Override PartName="/word/styles.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.styles+xml"/>
<Override PartName="/word/numbering.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.numbering+xml"/>
</Types>"""

ROOT_RELS = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="word/document.xml"/>
</Relationships>"""

DOC_RELS = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/styles" Target="styles.xml"/>
<Relationship Id="rId2" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/numbering" Target="numbering.xml"/>
</Relationships>"""


def write_docx(path, text, title=None):
    body = md_to_docx_body(text)
    if title:
        body = _para_xml(title, style="Heading1") + body
    doc = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
           '<w:document xmlns:w="%s" xmlns:r="%s"><w:body>%s'
           '<w:sectPr><w:pgSz w:w="11906" w:h="16838"/>'
           '<w:pgMar w:top="1134" w:right="1134" w:bottom="1134" w:left="1134"/></w:sectPr>'
           '</w:body></w:document>') % (W, R, body or _para_xml(""))
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("[Content_Types].xml", CONTENT_TYPES)
        zf.writestr("_rels/.rels", ROOT_RELS)
        zf.writestr("word/document.xml", doc)
        zf.writestr("word/styles.xml", STYLES_XML)
        zf.writestr("word/numbering.xml", NUMBERING_XML)
        zf.writestr("word/_rels/document.xml.rels", DOC_RELS)
    return "已生成 Word：%s（%s）" % (path, _fmt_size(os.path.getsize(path)))


# --------------------------------------------------------------------------- #
# Excel 写（Markdown 表格 / CSV -> xlsx）
# --------------------------------------------------------------------------- #
def _col_name(n):
    s = ""
    while n > 0:
        n, r = divmod(n - 1, 26)
        s = chr(65 + r) + s
    return s


def _sheet_xml(rows):
    out = ['<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
           '<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">'
           '<sheetData>']
    for ri, row in enumerate(rows, 1):
        out.append('<row r="%d">' % ri)
        for ci, val in enumerate(row, 1):
            ref = "%s%d" % (_col_name(ci), ri)
            s = str(val)
            if re.match(r"^-?\d+(\.\d+)?$", s.strip()) and len(s) < 16:
                out.append('<c r="%s"><v>%s</v></c>' % (ref, s.strip()))
            else:
                out.append('<c r="%s" t="inlineStr"><is><t xml:space="preserve">%s</t></is></c>'
                           % (ref, _x(s)))
        out.append("</row>")
    out.append("</sheetData></worksheet>")
    return "".join(out)


XLSX_CT = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>
<Default Extension="xml" ContentType="application/xml"/>
<Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/>
<Override PartName="/xl/worksheets/sheet1.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>
<Override PartName="/xl/styles.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.styles+xml"/>
</Types>"""

XLSX_RELS_ROOT = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="xl/workbook.xml"/>
</Relationships>"""

XLSX_WB_RELS = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet1.xml"/>
<Relationship Id="rId2" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/styles" Target="styles.xml"/>
</Relationships>"""

XLSX_STYLES = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<styleSheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">
<fonts count="1"><font><sz val="11"/><name val="Calibri"/></font></fonts>
<fills count="1"><fill><patternFill patternType="none"/></fill></fills>
<borders count="1"><border/></borders>
<cellStyleXfs count="1"><xf numFmtId="0" fontId="0" fillId="0" borderId="0"/></cellStyleXfs>
<cellXfs count="1"><xf numFmtId="0" fontId="0" fillId="0" borderId="0" xfId="0"/></cellXfs>
</styleSheet>"""


def _parse_rows(text):
    rows = []
    for line in text.replace("\r\n", "\n").replace("\r", "\n").split("\n"):
        if not line.strip():
            continue
        if line.strip().startswith("|"):
            cells = _split_table_row(line)
            if all(re.match(r"^:?-{2,}:?$", c) for c in cells if c):
                continue
            rows.append(cells)
        elif "\t" in line:
            rows.append(line.split("\t"))
        else:
            rows.append([c.strip() for c in line.split(",")])
    return rows


def write_xlsx(path, text, sheet_name="Sheet1"):
    rows = _parse_rows(text)
    wb = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
          '<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" '
          'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">'
          '<sheets><sheet name="%s" sheetId="1" r:id="rId1"/></sheets></workbook>') % _x(sheet_name)
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("[Content_Types].xml", XLSX_CT)
        zf.writestr("_rels/.rels", XLSX_RELS_ROOT)
        zf.writestr("xl/workbook.xml", wb)
        zf.writestr("xl/_rels/workbook.xml.rels", XLSX_WB_RELS)
        zf.writestr("xl/styles.xml", XLSX_STYLES)
        zf.writestr("xl/worksheets/sheet1.xml", _sheet_xml(rows))
    return "已生成 Excel：%s（%d 行，%s）" % (
        path, len(rows), _fmt_size(os.path.getsize(path)))


def doc_write(path, content, title=None):
    ext = os.path.splitext(str(path))[1].lower()
    if ext == ".docx":
        return write_docx(path, content, title=title)
    if ext in (".xlsx", ".xlsm"):
        return write_xlsx(path, content)
    if ext in (".csv", ".txt", ".md"):
        with open(path, "w", encoding="utf-8-sig" if ext == ".csv" else "utf-8",
                  newline="") as fh:
            fh.write(content if content.endswith("\n") else content + "\n")
        return "已写入：%s（%d 字）" % (path, len(content))
    raise ValueError("doc_write 只支持 .docx / .xlsx / .csv / .md / .txt，收到的是 %s" % ext)


# --------------------------------------------------------------------------- #
# Word 改（查找替换，另存）
# --------------------------------------------------------------------------- #
TEXT_PART_RE = re.compile(r"^word/(document|header\d*|footer\d*|footnotes|endnotes)\.xml$")
T_RE = re.compile(r"<w:t(\s[^>]*)?>(.*?)</w:t>", re.S)
P_RE = re.compile(r"<w:p\b[^>]*>.*?</w:p>", re.S)


def _unesc(s):
    return (s.replace("&lt;", "<").replace("&gt;", ">").replace("&quot;", '"')
             .replace("&apos;", "'").replace("&amp;", "&"))


def _esc(s):
    return (_clean_xml_text(s).replace("&", "&amp;").replace("<", "&lt;")
            .replace(">", "&gt;"))


def _splice(para, nodes, texts, s, e, new):
    """把段落里 [s,e) 这段文字换成 new（跨多个 <w:t> 时写在第一个里）。"""
    spans = []
    pos = 0
    for t in texts:
        spans.append((pos, pos + len(t)))
        pos += len(t)
    first = next(i for i, (a, b) in enumerate(spans) if b > s)
    last = next(i for i, (a, b) in enumerate(spans) if b >= e)
    pre = texts[first][: s - spans[first][0]]
    post = texts[last][e - spans[last][0]:]
    texts[first] = pre + new + (post if first == last else "")
    if last != first:
        texts[last] = post
        for k in range(first + 1, last):
            texts[k] = ""
    out = []
    cur = 0
    for i, m in enumerate(nodes):
        out.append(para[cur:m.start(2)])
        out.append(_esc(texts[i]))
        cur = m.end(2)
    out.append(para[cur:])
    return "".join(out)


def _fill_para(para, old, new, limit=500):
    """替换一个段落里的全部 old。

    v2.3.1：从"插入内容之后"继续找，绝不回头重扫 —— 否则 公司→公司名称 这类
    "新值包含旧值"的替换会无限复制（旧版会写到 200 次上限）。
    """
    if not old:
        return para, 0
    hits = 0
    pos = 0
    guard = 0
    while guard < limit:
        guard += 1
        nodes = list(T_RE.finditer(para))
        if not nodes:
            break
        texts = [_unesc(m.group(2)) for m in nodes]
        full = "".join(texts)
        idx = full.find(old, pos)
        if idx < 0:
            break
        para = _splice(para, nodes, texts, idx, idx + len(old), new)
        pos = idx + len(new)
        hits += 1
    return para, hits


def _fill_part(xml, pairs):
    hits = [0] * len(pairs)

    def one(m):
        para = m.group(0)
        for i, (old, new) in enumerate(pairs):
            para, n = _fill_para(para, old, new)
            hits[i] += n
        return para

    return P_RE.sub(one, xml), hits


def _zip_parts(data):
    with zipfile.ZipFile(io.BytesIO(data)) as zf:
        return [(i.filename, zf.read(i.filename)) for i in zf.infolist()]


def _verify_intact(before, out_path, changed):
    """改完再比一遍：除了我们动过的文字部件，其余必须逐字节完全一致。"""
    try:
        before_parts = dict(before)
        with zipfile.ZipFile(out_path) as zf:
            names = [i.filename for i in zf.infolist()]
            after = dict((n, zf.read(n)) for n in names)
    except Exception as exc:                      # noqa: BLE001
        return False, "校验打不开结果文件：%s" % exc
    if set(names) != set(before_parts):
        return False, "部件清单变了（模板里少了/多了文件），可能有损坏"
    broken = []
    for name in changed:
        blob = after.get(name)
        if blob is None:
            continue
        try:
            ET.fromstring(blob)
        except Exception:
            broken.append(name)
    if broken:
        return False, "改过的部件不是合法 XML：%s（写入的内容里可能有控制字符）" % "、".join(broken)
    diff = [n for n in names if n not in changed and before_parts.get(n) != after.get(n)]
    if diff:
        return False, "有 %d 个部件被意外改动：%s" % (len(diff), "、".join(diff[:4]))
    media = [n for n in names if n.startswith("word/media/")]
    heads = [n for n in names if re.match(r"word/header\d*\.xml$", n)]
    foots = [n for n in names if re.match(r"word/footer\d*\.xml$", n)]
    return True, ("其余 %d 个部件逐字节未变（图片 %d 张、页眉 %d 个、页脚 %d 个）"
                  % (len(names) - len(changed), len(media), len(heads), len(foots)))


def docx_fill(template, mapping=None, pairs=None, out=None):
    """在 Word 模板上原位填空：只改文字，页眉页脚图片样式全都原样保留。"""
    _need(template)
    data = _read(template)
    with zipfile.ZipFile(io.BytesIO(data)) as zf:
        names = zf.namelist()
    if "word/document.xml" not in names:
        raise ValueError("不像 .docx（缺 word/document.xml）；.doc 请先 convert 成 docx")

    jobs = []
    for k, v in (mapping or {}).items():
        k = str(k)
        if "{{" in k or "}}" in k:
            jobs.append((k, "" if v is None else str(v)))
        else:
            jobs.append(("{{%s}}" % k, "" if v is None else str(v)))
    for old, new in (pairs or []):
        jobs.append((str(old), "" if new is None else str(new)))
    if not jobs:
        raise ValueError("没有要填的内容：给 mapping={'姓名': '张三'} 或 pairs=[('旧', '新')]")

    changed = []
    total = 0
    per_key = [0] * len(jobs)
    out = out or os.path.splitext(template)[0] + "-填写.docx"
    with zipfile.ZipFile(io.BytesIO(data)) as zf:
        targets = [n for n in names if TEXT_PART_RE.match(n)]
        new_parts = {}
        for name in targets:
            xml = zf.read(name).decode("utf-8")
            filled, hits = _fill_part(xml, jobs)
            if filled != xml:
                new_parts[name] = filled.encode("utf-8")
                changed.append(name)
                for i, h in enumerate(hits):
                    per_key[i] += h
        total = sum(per_key)
        with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as zo:
            for item in zf.infolist():
                if item.filename in new_parts:
                    zo.writestr(item, new_parts[item.filename])
                else:
                    zo.writestr(item, zf.read(item.filename))

    done = ["%s（%d 处）" % (jobs[i][0], c) for i, c in enumerate(per_key) if c]
    miss = [jobs[i][0] for i, c in enumerate(per_key) if not c]
    msg = "已另存：%s" % out
    if done:
        msg += "\n已填 %d 处：%s" % (total, "；".join(done))
    if miss:
        msg += ("\n没找到：%s（模板里可能没有这个占位，或写法不一致；"
                "也可能是图片/文本框里的字，那种改不了）" % "；".join(miss))
    ok, detail = _verify_intact(_zip_parts(data), out, set(changed))
    msg += "\n%s：%s" % ("结构自检通过" if ok else "结构自检失败", detail)
    return msg


def docx_replace(path, replacements, out=None):
    pairs = [(str(o), str(n)) for o, n in replacements]
    return docx_fill(path, pairs=pairs, out=out)


# --------------------------------------------------------------------------- #
# Excel 改单元格（保留其它内容）
# --------------------------------------------------------------------------- #
def _ensure_shared(zf_read, names):
    """返回 (sharedStrings 原始 XML 文本, 条目列表)；没有就造一个空的。"""
    if "xl/sharedStrings.xml" in names:
        xml = zf_read("xl/sharedStrings.xml").decode("utf-8")
    else:
        xml = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
               '<sst xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" '
               'count="0" uniqueCount="0"/>')
    root = ET.fromstring(xml)
    items = []
    for si in root:
        items.append("".join(t.text or "" for t in si.iter(
            "{http://schemas.openxmlformats.org/spreadsheetml/2006/main}t")))
    return xml, items


SST_CT = ('<Override PartName="/xl/sharedStrings.xml" '
          'ContentType="application/vnd.openxmlformats-officedocument.'
          'spreadsheetml.sharedStrings+xml"/>')
SST_REL = ('<Relationship Id="rIdEmberSst" Type="http://schemas.openxmlformats.org/'
           'officeDocument/2006/relationships/sharedStrings" Target="sharedStrings.xml"/>')


def _cell_re(ref):
    return re.compile(r'<c\b[^>]*?\br="%s"[^>]*?(?:/>|>.*?</c>)' % re.escape(ref.upper()),
                      re.S)


def _cell_open_tag(chunk):
    m = re.match(r'<c\b([^>]*?)/?>', chunk, re.S)
    return m.group(1) if m else ""


def _strip_attr(attrs, name):
    return re.sub(r'\s+%s="[^"]*"' % name, "", attrs)


def xlsx_set(path, updates):
    """改已有单元格；保留其它内容与格式，并保证包结构合规（v2.3.1）。

    修的三件事：
      1. 写字符串时补 [Content_Types].xml 的 Override 和 workbook.xml.rels 的关系
         （以前只加 sharedStrings.xml，Excel 会报"需要修复"）；
      2. 设置新值前删掉 <f>，否则 Excel 重算会把新值覆盖；
      3. 不再用 ElementTree 整体重放工作表（会丢 mc:Ignorable / x14ac 声明和富文本），
         改成只替换目标 <c> 节点。
    """
    _need(path)
    data = _read(path)
    with zipfile.ZipFile(io.BytesIO(data)) as zf:
        names = zf.namelist()
        sheets = dict(_xlsx_sheets(zf))
        sst_xml = zf.read("xl/sharedStrings.xml").decode("utf-8") \
            if "xl/sharedStrings.xml" in names else ""
        ct_xml = zf.read("[Content_Types].xml").decode("utf-8") \
            if "[Content_Types].xml" in names else ""
        wb_rels = zf.read("xl/_rels/workbook.xml.rels").decode("utf-8") \
            if "xl/_rels/workbook.xml.rels" in names else ""
        parts = dict((n, zf.read(n)) for n in names)

    sst_items = re.findall(r"<si\b.*?</si>", sst_xml, re.S) if sst_xml else []
    changed, missed = [], []
    sheet_of = dict((v, k) for k, v in sheets.items())
    per_sheet = {}
    for sheet, ref, value in updates:
        sheet_name = sheet or (list(sheets)[0] if sheets else None)
        if sheet_name not in sheets:
            missed.append("%s!%s（没有这个工作表）" % (sheet_name, ref))
            continue
        per_sheet.setdefault(sheets[sheet_name], []).append((ref, value))

    for target, items in per_sheet.items():
        if target not in parts:
            continue
        xml = parts[target].decode("utf-8")
        for ref, value in items:
            pat = _cell_re(ref)
            m = pat.search(xml)
            if not m:
                missed.append("%s!%s（没这个单元格）" % (sheet_of.get(target, target), ref))
                continue
            attrs = _strip_attr(_cell_open_tag(m.group(0)), "t")
            sval = "" if value is None else str(value)
            if re.match(r"^-?\d+(\.\d+)?$", sval.strip()) and len(sval) < 16:
                new_cell = "<c%s><v>%s</v></c>" % (attrs, sval.strip())
            else:
                sst_items.append('<si><t xml:space="preserve">%s</t></si>' % _esc(sval))
                new_cell = '<c%s t="s"><v>%d</v></c>' % (attrs, len(sst_items) - 1)
            xml = xml[:m.start()] + new_cell + xml[m.end():]
            changed.append("%s!%s" % (sheet_of.get(target, target), ref))
        parts[target] = xml.encode("utf-8")

    if not changed:
        return "没有改到任何单元格：" + "；".join(missed or ["（参数不对）"])

    # sharedStrings 落盘 + 补齐类型/关系
    sst_text = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
                '<sst xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" '
                'count="%d" uniqueCount="%d">%s</sst>'
                % (len(sst_items), len(sst_items), "".join(sst_items)))
    parts["xl/sharedStrings.xml"] = sst_text.encode("utf-8")
    if "sharedStrings" not in ct_xml:
        ct_xml = ct_xml.replace("</Types>", SST_CT + "</Types>", 1)
        parts["[Content_Types].xml"] = ct_xml.encode("utf-8")
    if "sharedStrings" not in wb_rels:
        wb_rels = wb_rels.replace("</Relationships>", SST_REL + "</Relationships>", 1)
        parts["xl/_rels/workbook.xml.rels"] = wb_rels.encode("utf-8")

    with zipfile.ZipFile(path + ".tmp", "w", zipfile.ZIP_DEFLATED) as zo:
        for name in names:
            zo.writestr(name, parts.get(name, b""))
        if "xl/sharedStrings.xml" not in names:
            zo.writestr("xl/sharedStrings.xml", parts["xl/sharedStrings.xml"])
        if "[Content_Types].xml" not in names:
            zo.writestr("[Content_Types].xml", parts["[Content_Types].xml"])
        if "xl/_rels/workbook.xml.rels" not in names:
            zo.writestr("xl/_rels/workbook.xml.rels", parts["xl/_rels/workbook.xml.rels"])
    _safe_replace(path + ".tmp", path)

    msg = "已改 %d 处：%s" % (len(changed), "、".join(changed))
    if missed:
        msg += "\n没改到：" + "；".join(missed)
    return msg


# --------------------------------------------------------------------------- #
# Office/WPS 转换（本机装了才可用）
# --------------------------------------------------------------------------- #
PS_CONVERT = r"""
param([string]$src, [string]$dst, [string]$fmt)
$ErrorActionPreference = "Stop"
$map = @{
  'docx'=16; 'pdf'=17; 'txt'=2; 'rtf'=6; 'html'=8;
}
$ext = [System.IO.Path]::GetExtension($src).ToLower()
try {
  if (@('.doc','.docx','.rtf','.txt') -contains $ext) {
    $app = New-Object -ComObject Word.Application
    $app.Visible = $false
    $doc = $app.Documents.Open($src, $false, $true)
    $code = $map[$fmt]
    if (-not $code) { $code = 16 }
    $doc.SaveAs([ref]$dst, [ref]$code)
    $doc.Close($false)
    $app.Quit()
  } elseif (@('.xls','.xlsx','.csv') -contains $ext) {
    $app = New-Object -ComObject Excel.Application
    $app.Visible = $false
    $app.DisplayAlerts = $false
    $wb = $app.Workbooks.Open($src, 0, $true)
    if ($fmt -eq 'csv') { $wb.SaveAs($dst, 6) }
    elseif ($fmt -eq 'pdf') { $wb.ExportAsFixedFormat(0, $dst) }
    else { $wb.SaveAs($dst, 51) }
    $wb.Close($false)
    $app.Quit()
  } elseif (@('.ppt','.pptx') -contains $ext) {
    $app = New-Object -ComObject PowerPoint.Application
    $pres = $app.Presentations.Open($src, $true, $false, $false)
    if ($fmt -eq 'pdf') { $pres.SaveAs($dst, 32) }
    else { $pres.SaveAs($dst, 24) }
    $pres.Close()
    $app.Quit()
  } else {
    throw "不认得的扩展名: $ext"
  }
  Write-Output "OK"
} catch {
  Write-Output ("ERR:" + $_.Exception.Message)
}
"""


def office_convert(src, to, out=None):
    """借本机 Office/WPS 的 COM 转格式；没装就明确告诉他。"""
    _need(src)
    to = str(to or "").lower().lstrip(".")
    if to not in ("docx", "pdf", "txt", "rtf", "html", "xlsx", "csv", "pptx"):
        raise ValueError("不支持的转换目标：%s" % to)
    out = out or (os.path.splitext(src)[0] + "." + to)
    if os.path.abspath(out) == os.path.abspath(src):
        out = os.path.splitext(src)[0] + "-转换." + to
    import tempfile
    fd, ps = tempfile.mkstemp(suffix=".ps1", prefix="ember-conv-")
    with os.fdopen(fd, "w", encoding="utf-8-sig") as fh:
        fh.write(PS_CONVERT)
    cmd = ["powershell", "-NoProfile", "-NonInteractive", "-ExecutionPolicy", "Bypass",
           "-File", ps, "-src", os.path.abspath(src),
           "-dst", os.path.abspath(out), "-fmt", to]
    try:
        proc = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                              timeout=180)
    except FileNotFoundError:
        raise ValueError("这台机器没有 powershell，转换不可用")
    except subprocess.TimeoutExpired:
        raise ValueError("转换超时（180 秒），文件可能太大或 Office 卡住了")
    finally:
        try:
            os.remove(ps)
        except OSError:
            pass
    txt = (proc.stdout or b"").decode("utf-8", "replace").strip()
    if "OK" in txt and os.path.exists(out):
        return "已转换：%s -> %s（%s）" % (os.path.basename(src), out, _fmt_size(os.path.getsize(out)))
    raise ValueError("转换失败（这台机器可能没装 Office/WPS）：%s"
                     % (txt.splitlines()[-1] if txt else "无输出"))

# --------------------------------------------------------------------------- #
# 命令行入口：给 agent 用 run_cmd 调（不额外占一个工具位）
#     python doctools.py read   报告.docx
#     python doctools.py read   手册.pdf 1 5          # 只读第 1-5 页
#     python doctools.py write  out.docx 内容文件.md   # 从文件读内容（- 表示 stdin）
#     python doctools.py replace 模板.docx 旧的 新的 [输出.docx]
#     python doctools.py setcell 表.xlsx 工作表或- B2 新值
#     python doctools.py convert 老文件.doc docx [输出.docx]
# --------------------------------------------------------------------------- #
USAGE = __doc__.split("能干什么")[0].strip() + """

用法：
  doctools.py read    <文件> [起始页 结束页]
  doctools.py write   <文件.docx|.xlsx> <内容文件|->
  doctools.py replace <文件.docx> <旧文字> <新文字> [另存路径]
  doctools.py setcell <文件.xlsx> <工作表名|-> <单元格> <新值>
  doctools.py convert <文件> <目标格式> [输出路径]
  doctools.py fill    <模板.docx> 键=值 [键=值 ...] [-o 输出.docx]
     （只在文字上原位替换：页眉页脚图片样式全部保留，改完还会自检其它部件没变）
"""


def _main(argv):
    if not argv or argv[0] in ("-h", "--help"):
        print(USAGE)
        return 0
    cmd = argv[0].lower()
    try:
        if cmd == "read":
            if len(argv) < 2:
                raise ValueError("用法：read <文件> [起始页 结束页]")
            pages = None
            if len(argv) >= 4:
                pages = (int(argv[2]), int(argv[3]))
            print(doc_read(argv[1], pages=pages))
            return 0
        if cmd == "write":
            if len(argv) < 3:
                raise ValueError("用法：write <文件> <内容文件|->")
            if argv[2] == "-":
                content = sys.stdin.read()
            else:
                with open(argv[2], "r", encoding="utf-8", errors="replace") as fh:
                    content = fh.read()
            print(doc_write(argv[1], content))
            return 0
        if cmd == "replace":
            if len(argv) < 4:
                raise ValueError("用法：replace <文件.docx> <旧> <新> [另存路径]")
            out = argv[4] if len(argv) >= 5 else None
            print(docx_replace(argv[1], [(argv[2], argv[3])], out=out))
            return 0
        if cmd == "setcell":
            if len(argv) < 5:
                raise ValueError("用法：setcell <文件.xlsx> <工作表名|-> <单元格> <新值>")
            sheet = None if argv[2] in ("-", "") else argv[2]
            print(xlsx_set(argv[1], [(sheet, argv[3], argv[4])]))
            return 0
        if cmd == "fill":
            if len(argv) < 3:
                raise ValueError("用法：fill <模板.docx> 键=值 [键=值 ...] [-o 输出]")
            mapping, out = {}, None
            i = 2
            while i < len(argv):
                a = argv[i]
                if a in ("-o", "--out"):
                    i += 1
                    out = argv[i] if i < len(argv) else None
                elif "=" in a:
                    k, v = a.split("=", 1)
                    mapping[k] = v
                i += 1
            print(docx_fill(argv[1], mapping=mapping, out=out))
            return 0
        if cmd == "convert":
            if len(argv) < 3:
                raise ValueError("用法：convert <文件> <目标格式> [输出路径]")
            out = argv[3] if len(argv) >= 4 else None
            print(office_convert(argv[1], argv[2], out=out))
            return 0
        print("不认识的命令：%s\n" % cmd + USAGE)
        return 2
    except Exception as exc:                                  # noqa: BLE001
        print("出错：%s" % exc)
        return 1


if __name__ == "__main__":
    import sys
    sys.exit(_main(sys.argv[1:]))
