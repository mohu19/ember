@echo off
chcp 936 >nul
title ember - 选择历史会话
setlocal enabledelayedexpansion
set "HERE=%~dp0"
pushd "%HERE%" >nul 2>&1
if errorlevel 1 cd /d "%HERE%"

rem ---------- 自动挑对位数的 Python（32 位系统用 py32，64 位用 py）----------
set "PYEXE=%HERE%py\python.exe"
if /i "%PROCESSOR_ARCHITECTURE%"=="x86" if not defined PROCESSOR_ARCHITEW6432 set "PYEXE=%HERE%py32\python.exe"
if not exist "%PYEXE%" (
  echo.
  echo   [X] 找不到能用的 Python 运行时: %PYEXE%
  echo       64 位系统用 py\python.exe，32 位系统用 py32\python.exe
  echo       这个包可能解压不完整；也可以手动补上缺的那个 py\ / py32\ 文件夹
  echo.
  pause
  exit /b 1
)
:menu
cls
echo ==================================================
echo    ember  ^|  选择要继续的历史对话
echo ==================================================
echo.
"%PYEXE%" -c "pass" >nul 2>&1
if not "%ERRORLEVEL%"=="0" (
  if exist "%HERE%ucrt\x64" if exist "%HERE%py" copy /y "%HERE%ucrt\x64\*.dll" "%HERE%py\" >nul 2>&1
  if exist "%HERE%ucrt\x86" if exist "%HERE%py32" copy /y "%HERE%ucrt\x86\*.dll" "%HERE%py32\" >nul 2>&1
  "%PYEXE%" -c "pass" >nul 2>&1
)
if not "%ERRORLEVEL%"=="0" (
  echo   [X] Python 起不来，多半是 Win7 缺 UCRT，详见 diagnose.cmd
  pause
  exit /b 1
)
"%PYEXE%" "%HERE%program\agent.py" --list-sessions
echo.
set "N="
set /p N=输入编号后回车（直接回车=退出）: 
if "!N!"=="" goto :end
rem v2.3.1：先把输入写进临时文件再校验，绝不把用户输入拼进命令行（旧写法可被 & 注入）
set "CHK=%TEMP%\ember-num-check.txt"
>"%CHK%" echo !N!
findstr /r /c:"^[0-9][0-9]*$" "%CHK%" >nul
set "CHKRC=%ERRORLEVEL%"
del "%CHK%" >nul 2>&1
if not "%CHKRC%"=="0" goto :badnum
"%PYEXE%" "%HERE%program\agent.py" --resume !N!
echo.
echo   —— 本次会话已结束 ——
set "AGAIN="
set /p AGAIN=再选一个会话？[y=回到列表 / 回车=退出]: 
if /i "!AGAIN!"=="y" goto :menu
:end
endlocal
exit /b 0

:badnum
echo.
echo   只能输数字编号（或直接回车退出），已返回列表。
ping -n 2 127.0.0.1 >nul 2>nul
goto :menu