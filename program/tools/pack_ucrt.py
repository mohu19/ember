# -*- coding: utf-8 -*-
"""把本机的 UCRT 运行库拷成离线补丁：ucrt\\x64\\ 和 ucrt\\x86\\

背景：Windows 7 裸机没有"通用 C 运行库"，包里的 python.exe 会起不来。
      最省事的修法是装 vc_redist，但学校机器常常没网。
      这个脚本在一台"已经装好 UCRT"的 Windows 上跑一遍，把需要的那几十个
      DLL 拷进包里；拿到老机器上，run.cmd 会在 python 起不来时自动装进 py\\。

用法（在有 UCRT 的机器上）：
    py\\python.exe tools\\pack_ucrt.py

说明：
    * Win10/11 把 api-ms-win-crt-*.dll 做成了 API set，磁盘上没有实体文件，
      所以这个脚本通常要在 Win7 / Win8.1 上跑（装了 KB2999226 即可）。
    * 只复制，不改系统、不需要管理员权限。
"""
import os
import shutil
import sys

HERE = os.path.dirname(os.path.abspath(__file__))      # program/tools
# v2.3.1：项目根是"program"的上一层；以前写成 dirname(HERE)，补丁写到了 program\ucrt，永远修不好 Win7
ROOT = os.path.dirname(os.path.dirname(HERE))
SYSTEM_ROOT = os.environ.get("SystemRoot", r"C:\Windows")


def is_64bit_os():
    return bool(os.environ.get("PROCESSOR_ARCHITEW6432")) or \
        os.environ.get("PROCESSOR_ARCHITECTURE", "").upper() == "AMD64"


def candidate_dirs(arch):
    """返回该架构下 UCRT 可能所在的系统目录（按优先级）。"""
    out = []
    if arch == "x64":
        out.append(os.path.join(SYSTEM_ROOT, "System32"))
        out.append(os.path.join(SYSTEM_ROOT, "Sysnative"))   # 32 位进程看 64 位系统目录
    else:
        out.append(os.path.join(SYSTEM_ROOT, "SysWOW64"))
        out.append(os.path.join(SYSTEM_ROOT, "System32"))
    return [d for d in out if os.path.isdir(d)]


def collect(arch):
    """收集 ucrtbase.dll + api-ms-win-crt-*.dll，返回文件列表。"""
    files = []
    for d in candidate_dirs(arch):
        names = []
        base = os.path.join(d, "ucrtbase.dll")
        if os.path.isfile(base):
            names.append("ucrtbase.dll")
        try:
            names += [n for n in os.listdir(d)
                      if n.lower().startswith("api-ms-win-crt-") and n.lower().endswith(".dll")]
        except OSError:
            continue
        found = [os.path.join(d, n) for n in names]
        # 必须凑齐一族 api-ms-win-crt-*，否则光有 ucrtbase.dll 也不够
        api = [f for f in found if os.path.basename(f).lower().startswith("api-ms-win-crt-")]
        if len(api) >= 5:
            files = found
            break
    return files


def main():
    if os.name != "nt":
        print("这个脚本只能在 Windows 上跑。")
        return 2
    print("系统目录: %s   64 位系统: %s" % (SYSTEM_ROOT, is_64bit_os()))
    total = 0
    for arch in ("x64", "x86"):
        files = collect(arch)
        if not files:
            print("  %-4s 跳过：这台机器上找不到 api-ms-win-crt-*.dll" % arch)
            print("       （Win10/11 把它们做成了 API set；请在装了 KB2999226 的 Win7/8.1 上跑）")
            continue
        dest = os.path.join(ROOT, "ucrt", arch)
        os.makedirs(dest, exist_ok=True)
        size = 0
        for src in files:
            shutil.copy2(src, os.path.join(dest, os.path.basename(src)))
            size += os.path.getsize(src)
        total += size
        print("  %-4s 复制 %d 个文件，%.1f MB -> %s"
              % (arch, len(files), size / 1048576.0, dest))
    if not total:
        print("\n没有收集到任何文件。可以改用官方 vc_redist，见 README-FIRST.txt。")
        return 1

    readme = os.path.join(ROOT, "ucrt", "README.txt")
    with open(readme, "w", encoding="utf-8", newline="\r\n") as fh:
        fh.write(
            "这个目录是 Windows 7 用的离线 UCRT 补丁（由 tools\\pack_ucrt.py 生成）。\n\n"
            "怎么用：直接双击 run.cmd。如果包里的 python.exe 起不来（缺 UCRT），\n"
            "run.cmd 会自动把这里的 DLL 复制到 py\\ 和 py32\\ 旁边，然后再启动一次。\n\n"
            "不需要了可以整个删掉，不影响其他功能。\n")
    print("\n完成：共 %.1f MB。现在可以把整个文件夹拷到 Win7 机器上直接用。" % (total / 1048576.0))
    return 0


if __name__ == "__main__":
    sys.exit(main())
