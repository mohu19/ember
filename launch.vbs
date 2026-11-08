' 备用入口 2：双击 run.cmd / run.bat 都没反应时用这个。
' 它直接用 cmd.exe 打开 run.cmd，完全不经过 .cmd/.bat 的文件关联设置。
Option Explicit
Dim fso, sh, here, cmdline
Set fso = CreateObject("Scripting.FileSystemObject")
here = fso.GetParentFolderName(WScript.ScriptFullName)
If Not fso.FileExists(here & "\run.cmd") Then
    MsgBox "找不到 run.cmd。" & vbCrLf & "请把整个 ember 文件夹一起解压后再试。", 16, "ember"
    WScript.Quit 1
End If
Set sh = CreateObject("WScript.Shell")
sh.CurrentDirectory = here
cmdline = "cmd.exe /k """ & here & "\run.cmd"""
sh.Run cmdline, 1, False