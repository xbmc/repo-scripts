@ECHO OFF
CLS
COLOR 1B

:Begin
:: Set Addon name based on current directory fullname
FOR /F "Delims=" %%D IN ("%CD%") DO SET AddonName=%%~nxD

:: Extract Version # and SET %addonVer% variable
FOR /F "Tokens=2* Delims= " %%R IN ('FIND /v /n "&_&_&_&" "addon.xml" ^| FIND "[4]"') DO SET addonVer=%%R
SET addonVer=%addonVer:~9,-1%

:: Set window title
TITLE %AddonName%-%addonVer% Build Addon!

:MakeBuildFolder
:: Create Build folder
ECHO ----------------------------------------------------------------------
ECHO.
ECHO Creating \BUILD\addons\%AddonName%\ folder . . .
IF EXIST BUILD (
    RD BUILD /S /Q
)
MD BUILD
ECHO.

:MakeExcludeFile
:: Create exclude file
ECHO ----------------------------------------------------------------------
ECHO.
ECHO Creating exclude.txt file . . .
ECHO.
ECHO .svn>"BUILD\exclude.txt"
ECHO Thumbs.db>>"BUILD\exclude.txt"
ECHO Desktop.ini>>"BUILD\exclude.txt"

ECHO .pyo>>"BUILD\exclude.txt"
ECHO .pyc>>"BUILD\exclude.txt"
ECHO .bak>>"BUILD\exclude.txt"

:MakeReleaseBuild
:: Create release build
ECHO ----------------------------------------------------------------------
ECHO.
ECHO Copying required files to \Build\addons\%AddonName%\ folder . . .
XCOPY resources "BUILD\addons\%AddonName%\resources" /E /Q /I /Y /EXCLUDE:BUILD\exclude.txt
IF EXIST "addon.py" COPY addon.py "BUILD\addons\%AddonName%\"
IF EXIST "default.py" COPY default.py "BUILD\addons\%AddonName%\"
COPY addon.xml "BUILD\addons\%AddonName%\"
ECHO.
ECHO Copying optional files to \Build\addons\%AddonName%\ folder . . .
IF EXIST "icon.png" COPY icon.png "BUILD\addons\%AddonName%\"
IF EXIST "fanart.jpg" COPY fanart.jpg "BUILD\addons\%AddonName%\"
IF EXIST "changelog.txt" COPY changelog.txt "BUILD\addons\%AddonName%\"
IF EXIST "license.txt" COPY license.txt "BUILD\addons\%AddonName%\"

:Cleanup
:: Delete exclude.txt file
ECHO ----------------------------------------------------------------------
ECHO.
ECHO Cleaning up . . .
DEL "BUILD\exclude.txt"
ECHO.
ECHO.

ECHO ----------------------------------------------------------------------
ECHO.
SET /P zipaddon=Do you want create a zip of the Add-on.? [Y/N]:
IF "%zipaddon:~0,1%"=="y" (
    GOTO ZIP_BUILD
) ELSE (
    GOTO Finish
)

:ZIP_BUILD
    set ZIP="%ProgramFiles%\7-Zip\7z.exe"
    set ZIP_ROOT=7z.exe
    set ZIPOPS_EXE=a -tzip -mx=9 "%AddonName%-%addonVer%.zip" "%AddonName%"
    ECHO IF EXIST %ZIP% ( %ZIP% %ZIPOPS_EXE%>>"BUILD\addons\zip_build.bat"
    ECHO   ) ELSE (>>"BUILD\addons\zip_build.bat"
    ECHO   IF EXIST %ZIP_ROOT% ( %ZIP_ROOT% %ZIPOPS_EXE%>>"BUILD\addons\zip_build.bat"
    ECHO     ) ELSE (>>"BUILD\addons\zip_build.bat"
    ECHO     ECHO  not installed!  Skipping .zip compression...>>"BUILD\addons\zip_build.bat"
    ECHO     )>>"BUILD\addons\zip_build.bat"
    ECHO   )>>"BUILD\addons\zip_build.bat"
    cd BUILD\addons\
    ECHO Compressing "BUILD\addons\%AddonName%-%addonVer%.zip"...
    CALL zip_build.bat
    ::cd ..
    ::DEL "BUILD\zip_build.bat"
    DEL zip_build.bat
    GOTO Finish

:Finish
    :: Notify user of completion
    ECHO ======================================================================
    ECHO.
    ECHO Build Complete.
    ECHO.
    ECHO Final build is located in the \BUILD\addons\ folder.
    ECHO.
    ECHO copy: \addons\%AddonName%\ folder from the \BUILD\addons\ folder
    ECHO to: /XBMC/addons/ folder.
    ECHO.
    ECHO ======================================================================
    ECHO.
    GOTO END

:END
    ECHO Scroll up to check for errors.
    PAUSE