import sys

import xbmc
import xbmcaddon

from resources.lib.player import player_utils
from resources.lib.player.player import Player

addon = xbmcaddon.Addon()

if __name__ == "__main__":

    if len(sys.argv) == 3 and sys.argv[1] == "play":
        player_utils.preview(addon=addon, timer=int(
            sys.argv[2]), player=Player())

    elif len(sys.argv) == 2 and sys.argv[1] == "reset_volume":
        player_utils.reset_volume(addon=addon)

    else:
        addon.openSettings()
