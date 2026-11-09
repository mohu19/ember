# ember

一个能塞进 U 盘、Win7 也能跑的本地 AI agent。单文件 Python，**只用标准库**，不用装任何依赖。

```
双击 start.cmd  →  体检 / 网页终端 / 命令行，随便挑
```

## 为什么会有它

- **免安装**：整个文件夹拷到 U 盘就能用，不写注册表、不装运行库（Win7 缺 UCRT 会自动补）
- **不联网装包**：所有功能（含读 Word/PDF、网页界面）都是标准库手写的
- **两种界面**：`cmd` 命令行，或浏览器里的网页终端（可复制、可多行粘贴、能看见每一步工具调用）
- **多会话并行**：几个对话可以同时推进，侧边栏用黄点（在跑）/ 绿点（跑完没看）标状态

## 功能

| | |
|---|---|
| 工具 | `list_dir` `read_file` `write_file` `search_text` `run_cmd`（整机可读写，危险操作会二次确认） |
| 文档 | `.docx/.xlsx/.pptx/.pdf` 直接读成文字；`write_file` 写 `.docx/.xlsx` 生成真 Office 文件 |
| 模板 | 在现有 Word 上**原位填空**，页眉/页脚/图片/样式原样保留，改完自检"其余部件逐字节未变" |
| 体检 | `--doctor` 八步：配置 → DNS → 代理 → TLS/时间 → 鉴权 → 对话 → 流式 → 本地文件 |
| 长对话 | 自动压缩成一条摘要，原文进归档；`/context` 看用量，`/compact` 手动压 |
| 中断 | 运行中 `/stop`、`ESC`、`Ctrl+C` 都能停，连正在跑的子进程一起杀 |

## 快速开始

1. 解压/克隆到**能写**的目录（别放 `C:\Program Files`）
2. 双击 **`start.cmd`**，选 `1` 体检，确认通了再选 `2`（网页）或 `4`（命令行）
3. 第一次会让你粘 API Key（输入不回显），存在 `config.txt` 里

不想用启动台，也可以直接双击 `run.cmd`（命令行）或 `web.cmd`（网页）。

## 目录

```
start.cmd  run.cmd  web.cmd  resume.cmd  diagnose.cmd  run.bat  launch.vbs
config.txt         所有设置（含 key）
README-FIRST.txt   给最终用户的说明书（比这份详细）
program/           程序本体
  agent.py         agent 主程序（单文件，~5000 行）
  doctools.py      Word / Excel / PPT / PDF 工具（纯标准库）
  find_python.cmd  启动器共用的"挑一个能跑的 Python"
  prompt.txt       系统提示词，记事本可改
  webui.html       网页终端前端（单文件，ES5）
  tools/           自检、打包、UCRT 抓取
logs/              运行日志：crash-*.log（崩溃栈）/ run-YYYYMMDD.log（每次退出一行）
docs/              设计笔记
```

运行时（`py/`、`py32/`、`ucrt/`）和 `sessions/`、`workspace/` 不进仓库，见 `.gitignore`。

## 常用命令

```bat
:: 体检
py\python.exe program\agent.py --doctor

:: 命令行 / 网页
py\python.exe program\agent.py
py\python.exe program\agent.py --web 8765     :: 没 key 也能先开起来，填完点「刷新」

:: 文档工具
py\python.exe program\doctools.py read    报告.docx
py\python.exe program\doctools.py read    手册.pdf 1 5
py\python.exe program\doctools.py fill    模板.docx 姓名=张三 日期=2026-01-01
py\python.exe program\doctools.py setcell 表.xlsx - B2 95
py\python.exe program\doctools.py convert 旧文件.doc docx
```

## 自检

```bat
py\python.exe program\tools\selftest.py     :: 196 项（工具/中断/超时/压缩/文档/PDF/坏会话/启动器）
py\python.exe program\tools\test_web.py     :: 30 项（网页 API、多会话并行、坏会话、key 重读）
```

打包前会跑 9 项冒烟：解压后 `--check-key`、`py32` 能起、`doctools` 能导入、
跑一次 `run.cmd` 后启动文件哈希不变、`diagnose.cmd` 跑完全程、`webui.html` 的 JS 语法检查、
README 里提到的路径都真实存在、`web.cmd` 真能起服务并打出地址。

## 出问题时

`logs\run-YYYYMMDD.log` 每次退出都会追加一行：退出码、原因、模式、stdin 是否控制台、
会话、内存、运行时长、最后一条输入。崩了还会多一个 `logs\crash-*.log`（完整栈）。
把这两个文件发出来，比"它闪退了"有用得多。

## 已知边界

- PDF 只提**文字层**：扫描件没有 OCR；加密/极端 CID 字体可能提不出，会明确报错而不是给乱码
- `doctools.py convert` 依赖本机 Office/WPS（纯 COM），没装会明说
- 网页终端在老 IE（≤ IE8）上会提示换浏览器，命令行不受影响
- 会话是本地 JSONL，没有加密；不要把带 key 的配置目录整个分发出去（发 `部署包.zip`，它会把 key 清空）

## 开发

改完跑两套自检；打包用 `program\tools\make_package.py`（会清空 key、扫泄漏、解压冒烟）。

## 许可证

MIT，见 [LICENSE](LICENSE)。
