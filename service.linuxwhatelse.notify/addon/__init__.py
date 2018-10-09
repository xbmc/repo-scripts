import os

import xbmc
import xbmcaddon

PROFILE_PATH = xbmc.translatePath(xbmcaddon.Addon().getAddonInfo('profile'))
CACHE_DIR = os.path.join(PROFILE_PATH, 'cache')

if not os.path.exists(CACHE_DIR):
    os.makedirs(CACHE_DIR)

from addon import routes  # noqa:F401, isort:skip
