# Put this file into the scripts (addons) folder to be executed when XBMC starts, which is:
## /home/<username>/.xbmc/userdata on XBMC for Linux Dharma version;
## /home/<username>/.xbmc/scripts on XBMC for Linux pre-Dharma version;
## %APPDATA%\XBMC\userdata on XBMC for Windows Dharma version;
## Q:\scripts on XBMC4XBOX 3.0.1 version;

# This is not needed for XBMC Eden releases;
# If you already have an autoexec.py file, just append this file contents to the existing one.

import os
import xbmc

# Change this path according your XBMC setup (you may not need the '..' and 'addons')
script_path = xbmc.translatePath(os.path.join(os.getcwd(),'..','addons','script.xbmc-pbx-addon','bgservice.py'))
xbmc.executescript(script_path)

