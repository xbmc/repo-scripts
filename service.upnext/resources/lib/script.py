# -*- coding: utf-8 -*-
# GNU General Public License v2.0 (see COPYING or https://www.gnu.org/licenses/gpl-2.0.txt)
"""This is the actual Up Next API script"""

from datetime import datetime, timedelta
from math import ceil
from xbmc import Monitor
from xbmcgui import WindowXMLDialog
from popup import format_remaining, popup_art, ring_step, spoilers_allowed
from utils import addon_path, get_setting_bool, jsonrpc, localize, localize_date, localize_time

EPISODE_FIELDS = ['art', 'episode', 'firstaired', 'playcount', 'plot', 'rating', 'runtime', 'season',
                  'showtitle', 'title', 'tvshowid']
PREVIEW_CANDIDATES = 25  # random library episodes tried for one with the episode before it
PREVIEW_PROGRESS = 96  # percent of the finishing episode shown as played
PREVIEW_REMAINING = 84  # seconds of it shown as left


def library_preview(candidates=PREVIEW_CANDIDATES):
    """A next episode from the library with the one before it (finishing, next),
    so the test window shows real pictures and text; None without one."""
    result = jsonrpc(method='VideoLibrary.GetEpisodes', params={
        'properties': EPISODE_FIELDS, 'sort': {'method': 'random'}, 'limits': {'start': 0, 'end': candidates},
        'filter': {'field': 'episode', 'operator': 'greaterthan', 'value': '1'},
    })
    for upcoming in (result.get('result') or {}).get('episodes') or []:
        before = jsonrpc(method='VideoLibrary.GetEpisodes', params={
            'tvshowid': upcoming.get('tvshowid'), 'season': upcoming.get('season'),
            'properties': ['art', 'episode', 'season', 'title'],
            'filter': {'field': 'episode', 'operator': 'is', 'value': str(upcoming.get('episode', 0) - 1)},
        })
        finishing = ((before.get('result') or {}).get('episodes') or [None])[0]
        if finishing:
            return finishing, upcoming
    return None


def preview_properties(finishing, upcoming):
    """The window's properties for a library preview: the next episode as
    the real popup sets them (its plot and still hidden when Kodi hides them
    for unwatched episodes), and preview_finishing_* for the episode playing,
    which a skin can show where it would read the player (nothing plays)."""
    show_plot, show_thumb = spoilers_allowed(upcoming)
    art = popup_art(upcoming.get('art') or {}, show_thumb)
    rating = upcoming.get('rating')
    props = dict(art)
    props.update({
        'plot': upcoming.get('plot', '') if show_plot else '', 'tvshowtitle': upcoming.get('showtitle', ''),
        'title': upcoming.get('title', ''), 'season': str(upcoming.get('season', '')),
        'episode': str(upcoming.get('episode', '')),
        'seasonepisode': '{}x{}.'.format(upcoming.get('season', ''), upcoming.get('episode', '')),
        'year': localize_date(upcoming.get('firstaired', '')),
        'rating': str(round(float(rating), 1)) if rating is not None else '',
        'playcount': str(upcoming.get('playcount', 0)), 'runtime': str(upcoming.get('runtime', '')),
    })
    finishing_art = finishing.get('art') or {}
    props.update({
        'preview_finishing_art': finishing_art.get('thumb') or art['landscape'] or art['fanart'],
        'preview_finishing_season': str(finishing.get('season', '')),
        'preview_finishing_episode': str(finishing.get('episode', '')),
        'preview_finishing_title': finishing.get('title', ''),
        'preview_finishing_progress': str(PREVIEW_PROGRESS),
        'preview_finishing_remaining': format_remaining(PREVIEW_REMAINING),
    })
    return props


class TestPopup(WindowXMLDialog):
    ACTION_PLAYER_STOP = 13
    ACTION_NAV_BACK = 92
    progress_step_size = 0
    current_progress_percent = 100.0
    progress_control = None
    pause = False

    def onInit(self):  # pylint: disable=invalid-name
        self.set_info()
        self.prepare_progress_control()

        if get_setting_bool('stopAfterClose'):
            self.getControl(3013).setLabel(localize(30033))  # Stop
        else:
            self.getControl(3013).setLabel(localize(30034))  # Close

    def set_info(self):
        """An episode from the library and the one before it when there is
        one; else Game of Thrones' text without pictures (fanart.tv no
        longer serves the links this used)."""
        sample = library_preview()
        if sample:
            for key, value in preview_properties(*sample).items():
                self.setProperty(key, value)
            return
        self.setProperty('episode', '4')
        self.setProperty('playcount', '1')
        self.setProperty('plot', 'Lord Baelish arrives at Renly\'s camp just before he faces off against Stannis. '
                                 'Daenerys and her company are welcomed into the city of Qarth. Arya, Gendry, and '
                                 'Hot Pie find themselves imprisoned at Harrenhal.')
        self.setProperty('rating', '8.9')
        self.setProperty('season', '2')
        self.setProperty('seasonepisode', '2x4')
        self.setProperty('title', 'Garden of Bones')
        self.setProperty('tvshowtitle', 'Game of Thrones')
        self.setProperty('year', '2012')
        self.setProperty('runtime', '50')

    def prepare_progress_control(self):
        try:
            self.progress_control = self.getControl(3014)
        except RuntimeError:
            return
        self.progress_control.setPercent(100.0)  # pylint: disable=no-member,useless-suppression

    def update_progress_control(self, timeout, wait):
        if self.progress_control is None:
            return
        self.current_progress_percent -= 100 * wait / timeout
        self.progress_control.setPercent(self.current_progress_percent)  # pylint: disable=no-member,useless-suppression
        self.set_remaining(ceil((timeout / 1000) * (self.current_progress_percent / 100)), timeout / 1000)
        self.setProperty('endtime', localize_time(datetime.now() + timedelta(seconds=50 * 60)))

    def set_remaining(self, remaining, duration):
        self.setProperty('remaining', '%02d' % remaining)
        self.setProperty('remaining_time', format_remaining(remaining))
        self.setProperty('remaining_icon', '%02d' % ring_step(remaining, duration))

    def onFocus(self, controlId):  # pylint: disable=invalid-name
        pass

    def doAction(self):  # pylint: disable=invalid-name
        pass

    def closeDialog(self):  # pylint: disable=invalid-name
        self.close()

    def onClick(self, controlId):  # pylint: disable=invalid-name,unused-argument
        self.close()

    def onAction(self, action):  # pylint: disable=invalid-name
        if action == self.ACTION_PLAYER_STOP:
            self.close()
        elif action == self.ACTION_NAV_BACK:
            self.close()


def test_popup(window):
    popup = TestPopup(window, addon_path(), 'default', '1080i')
    step = 0
    wait = 100
    wait_s = wait / 1000
    timeout = 10000
    popup.set_remaining(timeout / 1000, timeout / 1000)
    popup.show()
    monitor = Monitor()
    while popup and step < timeout and not monitor.abortRequested():
        if popup.pause:
            continue
        monitor.waitForAbort(wait_s)
        popup.update_progress_control(timeout, wait)
        step += wait


def test_skip_button():
    from skip import LABELS, make_button
    button = make_button(localize(LABELS['intro']), on_skip=lambda: None)
    button.show()
    Monitor().waitForAbort(10)
    button.close()


def open_settings():
    from xbmcaddon import Addon
    Addon().openSettings()


def run(argv):
    """Route to API method"""
    if len(argv) == 3 and argv[1] == 'test_window' and argv[2] == 'script-upnext-skip.xml':
        test_skip_button()
    elif len(argv) == 3 and argv[1] == 'test_window':
        test_popup(argv[2])
    else:
        open_settings()
