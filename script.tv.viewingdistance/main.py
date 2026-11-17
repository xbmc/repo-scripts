# -*- coding: utf-8 -*-
"""TV Viewing Distance Calculator for Kodi.

Two questions, one answer screen: enter the TV diagonal to get the 16:9 screen size,
the SMPTE (30 deg) and THX (40 deg) seating distances and a suggested mount height,
or enter the seating distance to get the TV size range that fits it.
"""
import xbmcaddon
import xbmcgui

import calc

ADDON = xbmcaddon.Addon()
NAME = ADDON.getAddonInfo('name')
FOOTER = ('Guideline values only. Plan a whole TV wall to scale: '
          'getmediawall.com/design-your-wall')
CHOICES = ['I know my TV size', 'I know my seating distance']


def ask_number(heading):
    value = xbmcgui.Dialog().numeric(0, heading)
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return number if number > 0 else None


def run():
    dialog = xbmcgui.Dialog()
    choice = dialog.select(NAME, CHOICES)
    if choice == 0:
        diagonal = ask_number('TV screen diagonal (inches)')
        if diagonal is None:
            return
        lines = calc.report_for_tv(diagonal)
    elif choice == 1:
        distance = ask_number('Seating distance (inches)')
        if distance is None:
            return
        lines = calc.report_for_distance(distance)
    else:
        return
    dialog.textviewer(NAME, '\n'.join(lines + ['', FOOTER]))


