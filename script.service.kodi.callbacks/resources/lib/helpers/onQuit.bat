@echo off
:loop
tasklist | find " %1 " >nul
if not errorlevel 1 (
    timeout /t 2 >nul
    goto :loop
)
REM Put the code you want to run here
notepad.exe