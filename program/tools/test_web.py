# -*- coding: utf-8 -*-
"""网页终端自检：起一个假模型 + 真的 --web 服务，跑一遍 API。

用法:
    py\\python.exe tools\\test_web.py

它做的事：
    1) 在本地起一个假模型（不用 API key，不花钱）
    2) 起 agent.py --web（随机端口，不弹浏览器）
    3) 检查：口令校验 / 会话列表 / 新建会话 / 发消息 / 事件流 / 读回历史 / 停止
"""
import json
import os
import re
import subprocess
import sys
import tempfile
import threading
import time
import urllib.error
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
PY = os.path.join(ROOT, "py", "python.exe")
AGENT = os.path.join(ROOT, "agent.py")

sys.path.insert(0, ROOT)
sys.path.insert(0, HERE)
import selftest as st  # noqa: E402  复用假模型

RESULTS = []


def check(name, ok, detail=""):
    RESULTS.append((name, ok))
    print("   %s %s%s" % ("[PASS]" if ok else "[FAIL]", name, ("  <- " + detail) if detail else ""))


def main():
    if not os.path.exists(PY):
        PY_ = sys.executable
    else:
        PY_ = PY
    srv, api_base = st.start_server()
    tmp = tempfile.mkdtemp(prefix="ember-webtest-")
    ws = os.path.join(tmp, "ws")
    os.makedirs(ws)
    cfg = os.path.join(tmp, "cfg.txt")
    with open(cfg, "w", encoding="utf-8") as fh:
        fh.write("api_key = sk-fake-web-test\napi_base = %s\nenv_profile = off\n"
                 "auto_approve = on\nworkspace = %s\n" % (api_base, ws))

    env = dict(os.environ)
    env["PYTHONIOENCODING"] = "utf-8"
    proc = subprocess.Popen([PY_, AGENT, "--web", "8811", "--no-browser", "--config", cfg],
                            stdout=subprocess.PIPE, stderr=subprocess.STDOUT, env=env,
                            cwd=ROOT, text=True, encoding="utf-8", errors="replace")
    lines = []
    threading.Thread(target=lambda: [lines.append(l) for l in proc.stdout], daemon=True).start()

    url = None
    for _ in range(100):
        for line in lines:
            m = re.search(r"http://127\.0\.0\.1:(\d+)/\?t=([0-9a-f]+)", line)
            if m:
                url, port, token = m.group(0), m.group(1), m.group(2)
                break
        if url:
            break
        time.sleep(0.1)
    if not url:
        print("服务没起来：\n" + "".join(lines))
        srv.shutdown()
        return 1

    def req(path, method="GET", body=None, tok=None):
        tok = token if tok is None else tok
        sep = "&" if "?" in path else "?"
        u = "http://127.0.0.1:%s%s%st=%s" % (port, path, sep, tok)
        data = json.dumps(body).encode("utf-8") if body is not None else None
        r = urllib.request.Request(u, data=data, method=method,
                                   headers={"Content-Type": "application/json"})
        try:
            with urllib.request.urlopen(r, timeout=10) as resp:
                return resp.status, json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            try:
                return exc.code, json.loads(exc.read().decode("utf-8") or "{}")
            except Exception:
                return exc.code, {}

    try:
        code, _ = req("/api/state", tok="bad-token")
        check("没有口令一律 403", code == 403, str(code))

        code, state = req("/api/state")
        check("能拿到状态和会话列表", code == 200 and state.get("ok") and "sessions" in state)
        check("版本号对得上", state.get("version") == st.agent.VERSION,
              str(state.get("version")) + " vs " + st.agent.VERSION)

        code, made = req("/api/new", "POST", {})
        check("能新建会话", code == 200 and made.get("session"), str(made.get("session")))

        code, sent = req("/api/chat", "POST", {"text": "SCN:runcmd|echo web-test"})
        check("能发消息", code == 200 and sent.get("ok"), str(sent))
        sess0 = sent.get("session") or made.get("session")   # v2.1：事件按会话分开取

        kinds, since, deadline = [], 0, time.time() + 40
        while time.time() < deadline:
            _, evs = req("/api/events?since=%d&session=%s" % (since, sess0))
            for ev in evs:
                kinds.append(ev["kind"])
                since = max(since, ev["seq"])
            if "turn_end" in kinds or "error" in kinds:
                break
            time.sleep(0.25)
        check("事件流里有用户消息", "user" in kinds, str(kinds))
        check("事件流里有工具调用与结果", "tool_call" in kinds and "tool_result" in kinds, str(kinds))
        check("事件流里有流式正文", "delta" in kinds, str(kinds))
        check("这一轮正常结束", "turn_end" in kinds and "error" not in kinds, str(kinds))

        name = req("/api/state")[1].get("session")
        code, opened = req("/api/open?name=" + name)
        msgs = opened.get("messages") or []
        roles = [m.get("role") for m in msgs]
        check("能读回历史", code == 200 and "assistant" in roles, str(roles))
        check("工具结果已落盘", any("web-test" in str(m.get("content") or "") for m in msgs))

        code, _ = req("/api/stop", "POST", {})
        check("空闲时点停止不报错", code == 200)

        # ---- 多会话并行（v2.1）----
        def state():
            return req("/api/state")[1]

        def item_of(name):
            return [x for x in state().get("sessions", []) if x["name"] == name]

        _, a = req("/api/new", "POST", {})
        sa = a.get("session")
        req("/api/chat", "POST", {"text": "SCN:slow:1", "session": sa})
        deadline = time.time() + 15
        while time.time() < deadline:
            if item_of(sa) and item_of(sa)[0]["busy"]:
                break
            time.sleep(0.2)
        check("A 会话开始跑了", bool(item_of(sa) and item_of(sa)[0]["busy"]))

        _, b = req("/api/new", "POST", {})
        sb = b.get("session")
        req("/api/chat", "POST", {"text": "SCN:runcmd|echo 并发B", "session": sb})
        deadline = time.time() + 40
        b_done = False
        while time.time() < deadline:
            it = item_of(sb)
            if it and not it[0]["busy"]:
                b_done = True
                break
            time.sleep(0.3)
        check("B 跑完了（A 还在跑的时候）", b_done)
        check("A 仍在跑 —— 确实并行了", bool(item_of(sa) and item_of(sa)[0]["busy"]))

        _, evs_b = req("/api/events?session=%s&since=0" % sb)
        check("B 的事件里没有 A 的输出（不串台）",
              not any("第1段" in str(e.get("text", "")) for e in (evs_b or [])))

        req("/api/stop", "POST", {"session": sa})
        deadline = time.time() + 25
        while time.time() < deadline:
            it = item_of(sa)
            if it and not it[0]["busy"]:
                break
            time.sleep(0.2)
        it = item_of(sa)
        check("只停 A 就停了 A", bool(it) and not it[0]["busy"])
        check("A 后台结束 -> 绿点（未读）", bool(it) and it[0]["unread"] is True, str(it))

        req("/api/open?name=" + sa)
        it = item_of(sa)
        check("点开 A 之后绿点消失", bool(it) and it[0]["unread"] is False, str(it))

        # 改名 / 删除（新会话要先说一句才会落盘）
        code, made2 = req("/api/new", "POST", {})
        nm = made2.get("session")
        req("/api/chat", "POST", {"text": "改名前先写一句"})
        deadline = time.time() + 30
        while time.time() < deadline and req("/api/state")[1].get("busy"):
            time.sleep(0.2)
        code, rn = req("/api/rename", "POST", {"name": nm, "to": "renamed-by-test"})
        check("能改名", code == 200 and rn.get("session") == "renamed-by-test.jsonl", str(rn))
        code, dl = req("/api/delete", "POST", {"name": "renamed-by-test.jsonl"})
        check("能删除（连同归档）", code == 200 and dl.get("ok"), str(dl))
        code, dl2 = req("/api/delete", "POST", {"name": "../../agent.py"})
        check("删除接口不允许路径穿越", code == 200 and not dl2.get("ok"), str(dl2))
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=10)
        except Exception:
            proc.kill()
        srv.shutdown()

    bad = [n for n, ok in RESULTS if not ok]
    print("\n共 %d 项，通过 %d 项，失败 %d 项" % (len(RESULTS), len(RESULTS) - len(bad), len(bad)))
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
