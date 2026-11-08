# -*- coding: utf-8 -*-
"""ember 自检脚本（开发用，学校机器上可以删掉这个 tools/ 目录）

用一台假的 SSE 服务器模拟模型，验证：
  1) 运行中敲 /stop 能立刻中断流式回答
  2) 运行中敲 /stop 能杀掉正在跑的命令（连同子进程）
  3) 超时截断：模型不吐数据 / 命令跑太久 / 单轮总时长到顶，都能自动停
  4) 中断后存下来的会话历史仍然是合法的（不会留孤儿 tool 消息）
  5) v1.6：工具跑到一半被强杀，已经发生的消息仍在会话文件里，载入时能自动修补
  6) v1.6：默认 max_rounds = 60

用法:  py\\python.exe tools\\selftest.py
"""
import io
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

try:                                    # cp936 控制台下 detail 里有生僻字符也不能崩
    sys.stdout.reconfigure(errors="replace")
    sys.stderr.reconfigure(errors="replace")
except Exception:
    pass

HERE = os.path.dirname(os.path.abspath(__file__))          # program/tools
PROGRAM = os.path.dirname(HERE)                            # program


def _find_root(start):
    """往上找"有 py\\python.exe 的那层"= 项目根（兼容 program\\ 子目录）。"""
    cur = start
    for _ in range(4):
        if os.path.exists(os.path.join(cur, "py", "python.exe")):
            return cur
        cur = os.path.dirname(cur)
    return start


ROOT = _find_root(HERE)
PY = os.path.join(ROOT, "py", "python.exe")
AGENT = os.path.join(PROGRAM, "agent.py")

# v2.0.3：自检不许往真实的 sessions\ 里丢测试会话 —— 指到临时目录，
# 子进程（run_agent）会继承这个环境变量，也就一起隔离了。
TEST_SESSIONS = tempfile.mkdtemp(prefix="ember-selftest-sessions-")
os.environ["EMBER_SESSIONS"] = TEST_SESSIONS
os.makedirs(TEST_SESSIONS, exist_ok=True)
SESSIONS = TEST_SESSIONS

sys.path.insert(0, PROGRAM)      # agent.py 在 program\ 里（v2.2）
sys.path.insert(0, ROOT)
import agent  # noqa: E402  （只用来复用 sanity_check_history / load_session）


# --------------------------------------------------------------------------- #
# 假模型服务器
# --------------------------------------------------------------------------- #
class FakeModel(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.0"
    last_system = [""]
    retry_left = [0]          # v1.8：先故意返回 503 几次，测自动重试

    def log_message(self, *args):
        pass

    def _sse(self, obj):
        self.wfile.write(("data: " + json.dumps(obj, ensure_ascii=False) + "\n\n").encode("utf-8"))
        self.wfile.flush()

    def _chunk(self, delta, finish=None):
        self._sse({"choices": [{"index": 0, "delta": delta, "finish_reason": finish}]})

    def _done(self):
        self.wfile.write(b"data: [DONE]\n\n")
        self.wfile.flush()

    def _tool_call(self, name, args_obj):
        args = json.dumps(args_obj, ensure_ascii=False)
        half = len(args) // 2
        self._chunk({"tool_calls": [{"index": 0, "id": "call_fake_1", "type": "function",
                                     "function": {"name": name, "arguments": args[:half]}}]})
        time.sleep(0.05)
        self._chunk({"tool_calls": [{"index": 0, "function": {"arguments": args[half:]}}]})
        self._chunk({}, "tool_calls")
        self._done()

    def _tool_calls_multi(self, items):
        """一次返回多个工具调用（测"只执行了一半就被中断"的补账逻辑）。"""
        deltas = []
        for i, (name, args_obj) in enumerate(items):
            deltas.append({"index": i, "id": "call_fake_%d" % i, "type": "function",
                           "function": {"name": name,
                                        "arguments": json.dumps(args_obj, ensure_ascii=False)}})
        self._chunk({"tool_calls": deltas})
        self._chunk({}, "tool_calls")
        self._done()

    def do_POST(self):
        length = int(self.headers.get("Content-Length") or 0)
        try:
            body = json.loads(self.rfile.read(length).decode("utf-8"))
        except Exception:
            body = {}
        msgs = body.get("messages") or []
        for m in msgs:
            # 摘要/标题请求的 system 是模板，不算"这台机器的环境"，别覆盖掉
            if (m.get("role") == "system"
                    and m.get("content") not in (agent.SUMMARY_SYSTEM, agent.TITLE_PROMPT)):
                FakeModel.last_system[0] = m.get("content") or ""
        # 非流式请求 = 上下文压缩要的摘要 / 起标题（v2.0.3）
        if body.get("stream") is False:
            sys_msg = ""
            for m in msgs:
                if m.get("role") == "system" and m.get("content") != agent.SUMMARY_SYSTEM:
                    sys_msg = m.get("content") or ""
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            if sys_msg == agent.TITLE_PROMPT:
                content = "整理日志归档"
            else:
                content = ("1) 用户目标：测试上下文压缩\n2) 已决定：压缩可用\n"
                           "3) 文件：无\n4) 待办：继续\n5) 偏好：中文\n6) 事实：假模型")
            payload = {"choices": [{"index": 0, "message": {
                "role": "assistant", "content": content}}]}
            try:
                self.wfile.write(json.dumps(payload, ensure_ascii=False).encode("utf-8"))
            except Exception:
                pass
            return
        last_user = ""
        for m in reversed(msgs):
            if m.get("role") == "user":
                last_user = m.get("content") or ""
                break
        already_ran_tool = any(m.get("role") == "tool" for m in msgs)

        # 这个场景要卡在"等响应头"上：先别发 headers
        if last_user.startswith("SCN:headers"):
            time.sleep(7)

        # 这个场景先回 503，逼客户端走重试（v1.8）
        if last_user.startswith("SCN:retry503") and FakeModel.retry_left[0] > 0:
            FakeModel.retry_left[0] -= 1
            self.send_response(503)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            try:
                self.wfile.write(b'{"error":"temporarily unavailable"}')
            except Exception:
                pass
            return

        self.send_response(200)
        self.send_header("Content-Type", "text/event-stream")
        self.send_header("Cache-Control", "no-cache")
        self.end_headers()
        try:
            self.plan(last_user, already_ran_tool)
        except Exception:
            pass  # 客户端断开（被 /stop 掐掉）时写管道会报错，正常

    def plan(self, prompt, already_ran_tool):
        if prompt.startswith("SCN:empty"):     # v1.9：返回空内容，测 A1
            self._chunk({}, "stop")
            self._done()
            return
        if prompt.startswith("SCN:headers"):
            for piece in ["等到了。"]:
                self._chunk({"content": piece})
            self._chunk({}, "stop")
            self._done()
            return
        if prompt.startswith("SCN:stall"):
            self._chunk({"content": "开始"})
            time.sleep(600)                      # 之后一直不吐数据
            return
        if prompt.startswith("SCN:slow"):
            secs = float(prompt.split(":")[-1] or 1)
            i = 0
            while True:                          # 永远慢慢吐，等客户端中断
                i += 1
                self._chunk({"content": "第%d段……" % i})
                time.sleep(secs)
        if prompt.startswith("SCN:runcmd"):
            cmd = prompt.split("|", 1)[1]
            if not already_ran_tool:
                self._tool_call("run_cmd", {"command": cmd})
                return
            for piece in ["命令跑完了，", "我继续回答。"]:
                self._chunk({"content": piece})
            self._chunk({}, "stop")
            self._done()
            return
        if prompt.startswith("SCN:multitool"):
            cmd = prompt.split("|", 1)[1]
            if not already_ran_tool:
                self._tool_calls_multi([("run_cmd", {"command": cmd}),
                                        ("write_file", {"path": "never.txt", "content": "不该被写"})])
                return
            self._chunk({"content": "好了。"})
            self._chunk({}, "stop")
            self._done()
            return
        if prompt.startswith("SCN:gap"):
            # 先静默 5 秒（该看到实时状态行），再吐一段，再静默 8 秒（该看到"还在生成"提示），再吐一段
            time.sleep(5)
            self._chunk({"content": "ANSWER-ONE"})
            time.sleep(8)
            self._chunk({"content": "ANSWER-TWO"})
            self._chunk({}, "stop")
            self._done()
            return
        if prompt.startswith("SCN:looptool"):
            self._tool_call("run_cmd", {"command": "echo 循环测试"})
            return
        for piece in ["这是", "一个", "普通", "回答。"]:
            self._chunk({"content": piece})
        self._chunk({}, "stop")
        self._done()


def start_server():
    srv = ThreadingHTTPServer(("127.0.0.1", 0), FakeModel)
    srv.daemon_threads = True
    t = threading.Thread(target=srv.serve_forever)
    t.daemon = True
    t.start()
    return srv, "http://127.0.0.1:%d" % srv.server_address[1]


# --------------------------------------------------------------------------- #
# 工具
# --------------------------------------------------------------------------- #
def write_config(tmp, api_base, scenario_name, **over):
    cfg = {
        "api_key": "sk-fake-key-for-selftest",
        "api_base": api_base,
        "model": "deepseek-v4-flash",
        "thinking": "off",
        "auto_approve": "on",
        "tools": "on",
        "max_rounds": "12",
        "max_history": "60",
        "workspace": os.path.join(tmp, "ws"),
        "prompt_file": "prompt.txt",
        "system_extra": "",
        "max_tokens": "2000",
        "search_skip": "py,sessions",
        "cmd_timeout": "120",
        "cmd_timeout_max": "600",
        "api_timeout": "120",
        "turn_timeout": "1800",
    }
    cfg.update({k: str(v) for k, v in over.items()})
    path = os.path.join(tmp, "config-%s.txt" % scenario_name)
    with open(path, "w", encoding="utf-8") as fh:
        for k, v in cfg.items():
            fh.write("%s = %s\n" % (k, v))
    return path


def run_agent(tmp, cfg_path, prompt, expected_seconds, key_script=None, extra=None,
              stdin_data=None):
    """跑一次 agent.py -p，返回 (输出, 用时, 是否超时被杀)。"""
    argv = [PY, AGENT, "--config", cfg_path, "-p", prompt]
    if key_script:
        argv += ["--key-script", key_script]
    if extra:
        argv += extra
    env = dict(os.environ)
    env.pop("DEEPSEEK_API_KEY", None)
    env["PYTHONIOENCODING"] = "utf-8"
    t0 = time.time()
    proc = subprocess.Popen(argv, cwd=ROOT, stdin=subprocess.PIPE if stdin_data is not None
                            else subprocess.DEVNULL,
                            stdout=subprocess.PIPE, stderr=subprocess.STDOUT, env=env)
    killed = False
    try:
        out = proc.communicate(input=(stdin_data.encode("utf-8") if stdin_data is not None else None),
                               timeout=expected_seconds)[0]
    except subprocess.TimeoutExpired:
        killed = True
        agent.kill_tree(proc)
        out = proc.communicate()[0]
    used = time.time() - t0
    return out.decode("utf-8", "replace"), used, killed


def render(text):
    """模拟终端渲染：\\r 回到行首覆盖、\\n 换行、ANSI 颜色码不占位 —— 验证状态行不会糊掉正文。"""
    lines = [[]]
    col = 0
    i = 0
    n = len(text)
    while i < n:
        ch = text[i]
        if ch == "\x1b" and text[i + 1:i + 2] == "[":        # 跳过 \x1b[...m
            j = text.find("m", i)
            if j != -1:
                i = j + 1
                continue
        if ch == "\n":
            lines.append([])
            col = 0
        elif ch == "\r":
            col = 0
        elif ch == "\b":
            col = max(0, col - 1)
        else:
            row = lines[-1]
            while len(row) < col:
                row.append(" ")
            if len(row) == col:
                row.append(ch)
            else:
                row[col] = ch
            col += 1
        i += 1
    return ["".join(r) for r in lines]


def pid_alive(pid):
    try:
        out = subprocess.check_output(["tasklist", "/FI", "PID eq %d" % pid, "/NH"],
                                      stderr=subprocess.STDOUT).decode("gbk", "replace")
    except Exception:
        return False
    return ("%d" % pid) in out


def last_session_since(before):
    if not os.path.isdir(SESSIONS):
        return None
    now = set(os.listdir(SESSIONS))
    # 只认会话本体：.title / .archive.jsonl / .old 都是附属文件（v2.0.3）
    new = sorted(n for n in (now - before)
                 if n.endswith(".jsonl") and ".archive." not in n)
    if not new:
        return None
    return os.path.join(SESSIONS, new[-1])


RESULTS = []


def check(name, ok, detail=""):
    RESULTS.append((name, ok, detail))
    print("   %s %s%s" % ("[PASS]" if ok else "[FAIL]", name, ("  <- " + detail) if detail else ""))


# --------------------------------------------------------------------------- #
# 场景
# --------------------------------------------------------------------------- #
def main():
    srv, api_base = start_server()
    tmp = tempfile.mkdtemp(prefix="ember-selftest-")
    ws = os.path.join(tmp, "ws")
    os.makedirs(ws)
    print("临时目录: %s\n假模型: %s\n" % (tmp, api_base))

    before_sessions = set(os.listdir(SESSIONS)) if os.path.isdir(SESSIONS) else set()

    child = os.path.join(tmp, "child.py")
    with open(child, "w", encoding="utf-8") as fh:
        fh.write("import os,sys,time\n"
                 "d=sys.argv[1]\n"
                 "open(os.path.join(d,'pid.txt'),'w').write(str(os.getpid()))\n"
                 "for i in range(2400):\n"
                 "    open(os.path.join(d,'tick.txt'),'w').write(str(i))\n"
                 "    time.sleep(0.5)\n"
                 "open(os.path.join(d,'done.txt'),'w').write('finished')\n")
    long_cmd = '"%s" "%s" "%s"' % (PY, child, tmp)

    # ---- 0) 按键状态机（纯逻辑，不需要真控制台）----
    print("[0] 按键解析：/stop 回车、ESC、Ctrl+C、打字不丢")
    w = agent.StopWatcher()
    w.begin(hint=False)
    for ch in "/st":
        w.handle_key(ch)
    check("半个 /stop 不该触发", not w.requested())
    for ch in "op\r":
        w.handle_key(ch)
    check("/stop 回车 -> 触发", w.requested() and w.reason() == "/stop", w.reason())

    w2 = agent.StopWatcher()
    w2.begin(hint=False)
    for ch in "帮我看下 C 盘\r":
        w2.handle_key(ch)
    typed = w2.take_typed()
    check("运行中打的字被记下来", not w2.requested() and typed == ["帮我看下 C 盘"], str(typed))

    w3 = agent.StopWatcher()
    w3.begin(hint=False)
    w3.handle_key("\x1b")
    check("ESC -> 触发", w3.requested() and w3.reason() == "ESC", w3.reason())

    w4 = agent.StopWatcher()
    w4.begin(hint=False)
    w4.handle_key("\x03")
    check("Ctrl+C -> 触发", w4.requested() and w4.reason() == "Ctrl+C", w4.reason())

    w5 = agent.StopWatcher()
    w5.begin(hint=False)
    for ch in "ab\x08c":
        w5.handle_key(ch)
    w5.handle_key("\r")
    typed5 = w5.take_typed()
    check("退格键正常", typed5 == ["ac"], str(typed5))
    check("空回车不触发", not w5.requested())

    # ---- 1) 模型不吐数据 -> 空闲超时截断 ----
    print("[1] 模型 STALL（空闲超时截断）")
    cfg = write_config(tmp, api_base, "stall", api_timeout=5, turn_timeout=60)
    out, used, killed = run_agent(tmp, cfg, "SCN:stall", 40)
    check("未卡死、按时退出", not killed and used < 25, "用时 %.1fs" % used)
    check("输出了超时原因", "没有返回数据" in out, out.strip().splitlines()[-1][:80] if out.strip() else "")

    # ---- 2) 运行中敲 /stop -> 中断流式回答 ----
    print("[2] SLOW 流式回答 + 3 秒后敲 /stop")
    script = os.path.join(tmp, "keys-stop.txt")
    with open(script, "w", encoding="utf-8") as fh:
        fh.write("3000:/stop\n")
    cfg = write_config(tmp, api_base, "slow-stop", api_timeout=60, turn_timeout=300)
    out, used, killed = run_agent(tmp, cfg, "SCN:slow:1", 30, key_script=script)
    check("立刻中断（不是等到超时）", not killed and used < 12, "用时 %.1fs" % used)
    check("收到停止请求", "停止请求" in out)
    check("会话里记了中断原因", "本轮被中断" in out)
    sess = last_session_since(before_sessions)
    if sess:
        hist = agent.load_session(sess)
        ok, why = agent.sanity_check_history(hist)
        check("中断后历史仍合法", ok, why)
        check("中断后留有 assistant 记录", any(m.get("role") == "assistant" for m in hist))
    else:
        check("生成了会话文件", False, "sessions/ 里没有新文件")

    # ---- 2b) 模型"完全没反应"时敲 /stop -> 必须立刻断开（验证从别的线程掐 socket）----
    print("[2b] 模型卡住不吐数据（api_timeout=60）+ 3 秒后敲 /stop")
    script_b = os.path.join(tmp, "keys-stop-b.txt")
    with open(script_b, "w", encoding="utf-8") as fh:
        fh.write("3000:/stop\n")
    cfg = write_config(tmp, api_base, "stall-stop", api_timeout=60, turn_timeout=300)
    out, used, killed = run_agent(tmp, cfg, "SCN:stall", 30, key_script=script_b)
    check("卡住时也能立刻中断（不是等 60 秒超时）", not killed and used < 15, "用时 %.1fs" % used)
    check("是用户中断而不是超时", "停止请求" in out and "没有返回数据" not in out)

    # ---- 3) 运行中敲 /stop -> 杀掉正在跑的命令（连子进程）----
    print("[3] 长命令（模拟下载）+ 3 秒后敲 /stop")
    for f in ("done.txt", "pid.txt", "tick.txt"):
        p = os.path.join(tmp, f)
        if os.path.exists(p):
            os.remove(p)
    script2 = os.path.join(tmp, "keys-stop2.txt")
    with open(script2, "w", encoding="utf-8") as fh:
        fh.write("3000:/stop\n")
    cfg = write_config(tmp, api_base, "cmd-stop", api_timeout=60, turn_timeout=600,
                       cmd_timeout=600, cmd_timeout_max=600)
    out, used, killed = run_agent(tmp, cfg, "SCN:runcmd|" + long_cmd, 40, key_script=script2)
    check("命令被中断（没跑到 600 秒）", not killed and used < 20, "用时 %.1fs" % used)
    check("报告了进程被中断", "被 /stop 中断" in out or "中断" in out)
    time.sleep(1.0)
    check("子进程没有把活干完", not os.path.exists(os.path.join(tmp, "done.txt")))
    pidfile = os.path.join(tmp, "pid.txt")
    if os.path.exists(pidfile):
        pid = int(open(pidfile).read().strip() or 0)
        alive = pid_alive(pid)
        check("孙进程被一起杀掉（PID %d 已消失）" % pid, not alive)
    else:
        check("子进程写出了 PID 文件", False)

    # ---- 3b) 一次返回两个工具调用，跑到一半被 /stop（第二个必须补账，不能变孤儿）----
    print("[3b] 一次两个工具调用 + 跑到一半敲 /stop")
    for f in ("done.txt", "pid.txt", "tick.txt"):
        p = os.path.join(tmp, f)
        if os.path.exists(p):
            os.remove(p)
    script3 = os.path.join(tmp, "keys-stop3.txt")
    with open(script3, "w", encoding="utf-8") as fh:
        fh.write("3000:/stop\n")
    before3 = set(os.listdir(SESSIONS)) if os.path.isdir(SESSIONS) else set()
    cfg = write_config(tmp, api_base, "multi-stop", api_timeout=60, turn_timeout=600,
                       cmd_timeout=600, cmd_timeout_max=600)
    out, used, killed = run_agent(tmp, cfg, "SCN:multitool|" + long_cmd, 40, key_script=script3)
    check("整轮被中断", not killed and used < 20 and "本轮被中断" in out, "用时 %.1fs" % used)
    sess3 = last_session_since(before3)
    if sess3:
        hist = agent.load_session(sess3)
        tools = [m for m in hist if m.get("role") == "tool"]
        check("两个 tool 调用都有回账（没有孤儿）", len(tools) == 2, "实际 %d 条" % len(tools))
        check("没跑到的那个补了说明",
              any("没有执行" in (m.get("content") or "") for m in tools))
        ok, why = agent.sanity_check_history(hist)
        check("中断后历史仍合法", ok, why)
    else:
        check("生成了会话文件", False, "sessions/ 里没有新文件")
    check("后半截 write_file 没有执行", not os.path.exists(os.path.join(ws, "never.txt")))

    # ---- 4) 命令自己超时 -> 截断 + 杀进程树 ----
    print("[4] 长命令 + cmd_timeout=5（命令超时截断）")
    for f in ("done.txt", "pid.txt", "tick.txt"):
        p = os.path.join(tmp, f)
        if os.path.exists(p):
            os.remove(p)
    cfg = write_config(tmp, api_base, "cmd-timeout", api_timeout=30, turn_timeout=120,
                       cmd_timeout=5, cmd_timeout_max=5)
    out, used, killed = run_agent(tmp, cfg, "SCN:runcmd|" + long_cmd, 40)
    check("命令 5 秒左右被截断", not killed and used < 25, "用时 %.1fs" % used)
    check("报告了超时", "超时" in out)
    time.sleep(1.0)
    check("超时后没留下干活的进程", not os.path.exists(os.path.join(tmp, "done.txt")))
    pidfile = os.path.join(tmp, "pid.txt")
    if os.path.exists(pidfile):
        pid = int(open(pidfile).read().strip() or 0)
        check("超时也杀了进程树（PID %d 已消失）" % pid, not pid_alive(pid))
    tick = os.path.join(tmp, "tick.txt")
    if os.path.exists(tick):
        m1 = os.path.getmtime(tick)
        time.sleep(2.0)
        check("tick 文件已停止更新（真死了）", os.path.getmtime(tick) == m1)
    else:
        check("tick 文件存在", False)

    # ---- 5) 单轮总时长上限 ----
    print("[5] 模型一直要工具 + turn_timeout=6（单轮上限截断）")
    cfg = write_config(tmp, api_base, "turn-limit", api_timeout=30, turn_timeout=6,
                       max_rounds=200, cmd_timeout=3, cmd_timeout_max=3)
    out, used, killed = run_agent(tmp, cfg, "SCN:looptool", 40)
    check("单轮到点就停", not killed and used < 25, "用时 %.1fs" % used)
    check("提示了单轮上限", "单轮时间上限" in out)

    # ---- 6) 中断后还能接着干活（历史没被写坏）----
    print("[6] 用中断过的会话继续跑一轮（-c 续聊）")
    if sess:
        env = dict(os.environ)
        env.pop("DEEPSEEK_API_KEY", None)
        env["PYTHONIOENCODING"] = "utf-8"
        # 把 fake api_base 也喂给续聊那一轮
        argv = [PY, AGENT, "--config", cfg, "--api-base", api_base, "--resume", sess, "-p", "接着说"]
        proc = subprocess.Popen(argv, cwd=ROOT, stdin=subprocess.DEVNULL,
                                stdout=subprocess.PIPE, stderr=subprocess.STDOUT, env=env)
        try:
            out2 = proc.communicate(timeout=30)[0].decode("utf-8", "replace")
            rc = proc.returncode
        except subprocess.TimeoutExpired:
            agent.kill_tree(proc)
            out2, rc = "", -1
        check("续聊跑通（没有 400/历史报错）", rc == 0 and "普通" in out2 or "回答" in out2,
              out2.strip().replace("\n", " ")[-100:])
        hist = agent.load_session(sess)
        ok, why = agent.sanity_check_history(hist)
        check("续聊后历史仍合法", ok, why)

    # ---- 7) 逐条确认模式（auto_approve=off）没被按键监听搞坏 ----
    print("[7] 逐条确认：输入 y 执行 / 输入空跳过")
    cfg = write_config(tmp, api_base, "confirm", auto_approve="off", api_timeout=30,
                       turn_timeout=60, cmd_timeout=15)
    before7 = set(os.listdir(SESSIONS)) if os.path.isdir(SESSIONS) else set()
    out, used, killed = run_agent(tmp, cfg, "SCN:runcmd|echo ember-confirm-test", 40,
                                  stdin_data="y\r\n")
    check("确实弹出了确认", "需要你确认" in out, "用时 %.1fs" % used)
    check("输入 y 后真的执行了", not killed and "已退出码" in out or "退出码 0" in out)
    sess7 = last_session_since(before7)
    if sess7:
        hist = agent.load_session(sess7)
        tool_msgs = [m.get("content") or "" for m in hist if m.get("role") == "tool"]
        check("命令真的产出了结果", any("ember-confirm-test" in t for t in tool_msgs),
              str(tool_msgs)[:120])

    before7b = set(os.listdir(SESSIONS)) if os.path.isdir(SESSIONS) else set()
    out, used, killed = run_agent(tmp, cfg, "SCN:runcmd|echo 不该执行", 40, stdin_data="\r\n")
    sess7b = last_session_since(before7b)
    if sess7b:
        hist = agent.load_session(sess7b)
        tool_msgs = [m.get("content") or "" for m in hist if m.get("role") == "tool"]
        check("回车=跳过，命令没跑", any("拒绝" in t for t in tool_msgs), str(tool_msgs)[:120])
    else:
        # 同一秒内的会话文件可能同名，改成按内容找
        found = False
        if os.path.isdir(SESSIONS):
            for name in sorted(os.listdir(SESSIONS)):
                if not name.endswith(".jsonl"):
                    continue
                for m in agent.load_session(os.path.join(SESSIONS, name)):
                    if m.get("role") == "tool" and "拒绝" in (m.get("content") or ""):
                        found = True
        check("回车=跳过，命令没跑", found, "sessions 里没有找到拒绝记录")

    # ---- 8) 实时状态行 + 分界线（显示层不能被状态行糊掉）----
    print("[8] 状态行/分界线：正文不被糊掉，且能看出在干活")
    cfg_on = write_config(tmp, api_base, "status-on", api_timeout=60, turn_timeout=90,
                          status_line="on", separator="line")
    out, used, killed = run_agent(tmp, cfg_on, "SCN:gap", 60)
    screen = render(out)
    check("静默时画了实时状态行", "模型生成中" in out, "用时 %.1fs" % used)
    check("静默久了报了'还在生成'", "还在生成" in out)
    check("正文第一段干净（没被状态行糊掉）",
          any(ln.strip() == "ANSWER-ONE" for ln in screen), str(screen[:6]))
    check("正文里没粘上状态文字",
          all("模型生成中" not in ln and "还在生成" not in ln
              for ln in screen if "ANSWER" in ln))
    check("第二段也完整", any("ANSWER-TWO" in ln for ln in screen))
    check("画了每轮结束分界线", any("本轮结束" in ln for ln in screen))
    line_no = [i for i, ln in enumerate(screen) if "本轮结束" in ln]
    ans_no = [i for i, ln in enumerate(screen) if "ANSWER-TWO" in ln]
    check("分界线在回答之后", line_no and ans_no and line_no[0] > ans_no[0],
          "分界线第 %s 行, 回答第 %s 行" % (line_no, ans_no))

    cfg_off = write_config(tmp, api_base, "status-off", api_timeout=60, turn_timeout=90,
                           status_line="off", separator="ascii")
    out, used, killed = run_agent(tmp, cfg_off, "SCN:gap", 60)
    bare_cr = out.replace("\r\n", "").count("\r")
    check("status_line=off 时没有 \\r 重画", bare_cr == 0, "裸 \\r 个数 %d" % bare_cr)
    check("separator=ascii 用等号", "=====" in out and "本轮结束" in out)

    # ---- 8b) 等响应头时状态行的秒数必须真的在涨（回归：曾经只画一次卡在 1s）----
    print("[8b] 卡在'等模型响应头'时，状态行秒数要一直涨")
    cfg_h = write_config(tmp, api_base, "headers", api_timeout=60, turn_timeout=90,
                         status_line="on")
    out, used, killed = run_agent(tmp, cfg_h, "SCN:headers", 60)
    nums = [int(m) for m in re.findall(r"等待模型开始响应 (\d+)s", out)]
    check("等响应头时状态行画了多次", len(nums) >= 3, "画了 %d 次: %s" % (len(nums), nums))
    check("秒数确实在往上涨", nums and max(nums) >= 4, str(nums))
    check("秒数单调不减", nums == sorted(nums), str(nums))

    # ---- 8c) 上色：工具行/分界线有色，正文无色，关掉时干净 ----
    print("[8c] 上色：--color vt / off / win32")
    cfg_c = write_config(tmp, api_base, "color", api_timeout=30, turn_timeout=60,
                         status_line="on")
    out, used, killed = run_agent(tmp, cfg_c, "SCN:runcmd|echo color-test", 40,
                                  extra=["--color", "vt"])
    check("VT 模式工具行上了亮青(96)", "\x1b[96m" in out, repr(out[:60]))
    check("颜色写完有复位(\x1b[0m)", "\x1b[0m" in out)
    check("分界线用了暗灰(90)", "\x1b[90m" in out)
    check("带着颜色码渲染后正文仍完整",
          any("color-test" in ln or "命令跑完了" in ln for ln in render(out)))
    check("VT 模式下没崩", not killed and "本轮结束" in out)

    out_off, used, killed = run_agent(tmp, cfg_c, "SCN:runcmd|echo color-test", 40,
                                      extra=["--color", "off"])
    check("--color off 时没有任何颜色码", "\x1b[" not in out_off,
          repr([x for x in out_off.splitlines() if "\x1b" in x][:1]))

    out_w, used, killed = run_agent(tmp, cfg_c, "SCN:runcmd|echo color-test", 40,
                                    extra=["--color", "win32"])
    check("--color win32 不崩（无控制台时自动降级）",
          not killed and "本轮结束" in out_w and "color-test" in out_w)

    # ---- 9) resume 进去的历史会话里也能 /stop ----
    print("[9] --resume 续聊时敲 /stop")
    if sess:
        cfg9 = write_config(tmp, api_base, "resume-stop", api_timeout=60, turn_timeout=300,
                            status_line="on")
        script9 = os.path.join(tmp, "keys-resume.txt")
        with open(script9, "w", encoding="utf-8") as fh:
            fh.write("3000:/stop\n")
        before9 = set(os.listdir(SESSIONS)) if os.path.isdir(SESSIONS) else set()
        env = dict(os.environ)
        env.pop("DEEPSEEK_API_KEY", None)
        env["PYTHONIOENCODING"] = "utf-8"
        argv = [PY, AGENT, "--config", cfg9, "--resume", sess, "--key-script", script9,
                "--yolo"]
        proc = subprocess.Popen(argv, cwd=ROOT, stdin=subprocess.PIPE,
                                stdout=subprocess.PIPE, stderr=subprocess.STDOUT, env=env)
        try:
            out9 = proc.communicate(input="SCN:slow:0.5\n/exit\n".encode("utf-8"),
                                    timeout=60)[0].decode("utf-8", "replace")
            rc9 = proc.returncode
        except subprocess.TimeoutExpired:
            agent.kill_tree(proc)
            out9, rc9 = "", -1
        check("续聊时 /stop 生效了", "停止请求" in out9 and "本轮被中断" in out9,
              out9.strip().replace("\n", " ")[-90:])
        check("续聊后正常退出", rc9 == 0, "exit=%s" % rc9)
        check("分界线标了'已中断'", "已中断" in out9)
        hist9 = agent.load_session(sess)
        ok, why = agent.sanity_check_history(hist9)
        check("续聊+中断后历史仍合法", ok, why)
    else:
        check("有可续聊的会话", False)

    # ---- 10) 环境档案：新机器自动识别 ----
    print("[10] 环境档案：自动识别 / 缓存 / 换机器重探 / 注入提示词")
    prof = os.path.join(tmp, "env-profile-test.txt")
    cfg_e = write_config(tmp, api_base, "env", api_timeout=30, turn_timeout=60,
                         env_profile="auto", env_profile_file=prof)
    out_e, _, _ = run_agent(tmp, cfg_e, "SCN:runcmd|echo env", 40)
    check("第一次跑自动生成了环境档案", os.path.exists(prof))
    body = open(prof, encoding="utf-8").read() if os.path.exists(prof) else ""
    check("档案里有系统/命令行/网络/本包这些信息",
          all(k in body for k in ("【这台机器的环境", "系统: Windows", "命令行:", "网络:",
                                  "本包:", "常用位置:")))
    check("档案里没有泄漏 key/密钥", "sk-" not in body and "DEEPSEEK" not in body.upper())
    check("档案真的被注入进系统提示词", "【这台机器的环境" in FakeModel.last_system[0])
    m1 = os.path.getmtime(prof) if os.path.exists(prof) else 0
    time.sleep(1.2)
    out_e2, _, _ = run_agent(tmp, cfg_e, "SCN:runcmd|echo env2", 40)
    check("第二次不再重探（指纹没变就用缓存，省时间）", os.path.getmtime(prof) == m1)
    # 模拟"换了一台机器"：指纹不对了要自动重探
    time.sleep(1.2)
    if os.path.exists(prof):
        txt = open(prof, encoding="utf-8").read().replace("指纹: ", "指纹: 换机器了", 1)
        open(prof, "w", encoding="utf-8").write(txt)
    out_e3, _, _ = run_agent(tmp, cfg_e, "SCN:runcmd|echo env3", 40)
    check("指纹变了 -> 自动重新识别", os.path.getmtime(prof) > m1)
    check("重探后仍然注入提示词", "【这台机器的环境" in FakeModel.last_system[0])
    # env_profile = off 时完全不干活
    nope = os.path.join(tmp, "never-written.txt")
    cfg_eo = write_config(tmp, api_base, "envoff", api_timeout=30, turn_timeout=60,
                          env_profile="off", env_profile_file=nope)
    out_e4, _, _ = run_agent(tmp, cfg_eo, "SCN:runcmd|echo env4", 40)
    check("env_profile=off 时不探测也不注入",
          (not os.path.exists(nope)) and "【这台机器的环境" not in FakeModel.last_system[0])

    # ---- 10b) 兼容性：学校那台 Win7 + PowerShell 2.0 ----
    print("[10b] 向下兼容：Win7 / PowerShell 2.0 / 外部命令全挂也要能跑")
    check("版本号识别 6.1.7601 -> Windows 7 SP1",
          agent.windows_name((6, 1, 7601)) == "Windows 7 SP1")
    check("版本号识别 6.1.7600 -> Windows 7", agent.windows_name((6, 1, 7600)) == "Windows 7")
    check("版本号识别 6.3.9600 -> Windows 8.1", agent.windows_name((6, 3, 9600)) == "Windows 8.1")
    check("版本号识别 10.0.26200 -> Windows 11",
          agent.windows_name((10, 0, 26200)) == "Windows 11")
    check("识别不出也不崩（乱数据）", agent.windows_name(("x", "y")) == "")
    check("git 版本行去掉命令名（不会变成 'git git 2.5'）",
          agent.first_version_line("git version 2.54.0.windows.1\n") == "2.54.0.windows.1")

    calls = []
    real_popen = agent.subprocess.Popen

    def spy_popen(args, *a, **kw):
        calls.append(" ".join(map(str, args)) if not isinstance(args, str) else args)
        raise OSError("环境被锁死，外部命令一律不可用")   # 模拟最苛刻的学校机器

    agent.subprocess.Popen = spy_popen
    try:
        text_b, _ = agent.probe_environment({})
    finally:
        agent.subprocess.Popen = real_popen
    bad_calls = [c for c in calls
                 if re.search(r"powershell|pwsh|wmic|cmd\.exe|(^|\s)ver(\s|$)", c, re.I)]
    check("探测过程绝不调用 PowerShell/wmic/ver（Win7 只有 PS 2.0）",
          not bad_calls, str(bad_calls[:2]))
    check("外部命令全不可用时探测仍给出可用档案（降级不崩）",
          ("系统: Windows" in text_b) and ("本包:" in text_b) and ("命令行:" in text_b),
          text_b.splitlines()[1][:70] if len(text_b.splitlines()) > 1 else "")
    check("命令行全找不到时说明写的是'都没找到'而不是空白",
          "没找到" in text_b or "命令行: " in text_b)

    # ---- 11) v1.6：中途被强杀 / 关窗口，已经发生的消息必须还在 ----
    print("[11] 中途关窗口/强杀 -> 会话文件不丢已发生的消息")
    for f in ("done.txt", "pid.txt", "tick.txt"):
        p = os.path.join(tmp, f)
        if os.path.exists(p):
            os.remove(p)
    before11 = set(os.listdir(SESSIONS)) if os.path.isdir(SESSIONS) else set()
    cfg11 = write_config(tmp, api_base, "journal", api_timeout=60, turn_timeout=600,
                         cmd_timeout=600, cmd_timeout_max=600)
    # 工具正在跑（要跑 1200 秒）的时候 3 秒强杀，模拟"关窗口/任务管理器结束进程"
    out11, used11, killed11 = run_agent(tmp, cfg11, "SCN:runcmd|" + long_cmd, 3.0)
    check("确实是被强杀的（不是自然结束）", killed11, "用时 %.1fs" % used11)
    sess11 = last_session_since(before11)
    if sess11:
        raw11 = agent.load_session(sess11)
        check("user 消息已经落盘（不用等回合结束）",
              any(m.get("role") == "user" and "SCN:runcmd" in (m.get("content") or "")
                  for m in raw11), "%d 条" % len(raw11))
        check("assistant 的 tool_call 也已经落盘",
              any(m.get("tool_calls") for m in raw11))
        check("会话文件里不存 system（载入时按当前提示词重建）",
              all(m.get("role") != "system" for m in raw11))
        hist11 = list(raw11)
        fixed11 = agent.repair_history(hist11)
        check("载入时补上了没拿到结果的 tool_call", fixed11 >= 1, "补了 %d 条" % fixed11)
        ok, why = agent.sanity_check_history(hist11)
        check("修补后的历史合法（下一轮不会 400）", ok, why)
    else:
        check("生成了会话文件", False, "没有新会话")

    # ---- 12) v1.6：默认轮次与修补逻辑 ----
    print("[12] 默认 default：max_rounds=60 / 半截历史修补")
    check("max_rounds 默认 60",
          agent.CONFIG_DEFAULTS["max_rounds"] == "60" and agent.MAX_TOOL_ROUNDS == 60,
          "defaults=%s const=%s" % (agent.CONFIG_DEFAULTS["max_rounds"], agent.MAX_TOOL_ROUNDS))
    check("上下文预算默认 20 万 token",
          agent.CONFIG_DEFAULTS["context_budget"] == "200000",
          agent.CONFIG_DEFAULTS["context_budget"])
    h12 = [{"role": "user", "content": "上一句话还没人回答"}]
    n12 = agent.repair_history(h12)
    check("末尾是 user -> 补一条 assistant 说明",
          n12 == 1 and h12[-1].get("role") == "assistant", str(n12))
    h13 = [{"role": "assistant", "content": None,
            "tool_calls": [{"id": "c1", "type": "function",
                            "function": {"name": "run_cmd", "arguments": "{}"}}]}]
    n13 = agent.repair_history(h13)
    ok, why = agent.sanity_check_history(h13)
    check("孤立 tool_call -> 补一条 tool 结果", n13 == 1 and ok, why)

    # ---- 13) v1.7 上下文压缩 ----
    print("[13] 上下文压缩：折叠成摘要 / 不切开工具组 / 落盘可重载")
    agent.API_BASE = api_base
    agent.API_KEY = "sk-fake-key-for-selftest"
    agent.CONTEXT_BUDGET = 6000
    agent.CONTEXT_KEEP_TAIL = 2
    agent.CONTEXT_KEEP_FIRST = 1

    hist = agent.new_history()
    for i in range(8):
        hist.append({"role": "user", "content": "第%d个问题：看看目录 %d 里有什么" % (i, i)})
        hist.append({"role": "assistant", "content": None, "tool_calls": [
            {"id": "c%d" % i, "type": "function",
             "function": {"name": "list_dir", "arguments": json.dumps({"path": "."})}}]})
        hist.append({"role": "tool", "tool_call_id": "c%d" % i, "content": "x" * 3000})
        hist.append({"role": "assistant", "content": "看完了，%d 号目录没问题" % i})
    before = agent.estimate_tokens(hist)
    ok, n = agent.compact_history(hist, "deepseek-v4-flash")
    check("压缩真的发生了", bool(ok) and n > 0, "压缩前 %d token" % before)
    check("摘要只有一条，紧跟在 system 后面",
          sum(1 for m in hist if agent.is_summary_msg(m)) == 1 and agent.is_summary_msg(hist[1]))
    check("压缩后没有孤儿 tool（不会 400）", agent.sanity_check_history(hist)[0],
          agent.sanity_check_history(hist)[1])
    check("确实变小了（压到一半以内）", agent.estimate_tokens(hist) < before * 0.5,
          "%d -> %d" % (before, agent.estimate_tokens(hist)))
    check("首个任务原文还在（keep_first=1）",
          hist[2].get("content", "").startswith("第0个问题"), str(hist[2])[:40])
    check("工具组没被切开（assistant+tool 成对）",
          all(not (m.get("tool_calls") and not any(
              t.get("tool_call_id") == m["tool_calls"][0]["id"] for t in hist))
              for m in hist if m.get("tool_calls")))

    # 落盘：__summary__ 记录 + 重新载入
    spath = os.path.join(tmp, "compact-session.jsonl")
    hist2 = agent.new_history()
    for i in range(8):
        hist2.append({"role": "user", "content": "问%d" % i})
        hist2.append({"role": "assistant", "content": "答%d" % i + "y" * 400})
    agent.compact_history(hist2, "deepseek-v4-flash", force=True, session_path=spath)
    with open(spath, encoding="utf-8") as fh:
        roles = [json.loads(l).get("role") for l in fh if l.strip()]
    check("会话文件里写的是 __summary__ 记录", roles.count("__summary__") == 1, str(roles[:6]))
    check("会话文件里没有 system", "system" not in roles)
    reloaded = agent.load_session(spath)
    check("重新载入：摘要复原成消息、历史合法",
          agent.is_summary_msg(reloaded[0]) and agent.sanity_check_history(reloaded)[0])
    arc = spath.replace(".jsonl", ".archive.jsonl")
    check("被折叠的原文进了 archive（可回捞）",
          os.path.exists(arc) and os.path.getsize(arc) > 0)

    # 裁剪兜底时也不能把摘要裁掉
    old_max = agent.MAX_HISTORY
    agent.MAX_HISTORY = 2
    h3 = [{"role": "system", "content": "s"}, agent.summary_msg("早前摘要"),
          {"role": "user", "content": "a1"}, {"role": "assistant", "content": "b1"},
          {"role": "user", "content": "a2"}, {"role": "assistant", "content": "b2"}]
    agent.trim_history(h3)
    check("按条数兜底裁剪时摘要不被裁掉", agent.is_summary_msg(h3[1]))
    agent.MAX_HISTORY = old_max

    # ---- 14) v1.8：配置/编码/换行/搜索中断/重试/环境摘要 ----
    print("[14] v1.8 修复：行尾注释 / 头部截断 / GBK 读取 / CRLF / 搜索可中断 / 429 重试")
    old_conf = agent.CONFIG_FILE
    cpath = os.path.join(tmp, "inline.conf")
    with open(cpath, "w", encoding="utf-8") as fh:
        fh.write("color_tool = red   # 这是注释\n"
                 "model = deepseek-v4-pro # 换模型\n"
                 'system_extra = "用 # 号开头也行"  # 带引号的值\n')
    agent.CONFIG_FILE = cpath
    cfg_inline = agent.load_config()
    agent.CONFIG_FILE = old_conf
    check("行尾注释被去掉（color_* 能改动了）", cfg_inline.get("color_tool") == "red",
          repr(cfg_inline.get("color_tool")))
    check("带注释的 model 也正常", cfg_inline.get("model") == "deepseek-v4-pro",
          repr(cfg_inline.get("model")))
    check("引号里的 # 保留", cfg_inline.get("system_extra") == "用 # 号开头也行",
          repr(cfg_inline.get("system_extra")))

    capped = agent._cap("A" * 9000 + "\nTAIL_MARK_12345")
    check("超长结果保留尾部（报错在后面）", "TAIL_MARK_12345" in capped)
    check("超长结果有省略说明", "省略" in capped, capped[-40:].replace("\n", " "))

    agent.WORKSPACE = ws
    gbk_path = os.path.join(ws, "gbk.txt")
    with open(gbk_path, "wb") as fh:
        fh.write("中文内容：第一行\r\n第二行\r\n".encode("gbk"))
    out_gbk = agent.t_read_file({"path": "gbk.txt"})
    check("GBK/ANSI 文件不再乱码", "中文内容" in out_gbk, out_gbk.splitlines()[0][:40] if out_gbk else "")
    check("读文件会报出编码", "编码 gbk" in out_gbk)

    agent.t_write_file({"path": "crlf.txt", "content": "a\nb\n"})
    raw_crlf = open(os.path.join(ws, "crlf.txt"), "rb").read()
    check("写文件用 CRLF（Win7 记事本不再一行到底）", raw_crlf == b"a\r\nb\r\n", repr(raw_crlf))

    for i in range(30):
        with open(os.path.join(ws, "s%d.txt" % i), "w", encoding="utf-8") as fh:
            fh.write("hello\n")
    agent.stop.begin(hint=False)
    agent.stop.trigger("probe")
    t0 = time.time()
    out_s = agent.t_search_text({"pattern": "zzz_no_match", "path": "."})
    dt = time.time() - t0
    agent.stop.end()
    check("搜索能被 /stop 打断", "中断" in out_s and dt < 3.0, "%.2fs" % dt)

    body_env = ("【这台机器的环境】\n系统: Windows 7 SP1\n控制台: 颜色可用\n"
                "命令行: git 2.5\n常用位置: 桌面=C:\\x\n桌面文件夹(3 个): a、b、c\n")
    brief = agent.brief_env_block(body_env)
    check("环境档案默认只注入摘要", "系统: Windows 7" in brief and "桌面文件夹" not in brief)

    cfg_retry = write_config(tmp, api_base, "retry", api_timeout=30, turn_timeout=90)
    FakeModel.retry_left[0] = 2
    out_r, used_r, killed_r = run_agent(tmp, cfg_retry, "SCN:retry503", 90)
    check("503 会自动重试并最终成功", not killed_r and "普通" in out_r,
          out_r.strip().replace("\n", " ")[-80:])
    check("屏幕上看得到重试提示", "重试" in out_r)

    cfg_nokey = write_config(tmp, api_base, "nokey", api_timeout=30, env_profile="off")
    txt = open(cfg_nokey, encoding="utf-8").read().replace(
        "api_key = sk-fake-key-for-selftest", "api_key =")
    with open(cfg_nokey, "w", encoding="utf-8") as fh:
        fh.write(txt)
    env_nk = dict(os.environ)
    env_nk.pop("DEEPSEEK_API_KEY", None)
    env_nk["PYTHONIOENCODING"] = "utf-8"
    p_nk = subprocess.run([PY, AGENT, "--config", cfg_nokey, "--bootstrap"], cwd=ROOT,
                          input=b"", stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                          env=env_nk, timeout=60)
    out_nk = p_nk.stdout.decode("utf-8", "replace")
    check("--bootstrap 没 key 时自己问（一次进程搞定）",
          p_nk.returncode == 3 and "首次使用" in out_nk,
          "rc=%s" % p_nk.returncode)

    # ---- 15) v1.9：按评审报告改的那批 ----
    print("[15] v1.9：token 估算 / 危险命令 / 裁剪归档 / 单轮兜底 / deadline / 分页")
    check("ASCII 不再被低估（1 万字符 ≈ 3 千 token）",
          3000 <= agent.estimate_tokens([{"role": "user", "content": "a" * 10000}]) <= 3200,
          str(agent.estimate_tokens([{"role": "user", "content": "a" * 10000}])))
    check("中文按 1 字 1 token 左右",
          900 <= agent.estimate_tokens([{"role": "user", "content": "中" * 1000}]) <= 1100,
          str(agent.estimate_tokens([{"role": "user", "content": "中" * 1000}])))

    danger_cases = [
        ("format c: /q", True),
        ("diskpart", True),
        ("del /s /q D:\\tmp", True),
        ("rd /s /q C:\\x", True),
        ("reg delete HKLM\\Software\\X /f", True),
        ("shutdown /s /t 0", True),
        ("echo hi && format d:", True),
        ("cipher /w:C:\\", True),
        ("del C:\\*", True),
        ("del *.*", True),
        ('powershell -Command "Remove-Item -Recurse -Force C:\\x"', True),
        ("del file.txt", False),
        ("del /q temp.log", False),
        ("echo format c:", False),
        ("dir /s /b", False),
        ("python x.py --format json", False),
        ('git commit -m "del /s"', False),
        ("copy a b", False),
        ("mkdir x", False),
    ]
    wrong = [(c, want) for c, want in danger_cases
             if bool(agent.danger_reason("run_cmd", {"command": c})) != want]
    check("危险命令判定矩阵（真阳性 + 假阳性一起测）", not wrong, str(wrong[:3]))
    check("往系统目录写 dll 算危险",
          bool(agent.danger_reason("write_file",
                                   {"path": r"C:\Windows\System32\x.dll", "content": ""})))
    check("普通文本文件不算危险",
          not agent.danger_reason("write_file", {"path": os.path.join(ws, "a.txt"),
                                                 "content": "x"}))

    # 裁剪：按组切 + 写归档
    tpath = os.path.join(tmp, "trim-session.jsonl")
    h15 = [{"role": "system", "content": "s"}]
    for i in range(10):
        h15.append({"role": "user", "content": "u%d" % i})
        h15.append({"role": "assistant", "content": None, "tool_calls": [
            {"id": "t%d" % i, "type": "function", "function": {"name": "list_dir",
                                                               "arguments": "{}"}}]})
        h15.append({"role": "tool", "tool_call_id": "t%d" % i, "content": "r%d" % i})
        h15.append({"role": "assistant", "content": "a%d" % i})
    old_max = agent.MAX_HISTORY
    agent.MAX_HISTORY = 6
    dropped = agent.trim_history(h15, session_path=tpath)
    agent.MAX_HISTORY = old_max
    check("裁剪按组走、不产生孤儿 tool", agent.sanity_check_history(h15)[0],
          agent.sanity_check_history(h15)[1])
    tarc = tpath.replace(".jsonl", ".archive.jsonl")
    check("裁剪掉的原文进了归档（不再静默删除）",
          dropped > 0 and os.path.exists(tarc) and os.path.getsize(tarc) > 0,
          "drop=%d" % dropped)

    # 单轮内暴涨的第二道闸
    h16 = [{"role": "system", "content": "s"}]
    for i in range(6):
        h16.append({"role": "assistant", "content": None, "tool_calls": [
            {"id": "z%d" % i, "type": "function",
             "function": {"name": "read_file", "arguments": "{}"}}]})
        h16.append({"role": "tool", "tool_call_id": "z%d" % i, "content": "y" * 4000})
    n16 = agent.shrink_tool_outputs(h16)
    check("单轮暴涨时就地截断较早的 tool 结果", n16 >= 1, "截断 %d 条" % n16)
    check("截断后配对仍然完整（不会 400）", agent.sanity_check_history(h16)[0])

    # deadline 传进 run_cmd
    t0 = time.time()
    out_d = agent.t_run_cmd({"command": "ping -n 20 127.0.0.1"}, deadline=time.time() + 1.5)
    dt = time.time() - t0
    check("turn_timeout 能掐断正在跑的命令", dt < 8 and ("超时" in out_d or "中断" in out_d),
          "%.1fs" % dt)

    # Retry-After 解析
    class _E(object):
        headers = {"Retry-After": "2"}
    check("能读懂 Retry-After", agent.retry_after_seconds(_E()) == 2.0)

    # list_dir 分页
    many = os.path.join(ws, "many")
    os.makedirs(many, exist_ok=True)
    for i in range(310):
        open(os.path.join(many, "f%03d.txt" % i), "w").close()
    out_l = agent.t_list_dir({"path": "many"})
    check("list_dir 会分页并说明总数", "共 310 项" in out_l, out_l[-60:].replace("\n", " "))

    # 空 assistant（A1）
    before_empty = set(os.listdir(SESSIONS)) if os.path.isdir(SESSIONS) else set()
    cfg_e2 = write_config(tmp, api_base, "empty", api_timeout=30, turn_timeout=60)
    out_e, _, _ = run_agent(tmp, cfg_e2, "SCN:empty", 60)
    sess_e = last_session_since(before_empty)
    if sess_e:
        msgs_e = agent.load_session(sess_e)
        check("模型返回空内容时补了占位（不会发空 assistant）",
              any("空内容" in (m.get("content") or "") for m in msgs_e), str(msgs_e)[-80:])
    else:
        check("生成了会话文件", False)

    # A4：危险命令即使 auto_approve=on 也要拦一道（这里用不存在的目录，拒绝掉最安全）
    cfg_d = write_config(tmp, api_base, "danger", auto_approve="on", confirm_dangerous="on",
                         api_timeout=30, turn_timeout=60)
    out_d, _, _ = run_agent(tmp, cfg_d, "SCN:runcmd|del /s /q C:\\no_such_ember_dir", 40,
                            stdin_data="\r\n")
    check("危险命令即使自动同意也会问一次", "危险操作" in out_d, out_d[-100:].replace("\n", " "))
    check("拒绝后确实没有执行", "拒绝" in out_d)

    # resume / /history 的回显（v1.9）
    h17 = [{"role": "system", "content": "s"},
           {"role": "user", "content": "上次的问题"},
           {"role": "assistant", "content": "上次的回答"},
           {"role": "tool", "tool_call_id": "q1", "content": "很长的工具输出"},
           agent.summary_msg("早期聊过什么")]
    import io
    buf = io.StringIO()
    old_out = sys.stdout
    sys.stdout = buf
    try:
        agent.STATUS.set_enabled(False)
        agent.print_transcript(h17, max_msgs=8)
    finally:
        sys.stdout = old_out
    recap = buf.getvalue()
    check("回显里有用户发言", "你> 上次的问题" in recap, recap.replace("\n", " ")[:80])
    check("回显里有助手发言", "助手> 上次的回答" in recap)
    check("回显里摘要单独标出来", "【早前摘要】" in recap)
    check("回显不刷工具输出", "很长的工具输出" not in recap)

    # 单轮截断：先归档再截断（v1.9.1）
    old_budget = agent.CONTEXT_BUDGET
    agent.CONTEXT_BUDGET = 2000
    spath2 = os.path.join(tmp, "shrink-session.jsonl")
    h18 = [{"role": "system", "content": "s"}]
    for i in range(6):
        h18.append({"role": "assistant", "content": None, "tool_calls": [
            {"id": "k%d" % i, "type": "function",
             "function": {"name": "read_file", "arguments": "{}"}}]})
        h18.append({"role": "tool", "tool_call_id": "k%d" % i,
                    "content": "标记%d_" % i + "y" * 4000})
    n18 = agent.shrink_tool_outputs(h18, session_path=spath2)
    arc2 = spath2.replace(".jsonl", ".archive.jsonl")
    agent.CONTEXT_BUDGET = old_budget
    archived_ok = os.path.exists(arc2) and "标记0_" in open(arc2, encoding="utf-8").read()
    check("单轮截断前先把原文归档（提示语不撒谎）", n18 >= 1 and archived_ok,
          "截断 %d 条, 归档=%s" % (n18, archived_ok))

    # 写 .bat/.cmd/.vbs 用 GBK（cmd 按 ANSI 读，UTF-8 会乱码）
    agent.WORKSPACE = ws
    agent.t_write_file({"path": "script.bat", "content": "@echo off\necho 中文标题\n"})
    raw_bat = open(os.path.join(ws, "script.bat"), "rb").read()
    check("写 .bat 用 GBK（cmd 里不乱码）",
          "中文标题".encode("gbk") in raw_bat and "中文标题".encode("utf-8") not in raw_bat)
    agent.t_write_file({"path": "note.py", "content": "print('中文')\n"})
    raw_note = open(os.path.join(ws, "note.py"), "rb").read()
    check("代码文件仍写 UTF-8", "中文".encode("utf-8") in raw_note)
    agent.t_write_file({"path": "old.txt", "content": "中文备注\n"})
    raw_txt = open(os.path.join(ws, "old.txt"), "rb").read()
    check(".txt 按 GBK 写（Win7 记事本不乱码）",
          "中文备注".encode("gbk") in raw_txt and "中文备注".encode("utf-8") not in raw_txt)

    # 命令输出解码：UTF-8（chcp 65001）和 GBK 都要对
    check("命令输出 UTF-8 能认（chcp 65001）",
          agent.decode_output("中文测试".encode("utf-8"), cp=936) == "中文测试")
    check("命令输出 GBK 能认",
          agent.decode_output("中文测试".encode("gbk"), cp=936) == "中文测试")

    # /history all 不会刷屏
    h19 = [{"role": "system", "content": "s"}] + [
        {"role": "user", "content": "第%d条" % i} for i in range(400)]
    buf2 = io.StringIO()
    old_out2 = sys.stdout
    sys.stdout = buf2
    try:
        agent.print_transcript(h19, max_msgs=None)
    finally:
        sys.stdout = old_out2
    check("/history all 有上限（最多 200 条）",
          len(buf2.getvalue().splitlines()) <= 205, str(len(buf2.getvalue().splitlines())))

    # start_line 超范围
    out_r2 = agent.t_read_file({"path": "crlf.txt", "start_line": 999})
    check("start_line 超范围时给出说明", "超出范围" in out_r2, out_r2[:50])

    # ---- 16) v2.0.1：会话列表不读归档 / 受限话术不误报 ----
    print("[16] v2.0.1：会话列表不把归档当会话 / 受限话术不误报")
    spath = os.path.join(SESSIONS, "test-session-xyz.jsonl")
    apath = os.path.join(SESSIONS, "test-session-xyz.archive.jsonl")
    with open(spath, "w", encoding="utf-8") as fh:
        # 故意用"无空格"的紧凑 JSON（别的工具写出来的就是这种），解析也要认得
        fh.write(json.dumps({"role": "user", "content": "第一个问题"},
                            ensure_ascii=False, separators=(",", ":")) + "\n")
        fh.write(json.dumps({"role": "assistant", "content": "回答"}, ensure_ascii=False) + "\n")
    with open(apath, "w", encoding="utf-8") as fh:
        fh.write(json.dumps({"role": "user", "content": "归档里的旧内容"}, ensure_ascii=False) + "\n")
    names = [it["name"] for it in agent.session_items()]
    check("会话列表不把 .archive.jsonl 当会话",
          "test-session-xyz.archive.jsonl" not in names, str(names[:4]))
    check("会话列表能正常列出会话", "test-session-xyz.jsonl" in names)
    item = [it for it in agent.session_items() if it["name"] == "test-session-xyz.jsonl"][0]
    check("首句取的是用户提问（不是归档内容）", item["first"].startswith("第一个问题"),
          item["first"])
    check("轮数统计正确", item["turns"] == 1, str(item["turns"]))
    os.remove(spath)
    os.remove(apath)
    agent._SESSION_ITEM_CACHE.pop(spath, None)

    def confined(t):
        return any(re.search(p, t) for p in agent.CONFINED_PATTERNS)

    check("正常句子不误报（“无法访问”）",
          not confined("这个文件可能无法访问，检查一下权限"))
    check("正常句子不误报（“只能在”）",
          not confined("这个程序只能在 Windows 10 上跑"))
    check("真说自己受限时要报出来", confined("我只能在默认目录里操作"))
    check("真说自己受限时要报出来（C 盘）", confined("我无法访问 C:\\ 以外的路径"))

    # ---- 17) v2.0.3：自动起标题 ----
    print("[17] v2.0.3：自动起标题（不再拿首句当标题）")
    tpath2 = os.path.join(SESSIONS, "title-test.jsonl")
    with open(tpath2, "w", encoding="utf-8") as fh:
        fh.write(json.dumps({"role": "user", "content": "帮我把日志按日期整理"},
                            ensure_ascii=False) + "\n")
        fh.write(json.dumps({"role": "assistant", "content": "好的"}, ensure_ascii=False) + "\n")
    agent.API_BASE = api_base
    agent.API_KEY = "sk-fake"
    got = agent.ensure_title(tpath2, agent.load_session(tpath2), "deepseek-v4-flash")
    check("能生成标题", got == "整理日志归档", got)
    check("标题存在旁边的 .title 文件里", os.path.exists(agent.title_path(tpath2)))
    check("标题不是用户首句", got != "帮我把日志按日期整理", got)
    item2 = [i for i in agent.session_items() if i["name"] == "title-test.jsonl"][0]
    check("会话列表显示标题", item2["title"] == "整理日志归档", item2["title"])
    os.remove(tpath2)
    os.remove(agent.title_path(tpath2))
    agent._SESSION_ITEM_CACHE.pop(tpath2, None)

    # ---- 18) v2.3：文档工具（docx/xlsx 往返、改单元格、查找替换）----
    print("[18] v2.3：文档工具（纯标准库读写 Word/Excel）")
    import doctools as _dt
    dpath = os.path.join(tmp, "报告.docx")
    _dt.write_docx(dpath, "# 标题\n\n正文 **加粗**。\n\n| 项 | 值 |\n|---|---|\n| 甲 | 1 |\n")
    back = _dt.read_docx(dpath)
    check("docx 写->读 保留标题", "# 标题" in back, back[:40])
    check("docx 写->读 保留表格", "| 甲 | 1 |" in back, back[:60])
    xpath = os.path.join(tmp, "表.xlsx")
    _dt.write_xlsx(xpath, "名称,数量\n苹果,3\n")
    check("xlsx 写->读", "苹果" in _dt.read_xlsx(xpath) and "3" in _dt.read_xlsx(xpath))
    msg = _dt.xlsx_set(xpath, [(None, "B2", "42")])
    check("xlsx 改单元格", "42" in _dt.read_xlsx(xpath), msg)
    check("xlsx 改单元格的提示带工作表名", "Sheet1!B2" in msg, msg)
    out = _dt.docx_replace(dpath, [("正文", "这是正文")], out=os.path.join(tmp, "改.docx"))
    check("docx 查找替换", "这是正文" in _dt.read_docx(os.path.join(tmp, "改.docx")), out)
    check("替换不改原文件", "正文 **加粗**" not in _dt.read_docx(dpath))
    try:
        _dt.doc_read(os.path.join(tmp, "不存在.docx"))
        check("读不存在的文件会报错", False)
    except Exception:
        check("读不存在的文件会报错", True)

    # 走原有工具（不新增工具位）：read_file / write_file 自己认格式
    tw = os.path.join(tmp, "工单.docx")
    msg_w = agent.t_write_file({"path": tw, "content": "# 工单\n\n- 处理中\n"})
    check("write_file 能直接生成 docx", "已生成 Word" in msg_w, msg_w)
    got_r = agent.t_read_file({"path": tw})
    check("read_file 能直接读 docx", "# 工单" in got_r and "处理中" in got_r, got_r[:40])
    tx = os.path.join(tmp, "名单.xlsx")
    agent.t_write_file({"path": tx, "content": "姓名,分数\n张三,90\n"})
    check("write_file 能直接生成 xlsx", "张三" in agent.t_read_file({"path": tx}))
    check("工具总数还是 5 个", len(agent.TOOLS) == 5, str(len(agent.TOOLS)))

    # ---- 19) v2.3：Word 模板原位填空（跨 run + 页眉 + 不破坏其它部件）----
    print("[19] v2.3：模板填空不破坏格式")
    import zipfile as _zf
    W = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
    tpl = os.path.join(tmp, "模板.docx")
    doc_xml = ('<w:document xmlns:w="%s"><w:body>'
               '<w:p><w:r><w:t>公司：{{公</w:t></w:r><w:r><w:t>司}}</w:t></w:r></w:p>'
               '<w:p><w:r><w:t>部门：{{部门}}</w:t></w:r></w:p>'
               '</w:body></w:document>') % W
    hdr_xml = ('<w:hdr xmlns:w="%s"><w:p><w:r><w:t>页眉：{{公司}}</w:t></w:r></w:p></w:hdr>') % W
    img = bytes(range(256)) * 4
    with _zf.ZipFile(tpl, "w") as z:
        z.writestr("[Content_Types].xml", "<Types/>")
        z.writestr("_rels/.rels", "<Relationships/>")
        z.writestr("word/document.xml", doc_xml)
        z.writestr("word/header1.xml", hdr_xml)
        z.writestr("word/media/image1.png", img)
    outd = os.path.join(tmp, "填好.docx")
    msg = _dt.docx_fill(tpl, mapping={"公司": "星河科技", "部门": "研发部", "缺的": "x"}, out=outd)
    body19 = _dt.read_docx(outd)
    check("跨 run 的占位符也能填上", "星河科技" in body19 and "研发部" in body19, body19[:40])
    check("页眉里的占位符也填了",
          "星河科技" in _zf.ZipFile(outd).read("word/header1.xml").decode("utf-8"))
    check("没找到的占位符会明确报出来", "没找到" in msg and "缺的" in msg, msg.splitlines()[-2][:40])
    check("改完会做结构自检", "结构自检通过" in msg, msg.splitlines()[-1][:50])
    check("图片字节没被动过", _zf.ZipFile(outd).read("word/media/image1.png") == img)
    check("原模板没被改", "{{部门}}" in _zf.ZipFile(tpl).read("word/document.xml").decode("utf-8"))

    # ---- 20) v2.3.1：审计报告里的 P0 回归 ----
    print("[20] v2.3.1：审计 P0 回归（替换重复 / xlsx 字符串 / 危险前缀 / 启动器）")
    import zipfile as _zf2
    rp = os.path.join(tmp, "rep.docx")
    _dt.write_docx(rp, "正文第一句。公司简称。")
    rq = os.path.join(tmp, "rep2.docx")
    msg20 = _dt.docx_replace(rp, [("正文", "这是正文"), ("公司", "公司名称")], out=rq)
    body20 = _dt.read_docx(rq)
    check("新值包含旧值时只替换一次", body20.count("这是") == 1, msg20.splitlines()[1][:40])
    check("替换次数报的是真实值", "已填 2 处" in msg20, msg20.splitlines()[1][:40])

    xp = os.path.join(tmp, "c.xlsx")
    _dt.write_xlsx(xp, "名称,数量\n苹果,3\n")
    _dt.xlsx_set(xp, [(None, "B2", "文字值")])
    with _zf2.ZipFile(xp) as z20:
        ct20 = z20.read("[Content_Types].xml").decode("utf-8")
        rl20 = z20.read("xl/_rels/workbook.xml.rels").decode("utf-8")
    check("写字符串后 Content_Types 声明了 sharedStrings", "sharedStrings" in ct20)
    check("写字符串后 workbook.rels 有 sharedStrings 关系", "sharedStrings" in rl20)
    check("字符串值能读回", "文字值" in _dt.read_xlsx(xp))

    def _dz(c):
        return bool(agent.danger_reason("run_cmd", {"command": c}))
    check("cmd /c 前缀被剥掉", _dz("cmd /c format C: /y"))
    check("start 前缀被剥掉", _dz("start /min format C:"))
    check("powershell -Command 被剥掉", _dz("powershell -Command rm -r C:\\Users"))
    check("reg add 直接算危险", _dz("reg add HKLM\\Software\\X /f"))
    check("普通 del 不误报", not _dz("del /q file.txt"))
    check("echo 里出现 format 不误报", not _dz("echo format c:"))

    bad_launch = []
    for name in ("run.cmd", "web.cmd", "start.cmd", "resume.cmd", "diagnose.cmd"):
        fp = os.path.join(ROOT, name)
        if not os.path.exists(fp):
            continue
        for line in io.open(fp, "rb").read().decode("gbk", "replace").splitlines():
            st = line.strip().lower()
            if st.startswith("echo") and "->" in st:
                bad_launch.append("%s: %s" % (name, st[:40]))
    check("启动脚本里没有未转义的 -> （会清空文件）", not bad_launch, "；".join(bad_launch))

    # ---- 21) v2.3.2：PDF 文本提取（以前一个用例都没有）----
    print("[21] v2.3.2：PDF 文本层提取")
    pdf_ok = os.path.join(tmp, "hello.pdf")
    body = (b"BT /F1 12 Tf 20 100 Td (Hello PDF 123) Tj ET")
    parts = [
        b"%PDF-1.4\n",
        b"1 0 obj<</Type/Catalog/Pages 2 0 R>>endobj\n",
        b"2 0 obj<</Type/Pages/Kids[3 0 R]/Count 1>>endobj\n",
        b"3 0 obj<</Type/Page/Parent 2 0 R/MediaBox[0 0 300 200]"
        b"/Resources<</Font<</F1 5 0 R>>>>/Contents 4 0 R>>endobj\n",
        b"4 0 obj<</Length %d>>stream\n" % len(body) + body + b"\nendstream endobj\n",
        b"5 0 obj<</Type/Font/Subtype/Type1/BaseFont/Helvetica>>endobj\n",
        b"trailer<</Root 1 0 R>>\n%%EOF\n",
    ]
    with open(pdf_ok, "wb") as fh:
        fh.write(b"".join(parts))
    got21 = _dt.read_pdf(pdf_ok)
    check("能读出一页 PDF 的正文", "Hello PDF 123" in got21, got21[:50].replace("\n", " "))
    check("带了页码标记", "第 1 页" in got21, got21[:30])

    pdf_img = os.path.join(tmp, "scan.pdf")
    with open(pdf_img, "wb") as fh:
        fh.write(b"".join([
            b"%PDF-1.4\n",
            b"1 0 obj<</Type/Page/Resources<<>>>>/Contents 2 0 R>>endobj\n",
            b"2 0 obj<</Length 12>>stream\nq 1 0 0 1 0 0 cm Q\nendstream endobj\n",
            b"trailer<</Root 1 0 R>>\n%%EOF\n"]))
    got_img = _dt.read_pdf(pdf_img)
    check("没有文字层时明确说明", "没有文字层" in got_img, got_img[:40].replace("\n", " "))

    # ---- 收尾 ----
    srv.shutdown()
    after = set(os.listdir(SESSIONS)) if os.path.isdir(SESSIONS) else set()
    for name in sorted(after - before_sessions):
        try:
            os.remove(os.path.join(SESSIONS, name))
        except OSError:
            pass
    shutil.rmtree(tmp, ignore_errors=True)
    shutil.rmtree(TEST_SESSIONS, ignore_errors=True)   # 测试用的临时会话目录，直接删掉

    bad = [n for n, ok, _ in RESULTS if not ok]
    print("\n==================== 结果 ====================")
    print("共 %d 项，通过 %d 项，失败 %d 项" % (len(RESULTS), len(RESULTS) - len(bad), len(bad)))
    for n in bad:
        print("  失败: %s" % n)
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
