
REM Make sure that this path points to your kodi installation
set KodiLaunchCmd="%PROGRAMFILES%\Kodi\Kodi.exe"

echo Stopping Kodi...
echo.
taskkill /f /IM Kodi.exe>nul 2>nul

echo Starting %*...
echo.
%*


REM SOMETIMES Kodi starts too fast, and on some hardware if there is still a millisecond of sound being used, Kodi starts witout sound and some emulators say there is a problem with the sound hardware. If so, remove the REM of the next line:
REM timeout 1

REM Restart Kodi
echo Restarting Kodi...

REM Done? Restart Kodi
%KodiLaunchCmd%


