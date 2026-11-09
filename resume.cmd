@echo off
chcp 936 >nul
title ember - 选择历史会话
setlocal enabledelayedexpansion
set "HERE=%~dp0"
pushd "%HERE%" >nul 2>&1
if errorlevel 1 cd /d "%HERE%"

rem ---------- 自动挑对位数的 Python（32 位系统用 py32，64 位用 py）----------
call "%HERE%program\find_python.cmd"
if errorlevel 1 goto :nopy
:menu
cls
echo ==================================================
echo    ember  ^|  选择要继续的历史对话
echo ==================================================
echo.
%PYEXE% %PYARG% -c "pass" >nul 2>&1
if not "%ERRORLEVEL%"=="0" (
  if exist "%HERE%ucrt\x64" if exist "%HERE%py" copy /y "%HERE%ucrt\x64\*.dll" "%HERE%py\" >nul 2>&1
  if exist "%HERE%ucrt\x86" if exist "%HERE%py32" copy /y "%HERE%ucrt\x86\*.dll" "%HERE%py32\" >nul 2>&1
  %PYEXE% %PYARG% -c "pass" >nul 2>&1
)
if not "%ERRORLEVEL%"=="0" (
  echo   [X] Python 起不来，多半是 Win7 缺 UCRT，详见 diagnose.cmd
  pause
  exit /b 1
)
%PYEXE% %PYARG% "%HERE%program\agent.py" --list-sessions
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
%PYEXE% %PYARG% "%HERE%program\agent.py" --resume !N!
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

:nopy
echo.
echo   [X] 找不到能用的 Python。
echo       找过：本目录 py\python.exe、py32\python.exe，以及系统里的 py -3 / python
echo       常见原因：只拷了 .cmd，没把整个文件夹（含 py\ 和 py32\）一起拷；
echo                 或者压缩包解压不完整。
echo.
pause
exit /b 1
