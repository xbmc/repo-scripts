@echo off
SET windows=%SystemRoot%\system32\
SET default=C:\
SET cc=%cd%
set desktop1=%USERPROFILE%\desktop
set desktop2=%USERPROFILE%\desktop
SET ERROR="6000"
:Ask
SET /P ANSWER=CHOOSE YOUR OS! (1-WIN/2-LIN/3-MAC)? 

if /i {%ANSWER%}=={1} (goto :continue) 
if /i {%ANSWER%}=={2} (goto :continue)
if /i {%ANSWER%}=={3} (goto :continue)
goto :abort

:continue

pushd \\htpt\tools\smb\
SET cc=%cd%
if /i {%ANSWER%}=={1} (goto :a1) 
if /i {%ANSWER%}=={2} (goto :a2)
if /i {%ANSWER%}=={3} (goto :a3)
pause

:a1
SET ERROR=""
if exist %cc%\htpt2.ico echo COPYING ICON TO WINDOWS...
if exist %cc%\htpt2.ico xcopy %cc%\htpt2.ico %windows% /s /i /y >NUL
if not exist %cc%\htpt2.ico echo CANNOT LOCATE FILE: htpt2.ico && set ERROR=6020

if exist %cc%\HTPT.lnk echo COPYING SHORTCUT TO DESKTOP...
if exist %cc%\HTPT.lnk xcopy %cc%\htpt.lnk %desktop1% /s /i /y >NUL
if not exist %cc%\HTPT.lnk echo CANNOT LOCATE FILE: htpt.lnk && set ERROR=6040
goto :abort

:a2
echo COPYING ICON TO LINUX...
goto :abort

:a3
echo COPYING ICON TO MAC...
goto :abort




:abort
popd
if %ERROR% NEQ "" echo Operation Failed with Error No. %ERROR%
if %ERROR% EQU "" echo Operation Successful. && echo You may now browse your HTPT device.
pause