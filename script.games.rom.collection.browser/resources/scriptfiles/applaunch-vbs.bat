@echo off
Title Running %*

REM Set Variables
REM Change to Userdata Directory
cd /d "%XBMC_PROFILE_USERDATA%"
cd ..
set XBMCLaunchCmd="%XBMC_HOME%\XBMC.exe"
REM Check for portable mode
echo %XBMC_PROFILE_USERDATA%|find /i "portable_data">nul
if errorlevel 0 if not errorlevel 1 set XBMCLaunchCmd=%XBMCLaunchCmd% -p

echo Stopping XBMC...
echo.
taskkill /f /IM xbmc.exe>nul 2>nul
REM Give it a second to quit
cscript //B //Nologo "%cd%\userdata\addon_data\script.games.rom.collection.browser\scriptfiles\Sleep.vbs" 1
echo Starting %*...
echo.
%*

REM Restart XBMC
echo Restarting XBMC...
echo cscript //B //Nologo "%cd%\userdata\addon_data\script.games.rom.collection.browser\scriptfiles\LaunchXBMC.vbs" %XBMCLaunchCmd%
cscript //B //Nologo "%cd%\userdata\addon_data\script.games.rom.collection.browser\scriptfiles\LaunchXBMC.vbs" %XBMCLaunchCmd%