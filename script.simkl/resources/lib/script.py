#!/usr/bin/python
# -*- coding: UTF-8 -*-
"""The RunScript actions. The buttons of the settings page hand their action to the running service; a skin or a keymap can
do the same for the focused list item (RunScript(script.simkl, action=mark|unmark|plantowatch|rate), rate with an
optional rating=1-10, 0 removes it, none asks); action=show_log shows the Simkl lines of the Kodi log; called without
an action, the settings open."""

import collections
import os
import re
import sys

import xbmcaddon
import xbmcgui
import xbmcvfs

from resources.lib import focus

ADDON_ID = 'script.simkl'
SERVICE_ACTIONS =('login', 'logout', 'import_check', 'import_reset')
ITEM_ACTIONS = {'mark': 'ctx_mark', 'unmark': 'ctx_unmark', 'plantowatch': 'ctx_plantowatch', 'rate': 'ctx_rate'}
CONFIRMATIONS = {'logout': 32261, 'import_reset': 32260}
LOG_STAMP = re.compile(r'^\d{4}-\d{2}-\d{2} (\d{2}:\d{2}:\d{2})\.\d{3} T:\d+\s+(\w+) <general>: (?:\[script\.simkl\] )?(.*)$')
LOG_SHOWN = 300
LOG_SAVED = 2000


def simkl_lines(lines, keep=LOG_SAVED):
    """The Kodi log reduced to this add-on: every stamped line naming script.simkl, and a whole block (a stamped line
    with its unstamped continuation lines, the shape of a Python error) when any line of it does. Returns the last keep
    lines twice: as they are, for a file, and compact (time, level, message), for the screen."""
    raw = collections.deque(maxlen=keep)
    compact = collections.deque(maxlen=keep)
    block = []

    def flush():
        if any('script.simkl' in line for line in block):
            for line in block:
                match = LOG_STAMP.match(line)
                raw.append(line)
                compact.append('%s %s: %s' % match.groups() if match else '  ' + line.strip())
        del block[:]

    for line in lines:
        line = line.rstrip('\r\n')
        if LOG_STAMP.match(line):
            flush()
        block.append(line)
    flush()
    return list(raw), list(compact)


def show_log(addon):
    log_path = xbmcvfs.translatePath('special://logpath/kodi.log')
    try:
        with open(log_path, 'r', encoding='utf-8', errors='replace') as handle:
            raw, compact = simkl_lines(handle)
    except OSError as exc:
        focus.toast(addon, str(exc))
        return
    if not raw:
        focus.toast(addon, addon.getLocalizedString(32291))
        return
    folder = xbmcvfs.translatePath(addon.getAddonInfo('profile'))
    saved = os.path.join(folder, 'simkl.log')
    try:
        xbmcvfs.mkdirs(folder)
        with open(saved, 'w', encoding='utf-8') as handle:
            handle.write('\n'.join(raw) + '\n')
        head = addon.getLocalizedString(32290).format(saved)
    except OSError:
        head = log_path
    xbmcgui.Dialog().textviewer(addon.getLocalizedString(32289), head + '\n\n' + '\n'.join(compact[-LOG_SHOWN:]), True)


def main():
    addon = xbmcaddon.Addon(ADDON_ID)
    args = dict(arg.strip().split('=', 1) for arg in sys.argv[1:] if '=' in arg)
    action = args.get('action', '').strip()
    if action in ITEM_ACTIONS:
        payload = focus.from_infolabels()
        rating = args.get('rating', '').strip() if action == 'rate' else ''
        given = rating.isdigit() and int(rating) <= 10
        # what the service would refuse anyway, said before a pick; a rating given as an argument goes to the service's own check
        refused = focus.refusal(payload, ITEM_ACTIONS[action], pick=action == 'rate' and not given)
        if refused:
            focus.toast(addon, addon.getLocalizedString(refused).format(focus.rating_subject(payload)[0]))
            return
        if action == 'rate':
            payload['rating'] = int(rating) if given else focus.pick_rating(addon, *focus.rating_subject(payload))
            if payload['rating'] is None:
                return
        focus.notify_service(ITEM_ACTIONS[action], payload)
        return
    if action == 'show_log':
        show_log(addon)
        return
    if action not in SERVICE_ACTIONS:
        addon.openSettings()
        return
    if action in CONFIRMATIONS and not xbmcgui.Dialog().yesno('Simkl', addon.getLocalizedString(CONFIRMATIONS[action])):
        return
    focus.notify_service(action)
