from datetime import datetime

import xbmcaddon
import xbmcgui
from resources.lib.player.player_utils import get_types_replaced_by_type
from resources.lib.timer.period import Period
from resources.lib.timer.timer import (MEDIA_ACTION_START,
                                       MEDIA_ACTION_START_AT_END,
                                       MEDIA_ACTION_START_STOP,
                                       MEDIA_ACTION_STOP,
                                       MEDIA_ACTION_STOP_AT_END,
                                       MEDIA_ACTION_STOP_START, Timer)
from resources.lib.utils import datetime_utils
from resources.lib.utils.settings_utils import (CONFIRM_CUSTOM, CONFIRM_NO,
                                                CONFIRM_YES)

MIN_PRIO = -12
MAX_PRIO = 12
LOW_PRIO_MARK = -10
HIGH_PRIO_MARK = 10
DEFAULT_PRIO = 0


def get_next_lower_prio(timers: 'list[Timer]') -> int:

    _min = min(timers, key=lambda t: t.priority if t.priority >
               LOW_PRIO_MARK else DEFAULT_PRIO).priority
    return _min - 1 if _min > LOW_PRIO_MARK + 1 else _min


def get_next_higher_prio(timers: 'list[Timer]') -> int:

    _max = max(timers, key=lambda t: t.priority if t.priority <
               HIGH_PRIO_MARK else DEFAULT_PRIO).priority
    return _max + 1 if _max < HIGH_PRIO_MARK - 1 else _max


def determine_overlappings(timer: Timer, timers: 'list[Timer]', base: datetime, ignore_extra_prio=False, to_display=False) -> 'list[Timer]':

    def _is_exact_match(period1: Period, period2: Period, base: datetime) -> bool:

        if type(period1.start) == type(period2.start):
            return period1.start == period2.start and period1.end == period2.end

        return _is_exact_match(Period.to_datetime_period(period1, base), Period.to_datetime_period(period2, base), base)

    def _disturbs(types: 'list[str]', type2: str, media_action1: int, media_action2: int, period1: Period, period2: Period, base: datetime) -> bool:

        if media_action1 == MEDIA_ACTION_START_STOP:
            play_media1 = period1.start
            stop_media1 = period1.end
            replace = type2 in types

        elif media_action1 == MEDIA_ACTION_START:
            play_media1 = period1.start
            stop_media1 = None
            replace = type2 in types

        elif media_action1 == MEDIA_ACTION_START_AT_END:
            play_media1 = period1.end
            stop_media1 = None
            replace = type2 in types

        elif media_action1 == MEDIA_ACTION_STOP_START:
            play_media1 = period1.end
            stop_media1 = period1.start
            replace = type2 in types

        elif media_action1 == MEDIA_ACTION_STOP:
            play_media1 = None
            stop_media1 = period1.start
            replace = True

        elif media_action1 == MEDIA_ACTION_STOP_AT_END:
            play_media1 = None
            stop_media1 = period1.end
            replace = True

        else:
            return False

        if not replace:
            return False

        if _is_exact_match(period1, period2, base):
            return True

        elif media_action2 == MEDIA_ACTION_START_STOP:

            if play_media1:
                s, e, hit = period2.hit(play_media1, base)
                if s and e and hit:
                    return True

            if stop_media1:
                s, e, hit = period2.hit(stop_media1, base)
                if s and e and hit:
                    return True

            return False

        elif media_action2 == MEDIA_ACTION_STOP_START:

            if play_media1:
                s, e, hit = period2.hit(play_media1, base)
                return s and e and hit

        return False

    timer_replace_types = get_types_replaced_by_type(timer.media_type)

    overlapping_timers: 'list[Timer]' = list()
    for t in timers:

        if t.id == timer.id or (ignore_extra_prio and (t.priority <= LOW_PRIO_MARK or t.priority >= HIGH_PRIO_MARK)):
            continue

        t_replace_types = get_types_replaced_by_type(t.media_type)

        overlapping_periods: 'list[Period]' = list()
        for p in t.periods:

            for n in timer.periods:

                if _disturbs(timer_replace_types, t.media_type, timer.media_action, t.media_action, n, p, base) or _disturbs(t_replace_types, timer.media_type, t.media_action, timer.media_action, p, n, base):
                    overlapping_periods.append(p)

        if overlapping_periods:

            overlapping_timers.append(t)

            if to_display:

                if t.is_timer_by_date():
                    days = [p.start.weekday()]

                else:
                    days = [
                        datetime_utils.WEEKLY] if datetime_utils.WEEKLY in t.days else list()
                    days.extend([p.start.days for p in overlapping_periods])

                t.days = days
                t.periods = overlapping_periods

    overlapping_timers.sort(key=lambda t: (t.days, t.date, t.start,
                                           t.media_action, t.system_action))

    return overlapping_timers


def ask_overlapping_timers(timer: Timer, overlapping_timers: 'list[Timer]') -> int:

    addon = xbmcaddon.Addon()
    now = datetime.today()

    earlier_timers = [
        t for t in overlapping_timers if datetime_utils.time_diff(t.periods[0].start, timer.periods[0].start, now) > 0]

    lines = list()
    for t in overlapping_timers:
        lines.append(t.format("$L ($H)", 50, 12))
    lines.append("\n" + addon.getLocalizedString(32052) %
                 timer.format("$L ($T)", 50, 12))

    answer = xbmcgui.Dialog().yesnocustom(heading=addon.getLocalizedString(
        32050 if earlier_timers else 32051), message="\n".join(lines), customlabel=addon.getLocalizedString(32022))
    if answer == CONFIRM_YES:
        timer.priority = get_next_higher_prio(overlapping_timers)
        return CONFIRM_YES

    elif answer == CONFIRM_NO:
        timer.priority = get_next_lower_prio(overlapping_timers)
        return CONFIRM_YES

    return CONFIRM_CUSTOM
