@echo off
chcp 936 >nul
title ember 诊断
setlocal
set "HERE=%~dp0"
pushd "%HERE%" >nul 2>&1
if errorlevel 1 cd /d "%HERE%"
set "AGENT=%HERE%program\agent.py"

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
echo  [位数] %PROCESSOR_ARCHITECTURE%
echo  [包里] py\ ：
if exist "%HERE%py\python.exe" echo         有
if not exist "%HERE%py\python.exe" echo         没有
echo         py32\ ：
if exist "%HERE%py32\python.exe" echo         有
if not exist "%HERE%py32\python.exe" echo         没有
echo.
echo  [1] 选一个能用的 Python
call "%HERE%program\find_python.cmd"
if errorlevel 1 goto :nopy
echo      选中的: %PYEXE% %PYARG%
%PYEXE% %PYARG% -V
if not "%ERRORLEVEL%"=="0" goto :badpy
echo.
echo  [2] 系统信息
ver
echo.
echo  [3] 完整体检（配置 / 网络 / 模型 / 流式）
echo.
%PYEXE% %PYARG% "%AGENT%" --doctor
echo.
echo  —— 诊断结束 ——
echo  如果上面有红字，把整屏抄下来；logs\ 里的 run-*.log 也有记录。
pause
endlocal
exit /b 0

:nopy
echo.
echo      [X] 找不到能用的 Python
echo          找过：本目录 py\python.exe、py32\python.exe，以及系统里的 py -3 / python
echo          常见原因：只拷了 .cmd 没拷 py\ 和 py32\；或者压缩包解压不完整
echo.
pause
endlocal
exit /b 1

:badpy
echo.
echo      [X] 选中的 Python 起不来，多半是 Win7 缺 UCRT
echo          1. 包里带 ucrt\ 的话，重新双击 run.cmd 会自动补
echo          2. 装一次 vc_redist（64 位装 x64），装完重启
echo          3. Win7 SP1 还要 KB2533623
echo.
pause
endlocal
exit /b 1