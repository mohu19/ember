#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""ember v1.8 —— 极简自研 agent（单文件，仅标准库，兼容 Python 3.8 / Windows 7）

用法:
    python agent.py                     交互模式
    python agent.py -p "看一下这个文件"   一次性提问
    python agent.py -c                  继续最近一次会话
    python agent.py --list-sessions     列出历史会话（带编号）
    python agent.py --resume 2          继续列表里第 2 个会话（等价于双击 resume.cmd）
    python agent.py --yolo / --safe     本次强制自动同意 / 强制逐条确认
    python agent.py --show-config       看当前生效的配置、提示词来源与路径
    python agent.py --version           看版本号
    python agent.py --check-key         有 key 返回 0，没有返回 1（脚本用）
    python agent.py --set-key sk-xxx    把 key 写进 config.txt
    python agent.py --config 别的.txt    用另一份配置文件（多份配置/多环境用）
    python agent.py --api-base http://x  临时换接口地址
    python agent.py --key-script f.txt   测试钩子：按脚本回放按键（每轮开始时计时）
    python agent.py --no-stop-keys      关掉运行中的按键监听（只留 Ctrl+C）

运行中想停下：
    敲 /stop 回车，或按 ESC，或按 Ctrl+C —— 三种都行。会立刻中断本次回答/工具调用，
    正在跑的命令会被连同子进程一起杀掉；运行中敲的其它内容会记下来，本轮结束后自动发出。

超时截断（都能在 config.txt 里改）:
    api_timeout   模型多久没吐数据算超时（默认 120 秒）
    turn_timeout  一次提问的总时长上限（默认 1800 秒 = 30 分钟，0 = 不限）
    cmd_timeout   run_cmd 默认超时（默认 120 秒）
    cmd_timeout_max  agent 能要求的最长超时（默认 600 秒）
    status_line   运行中的实时状态行：auto（真终端才显示）/ on / off
    separator     每轮回答后的分界线：line / ascii / blank / none
    color         上色：auto（Win10+ 走 ANSI，Win7 走控制台属性接口）/ on / vt / win32 / off
    color_tool / color_think / color_warn / color_error / color_dim / color_user
                  各部分用什么颜色（值见 config.txt 里的调色板列表）

配置开关都在 config.txt（记事本改）。系统提示词在 prompt.txt（记事本改，可多行，
以 # 或 // 开头的行会被忽略）。程序还会在末尾自动追加一段"运行环境事实"。

v2.3.3（修网页终端整体失灵）:
    * webui.html 里给老 IE 的提示串写坏了（单引号没转义），整段 JS 语法错误，
      结果是所有事件都没绑上：回车变成换行、按钮没反应
    * 打包冒烟新增 webui.html 的 JS 语法检查（node --check），这类问题以后发不出去
v2.3.2（PDF 解析补强）:
    * 支持 /ObjStm 对象流、间接 /Resources 与 /Font、/Pages 页树
    * 逐字定位的 PDF 用自适应间距，不再把单词拆成单字
    * 抠不出文字时明确说「提取失败/没有文字层」，不再把乱码当正文
    * 新增 2 条 PDF 用例（之前一条都没有）
v2.3.1（按审计报告修的一轮）:
    * 修 replace 在「新值包含旧值」时复制 200 份（会写坏文档还说成功）
    * 修 run.cmd 里 `->` 被当成重定向、把 diagnose.cmd 清空
    * 危险命令识别先剥 cmd/start/powershell 外壳，`cmd /c format C:` 不再绕过
    * xlsx 写字符串补齐 Content_Types/rels；设值前删 <f>；不再整体重放工作表 XML
    * PDF 提不出文字时明确报错，不再把乱码当正文；长文档导出成 .txt 并提示分页
    * UCRT 按位数拷贝（不再往 py32 塞 x64 dll）；pack_ucrt 的 ROOT 修对
    * 网页：新建会话不再 404；停止状态不再被覆盖成「完成」；改名不再重放历史；
      双开自动换端口；IE8 给明确提示
    * --version 等纯本地命令不再联网/写档案；写 config 失败给人话；key 输入不回显
    * 自检：cp936 控制台不再崩；默认关掉环境探测；新增 12 项针对本报告的回归
v2.3.0（文档工具，不新增工具位）:\n    * read_file 直接读 .docx/.xlsx/.pptx/.pdf（纯标准库解析，扫描件 PDF 只有文字层能读）\n    * write_file 写 .docx/.xlsx 会生成真正的 Office 文档，内容用 Markdown 写\n    * 改已有 Word/Excel、转老格式：program\\doctools.py（run_cmd 调用）\nv2.2.0（目录整理 + 体检 + 启动台）:
    * 程序收进 program\ 子目录：根目录只留 README / config.txt / 各个启动项，
      聊天记录、工作区、运行时仍在根目录；单文件拷走也能跑（自动识别根目录）
    * 新增 --doctor 体检：配置 -> DNS -> 代理 -> TLS/证书/时间 -> 鉴权 -> 对话 -> 流式 -> 本地文件，
      每一步都指出「哪坏了、怎么修」
    * 新增 start.cmd 启动台：体检 / 网页终端 / 命令行（新窗口或本窗口）/ 看配置 / 选历史
v2.1.0（多会话并行）:
    * 运行模型从「一次只跑一个」改成「每个会话各自推进」：会话各有历史、事件队列、
      中断标志；A 在跑的时候可以切到 B、新建 C、给 C 发消息
    * 侧边栏状态点：黄点=正在跑，绿点=跑完了但你没看（点开即消失），红点=等你确认
    * 事件按会话分开轮询，两个会话的输出不会串台；/stop 只停指定会话
    * 状态行（工具调用、压缩、提醒）改为进会话日志，不再刷控制台
v2.0.4（测试隔离）:
    * 自检不再往真实的 sessions\ 里写测试会话：用 EMBER_SESSIONS 环境变量指到临时目录，
      run_agent 子进程一起隔离，跑完自动删除（以前跑一次自检，侧边栏就多十几个假会话）
v2.0.3（自动标题 + 侧边栏细节）:
    * 会话自动起标题：第一轮对话后让模型给一个 <=12 字的标题，存在 <会话>.title；
      改名会覆盖它；老会话第一次被打开时补生成
    * 侧边栏显示标题（不再是首句），副行保留首句；两个操作图标放大到 22px 并常显淡色
v2.0.2（网页端打磨）:
    * 会话可删除 / 重命名；列表不再把 *.archive.jsonl 当会话，按 mtime+size 缓存，
      只扫行首不做全量 JSON 解析（会话多了不再拖慢，网页每 2 秒拉列表也不重复扫盘）
    * 命令输出边跑边推（0.25 秒一份增量），长任务能看见进度
    * 输入框 Enter 发送、Shift+Enter 换行；输入法选词时按回车不会误发
    * 默认简洁模式（隐藏"谁说的"和条目上的复制），回答里的代码块单独带"复制代码"
    * 页面右上角显示界面构建时间，一眼能看出是不是旧页面
    * 少一条噪声：只有"第一人称说自己被限制"才提示，正常句子里的"无法访问"不再误报
v2.0（网页终端，可选）:
    * 新增 --web：内置 http.server（仅标准库）在 127.0.0.1 起一个网页终端，
      webui.html 是前端。左边历史会话、右边看每一步工具调用，支持复制、多行粘贴、
      按钮停止、弹窗确认；和 cmd 共用同一份 sessions\。
    * 事件用轮询（300ms），不依赖 WebSocket，老浏览器也能用；地址带一次性口令防跨站调用。
v1.9.1（捉虫 + 老系统适配）:
    * 压缩期间按 Ctrl+C 会把整个程序打死（stop.begin() 原来在压缩之后）
    * 单轮工具截断说"原文在归档"但其实没归档 —— 现在先归档再截断
    * 写 .bat/.cmd/.vbs/.reg 用 UTF-8，cmd/regedit 按 ANSI 读 → 中文乱码；改成 GBK
    * .txt/.log/.ini/.cfg/.csv/.inf/.url 同样按 GBK 写（Win7 记事本、Excel 都不乱码）；
      GBK 表示不了的字符退回 UTF-8 带 BOM
    * 命令输出解码：chcp 65001 的 UTF-8 现在能正确识别（GBK 误读成 UTF-8 的坑也保留防护）
    * 上下文预算默认 60000 -> 200000（窗口 1M 级，只占两成，尽量少压缩少失忆）
    * del *.* / del *（清当前目录）没被危险确认拦住
    * /history all 没有上限，几百条会刷屏；顺带 start_line 超范围时给说明
    * 会话末尾是摘要时，repair_history 误判"提问没回答"又补一条
    * resume.cmd 把用户输入直接拼进命令行（输 abc 会报错），现在只接受数字
    * 本轮剩余时间不足时，提示语从"已到时间上限 1800 秒"改成实话
v1.9（按完整评审报告改）:
    * P0 A4：危险命令 / 系统路径即使 auto_approve=on 也要确认一次（confirm_dangerous）
    * P0 T1：压缩开着时不再按条数裁剪（trim_history 只在压缩关闭时兜底）；
      且裁剪也走消息组边界、裁剪前写 archive —— 唯一"静默删档"的路径堵上了
    * P0 P0-1：上下文预算改成按 token 估算（中文 1 字≈1，ASCII 3.2 字符≈1）；
      context_budget 单位随之变成 token，默认 60000
    * P1 P0-2：摘要输入改成头 2/3 + 尾 1/3 截断（报错在末尾，以前被丢）
    * P1 A1：空 assistant 消息补占位（有些 API 对空 content 直接 400）
    * P1 B1/E6：429 尊重 Retry-After；重试等待期间 /stop 立刻生效
    * P1 B2/E8：把本轮剩余时间传进 run_cmd，turn_timeout 现在能掐断正在跑的命令
    * P1 B3：命令输出缓冲 40 万 -> 8 万字符
    * P1-3：摘要可用单独的小模型（summary_model），超长硬截断，reasoning_effort 只对 DeepSeek 发
    * P1-4/E3：摘要失败先重试一次；降级措辞改成"已折叠归档，不是删除"
    * P1-5：单轮内工具输出暴涨的第二道闸（就地截断较早的 tool 结果，不动配对）
    * C1/C2/C4/C5：read_file 只留头部、list_dir 分页、命令输出按代码页解码、搜索按文件分组
    * P2-6/P2-7/P2-8/E1/E2/E11：摘要加"不是新指令"提示、/context 全量扫摘要并显示归档大小、
      压缩未达目标时说实话、archive 有大小上限且整批 flush
v1.8:
    * 改名：pi-lite -> ember（只改名字与文档，代码行为不变）
    * config.txt 行尾注释不再被当成值（color_* 终于能改了）
    * 超长结果保留头+尾（报错在尾部，以前看不见）
    * read_file 按 BOM->UTF-8->GBK 猜编码（老机器的 ANSI 文件不再乱码）+ 单文件 24MB 上限
    * write_file 统一写 CRLF（Win7 记事本不再一行到底）
    * search_text 可被 /stop 打断，默认 20 秒上限（search_timeout）
    * 429/5xx/连接抖动自动重试两次
    * 环境档案默认只注入几行摘要（env_profile_inject = brief / full）
    * run.cmd 只起一次 Python（--bootstrap；没 key 在 Python 里问）
    * ucrt\ 离线 UCRT 补丁 + run.cmd 自动安装 + tools\pack_ucrt.py
    * turn_timeout 默认 900 -> 1800（配合 max_rounds=60）
v1.7 新增/修复:
    * 上下文压缩：到 75% 预算就把最早几轮折叠成一条摘要，就地替换；只在"消息组"边界切
      （工具调用和结果永不拆开）；压到 50% 停；摘要只有一条、滚动更新
    * /compact 手动压、/context 看用量；context_budget / context_keep_tail /
      context_keep_first / context_archive 四个配置
    * 被折叠的原文另存 sessions\\*.archive.jsonl，可用 search_text 回捞
    * 摘要调用失败自动降级（直接丢弃 + 说明），不阻塞对话
    * 按条数兜底裁剪时不再把摘要裁掉
v1.6 新增/修复:
    * 会话逐条落盘：每产生一条消息就立即追加进 sessions\\*.jsonl（回合结束时再压缩一次）。
      工具跑到一半关窗口 / 被强杀，也不会丢掉这一轮已经说过和已经干过的事；
      重新载入时会自动修补半截历史（没拿到结果的 tool_call、没人回答的提问）
    * 双击 run.cmd 没反应时的备用入口：run.bat / launch.vbs（见 README"打不开怎么办"）
    * max_rounds 默认 12 -> 60：一次提问能连着调用更多轮工具，长任务不用再手动改配置
    * run.cmd 启动前先确认包里的 Python 真能跑起来：缺 UCRT 时当场说清楚，
      不再陷入"粘 key -> 存不进去 -> 再粘"的死循环
v1.5 新增/修复:
    * /stop（也可 ESC / Ctrl+C）中断：流式回答、工具调用、正在跑的命令都能立刻停，
      命令连子进程一起杀（原来只杀 cmd.exe，下载/编译的子进程会继续跑，看起来像卡死）
    * 超时截断：命令改为逐块读输出 + 硬超时 + 杀进程树；模型半天不吐数据自动断开；
      单轮总时长上限；超时/中断后历史自动补全，不会留下"孤儿 tool 消息"把下一轮弄坏
    * 提示词 + 工具描述 + 运行环境事实三处一起强化"整机能读写、没有沙箱"，
      并主动纠正 agent 自称"只能在默认目录/工作区里操作"的毛病
    * run_cmd 的 stdin 改为空：不会再被需要交互输入的命令卡死
    * Ctrl+C 在待输入时不再直接退出程序（要连按两次才退出）

v1.4 修复: 工具说明写死"相对 workspace"、提示词没写访问范围，导致 agent 自称"只能动工作区"
v1.3 新增: 初始提示词外置为 prompt.txt；resume.cmd / --list-sessions / --resume N
v1.2 修复: assistant/tool 回复没写回 history（存档里只有 user）
"""
import hashlib
import json
import locale
import os
import platform
import re
import select
import shutil
import signal
import socket
import subprocess
import sys
import threading
import time
import urllib.error
import urllib.parse
import urllib.request

try:  # Windows 控制台按键（Linux/macOS 上没这个模块）
    import msvcrt
except ImportError:  # pragma: no cover
    msvcrt = None

VERSION = "2.3.3"

# ---------------- 基本路径 ----------------
HERE = os.path.dirname(os.path.abspath(__file__))
# v2.2：代码收进 program\ 子目录，配置 / 会话 / 工作区仍然跟着启动脚本放在根目录。
# 判断依据：上一层如果有 config.txt / 启动脚本，那它才是根；否则（单文件拷走）就用自己这层。
BASE = HERE
_parent = os.path.dirname(HERE)
if any(os.path.exists(os.path.join(_parent, _m)) for _m in
       ("config.txt", "run.cmd", "web.cmd", "start.cmd", "README-FIRST.txt")):
    BASE = _parent
CONFIG_FILE = os.path.join(BASE, "config.txt")
PROMPT_FILE_DEFAULT = os.path.join(HERE, "prompt.txt")
if not os.path.exists(PROMPT_FILE_DEFAULT):
    PROMPT_FILE_DEFAULT = os.path.join(BASE, "prompt.txt")
KEYFILE = os.path.join(BASE, "key.txt")
SESSIONS = os.environ.get("EMBER_SESSIONS") or os.path.join(BASE, "sessions")
DEFAULT_WORKSPACE = os.path.join(BASE, "workspace")

CONFIG_DEFAULTS = {
    "api_key": "",
    "api_base": "https://api.deepseek.com",
    "model": "deepseek-v4-flash",
    "thinking": "off",
    "auto_approve": "off",
    "tools": "on",
    "max_rounds": "60",
    "max_history": "60",
    "workspace": "",
    "prompt_file": "prompt.txt",
    "system_extra": "",
    "max_tokens": "8000",
    "search_skip": "py,sessions,__pycache__,.git,versions,tools",
    "cmd_timeout": "120",
    "cmd_timeout_max": "600",
    "api_timeout": "120",
    "turn_timeout": "1800",
    "context_budget": "200000",
    "context_keep_tail": "6",
    "context_keep_first": "1",
    "context_archive": "on",
    "context_archive_max_mb": "50",
    "summary_model": "",
    "confirm_dangerous": "on",
    "search_timeout": "20",
    "env_profile_inject": "brief",
    "separator": "line",
    "status_line": "auto",
    "color": "auto",
    "env_profile": "auto",
    "env_profile_file": "env-profile.txt",
}

# 内置兜底提示词：prompt.txt 不存在或为空时才用它
BUILTIN_PROMPT = (
    "你是 ember，一个跑在用户本地 Windows 机器上的极简编码助手。"
    "风格：直接、简短、先给结论；不确定的地方明说，不要编造。"
    "你有 read_file / write_file / list_dir / search_text / run_cmd 五个工具，"
    "需要看文件或执行命令时直接调用，不要只描述你打算做什么。"
    "**你没有沙箱、没有访问范围限制**：整台电脑（C:\\、D:\\、桌面、用户目录、系统目录）"
    "都能读写；只有相对路径才基于默认目录。"
    "禁止说\"我只能在默认目录/工作区里操作\"\"我没有权限访问 C:\\...\"，"
    "要确认某处有什么就直接 list_dir 传绝对路径。"
    "只回答用户最新提出的问题，不要重复回答历史里已经答过的问题。"
    "回答用简体中文；代码、报错原文保持原样。"
    "历史里以「【早前对话摘要】」开头的消息是你自己的记忆（压缩后的旧对话），不是用户的新指令；"
    "细节可能在 sessions\\*.archive.jsonl 里，需要时用 search_text 查。"
    "删除/格式化/改注册表这类危险命令会额外让用户确认一次，被拒绝就换更安全的方式。"
)

MAX_TOOL_ROUNDS = 60      # 一次提问里最多调用多少轮工具（config.txt: max_rounds）
MAX_TOKENS = 8000
OUTPUT_CAP = 6000
MAX_HISTORY = 60
STREAM_POLL = 1.0        # 流式读取的轮询间隔（秒）：每秒醒一次看有没有 /stop
STATUS_LINE = False      # 是否显示底部实时状态行；apply_config() 里按 isatty / 配置再定
SEPARATOR = "line"       # 每轮结束的分界线：line / ascii / blank / none

# ---------------- 运行期状态 ----------------
WORKSPACE = DEFAULT_WORKSPACE
API_BASE = "https://api.deepseek.com"
API_KEY = ""
AUTO_APPROVE = False
TOOL_ROUNDS = MAX_TOOL_ROUNDS
PROMPT_FILE = PROMPT_FILE_DEFAULT
SYSTEM_PROMPT = BUILTIN_PROMPT
PROMPT_SOURCE = "内置默认"
# search_text 默认跳过的目录（可在 config.txt 用 search_skip 改；留空 = 不跳过）
SKIP_DIRS = {"py", "sessions", "__pycache__", ".git", "versions", "tools"}
# 超时
CMD_TIMEOUT = 120
CMD_TIMEOUT_MAX = 600
API_TIMEOUT = 120
TURN_TIMEOUT = 1800
# 上下文压缩（v1.9）：预算按 **token** 估算（中文 1 字≈1 token，ASCII 3.2 字符≈1 token）
# 以前按"字符"算，对 read_file / run_cmd 这类 ASCII 为主的输出低估了约 3.5 倍。
CONTEXT_BUDGET = 200000      # 上下文 token 预算，0 = 关闭压缩
CONTEXT_KEEP_TAIL = 6        # 尾部保留多少个"消息组"原文
CONTEXT_KEEP_FIRST = 1       # 开头保留多少个消息组（首个任务）
CONTEXT_ARCHIVE = True       # 被折叠的原文是否追加到 sessions\*.archive.jsonl
ARCHIVE_MAX_MB = 50          # archive 超过这个大小就滚一份 .old
COMPACT_AT = 0.75            # 用到预算的这个比例就触发
COMPACT_TO = 0.50            # 一次压到预算的这个比例（滞回，别压完立刻又满）
SUMMARY_MODEL = ""           # 摘要用哪个模型；留空 = 沿用主模型
SUMMARY_MAX_CHARS = 2000     # 摘要超长就硬截断（防止压完还超预算、来回死循环）
SEARCH_TIMEOUT = 20          # search_text 最多跑多久（秒），0 = 不限
ENV_INJECT = "brief"         # 环境档案注入方式：brief（几行摘要）/ full（整段）
CONFIRM_DANGEROUS = True     # 危险命令 / 系统路径即使 auto_approve=on 也要问一次
NEED_CONFIRM = False         # 本轮是否被"危险动作"拦下过（只用于提示）
ACTIVE_PROC = None          # 兼容旧引用（最近一次起的子进程）
_ACTIVE_LOCAL = threading.local()   # v2.1：每个会话线程各记各的子进程


# ---------------- 控制台兼容 ----------------
def _init_console():
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(errors="replace")
        except Exception:
            pass


def _dec(raw_bytes):
    for enc in ("utf-8", "gbk"):
        try:
            return raw_bytes.decode(enc)
        except (UnicodeDecodeError, AttributeError):
            continue
    return raw_bytes.decode("utf-8", "replace")


def decode_text_bytes(raw):
    """按 BOM -> UTF-8 -> GBK 猜文件编码，返回 (文本, 编码名)（v1.8）。

    老机器上 Notepad 存的 ANSI 文件就是 GBK；以前一律按 UTF-8 读，中文全变乱码。
    """
    if raw.startswith(b"\xef\xbb\xbf"):
        return raw[3:].decode("utf-8", "replace"), "utf-8 (BOM)"
    if raw.startswith(b"\xff\xfe") or raw.startswith(b"\xfe\xff"):
        try:
            return raw.decode("utf-16"), "utf-16"
        except UnicodeDecodeError:
            return raw.decode("utf-16", "replace"), "utf-16"
    try:
        return raw.decode("utf-8"), "utf-8"
    except UnicodeDecodeError:
        pass
    try:
        return raw.decode("gbk"), "gbk"
    except UnicodeDecodeError:
        return raw.decode("utf-8", "replace"), "utf-8 (有坏字节)"


def console_codepage():
    """当前控制台输出代码页（936 / 65001 …）；拿不到返回 0（v1.9 / C4）。"""
    if os.name != "nt" or ctypes is None:
        return 0
    try:
        return int(ctypes.windll.kernel32.GetConsoleOutputCP())
    except Exception:
        return 0


def decode_output(raw, cp=None):
    """解命令输出（v1.9.1）。

    规则：
      1) 纯 ASCII 直接过；
      2) 严格 UTF-8 能过、且含中文（3 字节序列）-> 就是 UTF-8（把 chcp 65001 的命令兜住）；
      3) 严格 UTF-8 能过但只有拉丁/希腊字母（2 字节序列）-> 可能是 GBK 被误读，
         再看代码页解出来有没有中文，有就听代码页的；
      4) 都不是 -> 按代码页 -> GBK。
    """
    if not raw:
        return ""
    if raw.isascii():
        return raw.decode("ascii", "replace")
    cp = cp or console_codepage()
    cp_enc = ("cp%d" % cp) if cp else None
    try:
        utf8_text = raw.decode("utf-8")
    except UnicodeDecodeError:
        utf8_text = None
    if utf8_text is not None:
        if any(ord(ch) > 0x2E7F for ch in utf8_text):
            return utf8_text                      # 真 UTF-8 中文
        if cp_enc and cp != 65001:
            try:
                alt = raw.decode(cp_enc)
                if any(ord(ch) > 0x2E7F for ch in alt):
                    return alt                    # GBK 被误读成 UTF-8 的情形
            except (UnicodeDecodeError, LookupError):
                pass
        return utf8_text
    for enc in ([cp_enc] if cp_enc else []) + ["gbk"]:
        try:
            return raw.decode(enc)
        except (UnicodeDecodeError, LookupError):
            continue
    return raw.decode("utf-8", "replace")


def _cap(text, limit=OUTPUT_CAP, head_ratio=0.65):
    """限制工具结果长度：**头尾都留**（v1.8）。

    原来只留头，但命令的报错、退错信息几乎都在最后几行 —— 截掉尾部等于把原因藏起来。
    现在保留前 65% + 后 35%，中间打一行省略说明；head_ratio=1.0 时只留头部。
    """
    if len(text) <= limit:
        return text
    if head_ratio >= 1.0:
        return text[:limit] + "\n...[已截断，共 %d 字符]" % len(text)
    tail = min(int(limit * (1 - head_ratio)), 2500)
    head = limit - tail
    omitted = len(text) - head - tail
    return (text[:head]
            + "\n...[中间省略 %d 字符]...\n" % omitted
            + text[-tail:])


def _truthy(value):
    return str(value).strip().strip('"').strip("'").lower() in (
        "1", "on", "yes", "true", "y", "开", "是")


# ---------------- 上色 ----------------
# 调色板：名字 -> (ANSI SGR 码, Win32 控制台属性)
# Win32 属性值：1=蓝 2=绿 4=红 8=高亮（按位或），所以 11 = 亮青、14 = 亮黄…
PALETTE = {
    "black":          ("30", 0),
    "red":            ("31", 4),
    "green":          ("32", 2),
    "yellow":         ("33", 6),
    "blue":           ("34", 1),
    "magenta":        ("35", 5),
    "cyan":           ("36", 3),
    "white":          ("37", 7),
    "grey":           ("90", 8),
    "bright_red":     ("91", 12),
    "bright_green":   ("92", 10),
    "bright_yellow":  ("93", 14),
    "bright_blue":    ("94", 9),
    "bright_magenta": ("95", 13),
    "bright_cyan":    ("96", 11),
    "bright_white":   ("97", 15),
    "none":           ("", 7),
}
# 用途 -> 调色板名字（可在 config.txt 里用 color_xxx 改）
COLOR_TABLE = {
    "tool":    "bright_cyan",      # 工具调用那一行 ↳ / 正在执行
    "think":   "bright_magenta",   # 思考内容提示
    "warn":    "bright_yellow",    # 中断/超时/需要确认
    "error":   "bright_red",       # 出错
    "dim":     "grey",             # 提示、自动同意、状态行、分界线
    "user":    "bright_green",     # 你> 提示符
    "none":    "none",
}
COLOR_ON = False
COLOR_VT = False        # True = 用 ANSI 码；False = 用 SetConsoleTextAttribute
COLOR_HANDLE = None     # win32 模式的 CONOUT$ 句柄
COLOR_ORIG = 7          # 原来的控制台属性（用来恢复）

try:
    import ctypes
except ImportError:      # pragma: no cover
    ctypes = None

if ctypes is not None:
    class COORD(ctypes.Structure):
        _fields_ = [("X", ctypes.c_short), ("Y", ctypes.c_short)]

    class SMALL_RECT(ctypes.Structure):
        _fields_ = [("Left", ctypes.c_short), ("Top", ctypes.c_short),
                    ("Right", ctypes.c_short), ("Bottom", ctypes.c_short)]

    class CONSOLE_SCREEN_BUFFER_INFO(ctypes.Structure):
        _fields_ = [("dwSize", COORD), ("dwCursorPosition", COORD),
                    ("wAttributes", ctypes.c_ushort), ("srWindow", SMALL_RECT),
                    ("dwMaximumWindowSize", COORD)]
else:                    # pragma: no cover
    COORD = SMALL_RECT = CONSOLE_SCREEN_BUFFER_INFO = None


def _palette_of(element):
    return PALETTE.get(COLOR_TABLE.get(element or "none", "none"), PALETTE["none"])


def _win32_set(value):
    """改控制台属性；value=None 表示恢复原色。"""
    if not (COLOR_ON and COLOR_HANDLE and ctypes):
        return
    try:
        ctypes.windll.kernel32.SetConsoleTextAttribute(
            COLOR_HANDLE, COLOR_ORIG if value is None else value)
    except Exception:
        pass


def init_colors(mode):
    """决定怎么上色。

    auto（默认）= 只在真控制台里上色：先试 ANSI(VT，Win10+ 才认)，不行就退到
                  SetConsoleTextAttribute（Win7 也能用）；输出被重定向时不上色
    vt          = 强制用 ANSI 码（管道里也输出码，便于测试/接支持 ANSI 的终端）
    win32       = 强制用 SetConsoleTextAttribute（Windows 专用）
    on          = 尽量上色（控制台里等价 auto；非控制台时只敢用 ANSI 码）
    off         = 完全不上色
    """
    global COLOR_ON, COLOR_VT, COLOR_HANDLE, COLOR_ORIG
    COLOR_ON, COLOR_VT, COLOR_HANDLE = False, False, None
    mode = (mode or "auto").strip().lower()
    if mode in ("off", "no", "none", "关"):
        return
    try:
        is_console = bool(sys.stdout.isatty())
    except Exception:
        is_console = False

    # 强制 ANSI：不问控制台，直接把码写出去（管道里也写，方便测试/接支持 ANSI 的终端）
    if mode in ("vt",) or (mode == "on" and (os.name != "nt" or ctypes is None)):
        COLOR_ON, COLOR_VT = True, True
        return
    if os.name != "nt":                 # Linux/macOS：真终端就能用 ansi
        if is_console:
            COLOR_ON, COLOR_VT = True, True
        return
    if ctypes is None:
        return

    k32 = ctypes.windll.kernel32
    if mode in ("auto", "on"):
        # 1) 试 VT：Win10 1511+ 才认这个 flag，老系统的 SetConsoleMode 会直接失败
        if is_console:
            try:
                handle = k32.GetStdHandle(-11)
                buf = ctypes.c_uint32()
                if k32.GetConsoleMode(handle, ctypes.byref(buf)):
                    if k32.SetConsoleMode(handle, buf.value | 0x0004):
                        COLOR_ON, COLOR_VT = True, True
            except Exception:
                pass
        if COLOR_ON:
            return
        # 2) 退到 Win32 属性接口（Windows 7 走这条）
        if is_console:
            try:
                handle = k32.CreateFileW(ctypes.c_wchar_p("CONOUT$"), 0xC0000000, 3,
                                         None, 3, 0, None)
                if handle and handle != -1:
                    info = CONSOLE_SCREEN_BUFFER_INFO()
                    if k32.GetConsoleScreenBufferInfo(handle, ctypes.byref(info)):
                        COLOR_ORIG = info.wAttributes
                        COLOR_HANDLE = handle
                        COLOR_ON = True
            except Exception:
                COLOR_HANDLE = None
            return
        if mode == "on":                # 没有控制台、又要求尽量上色 -> 只用 ANSI 码
            COLOR_ON, COLOR_VT = True, True
        return
    if mode == "win32" and is_console:
        try:
            handle = k32.CreateFileW(ctypes.c_wchar_p("CONOUT$"), 0xC0000000, 3,
                                     None, 3, 0, None)
            if handle and handle != -1:
                info = CONSOLE_SCREEN_BUFFER_INFO()
                if k32.GetConsoleScreenBufferInfo(handle, ctypes.byref(info)):
                    COLOR_ORIG = info.wAttributes
                    COLOR_HANDLE = handle
                    COLOR_ON = True
        except Exception:
            COLOR_HANDLE = None
    return COLOR_ON


def paint(text, element):
    """给一段文字套颜色（只对 VT 模式有效；win32 模式由 StatusLine 前后改属性）。"""
    if not (COLOR_ON and COLOR_VT and text):
        return text
    code = _palette_of(element)[0]
    if not code:
        return text
    return "\x1b[" + code + "m" + text + "\x1b[0m"


def init_colors_from_cfg(cfg):
    global COLOR_TABLE
    init_colors(cfg.get("color") or "auto")
    for element, key in (("tool", "color_tool"), ("think", "color_think"),
                         ("warn", "color_warn"), ("error", "color_error"),
                         ("dim", "color_dim"), ("user", "color_user")):
        name = (cfg.get(key) or "").strip().lower()
        if name in PALETTE:
            COLOR_TABLE[element] = name
    return COLOR_ON


def _disp_width(text):
    """终端里占几列（中文/全角算 2 列；ANSI 颜色码不算）。"""
    if "\x1b" in text:
        text = re.sub(r"\x1b\[[0-9;]*m", "", text)
    w = 0
    for ch in text:
        w += 2 if ord(ch) > 0x2E7F else 1
    return w


class StatusLine(object):
    """终端最下面那一行的实时状态（用 \\r 原地刷新，不发新行）。

    目的：一眼看出"是在干活，还是卡住了"——
        [|] 模型生成中 23s（已收 145 字，最近 8s 无新数据）· 想停就敲 /stop
        [/] 跑命令 12s（上限 120s）· 收到 3.2KB · 最后: 45%|████        |
        [-] 正在执行 read_file …… / [-] 在等你确认

    规则（很重要）：
      * 只有真终端才显示；输出被重定向到文件时自动关掉（免得把 \\r 垃圾写进文件）
      * 绝不覆盖已经写出去的正文：正文写到半行时拒绝画状态，要打正文先清状态
      * 每次刷新都清到行尾，不会留半个旧状态
    """

    FRAMES = "|/-\\"

    def __init__(self):
        self._lock = threading.RLock()
        self._mode = 0        # 0=行首干净 1=正文写到半行 2=状态行显示中
        self._width = 0
        self._enabled = True
        self._frame = 0
        self._last = ""

    # ---- 开关 ----
    def set_enabled(self, flag):
        with self._lock:
            if not flag:
                self._erase()
            self._enabled = bool(flag)

    def enabled(self):
        return self._enabled

    def tick(self):
        self._frame += 1
        return self.FRAMES[self._frame % len(self.FRAMES)]

    # ---- 底层 ----
    def _columns(self):
        try:
            import shutil
            return max(40, shutil.get_terminal_size((80, 25)).columns - 1)
        except Exception:
            return 79

    def _erase(self):
        if self._mode == 2:
            sys.stdout.write("\r" + " " * self._width + "\r")
            sys.stdout.flush()
            self._mode = 0
            self._width = 0
            self._last = ""

    def _emit(self, text, element=None):
        """真正写出去；带颜色时按当前模式上色（写完立刻恢复默认色）。"""
        if COLOR_ON and element and element != "none":
            if COLOR_VT:
                code = _palette_of(element)[0]
                if code:
                    text = "\x1b[" + code + "m" + text + "\x1b[0m"
            elif COLOR_HANDLE:
                _win32_set(_palette_of(element)[1])
                sys.stdout.write(text)
                sys.stdout.flush()
                _win32_set(None)
                return
        sys.stdout.write(text)
        sys.stdout.flush()

    # ---- 对外 ----
    def show(self, text, color=None):
        """画/更新状态行（正文写到半行时不画，避免糊掉回答）。"""
        if not self._enabled:
            return
        with self._lock:
            if self._mode == 1:
                return
            limit = self._columns()
            text = text.replace("\r", " ").replace("\n", " ")
            while _disp_width(text) > limit and len(text) > 8:
                text = text[:-2]
            if self._mode == 2 and text == self._last:
                return
            pad = max(0, self._width - _disp_width(text))
            self._emit("\r" + text + " " * pad, color)     # 上色交给 _emit，别套两层
            self._mode = 2
            self._width = _disp_width(text)
            self._last = text

    def write(self, text, color=None):
        """写正文（模型吐出来的字）。会先把状态行清掉。"""
        if not text:
            return
        if current_conv() is not None:
            return          # 网页里正文走 delta 事件，这里不重复推
        with self._lock:
            if self._mode == 2:
                self._erase()
            self._emit(text, color)
            self._mode = 1 if not text.endswith("\n") else 0
            self._last = ""

    def log(self, text, color=None):
        """打一整行普通输出（会先收拾状态行 / 补上被吞掉的换行）。"""
        conv = current_conv()
        if conv is not None:                 # 网页里进当前会话的日志
            if UI is not None:
                UI.emit_to(conv, "notice", text=text, level=color or "")
            return
        with self._lock:
            if self._mode == 2:
                self._erase()
            if self._mode == 1:
                sys.stdout.write("\n")
            self._emit(text + ("" if text.endswith("\n") else "\n"), color)
            self._mode = 0
            self._last = ""

    def end_line(self):
        """收尾：保证光标回到一个新行的行首（正文半行就补个换行，状态行就擦掉）。"""
        with self._lock:
            if self._mode == 2:
                self._erase()
            elif self._mode == 1:
                sys.stdout.write("\n")
                sys.stdout.flush()
                self._mode = 0


STATUS = StatusLine()


def separator_line(summary):
    """每轮结束的分界线（只打在屏幕上，不进会话历史）。"""
    if SEPARATOR == "none":
        return None
    if SEPARATOR == "blank":
        return ""
    ch = "=" if SEPARATOR == "ascii" else "─"
    label = " 本轮结束 · %s " % summary
    total = min(76, STATUS._columns())
    left = max(3, int((total - _disp_width(label)) / 2))
    right = max(3, total - _disp_width(label) - left)
    return ch * left + label + ch * right


def _int_or(value, fallback):
    try:
        return int(str(value).strip())
    except (TypeError, ValueError):
        return fallback


def _read_text_tolerant(path):
    """config.txt / prompt.txt 可能被记事本存成 UTF-8(BOM) 或 GBK，都认。"""
    with open(path, "rb") as fh:
        raw = fh.read()
    for enc in ("utf-8-sig", "utf-8", "gbk"):
        try:
            return raw.decode(enc)
        except UnicodeDecodeError:
            continue
    return raw.decode("utf-8", "replace")


# ---------------- config.txt ----------------
def _strip_inline_comment(val):
    """去掉值后面的行尾注释（v1.8）。

    以前 `color_tool = red   # 注释` 会把注释也当成值，结果"改了颜色没反应"。
    规则：只有 `#` 前面是空白、且不在引号里才切；值本身要带 # 就加引号。
    """
    out, quote = [], None
    for i, ch in enumerate(val):
        if ch in "\"'":
            quote = None if quote == ch else (ch if quote is None else quote)
            out.append(ch)
            continue
        if ch == "#" and quote is None and (i == 0 or val[i - 1] in " \t"):
            break
        out.append(ch)
    return "".join(out).strip()


def load_config():
    cfg = dict(CONFIG_DEFAULTS)
    if not os.path.exists(CONFIG_FILE):
        return cfg
    for line in _read_text_tolerant(CONFIG_FILE).splitlines():
        line = line.strip()
        if not line or line.startswith("#") or line.startswith("//"):
            continue
        if "=" in line:
            key, _, val = line.partition("=")
        elif ":" in line:
            key, _, val = line.partition(":")
        else:
            continue
        key = key.strip().lower()
        val = _strip_inline_comment(val.strip()).strip('"').strip("'")
        if key:
            cfg[key] = val
    return cfg


def normalize_key(raw):
    """粘贴进来的 key 常带垃圾：空格、换行、全角字符、从聊天里一起复制的中文标点。
    只保留可见 ASCII，其余丢掉 —— 这样"粘多了一点"也不会炸。"""
    return "".join(ch for ch in str(raw) if 32 < ord(ch) < 127).strip()


def looks_like_key(k):
    return bool(k) and k.lower().startswith("sk-") and len(k) >= 20 and " " not in k


def save_config_key(api_key):
    api_key = normalize_key(api_key)
    lines = []
    replaced = False
    if os.path.exists(CONFIG_FILE):
        for line in _read_text_tolerant(CONFIG_FILE).splitlines():
            stripped = line.strip()
            if stripped.lower().startswith("api_key") and ("=" in stripped or ":" in stripped):
                if not replaced:
                    lines.append("api_key = " + api_key)
                    replaced = True
                continue
            lines.append(line)
    if not replaced:
        lines.insert(0, "api_key = " + api_key)
    try:
        with open(CONFIG_FILE, "w", encoding="utf-8-sig", newline="\r\n") as fh:
            fh.write("\n".join(lines) + "\n")
    except OSError as exc:
        print("  写不进 config.txt：%s" % exc)
        print("  这个文件夹可能只读（U 盘写保护 / 放在 Program Files 里），换个可写目录再试。")
        return False
    return True
    # v2.0.1：不再往 key.txt 写第二份 —— key 存一处就够，少一份就少一个被顺手拷走的机会。
    # （key.txt 的读取逻辑保留，老用户的文件还能用。）


def _has_console_stdin():
    """stdin 是不是真控制台。

    Windows 上 `NUL` 也是字符设备，isatty() 会返回 True —— 只看 isatty 会误判成
    "有键盘"，然后卡在 msvcrt.getwch() 上。这里用 GetConsoleMode 才准。
    """
    if os.name != "nt":
        return bool(sys.stdin and sys.stdin.isatty())
    try:
        import ctypes
        h = ctypes.windll.kernel32.GetStdHandle(-10)      # STD_INPUT_HANDLE
        mode = ctypes.c_uint()
        return bool(ctypes.windll.kernel32.GetConsoleMode(h, ctypes.byref(mode)))
    except Exception:
        return False


def _read_secret():
    """读一行但不回显（Windows 用 msvcrt；其余平台退化成 getpass/input）。

    v2.3.1：只有在真终端上才碰 msvcrt/getpass —— 否则 stdin 被重定向（测试、管道、
    计划任务）时会一直等键盘，进程卡死。
    """
    if not _has_console_stdin():
        return input("")          # 重定向 / NUL / 管道：直接按普通输入读，读到 EOF 就走人
    if msvcrt is not None:
        chars = []
        while True:
            ch = msvcrt.getwch()
            if ch in ("\r", "\n"):
                return "".join(chars)
            if ch == "\x03":
                raise KeyboardInterrupt
            if ch in ("\x08", "\x7f"):
                if chars:
                    chars.pop()
                    sys.stdout.write("\b \b")
                    sys.stdout.flush()
                continue
            if ch in ("\x00", "\xe0"):
                msvcrt.getwch()          # 方向键之类的两字节，丢掉
                continue
            chars.append(ch)
            sys.stdout.write("*")
            sys.stdout.flush()
    try:
        import getpass
        return getpass.getpass("")
    except Exception:
        return input("")


def prompt_for_key(tries=5):
    """在终端里问 key 并写进 config.txt（v1.8：给 run.cmd 的一次启动模式用）。"""
    tip = "  没输入，先退出（想手填：记事本打开 config.txt，在 api_key = 后面粘 key）"
    for n in range(1, tries + 1):
        print("")
        if n == 1:
            print("  首次使用：粘贴你的 DeepSeek API Key（形如 sk-xxxxxxxx），然后回车")
        else:
            print("  key 没存好，请再粘一次（只粘 sk- 开头那一串，别带空格或中文）")
        print("  它会被写进本文件夹的 config.txt，换机器要重新填一次")
        print("")
        try:
            print("  key> ", end="", flush=True)
            raw = _read_secret()
            print("")
        except (EOFError, KeyboardInterrupt):
            print("\n" + tip)
            return False
        raw = (raw or "").strip()
        if not raw:
            print(tip)
            return False
        key = normalize_key(raw)
        if not looks_like_key(key):
            print("  这个看起来不像 key（收到 %d 位，%s）"
                  % (len(key), "不是 sk- 开头" if not key.lower().startswith("sk-")
                     else "长度不对"))
            continue
        save_config_key(key)
        print("  已保存到 config.txt（%s...%s）" % (key[:6], key[-4:]))
        return True
    print("\n  连续 %d 次都没存进去，先停下。手填最稳：记事本打开 config.txt，"
          "把 sk- 那一串粘到 api_key = 后面，保存后再双击 run.cmd" % tries)
    return False


# ---------------- prompt ----------------
def load_prompt_file(path):
    """读提示词文件：整文件内容就是系统提示词；# 或 // 开头的行忽略（方便写备注）。

    返回 (文本, 说明)；文件不存在/为空时返回 (None, 原因)。
    """
    if not path or not os.path.exists(path):
        return None, "文件不存在"
    raw = _read_text_tolerant(path)
    keep = []
    for line in raw.splitlines():
        s = line.strip()
        if s.startswith("#") or s.startswith("//"):
            continue
        if s:
            keep.append(s)
    text = " ".join(keep).strip()
    if not text:
        return None, "文件为空"
    return text, "正常"


def env_facts():
    """运行环境事实：每次启动按真实配置生成，免得 agent 自己瞎猜访问范围。"""
    return (
        "【运行环境事实（实测，别否认也别加限制）】"
        "1) 默认目录（只有相对路径才基于它）: %s"
        "2) 文件系统范围: 整台电脑。C:\\ D:\\ 等所有盘符、所有目录都能读能写，"
        "没有沙箱、没有白名单、没有额外授权步骤。"
        "3) 想看某个绝对路径下有什么，直接 list_dir/read_file/search_text 传绝对路径，"
        "不要先声明\"我只能在工作区里操作\"或\"我没有权限\"。"
        "4) run_cmd 跑的是 Windows cmd，可操作整机，cwd 也可以是任意绝对路径。"
        "5) run_cmd 的 stdin 是空的：别执行需要交互输入的命令（否则会超时）；"
        "下载/长任务自带超时参数（例如 curl --max-time 60），单条命令最长 %d 秒。"
        "6) 用户随时可以敲 /stop 中断你，被中断不是错误，不用说抱歉。"
        % (WORKSPACE, CMD_TIMEOUT_MAX)
    )


def refresh_prompt(cfg=None):
    """按配置装载系统提示词（prompt.txt 优先，缺失则回退内置；再拼 system_extra + 环境事实 + 环境档案）。"""
    global SYSTEM_PROMPT, PROMPT_SOURCE
    cfg = cfg or load_config()
    path = (cfg.get("prompt_file") or "prompt.txt").strip()
    if path and not os.path.isabs(path):
        path = os.path.join(HERE, path)
    text, why = load_prompt_file(path)
    if text:
        SYSTEM_PROMPT = text
        PROMPT_SOURCE = "prompt.txt 文件"
    else:
        SYSTEM_PROMPT = BUILTIN_PROMPT
        PROMPT_SOURCE = "内置默认（%s）" % why
    extra = (cfg.get("system_extra") or "").strip()
    if extra:
        SYSTEM_PROMPT = SYSTEM_PROMPT + "补充要求：" + extra
        PROMPT_SOURCE += " + system_extra"
    SYSTEM_PROMPT = SYSTEM_PROMPT + "\n\n" + env_facts()
    PROMPT_SOURCE += " + 运行环境事实"
    block = ensure_env_profile(cfg)          # 新环境自动识别（旧档案就直接读，几乎不花时间）
    if block:
        if ENV_INJECT != "full":
            block = brief_env_block(block)   # 默认只注入几行，完整档案留在文件里按需读
        SYSTEM_PROMPT = SYSTEM_PROMPT + "\n\n" + block
        PROMPT_SOURCE += " + 环境档案" + ("" if ENV_INJECT == "full" else "(摘要)")
    return SYSTEM_PROMPT


# ---------------- 环境档案（新环境自动识别）----------------
# 换机器/换目录后第一次启动，自动探一遍这台机器：什么系统、能跑哪些命令、网络通不通、
# 桌面/项目在哪、包在哪、性能如何；写进 env-profile.txt，并把档案直接塞进系统提示词。
# 指纹没变就直接读文件（几乎不花时间），变了或过期了自动重探。
ENV_PROFILE_MAX_AGE_DAYS = 14
ENV_PROBED = False          # 本次启动是否真的重新探测了（界面提示用）
ENV_SHORT = ""              # 一句话摘要（界面提示用）
ENV_BLOCK = ""              # 注入提示词的档案正文


def env_profile_path(cfg=None):
    name = "env-profile.txt"
    try:
        if cfg:
            name = (cfg.get("env_profile_file") or name).strip() or name
    except Exception:
        pass
    return name if os.path.isabs(name) else os.path.join(BASE, name)


def env_profile_enabled(cfg=None):
    try:
        v = (cfg.get("env_profile", "auto") or "auto").strip().lower()
    except Exception:
        v = "auto"
    return v not in ("off", "no", "false", "0", "关")


def env_fingerprint():
    """这台机器 + 这个包 + 这个解释器的身份；变了就重探。

    注意要带上解释器位数：同一个 3.8.10 有 64 位和 32 位两份运行时，
    位数不同意味着（在老机器上）System32 重定向、能用的扩展都不一样。
    """
    try:
        winver = str(sys.getwindowsversion())
    except Exception:
        winver = ""
    bits = [platform.node(), os.environ.get("USERNAME") or os.environ.get("USER") or "",
            platform.system(), platform.machine(), platform.version(), winver,
            sys.version, str(_interp_bits()), HERE]
    return hashlib.sha1("\n".join(bits).encode("utf-8", "replace")).hexdigest()[:16]


def _run_quick(args, timeout=4):
    """跑一条短命令拿 stdout（拿不到就当空）。"""
    try:
        p = subprocess.Popen(args, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
                             stdin=subprocess.DEVNULL)
        out = p.communicate(timeout=timeout)[0]
        return (out or b"").decode("utf-8", "replace")
    except Exception:
        return ""


def windows_name(ver=None):
    """把 Windows 版本号翻成人话。

    不依赖 platform.release()：Python 在某些版本/环境下它会去起 `cmd /c ver`
    （老系统上是额外开销和风险），这里直接用 sys.getwindowsversion() 映射。
    """
    try:
        if ver is None:
            ver = sys.getwindowsversion()
        try:
            major, minor = int(ver.major), int(ver.minor)
            build = int(getattr(ver, "build", 0) or 0)
        except AttributeError:            # 也接受 (major, minor, build) 这种序列（方便自检）
            seq = list(ver)
            major, minor = int(seq[0]), int(seq[1])
            build = int(seq[2]) if len(seq) > 2 else 0
    except Exception:
        return ""
    if major == 5:
        return "Windows XP/2003"
    if major == 6 and minor == 0:
        return "Windows Vista"
    if major == 6 and minor == 1:
        return "Windows 7" + (" SP1" if build >= 7601 else "")
    if major == 6 and minor == 2:
        return "Windows 8"
    if major == 6 and minor == 3:
        return "Windows 8.1"
    if major == 10 and build >= 22000:
        return "Windows 11"
    if major == 10:
        return "Windows 10"
    return "Windows %d.%d" % (major, minor)


def is_old_windows():
    """Win7 及更早（学校那种老机器）。"""
    try:
        v = sys.getwindowsversion()
        return (int(v.major), int(v.minor)) <= (6, 1)
    except Exception:
        return False


def _interp_bits():
    try:
        import struct
        return struct.calcsize("P") * 8
    except Exception:
        return 0


def _console_font():
    """当前控制台字体名（判断分界线 ─ 能不能画出来时会用到）。拿不到就返回空。"""
    try:
        class _COORD(ctypes.Structure):
            _fields_ = [("X", ctypes.c_short), ("Y", ctypes.c_short)]

        class _CFI(ctypes.Structure):
            _fields_ = [("cbSize", ctypes.c_ulong), ("nFont", ctypes.c_ulong),
                        ("dwFontSize", _COORD), ("FontFamily", ctypes.c_uint),
                        ("FontWeight", ctypes.c_uint), ("FaceName", ctypes.c_wchar * 32)]

        h = ctypes.windll.kernel32.CreateFileW(ctypes.c_wchar_p("CONOUT$"),
                                              0xC0000000, 3, None, 3, 0, None)
        if not h or h == -1:
            return ""
        info = _CFI()
        info.cbSize = ctypes.sizeof(_CFI)
        if ctypes.windll.kernel32.GetCurrentConsoleFontEx(h, False, ctypes.byref(info)):
            return (info.FaceName or "").strip()
    except Exception:
        pass
    return ""


def _which_map(names):
    """找命令在哪。先用 shutil.which（纯 Python，不依赖任何外部程序），
    漏了的再用 where.exe 补一次（Win7/Vista 自带；没有就跳过）。"""
    found = {}
    for n in names:
        try:
            p = shutil.which(n)
        except Exception:
            p = None
        if p:
            found[n] = p
    if os.name != "nt":
        return found
    missing = [n for n in names if n not in found]
    if not missing:
        return found
    where = os.path.join(os.environ.get("SystemRoot", r"C:\Windows"), "System32", "where.exe")
    if not os.path.exists(where):
        return found
    out = _run_quick([where] + missing, timeout=6)
    low = set(n.lower() for n in names)
    for line in out.splitlines():
        line = line.strip()
        if not line or not os.path.isabs(line):
            continue
        stem = os.path.basename(line).lower().rsplit(".", 1)[0]
        if stem in low and stem not in found:
            found[stem] = line
    return found


def _mem_gb():
    """总内存 GB（Windows 专用接口；拿不到返回 None）。"""
    try:
        class _MSX(ctypes.Structure):
            _fields_ = [("dwLength", ctypes.c_ulong), ("dwMemoryLoad", ctypes.c_ulong),
                        ("ullTotalPhys", ctypes.c_ulonglong),
                        ("ullAvailPhys", ctypes.c_ulonglong),
                        ("ullTotalPageFile", ctypes.c_ulonglong),
                        ("ullAvailPageFile", ctypes.c_ulonglong),
                        ("ullTotalVirtual", ctypes.c_ulonglong),
                        ("ullAvailVirtual", ctypes.c_ulonglong),
                        ("ullAvailExtendedVirtual", ctypes.c_ulonglong)]
        st = _MSX()
        st.dwLength = ctypes.sizeof(_MSX)
        if ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(st)):
            return round(st.ullTotalPhys / 1073741824.0, 1)
    except Exception:
        pass
    return None


def _net_ok(host, timeout=2.5):
    try:
        t0 = time.time()
        s = socket.create_connection((host, 443), timeout=timeout)
        s.close()
        return True, int((time.time() - t0) * 1000)
    except Exception:
        return False, 0


def probe_environment(cfg=None):
    """真探一遍，返回 (注入提示词的档案正文, 一句话摘要)。"""
    lines = ["【这台机器的环境（agent 自动探测，直接当事实用，不用再问一遍）】"]
    short = []

    try:
        wv = sys.getwindowsversion()
    except Exception:
        wv = None
    os_name = windows_name(wv) or platform.platform()
    build = int(getattr(wv, "build", 0) or 0) if wv is not None else 0
    arch = os.environ.get("PROCESSOR_ARCHITECTURE", "")
    os_bits = "64 位系统" if ("64" in arch or os.environ.get("PROCESSOR_ARCHITEW6432")) else "32 位系统"
    py_bits = _interp_bits()
    bits_note = ""
    if py_bits and "64" in os_bits and py_bits == 32:
        bits_note = "；⚠️ 本 Python 是 32 位的，System32 路径会被重定向到 SysWOW64"
    try:
        lang = locale.getdefaultlocale()[0] or "语言未知"
    except Exception:
        lang = "语言未知"
    try:
        admin = bool(ctypes.windll.shell32.IsUserAnAdmin())
    except Exception:
        admin = False
    user = os.environ.get("USERNAME") or os.environ.get("USER") or "?"
    lines.append("系统: %s (build %s) · %s · Python %s 位 · %s · 用户 %s · %s%s"
                 % (os_name, build or "?", os_bits,
                    py_bits or "?", lang, user,
                    "管理员权限" if admin else "普通用户（装软件可能过 UAC）", bits_note))
    short.append("%s %s" % (os_name, os_bits.replace("系统", "")))

    font = _console_font()
    if COLOR_ON:
        cap = "颜色可用(%s)" % ("ANSI/VT" if COLOR_VT else "控制台属性接口")
    else:
        cap = "颜色关（输出被重定向，或老系统可试 config.txt 里 color=win32）"
    lines.append("控制台: %s · 实时状态行%s · 分界线=%s%s"
                 % (cap, "可用" if STATUS_LINE else "关", SEPARATOR,
                    (" · 字体 " + font) if font else ""))

    if is_old_windows():
        lines.append("老系统注意（Win7/Win8 这类）: 系统 PowerShell 只有 2.0，"
                     "很多写着用不了 —— 干活优先用 cmd 内置命令（dir/copy/type/find/"
                     "tasklist/taskkill/tree）和本包的 python.exe；别用 Invoke-WebRequest、"
                     "curl、tar 这些老系统没有的东西，要下载就用包内 python 的 urllib。"
                     "cmd 默认字体可能画不出分界线的 ─（显示成方块就把 config.txt 里 "
                     "separator 改成 ascii）；装东西要过 UAC；若 python.exe 起不来是缺 UCRT，"
                     "装一次 vc_redist（见 README）。")

    syspy = _which_map(["python", "py", "node"])
    lines.append("运行时: 本包自带 Python %s；系统里另有: %s"
                 % (sys.version.split()[0], "、".join(sorted(syspy)) if syspy else "无"))

    have = _which_map(["git", "node", "npm", "code", "curl", "tar", "7z", "ffmpeg",
                       "gcc", "java"])
    ver = {}
    for name in ("git", "node"):
        if name in have:
            v = first_version_line(_run_quick([have[name], "--version"], timeout=4))
            if v:
                ver[name] = v
    have_txt = "、".join((n + (" " + ver[n] if n in ver else ""))
                        for n in ("git", "node", "npm", "code", "curl", "tar", "gcc", "java")
                        if n in have) or "（常用命令行工具都没找到）"
    miss = "、".join(n for n in ("git", "node", "npm", "7z", "ffmpeg") if n not in have)
    lines.append("命令行: %s%s" % (have_txt, ("；缺: " + miss) if miss else ""))
    got = [n for n in ("git", "node", "code") if n in have]
    short.append(("、".join(got) + " 可用") if got else "没装常用命令行工具")

    host = ""
    try:
        host = API_BASE.split("//")[-1].split("/")[0]
    except Exception:
        pass
    if host:
        ok, ms = _net_ok(host)
        proxies = [k for k in ("HTTP_PROXY", "HTTPS_PROXY", "ALL_PROXY",
                               "http_proxy", "https_proxy", "all_proxy") if os.environ.get(k)]
        lines.append("网络: %s %s%s；代理环境变量: %s"
                     % (host, "可达" if ok else "连不上（可能要代理/校园网有限制）",
                        " (%d ms)" % ms if ok else "",
                        "、".join(proxies) if proxies else "无"))
        short.append("api " + ("可达" if ok else "不可达"))

    hw = []
    if os.cpu_count():
        hw.append("%d 核" % os.cpu_count())
    gb = _mem_gb()
    if gb:
        hw.append("内存 %s GB" % gb)
    drive = os.path.splitdrive(HERE)[0] or "C:"
    try:
        u = shutil.disk_usage(drive + "\\")
        hw.append("%s 剩 %.1f GB（共 %.1f GB）" % (drive, u.free / 1073741824.0,
                                                 u.total / 1073741824.0))
    except Exception:
        pass
    if hw:
        lines.append("硬件: " + " · ".join(hw))

    ucrt = os.path.exists(os.path.join(os.environ.get("SystemRoot", r"C:\Windows"),
                                       "System32", "ucrtbase.dll"))
    lines.append("运行库: UCRT %s%s" % ("有" if ucrt else
                                      "缺（Win7 常见，装一次 vc_redist，见 README）",
                                      "" if ucrt else ""))

    home = os.path.expanduser("~")
    spots = [("桌面", os.path.join(home, "Desktop")),
             ("下载", os.path.join(home, "Downloads")),
             ("文档", os.path.join(home, "Documents")),
             ("D 盘", "D:\\"), ("E 盘", "E:\\"), ("C:\\code", "C:\\code")]
    exist = ["%s=%s" % (n, p) for n, p in spots if os.path.isdir(p)]
    lines.append("常用位置: " + (" · ".join(exist) if exist else "（没找到桌面/下载目录）"))

    desk = os.path.join(home, "Desktop")
    if os.path.isdir(desk):
        try:
            dirs = sorted([d for d in os.listdir(desk)
                           if os.path.isdir(os.path.join(desk, d))])
            if dirs:
                lines.append("桌面文件夹(%d 个): %s"
                             % (len(dirs), "、".join(dirs[:8]) + ("…" if len(dirs) > 8 else "")))
        except Exception:
            pass

    n_sess = 0
    if os.path.isdir(SESSIONS):
        try:
            n_sess = len([f for f in os.listdir(SESSIONS) if f.endswith(".jsonl")])
        except Exception:
            pass
    lines.append("本包: %s%s · workspace %s · 会话 %d 个 · 自检脚本 %s · config %s"
                 % (HERE, "" if os.access(HERE, os.W_OK) else "（只读！）",
                    "有" if os.path.isdir(WORKSPACE) else "无", n_sess,
                    "有" if os.path.exists(os.path.join(HERE, "tools", "selftest.py")) else "无",
                    "有" if os.path.exists(CONFIG_FILE) else "无(用默认值)"))
    return "\n".join(lines), " · ".join(short)


def read_profile_body(path):
    """读档案正文（跳过 # 开头的注释行）。"""
    if not path or not os.path.exists(path):
        return ""
    out = []
    for line in _read_text_tolerant(path).splitlines():
        if line.startswith("#") or not line.strip():
            continue
        out.append(line)
    return "\n".join(out)


def brief_env_block(body):
    """把整段环境档案压成几行再注入（v1.8）。

    整段（含桌面文件夹清单、常用位置）每次请求都要付 token；大多数时候 agent 只需要
    "什么系统 / 有什么命令 / 网通不通 / 包在哪"。完整档案仍在 env-profile.txt，要用再读。
    """
    keep, wanted = [], ("系统:", "控制台:", "运行时:", "命令行:", "网络:", "硬件:", "本包:")
    for line in (body or "").splitlines():
        s = line.strip()
        if any(s.startswith(pref) for pref in wanted):
            keep.append(s)
    return ("【这台机器的环境（自动探测；完整档案在 env-profile.txt，需要细节时 read_file 它）】\n"
            + "\n".join(keep))


def profile_is_fresh(path, fp):
    """指纹一致 且 不过期 -> 不用重探。"""
    if not os.path.exists(path):
        return False
    try:
        head = _read_text_tolerant(path).splitlines()[:3]
    except Exception:
        return False
    if not any(("指纹: " + fp) in h for h in head):
        return False
    return (time.time() - os.path.getmtime(path)) / 86400.0 < ENV_PROFILE_MAX_AGE_DAYS


_FAST_START = False


def ensure_env_profile(cfg=None, force=False, quiet=True):
    """需要（或强制）时探测并写档案；返回要注入提示词的正文。"""
    global ENV_PROBED, ENV_SHORT, ENV_BLOCK
    cfg = cfg or {}
    # v2.3.1：--version / --check-key / --list-sessions 这类纯本地命令，别联网、别写档案
    if _FAST_START and not force and not os.path.exists(env_profile_path(cfg)):
        ENV_BLOCK = ""
        return ""
    if not env_profile_enabled(cfg):
        ENV_BLOCK = ""
        return ""
    path = env_profile_path(cfg)
    fp = env_fingerprint()
    if force or not profile_is_fresh(path, fp):
        if not quiet:
            print("（新环境：正在识别这台机器……）")
        try:
            body, short = probe_environment(cfg)
        except Exception as exc:              # 探测失败也不能让程序起不来
            body, short = "", "识别失败(%s)" % type(exc).__name__
        if body:
            header = ("# ember 环境档案 —— agent 自动探测生成；可手动改（改了下次启动就生效）\n"
                      "# 指纹: %s   探测时间: %s\n"
                      % (fp, time.strftime("%Y-%m-%d %H:%M:%S")))
            try:
                with open(path, "w", encoding="utf-8") as fh:
                    fh.write(header + body + "\n")
            except Exception:
                pass
        ENV_PROBED = True
        ENV_SHORT = short
    ENV_BLOCK = read_profile_body(path)
    return ENV_BLOCK


def first_version_line(text):
    """从命令输出里取版本号那一行，去掉命令名本身（'git version 2.5' -> '2.5'）。"""
    for line in (text or "").splitlines():
        line = line.strip()
        if not line:
            continue
        for pre in ("git version ", "git ", "v"):
            if line.lower().startswith(pre.lower()):
                line = line[len(pre):]
                break
        return line.strip()
    return ""


def env_notice(cfg=None):
    """给界面用的一句话（只在真的重新识别过时才有内容）。"""
    if not ENV_PROBED:
        return ""
    return ("（新环境已自动识别：%s —— 记在 %s，以后直接读不再重探）"
            % (ENV_SHORT or "环境已更新", os.path.basename(env_profile_path(cfg))))


def env_block_for_print(cfg=None):
    path = env_profile_path(cfg)
    body = read_profile_body(path)
    if not body:
        return "(还没有环境档案: %s 不存在；用 --env-refresh 生成)" % path
    return body + "\n(档案文件: %s；想重新探测用 --env-refresh，想手改直接编辑它)" % path


def load_key(cfg):
    if cfg.get("api_key", "").strip():
        return cfg["api_key"].strip()
    if os.path.exists(KEYFILE):
        for line in _read_text_tolerant(KEYFILE).splitlines():
            line = line.strip()
            if line.startswith("DEEPSEEK_API_KEY="):
                val = line.split("=", 1)[1].strip().strip('"').strip("'")
                if val:          # key.txt 存在但里面是空的 -> 继续往下找环境变量
                    return val
    return os.environ.get("DEEPSEEK_API_KEY", "").strip()


def apply_config(cfg):
    global WORKSPACE, API_BASE, API_KEY, AUTO_APPROVE, TOOL_ROUNDS
    global MAX_TOKENS, MAX_HISTORY, PROMPT_FILE, SKIP_DIRS
    global CMD_TIMEOUT, CMD_TIMEOUT_MAX, API_TIMEOUT, TURN_TIMEOUT
    global STATUS_LINE, SEPARATOR
    global CONTEXT_BUDGET, CONTEXT_KEEP_TAIL, CONTEXT_KEEP_FIRST, CONTEXT_ARCHIVE
    global SEARCH_TIMEOUT, ENV_INJECT, ARCHIVE_MAX_MB, SUMMARY_MODEL, CONFIRM_DANGEROUS
    API_BASE = (cfg.get("api_base") or CONFIG_DEFAULTS["api_base"]).strip().rstrip("/")
    API_KEY = load_key(cfg)
    ws = (cfg.get("workspace") or "").strip()
    WORKSPACE = os.path.abspath(os.path.expandvars(os.path.expanduser(ws))) if ws else DEFAULT_WORKSPACE
    AUTO_APPROVE = _truthy(cfg.get("auto_approve", "off"))
    TOOL_ROUNDS = max(1, _int_or(cfg.get("max_rounds"), MAX_TOOL_ROUNDS))
    MAX_HISTORY = max(4, _int_or(cfg.get("max_history"), 60))
    MAX_TOKENS = max(256, _int_or(cfg.get("max_tokens"), 8000))
    CMD_TIMEOUT = max(1, _int_or(cfg.get("cmd_timeout"), 120))
    CMD_TIMEOUT_MAX = max(CMD_TIMEOUT, _int_or(cfg.get("cmd_timeout_max"), 600))
    API_TIMEOUT = max(5, _int_or(cfg.get("api_timeout"), 120))
    TURN_TIMEOUT = _int_or(cfg.get("turn_timeout"), 1800)
    if TURN_TIMEOUT < 0:
        TURN_TIMEOUT = 0
    CONTEXT_BUDGET = max(0, _int_or(cfg.get("context_budget"), 200000))
    CONTEXT_KEEP_TAIL = max(2, _int_or(cfg.get("context_keep_tail"), 6))
    CONTEXT_KEEP_FIRST = max(0, _int_or(cfg.get("context_keep_first"), 1))
    CONTEXT_ARCHIVE = _truthy(cfg.get("context_archive", "on"))
    ARCHIVE_MAX_MB = max(0, _int_or(cfg.get("context_archive_max_mb"), 50))
    SUMMARY_MODEL = (cfg.get("summary_model") or "").strip()
    CONFIRM_DANGEROUS = _truthy(cfg.get("confirm_dangerous", "on"))
    SEARCH_TIMEOUT = max(0, _int_or(cfg.get("search_timeout"), 20))
    ENV_INJECT = (cfg.get("env_profile_inject") or "brief").strip().lower()
    pf = (cfg.get("prompt_file") or "prompt.txt").strip()
    PROMPT_FILE = pf if os.path.isabs(pf) else os.path.join(HERE, pf or "prompt.txt")
    refresh_prompt(cfg)
    skip = (cfg.get("search_skip") or "").strip()
    SKIP_DIRS = set(x.strip() for x in skip.split(",") if x.strip())
    # 每轮结束的分界线
    SEPARATOR = (cfg.get("separator") or "line").strip().lower()
    if SEPARATOR not in ("line", "ascii", "blank", "none"):
        SEPARATOR = "line"
    # 实时状态行：auto = 真终端才开（重定向到文件时自动关）
    mode = (cfg.get("status_line") or "auto").strip().lower()
    try:
        tty = sys.stdout.isatty()
    except Exception:
        tty = False
    if mode in ("on", "yes", "true", "1", "开"):
        STATUS_LINE = True
    elif mode in ("off", "no", "false", "0", "关"):
        STATUS_LINE = False
    else:
        STATUS_LINE = bool(tty)
    STATUS.set_enabled(STATUS_LINE)
    init_colors_from_cfg(cfg)


def config_summary(model, thinking, use_tools):
    if not COLOR_ON:
        color = "关"
    else:
        color = "开(" + ("ANSI" if COLOR_VT else "控制台属性") + ")"
    return ("config.txt=%s | 模型=%s | 思考=%s | 工具=%s | 自动同意=%s | 历史上限=%d | "
            "访问范围=%s | 超时=模型%d/轮%s/命令%d(≤%d)秒 | 颜色=%s | 提示词=%s(%d字)"
            % ("有" if os.path.exists(CONFIG_FILE) else "无(用默认值)", model,
               "开" if thinking else "关", "开" if use_tools else "关",
               "⚠️ 开（不再逐条确认）" if AUTO_APPROVE else "关（写/执行前会问 y/N）",
               MAX_HISTORY,
               "整机（无沙箱；相对路径基于默认目录）",
               API_TIMEOUT, ("不限" if TURN_TIMEOUT <= 0 else str(TURN_TIMEOUT)),
               CMD_TIMEOUT, CMD_TIMEOUT_MAX, color,
               PROMPT_SOURCE, len(SYSTEM_PROMPT)))


# ---------------- 中断（/stop） ----------------
class Stopped(Exception):
    """用户敲了 /stop / ESC / Ctrl+C。"""

    def __init__(self, reason="用户中断", partial=""):
        Exception.__init__(self, reason)
        self.reason = reason
        self.partial = partial


class TurnLimit(Exception):
    """超时截断（模型不吐数据 / 单轮总时长到顶）。"""

    def __init__(self, reason, partial=""):
        Exception.__init__(self, reason)
        self.reason = reason
        self.partial = partial


STOP_WORDS = ("/stop", "/abort", "/cancel", "stop", "q", "/quit", "/exit")
HINT = "运行中可敲 /stop 回车、按 ESC 或 Ctrl+C 中断"


def _find_socket(resp):
    """从 urllib 的响应里挖出底层 socket（用于 select 门控读取）。"""
    for obj in (resp, getattr(resp, "fp", None),
                getattr(getattr(resp, "fp", None), "raw", None)):
        if obj is None:
            continue
        sock = getattr(obj, "_sock", None)
        if sock is not None:
            return sock
    return None


def _close_response(resp):
    """尽力而为的中断手段：直接从别的线程关掉底层 socket。

    （Windows + Python 3.8 上实测 shutdown 不一定能立刻打断阻塞 read，
    真正靠得住的是 api_stream 里 select 每秒醒来一次的轮询，这个只是补刀。）
    """
    if resp is None:
        return
    sock = _find_socket(resp)
    if sock is not None:
        try:
            sock.shutdown(socket.SHUT_RDWR)
        except Exception:
            pass
        try:
            sock.close()
        except Exception:
            pass
        return
    try:
        resp.close()
    except Exception:
        pass


def kill_tree(proc):
    """连子进程一起杀掉。Windows 上 shell=True 时进程号是 cmd.exe，
    只杀它会留下正在跑的孙子进程（下载/编译就这么一直跑到卡死）。"""
    if proc is None:
        return
    try:
        if proc.poll() is not None:
            return
    except Exception:
        pass
    if os.name == "nt":
        try:
            subprocess.call(["taskkill", "/F", "/T", "/PID", str(proc.pid)],
                            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=20)
        except Exception:
            pass
    else:
        try:
            os.killpg(os.getpgid(proc.pid), signal.SIGKILL)
        except Exception:
            pass
    try:
        proc.kill()
    except Exception:
        pass


def set_active_proc(proc):
    global ACTIVE_PROC
    ACTIVE_PROC = proc
    _ACTIVE_LOCAL.proc = proc
    if proc is not None and stop.requested():
        kill_tree(proc)


def get_active_proc():
    """本线程当前在跑的子进程（网页里每个会话只杀自己的）。"""
    return getattr(_ACTIVE_LOCAL, "proc", None)


class StopWatcher(object):
    """后台盯着键盘：运行中敲 /stop 回车、按 ESC、按 Ctrl+C 都能立刻中断。

    运行中敲的其它整行内容会被记住，本轮结束后当成下一句输入自动发出（打字不丢）。
    """

    def __init__(self):
        self._flag = threading.Event()
        self._reason = ""
        self._buf = ""
        self._listen = False
        self._dead = False
        self._lock = threading.Lock()
        self._resp = None
        self._typed = []
        self._thread = None
        self._prev_sigint = None
        self._script_plan = None
        self._keys_active = False
        self._stopped_turn = False
        self._stopped_reason = ""

    # ---- 查询 ----
    def requested(self):
        return self._flag.is_set()

    def was_stopped(self):
        """本轮（已经结束的那一轮）是不是被 /stop 中断的。

        run_turn 收尾时会把标志清掉，所以这里单独记一份，
        调用方想知道"上一轮被打断了没"要用这个。
        """
        return self._stopped_turn

    def reason(self):
        return self._reason or "用户中断"

    def take_typed(self):
        with self._lock:
            lines = self._typed[:]
            del self._typed[:]
        return lines

    def set_response(self, resp):
        self._resp = resp
        if self._flag.is_set():
            _close_response(resp)

    def clear_response(self, resp=None):
        if resp is None or self._resp is resp:
            self._resp = None

    # ---- 生命周期 ----
    def install(self, use_keys=True):
        """启动按键线程（Windows 控制台且 stdin 是终端才有意义）。"""
        if self._thread or not use_keys or msvcrt is None or not sys.stdin.isatty():
            return
        self._thread = threading.Thread(target=self._key_loop)
        self._thread.daemon = True
        self._thread.start()
        self._keys_active = True

    def begin(self, hint=True):
        """一轮开始：开门收键盘。"""
        self._flag.clear()
        self._reason = ""
        self._buf = ""
        self._stopped_turn = False
        with self._lock:
            del self._typed[:]
        self._listen = True
        self._install_sigint()
        if hint and self._keys_active:
            STATUS.log("(%s)" % HINT, color="dim")
        self._start_script()

    def end(self):
        """一轮结束：关门，并还原 Ctrl+C 行为。"""
        self._listen = False
        self._uninstall_sigint()
        self._stopped_turn = self._flag.is_set()      # 留给调用方判断"这轮是不是被中断的"
        self._stopped_reason = self._reason
        self._flag.clear()
        self._reason = ""
        self._buf = ""

    def pause(self):
        """让 input() 正常读键盘（确认 y/N 时用）。

        同时把 Ctrl+C 交还给 Python 默认行为（抛 KeyboardInterrupt），
        否则 input() 被信号"重试"机制卡住，回车之前 Ctrl+C 没反应。
        """
        self._listen = False
        self._buf = ""
        self._uninstall_sigint()

    def resume(self):
        if not self._dead:
            self._listen = True
            self._install_sigint()

    def trigger(self, reason):
        if self._flag.is_set():
            return
        self._reason = reason
        self._flag.set()
        self._note("[停止请求: %s] 正在中断当前操作……" % reason, "warn")
        _close_response(self._resp)
        kill_tree(ACTIVE_PROC)

    # ---- 键盘处理（纯逻辑，便于测试）----
    def handle_key(self, key):
        if isinstance(key, bytes):
            key = key.decode("gbk", "replace")
        if key == "\x03":
            self.trigger("Ctrl+C")
            return
        if key == "\x1b":
            self.trigger("ESC")
            return
        if key in ("\r", "\n"):
            line = self._buf.strip()
            self._buf = ""
            if not line:
                return
            if line.lower() in STOP_WORDS:
                self.trigger("/stop")
            else:
                with self._lock:
                    self._typed.append(line)
                self._note("[记下了] 本轮结束后自动发出: %s" % line)
            return
        if key in ("\b", "\x7f"):
            self._buf = self._buf[:-1]
            return
        if key == "\t":
            return
        self._buf += key

    def _note(self, msg, color="dim"):
        try:
            STATUS.log("\n" + msg, color=color)
        except Exception:
            pass

    def _key_loop(self):
        while not self._dead:
            try:
                if not self._listen or not msvcrt.kbhit():
                    time.sleep(0.03)
                    continue
                ch = msvcrt.getch()
            except Exception:
                time.sleep(0.15)
                continue
            if ch in (b"\xe0", b"\x00"):     # 方向键/功能键的第二字节，吃掉
                try:
                    msvcrt.getch()
                except Exception:
                    pass
                continue
            self.handle_key(ch)

    # ---- 按键脚本回放（--key-script，测试用）----
    def attach_script(self, path):
        plan = []
        try:
            raw = _read_text_tolerant(path)
        except Exception as exc:
            print("(按键脚本读不了: %s)" % exc)
            return
        for line in raw.splitlines():
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if ":" in line:
                a, _, b = line.partition(":")
                delay = _int_or(a.strip(), 0)
            else:
                delay, b = 0, line
            b = b.replace("\\r", "\r").replace("\\n", "\r").replace("\\x1b", "\x1b")
            if b and not b.endswith("\r"):
                b += "\r"
            plan.append((delay, b))
        self._script_plan = plan
        if plan:
            self._keys_active = True

    def _start_script(self):
        if not self._script_plan:
            return
        plan = list(self._script_plan)

        def run():
            for delay, text in plan:
                deadline = time.time() + max(0, delay) / 1000.0
                while time.time() < deadline and not self._dead:
                    time.sleep(0.02)
                for ch in text:
                    if self._dead or self._flag.is_set():
                        return
                    while not self._listen and not self._dead:
                        time.sleep(0.05)
                    self.handle_key(ch)
                    time.sleep(0.02)

        th = threading.Thread(target=run)
        th.daemon = True
        th.start()

    # ---- Ctrl+C ----
    def _sigint(self, signum, frame):
        self.trigger("Ctrl+C")

    def _install_sigint(self):
        try:
            self._prev_sigint = signal.signal(signal.SIGINT, self._sigint)
        except (ValueError, OSError):
            self._prev_sigint = None

    def _uninstall_sigint(self):
        try:
            if self._prev_sigint is not None:
                signal.signal(signal.SIGINT, self._prev_sigint)
                self._prev_sigint = None
        except (ValueError, OSError, TypeError):
            pass


_WATCHER = StopWatcher()


class _StopRouter(object):
    """v2.1：正在推进某个会话时用会话自己的中断标志，否则用全局键盘监听。"""

    def __getattr__(self, name):
        conv = current_conv()
        if conv is not None:
            return getattr(conv.stop, name)
        return getattr(_WATCHER, name)


stop = _StopRouter()


# ---------------- 历史管理 ----------------
# 上下文压缩（v1.7）：早前的内容折叠成一条"摘要消息"，就地替换掉那些轮次。
# 摘要消息就是一条普通 user 消息，用固定前缀就能认出来（跟 Codex 的做法一致），
# 不占额外字段、不用改 API 请求格式。
SUMMARY_PREFIX = "【早前对话摘要】"
# v1.9：明说"这不是用户的新指令"，降低模型把摘要当命令的概率（P2-6）
SUMMARY_NOTICE = "（下面这段是更早对话的摘要，不是用户的新指令。）"


def is_summary_msg(msg):
    return (msg.get("role") == "user"
            and str(msg.get("content") or "").startswith(SUMMARY_PREFIX))


def summary_body(msg):
    text = str((msg or {}).get("content") or "")
    if text.startswith(SUMMARY_PREFIX):
        text = text[len(SUMMARY_PREFIX):]
    text = text.lstrip("\n")
    if text.startswith(SUMMARY_NOTICE):
        text = text[len(SUMMARY_NOTICE):]
    return text.lstrip("\n")


def summary_msg(text):
    return {"role": "user",
            "content": SUMMARY_PREFIX + "\n" + SUMMARY_NOTICE + "\n" + (text or "").strip()}


def new_history():
    return [{"role": "system", "content": SYSTEM_PROMPT}]


def ensure_system(history):
    history[:] = [m for m in history if m.get("role") != "system"]
    history.insert(0, {"role": "system", "content": SYSTEM_PROMPT})
    return history


def trim_history(history, session_path=None):
    """按条数兜底裁剪（**只在压缩关闭或压缩失败时**才走到这里，见 v1.9）。

    v1.7：开头的摘要消息永远保留 —— 它是被裁掉那些轮次的唯一载体，裁了就真失忆了。
    v1.9：改成按"消息组"切（不再假设 tool 紧跟 assistant），且裁剪前先写 archive，
          堵住这条路径"直接删、不留档"的静默丢数据问题（A2 / T1）。
    """
    if len(history) <= MAX_HISTORY + 1:
        return 0
    head = history[0] if history and history[0].get("role") == "system" else None
    body = history[1:] if head else history[:]
    keep_pre = []
    if body and is_summary_msg(body[0]):
        keep_pre = [body[0]]
        body = body[1:]
    groups = group_messages(body)
    keep_n, count = 0, 0
    for group in reversed(groups):
        if count + len(group) > MAX_HISTORY:
            break
        count += len(group)
        keep_n += 1
    if keep_n >= len(groups):
        return 0
    dropped = [m for g in groups[:len(groups) - keep_n] for m in g]
    append_archive(session_path, dropped)
    history[:] = (([head] if head else []) + keep_pre
                  + [m for g in groups[len(groups) - keep_n:] for m in g])
    return len(dropped)


def sanity_check_history(history):
    known = set()
    for msg in history:
        if msg.get("role") == "assistant":
            for call in (msg.get("tool_calls") or []):
                if call.get("id"):
                    known.add(call["id"])
        elif msg.get("role") == "tool":
            if msg.get("tool_call_id") not in known:
                return False, "孤立 tool 消息: %s" % msg.get("tool_call_id")
    return True, "ok"


# ---------------- 路径 ----------------
def resolve_path(path, must_exist=False):
    if not path:
        path = "."
    if not os.path.isabs(path):
        path = os.path.join(WORKSPACE, path)
    full = os.path.abspath(path)
    try:
        inside = os.path.commonpath([full, WORKSPACE]) == WORKSPACE
    except ValueError:
        inside = False
    if must_exist and not os.path.exists(full):
        raise IOError("路径不存在: %s" % full)
    return full, inside


# ---------------- 工具 ----------------
MAX_READ_BYTES = 24 * 1024 * 1024       # 单次最多读这么多，防止超大日志把内存吃光


def t_read_file(args):
    full, _ = resolve_path(args.get("path", ""), must_exist=True)
    if os.path.abspath(full) == os.path.abspath(CONFIG_FILE):
        try:
            raw_cfg = _read_text_tolerant(full)
        except Exception:
            raw_cfg = ""
        masked = []
        for line in raw_cfg.splitlines():
            st = line.strip().lower()
            if st.startswith("api_key") and ("=" in line or ":" in line):
                head, _, val = line.partition("=" if "=" in line else ":")
                val = val.strip()
                masked.append("%s= %s" % (head, ("(已隐藏，%d 位)" % len(val)) if val else ""))
            else:
                masked.append(line)
        return "\n".join("%5d| %s" % (i + 1, t) for i, t in enumerate(masked))

    ext_doc = os.path.splitext(full)[1].lower()
    if ext_doc in DOC_EXTS:
        pages = args.get("pages")
        if isinstance(pages, (list, tuple)) and len(pages) == 2:
            pages = (int(pages[0]), int(pages[1]))
        else:
            pages = None
        try:
            text = _dt().doc_read(full, pages=pages)
        except Exception as exc:
            return ("读不了这个文档：%s\n（.doc/.xls/.ppt 是老格式，先用 run_cmd 调 "
                    "program\\doctools.py convert 转成新格式；扫描版 PDF 没有文字层）" % exc)
        if len(text) <= OUTPUT_CAP:
            return text
        # 太长：把全文导成 txt，让模型自己分页读（否则只能看到开头 6000 字）
        try:
            dump = full + ".txt"
            with open(dump, "w", encoding="utf-8", newline="\n") as fh:
                fh.write(text)
            hint = ("\n\n（文档太长：共 %d 字。全文已导出到 %s，用 read_file 带 start_line 分段读；"
                    "PDF 也可以直接用 pages=[起,止] 只读某几页）" % (len(text), dump))
        except OSError:
            hint = "\n\n（文档太长：共 %d 字，超过单次上限 %d 字）" % (len(text), OUTPUT_CAP)
        keep = max(500, OUTPUT_CAP - len(hint) - 8)
        return text[:keep] + hint
    start = max(1, _int_or(args.get("start_line"), 1))
    max_lines = max(1, _int_or(args.get("max_lines"), 200))
    size = os.path.getsize(full)
    with open(full, "rb") as fh:
        raw = fh.read(MAX_READ_BYTES)          # 只读到上限，不整文件进内存
    text, enc = decode_text_bytes(raw)
    lines = text.splitlines()
    seg = lines[start - 1:start - 1 + max_lines]
    if not seg:
        return "（文件共 %d 行，start_line=%d 已经超出范围）" % (len(lines), start)
    body = "\n".join("%5d| %s" % (start + i, line) for i, line in enumerate(seg))
    note = ""
    if size > MAX_READ_BYTES:
        note = "；文件 %.1f MB，只读了前 %.0f MB" % (size / 1048576.0,
                                                    MAX_READ_BYTES / 1048576.0)
    # v1.9（C1）：read_file 本来就分页，截断只留头部 —— 从中间截会让行号断层
    return _cap("%s\n(共 %d 行，本次显示 %d-%d 行，编码 %s%s；要接着读用 start_line=%d)"
                % (body, len(lines), start, start + len(seg) - 1, enc, note,
                   start + len(seg)), head_ratio=1.0)


# 这些文件是给"老系统 / Office / cmd"看的，按 ANSI(GBK) 写；其余按 UTF-8。
# （Python/JS/JSON 不能写 GBK，否则解释器会读错。）
ANSI_EXTS = (".bat", ".cmd", ".vbs", ".reg", ".txt", ".log", ".ini",
             ".cfg", ".csv", ".inf", ".url")


def t_write_file(args):
    full, _ = resolve_path(args.get("path", ""))
    content = args.get("content", "")
    mode = (args.get("mode") or "overwrite").lower()
    os.makedirs(os.path.dirname(full) or ".", exist_ok=True)
    if os.path.splitext(full)[1].lower() in (".docx", ".xlsx"):
        if mode == "append":
            return "（.docx/.xlsx 不能追加，这是二进制文档；要改内容请用 doctools 脚本）"
        try:
            return _dt().doc_write(full, content)
        except Exception as exc:
            return "生成失败：%s" % exc
    # v1.8：统一成 CRLF —— Win7 的老记事本不认纯 LF，会把整个文件显示成一行
    text = content.replace("\r\n", "\n").replace("\r", "\n")
    data = text.replace("\n", "\r\n") if os.name == "nt" else text
    # v1.9.1：给老系统看的文件按 GBK 写。
    #   cmd/regedit/Win7 记事本都按系统代码页(936)读，写 UTF-8 中文会乱码；
    #   GBK 表示不了的字符（emoji 等）退回 UTF-8 带 BOM，老记事本也认 BOM。
    enc = "utf-8"
    ext = os.path.splitext(full)[1].lower()
    if os.name == "nt" and ext in ANSI_EXTS:
        try:
            data.encode("gbk")
            enc = "gbk"
        except UnicodeEncodeError:
            enc = "utf-8-sig"
    with open(full, "a" if mode == "append" else "w", encoding=enc, newline="") as fh:
        fh.write(data)
    label = {"gbk": "GBK", "utf-8-sig": "UTF-8 BOM", "utf-8": "UTF-8"}[enc]
    return "%s 已写入 %d 字节（%s）: %s" % ("追加" if mode == "append" else "覆盖",
                                          len(data.encode(enc)), label, full)


def t_list_dir(args):
    full, _ = resolve_path(args.get("path", "."))
    if not os.path.isdir(full):
        raise IOError("不是目录: %s" % full)
    limit = max(1, _int_or(args.get("limit"), 300))
    names = sorted(os.listdir(full))
    rows = []
    for name in names[:limit]:
        p = os.path.join(full, name)
        try:
            if os.path.isdir(p):
                rows.append("[目录] %s/" % name)
            else:
                rows.append("[文件] %s  %d 字节" % (name, os.path.getsize(p)))
        except OSError:
            rows.append("[?] %s" % name)
    # v1.9（C2）：分页 + 明说被截断了，别让人以为目录就这么点
    tail = ""
    if len(names) > limit:
        tail = ("\n...(共 %d 项，只列前 %d 项；要看全部请分批，"
                "或用 search_text 定位)" % (len(names), limit))
    return _cap("\n".join(rows) + tail if rows else "(空目录)")


def t_search_text(args):
    pattern = args.get("pattern", "")
    if not pattern:
        raise ValueError("pattern 不能为空")
    root, _ = resolve_path(args.get("path", "."))
    try:
        rx = re.compile(pattern)
    except re.error as exc:
        raise ValueError("正则不合法: %s" % exc)
    hits = {}                       # 文件 -> [(行号, 原文)]，按文件分组（v1.9 / C5）
    total = 0
    MAX_HITS, MAX_FILES, PER_FILE = 120, 60, 20
    skip_dirs = SKIP_DIRS
    deadline = time.time() + SEARCH_TIMEOUT if SEARCH_TIMEOUT > 0 else None
    stop_note = ""
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in skip_dirs]
        for name in filenames:
            # v1.8：能被打断、也有时间上限 —— 以前一句全盘搜索能锁死几分钟且 /stop 无效
            if stop.requested():
                stop_note = "\n...(被 %s 中断，已搜到的结果在上面)" % stop.reason()
                break
            if deadline and time.time() > deadline:
                stop_note = ("\n...(已跑满 %d 秒，先停下；范围太大就换个目录再搜，"
                             "或把 config.txt 的 search_timeout 调大)" % SEARCH_TIMEOUT)
                break
            p = os.path.join(dirpath, name)
            try:
                if os.path.getsize(p) > 2_000_000:
                    continue
                with open(p, "rb") as fh:
                    raw = fh.read(2_000_000)
                text, _enc = decode_text_bytes(raw)
                rel = os.path.relpath(p, root)
                for i, line in enumerate(text.splitlines(), 1):
                    if rx.search(line):
                        hits.setdefault(rel, []).append((i, line.rstrip()[:200]))
                        total += 1
                        if total >= MAX_HITS:
                            stop_note += "\n...(命中超过 %d 处，已停)" % MAX_HITS
                            break
                if total >= MAX_HITS:
                    break
            except (IOError, OSError):
                continue
        if stop_note or total >= MAX_HITS:
            break
        if len(hits) >= MAX_FILES:
            stop_note += "\n...(命中文件超过 %d 个，已停)" % MAX_FILES
            break

    if not hits:
        return stop_note.strip() or "(没有匹配)"
    blocks = ["%d 个文件、%d 处命中：" % (len(hits), total)]
    for rel, rows in hits.items():
        blocks.append("")
        blocks.append("%s  (%d 处)" % (rel, len(rows)))
        for i, line in rows[:PER_FILE]:
            blocks.append("%6d| %s" % (i, line))
        if len(rows) > PER_FILE:
            blocks.append("      ...(这个文件还有 %d 处没显示)" % (len(rows) - PER_FILE))
    return _cap("\n".join(blocks) + stop_note)


class OutputBuf(object):
    """命令输出的兜底缓冲：一直读（不堵住管道），但只在限额内留着。

    v1.9（B3）：限额从 40 万降到 8 万 —— 反正最终只留 6000 字符（头 65% + 尾 35%），
    先攒 40 万再裁纯属白占内存和 CPU。
    """

    LIMIT = 80000

    def __init__(self):
        self._chunks = []
        self._n = 0
        self.total = 0

    def feed(self, data):
        self.total += len(data)
        if self._n < self.LIMIT:
            self._chunks.append(data)
            self._n += len(data)

    def text(self):
        return decode_output(b"".join(self._chunks))

    def tail(self, width=70):
        for chunk in reversed(self._chunks[-6:]):
            for line in reversed(decode_output(chunk).splitlines()):
                line = line.strip()
                if line:
                    return line[-width:]
        return ""


def t_run_cmd(args, deadline=None):
    cmd = args.get("command", "")
    if not cmd:
        raise ValueError("command 不能为空")
    cwd, _ = resolve_path(args.get("cwd", "."))
    if not os.path.isdir(cwd):
        cwd = WORKSPACE
    want = _int_or(args.get("timeout"), CMD_TIMEOUT)
    if want <= 0:
        want = CMD_TIMEOUT
    limit = min(want, CMD_TIMEOUT_MAX)
    # v1.9（B2 / E8）：把本轮剩余时间也算进来，否则 turn_timeout 拦不住正在跑的命令
    if deadline:
        remaining = deadline - time.time()
        if remaining <= 0:
            return ("（本轮剩余时间不足，这条命令没有执行；turn_timeout = %d 秒，可调大）"
                    % TURN_TIMEOUT)
        limit = max(1, min(limit, int(remaining)))

    popen_kw = {"cwd": cwd, "stdout": subprocess.PIPE, "stderr": subprocess.STDOUT,
                "stdin": subprocess.DEVNULL}       # stdin 空：不会被要交互输入的命令卡死
    if os.name != "nt":
        popen_kw["start_new_session"] = True
    try:
        proc = subprocess.Popen(cmd, shell=True, **popen_kw)
    except Exception as exc:
        return "命令启动失败: %s: %s" % (type(exc).__name__, exc)

    buf = OutputBuf()
    live = {"at": 0.0, "len": 0}
    live_conv = current_conv()          # 泵线程拿不到线程本地，启动前先抓住

    def push_live(force=False):
        """v2.0.1：网页模式下把命令输出边跑边推（每 0.25 秒最多一次）。

        全量解码累计缓冲、只发新增部分 —— 这样多字节字符被切开也不会乱码。
        """
        if UI is None:
            return
        now = time.time()
        if not force and now - live["at"] < 0.25:
            return
        live["at"] = now
        text = buf.text()
        if len(text) > live["len"]:
            extra = text[live["len"]:]
            live["len"] = len(text)
            if live_conv is not None:
                UI.emit_to(live_conv, "tool_output", text=extra, total=buf.total)
            else:
                ui_emit("tool_output", text=extra, total=buf.total)

    def pump():
        try:
            while True:
                chunk = proc.stdout.read(4096)
                if not chunk:
                    break
                buf.feed(chunk)
                push_live()
        except Exception:
            pass
        finally:
            push_live(force=True)
            try:
                proc.stdout.close()
            except Exception:
                pass

    reader = threading.Thread(target=pump)
    reader.daemon = True
    reader.start()
    set_active_proc(proc)

    start = time.time()
    note_at = start
    killed = None
    status_shown = False
    try:
        while True:
            if proc.poll() is not None:
                break
            if stop.requested():
                killed = "被 %s 中断" % stop.reason()
                break
            ran = time.time() - start
            if ran > limit:
                killed = "超时（超过 %d 秒）" % limit
                break
            time.sleep(0.15)
            now = time.time()
            if now - note_at >= 0.5 and now - start >= 1.0:
                note_at = now
                tail = buf.tail()
                STATUS.show("[%s] 跑命令 %.0fs / 上限 %ds · 收到 %.1fKB%s · 敲 /stop 可中断"
                            % (STATUS.tick(), now - start, limit, buf.total / 1024.0,
                               (" · 最后: " + tail) if tail else ""), color="dim")
                status_shown = True
    finally:
        if killed:
            kill_tree(proc)
        try:
            set_active_proc(None)
        except Exception:
            pass
    if status_shown:
        STATUS.end_line()
    reader.join(3.0)
    try:
        rc = proc.poll()
    except Exception:
        rc = None
    out = buf.text()
    if killed:
        head = "$ %s\n(进程%s；跑了 %.1fs，共收到 %d 字节输出，已连同子进程一起杀掉)" \
               % (cmd, killed, time.time() - start, buf.total)
    else:
        head = "$ %s\n(退出码 %s，用时 %.1fs，输出 %d 字节)" % (cmd, rc, time.time() - start, buf.total)
    return _cap(head + "\n" + (out or "(无输出)"))


# ---------------- 文档工具（v2.3，纯标准库） ----------------
DOC_EXTS = (".docx", ".doc", ".xlsx", ".xls", ".xlsm", ".pptx", ".ppt", ".pdf")


def _dt():
    """惰性导入同目录的 doctools。

    包里用的是嵌入式 Python，带 python38._pth 时 sys.path 不会自动加脚本目录，
    所以这里自己补一下，不能靠模块级 import。
    """
    import sys
    here = os.path.dirname(os.path.abspath(__file__))
    if here not in sys.path:
        sys.path.insert(0, here)
    import doctools
    return doctools


TOOLS = [
    {"type": "function", "function": {
        "name": "list_dir",
        "description": "列出目录内容。path 支持绝对路径（如 C:\\\\Users、D:\\\\、C:\\\\Windows）或相对默认目录的路径；"
                       "默认 . 表示默认目录。整机任意目录都能列",
        "parameters": {"type": "object", "properties": {"path": {"type": "string", "description": "目录路径，默认 ."}}}}},
    {"type": "function", "function": {
        "name": "read_file",
        "description": "读取文件（带行号）。文本按行显示；.docx/.xlsx/.pptx/.pdf 会自动解析成文字（PDF 只读文字层，扫描件没字）。老格式 .doc/.xls/.ppt 要先用 doctools 转。整机任意位置可读",
        "parameters": {"type": "object", "properties": {
            "path": {"type": "string", "description": "文件路径，绝对路径（C:\\\\... 或 D:\\\\...）或相对默认目录的路径"},
            "start_line": {"type": "integer", "description": "起始行，默认 1"},
            "max_lines": {"type": "integer", "description": "最多读多少行，默认 200"},
            "pages": {"type": "array", "items": {"type": "integer"},
                      "description": "只读 PDF 的第几页到第几页，如 [1, 5]；只对 .pdf 有效"}},
            "required": ["path"]}}},
    {"type": "function", "function": {
        "name": "write_file",
        "description": "写文件（覆盖或追加）。路径以 .docx/.xlsx 结尾时生成真正的 Office 文档，content 用 Markdown 写（标题/列表/表格/代码块/粗体）。整机任意位置可写",
        "parameters": {"type": "object", "properties": {
            "path": {"type": "string", "description": "文件路径，绝对路径或相对默认目录的路径"},
            "content": {"type": "string"},
            "mode": {"type": "string", "description": "overwrite（默认）或 append"}}, "required": ["path", "content"]}}},
    {"type": "function", "function": {
        "name": "search_text",
        "description": "在目录里按正则搜索文本，返回 文件:行号: 内容。传绝对路径就能搜整机",
        "parameters": {"type": "object", "properties": {
            "pattern": {"type": "string"},
            "path": {"type": "string", "description": "搜索根目录，绝对路径或相对默认目录；默认默认目录"}}, "required": ["pattern"]}}},
    {"type": "function", "function": {
        "name": "run_cmd",
        "description": "执行 shell 命令（Windows 上是 cmd.exe）。cwd 可指定任意绝对路径，命令本身也能操作整机任意位置。"
                       "注意：stdin 是空的，别用需要交互输入的命令；下载/长任务请自带超时参数；超时会连子进程一起被杀掉",
        "parameters": {"type": "object", "properties": {
            "command": {"type": "string"},
            "cwd": {"type": "string", "description": "工作目录，绝对路径或相对默认目录；默认默认目录"},
            "timeout": {"type": "integer", "description": "超时秒数，默认 %d，最多 %d" % (CMD_TIMEOUT, CMD_TIMEOUT_MAX)}},
            "required": ["command"]}}},
]

TOOL_FUNCS = {"list_dir": t_list_dir, "read_file": t_read_file, "write_file": t_write_file,
              "search_text": t_search_text, "run_cmd": t_run_cmd}
NEEDS_CONFIRM = {"write_file", "run_cmd"}

# v1.9（A4）：这些动作即使 auto_approve=on 也要再问一次 —— 一条命令就能毁机器的东西。
# 只看"命令位"（每段第一个词），不做全文关键词匹配 —— 否则 `echo format c:` 也会被拦。
DANGEROUS_HEADS = ("format", "diskpart", "bcdedit", "vssadmin", "wbadmin", "shutdown")
DANGEROUS_PATH = re.compile(
    r"^(?:[a-z]:\\(?:windows|program files|program files \(x86\)|programdata)(\\|$)"
    r"|\\\\|.*\\startup(\\|$))",
    re.I)
DANGEROUS_EXT = re.compile(r"\.(sys|dll|exe|drv|ocx|msi)$", re.I)
ROOT_OR_WILD = re.compile(r'^[a-z]:[\\/]?(\*.*)?$|\\\*$|^[a-z]:[\\/][^*]*\\\*$', re.I)


def _cmd_segments(cmd):
    """按 && || | & ; 粗切命令行（尊重引号），返回每段。够用即可。"""
    parts, buf, quote = [], [], None
    for ch in cmd:
        if ch in "\"'":
            quote = None if quote == ch else (ch if quote is None else quote)
            buf.append(ch)
            continue
        if quote is None and ch in "&|;\n":
            parts.append("".join(buf))
            buf = []
            continue
        buf.append(ch)
    parts.append("".join(buf))
    return [p.strip() for p in parts if p.strip()]


CMD_WRAPPERS = ("cmd", "start", "call", "powershell", "pwsh", "bash", "sh")


def _unwrap(seg):
    """剥掉 cmd /c、start /min、powershell -Command 这类外壳，看真正要执行的命令。

    v2.3.1：以前只看第一个词，`cmd /c format C: /y` 能整条绕过危险确认。
    """
    text = seg.strip()
    for _ in range(4):
        toks = text.lstrip("@").split()
        if not toks:
            return ""
        head = toks[0].strip('"').lower()
        base = head[:-4] if head.endswith(".exe") else head
        if base not in CMD_WRAPPERS:
            return text
        nxt = 1
        while nxt < len(toks):
            t = toks[nxt].strip('"').lower()
            if base == "cmd" and t in ("/c", "/k", "/r", "/s"):
                nxt += 1
                continue
            if base in ("powershell", "pwsh") and t in ("-command", "-c", "-e",
                                                        "-encodedcommand"):
                nxt += 1
                continue
            if t.startswith("/") or t.startswith("-"):
                nxt += 1
                continue
            break
        if nxt >= len(toks):
            return ""
        text = " ".join(toks[nxt:])
    return text


def danger_reason(name, args):
    """返回"为什么这次调用危险"的说明；安全则返回空串（v1.9 / A4）。

    判定原则：**只看命令位**（每段第一个词，剥掉 cmd/start/powershell 外壳）+ 关键参数。
    普通删除（del 文件、del /q 文件）不会触发；递归删除、盘符通配、分区/引导/注册表
    操作、擦除、强杀进程、递归删目录才会。
    """
    if not CONFIRM_DANGEROUS:
        return ""
    if name == "run_cmd":
        cmd = str(args.get("command") or "")
        for raw_seg in _cmd_segments(cmd):
            seg = _unwrap(raw_seg)
            if not seg:
                continue
            low = seg.lower()
            toks = low.split()
            if not toks:
                continue
            head = toks[0].lstrip("@").strip('"')
            if head.endswith(".exe") or head.endswith(".com"):
                head = head.rsplit(".", 1)[0]
            rest = toks[1:]
            if head in DANGEROUS_HEADS:
                return "命令里出现了 `%s`" % head
            if head == "cipher" and any(a == "/w" or a.startswith("/w:") for a in rest):
                return "cipher /w 会擦除磁盘空闲区"
            if head == "takeown" and "/f" in rest:
                return "takeown /f 会夺取文件所有权"
            if head == "icacls" and any(a in ("/grant", "/reset", "/setowner") for a in rest):
                return "icacls 会改文件权限/所有权"
            if head == "reg" and rest and rest[0] in ("delete", "add", "import"):
                return "reg %s 会直接改注册表" % rest[0]
            if head == "taskkill" and "/f" in rest and "/im" in rest:
                return "taskkill /f /im 会强杀一批进程"
            if head in ("del", "erase") and "/s" in rest:
                return "del /s 会递归删除"
            if head in ("rd", "rmdir") and "/s" in rest:
                return "rd /s 会递归删除目录"
            if head in ("del", "erase", "rd", "rmdir") and any(ROOT_OR_WILD.match(a) for a in rest):
                return "%s 直接指向盘符根或通配符" % head
            if head in ("del", "erase") and any(a in ("*", "*.*") for a in rest):
                return "%s *.* 会清空当前目录" % head
            if head in ("rm", "rmdir") and any(a in ("-r", "-rf", "-fr", "--recursive")
                                               for a in rest):
                return "%s -r 会递归删除" % head
            if head == "remove-item" and any(a in ("-recurse", "-r") for a in rest):
                return "Remove-Item -Recurse 会递归删除"
            if head in ("find", "xargs") and "rm" in low and "-delete" in low:
                return "find -delete 会批量删除"
        return ""
    if name == "write_file":
        raw = str(args.get("path") or "")
        try:
            full, _ = resolve_path(raw)
        except Exception:
            full = raw
        if DANGEROUS_EXT.search(full):
            return "要写的是可执行文件/系统文件（%s）" % os.path.basename(full)
        if DANGEROUS_PATH.match(os.path.abspath(full)):
            return "目标在系统目录或启动目录里（%s）" % full
        return ""
    return ""


def _outside_target(name, args):
    raw = args.get("cwd") if name == "run_cmd" else args.get("path")
    if not raw:
        return ""
    try:
        full, inside = resolve_path(raw)
    except Exception:
        return ""
    return "" if inside else full


def _ask_confirm(name, args, danger=""):
    """向用户确认一次；返回 True 表示执行（v1.9 抽出，危险动作也要走这里）。"""
    if UI is not None:                      # 网页终端：弹窗确认
        return UI.ask_confirm(name, args, danger)
    preview = json.dumps(args, ensure_ascii=False)
    if len(preview) > 400:
        preview = preview[:400] + " ..."
    outside = _outside_target(name, args)
    lines = []
    if danger:
        lines.append("[危险操作] %s" % danger)
    if outside:
        lines.append("[提示] 目标在默认目录之外（这是允许的，绝对路径本来就能动整机）: %s" % outside)
    lines.append("[需要你确认] %s" % name)
    lines.append("  %s" % preview)
    if not danger:
        lines.append("  （现在是在等你，不是卡住；以后不想被问：config.txt 里 auto_approve = on）")
    else:
        lines.append("  （这条即使开了 auto_approve 也会问一次；确认要执行就输 y）")
    lines.append("  （想放弃本轮：按 Ctrl+C）")
    STATUS.log("\n".join(lines), color="warn")
    stop.pause()
    try:
        answer = input("  执行? [y=执行 / 回车=跳过]: ").strip().lower()
    except EOFError:
        answer = ""
    except KeyboardInterrupt:
        STATUS.log("  (Ctrl+C)", color="dim")
        stop.resume()
        stop.trigger("Ctrl+C")
        return None
    finally:
        stop.resume()
    return answer in ("y", "yes", "是")


def exec_tool(name, args, auto_approve, deadline=None):
    func = TOOL_FUNCS.get(name)
    if func is None:
        return "未知工具: %s" % name
    danger = danger_reason(name, args)
    if name in NEEDS_CONFIRM:
        if auto_approve and not danger:
            # v1.9：自动同意也改用 warn 色 —— 做了事却用最不显眼的颜色不合适
            if name == "run_cmd":
                STATUS.log("  [自动同意] run_cmd: %s" % str(args.get("command", ""))[:200],
                           color="dim")
            else:
                STATUS.log("  [自动同意] %s -> %s" % (name, str(args.get("path", ""))[:200]),
                           color="dim")
        else:
            ok = _ask_confirm(name, args, danger)
            if ok is None:
                return "用户在确认时中断了本轮，%s 没有执行。" % name
            if not ok:
                return "用户拒绝了这次 %s 调用。" % name
    else:
        STATUS.show("[%s] 正在执行 %s ……" % (STATUS.tick(), name), color="dim")
    try:
        ui_emit("tool_call", name=name, args=args)
        if name == "run_cmd":
            out = _cap(str(func(args or {}, deadline=deadline)))
        else:
            out = _cap(str(func(args or {})))
        ui_emit("tool_result", name=name, output=out, summary=_result_head(out))
        return out
    except Exception as exc:
        msg = "工具执行出错: %s: %s" % (type(exc).__name__, exc)
        ui_emit("tool_result", name=name, output=msg, summary=msg)
        return msg


# ---------------- API（流式） ----------------
def _open_stream(req, started):
    """在后台线程里建连接，主线程每 0.2 秒回头看一眼有没有 /stop。

    直接 urlopen 会在"等模型第一个字节"时盲等（模型忙起来能等十几秒），
    那段时间敲 /stop 是没人理的 —— 所以放进线程，由主线程轮询。
    等待期间底部状态行会一直跳，看得出来是"在等"而不是"死了"。
    """
    box = {"note_at": 0.0}

    def worker():
        try:
            box["resp"] = urllib.request.urlopen(req, timeout=API_TIMEOUT)
        except Exception as exc:                 # noqa: BLE001 —— 原样抛回主线程
            box["err"] = exc
        if stop.requested() and box.get("resp") is not None:
            try:
                box["resp"].close()
            except Exception:
                pass

    th = threading.Thread(target=worker)
    th.daemon = True
    th.start()
    while th.is_alive():
        if stop.requested():
            raise Stopped(stop.reason())
        ran = time.time() - started
        if ran > API_TIMEOUT:
            raise TurnLimit("连接模型超时（%d 秒没有响应），已中断" % API_TIMEOUT)
        if ran - box["note_at"] >= 1.0:      # note_at 存的是相对秒数，别混绝对时间戳
            box["note_at"] = ran
            STATUS.show("[%s] 等待模型开始响应 %.0fs（%d 秒还没动静会自动断开）"
                        % (STATUS.tick(), ran, API_TIMEOUT), color="dim")
        th.join(0.2)
    if "err" in box:
        raise box["err"]
    return box.get("resp")


def api_stream(messages, model, thinking, use_tools):
    body = {"model": model, "messages": messages, "stream": True, "max_tokens": MAX_TOKENS}
    if not thinking and supports_reasoning_effort():
        body["reasoning_effort"] = "none"
    if use_tools:
        body["tools"] = TOOLS
        body["tool_choice"] = "auto"
    data = json.dumps(body, ensure_ascii=False).encode("utf-8")
    req = urllib.request.Request(
        API_BASE + "/chat/completions", data=data, method="POST",
        headers={"Content-Type": "application/json", "Authorization": "Bearer " + API_KEY})
    first_started = time.time()
    started = first_started
    # v1.8：429 / 5xx / 连接抖动自动重试两次（校园网最爱在接上时断一下）
    # v1.9：尊重 Retry-After；等待期间分段 sleep，/stop 立刻生效（B1 / E6）
    retry_codes = (429, 500, 502, 503, 504)
    resp, last_err = None, None
    for attempt in range(3):
        started = time.time()
        try:
            resp = _open_stream(req, started)
            if resp is None:
                raise RuntimeError("空的响应")
            break
        except urllib.error.HTTPError as exc:
            try:
                detail = _dec(exc.read())[:500]
            except Exception:
                detail = ""
            last_err = RuntimeError("HTTP %s: %s" % (exc.code, detail))
            if exc.code in retry_codes and attempt < 2 and not stop.requested():
                wait = retry_after_seconds(exc) or (1.5 * (attempt + 1))
                STATUS.log("  （服务端返回 %s，%.0f 秒后重试 %d/2）"
                           % (exc.code, wait, attempt + 1), color="warn")
                if not sleep_responsive(wait):
                    raise Stopped(stop.reason())
                continue
            raise last_err
        except socket.timeout:
            raise TurnLimit("连接模型超时（%d 秒没有响应），已中断" % API_TIMEOUT)
        except urllib.error.URLError as exc:
            last_err = RuntimeError("连不上 %s：%s" % (API_BASE, getattr(exc, "reason", exc)))
            if attempt < 2 and not stop.requested():
                wait = 1.5 * (attempt + 1)
                STATUS.log("  （网络没通，%.0f 秒后重试 %d/2）" % (wait, attempt + 1), color="warn")
                if not sleep_responsive(wait):
                    raise Stopped(stop.reason())
                continue
            raise last_err
    if resp is None and last_err is not None:
        raise last_err

    text_parts, calls = [], {}
    printed = False
    reasoning_len = 0
    finished = False
    stall_at = 0.0
    last_data = time.time()
    last_note = started

    def handle_line(line):
        """处理一行 SSE；返回 True 表示收到 [DONE]。"""
        nonlocal printed, reasoning_len
        line = line.strip()
        if not line or not line.startswith("data:"):
            return False
        payload = line[5:].strip().rstrip("\r")   # v1.9（E5）：别依赖 strip 的巧合
        if payload == "[DONE]":
            return True
        try:
            obj = json.loads(payload)
        except ValueError:
            return False
        if obj.get("error"):
            raise RuntimeError(str(obj["error"])[:500])
        choices = obj.get("choices") or []
        if not choices:
            return False
        delta = choices[0].get("delta") or {}
        think = delta.get("reasoning_content")
        if think:
            reasoning_len += len(think)
        piece = delta.get("content")
        if piece:
            if not printed and reasoning_len:
                STATUS.log("  （先思考了 %d 字）" % reasoning_len, color="think")
            text_parts.append(piece)
            STATUS.write(piece)          # 正文优先：先把状态行擦掉再吐字
            ui_emit("delta", text=piece)
            printed = True
        for tc in delta.get("tool_calls") or []:
            idx = tc.get("index", 0)
            slot = calls.setdefault(idx, {"id": "", "name": "", "args": ""})
            if tc.get("id"):
                slot["id"] = tc["id"]
            fn = tc.get("function") or {}
            if fn.get("name") and not slot["name"]:
                slot["name"] = fn["name"]
            if fn.get("arguments"):
                slot["args"] += fn["arguments"]
        return False

    sock = _find_socket(resp)
    buf = b""
    stop.set_response(resp)
    try:
        while True:
            now = time.time()
            if stop.requested():
                raise Stopped(stop.reason(), "".join(text_parts))
            if now - last_data > API_TIMEOUT:
                raise TurnLimit("模型 %d 秒没有返回数据，已中断" % API_TIMEOUT, "".join(text_parts))
            if not printed and now - last_note >= 1.5:
                last_note = now
                chars = sum(len(p) for p in text_parts)
                if reasoning_len and not chars:
                    detail = "思考中 %d 字（还没出正文）" % reasoning_len
                else:
                    detail = "已收 %d 字" % chars
                STATUS.show("[%s] 模型生成中 %.0fs · %s · 想停就敲 /stop"
                            % (STATUS.tick(), now - first_started, detail), color="dim")
            # 正文吐到一半时没法在行内刷状态（会糊掉回答），所以静默久了就另起一行报平安
            silent = now - last_data
            if printed and silent >= 5 and (stall_at == 0 or now - stall_at >= 10):
                stall_at = now
                STATUS.log("  ⟨模型还在生成，已经 %.0f 秒没有新内容了%s⟩"
                           % (silent,
                              "，%d 秒后会判超时断开" % API_TIMEOUT if silent > API_TIMEOUT - 30 else ""),
                           color="dim")
            # 每秒醒一次：这样模型卡住时也能立刻响应 /stop，且空闲超时是我们自己判的
            if sock is not None and sock.fileno() >= 0:
                try:
                    ready, _, _ = select.select([sock], [], [], STREAM_POLL)
                except Exception:
                    ready = [sock]
                if not ready:
                    continue
            try:
                chunk = resp.read1(65536)
            except socket.timeout:
                raise TurnLimit("模型 %d 秒没有返回数据，已中断" % API_TIMEOUT, "".join(text_parts))
            if not chunk:
                break
            last_data = time.time()
            stall_at = 0.0
            buf += chunk
            while b"\n" in buf:
                raw_line, _, buf = buf.partition(b"\n")
                if handle_line(_dec(raw_line)):
                    finished = True
                    break
            if finished:
                break
    except (ValueError, OSError):
        # 响应被中断线程掐掉 / socket 中途坏了
        if stop.requested():
            raise Stopped(stop.reason(), "".join(text_parts))
        if not text_parts and not calls:
            raise
    finally:
        stop.clear_response(resp)
        try:
            resp.close()
        except Exception:
            pass
    STATUS.end_line()        # 正文半行就补换行，状态行就擦掉
    return "".join(text_parts), [calls[k] for k in sorted(calls)]


def _tool_call_records(calls):
    out = []
    for i, c in enumerate(calls):
        out.append({"id": c["id"] or ("call_%d_%s" % (i, int(time.time()))),
                    "type": "function",
                    "function": {"name": c["name"], "arguments": c["args"] or "{}"}})
    return out


def _result_head(result, width=160):
    """屏幕上那一行 ↳ 的摘要：命令 + 状态行（超时/被杀/退出码/文件行数这类以 ( 开头）。"""
    lines = [ln for ln in (result or "").splitlines() if ln.strip()]
    if not lines:
        return ""
    head = lines[0][:90]
    for ln in lines[1:]:
        s = ln.strip()
        if s.startswith("("):
            return "%s | %s" % (head, s[:width])
    return head


def run_turn(history, model, thinking, use_tools, journal=None, session_path=None):
    """把这一轮的所有消息追加进 history 本体并返回最终文本。

    每条消息都通过 remember() 落盘（journal）—— 所以工具跑到一半被关窗口，
    已经发生的事还在会话文件里，下次 resume 能接上。

    开头先看上下文水位：超了就把最早几轮折叠成摘要（v1.7），再开始新一轮。

    被 /stop 或超时打断时，会把"已发出但没执行"的 tool_call 补上说明，
    保证历史里不会留孤立的 tool 消息（否则下一轮 API 会直接报错）。
    """
    started = time.time()
    deadline = started + TURN_TIMEOUT if TURN_TIMEOUT > 0 else None
    open_calls = []
    stop.begin()
    try:
        # v1.9：压缩挪进 try 里（原来在 stop.begin() 之前，压缩那几秒按 Ctrl+C 会直接
        # 抛 KeyboardInterrupt 把程序打死；现在会被当成正常中断处理）
        maybe_compact(history, model, session_path=session_path, journal=journal)
        for _round in range(TOOL_ROUNDS):
            if stop.requested():
                raise Stopped(stop.reason())
            if deadline and time.time() > deadline:
                raise TurnLimit("超过单轮时间上限 %d 秒" % TURN_TIMEOUT)
            text, calls = api_stream(history, model, thinking, use_tools)
            if not calls:
                if not str(text or "").strip():       # v1.9（A1）：空 assistant 有些 API 直接 400
                    text = "（模型这次返回了空内容，请再说一次或换个说法）"
                remember(history, {"role": "assistant", "content": text}, journal)
                return text
            tool_calls = _tool_call_records(calls)
            remember(history, {"role": "assistant", "content": text or None,
                               "tool_calls": tool_calls}, journal)
            open_calls = list(tool_calls)
            for idx, call in enumerate(tool_calls):
                name = call["function"]["name"]
                try:
                    args = json.loads(call["function"]["arguments"] or "{}")
                except ValueError:
                    args = {}
                if not isinstance(args, dict):
                    args = {}
                result = exec_tool(name, args, AUTO_APPROVE, deadline=deadline)
                STATUS.log("  ↳ %s: %s" % (name, _result_head(result)), color="tool")
                remember(history, {"role": "tool", "tool_call_id": call["id"],
                                   "content": result}, journal)
                open_calls = list(tool_calls[idx + 1:])
                if stop.requested():
                    raise Stopped(stop.reason())
                shrink_tool_outputs(history, session_path=session_path)  # 单轮内暴涨的第二道闸
            if deadline and time.time() > deadline:
                raise TurnLimit("超过单轮时间上限 %d 秒" % TURN_TIMEOUT)
        fallback = "(工具调用轮次过多（上限 %d 轮），已停止；要接着干就说一声)" % TOOL_ROUNDS
        STATUS.log("\n" + fallback, color="warn")
        remember(history, {"role": "assistant", "content": fallback}, journal)
        return fallback
    except (Stopped, TurnLimit) as exc:
        for call in open_calls:
            remember(history, {"role": "tool", "tool_call_id": call["id"],
                               "content": "（本轮被中断，这个调用没有执行）"}, journal)
        note = "（本轮被中断：%s）" % exc.reason
        partial = (exc.partial or "").strip()
        content = (partial + "\n\n" + note) if partial else note
        STATUS.log("\n" + note, color="warn")
        remember(history, {"role": "assistant", "content": content}, journal)
        return content
    finally:
        stop.end()
        STATUS.end_line()


# ---------------- 会话存取 ----------------
def new_session_file():
    if not os.path.isdir(SESSIONS):
        os.makedirs(SESSIONS)
    base = time.strftime("%Y%m%d-%H%M%S")
    path = os.path.join(SESSIONS, base + ".jsonl")
    n = 1
    while os.path.exists(path):      # 同一秒内开两次会话也不会互相覆盖
        n += 1
        path = os.path.join(SESSIONS, "%s-%d.jsonl" % (base, n))
    return path


def _record_of(msg):
    """内存消息 -> 落盘记录：摘要消息写成 __summary__ 记录（v1.7）。"""
    if is_summary_msg(msg):
        return {"role": "__summary__", "content": summary_body(msg)}
    return msg


def _write_records(path, records):
    """原子写：先写 .tmp 再替换，写到一半断电/被杀不会留下半个会话文件。"""
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as fh:
        for rec in records:
            fh.write(json.dumps(rec, ensure_ascii=False) + "\n")
    os.replace(tmp, path)


def save_session(path, history):
    """整文件重写（回合收尾 / 手动 /save / 压缩后 用）。

    不写 system 消息 —— 载入时会按当时的提示词重建一条，避免旧提示词混进新会话。
    """
    body = [m for m in history if m.get("role") != "system"]
    if not body:
        return                      # 一句话都没说过就别留空会话文件（历史列表会难看）
    _write_records(path, [_record_of(m) for m in body])


KEY_SHAPE = re.compile(r"sk-[A-Za-z0-9]{20,}")


def redact_secrets(text):
    """落盘/回显前把 key 抹掉（审计 P0-2：会话里不该留 key）。"""
    if not text:
        return text
    return KEY_SHAPE.sub("sk-***已抹掉***", text)


def append_message(path, msg):
    """把一条消息立刻追加进会话文件（v1.6）。

    为什么不再只靠回合结束时的整文件重写：工具跑到一半关窗口 / 任务管理器强杀，
    那一轮就全丢了 —— 用户看到的是"记录停在我上句话"。改成每条消息落一次盘，
    最坏情况也只丢"最后一条还没生成完"的内容。
    """
    if not path or not msg or msg.get("role") == "system":
        return
    try:
        with open(path, "a", encoding="utf-8") as fh:
            fh.write(json.dumps(_record_of(msg), ensure_ascii=False) + "\n")
    except (IOError, OSError):
        pass


def remember(history, msg, journal=None):
    """append 到内存历史，同时（如果给了 journal）落盘。所有消息都走这里。"""
    history.append(msg)
    if journal is not None:
        journal(msg)
    return msg


def append_archive(path, msgs):
    """把即将被折叠掉的原文追加到旁边的 .archive.jsonl（v1.7）。

    摘要必然有损，原文留在磁盘上，"忘了"就变成"去 archive 里搜"——
    agent 自己就能用 search_text 回捞，不需要向量库。

    v1.9：整批一次写 + flush（避免半截行），超过 context_archive_max_mb 就滚一份 .old。
    """
    if not CONTEXT_ARCHIVE or not path or not msgs:
        return ""
    dest = os.path.splitext(path)[0] + ".archive.jsonl"
    try:
        if (ARCHIVE_MAX_MB and os.path.exists(dest)
                and os.path.getsize(dest) > ARCHIVE_MAX_MB * 1048576):
            os.replace(dest, dest + ".old")
        blob = "".join(json.dumps(m, ensure_ascii=False) + "\n" for m in msgs)
        with open(dest, "a", encoding="utf-8") as fh:
            fh.write(blob)
            fh.flush()
            try:
                os.fsync(fh.fileno())
            except (OSError, ValueError):
                pass
        return dest
    except (IOError, OSError):
        return ""


def load_session(path):
    messages = []
    # utf-8-sig：记事本"另存为 UTF-8"会写 BOM，用 utf-8 读会把第一行当坏 JSON 丢掉
    with open(path, "r", encoding="utf-8-sig", errors="replace") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            try:
                rec = json.loads(line)
            except ValueError:
                continue                  # 写到一半被杀 -> 最后一行是半截 JSON，跳过
            role = rec.get("role")
            if role == "__summary__":
                messages.append(summary_msg(rec.get("content") or ""))
            elif role == "__archive__":
                continue
            elif role:
                messages.append(rec)
    return messages


def repair_history(history, journal=None, tail_note=None):
    """把"中途被关掉"留下的半截历史补成 API 能接受的样子（v1.6）。

    两种残缺：
      1) assistant 声明了 tool_calls，但 tool 结果没写进去就断了 -> 补一条"没拿到结果"
         （不补的话，下一次请求会因为孤立 tool_call 直接 400）
      2) 最后一条是 user（提问发出去了，回答还没开始/没写完）-> 补一条 assistant 说明
    返回补了几条，方便界面上提示一句。
    """
    fixed = 0
    answered = {}
    for msg in history:
        if msg.get("role") == "assistant":
            for call in (msg.get("tool_calls") or []):
                if call.get("id"):
                    answered[call["id"]] = False
        elif msg.get("role") == "tool":
            cid = msg.get("tool_call_id")
            if cid in answered:
                answered[cid] = True
    # v1.9：先删掉"id 根本不存在"的孤立 tool（手改会话 / 跨版本迁移会造出来）
    known = set(answered)
    if any(m.get("role") == "tool" and m.get("tool_call_id") not in known for m in history):
        cleaned = [m for m in history
                   if not (m.get("role") == "tool" and m.get("tool_call_id") not in known)]
        fixed += len(history) - len(cleaned)
        history[:] = cleaned
    for cid, done in answered.items():
        if not done:
            remember(history, {"role": "tool", "tool_call_id": cid,
                               "content": "（会话在这次工具调用执行期间被关闭，没有拿到结果；"
                                          "需要的话重新调用一次）"}, journal)
            fixed += 1
    if history and history[-1].get("role") == "user" and not is_summary_msg(history[-1]):
        remember(history, {"role": "assistant",
                           "content": tail_note or
                           "（上次会话在这里被关闭，这条提问没来得及回答）"}, journal)
        fixed += 1
    return fixed


def heal_history(history):
    """sanity_check 不过就修一把，返回补/删了几条（v1.9 的 A3）。

    以前只把"历史自检异常"打一行日志，不做任何事 —— 修不了就一直是坏的。
    """
    ok, _why = sanity_check_history(history)
    if ok:
        return 0
    return repair_history(history)


def resume_history(path):
    """载入会话：按当前提示词重建 system + 修补半截历史。返回 (history, 补了几条)。"""
    history = ensure_system(load_session(path))
    fixed = repair_history(history)
    fixed += heal_history(history)
    return history, fixed


# ---------------- 上下文压缩（v1.7） ----------------
# 把"最早的若干轮"折叠成一条摘要消息，就地替换掉它们。抄的三处：
#   Codex   —— 摘要就是一条带固定前缀的普通消息；只保留最近原文；就地重建历史
#   OpenHands —— 压到一半（滞回）；只在"消息组"边界切；摘要失败要能降级
#   LangMem —— 旧摘要 + 新内容 -> 新摘要，永远只有一份
SUMMARY_SYSTEM = (
    "你在压缩一段 agent 与用户的对话记录。只输出摘要，不要寒暄、不要解释你在做什么。\n"
    "必须保留：\n"
    "1) 用户的目标与约束（原话里明确说过的）\n"
    "2) 已做出的决定、结论\n"
    "3) 改动过 / 创建过的文件路径\n"
    "4) 尚未完成的事、下一步\n"
    "5) 用户偏好（语言、风格、忌讳）\n"
    "6) 关键事实（环境、配置、报错原文要点）\n"
    "丢弃：寒暄、重复的试错过程、已被推翻的方案。\n"
    "只写输入里确实出现过的内容，不要推测、不要替用户补充下一步；\n"
    "“尚未完成”只能写输入里明确说了没做成的。\n"
    "若输入里有【已有摘要】，把它的内容合并进新摘要，不要并列成两份。\n"
    "用中文，条目式，长度不超过 800 字。"
)


def _text_tokens(text):
    """粗估 token：中日韩字符按 1 个算，其余（英文/代码/日志）按 3.2 字符 1 个算。

    以前一律 len(text) 当 token，对工具输出（几乎全是 ASCII）低估约 3.5 倍，
    导致"预算还早着呢"其实早就超窗口了。stdlib 没有 tokenizer，这个近似够用。
    """
    if not text:
        return 0
    cjk = 0
    for ch in text:
        if ord(ch) > 0x2E7F:          # CJK、全角标点、假名等
            cjk += 1
    return int(cjk + (len(text) - cjk) / 3.2)


def message_tokens(msg):
    n = _text_tokens(str(msg.get("content") or ""))
    for call in (msg.get("tool_calls") or []):
        n += _text_tokens(str((call.get("function") or {}).get("arguments") or "")) + 6
    return n + 8


def estimate_tokens(messages):
    return sum(message_tokens(m) for m in messages)


# 兼容旧名字（v1.9 起单位是 token）
estimate_chars = estimate_tokens


def shrink_tool_outputs(history, keep_last=3, per_msg=1200, session_path=None):
    """单轮内工具输出暴涨时的第二道闸（v1.9 / P1-5）。

    一个回合里连读十个大文件，能从 50% 直接冲到 90%+，而压缩只在"每轮开始前"跑，
    这一轮已经带着旧历史发出去了。所以这里就地瘦身：
      **只改 content，不删消息、不动 tool_call_id** —— 配对依旧完整，不会 400。

    v1.9.1：截断前先把原文写进 archive（否则提示里"完整内容在归档"是句假话）。
    """
    if not CONTEXT_BUDGET:
        return 0
    if estimate_tokens(history) <= CONTEXT_BUDGET * 0.9:
        return 0
    idxs = [i for i, m in enumerate(history) if m.get("role") == "tool"]
    if len(idxs) <= keep_last:
        return 0
    victims = [(i, history[i]) for i in idxs[:-keep_last]
               if len(str(history[i].get("content") or "")) > per_msg]
    if not victims:
        return 0
    archived = append_archive(session_path, [m for _i, m in victims])
    note = ("\n（这条结果过长，已就地截断；完整内容在会话归档里，可用 search_text 查）"
            if archived else "\n（这条结果过长，已就地截断）")
    for i, msg in victims:
        history[i] = dict(msg, content=clip_text(str(msg.get("content") or ""), per_msg) + note)
    STATUS.log("  （本轮工具输出过多，已把 %d 条较早的结果就地截断%s）"
               % (len(victims), "（原文已归档）" if archived else ""), color="dim")
    return len(victims)


def group_messages(messages):
    """切成"不可分割的组"：一条 user / 一条 assistant / assistant(tool_calls)+它的全部 tool 结果。

    只在这个边界上删内容 —— 把工具调用和结果切开，下一轮请求必 400。
    """
    groups, i, n = [], 0, len(messages)
    while i < n:
        msg = messages[i]
        if msg.get("role") == "assistant" and msg.get("tool_calls"):
            ids = set(c.get("id") for c in msg["tool_calls"] if c.get("id"))
            j = i + 1
            while (j < n and messages[j].get("role") == "tool"
                   and messages[j].get("tool_call_id") in ids):
                j += 1
            groups.append(messages[i:j])
            i = j
        else:
            groups.append([msg])
            i += 1
    return groups


def clip_text(text, limit):
    """头 2/3 + 尾 1/3 截断（v1.9）。

    工具结果的关键信息几乎都在末尾（traceback 最后一行、退出码、结论段），
    只留开头等于把最该保留的丢掉。
    """
    if limit <= 0 or len(text) <= limit:
        return text
    head = limit * 2 // 3
    tail = limit - head
    return text[:head] + "\n…（中略）…\n" + text[-tail:]


def render_for_summary(groups, per_msg=2000, total=160000):
    """把待压缩的组渲染成给摘要模型看的纯文本：每条头尾截断、总长封顶。"""
    def build(limit):
        lines, names = [], {}
        for group in groups:
            for msg in group:
                role = msg.get("role")
                body = str(msg.get("content") or "").strip()
                if role == "assistant":
                    for call in (msg.get("tool_calls") or []):
                        fn = call.get("function") or {}
                        names[call.get("id")] = fn.get("name") or "?"
                        lines.append("[调用 %s] %s" % (fn.get("name") or "?",
                                                     clip_text(str(fn.get("arguments") or ""), 300)))
                    if body:
                        lines.append("[助手] " + clip_text(body, limit))
                elif role == "tool":
                    lines.append("[工具 %s 结果] %s"
                                 % (names.get(msg.get("tool_call_id"), "?"),
                                    clip_text(body, limit)))
                else:
                    lines.append("[用户] " + clip_text(body, limit))
        return "\n".join(lines)

    text = build(per_msg)
    if len(text) > total:                 # 太长就先压每条的长度（600 起步），再不行再掐
        text = build(max(600, per_msg // 2))
    if len(text) > total:
        text = clip_text(text, total)
    return text


def sleep_responsive(seconds):
    """分段 sleep，期间照样响应 /stop（v1.9）。返回 False 表示被中断。"""
    end = time.time() + max(0.0, seconds)
    while time.time() < end:
        if stop.requested():
            return False
        time.sleep(min(0.2, max(0.01, end - time.time())))
    return True


def retry_after_seconds(exc):
    """读 429 的 Retry-After（秒数或 HTTP 日期），读不到返回 0（v1.9 / B1）。"""
    try:
        raw = (exc.headers or {}).get("Retry-After")
    except Exception:
        return 0
    if not raw:
        return 0
    raw = str(raw).strip()
    if raw.isdigit():
        return min(float(raw), 60.0)
    try:
        from email.utils import parsedate_to_datetime
        when = parsedate_to_datetime(raw)
        return max(0.0, min(60.0, when.timestamp() - time.time()))
    except Exception:
        return 0


def supports_reasoning_effort():
    """reasoning_effort 是 DeepSeek 的字段；换别家 base 可能直接 400（v1.9）。"""
    try:
        host = API_BASE.split("//")[-1].split("/")[0].lower()
    except Exception:
        return False
    return "deepseek" in host


def api_complete(messages, model, max_tokens=1200):
    """非流式的一次调用（只给摘要用），复用 _open_stream 以支持 /stop 与超时。"""
    body = {"model": SUMMARY_MODEL or model, "messages": messages,
            "stream": False, "max_tokens": max_tokens}
    if supports_reasoning_effort():
        body["reasoning_effort"] = "none"
    data = json.dumps(body, ensure_ascii=False).encode("utf-8")
    req = urllib.request.Request(
        API_BASE + "/chat/completions", data=data, method="POST",
        headers={"Content-Type": "application/json", "Authorization": "Bearer " + API_KEY})
    resp = _open_stream(req, time.time())
    try:
        raw = resp.read()
    finally:
        try:
            resp.close()
        except Exception:
            pass
    obj = json.loads(_dec(raw))
    return str(((obj.get("choices") or [{}])[0].get("message") or {}).get("content") or "")


def compact_history(history, model, force=False, journal=None, session_path=None):
    """把最早的若干组折叠成一条摘要，就地替换。返回 (是否压了, 摘要字数)。

    切法： [system] [摘要?] [保留头部 keep_first 组] [被折叠的中间组] [保留尾部 keep_tail 组]
    """
    if not CONTEXT_BUDGET:
        return False, 0
    total = estimate_tokens(history)
    if not force and total <= CONTEXT_BUDGET * COMPACT_AT:
        return False, 0

    head = history[0] if history and history[0].get("role") == "system" else None
    rest = history[1:] if head else list(history)
    prev = ""
    if rest and is_summary_msg(rest[0]):
        prev = summary_body(rest[0])
        rest = rest[1:]
    groups = group_messages(rest)
    if len(groups) <= CONTEXT_KEEP_FIRST + CONTEXT_KEEP_TAIL:
        return False, 0

    keep_head = groups[:CONTEXT_KEEP_FIRST]
    target = CONTEXT_BUDGET * COMPACT_TO

    def size_from(cut_idx):
        return estimate_tokens([m for g in (keep_head + groups[cut_idx:]) for m in g])

    cut = max(CONTEXT_KEEP_FIRST, len(groups) - CONTEXT_KEEP_TAIL)
    while cut < len(groups) - 1 and size_from(cut) > target:
        cut += 1
    mid = [m for g in groups[CONTEXT_KEEP_FIRST:cut] for m in g]
    tail = groups[cut:]
    if not mid:
        return False, 0
    if len(mid) < 2 and not force:
        return False, 0          # 只压一条消息没意义（还容易把一问一答拆成两半），等它长大点

    STATUS.log("  （上下文已用 %.0f%%，正在把最早 %d 条折叠成摘要…）"
               % (100.0 * total / CONTEXT_BUDGET, len(mid)), color="dim")
    payload = ""
    if prev:
        payload += "【已有摘要】\n" + prev + "\n\n"
    payload += "【待压缩对话】\n" + render_for_summary(groups[CONTEXT_KEEP_FIRST:cut])

    text = ""
    for attempt in (1, 2):                       # v1.9：失败重试一次，再降级
        try:
            text = api_complete([{"role": "system", "content": SUMMARY_SYSTEM},
                                 {"role": "user", "content": payload}], model).strip()
        except (Stopped, TurnLimit) as exc:
            STATUS.log("  （压缩被中断：%s）" % getattr(exc, "reason", "中断"), color="warn")
            return False, 0
        except Exception as exc:
            if attempt == 1:
                STATUS.log("  （摘要调用失败：%s，1 秒后重试）"
                           % type(exc).__name__, color="warn")
                if not sleep_responsive(1.2):
                    return False, 0
                continue
            STATUS.log("  （摘要仍然失败：%s，改用归档降级）"
                       % type(exc).__name__, color="warn")
        if text:
            break

    if len(text) > SUMMARY_MAX_CHARS:            # v1.9：模型不听话时硬截断，别把空间吃回去
        text = clip_text(text, SUMMARY_MAX_CHARS)
        STATUS.log("  （摘要偏长，已截到 %d 字）" % SUMMARY_MAX_CHARS, color="dim")

    archive = append_archive(session_path, mid)
    if not text:
        # 降级措辞（v1.9）：原文是"折叠归档"，不是"删除"，模型别以为真没了
        text = "（摘要生成失败：最早 %d 条已折叠归档，不是删除" % len(mid)
        text += ("；原文见 %s，可用 search_text 查）" % os.path.basename(archive)
                 if archive else "；未开启归档）")
    if archive:
        text += "\n（更早的原始记录：%s，需要细节时可以用 search_text 查）" % os.path.basename(archive)
    history[:] = (([head] if head else []) + [summary_msg(text)]
                  + [m for g in (keep_head + tail) for m in g])
    if session_path:
        try:
            save_session(session_path, history)
        except (IOError, OSError):
            pass
    after = estimate_tokens(history)
    ratio = 100.0 * after / max(1, CONTEXT_BUDGET)
    note = ""
    if ratio > COMPACT_TO * 100 + 5:             # v1.9：没压到目标就说实话
        note = ("；未到目标 %.0f%%：尾部保留的内容本身太大，可调小 context_keep_tail"
                % (COMPACT_TO * 100))
    STATUS.log("  （已压缩 %d 条 -> 摘要 %d 字，现在约 %.0f%% 预算%s）"
               % (len(mid), len(text), ratio, note), color="dim")
    return True, len(text)


def maybe_compact(history, model, session_path=None, journal=None):
    """到水位才压（每轮开始前调一次）。任何异常都不该影响本轮对话。"""
    if not CONTEXT_BUDGET:
        return False
    try:
        if estimate_tokens(history) <= CONTEXT_BUDGET * COMPACT_AT:
            return False
        ok, _ = compact_history(history, model, journal=journal, session_path=session_path)
        return ok
    except Exception as exc:
        STATUS.log("  （压缩出错，跳过：%s）" % type(exc).__name__, color="warn")
        return False


def archive_size_text(session_path):
    if not session_path:
        return ""
    dest = os.path.splitext(session_path)[0] + ".archive.jsonl"
    try:
        if not os.path.exists(dest):
            return ""
        return "归档 %.1f MB" % (os.path.getsize(dest) / 1048576.0)
    except OSError:
        return ""


def print_transcript(history, max_msgs=12, per_msg=160, title=None):
    """把最近几轮整理成人能看的样子（v1.9：resume 回显 / /history 用）。

    以前 resume 只打印"共 N 条历史"，用户完全看不到上次聊了什么。
    """
    if title:
        STATUS.log(title, color="dim")
    msgs = [m for m in history if m.get("role") != "system"]
    if not msgs:
        STATUS.log("  (还没有对话内容)", color="dim")
        return
    picked = msgs if max_msgs is None else msgs[-max_msgs:]
    if max_msgs is None and len(picked) > 200:
        picked = picked[-200:]
        STATUS.log("  …（只显示最后 200 条）", color="dim")
    if len(msgs) > len(picked):
        STATUS.log("  …（更早的 %d 条已省略，/history all 看全部）"
                   % (len(msgs) - len(picked)), color="dim")
    for msg in picked:
        role = msg.get("role")
        if role == "tool":
            continue
        if is_summary_msg(msg):
            body = " ".join(summary_body(msg).split())
            STATUS.log("  【早前摘要】" + (body[:200] + "…" if len(body) > 200 else body),
                       color="think")
            continue
        text = " ".join(str(msg.get("content") or "").split())
        if not text:
            continue
        if len(text) > per_msg:
            text = text[:per_msg] + "…"
        STATUS.log(("  你> " + text) if role == "user" else ("  助手> " + text),
                   color="user" if role == "user" else None)


def context_report(history, session_path=None):
    used = estimate_tokens(history)
    summary_len = 0
    for msg in history[1:]:                      # v1.9：全扫，不再假设摘要在第 2 条
        if is_summary_msg(msg):
            summary_len = len(summary_body(msg))
            break
    pct = (100.0 * used / CONTEXT_BUDGET) if CONTEXT_BUDGET else 0.0
    if CONTEXT_BUDGET:
        head = ("上下文: 约 %d token / 预算 %d（%.0f%%，到 %.0f%% 触发压缩）"
                % (used, CONTEXT_BUDGET, pct, COMPACT_AT * 100))
    else:
        head = "上下文: 约 %d token（压缩已关闭，context_budget=0）" % used
    line = ("%s · 消息 %d 条 · 尾部保留 %d 组 · 摘要 %d 字"
            % (head, len(history), CONTEXT_KEEP_TAIL, summary_len))
    arch = archive_size_text(session_path)
    return line + ((" · " + arch) if arch else "")


_SESSION_ITEM_CACHE = {}
_SESSION_ITEM_LOCK = threading.Lock()
TITLE_PROMPT = (
    "给下面这段对话起一个标题，要求：\n"
    "- 不超过 12 个汉字（或 20 个字符）\n"
    "- 概括用户想做的事，不要照抄原句\n"
    "- 只输出标题本身：不要引号、不要句号、不要“标题：”这样的前缀\n"
)


def title_path(session_path):
    return os.path.splitext(session_path)[0] + ".title"


def read_title(session_path):
    try:
        with open(title_path(session_path), "r", encoding="utf-8") as fh:
            return fh.read().strip()
    except (IOError, OSError):
        return ""


def default_display_name(name):
    """没起标题时用什么当标题：时间戳文件名 -> 时间；改过名的 -> 名字本身。"""
    base = name[:-6] if str(name).endswith(".jsonl") else str(name)
    m = re.match(r"^(\d{4})(\d{2})(\d{2})-(\d{2})(\d{2})(\d{2})(-\d+)?$", base)
    if m:
        return "%s-%s-%s %s:%s" % (m.group(1), m.group(2), m.group(3), m.group(4), m.group(5))
    return base


def ensure_title(session_path, history, model=None, force=False):
    """给会话生成一个短标题（只在第一次成功对话后跑一次）。

    v2.0.3：不再拿用户第一句话当标题 —— 那是"他说了什么"，不是"这件事叫什么"。
    标题存在 <会话名>.title 里，和 jsonl 分开，重写会话文件也不会丢。
    """
    if not session_path:
        return ""
    tp = title_path(session_path)
    if os.path.exists(tp) and not force:
        return read_title(session_path)
    msgs = [m for m in history if m.get("role") in ("user", "assistant") and m.get("content")]
    if len(msgs) < 2:
        return ""
    sample = ""
    for m in msgs[:6]:
        who = "用户" if m.get("role") == "user" else "助手"
        sample += "%s：%s\n" % (who, clip_text(str(m["content"]), 300))
    try:
        title = api_complete([{"role": "system", "content": TITLE_PROMPT},
                              {"role": "user", "content": sample}],
                             model or "", max_tokens=48).strip()
    except Exception:
        return ""
    title = " ".join(title.strip().strip("《》\"'“”‘’。.,， \n").split())
    if not title:
        return ""
    if len(title) > 24:
        title = title[:24]
    try:
        with open(tp, "w", encoding="utf-8", newline="\n") as fh:
            fh.write(title)
    except (IOError, OSError):
        return ""
    _SESSION_ITEM_CACHE.pop(session_path, None)
    return title


def _scan_session_file(path):
    """只扫一遍，不做全量 JSON 解析（v2.0.1：会话多了以后每次列目录都卡）。

    返回 (first, msgs, turns)；文件读不了返回 None。
    """
    first, msgs, turns = "", 0, 0
    try:
        with open(path, "r", encoding="utf-8-sig", errors="replace") as fh:
            for line in fh:
                if not line.strip():
                    continue
                msgs += 1
                head = line[:64]
                if not first and re.search(r'"role"\s*:\s*"user"', head):
                    try:
                        obj = json.loads(line)
                    except ValueError:
                        continue
                    body = obj.get("content")
                    if body and not str(body).startswith(SUMMARY_PREFIX):
                        first = str(body).replace("\n", " ").strip()[:42]
                elif re.search(r'"role"\s*:\s*"assistant"', head):
                    turns += 1
    except (IOError, OSError):
        return None
    return first, msgs, turns


def session_items():
    """历史会话列表（按修改时间倒序）。

    v2.0.1 三处修正：
      * 不再把 *.archive.jsonl 当成会话（以前它们会出现在 resume 列表里，
        而且每次刷新都要被完整解析一遍 —— 对话越长越卡）
      * 不再 json.loads 每一行，只按行首判角色
      * 按 (mtime, size) 缓存，网页每 2 秒拉一次列表也不重复扫盘
    """
    items = []
    if not os.path.isdir(SESSIONS):
        return items
    alive = set()
    for name in os.listdir(SESSIONS):
        if not name.endswith(".jsonl") or ".archive." in name or name.endswith(".old"):
            continue
        path = os.path.join(SESSIONS, name)
        try:
            st = os.stat(path)
        except (IOError, OSError):
            continue
        alive.add(path)
        key = (st.st_mtime, st.st_size)
        with _SESSION_ITEM_LOCK:
            hit = _SESSION_ITEM_CACHE.get(path)
        if hit and hit[0] == key:
            item = dict(hit[1])
        else:
            scanned = _scan_session_file(path)
            if scanned is None:
                continue
            first, msgs, turns = scanned
            item = {"path": path, "name": name, "msgs": msgs, "turns": turns,
                    "first": first, "mtime": st.st_mtime}
            with _SESSION_ITEM_LOCK:
                _SESSION_ITEM_CACHE[path] = (key, item)
            item = dict(item)
        item["title"] = read_title(path) or default_display_name(name)
        items.append(item)
    with _SESSION_ITEM_LOCK:
        for gone in [p for p in list(_SESSION_ITEM_CACHE) if p not in alive]:
            _SESSION_ITEM_CACHE.pop(gone, None)
    items.sort(key=lambda x: x["mtime"], reverse=True)
    return items


def latest_session():
    items = session_items()
    return items[0]["path"] if items else None


def print_sessions():
    items = session_items()
    if not items:
        print("还没有任何历史会话。")
        return items
    print("可继续的历史会话（按时间倒序，最近的在前）：")
    for i, it in enumerate(items, 1):
        print("  %2d) %s   %d 条 · %d 轮  「%s」"
              % (i, time.strftime("%Y-%m-%d %H:%M", time.localtime(it["mtime"])),
                 it["msgs"], it["turns"], it["first"] or "(无提问)"))
    print("共 %d 个。用编号继续（双击 resume.cmd 也行）。" % len(items))
    return items


# ---------------- 交互 ----------------
# v2.0.1：原来只要回答里出现"无法访问""只能在"这类词就弹提示，正常句子也会误报。
# 现在要求是"第一人称 + 明确说自己被限制"，才认为它把自己的能力说错了。
CONFINED_PATTERNS = (
    r"我(只能|只可以|仅能)(在|访问|操作).{0,16}(工作区|默认目录|workspace)",
    r"(我|这里)(无法|不能|没法|没有权限)(访问|读取|打开|操作).{0,12}"
    r"(工作区|默认目录|workspace|C:|D:|整机|外面的)",
    r"(超出|不在)(了)?(我的)?(访问)?(范围|工作区|默认目录)",
    r"需要你(先|把).{0,12}(文件|资料|东西).{0,8}(放到|放进|拷到|移到)(工作区|默认目录)",
)


def _warn_if_confined(text):
    """agent 又自称只能在小圈子里干活时，现场把话术塞给用户。"""
    if not text:
        return
    for pat in CONFINED_PATTERNS:
        m = re.search(pat, text)
        if m:
            STATUS.log("(提示：它说的「%s」是它自己搞错了 —— 它没有沙箱，整机都能读写。"
                       "直接回它一句： 用绝对路径 list_dir(\"C:\\\\\") 看整机 )"
                       % m.group(0)[:20], color="warn")
            return


def input_prompt(text):
    """打印提示符并读一行（提示符尽量上色；win32 模式下输入的字也会跟着是那个色）。"""
    if COLOR_ON and not COLOR_VT and COLOR_HANDLE:
        _win32_set(_palette_of("user")[1])
        try:
            return input(text)
        finally:
            _win32_set(None)
    return input(paint(text, "user"))


def interactive(model, thinking, use_tools, session_file, history):
    global AUTO_APPROVE
    # 每产生一条消息就落盘（session_file 变量在 /new 时会被改，闭包跟着走新文件）
    journal = lambda msg: append_message(session_file, msg)
    STATUS.log("ember v%s  %s" % (VERSION, config_summary(model, thinking, use_tools)),
               color="tool")
    STATUS.log("默认目录: %s" % WORKSPACE, color="dim")
    if ENV_PROBED:      # 只在换机器/换目录后的第一次启动时提示一句
        STATUS.log(env_notice(), color="dim")
    if AUTO_APPROVE:
        STATUS.log("⚠️  已开启自动同意：agent 写文件/执行命令都不会再问你（改 config.txt 可关）",
                   color="warn")
    STATUS.log("直接说需求即可；运行中敲 /stop（或 ESC / Ctrl+C）可中断；/help 看命令，/exit 退出。\n",
               color="dim")
    pending = []
    last_ctrlc = 0.0
    while True:
        if pending:
            user = pending.pop(0).strip()
            STATUS.log("你> %s" % user, color="user")
        else:
            try:
                user = input_prompt("你> ").strip()
            except KeyboardInterrupt:
                now = time.time()
                if now - last_ctrlc < 3:
                    print()
                    break
                last_ctrlc = now
                STATUS.log("(想退出：3 秒内再按一次 Ctrl+C，或输入 /exit)", color="dim")
                continue
            except EOFError:
                print()
                break
        if not user:
            continue
        if user in ("/exit", "/quit", "exit", "quit"):
            break
        if user in ("/stop", "/abort"):
            STATUS.log("(现在没有在运行的任务；运行中敲 /stop 才会中断)", color="dim")
            continue
        if user == "/help":
            STATUS.log("/new 新会话  /model <名>  /tools on|off  /think on|off  /approve on|off\n"
                       "/compact 立刻把早前内容压成摘要  /context 看上下文用量\n"
                       "/history 看最近 20 条对话（/history all 看全部）\n"
                       "/stop 中断正在跑的回答/命令（运行中敲 ESC 或 Ctrl+C 也一样）\n"
                       "/prompt 看当前提示词  /prompt reload 重读 prompt.txt  /config 配置  "
                       "/history 历史  /save  /exit", color="dim")
            continue
        if user == "/context":
            STATUS.log(context_report(history, session_path=session_file), color="dim")
            continue
        if user == "/compact":
            ok, n = compact_history(history, model, force=True,
                                    journal=journal, session_path=session_file)
            if ok:
                STATUS.log("(已压缩：摘要 %d 字，接着聊就行)" % n, color="dim")
            else:
                STATUS.log("(还压不了：要么内容不多，要么轮次太少/压缩被关掉了)", color="dim")
            continue
        if user.startswith("/prompt"):
            if user.endswith("reload"):
                refresh_prompt()
                STATUS.log("(已重新读取 %s；来源：%s，共 %d 字)"
                           % (PROMPT_FILE, PROMPT_SOURCE, len(SYSTEM_PROMPT)), color="dim")
                ensure_system(history)
            else:
                STATUS.log("提示词来源: %s\n文件: %s\n---- 8< ----\n%s\n---- 8< ----"
                           % (PROMPT_SOURCE, PROMPT_FILE, SYSTEM_PROMPT), color="dim")
            continue
        if user == "/config":
            STATUS.log("配置文件: %s" % CONFIG_FILE, color="dim")
            STATUS.log(config_summary(model, thinking, use_tools), color="dim")
            continue
        if user.startswith("/history"):
            show_all = user.split()[-1].lower() == "all"
            tools = sum(1 for m in history if m.get("role") == "tool")
            STATUS.log("(历史 %d 条，上限 %d；另有工具结果 %d 条，只显示对话)"
                       % (len(history), MAX_HISTORY, tools), color="dim")
            print_transcript(history, max_msgs=None if show_all else 20,
                             per_msg=200 if show_all else 160)
            continue
        if user == "/new":
            history[:] = new_history()
            session_file = new_session_file()
            STATUS.log("(已开新会话)", color="dim")
            continue
        if user.startswith("/model"):
            parts = user.split()
            model = parts[1] if len(parts) > 1 else model
            STATUS.log("(模型 %s)" % model, color="dim")
            continue
        if user.startswith("/tools"):
            use_tools = not user.endswith("off")
            STATUS.log("(工具 %s)" % ("开" if use_tools else "关"), color="dim")
            continue
        if user.startswith("/think"):
            thinking = not user.endswith("off")
            STATUS.log("(思考 %s)" % ("开" if thinking else "关"), color="dim")
            continue
        if user.startswith("/approve"):
            AUTO_APPROVE = not user.endswith("off")
            STATUS.log("(自动同意 %s；想永久生效改 config.txt 里的 auto_approve)"
                       % ("开 —— 不再逐条确认" if AUTO_APPROVE else "关"), color="dim")
            continue
        if user == "/save":
            save_session(session_file, history)
            STATUS.log("(已保存 %s)" % os.path.basename(session_file), color="dim")
            continue

        mark = len(history)
        remember(history, {"role": "user", "content": user}, journal)
        t0 = time.time()
        tools_used = 0
        try:
            run_turn(history, model, thinking, use_tools, journal=journal,
                     session_path=session_file)
        except Exception as exc:
            # 不再 del history[mark:] 把这句话丢掉：用户说的每个字都已经落盘了。
            # 先补齐半截的 tool_call，再补一句"这轮出错了"，历史保持合法。
            STATUS.log("\n[出错] %s" % exc, color="error")
            repair_history(history, journal=journal,
                           tail_note="（本轮出错，这条提问没有得到回答：%s）" % exc)
            save_session(session_file, history)
            continue
        used = time.time() - t0
        tools_used = sum(1 for m in history[mark:] if m.get("role") == "tool")
        interrupted = stop.was_stopped()
        if interrupted:
            STATUS.log("(已按你的要求中断 —— 接着说要做什么就行)", color="warn")
        else:
            _warn_if_confined(history[-1].get("content") or "")
        # 每轮结束打一条分界线：好找"这次回答到哪儿为止"
        parts = []
        if interrupted:
            parts.append("已中断")
        parts.append("%.1fs" % used)
        if tools_used:
            parts.append("工具 %d 次" % tools_used)
        line = separator_line(" · ".join(parts))
        if line is not None:
            STATUS.log(line, color="dim")
        pending = stop.take_typed() + pending
        # v1.9（T1）：压缩开着就别再按条数删 —— 那是另一套"删了不留档"的机制，
        # 会和刚压好的摘要打架。只有压缩关掉（或这轮压失败）时才走条数兜底。
        dropped = 0
        if not CONTEXT_BUDGET:
            dropped = trim_history(history, session_path=session_file)
            if dropped:
                STATUS.log("(压缩已关闭：按条数上限裁掉最旧 %d 条，%s)"
                           % (dropped, "原文已进归档" if CONTEXT_ARCHIVE else "原文未存档"),
                           color="warn")
        ok, why = sanity_check_history(history)
        if not ok:
            fixed = heal_history(history)
            STATUS.log("(历史自检异常（%s），已修 %d 条)" % (why, fixed), color="warn")
        save_session(session_file, history)
        # v2.0.3：第一次成功对话后，后台起个标题（不挡下一句）
        if not read_title(session_file):
            threading.Thread(target=ensure_title,
                             args=(session_file, list(history), model),
                             daemon=True).start()
    save_session(session_file, history)
    STATUS.log("(会话已保存: %s)" % os.path.basename(session_file), color="dim")


# ---------------- 网页终端（v2.1：多会话并行） ----------------
# 纯标准库 http.server + 事件轮询，不引入任何依赖、不需要联网装包。
# 每个会话有自己的历史、事件队列、中断标志；几个会话可以同时各跑一轮。
WEB_HTML = os.path.join(HERE, "webui.html")
UI = None
WEB_TOKEN = ""
_CONV_LOCAL = threading.local()


def current_conv():
    """当前线程正在推进的会话（cmd 模式下是 None）。"""
    return getattr(_CONV_LOCAL, "conv", None)


class ConvStop(object):
    """网页里每个会话自己的中断标志：不碰键盘、不装信号。"""

    def __init__(self):
        self._ev = threading.Event()
        self._stopped = False
        self._reason = ""
        self._resp = None

    def begin(self, hint=False):
        self._ev.clear()
        self._stopped = False
        self._reason = ""

    def end(self):
        self._stopped = self._ev.is_set()
        self._ev.clear()

    def requested(self):
        return self._ev.is_set()

    def was_stopped(self):
        return self._stopped

    def reason(self):
        return self._reason or "用户中断"

    def trigger(self, reason):
        if self._ev.is_set():
            return
        self._reason = reason
        self._ev.set()
        _close_response(self._resp)          # 先掐掉正在读的流
        proc = get_active_proc()
        if proc is not None:
            kill_tree(proc)

    def set_response(self, resp):
        self._resp = resp
        if self._ev.is_set():
            _close_response(resp)

    def clear_response(self, resp=None):
        if resp is None or self._resp is resp:
            self._resp = None

    # 键盘 / 信号相关：网页里没有，留空实现让调用方不用分支
    def install(self, use_keys=False):
        pass

    def pause(self):
        pass

    def resume(self):
        pass

    def take_typed(self):
        return []

    def attach_script(self, plan):
        return None


class Conv(object):
    """一个会话在网页进程里的运行时状态。"""

    def __init__(self, name, path):
        self.name = name
        self.path = path
        self.history = None
        self.busy = False
        self.unread = False
        self.events = []
        self.seq = 0
        self.lock = threading.RLock()
        self.stop = ConvStop()
        self.confirm = {"id": 0, "ev": None, "answer": False}


def ui_emit(kind, **kw):
    """往"当前会话"推一条事件；不是 web 模式时什么也不做。"""
    if UI is None:
        return
    try:
        UI.emit(kind, **kw)
    except Exception:
        pass


class WebUI(object):
    def __init__(self):
        self.lock = threading.RLock()
        self.convs = {}
        self.active = ""
        self.model = ""
        self.thinking = False
        self.use_tools = True

    # ---- 会话对象 ----
    def conv(self, name, create=False):
        name = os.path.basename(str(name or ""))
        with self.lock:
            c = self.convs.get(name)
            if c is None and create and name:
                c = Conv(name, os.path.join(SESSIONS, name))
                self.convs[name] = c
            return c

    def drop(self, name):
        with self.lock:
            self.convs.pop(os.path.basename(str(name or "")), None)

    # ---- 事件 ----
    def emit_to(self, conv, kind, **kw):
        if conv is None:
            return
        with conv.lock:
            conv.seq += 1
            ev = dict(kw)
            ev["seq"] = conv.seq
            ev["kind"] = kind
            conv.events.append(ev)
            if len(conv.events) > 4000:      # 长会话别把内存堆爆
                del conv.events[:2000]

    def emit(self, kind, **kw):
        conv = current_conv() or self.conv(self.active)
        self.emit_to(conv, kind, **kw)

    def since(self, conv, n):
        with conv.lock:
            return [e for e in conv.events if e["seq"] > n]

    # ---- 打开 / 新建 ----
    def open(self, name):
        name = os.path.basename(str(name or ""))
        path = os.path.join(SESSIONS, name)
        known = self.convs.get(name)
        if not name.endswith(".jsonl") or (not os.path.exists(path) and known is None):
            return None
        conv = self.conv(name, create=True)
        with conv.lock:
            if conv.history is None:
                conv.history = ensure_system(load_session(path))
                repair_history(conv.history)
            conv.unread = False
        self.active = name
        return conv

    def new(self):
        name = os.path.basename(new_session_file())
        path = os.path.join(SESSIONS, name)
        conv = Conv(name, path)
        conv.history = new_history()
        try:                                  # v2.3.1：立刻落一个合法文件，否则 open 会 404
            save_session(path, conv.history)
        except Exception:
            pass
        with self.lock:
            self.convs[name] = conv
        self.active = name
        return conv

    # ---- 跑一轮 ----
    def start_chat(self, text, name=None):
        name = name or self.active
        conv = self.conv(name)
        if conv is None:
            return False, "找不到会话"
        with conv.lock:
            if conv.busy:
                return False, "这个会话上一轮还没结束"
            conv.busy = True
        th = threading.Thread(target=self._worker, args=(conv, text))
        th.daemon = True
        th.start()
        return True, ""

    def _worker(self, conv, text):
        _CONV_LOCAL.conv = conv
        journal = lambda m: append_message(conv.path, m)
        try:
            if conv.history is None:
                conv.history = new_history()
            remember(conv.history, {"role": "user", "content": text}, journal)
            self.emit_to(conv, "user", text=text)
            mark = len(conv.history)
            t0 = time.time()
            # v2.3.1：begin/end 交给 run_turn 管；这里再 end 一次会把 was_stopped 覆盖成 False
            run_turn(conv.history, self.model, self.thinking, self.use_tools,
                     journal=journal, session_path=conv.path)
            tools = sum(1 for m in conv.history[mark:] if m.get("role") == "tool")
            stopped = bool(getattr(conv.stop, "was_stopped", lambda: False)())
            save_session(conv.path, conv.history)
            self.emit_to(conv, "turn_end", elapsed=time.time() - t0, tools=tools,
                         stopped=stopped)
            threading.Thread(target=self._title_job, args=(conv,), daemon=True).start()
        except Exception as exc:                 # noqa: BLE001
            self.emit_to(conv, "error", text="%s: %s" % (type(exc).__name__, exc))
            try:
                repair_history(conv.history, journal=journal,
                               tail_note="（本轮出错，这条提问没有得到回答：%s）" % exc)
                save_session(conv.path, conv.history)
            except Exception:
                pass
        finally:
            with conv.lock:
                conv.busy = False
                if self.active != conv.name:
                    conv.unread = True
            _CONV_LOCAL.conv = None

    def _title_job(self, conv):
        try:
            title = ensure_title(conv.path, list(conv.history or []), self.model)
            if title:
                self.emit_to(conv, "title", session=conv.name, title=title)
        except Exception:
            pass

    # ---- 确认 ----
    def ask_confirm(self, name, args, danger=""):
        conv = current_conv()
        if conv is None:
            return False
        ev = threading.Event()
        with conv.lock:
            conv.confirm = {"id": conv.confirm["id"] + 1, "ev": ev, "answer": False,
                            "name": name, "args": args, "danger": danger or ""}
            cid = conv.confirm["id"]
        self.emit_to(conv, "confirm", id=cid, name=name, args=args, danger=danger or "",
                     session=conv.name)
        ev.wait(180)
        with conv.lock:
            return bool(conv.confirm["answer"])

    def answer(self, name, cid, ok):
        conv = self.conv(name)
        if conv is None:
            return False
        with conv.lock:
            if cid == conv.confirm["id"] and conv.confirm["ev"]:
                conv.confirm["answer"] = bool(ok)
                conv.confirm["ev"].set()
                return True
        return False

    def pending_confirm(self, conv):
        with conv.lock:
            ev = conv.confirm.get("ev")
            if ev is None or ev.is_set():
                return None
            return {"id": conv.confirm["id"],
                    "name": conv.confirm.get("name", ""),
                    "args": conv.confirm.get("args", ""),
                    "danger": conv.confirm.get("danger", ""),
                    "session": conv.name}

    # ---- 删除 / 改名 ----
    def _session_path(self, name):
        base = os.path.basename(str(name or "")).strip()
        if not base.endswith(".jsonl") or base.startswith("."):
            return None
        return os.path.join(SESSIONS, base)

    def delete_session(self, name):
        path = self._session_path(name)
        if not path or not os.path.exists(path):
            return False
        conv = self.conv(name)
        if conv is not None and conv.busy:
            return False
        stem = os.path.splitext(path)[0]
        for p in (path, stem + ".title", stem + ".archive.jsonl", stem + ".archive.jsonl.old"):
            try:
                if os.path.exists(p):
                    os.remove(p)
            except OSError:
                pass
        _SESSION_ITEM_CACHE.pop(path, None)
        self.drop(name)
        if self.active == os.path.basename(path):
            self.active = ""
        return True

    def rename_session(self, name, new_name):
        path = self._session_path(name)
        if not path or not os.path.exists(path):
            return ""
        base = os.path.basename(str(new_name or "")).strip()
        if base.lower().endswith(".jsonl"):
            base = base[:-6]
        if not base or re.search(r'[\\/:*?"<>|]', base):
            return ""
        if re.match(r"^(con|prn|aux|nul|com[1-9]|lpt[1-9])$", base.lower()):
            return ""
        dest = os.path.join(SESSIONS, base + ".jsonl")
        if os.path.exists(dest):
            return ""
        old = self.conv(name)
        if old is not None and old.busy:
            return ""
        try:
            os.rename(path, dest)
            old_stem, new_stem = os.path.splitext(path)[0], os.path.splitext(dest)[0]
            for suffix in (".archive.jsonl", ".archive.jsonl.old"):
                if os.path.exists(old_stem + suffix):
                    os.rename(old_stem + suffix, new_stem + suffix)
        except OSError:
            return ""
        _SESSION_ITEM_CACHE.pop(path, None)
        # 手动改名 = 显式标题，压过自动生成的
        try:
            with open(title_path(dest), "w", encoding="utf-8", newline="\n") as fh:
                fh.write(base)
        except (IOError, OSError):
            pass
        with self.lock:
            if old is not None:
                self.convs.pop(os.path.basename(path), None)
                old.name = os.path.basename(dest)
                old.path = dest
                self.convs[old.name] = old
        if self.active == os.path.basename(path):
            self.active = os.path.basename(dest)
        return os.path.basename(dest)


def run_web(port, model, thinking, use_tools, open_browser=True):
    """启动网页终端。Ctrl+C 结束。"""
    global UI, WEB_TOKEN
    if not os.path.exists(WEB_HTML):
        print("找不到 webui.html —— 它应该和 agent.py 放在同一个文件夹里。")
        return 1
    from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

    ui = WebUI()
    ui.model, ui.thinking, ui.use_tools = model, thinking, use_tools
    UI = ui
    WEB_TOKEN = os.urandom(8).hex()

    def session_list(limit=80):
        out = []
        for it in session_items()[:limit]:
            c = ui.convs.get(it["name"])
            out.append({"name": it["name"],
                        "title": it.get("title") or it["name"],
                        "msgs": it["msgs"], "first": it["first"],
                        "time": time.strftime("%m-%d %H:%M", time.localtime(it["mtime"])),
                        "busy": bool(c and c.busy),
                        "unread": bool(c and c.unread),
                        "confirm": bool(c and ui.pending_confirm(c))})
        return out

    class Handler(BaseHTTPRequestHandler):
        protocol_version = "HTTP/1.0"

        def log_message(self, fmt, *args):
            pass

        def _send(self, code, body, ctype="application/json; charset=utf-8"):
            data = body if isinstance(body, bytes) else \
                json.dumps(body, ensure_ascii=False).encode("utf-8")
            self.send_response(code)
            self.send_header("Content-Type", ctype)
            self.send_header("Content-Length", str(len(data)))
            self.send_header("Cache-Control", "no-store, no-cache, must-revalidate")
            self.send_header("Pragma", "no-cache")
            self.send_header("Expires", "0")
            self.end_headers()
            try:
                self.wfile.write(data)
            except Exception:
                pass

        def _token_ok(self):
            q = urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query)
            return q.get("t", [""])[0] == WEB_TOKEN

        def _body(self):
            try:
                n = int(self.headers.get("Content-Length") or 0)
                raw = self.rfile.read(n) if n else b"{}"
                return json.loads(raw.decode("utf-8") or "{}")
            except Exception:
                return {}

        def do_GET(self):
            parsed = urllib.parse.urlparse(self.path)
            if parsed.path in ("/", "/index.html"):
                try:
                    with open(WEB_HTML, "rb") as fh:
                        data = fh.read()
                    # 把 __BUILD__ 换成这个 HTML 的修改时间：一眼能看出是不是旧页面
                    stamp = time.strftime("%m-%d %H:%M",
                                          time.localtime(os.path.getmtime(WEB_HTML)))
                    data = data.replace(b"__BUILD__", stamp.encode("ascii", "replace"))
                except OSError:
                    self._send(500, {"ok": False, "error": "webui.html 缺失"})
                    return
                self._send(200, data, "text/html; charset=utf-8")
                return
            if not self._token_ok():
                self._send(403, {"ok": False, "error": "token"})
                return
            q = urllib.parse.parse_qs(parsed.query)
            if parsed.path == "/api/state":
                conv = ui.conv(ui.active) if ui.active else None
                self._send(200, {
                    "ok": True, "active": ui.active,
                    "busy": bool(conv and conv.busy),
                    "session": ui.active, "model": ui.model, "version": VERSION,
                    "ctx": estimate_tokens(conv.history) if conv and conv.history else 0,
                    "sessions": session_list(),
                })
            elif parsed.path == "/api/events":
                conv = ui.conv(q.get("session", [""])[0])
                if conv is None:
                    self._send(200, [])
                    return
                try:
                    since = int(q.get("since", ["0"])[0])
                except ValueError:
                    since = 0
                self._send(200, ui.since(conv, since))
            elif parsed.path == "/api/open":
                name = q.get("name", [""])[0]
                conv = ui.open(name) if name else None
                if conv is None:
                    self._send(404, {"ok": False, "error": "找不到会话"})
                    return
                msgs = []
                for m in conv.history:
                    role = m.get("role")
                    if role == "system":
                        continue
                    if is_summary_msg(m):
                        msgs.append({"role": "summary", "content": summary_body(m)})
                        continue
                    msgs.append({"role": role, "content": m.get("content"),
                                 "tool_calls": m.get("tool_calls"),
                                 "tool_call_id": m.get("tool_call_id")})
                # 老会话第一次被打开时补一个标题（后台跑，不挡这次打开）
                want_title = q.get("title", ["0"])[0] == "1"
                if (want_title and not read_title(conv.path)
                        and sum(1 for m in conv.history
                                if m.get("role") in ("user", "assistant")) >= 2):
                    threading.Thread(target=ui._title_job, args=(conv,), daemon=True).start()
                self._send(200, {"ok": True, "messages": msgs, "seq": conv.seq,
                                 "session": conv.name,
                                 "title": read_title(conv.path) or default_display_name(conv.name),
                                 "busy": conv.busy, "model": ui.model, "version": VERSION,
                                 "pending_confirm": ui.pending_confirm(conv),
                                 "ctx": estimate_tokens(conv.history),
                                 "sessions": session_list()})
            else:
                self._send(404, {"ok": False, "error": "not found"})

        def do_POST(self):
            if not self._token_ok():
                self._send(403, {"ok": False, "error": "token"})
                return
            path = urllib.parse.urlparse(self.path).path
            body = self._body()
            if path == "/api/chat":
                text = str(body.get("text") or "").strip()
                target = str(body.get("session") or ui.active or "")
                ok, err = ui.start_chat(text, target) if text else (False, "空消息")
                self._send(200 if ok else (400 if not text else 409),
                           {"ok": ok, "error": err, "session": target})
            elif path == "/api/new":
                conv = ui.new()
                self._send(200, {"ok": True, "session": conv.name})
            elif path == "/api/stop":
                conv = ui.conv(body.get("session") or ui.active)
                if conv is not None:
                    conv.stop.trigger("/stop")
                    with conv.lock:
                        if conv.confirm.get("ev") and not conv.confirm["ev"].is_set():
                            conv.confirm["answer"] = False
                            conv.confirm["ev"].set()
                self._send(200, {"ok": conv is not None})
            elif path == "/api/confirm":
                ok = ui.answer(str(body.get("session") or ""), int(body.get("id") or 0),
                               bool(body.get("ok")))
                self._send(200, {"ok": ok})
            elif path == "/api/delete":
                self._send(200, {"ok": ui.delete_session(body.get("name") or "")})
            elif path == "/api/rename":
                new = ui.rename_session(body.get("name") or "", body.get("to") or "")
                self._send(200, {"ok": bool(new), "session": new})
            else:
                self._send(404, {"ok": False, "error": "not found"})

    def _port_busy(num):
        """Windows 上 SO_REUSEADDR 允许第二次 bind 同一端口，得自己先探一下。"""
        import socket as _socket
        sk = _socket.socket(_socket.AF_INET, _socket.SOCK_STREAM)
        sk.settimeout(0.3)
        try:
            return sk.connect_ex(("127.0.0.1", num)) == 0
        finally:
            sk.close()

    ThreadingHTTPServer.allow_reuse_address = False
    httpd = None
    for p in range(port, port + 20):
        if _port_busy(p):
            continue
        try:
            httpd = ThreadingHTTPServer(("127.0.0.1", p), Handler)
            httpd.daemon_threads = True
            port = p
            break
        except OSError:
            continue
    if httpd is None:
        print("端口 %d 附近都被占用了，换一个：agent.py --web 9000" % port)
        return 1

    url = "http://127.0.0.1:%d/?t=%s" % (port, WEB_TOKEN)
    print("ember 网页终端已启动：%s" % url, flush=True)
    print("（只在 127.0.0.1 上监听，局域网访问不到；Ctrl+C 结束）", flush=True)
    try:
        if open_browser:
            os.startfile(url)          # 自动开默认浏览器；失败也不影响
    except Exception:
        pass
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        httpd.server_close()
        UI = None
    return 0


# ---------------- 体检（--doctor） ----------------
HTTP_HINTS = {
    400: "请求格式被拒，通常是 config 里 api_base 写错了",
    401: "API Key 不对：去平台复制新的，粘到 config.txt 的 api_key = 后面",
    402: "余额不足：去平台充值",
    403: "没权限：可能是区域/账号限制，或这个 key 被禁用了",
    404: "路径或模型不存在：检查 api_base 结尾、model 名字",
    429: "被限流：等一会儿再试，或降低并发",
    500: "服务端故障，稍后再试",
    502: "网关错误，通常是网络/代理问题",
    503: "服务不可用，稍后再试",
}


def doctor(model_name=None):
    """--doctor：从配置一路查到流式输出，任何一步断了都给出下一步怎么做。"""
    import socket
    import ssl
    from email.utils import parsedate_to_datetime

    if not model_name:
        model_name = (load_config().get("model") or CONFIG_DEFAULTS["model"]).strip()
    total = 8
    fails = 0

    def section(n, name):
        print()
        print("  [%d/%d] %s" % (n, total, name))

    def good(msg):
        print("        [ OK ] %s" % msg)

    def bad(msg, hint=None):
        nonlocal fails
        fails += 1
        print("        [ !! ] %s" % msg)
        if hint:
            print("               -> %s" % hint)

    print("ember 体检  v%s   (Python %s)" % (VERSION, sys.version.split()[0]))
    print("配置文件: %s" % CONFIG_FILE)

    # ---- 1) 配置 ----
    section(1, "配置文件")
    if os.path.exists(CONFIG_FILE):
        good("config.txt 存在")
    else:
        bad("没有 config.txt", "双击 run.cmd 会让你填 key；包不完整就重新解压")
    if API_KEY:
        shown = (API_KEY[:6] + "..." + API_KEY[-4:]) if len(API_KEY) > 12 else "***"
        good("api_key 已设置：%s（共 %d 位）" % (shown, len(API_KEY)))
    else:
        bad("没有 API Key", "在 config.txt 写 api_key = sk-... 或设环境变量 DEEPSEEK_API_KEY")
    good("api_base = %s" % API_BASE)
    good("model    = %s" % model_name)

    try:
        u = urllib.parse.urlparse(API_BASE)
        host = u.hostname or ""
        port = u.port or (443 if u.scheme == "https" else 80)
    except Exception:
        host, port = "", 443

    # ---- 2) DNS ----
    section(2, "域名解析")
    ip = None
    if not host:
        bad("api_base 里解析不出域名", "检查 config.txt 的 api_base（要写成 https://域名）")
    else:
        t = time.time()
        try:
            infos = socket.getaddrinfo(host, port, 0, socket.SOCK_STREAM)
            ip = infos[0][4][0]
            good("%s -> %s（%d ms）" % (host, ip, (time.time() - t) * 1000))
        except Exception as exc:
            bad("解析失败：%s: %s" % (type(exc).__name__, exc),
                "换个网络试试；公司网可能要配 HTTPS_PROXY")

    # ---- 3) 代理 ----
    section(3, "代理设置")
    envs = ("HTTPS_PROXY", "https_proxy", "HTTP_PROXY", "http_proxy",
            "ALL_PROXY", "all_proxy", "NO_PROXY", "no_proxy")
    used = [(k, os.environ.get(k)) for k in envs if os.environ.get(k)]
    if used:
        for k, v in used:
            good("%s = %s" % (k, v))
        good("会走系统代理（Python 的 urllib 自动认这些变量）")
    else:
        good("没设代理，直连")

    # ---- 4) TLS ----
    section(4, "TLS / 证书 / 本机时间")
    if ip and host and str(API_BASE).lower().startswith("https"):
        t = time.time()
        try:
            ctx = ssl.create_default_context()
            with socket.create_connection((ip, port), timeout=10) as raw:
                with ctx.wrap_socket(raw, server_hostname=host) as ss:
                    proto = ss.version()
                    cert = ss.getpeercert() or {}
            good("握手成功（%s，%d ms）" % (proto, (time.time() - t) * 1000))
            if cert.get("notAfter"):
                good("服务器证书有效期到 %s" % cert["notAfter"])
        except ssl.SSLCertVerificationError as exc:
            bad("证书校验失败：%s" % exc,
                "多半是系统时间不对、公司代理换证书，或 Win7 缺根证书（KB931125）")
        except Exception as exc:
            bad("%s: %s" % (type(exc).__name__, exc),
                "防火墙/代理/网络问题；也可能是本机时间差太多")
    else:
        good("跳过（不是 https，或没有域名）")

    # ---- 5) 鉴权 + 时间偏差 ----
    section(5, "接口鉴权  GET /models")
    models = []
    base = API_BASE.rstrip("/")
    req = urllib.request.Request(base + "/models",
                                 headers={"Authorization": "Bearer " + (API_KEY or "")})
    t = time.time()
    try:
        with urllib.request.urlopen(req, timeout=max(10, API_TIMEOUT)) as resp:
            raw = resp.read()
            date_hdr = resp.headers.get("Date")
        ms = int((time.time() - t) * 1000)
        data = json.loads(raw.decode("utf-8", "replace") or "{}")
        models = [m.get("id") for m in (data.get("data") or []) if m.get("id")]
        good("HTTP 200（%d ms），可用模型 %d 个" % (ms, len(models)))
        if model_name in models:
            good("model「%s」在可用列表里" % model_name)
        elif models:
            # 很多服务会把别名藏起来（列表里没有，但调用能用），所以先记一笔，以第 6 步实测为准
            print("        [ .. ] model「%s」不在 /models 列表里（列表里有：%s）"
                  % (model_name, "、".join(models[:6])))
            print("               可能是别名，第 6 步实际调用一次就知道")
        if date_hdr:
            try:
                skew = time.time() - parsedate_to_datetime(date_hdr).timestamp()
                if abs(skew) > 300:
                    bad("本机时间与服务器差 %d 秒" % skew,
                        "时间不对会让 TLS/鉴权随机失败：先把系统时间校准")
                else:
                    good("本机时间偏差 %d 秒（正常）" % skew)
            except Exception:
                pass
    except urllib.error.HTTPError as exc:
        body = ""
        try:
            body = exc.read().decode("utf-8", "replace")[:160]
        except Exception:
            pass
        bad("HTTP %d %s" % (exc.code, body or exc.reason), HTTP_HINTS.get(exc.code, ""))
    except Exception as exc:
        bad("%s: %s" % (type(exc).__name__, exc),
            "网络不通：看上面的 DNS/代理，或换个网络再试")

    # ---- 6) 对话接口 ----
    section(6, "对话接口  POST /chat/completions")
    payload = {"model": model_name, "max_tokens": 1, "stream": False,
               "messages": [{"role": "user", "content": "ping"}]}
    body = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(base + "/chat/completions", data=body,
                                 headers={"Content-Type": "application/json",
                                          "Authorization": "Bearer " + (API_KEY or "")})
    t = time.time()
    try:
        with urllib.request.urlopen(req, timeout=max(15, API_TIMEOUT)) as resp:
            raw = resp.read()
        ms = int((time.time() - t) * 1000)
        data = json.loads(raw.decode("utf-8", "replace") or "{}")
        choice = (data.get("choices") or [{}])[0]
        txt = ((choice.get("message") or {}).get("content") or "").strip()
        good("HTTP 200（%d ms），回了 %d 个字%s" % (ms, len(txt), "：" + txt[:20] if txt else ""))
        usage = data.get("usage") or {}
        if usage:
            good("用量：prompt %s / completion %s" % (usage.get("prompt_tokens"),
                                                     usage.get("completion_tokens")))
    except urllib.error.HTTPError as exc:
        hint = HTTP_HINTS.get(exc.code, str(exc.reason))
        if exc.code in (400, 404):
            hint = "model 名字可能不对：现在用的是「%s」；%s" % (model_name, hint)
        bad("HTTP %d" % exc.code, hint)
    except Exception as exc:
        bad("%s: %s" % (type(exc).__name__, exc), "同上：网络/代理/防火墙")

    # ---- 7) 流式 ----
    section(7, "流式输出  SSE")
    payload["stream"] = True
    body = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(base + "/chat/completions", data=body,
                                 headers={"Content-Type": "application/json",
                                          "Accept": "text/event-stream",
                                          "Authorization": "Bearer " + (API_KEY or "")})
    t = time.time()
    first = None
    chunks = 0
    try:
        with urllib.request.urlopen(req, timeout=max(15, API_TIMEOUT)) as resp:
            for raw in resp:
                line = raw.decode("utf-8", "replace").strip()
                if not line.startswith("data:"):
                    continue
                if line[5:].strip() == "[DONE]":
                    break
                if first is None:
                    first = time.time() - t
                chunks += 1
        if chunks:
            good("收到 %d 个数据块，首块 %d ms" % (chunks, (first or 0) * 1000))
        else:
            bad("连上了但没收到数据块", "服务端可能不支持 stream=true；把 config 的 model 换个试试")
    except urllib.error.HTTPError as exc:
        bad("HTTP %d" % exc.code, HTTP_HINTS.get(exc.code, str(exc.reason)))
    except Exception as exc:
        bad("%s: %s" % (type(exc).__name__, exc), "流式最容易卡在中间代理上，试试换网络")

    # ---- 8) 本地文件 ----
    section(8, "本地文件")
    if os.path.exists(PROMPT_FILE):
        good("prompt.txt 在（%d 字，来源：%s）" % (len(SYSTEM_PROMPT), PROMPT_SOURCE))
    else:
        bad("没有 prompt.txt", "包里必须带 prompt.txt（它和 agent.py 放一起）")
    good("工具 %d 个；默认目录 %s" % (len(TOOLS), WORKSPACE))
    for label, folder in (("会话目录", SESSIONS), ("工作目录", WORKSPACE)):
        try:
            if not os.path.isdir(folder):
                os.makedirs(folder)
            probe = os.path.join(folder, ".doctor-write-test")
            with open(probe, "w", encoding="utf-8") as fh:
                fh.write("ok")
            os.remove(probe)
            good("%s 可写：%s" % (label, folder))
        except Exception as exc:
            bad("%s 不可写：%s（%s）" % (label, folder, exc),
                "换个目录解压，或检查文件夹权限")

    # ---- 结论 ----
    print()
    print("=" * 52)
    if fails == 0:
        print("结论：都正常，可以直接用。")
    else:
        print("结论：有 %d 项没过（上面标 [ !! ] 的行）。" % fails)
        print("      先按每项后面的 -> 提示处理；还不行就把整屏抄下来发我。")
    return 0 if fails == 0 else 1


# ---------------- 入口 ----------------
def main():
    global CONFIG_FILE, API_BASE
    _init_console()
    argv = sys.argv[1:]

    # 先扫 --config / --api-base / --color / --key-script（要在读配置之前生效）
    key_script = None
    use_stop_keys = True
    cli_api_base = None
    cli_color = None
    i = 0
    while i < len(argv):
        a = argv[i]
        if a == "--config" and i + 1 < len(argv):
            CONFIG_FILE = os.path.abspath(argv[i + 1]); i += 2; continue
        if a == "--key-script" and i + 1 < len(argv):
            key_script = argv[i + 1]; i += 2; continue
        if a == "--api-base" and i + 1 < len(argv):
            cli_api_base = argv[i + 1].strip().rstrip("/"); i += 2; continue
        if a == "--color" and i + 1 < len(argv):
            cli_color = argv[i + 1].strip().lower(); i += 2; continue
        if a == "--no-stop-keys":
            use_stop_keys = False; i += 1; continue
        i += 1

    global _FAST_START
    _FAST_START = any(a in ("--version", "-V", "--check-key", "--show-config",
                            "--list-sessions", "--set-key", "--doctor", "-h", "--help",
                            "--resume") for a in argv)

    cfg = load_config()
    if cli_color:
        cfg["color"] = cli_color
    apply_config(cfg)
    if cli_api_base:          # 命令行优先级最高（apply_config 会拿配置覆盖）
        API_BASE = cli_api_base

    model = (cfg.get("model") or CONFIG_DEFAULTS["model"]).strip()
    thinking = _truthy(cfg.get("thinking", "off"))
    use_tools = _truthy(cfg.get("tools", "on"))
    prompt, cont, resume = None, False, None
    set_key = None
    bootstrap = False
    web_port = 0
    open_browser = True
    quiet_flag = "--quiet" in argv or "-q" in argv
    i = 0
    while i < len(argv):
        a = argv[i]
        if a in ("-p", "--print") and i + 1 < len(argv):
            prompt = argv[i + 1]; i += 2; continue
        if a in ("-c", "--continue"):
            cont = True; i += 1; continue
        if a == "--list-sessions":
            print_sessions(); return 0
        if a in ("--resume", "--session") and i + 1 < len(argv):
            resume = argv[i + 1]; i += 2; continue
        if a in ("--model", "--api-base", "--config", "--key-script", "--color") and i + 1 < len(argv):
            if a == "--model":
                model = argv[i + 1]
            i += 2; continue
        if a == "--set-key" and i + 1 < len(argv):
            set_key = argv[i + 1]; i += 2; continue
        if a == "--think":
            thinking = True; i += 1; continue
        if a == "--yolo":
            set_auto_approve(True); i += 1; continue
        if a == "--safe":
            set_auto_approve(False); i += 1; continue
        if a == "--no-tools":
            use_tools = False; i += 1; continue
        if a in ("--no-stop-keys",):
            i += 1; continue
        if a == "--doctor":
            return doctor(model)
        if a == "--show-config":
            cfg2 = load_config()
            print("配置文件: %s%s" % (CONFIG_FILE, "" if os.path.exists(CONFIG_FILE) else "  (不存在)"))
            for k in sorted(cfg2):
                v = cfg2[k]
                if k == "api_key":
                    v = (v[:6] + "..." + v[-4:]) if len(v) > 12 else ("(空)" if not v else "***")
                print("  %-13s = %s" % (k, v))
            print("默认目录: %s" % WORKSPACE)
            print("自动同意: %s" % ("开" if AUTO_APPROVE else "关"))
            print("超时: 模型无数据 %ds / 单轮 %s / 命令 %ds(≤%ds)"
                  % (API_TIMEOUT, ("不限" if TURN_TIMEOUT <= 0 else "%ds" % TURN_TIMEOUT),
                     CMD_TIMEOUT, CMD_TIMEOUT_MAX))
            print("颜色: %s" % ("关" if not COLOR_ON else
                              ("开（ANSI/VT）" if COLOR_VT else "开（SetConsoleTextAttribute）")))
            print("环境档案: %s%s"
                  % (env_profile_path(cfg2),
                     "（已识别: %s）" % ENV_SHORT if ENV_BLOCK else "（还没有，用 --env-refresh 生成）"))
            print("提示词: %s（%s，共 %d 字）" % (PROMPT_FILE, PROMPT_SOURCE, len(SYSTEM_PROMPT)))
            return 0
        if a in ("-V", "--version"):
            print("ember v%s  (Python %s)" % (VERSION, sys.version.split()[0]))
            return 0
        if a == "--check-key":
            return 0 if API_KEY else 1
        if a == "--env":                      # 有档案就读；没有/过期/换机器了就自动重探
            ensure_env_profile(cfg, quiet=quiet_flag)
            if quiet_flag and not ENV_PROBED:
                return 0
            print(env_block_for_print())
            return 0
        if a == "--env-full":                 # 连注释头一起打（看指纹/探测时间）
            ensure_env_profile(cfg, quiet=quiet_flag)
            p = env_profile_path(cfg)
            print(_read_text_tolerant(p).strip() if os.path.exists(p) else "(还没有档案)")
            return 0
        if a == "--env-refresh":              # 强制重新探测
            ensure_env_profile(cfg, force=True, quiet=quiet_flag)
            print(env_block_for_print())
            return 0
        if a == "--quiet":
            i += 1; continue
        if a == "--bootstrap":
            bootstrap = True; i += 1; continue
        if a == "--web":
            web_port = 8765
            if i + 1 < len(argv) and str(argv[i + 1]).isdigit():
                web_port = int(argv[i + 1])
                i += 1
            i += 1; continue
        if a == "--no-browser":
            open_browser = False; i += 1; continue
        if a in ("-h", "--help"):
            print(__doc__); return 0
        print("未知参数: %s（-h 看用法）" % a)
        return 2

    if set_key is not None:
        k = normalize_key(set_key)
        if not looks_like_key(k):
            print("这个 key 看起来不对，没有保存。")
            if not k:
                print("  收到的是空的（或只有空格/中文标点）")
            else:
                print("  收到的是: %s…（共 %d 位）" % (k[:10], len(k)))
            if k and not k.lower().startswith("sk-"):
                print("  DeepSeek 的 key 是 sk- 开头的一串字符")
            elif k:
                print("  长度不对：正常是 sk- 再加 32 位字符（共 35 位）")
            print("  改法：1) 重开 run.cmd 再粘一次（别带空格/中文）"
                  "  2) 或记事本打开 config.txt 填在 api_key = 后面")
            return 2
        save_config_key(k)
        print("已把 key 写入 %s（%s...%s，共 %d 位）"
              % (CONFIG_FILE, k[:6], k[-4:], len(k)))
        return 0

    if bootstrap and not API_KEY:
        # v1.8：run.cmd 只起一次 Python。没 key 就在这里问，存完直接进入对话，
        # 不再像以前那样"cmd 问一次 -> 起 python 存 -> 再起 python 启动"。
        if not prompt_for_key():
            return 3                  # 3 = 没填 key（run.cmd 会当成"正常退出"处理）
        cfg = load_config()
        apply_config(cfg)

    if not API_KEY:
        print("没有找到 API Key。三种办法：\n"
              "  1) 双击 run.cmd，首次它会问你\n"
              "  2) 用记事本打开 config.txt，把 api_key = 后面填上 sk-xxxx\n"
              "  3) 命令行：python agent.py --set-key sk-xxxx\n"
              "config.txt: %s" % CONFIG_FILE)
        return 1

    if not os.path.isdir(WORKSPACE):
        os.makedirs(WORKSPACE)

    if web_port:                       # v2.0：网页终端（和 cmd 共用 sessions\）
        return run_web(web_port, model, thinking, use_tools, open_browser=open_browser)

    if key_script:
        stop.attach_script(key_script)
    stop.install(use_keys=use_stop_keys and not key_script)

    # 选会话：--resume N（列表编号）/ -c（最近一个）/ 无（新会话）
    session_file = None
    if resume is not None:
        items = session_items()
        picked = None
        if str(resume).isdigit():
            n = int(resume)
            if 1 <= n <= len(items):
                picked = items[n - 1]
            else:
                print("编号超出范围：现在只有 %d 个会话。" % len(items))
                return 2
        elif os.path.exists(str(resume)):
            picked = {"path": str(resume)}
        elif os.path.exists(os.path.join(SESSIONS, str(resume))):
            picked = {"path": os.path.join(SESSIONS, str(resume))}
        else:
            print("找不到会话: %s" % resume)
            return 2
        history, fixed = resume_history(picked["path"])
        session_file = picked["path"]
        print("(继续会话 %s，共 %d 条历史)" % (os.path.basename(session_file), len(history)))
        if fixed:
            print("(上次会话有点不完整：已自动修补 %d 处，接着聊就行)" % fixed)
        if prompt is None and len(history) > 1:
            print_transcript(history, max_msgs=8, title="  --- 上次聊到这儿 ---")
            STATUS.log("  ---（接着输入就行；/history all 看全部）---", color="dim")
    elif cont:
        path = latest_session()
        if path:
            history, fixed = resume_history(path)
            session_file = path
            print("(继续最近会话 %s，共 %d 条历史)" % (os.path.basename(path), len(history)))
            if fixed:
                print("(上次会话有点不完整：已自动修补 %d 处，接着聊就行)" % fixed)
            if prompt is None and len(history) > 1:
                print_transcript(history, max_msgs=8, title="  --- 上次聊到这儿 ---")
                STATUS.log("  ---（接着输入就行；/history all 看全部）---", color="dim")
        else:
            history = new_history()
            print("(没有历史会话，开新会话)")
    else:
        history = new_history()
    if not session_file:
        session_file = new_session_file()

    if prompt:
        journal = lambda msg: append_message(session_file, msg)
        mark = len(history)
        remember(history, {"role": "user", "content": prompt}, journal)
        t0 = time.time()
        try:
            run_turn(history, model, thinking, use_tools, journal=journal,
                     session_path=session_file)
        except Exception as exc:
            STATUS.log("[出错] %s" % exc, color="error")
            repair_history(history, journal=journal,
                           tail_note="（本轮出错，这条提问没有得到回答：%s）" % exc)
            save_session(session_file, history)
            return 1
        used = time.time() - t0
        parts = ["已中断" if stop.was_stopped() else "完成", "%.1fs" % used]
        tools_used = sum(1 for m in history[mark:] if m.get("role") == "tool")
        if tools_used:
            parts.insert(1, "工具 %d 次" % tools_used)
        line = separator_line(" · ".join(parts))
        if line is not None:
            STATUS.log(line, color="dim")
        if not CONTEXT_BUDGET:      # v1.9（T1）：压缩开着时不再按条数删
            trim_history(history, session_path=session_file)
        heal_history(history)
        save_session(session_file, history)
        if not read_title(session_file):
            try:
                ensure_title(session_file, history, model)
            except Exception:
                pass
        return 0

    interactive(model, thinking, use_tools, session_file, history)
    return 0


def set_auto_approve(value):
    global AUTO_APPROVE
    AUTO_APPROVE = bool(value)


if __name__ == "__main__":
    sys.exit(main())
