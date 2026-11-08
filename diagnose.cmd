@echo off
chcp 936 >nul
title ember 诊断
setlocal
set "HERE=%~dp0"
pushd "%HERE%" >nul 2>&1
if errorlevel 1 cd /d "%HERE%"
set "AGENT=%HERE%program\agent.py"
set "PYEXE=%HERE%py\python.exe"
if /i "%PROCESSOR_ARCHITECTURE%"=="x86" if not defined PROCESSOR_ARCHITEW6432 set "PYEXE=%HERE%py32\python.exe"

echo ==========================================================
echo    ember 诊断
echo ==========================================================
echo.
echo  [目录] %HERE%
echo  [程序] %AGENT%
if exist "%AGENT%" goto :agent_ok
echo         缺失！包不完整
goto :noagent
:agent_ok
echo         存在

:noagent
echo  [配置] %HERE%config.txt
if exist "%HERE%config.txt" goto :cfg_ok
echo         缺失！
goto :cfg_done
:cfg_ok
echo         存在
:cfg_done

echo  [运行时] %PYEXE%
if exist "%PYEXE%" goto :py_ok
echo         缺失！
goto :nopy
:py_ok
echo         存在

echo.
echo  [1] Python 能不能起来
"%PYEXE%" -V
if not "%ERRORLEVEL%"=="0" goto :badpy

echo.
echo  [2] 系统信息
echo      %PROCESSOR_ARCHITECTURE%
ver
echo.
echo  [3] 完整体检（配置 / 网络 / 模型 / 流式）
echo.
"%PYEXE%" "%AGENT%" --doctor
echo.
echo  —— 诊断结束 ——
pause
endlocal
exit /b 0

:badpy
echo.
echo      [X] Python 起不来，多半是 Win7 缺 UCRT。三种办法，任选一种：
echo          1. 包里有 ucrt 目录的话，重新双击 run.cmd 会自动补
echo          2. 装一次 vc_redist，64 位就装 x64，装完重启
echo          3. Win7 SP1 还要 KB2533623
echo.
pause
endlocal
exit /b 1

:nopy
echo.
echo      [X] 找不到 Python 运行时 %PYEXE%
echo          64 位系统用 py\python.exe，32 位系统用 py32\python.exe
echo.
pause
endlocal
exit /b 1