@echo off
chcp 936 >nul
title ember web
setlocal
set "HERE=%~dp0"
pushd "%HERE%" >nul 2>&1
if errorlevel 1 cd /d "%HERE%"

if not exist "%HERE%program\agent.py" goto :nofile
if not exist "%HERE%program\webui.html" goto :noweb

call "%HERE%program\find_python.cmd"
if errorlevel 1 goto :nopy

%PYEXE% %PYARG% -c "pass" >nul 2>&1
if not "%ERRORLEVEL%"=="0" (
  rem v2.3.1：起不来先补 UCRT（按位数拷，别把 x64 拷进 py32）
  if exist "%HERE%ucrt\x64" if exist "%HERE%py" copy /y "%HERE%ucrt\x64\*.dll" "%HERE%py\" >nul 2>&1
  if exist "%HERE%ucrt\x86" if exist "%HERE%py32" copy /y "%HERE%ucrt\x86\*.dll" "%HERE%py32\" >nul 2>&1
  %PYEXE% %PYARG% -c "pass" >nul 2>&1
)
if not "%ERRORLEVEL%"=="0" goto :badpy

echo   启动网页终端（浏览器会自动打开；没有就手动访问下面那个地址）
echo   关掉这个窗口或按 Ctrl+C 就结束服务
echo.
%PYEXE% %PYARG% "%HERE%program\agent.py" --web %*
echo.
echo   网页终端已停止。
pause
endlocal
exit /b 0

:noweb
echo.
echo   [X] 缺少 webui.html —— 它必须和 agent.py 放在同一个文件夹里。
echo       如果只想要命令行，双击 run.cmd 就行。
echo.
pause
exit /b 1

:nofile
echo   [X] 这个文件夹里没有 agent.py —— 包不完整。
pause
exit /b 1

:nopy
echo.
echo   [X] 找不到能用的 Python。
echo       找过这些地方：
echo         - 本目录 py\python.exe     %HERE%py\python.exe
echo         - 本目录 py32\python.exe   %HERE%py32\python.exe
echo         - 系统里已装的 py -3 / python
echo.
echo       常见原因只有两个：
echo         1) 只拷了 .cmd，没有把整个文件夹（含 py\ 和 py32\）一起拷
echo         2) 压缩包解压不完整
echo       解决：重新解压完整包；或者在一台有 Python 3.8+ 的机器上装好再拷过来。
echo.
pause
exit /b 1
:badpy
echo.
echo   [X] 包里的 Python 起不来: %PYEXE% %PYARG%
echo       最常见原因：Windows 7 缺"通用 C 运行库"（UCRT）。
echo         1) 包里带 ucrt\ 的话，重新双击一次会自动补（本脚本已试过一次）
echo         2) 以管理员身份装 vc_redist：64 位装 x64，32 位装 x86，装完重启
echo         3) Win7 SP1 还要 KB2533623
echo       详见 README-FIRST.txt 的"缺 UCRT 怎么办"
echo.
pause
exit /b 1
