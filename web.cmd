@echo off
chcp 936 >nul
title ember web
setlocal
set "HERE=%~dp0"
pushd "%HERE%" >nul 2>&1
if errorlevel 1 cd /d "%HERE%"

if not exist "%HERE%program\agent.py" goto :nofile
if not exist "%HERE%program\webui.html" goto :noweb

set "PYEXE=%HERE%py\python.exe"
if /i "%PROCESSOR_ARCHITECTURE%"=="x86" if not defined PROCESSOR_ARCHITEW6432 set "PYEXE=%HERE%py32\python.exe"
if not exist "%PYEXE%" goto :nopy

"%PYEXE%" -c "pass" >nul 2>&1
if not "%ERRORLEVEL%"=="0" (
  rem v2.3.1：起不来先补 UCRT（按位数拷，别把 x64 拷进 py32）
  if exist "%HERE%ucrt\x64" if exist "%HERE%py" copy /y "%HERE%ucrt\x64\*.dll" "%HERE%py\" >nul 2>&1
  if exist "%HERE%ucrt\x86" if exist "%HERE%py32" copy /y "%HERE%ucrt\x86\*.dll" "%HERE%py32\" >nul 2>&1
  "%PYEXE%" -c "pass" >nul 2>&1
)
if not "%ERRORLEVEL%"=="0" goto :badpy

echo   启动网页终端（浏览器会自动打开；没有就手动访问下面那个地址）
echo   关掉这个窗口或按 Ctrl+C 就结束服务
echo.
"%PYEXE%" "%HERE%program\agent.py" --web %*
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
echo   [X] 找不到 Python 运行时: %PYEXE%
pause
exit /b 1

:badpy
echo   [X] 包里的 Python 启动失败，多半是 Win7 缺 UCRT。
echo       先双击 diagnose.cmd 看看，或看 README 的"缺 UCRT 怎么办"。
pause
exit /b 1