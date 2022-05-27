import sys

import xbmcaddon

from resources.lib.contextmenu.set_timer import SetTimer
from resources.lib.player.player import Player
from resources.lib.player.player_utils import preview, reset_volume

addon = xbmcaddon.Addon()

if __name__ == "__main__":

    if len(sys.argv) == 3 and sys.argv[1] == "play":
        preview(addon=addon, timerid=int(
            sys.argv[2]), player=Player())

    elif len(sys.argv) == 5 and sys.argv[1] == "set_timer":
        SetTimer(label=sys.argv[2], path=sys.argv[3], timer=int(sys.argv[4]))

    elif len(sys.argv) == 2 and sys.argv[1] == "reset_volume":
        reset_volume(addon=addon)

    else:
        addon.openSettings()
