@echo off
rem ============================================================
rem  选一个"真能跑起来"的 Python，给各个启动脚本用（call 它）
rem  成功: 设置 PYEXE（带引号的路径，或 py/python）和 PYARG，exit /b 0
rem  失败: exit /b 1
rem  不靠 PROCESSOR_ARCHITECTURE 猜位数 —— 直接试跑，谁能跑用谁。
rem ============================================================
set "PYEXE="
set "PYARG="
for %%I in ("%~dp0..") do set "ROOT=%%~fI\"

rem 1) 包里的 64 位
if exist "%ROOT%py\python.exe" (
  "%ROOT%py\python.exe" -c "pass" >nul 2>&1
  if not errorlevel 1 set "PYEXE="%ROOT%py\python.exe""
)

rem 2) 包里的 32 位
if not defined PYEXE if exist "%ROOT%py32\python.exe" (
  "%ROOT%py32\python.exe" -c "pass" >nul 2>&1
  if not errorlevel 1 set "PYEXE="%ROOT%py32\python.exe""
)

rem 3) 都起不来：多半是 Win7 缺 UCRT，按位数补一次再试
if not defined PYEXE if exist "%ROOT%ucrt" (
  if exist "%ROOT%ucrt\x64" if exist "%ROOT%py" copy /y "%ROOT%ucrt\x64\*.dll" "%ROOT%py\" >nul 2>&1
  if exist "%ROOT%ucrt\x86" if exist "%ROOT%py32" copy /y "%ROOT%ucrt\x86\*.dll" "%ROOT%py32\" >nul 2>&1
  if not defined PYEXE if exist "%ROOT%py\python.exe" (
    "%ROOT%py\python.exe" -c "pass" >nul 2>&1
    if not errorlevel 1 set "PYEXE="%ROOT%py\python.exe""
  )
  if not defined PYEXE if exist "%ROOT%py32\python.exe" (
    "%ROOT%py32\python.exe" -c "pass" >nul 2>&1
    if not errorlevel 1 set "PYEXE="%ROOT%py32\python.exe""
  )
)

rem 4) 包里彻底不行：退回本机已安装的 Python（有就用，没有才报错）
if not defined PYEXE (
  py -3 -c "pass" >nul 2>&1
  if not errorlevel 1 ( set "PYEXE=py" & set "PYARG=-3" )
)
if not defined PYEXE (
  python -c "pass" >nul 2>&1
  if not errorlevel 1 set "PYEXE=python"
)

if not defined PYEXE exit /b 1
exit /b 0