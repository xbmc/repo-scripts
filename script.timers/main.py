import xbmcaddon
from resources.lib.contextmenu.set_timer import SetTimer
from resources.lib.player.player import Player
from resources.lib.player.player_utils import preview, reset_volume
from resources.lib.timer.pause_timers import reset_pause, set_pause
from resources.lib.utils.settings_utils import (ask_timer_for_edit_in_settings,
                                                delete_timer,
                                                prepare_empty_timer_in_setting,
                                                reset_timer_settings)


def main(argv: 'list[str]') -> None:

    addon = xbmcaddon.Addon()

    if len(argv) == 2 and argv[1] == "play":
        timerid = addon.getSettingInt("timer_id")
        preview(addon=addon, timerid=timerid, player=Player())

    elif len(argv) == 5 and argv[1] == "set_timer":
        SetTimer(label=argv[2], path=argv[3], timer=int(argv[4]))

    elif len(argv) == 2 and argv[1] == "reset_volume":
        reset_volume(addon=addon)

    elif len(argv) == 2 and argv[1] == "set_pause":
        set_pause()

    elif len(argv) == 2 and argv[1] == "reset_pause":
        reset_pause()

    elif len(argv) == 2 and argv[1] == "add":
        prepare_empty_timer_in_setting()

    elif len(argv) == 2 and argv[1] == "back":
        reset_timer_settings()

    elif len(argv) == 2 and argv[1] == "edit":
        ask_timer_for_edit_in_settings()

    elif len(argv) == 2 and argv[1] == "delete":
        delete_timer()
        addon.openSettings()

    elif len(argv) == 2 and argv[1] == "save":
        # actual saving happens in scheduler (listener) which is triggered by next line
        reset_timer_settings()
        addon.openSettings()

    else:
        reset_timer_settings()
        addon.openSettings()
