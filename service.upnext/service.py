import xbmcaddon
import xbmc
import os
from resources.lib.monitor import Monitor

cwd = xbmcaddon.Addon(id='service.upnext').getAddonInfo('path').decode('utf-8')
BASE_RESOURCE_PATH = xbmc.translatePath(os.path.join(cwd, 'resources', 'lib')).decode('utf-8')
sys.path.append(BASE_RESOURCE_PATH)


# start the monitor
Monitor().run()
