

taskkill /f /IM XBMC.exe

REM Launch app
%*


REM SOMETIMES xbmc starts too fast, and on some hardware if there is still a millisecond of sound being used, XBMC starts witout sound and some emulators say there is a problem with the sound hardware. If so, remove comment:
REM sleep 1


REM Done? Restart XBMC
"XBMC.exe"


