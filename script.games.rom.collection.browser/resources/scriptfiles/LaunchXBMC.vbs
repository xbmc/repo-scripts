WScript.Sleep(1500)
On Error Resume Next
XBMCPath="""" & wscript.arguments(0) & """"
XBMCParams=wscript.arguments(1)

Dim objShell
Set objShell = WScript.CreateObject ("WScript.shell")
objShell.run XBMCPath & " " & XBMCParams