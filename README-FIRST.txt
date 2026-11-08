ember v2.3.3 —— 一个能塞进 U 盘、Win7 也能跑的本地 agent

不用安装任何东西：解压 -> 双击 run.cmd -> 粘一次 API Key -> 直接说话。
自带 Python 3.8（64/32 位各一份），不写注册表、不要管理员权限，
不依赖 Node / Bun（Win7 上起不来）、也不依赖 PowerShell（老系统只有 2.0）。


======================== 三步开始 ========================
1) 把整个文件夹解压到能写的地方（桌面、D 盘都行，别放 C:\Program Files）
2) 双击 start.cmd —— 启动台：先体检、再选"网页终端"还是"命令行"
   （想直接进命令行也行：双击 run.cmd。第一次会让你粘 API Key，之后不用再输）
3) 直接说需求，例如：  看看桌面有什么文件，按大小排个序

想接着以前的对话：双击 resume.cmd，输编号。进来会先把**上次最后几轮回显一遍**
（看到「--- 上次聊到这儿 ---」就对了）；对话里 /history 看最近 20 条，/history all 看全部。
不想用脚本启动（脚本被拦时）：在这个文件夹的地址栏输入 cmd 回车，然后执行
    py\python.exe program\agent.py
（32 位系统把 py\ 换成 py32\）

双击没反应？按顺序试：
    run.bat  ->  launch.vbs  ->  地址栏 cmd 模式  ->  diagnose.cmd
（.bat 和 .cmd 是两套文件关联；launch.vbs 直接调 cmd.exe，绕过关联）


======================== 它能干什么 ========================
工具（需要时自己调用，不用你点名）：
    list_dir      列目录
    read_file     读文件（带行号）
    write_file    写文件（覆盖 / 追加）
    search_text   按正则搜文本
    run_cmd       执行命令（默认先问你 y/N；auto_approve = on 则直接做）

没有沙箱：整机都能读写，绝对路径直接用；只有相对路径才基于 workspace\。

对话里能用的命令：
    /help  /new  /model <名>  /tools on|off  /think on|off  /approve on|off
    /compact  /context  /stop  /prompt  /config  /history  /save  /exit

运行中想停：敲 /stop 回车，或按 ESC / Ctrl+C。
正在跑的命令会被连子进程一起杀掉，不会在后台偷偷继续。


======================== 网页终端（v2.0，可选）========================
cmd 窗口干不了的两件事 —— 复制、多行粘贴 —— 可以在网页里做。

双击 web.cmd：会自动打开浏览器（没开就把窗口里那行
http://127.0.0.1:xxxx/?t=... 粘进浏览器）。

    * 左边是历史会话，点一下就切过去（和 resume.cmd 用的是同一份）
    * 右边看得见它每一步干了什么：命令、参数、输出（点标题展开）、耗时
    * 输入框支持多行和整段粘贴；Ctrl+Enter 发送，Enter 换行
    * 每条回答、每个工具结果旁边都有"复制"
    * 运行中可以点"停止"，等于 cmd 里的 /stop
    * 需要确认时会在网页里弹窗（y/N 换成两个按钮）

只监听 127.0.0.1，局域网里别人访问不到；地址里那串 t=... 是口令，
防止你正开着的别的网页偷偷调它。关窗口或 Ctrl+C 结束。
两边共用 sessions\，网页和 cmd 可以交替用，聊的是同一段对话。


======================== 文档：Word / Excel / PPT / PDF ========================
不用装 python-docx 那些库，标准库就够（学校机器没网也能用）。

    - 让它"读一下这个 Word/Excel/PPT/PDF"就行 —— 它内部直接解析，不用你转格式
    - 让它"做个表格/写份报告"并指定 .docx / .xlsx，会生成真正的 Office 文件，
      内容用 Markdown 写（# 标题、- 列表、| a | b | 表格、``` 代码块）
    - 改现有 Word 的某几个词、改 Excel 的某个单元格、把 .doc/.xls/.ppt 转新格式，
      它会调用 program\doctools.py（命令行也能自己用）：

        py\python.exe program\doctools.py read   报告.docx
        py\python.exe program\doctools.py read   手册.pdf 1 5
        py\python.exe program\doctools.py replace 模板.docx 旧文字 新文字
        py\python.exe program\doctools.py setcell 表.xlsx - B2 95
        py\python.exe program\doctools.py convert 旧文件.doc docx

    边界：PDF 只提文字层（扫描件读不出）；docx 替换按整段匹配；xlsx 只能改已有单元格。


======================== 常用配置（config.txt）========================
记事本改，保存即可，下次启动生效。每一项在文件里都有注释。

    api_key          你的 DeepSeek key（不写也行，用环境变量 DEEPSEEK_API_KEY）
    model            deepseek-v4-flash（默认，快而省）/ deepseek-v4-pro
    auto_approve     on（默认）= 写文件、跑命令不再问你；off = 每条都问 y/N
    confirm_dangerous on（默认）= 就算开了自动同意，format / del /s / 往系统目录写 .dll
                     这类破坏性动作仍然会问你一次；off = 完全不管
    max_rounds       一次提问最多几轮工具调用（默认 60）
    context_budget   上下文预算（默认 200000 token；窗口是 1M 级，只用了两成；0 = 关闭）
    cmd_timeout      单条命令超时（秒，默认 120）
    search_timeout   单次搜索最多跑多久（秒，默认 20；期间也能 /stop）
    turn_timeout     一次提问总时长上限（秒，默认 1800 = 30 分钟；0 = 不限）
    workspace        相对路径的起点（默认包内 workspace\，也可以写绝对路径）
    color            auto（Win10+ 上色，Win7 自动走控制台属性）/ off


======================== 聊久了会忘？自动压缩 ========================
上下文用到 75% 预算时，自动把"最早几轮"交给模型压成一条摘要，就地替换掉它们：
    * 只在"消息组"边界切（工具调用和它的结果永不拆开）
    * 保留 system、首个任务、以及最近 6 组原文
    * 摘要只有一条，是滚动更新（旧摘要 + 新内容），不会越叠越大
    * 被折叠的原文另存 sessions\*.archive.jsonl，可以让它 search_text 回捞
    * 摘要失败会自动重试一次；还失败就降级成"折叠归档 + 说明"，不会卡住对话

预算按 **token** 估（v1.9 改的）：中文 1 字≈1，英文/日志 3.2 字符≈1。
默认 20 万 token —— 模型窗口是 1M 级，只用了两成，图的是"尽量少压缩、少失忆"。
代价是每轮请求都更大（更贵更慢）；想省钱调到 80000，想更少压缩调到 500000。
旧版按"字符"算是错的：命令输出几乎全 ASCII，会被低估三倍多，压缩时机完全失控。

看用量：/context（含归档大小）   立刻压一次：/compact   不要压缩：context_budget = 0
想省钱：summary_model 填个便宜的小模型，摘要就不用主模型跑了


======================== 文件都在哪 ========================
根目录只放"要点的东西"，程序本体都在 program\ 里：

    start.cmd         启动台：体检 / 网页终端 / 命令行（新窗口或本窗口）/ 配置 / 历史
    run.cmd           直接进命令行
    web.cmd           直接进网页终端
    resume.cmd        选历史会话
    diagnose.cmd      出问题时用：环境 + 完整体检
    run.bat           备用入口（.cmd 关联坏了时用）
    launch.vbs        备用入口（直接调 cmd.exe）
    config.txt        所有设置（含 key）
    README-FIRST.txt  就是这份

    program\          程序本体
      agent.py          全部代码（单文件，只用标准库）
      prompt.txt        人设 / 系统提示词，记事本可改
      webui.html        网页终端的前端
      program\tools\    开发者自检脚本（删了就不能重新生成 ucrt 补丁）
    workspace\        默认工作目录
    sessions\         会话存档；*.archive.jsonl 是被压缩掉的原文
    py\ / py32\       64 位 / 32 位 Python 运行时
    ucrt\             Win7 离线 UCRT 补丁（已内置 2.5MB，只有 python 起不来时才会用到）

搬迁/分发：**拷 zip 包，不要直接拷这个工作目录** —— 工作目录里有你的 key、
聊天记录（sessions\）和本机环境档案，只适合自己用。
只想带走设置：单独拷 config.txt。


======================== 体检（API 不通时先跑这个）========================
双击 start.cmd 选 1，或者双击 diagnose.cmd，或者命令行：
    py\python.exe program\agent.py --doctor

它按顺序过 8 关，哪一关红了都直接告诉你怎么修：

    1 配置文件        config.txt 在不在、key 有没有、api_base/model 是什么
    2 域名解析        api.deepseek.com 能不能解析、耗时多少
    3 代理设置        有没有走 HTTP(S)_PROXY，走的是哪个
    4 TLS / 证书      握手版本、证书到期时间；顺带查本机时间偏差
    5 接口鉴权        GET /models；401=key 错、402=没钱、429=限流，各自给提示
    6 对话接口        POST /chat/completions 真发一句话，看回不回、多快
    7 流式输出        SSE 能不能收到块、首块多久（最容易卡在中间代理上）
    8 本地文件        prompt.txt / 会话目录 / 工作目录能不能写

名字对了就一句"都正常，可以直接用"，有问题就把整屏抄下来发我。

======================== 出问题 ========================
双击闪一下就没了 / 完全没反应
    -> 右键 run.cmd -> 属性 -> 勾"解除锁定"，再试；还不行试 run.bat、launch.vbs
    -> 或者地址栏输 cmd，手动跑 py\python.exe program\agent.py，看完整报错

报 api-ms-win-crt-runtime-l1-1-0.dll 缺失
    -> Win7 缺 UCRT。**包里已经带了 ucrt\ 补丁**，直接双击 run.cmd 就行：
       run.cmd 发现 python 起不来，会自动把 ucrt\x64（或 x86）的 DLL 复制到
       py\ 和 py32\ 旁边，然后再启动一次，不需要管理员权限、不需要联网。
       还不行的话：
       a) 以管理员身份装 vc_redist（64 位装 x64，32 位装 x86），装完重启
       b) 在装好 UCRT 的机器上跑 py\python.exe program\tools\pack_ucrt.py 重新生成 ucrt\
       Win7 SP1 还需要 KB2533623。

中文变问号 / 花屏
    -> 在 cmd 窗口先执行 chcp 936

401 / 403
    -> key 不对或余额不足；/config 看当前生效的配置

一直卡着不动
    -> 敲 /stop 回车；还不听，看 config.txt 里 cmd_timeout / turn_timeout 是不是被改大了

它说"只能在 workspace 里操作"
    -> 那是它自己说错了，整机都能读写。直接回它：用绝对路径 list_dir("C:\\")


======================== 版本 ========================
v2.3.3 修网页终端整体失灵（2.3.2 的 JS 语法错误，导致回车变换行、按钮没反应）；
       打包流程新增 JS 语法检查，这类问题不会再发出去。
v2.3.2 PDF 解析补强：支持对象流/间接资源/页树，逐字定位的 PDF 不再拆字；
       提取不出文字时明确报错，不再把乱码当正文。
v2.3.1 按审计报告修的一轮：replace 不再复制 N 份、run.cmd 不再清空 diagnose.cmd、
       危险命令前缀不再绕过、xlsx 写字符串合规、PDF 提不出字会明确报错、
       UCRT 按位数拷、启动器/网页/自检的一批小毛病。
v2.3.0 文档工具：read_file 直接读 docx/xlsx/pptx/pdf，write_file 直接生成 Office 文档，
       改现有文档/转老格式用 program\doctools.py（纯标准库，不新增工具位）。
v2.2.0 目录整理：程序收进 program\，根目录只留 README / config.txt / 启动项；
       新增 start.cmd 启动台（体检 / 网页终端 / 命令行 新窗口或本窗口 / 配置 / 历史）；
       新增 --doctor 八步体检（配置→DNS→代理→TLS→鉴权→对话→流式→本地文件）。

v2.1.0 多会话并行：每个会话各自推进，A 在跑时可以切到 B、新建 C、给 C 发消息。
       侧边栏状态点：黄点=正在跑，绿点=跑完了但你没看（点开消失），红点=等你确认。
       事件按会话隔离（不串台），/stop 只停当前会话；状态行改为进会话日志。
v2.0.4 自检不再往真实 sessions\ 写测试会话（用 EMBER_SESSIONS 指到临时目录）。
v2.0.3 会话自动起标题（模型看完第一轮给一个 ≤12 字的标题，存在 <会话>.title；
       改名会覆盖标题；老会话第一次打开时补生成）。侧边栏显示标题、副行保留首句，
       两个操作图标加大常显。
v2.0.2 网页端打磨：会话可删除/重命名；命令输出边跑边推；Enter 发送、Shift+Enter 换行
       （输入法选词不误发）；默认简洁模式；代码块单独"复制代码"；右上角显示界面构建时间；
       会话列表不再把归档当会话、按 mtime+size 缓存（会话多了不拖慢）。
v2.0   网页终端（可选）：双击 web.cmd，浏览器里看会话、看每一步工具调用、复制、
       多行粘贴、点按钮停止/确认；和 cmd 共用同一份 sessions\。
       只用标准库 http.server，不引入依赖，仍然免安装。
v1.9.1 捉虫 + 老系统适配：压缩时按 Ctrl+C 不再把程序打死；单轮截断前真的先归档；
       写 .bat/.cmd/.vbs/.reg/.txt/.log/.ini/.csv 改用 GBK（cmd/记事本/Excel 不乱码），
       命令输出能认 chcp 65001 的 UTF-8；del *.* 也拦；/history all 上限 200 条；
       resume.cmd 只收数字；上下文预算默认 20 万 token（1M 窗口，尽量少压缩）。
v1.9   按完整评审报告修订，三条线：
       安全 —— 递归删除/格式化/改注册表/关机/强杀/写系统目录或 .exe/.dll 会额外确认一次
              （confirm_dangerous）；普通删文件不拦。
       稳定 —— 预算改按 token 算（60000）；压缩与"按条数裁剪"不再互相打架，裁剪也进归档；
              摘要失败重试、空回复补位、429 读 Retry-After、turn_timeout 能掐断正在跑的命令。
       顺手 —— read_file 只留头、list_dir 分页、命令输出按代码页解码、搜索按文件分组、
              /context 显示归档大小、resume 回显上次末几轮、/history 看对话记录。
v1.8   改名 pi-lite -> ember；README 重写
       配置行尾注释不再被当成值；超长结果保留尾部（报错看得见）
       GBK/ANSI 文件不再乱码；写文件统一 CRLF（Win7 记事本）
       搜索可 /stop 中断、默认 20 秒上限；429/5xx 自动重试两次
       环境档案只注入摘要（省 token）；run.cmd 只起一次 Python
       新增 ucrt\ 离线补丁机制 + tools\pack_ucrt.py
       turn_timeout 默认 900 -> 1800（30 分钟，配合 max_rounds=60）
v1.7   上下文压缩（摘要就地替换 + archive 回捞）、/compact、/context
v1.6   会话逐条落盘、中断后自动修补历史、run.bat / launch.vbs、max_rounds 60
v1.5   /stop 中断、实时状态行、分界线、Win7 上色
