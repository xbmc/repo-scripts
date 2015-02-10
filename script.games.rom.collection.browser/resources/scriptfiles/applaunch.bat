
cd /d "%XBMC_PROFILE_USERDATA%"
cd ..
set XBMCLaunchCmd="%XBMC_HOME%\XBMC.exe"
REM Check for portable mode
echo %XBMC_PROFILE_USERDATA%|find /i "portable_data">nul
if errorlevel 0 if not errorlevel 1 set XBMCLaunchCmd=%XBMCLaunchCmd% -p

echo Stopping XBMC...
echo.
taskkill /f /IM xbmc.exe>nul 2>nul

echo Starting %*...
echo.
%*


REM SOMETIMES xbmc starts too fast, and on some hardware if there is still a millisecond of sound being used, XBMC starts witout sound and some emulators say there is a problem with the sound hardware. If so, remove the REM of the next line:
REM timeout 1

REM Restart XBMC
echo Restarting XBMC...

REM Done? Restart XBMC
%XBMCLaunchCmd%


