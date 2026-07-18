"""Addon helper script entry point: opens the addon settings."""

import xbmcaddon

from resources.lib.aom.kodi.settings import ADDON_ID


if __name__ == '__main__':
    xbmcaddon.Addon(ADDON_ID).openSettings()
