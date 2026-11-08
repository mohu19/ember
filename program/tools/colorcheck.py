# -*- coding: utf-8 -*-
"""ember 上色自检（要有 Windows 控制台才有意义）

Windows 上色有两条路：
  1) ANSI/VT 码               —— Win10 1511+ 支持
  2) SetConsoleTextAttribute  —— Win7 也能用（学校那种老机器走这条）

这个脚本会分配一个（藏起来的）控制台，走 2) 那条路把带色的字写进控制台缓冲区，
再用 ReadConsoleOutputAttribute 把每个字符的颜色属性读回来，逐项和预期比。
结果打在**启动它的那个终端**上（不是藏起来的那个），所以能直接看结论。

用法:  py\\python.exe tools\\colorcheck.py
"""
import ctypes
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)
import agent  # noqa: E402

REAL = sys.stdout                      # 启动它的终端（结论打这里）
k32 = ctypes.windll.kernel32
user32 = ctypes.windll.user32

if not k32.GetConsoleWindow():
    if not k32.AllocConsole():         # 被别的（不可见的）控制台占着时会失败
        k32.FreeConsole()
        k32.AllocConsole()
    user32.ShowWindow(k32.GetConsoleWindow(), 0)     # 立刻藏起来
if not k32.GetConsoleWindow():
    REAL.write("[FAIL] 拿不到控制台窗口，这个自检需要真控制台\n")
    sys.exit(1)

con = open("CONOUT$", "w", buffering=1)      # 用系统默认编码写控制台设备，中文才不会乱码
CONOUT = k32.CreateFileW(ctypes.c_wchar_p("CONOUT$"), 0xC0000000, 3, None, 3, 0, None)
RESULTS = []


def check(name, ok, detail=""):
    RESULTS.append((name, ok))
    REAL.write("   %s %s%s\n" % ("[PASS]" if ok else "[FAIL]", name,
                                 ("  <- " + detail) if detail else ""))
    REAL.flush()


def row_attrs(row, count=30):
    """读一整行每个字符的颜色属性。中文是全角，一个字符占两格，
    第二格带 COMMON_LVB_LEADING/TRAILING_BYTE（0x100/0x200）标记，
    所以比较时只看低 4 位（前景色）。"""
    n = ctypes.c_ulong()
    arr = (ctypes.c_ushort * count)()
    k32.ReadConsoleOutputAttribute(CONOUT, arr, count, agent.COORD(0, row),
                                   ctypes.byref(n))
    return [(arr[i] & 0x0F) for i in range(min(n.value, count))]


def cursor_row():
    info = agent.CONSOLE_SCREEN_BUFFER_INFO()
    k32.GetConsoleScreenBufferInfo(CONOUT, ctypes.byref(info))
    return info.dwCursorPosition.Y


def write_into_console(text, element=None):
    """按 agent 的方式写进控制台，返回写的那一行的行号。"""
    sys.stdout = con
    try:
        agent.STATUS.log(text, color=element)
    finally:
        sys.stdout = REAL
    return cursor_row() - 1            # 刚写的那一行（log 会补一个换行，光标在下一行）


REAL.write("控制台: 已分配并隐藏（窗口句柄 %s）\n" % k32.GetConsoleWindow())
REAL.write("\n---- 1) 探测上色通道 ----\n")
sys.stdout = con
agent.init_colors("win32")
sys.stdout = REAL
REAL.write("   COLOR_ON=%s，COLOR_VT=%s，COLOR_ORIG=%d，COLOR_HANDLE=%s\n"
           % (agent.COLOR_ON, agent.COLOR_VT, agent.COLOR_ORIG, agent.COLOR_HANDLE))
if not agent.COLOR_ON:
    REAL.write("[FAIL] 拿不到控制台句柄，Win7 那条路不通\n")
    sys.exit(1)

REAL.write("\n---- 2) 真写一行带色的字，再从缓冲区读回颜色属性 ----\n")
for element, label in (("tool", "工具/自动同意"), ("think", "思考"),
                       ("warn", "中断/警告"), ("error", "出错"),
                       ("dim", "提示/状态/分界线"), ("user", "你的输入")):
    want = agent._palette_of(element)[1]
    row = write_into_console("  色块测试 %s" % label, element)
    got = row_attrs(row, 12)
    ok = got.count(want) >= 4
    check("%s -> 属性 %3d（%s，调色板 %s）" % (label, want,
                                          "命中 %d 个字符" % got.count(want),
                                          agent.COLOR_TABLE.get(element)),
          ok, str(got))

REAL.write("\n---- 3) 写完有没有自动恢复原色 ----\n")
sys.stdout = con
agent.STATUS.log("  收尾这一行", color="none")
sys.stdout = REAL
info = agent.CONSOLE_SCREEN_BUFFER_INFO()
k32.GetConsoleScreenBufferInfo(CONOUT, ctypes.byref(info))
check("颜色用完已恢复默认（当前 0x%02X / 原 0x%02X）" % (info.wAttributes, agent.COLOR_ORIG),
      info.wAttributes == agent.COLOR_ORIG)

REAL.write("\n---- 4) 另一条路：ANSI(VT) 码能不能被这台机器的控制台解析 ----\n")
if agent.os.name == "nt":
    sys.stdout = con
    agent.init_colors("vt")            # 强制发 ANSI 码
    row = write_into_console("  VT 通道测试", "tool")
    sys.stdout = REAL
    got = row_attrs(row, 12)
    vt_ok = got.count(11) >= 4
    check("ANSI(\\x1b[96m) 被控制台解析成亮青", vt_ok, str(got))
    REAL.write("   说明：%s\n" % ("这台控制台认 ANSI（Win10 1511+ 才认）"
                              if vt_ok else
                              "这台控制台不认 ANSI（Win7/8 常见）—— 不影响用，"
                              "auto 模式会自动走控制台属性那条路"))
else:
    check("非 Windows，跳过", True)

bad = [n for n, o in RESULTS if not o]
REAL.write("\n==================== 结论 ====================\n")
REAL.write("共 %d 项，通过 %d 项，失败 %d 项\n" % (len(RESULTS), len(RESULTS) - len(bad), len(bad)))
for n in bad:
    REAL.write("  失败: %s\n" % n)
REAL.write("这台机器跑 ember 时：颜色 %s\n" % ("可用（走 SetConsoleTextAttribute）" if not bad
                                           else "有问题，建议 config.txt 里 color = off"))
REAL.flush()
sys.exit(1 if bad else 0)
