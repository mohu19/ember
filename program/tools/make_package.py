# -*- coding: utf-8 -*-
"""打「干净部署包」zip（给 ember 拷到别的机器用）

包里有什么：program\（agent.py / webui.html / prompt.txt / tools\）/
            config.txt(api_key 清空) / 各个启动 .cmd /
            README-FIRST.txt / py\\ 运行时 / tools\\ 自检脚本 / 空 workspace\\
包外排除什么：key.txt（有钥匙）、你本机 config.txt 里的 api_key、
            sessions\\（聊天记录）、versions\\（旧版备份）、__pycache__、
            workspace\\ 里的测试文件

用法:
    py\\python.exe tools\\make_package.py                 # 默认打到项目同级目录（本文件夹的上一层）
    py\\python.exe tools\\make_package.py D:\\别的路径\\x.zip
打完会自动扫一遍 zip 里有没有 sk- 泄漏，并解压到临时目录跑一次冒烟测试。
"""
import hashlib
import os
import re
import shutil
import subprocess
import sys
import threading
import tempfile
import time
import zipfile

HERE = os.path.dirname(os.path.abspath(__file__))          # program/tools


def _find_root(start):
    cur = start
    for _ in range(4):
        if os.path.exists(os.path.join(cur, "py", "python.exe")):
            return cur
        cur = os.path.dirname(cur)
    return os.path.dirname(os.path.dirname(start))


ROOT = _find_root(HERE)
VERSION = "2.4.0"
ROOT_IN_ZIP = "ember-v%s" % VERSION

FILES = ["program/agent.py", "program/doctools.py", "program/webui.html", "program/prompt.txt",
         "program/find_python.cmd",
         "run.cmd", "run.bat", "launch.vbs", "web.cmd", "start.cmd",
         "resume.cmd", "diagnose.cmd", "README-FIRST.txt"]
DIRS = ["program/tools", "py", "py32", "ucrt"]   # py=64 位运行时，py32=32 位运行时（老机器用）
SKIP_DIR_NAMES = {"__pycache__", ".git", "sessions", "versions", "workspace"}
SKIP_FILE_SUFFIX = (".pyc", ".pyo")


def read_tolerant(path):
    raw = open(path, "rb").read()
    for enc in ("utf-8-sig", "utf-8", "gbk"):
        try:
            return raw.decode(enc)
        except UnicodeDecodeError:
            continue
    return raw.decode("utf-8", "replace")


def clean_config_bytes():
    """把 api_key 清空后的 config.txt 内容（只进包，不动本地文件）。"""
    text = read_tolerant(os.path.join(ROOT, "config.txt"))
    out = []
    for line in text.splitlines():
        s = line.strip().lower()
        if s.startswith("api_key") and ("=" in line or ":" in line):
            out.append("api_key =")
        else:
            out.append(line)
    return ("\r\n".join(out) + "\r\n").encode("utf-8")


def build(out_path):
    if os.path.exists(out_path):
        os.remove(out_path)
    manifest = []
    missing = []
    with zipfile.ZipFile(out_path, "w", zipfile.ZIP_DEFLATED, compresslevel=9) as zf:
        for name in FILES:
            src = os.path.join(ROOT, name)
            if not os.path.exists(src):
                missing.append(name)
                print("  [缺失] %s" % name)
                continue
            zf.write(src, ROOT_IN_ZIP + "/" + name)
            manifest.append((name, os.path.getsize(src)))
        # config.txt：api_key 清空后入包
        data = clean_config_bytes()
        zf.writestr(ROOT_IN_ZIP + "/config.txt", data)
        manifest.append(("config.txt（api_key 已清空）", len(data)))
        for d in DIRS:
            src_dir = os.path.join(ROOT, d)
            if not os.path.isdir(src_dir):
                continue
            for dirpath, dirnames, filenames in os.walk(src_dir):
                dirnames[:] = [x for x in dirnames if x not in SKIP_DIR_NAMES]
                for fn in filenames:
                    if fn.endswith(SKIP_FILE_SUFFIX):
                        continue
                    full = os.path.join(dirpath, fn)
                    rel = os.path.relpath(full, ROOT).replace("\\", "/")
                    zf.write(full, ROOT_IN_ZIP + "/" + rel)
                    manifest.append((rel, os.path.getsize(full)))
        # 空的 workspace 目录（解压出来就有）
        zf.writestr(ROOT_IN_ZIP + "/workspace/", "")
    return manifest, missing


def real_keys():
    """把本机真实存在的 key 读出来（只用来做泄漏比对，不打印）。"""
    keys = []
    cfg = os.path.join(ROOT, "config.txt")
    if os.path.exists(cfg):
        for line in read_tolerant(cfg).splitlines():
            s = line.strip()
            if s.lower().startswith("api_key") and ("=" in s or ":" in s):
                v = re.split(r"[=:]", s, 1)[1].strip().strip('"').strip("'")
                if v:
                    keys.append(v)
    kf = os.path.join(ROOT, "key.txt")
    if os.path.exists(kf):
        v = read_tolerant(kf).split("=", 1)[-1].strip().strip('"').strip("'")
        if v:
            keys.append(v)
    return [k for k in keys if k]


TEXTY = (".py", ".txt", ".cmd", ".bat", ".md", ".json", ".yaml", ".yml", ".ini",
         ".cfg", ".html", ".vbs", ".ps1", ".xml", ".rels")
KEY_SHAPE = re.compile(rb"sk-[A-Za-z0-9]{24,}")


def verify(out_path, py_exe):
    ok = True
    keys = real_keys()
    print("\n---- 1) 查有没有把 key 打进去 ----")
    print("   （本机找到 %d 个真实 key 值，逐个在包里搜；另外再按 sk- 形状扫文本文件）"
          % len(keys))
    shape_hits = []
    with zipfile.ZipFile(out_path) as zf:
        for info in zf.infolist():
            if info.is_dir():
                continue
            blob = zf.read(info.filename)
            for k in keys:                                  # 决定性检查：真值比对
                if k.encode("utf-8") in blob or k.encode("utf-16-le") in blob:
                    ok = False
                    print("  [FAIL] %s 里出现了真实 key 值！" % info.filename)
            if info.filename.lower().endswith(TEXTY):
                for m in KEY_SHAPE.finditer(blob):
                    shape_hits.append((info.filename, m.group(0)[:12].decode() + "..."))
        if not shape_hits:
            print("  [PASS] 文本文件里没有 sk-开头的长密钥形状")
        else:
            # 帮助文本里的 sk-xxxxxxxx 之类是字数不够的，不会命中；命中就要看
            ok = False
            print("  [FAIL] 疑似密钥形状:")
            for name, sample in shape_hits:
                print("        %s: %s" % (name, sample))
        cfg = zf.read(ROOT_IN_ZIP + "/config.txt").decode("utf-8")
        line = [l for l in cfg.splitlines() if l.strip().lower().startswith("api_key")][0]
        print("  [%s] 包里的 config.txt: %r" % ("PASS" if line.strip() == "api_key =" else "FAIL", line))
        ok = ok and line.strip() == "api_key ="
        # 机器档案也不能进包：里面有用户名、桌面文件夹清单、机器指纹
        names = zf.namelist()
        leaked = [n for n in names if "env-profile" in n.lower()]
        print("  [%s] 不包含本机环境档案 env-profile.txt（含用户名/桌面清单）"
              % ("PASS" if not leaked else "FAIL"))
        ok = ok and not leaked
        # v1.6：备用入口必须一起进包，否则老机器打不开就真没辙了
        want = ("program/agent.py", "program/doctools.py", "program/prompt.txt",
                "program/webui.html", "program/tools/selftest.py", "program/find_python.cmd",
                "config.txt", "README-FIRST.txt", "run.cmd", "run.bat", "launch.vbs",
                "web.cmd", "start.cmd", "resume.cmd", "diagnose.cmd",
                "py/python.exe", "py32/python.exe",
                "ucrt/x64/ucrtbase.dll", "ucrt/x86/ucrtbase.dll")
        missing = [n for n in want if (ROOT_IN_ZIP + "/" + n) not in names]
        print("  [%s] 入口文件齐全（%s）" % ("PASS" if not missing else "FAIL",
                                          "、".join(want)))
        ok = ok and not missing

    print("\n---- 2) 解压到临时目录跑一次冒烟测试 ----")
    tmp = tempfile.mkdtemp(prefix="ember-pkgtest-")
    try:
        with zipfile.ZipFile(out_path) as zf:
            zf.extractall(tmp)
        root = os.path.join(tmp, ROOT_IN_ZIP)
        env = dict(os.environ)
        env.pop("DEEPSEEK_API_KEY", None)
        env["PYTHONIOENCODING"] = "utf-8"
        exe = os.path.join(root, "py", os.path.basename(py_exe))

        def run(args):
            p = subprocess.Popen([exe, os.path.join(root, "program", "agent.py")] + args, cwd=root,
                                 stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
                                 stderr=subprocess.STDOUT, env=env)
            out = p.communicate(timeout=60)[0].decode("utf-8", "replace")
            return p.returncode, out

        rc, out = run(["--check-key"])
        print("  [%s] 解压后 --check-key 返回 1（= 没有 key，首次会问你）"
              % ("PASS" if rc == 1 else "FAIL"))
        ok = ok and rc == 1
        rc, out = run(["--show-config"])
        good = rc == 0 and "api_key" in out and "(空)" in out
        print("  [%s] 解压后 --show-config 能跑，api_key 为空" % ("PASS" if good else "FAIL"))
        ok = ok and good
        rc, out = run(["-p", "hi"])
        good = rc == 1 and "没有找到 API Key" in out
        print("  [%s] 没 key 时给的是友好提示而不是报错" % ("PASS" if good else "FAIL"))
        ok = ok and good

        # v2.3.1：32 位运行时也要能起（以前从没验过）
        exe32 = os.path.join(root, "py32", "python.exe")
        if os.path.exists(exe32):
            p32 = subprocess.run([exe32, "-c", "pass"], cwd=root, timeout=120,
                                 stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
            good32 = p32.returncode == 0
            print("  [%s] 解压后 py32\\python.exe 能启动" % ("PASS" if good32 else "FAIL"))
            ok = ok and good32

        # doctools 能导入（_pth 隔离模式下最容易漏）
        p_dt = subprocess.run([exe, "-c", "import sys; sys.path.insert(0, 'program'); "
                               "import doctools; print(doctools.__name__)"],
                              cwd=root, timeout=120, stdout=subprocess.PIPE,
                              stderr=subprocess.STDOUT)
        good_dt = p_dt.returncode == 0
        print("  [%s] 解压后 doctools 能导入" % ("PASS" if good_dt else "FAIL"))
        ok = ok and good_dt

        # 真跑一次 run.cmd：启动器不能改坏任何文件（P0-1 的回归）
        launchers = ("run.cmd", "run.bat", "launch.vbs", "web.cmd", "start.cmd",
                     "resume.cmd", "diagnose.cmd", "config.txt", "README-FIRST.txt")
        before = {}
        for n in launchers:
            fp = os.path.join(root, n)
            if os.path.exists(fp):
                before[n] = hashlib.sha256(open(fp, "rb").read()).hexdigest()
        try:
            subprocess.run(["cmd", "/c", "echo /exit | run.cmd"], cwd=root, timeout=180,
                           stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                           env=dict(env, PYTHONIOENCODING="utf-8"))
            bad = [n for n, h in before.items()
                   if not os.path.exists(os.path.join(root, n))
                   or hashlib.sha256(open(os.path.join(root, n), "rb").read()).hexdigest() != h]
            print("  [%s] 跑一次 run.cmd 后启动文件全部没变%s"
                  % ("PASS" if not bad else "FAIL", "" if not bad else "：" + "、".join(bad)))
            ok = ok and not bad
            # v2.4：README 里提到的每个路径都必须在包里存在（防止文档漂移）
            rd = os.path.join(root, "README-FIRST.txt")
            rd_txt = open(rd, encoding="utf-8-sig", errors="replace").read()
            tokens = set(re.findall(r"(?:program|py32?|ucrt)\\[\w\\.]+|[\w-]+\.cmd", rd_txt))
            missing_doc = [t for t in sorted(tokens)
                           if not os.path.exists(os.path.join(root, t.replace("\\", os.sep)))]
            print("  [%s] README 里提到的路径都存在（%d 个）%s"
                  % ("PASS" if not missing_doc else "FAIL", len(tokens),
                     "" if not missing_doc else " 缺：" + "、".join(missing_doc)))
            ok = ok and not missing_doc

            # v2.4：web.cmd 冒烟 —— 能起服务、能打出访问地址，然后杀掉整棵进程树
            web_proc = None
            try:
                web_proc = subprocess.Popen(
                    ["cmd", "/c", "web.cmd", "8899"], cwd=root,
                    stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    creationflags=getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0))
                lines = []

                def _reader(proc, box):
                    try:
                        for ln in proc.stdout:
                            box.append(ln)
                            if b"127.0.0.1:" in ln and b"t=" in ln:
                                return
                    except Exception:
                        pass

                th = threading.Thread(target=_reader, args=(web_proc, lines), daemon=True)
                th.start()
                th.join(30)
                got_url = any(b"127.0.0.1:" in ln and b"t=" in ln for ln in lines)
                print("  [%s] web.cmd 能启动并打出访问地址" % ("PASS" if got_url else "FAIL"))
                ok = ok and got_url
            except Exception as exc:                  # noqa: BLE001
                print("  [FAIL] web.cmd 冒烟失败：%s" % exc)
                ok = False
            finally:
                if web_proc is not None:
                    subprocess.run(["taskkill", "/F", "/T", "/PID", str(web_proc.pid)],
                                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            # diagnose.cmd 必须真的跑到底（以前块里 echo 1) 会提前闭合，整段被跳过）
            dg = subprocess.run(["cmd", "/c", "diagnose.cmd < nul"], cwd=root, timeout=180,
                                stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
            dg_out = dg.stdout.decode("gbk", "replace")
            good_dg = ("[1]" in dg_out) and ("[3]" in dg_out)
            print("  [%s] diagnose.cmd 能跑完全程（[1] 和 [3] 都打印了）"
                  % ("PASS" if good_dg else "FAIL"))
            ok = ok and good_dg

            # webui.html 的 JS 语法必须过（2.3.2 就是这里坏了：回车变换行，整页没反应）
            node_exe = shutil.which("node")
            if node_exe:
                web = os.path.join(root, "program", "webui.html")
                html = open(web, encoding="utf-8").read()
                mm = re.search(r"<script>(.*?)</script>", html, re.S)
                js_file = os.path.join(tmp, "webui-check.js")
                with open(js_file, "w", encoding="utf-8") as fh:
                    fh.write(mm.group(1) if mm else "")
                nr = subprocess.run([node_exe, "--check", js_file],
                                    stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                    timeout=90)
                good_js = nr.returncode == 0
                print("  [%s] webui.html 的 JS 语法检查" % ("PASS" if good_js else "FAIL"))
                if not good_js:
                    print("        " + nr.stdout.decode("utf-8", "replace").splitlines()[0])
                ok = ok and good_js
            else:
                print("  [跳过] 本机没有 node，没法做 webui.html 语法检查")
        except Exception as exc:                      # noqa: BLE001
            print("  [FAIL] run.cmd 冒烟测试跑不起来：%s" % exc)
            ok = False
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    return ok


def main():
    # 默认放在项目同级目录（也就是 ember-vX.Y.Z\ 的上一层），不再写死某个人的桌面路径
    default = os.path.join(os.path.dirname(ROOT), "ember-v%s-部署包.zip" % VERSION)
    out_path = sys.argv[1] if len(sys.argv) > 1 else default
    out_dir = os.path.dirname(os.path.abspath(out_path))
    if not os.path.isdir(out_dir):
        os.makedirs(out_dir)

    print("打包: %s" % out_path)
    manifest, missing = build(out_path)
    if missing:
        print("\n[FAIL] 少了 %d 个必需文件：%s" % (len(missing), "、".join(missing)))
    print("\n---- 包内清单 ----")
    for name, size in sorted(manifest):
        print("  %8.1f KB  %s" % (size / 1024.0, name))
    total_raw = sum(s for _, s in manifest)
    print("  %d 个文件，原始 %0.1f MB，压缩后 %0.1f MB"
          % (len(manifest), total_raw / 1048576.0, os.path.getsize(out_path) / 1048576.0))

    py_exe = os.path.join(ROOT, "py", "python.exe")
    ok = verify(out_path, py_exe) and not missing
    print("\n==================== 结论 ====================")
    print("%s  交付物: %s" % ("[PASS] 可以直接拷到别的机器用" if ok else "[FAIL] 有问题，别发出去",
                            out_path))
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
