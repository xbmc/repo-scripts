import time

import xbmcaddon
import xbmcgui
from resources.lib.timer import storage
from resources.lib.timer.timer import (DEFAULT_TIME, END_TYPE_NO, FADE_OFF,
                                       MEDIA_ACTION_NONE, SYSTEM_ACTION_NONE,
                                       Timer)
from resources.lib.utils.datetime_utils import WEEKLY

_ON_SETTING_CHANGE_EVENTS = "onSettingChangeEvents"
_SETTING_CHANGE_EVENTS_MAX_SECS = 5
_SETTING_CHANGE_EVENTS_ACTIVE = 0


def deactivate_on_settings_changed_events() -> None:

    addon = xbmcaddon.Addon()
    now = str(int(time.time()))
    addon.setSetting(_ON_SETTING_CHANGE_EVENTS, now)


def activate_on_settings_changed_events() -> None:

    addon = xbmcaddon.Addon()
    addon.setSetting(_ON_SETTING_CHANGE_EVENTS,
                     str(_SETTING_CHANGE_EVENTS_ACTIVE))


def is_settings_changed_events() -> bool:

    addon = xbmcaddon.Addon()
    current = int("0%s" % addon.getSetting(_ON_SETTING_CHANGE_EVENTS))
    now = int(time.time())
    return now - current > _SETTING_CHANGE_EVENTS_MAX_SECS


def trigger_settings_changed_event() -> None:

    deactivate_on_settings_changed_events()
    activate_on_settings_changed_events()


def prepare_empty_timer_in_setting(timer_id=None) -> None:

    if timer_id == None:
        timer_id = storage.get_next_id()

    deactivate_on_settings_changed_events()
    addon = xbmcaddon.Addon()
    addon.setSettingInt("timer_id", timer_id)
    addon.setSettingString("timer_label", addon.getLocalizedString(32257))
    addon.setSetting("timer_days", "")
    addon.setSetting("timer_start", DEFAULT_TIME)
    addon.setSettingInt("timer_end_type", END_TYPE_NO)
    addon.setSetting("timer_duration", DEFAULT_TIME)
    addon.setSetting("timer_end", DEFAULT_TIME)
    addon.setSettingInt("timer_system_action", SYSTEM_ACTION_NONE)
    addon.setSettingInt("timer_media_action", MEDIA_ACTION_NONE)
    addon.setSettingString("timer_path", "")
    addon.setSettingString("timer_mediatype", "")
    addon.setSettingBool("timer_repeat", False)
    addon.setSettingBool("timer_shuffle", False)
    addon.setSettingBool("timer_resume", True)
    addon.setSettingInt("timer_fade", FADE_OFF)
    addon.setSettingInt(
        "timer_vol_min", addon.getSettingInt("vol_min_default"))
    addon.setSettingInt("timer_vol_max", addon.getSettingInt("vol_default"))
    addon.setSettingBool("timer_notify", True)
    activate_on_settings_changed_events()


def reset_timer_settings() -> None:

    prepare_empty_timer_in_setting(timer_id=-1)


def save_timer_from_settings() -> None:

    addon = xbmcaddon.Addon()

    timer_id = addon.getSettingInt("timer_id")

    if timer_id < 0:
        return

    days = addon.getSetting("timer_days")
    if days not in ["", str(WEEKLY)]:
        days = [int(d) for d in days.split("|")]
    else:
        days = list()

    timer = Timer(timer_id)
    timer.days = days
    timer.duration = addon.getSetting("timer_duration")
    timer.end = addon.getSetting("timer_end")
    timer.end_type = addon.getSettingInt("timer_end_type")
    timer.fade = addon.getSettingInt("timer_fade")
    timer.label = addon.getSettingString("timer_label")
    timer.media_action = addon.getSettingInt("timer_media_action")
    timer.media_type = addon.getSettingString("timer_mediatype")
    timer.notify = addon.getSettingBool("timer_notify")
    timer.path = addon.getSettingString("timer_path")
    timer.repeat = addon.getSettingBool("timer_repeat")
    timer.resume = addon.getSettingBool("timer_resume")
    timer.shuffle = addon.getSettingBool("timer_shuffle")
    timer.start = addon.getSetting("timer_start")
    timer.system_action = addon.getSettingInt("timer_system_action")
    timer.vol_min = addon.getSettingInt("timer_vol_min")
    timer.vol_max = addon.getSettingInt("timer_vol_max")

    storage.save_timer(timer=timer)


def select_timer(multi=False, extra=None) -> 'tuple[list[Timer], list[int]]':

    addon = xbmcaddon.Addon()

    timers = storage.load_timers_from_storage()
    if not timers and not extra:
        xbmcgui.Dialog().notification(addon.getLocalizedString(
            32000), addon.getLocalizedString(32258))

        return None, None

    timers.sort(key=lambda t: (t.days, t.start,
                t.media_action, t.system_action))

    options = extra or list()

    options.extend(["%s (%s)" % (
        timer.label,
        timer.periods_to_human_readable()
    ) for timer in timers])

    if multi:
        selection = xbmcgui.Dialog().multiselect(
            addon.getLocalizedString(32103), options)
    else:
        selection = [xbmcgui.Dialog().select(
            addon.getLocalizedString(32103), options)]

    if not selection or -1 in selection:
        return timers, None
    else:
        return timers, selection


def delete_timer() -> None:

    timers, idx = select_timer(multi=True)
    if idx is None:
        return

    for i in idx:
        storage.delete_timer(timers[i].id)

    trigger_settings_changed_event()

    addon = xbmcaddon.Addon()
    xbmcgui.Dialog().notification(addon.getLocalizedString(
        32000), addon.getLocalizedString(32029))


def ask_timer_for_edit_in_settings() -> None:

    timers, idx = select_timer()
    if idx is None:
        return

    timer = timers[idx[0]]
    load_timer_into_settings(timer=timer)


def load_timer_into_settings(timer: Timer) -> None:

    addon = xbmcaddon.Addon()
    deactivate_on_settings_changed_events()
    addon.setSettingInt("timer_id", timer.id)
    addon.setSettingString("timer_label", timer.label)
    addon.setSetting("timer_days", "|".join([str(d) for d in timer.days]))
    addon.setSetting("timer_start", timer.start)
    addon.setSettingInt("timer_end_type", timer.end_type)
    addon.setSetting("timer_duration", timer.duration)
    addon.setSetting("timer_end", timer.end)
    addon.setSettingInt("timer_system_action", timer.system_action)
    addon.setSettingInt("timer_media_action", timer.media_action)
    addon.setSettingString("timer_path", timer.path)
    addon.setSettingString("timer_mediatype", timer.media_type)
    addon.setSettingBool("timer_repeat", timer.repeat)
    addon.setSettingBool("timer_shuffle", timer.shuffle)
    addon.setSettingBool("timer_resume", timer.resume)
    addon.setSettingInt("timer_fade", timer.fade)
    addon.setSettingInt("timer_vol_min", timer.vol_min)
    addon.setSettingInt("timer_vol_max", timer.vol_max)
    addon.setSettingBool("timer_notify", timer.notify)
    activate_on_settings_changed_events()
