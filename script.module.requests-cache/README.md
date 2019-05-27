script.module.requests-cache
======================

Python [requests-cache](https://github.com/reclosedev/requests-cache) library packed for KODI.

```
import requests_cache

#define the cache file to reside in the ..\Kodi\userdata\addon_data\(your addon)
addonUserDataFolder = xbmc.translatePath(addon.getAddonInfo('profile'))
CACHE_FILE          = xbmc.translatePath(os.path.join(addonUserDataFolder, 'requests_cache'))

#cache expires after: 86400=1day   604800=7 days
requests_cache.install_cache(CACHE_FILE, backend='sqlite', expire_after=604800 )  
```