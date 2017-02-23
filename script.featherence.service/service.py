import xbmc, xbmcgui
import os, sys
import subprocess
import xbmcaddon

from variables import *
from modules import *
	
if os.path.exists(skin_path) and xbmc.getCondVisibility('System.HasAddon(skin.featherence)') and 1 + 1 == 3:
	xbmc.sleep(5000)
	from shared_modules4 import *
	printpoint, guisettings_file_ = guicheck(admin)
	guikeeper(admin, guicheck=printpoint, guiread=guisettings_file_)
	xbmc.sleep(1000)

xbmc.sleep(2000)

mode5('', admin, 'demon', '')
