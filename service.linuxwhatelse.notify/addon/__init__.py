import os

import xbmc
import xbmcaddon

import mapper

addon = xbmcaddon.Addon()
player = xbmc.Player()


mpr = mapper.Mapper()


profile_path = xbmc.translatePath(addon.getAddonInfo('profile'))
cache_dir = os.path.join(profile_path, 'cache')
if not os.path.exists(cache_dir):
    os.makedirs(cache_dir)