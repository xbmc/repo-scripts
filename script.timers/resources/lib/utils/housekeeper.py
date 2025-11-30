from datetime import datetime

import xbmc
import xbmcaddon
from resources.lib.timer.storage import Storage
from resources.lib.timer.timer import TIMER_BY_DATE, Timer
from resources.lib.utils import datetime_utils

ACTION_NOTHING = 0
ACTION_UPDATE = 1
ACTION_DELETE = 2


def check_timer(timer: Timer, threshold: datetime) -> int:

    if timer.is_weekly_timer() or timer.is_off():
        return ACTION_NOTHING

    timer.init()
    timer.apply(dtd=datetime_utils.DateTimeDelta(threshold))
    if timer.date == "":
        timer.to_timer_by_date(timer.upcoming_event)
        return ACTION_UPDATE

    last_known_date = datetime_utils.parse_date_str(timer.date)
    if timer.upcoming_event:
        timer.date = datetime_utils.to_date_str(timer.upcoming_event)

    weekdays_to_remove = list()
    has_upcoming = False
    for p in timer.periods:
        s, e, hit = p.hit(threshold, last_known_date)
        start = threshold + s
        end = threshold + e
        if not hit and end < threshold:
            weekdays_to_remove.append(start.weekday())
        elif hit and timer.is_timer_by_date():
            return ACTION_NOTHING
        elif threshold <= start <= end:
            has_upcoming = True

    timer.days = [day for day in timer.days if day not in weekdays_to_remove]
    if not timer.days or timer.days == [TIMER_BY_DATE] and not has_upcoming:
        return ACTION_DELETE

    elif weekdays_to_remove:
        return ACTION_UPDATE

    return ACTION_NOTHING


def cleanup_outdated_timers() -> None:

    addon = xbmcaddon.Addon()
    if not addon.getSettingBool("clean_outdated"):
        return

    storage = Storage()
    timers = storage.load_timers_from_storage()

    updated_any = False
    timers_to_remove = list()

    now = datetime.today()
    for timer in timers:
        action = check_timer(timer, now)
        if action == ACTION_UPDATE:
            updated_any = True
        elif action == ACTION_DELETE:
            timers_to_remove.append(timer)

    for timer in timers_to_remove:
        xbmc.log(f"remove outdated timer: {str(timer)}", xbmc.LOGINFO)
        timers.remove(timer)

    if updated_any or timers_to_remove:
        storage.replace_storage(timers)
