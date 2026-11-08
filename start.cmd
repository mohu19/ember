@echo off
chcp 936 >nul
title ember 启动台
setlocal
set "HERE=%~dp0"
pushd "%HERE%" >nul 2>&1
if errorlevel 1 cd /d "%HERE%"

set "AGENT=%HERE%program\agent.py"
set "PYEXE=%HERE%py\python.exe"
if /i "%PROCESSOR_ARCHITECTURE%"=="x86" if not defined PROCESSOR_ARCHITEW6432 set "PYEXE=%HERE%py32\python.exe"

if not exist "%AGENT%" goto :nofile
if not exist "%PYEXE%" goto :nopy

"%PYEXE%" -c "pass" >nul 2>&1
if not "%ERRORLEVEL%"=="0" (
  if exist "%HERE%ucrt" call :install_ucrt
  "%PYEXE%" -c "pass" >nul 2>&1
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
"%PYEXE%" "%AGENT%" --doctor
echo.
pause
goto :menu

:web
echo.
"%PYEXE%" "%AGENT%" --check-key >nul 2>&1
if not "%ERRORLEVEL%"=="0" (
  echo   还没有可用的 API Key。
  echo   先选 4（命令行）跑一次，它会让你填 key，然后回来开网页。
  echo.
  pause
  goto :menu
)
start "ember web" cmd /k ""%PYEXE%" "%AGENT%" --web"
echo   网页终端已在另一个窗口启动，浏览器会自动打开。
echo   关掉那个控制台窗口 = 停止服务。
echo.
pause
goto :menu

:cmdnew
echo.
start "ember" cmd /k ""%PYEXE%" "%AGENT%" --bootstrap"
echo   已经在新窗口里打开命令行版。
echo.
goto :menu

:cmdsame
echo.
"%PYEXE%" "%AGENT%" --bootstrap
echo.
echo   —— 命令行会话已结束 ——
pause
goto :menu

:cfg
echo.
"%PYEXE%" "%AGENT%" --show-config
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
echo   [X] 找不到 Python 运行时: %PYEXE%
echo       64 位系统用 py\python.exe，32 位系统用 py32\python.exe
echo.
pause
exit /b 1

:badpy
echo.
echo   [X] 包里的 Python 起不来，多半是 Win7 缺 UCRT。
echo       双击 diagnose.cmd 看详细原因，或按 README 的"缺 UCRT 怎么办"处理。
echo.
pause
exit /b 1

:end
endlocal
exit /b 0