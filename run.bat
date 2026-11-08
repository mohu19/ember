@echo off
rem 备用入口 1：双击 run.cmd 没反应时用这个。
rem .bat 和 .cmd 在注册表里是两套文件关联，坏一个另一个通常还能用。
if not exist "%~dp0run.cmd" (
  echo 找不到 run.cmd，请把整个 ember 文件夹一起解压后再试。
  pause
  exit /b 1
)
call "%~dp0run.cmd" %*