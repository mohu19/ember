@echo off
chcp 936 >nul
title ember 启动台
setlocal
set "HERE=%~dp0"
pushd "%HERE%" >nul 2>&1
if errorlevel 1 cd /d "%HERE%"

set "AGENT=%HERE%program\agent.py"
call "%HERE%program\find_python.cmd"
if errorlevel 1 goto :nopy

if not exist "%AGENT%" goto :nofile

%PYEXE% %PYARG% -c "pass" >nul 2>&1
if not "%ERRORLEVEL%"=="0" (
  if exist "%HERE%ucrt" call :install_ucrt
  %PYEXE% %PYARG% -c "pass" >nul 2>&1
)
if not "%ERRORLEVEL%"=="0" goto :badpy

:menu
cls
echo ==========================================================
echo    ember  ^|  启动台
echo ==========================================================
echo.
echo    1) 体检 API（key / 网络 / 模型 / 流式）
echo    2) 打开网页终端（浏览器界面）
echo    3) 命令行  - 新开一个窗口
echo    4) 命令行  - 就在这个窗口
echo    5) 看当前配置
echo    6) 选历史会话继续
echo    0) 退出
echo.
set "CH="
set /p CH=输入数字后回车: 
if not defined CH goto :end
if "%CH%"=="1" goto :doctor
if "%CH%"=="2" goto :web
if "%CH%"=="3" goto :cmdnew
if "%CH%"=="4" goto :cmdsame
if "%CH%"=="5" goto :cfg
if "%CH%"=="6" goto :resume
if "%CH%"=="0" goto :end
goto :menu

:doctor
echo.
%PYEXE% %PYARG% "%AGENT%" --doctor
echo.
pause
goto :menu

:web
echo.
%PYEXE% %PYARG% "%AGENT%" --check-key >nul 2>&1
if not "%ERRORLEVEL%"=="0" (
  echo   还没有可用的 API Key。
  echo   先选 4（命令行）跑一次，它会让你填 key，然后回来开网页。
  echo.
  pause
  goto :menu
)
start "ember web" cmd /k %PYEXE% %PYARG% "%AGENT%" --web
echo   网页终端已在另一个窗口启动，浏览器会自动打开。
echo   关掉那个控制台窗口 = 停止服务。
echo.
pause
goto :menu

:cmdnew
echo.
start "ember" cmd /k %PYEXE% %PYARG% "%AGENT%" --bootstrap
echo   已经在新窗口里打开命令行版。
echo.
goto :menu

:cmdsame
echo.
%PYEXE% %PYARG% "%AGENT%" --bootstrap
echo.
echo   —— 命令行会话已结束 ——
pause
goto :menu

:cfg
echo.
%PYEXE% %PYARG% "%AGENT%" --show-config
echo.
pause
goto :menu

:resume
call "%HERE%resume.cmd"
goto :menu

:install_ucrt
rem v2.3.1: copy by target arch, never put x64 dll into py32
if exist "%HERE%ucrt\x64" if exist "%HERE%py" copy /y "%HERE%ucrt\x64\*.dll" "%HERE%py\" >nul 2>&1
if exist "%HERE%ucrt\x86" if exist "%HERE%py32" copy /y "%HERE%ucrt\x86\*.dll" "%HERE%py32\" >nul 2>&1
goto :eof
:nofile
echo.
echo   [X] 找不到 program\agent.py —— 包不完整。
echo       解决：把整个 ember 文件夹一起解压，别只拷一个 .cmd 出来。
echo.
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
:end
endlocal
exit /b 0