@echo off
chcp 936 >nul
title ember
setlocal enabledelayedexpansion
set "HERE=%~dp0"
pushd "%HERE%" >nul 2>&1
if errorlevel 1 cd /d "%HERE%"

rem ---------- 0) 包是不是完整的 ----------
if not exist "%HERE%program\agent.py" goto :nofile
if not exist "%HERE%config.txt" goto :noconfig

rem ---------- 1) 自动挑对位数的 Python（32 位系统用 py32，64 位用 py）----------
set "PYEXE=%HERE%py\python.exe"
if /i "%PROCESSOR_ARCHITECTURE%"=="x86" if not defined PROCESSOR_ARCHITEW6432 set "PYEXE=%HERE%py32\python.exe"
if not exist "%PYEXE%" goto :nopy

rem ---------- 2) Python 能不能起来；起不来且带了离线 UCRT 补丁就先装补丁再试 ----------
"%PYEXE%" -c "pass" >nul 2>&1
if "%ERRORLEVEL%"=="0" goto :ready
if exist "%HERE%ucrt" call :install_ucrt
"%PYEXE%" -c "pass" >nul 2>&1
if not "%ERRORLEVEL%"=="0" goto :badpy

:ready
rem ---------- 3) 启动（没 key 会在 python 里问，全程只起一次进程）----------
echo   启动 ember（模型 / 目录以 config.txt 为准）
echo   运行中敲 /stop 回车（或 ESC / Ctrl+C）可中断；/help 看命令，/exit 退出
echo.
set "PYTHONIOENCODING="
"%PYEXE%" "%HERE%program\agent.py" --bootstrap %*
set "RC=%ERRORLEVEL%"
echo.
if "%RC%"=="3" goto :nokey
if not "%RC%"=="0" (
  echo   ember 异常退出（退出码 %RC%）
  echo   把上面最后几行报错抄下来，或双击 diagnose.cmd 看诊断
) else (
  echo   ember 已退出
)
echo.
echo   双击没反应 / 窗口一闪而过？按顺序试：run.bat -^> launch.vbs -^> diagnose.cmd
echo   （详见 README-FIRST.txt 的"双击没反应"）
echo.
pause
endlocal
exit /b 0

:nokey
echo   这次没填 API Key，已退出（下次双击 run.cmd 还会再问）。
echo   手填也行：记事本打开 config.txt，把 sk- 开头那一串粘到 api_key = 后面。
echo.
pause
endlocal
exit /b 0

:install_ucrt
rem v2.3.1: copy by target arch, never put x64 dll into py32
if exist "%HERE%ucrt\x64" if exist "%HERE%py" copy /y "%HERE%ucrt\x64\*.dll" "%HERE%py\" >nul 2>&1
if exist "%HERE%ucrt\x86" if exist "%HERE%py32" copy /y "%HERE%ucrt\x86\*.dll" "%HERE%py32\" >nul 2>&1
goto :eof
:nofile
echo.
echo   [X] 这个文件夹里没有 agent.py —— 包不完整，或者只把 run.cmd 单独拷了出来。
echo       解决：把整个 ember 文件夹一起解压，再双击文件夹里的 run.cmd
echo.
pause
exit /b 1

:noconfig
echo.
echo   [X] 缺少 config.txt（配置和 key 都存在这个文件里）。
echo       解决：重新解压完整包，或从别的机器拷一份 config.txt 过来
echo.
pause
exit /b 1

:nopy
echo.
echo   [X] 找不到能用的 Python 运行时: %PYEXE%
echo       64 位系统用 py\python.exe，32 位系统用 py32\python.exe
echo       这个包可能解压不完整；也可以手动补上缺的那个 py\ / py32\ 文件夹
echo.
pause
exit /b 1

:badpy
echo.
echo   [X] 包里的 Python 启动失败: %PYEXE%
echo       最常见原因：Windows 7 缺"通用 C 运行库"（UCRT）。
echo.
echo       三种办法，任选一种：
echo         1) 如果包里有 ucrt\x64 或 ucrt\x86 目录，重新双击 run.cmd 会自动装
echo         2) 以管理员身份装一次 vc_redist（64 位装 x64，32 位装 x86），装完重启
echo         3) 在装好 UCRT 的机器上跑 tools\pack_ucrt.py 生成 ucrt\ 目录再拷过来
echo       Win7 SP1 还需要 KB2533623；详见 README-FIRST.txt"缺 UCRT 怎么办"
echo.
pause
exit /b 1