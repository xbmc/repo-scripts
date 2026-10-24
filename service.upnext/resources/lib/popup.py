# -*- coding: utf-8 -*-
# GNU General Public License v2.0 (see COPYING or https://www.gnu.org/licenses/gpl-2.0.txt)
"""Behaviour shared by the Up Next and Still Watching popups"""

from datetime import datetime, timedelta
from platform import machine
from xbmcgui import WindowXMLDialog
from utils import localize_date, localize_time

ACTION_PLAYER_STOP = 13
ACTION_NAV_BACK = 92
OS_MACHINE = machine()


class Popup(WindowXMLDialog):
    item = None
    cancel = False
    dismissed = False
    progress_step_size = 0
    current_progress_percent = 100
    progress_control = None

    def __init__(self, *args, **kwargs):
        self.action_exitkeys_id = [10, 13]
        self.progress_control = None
        if OS_MACHINE[0:5] == 'armv7':
            WindowXMLDialog.__init__(self)
        else:
            WindowXMLDialog.__init__(self, *args, **kwargs)

    def onInit(self):  # pylint: disable=invalid-name
        self.set_info()
        self.prepare_progress_control()

    def set_info(self):
        if self.item is None:
            return
        episode_info = '{}x{}.'.format(self.item.get('season', ''), self.item.get('episode', ''))
        if self.item.get('rating') is None:
            rating = ''
        else:
            rating = str(round(float(self.item.get('rating')), 1))

        art = self.item.get('art') or {}
        self.setProperty('fanart', art.get('tvshow.fanart', ''))
        self.setProperty('landscape', art.get('tvshow.landscape', ''))
        self.setProperty('clearart', art.get('tvshow.clearart', ''))
        self.setProperty('clearlogo', art.get('tvshow.clearlogo', ''))
        self.setProperty('poster', art.get('tvshow.poster', ''))
        self.setProperty('thumb', art.get('thumb', ''))
        self.setProperty('plot', self.item.get('plot', ''))
        self.setProperty('tvshowtitle', self.item.get('showtitle', ''))
        self.setProperty('title', self.item.get('title', ''))
        self.setProperty('season', str(self.item.get('season', '')))
        self.setProperty('episode', str(self.item.get('episode', '')))
        self.setProperty('seasonepisode', episode_info)
        self.setProperty('year', localize_date(self.item.get('firstaired', '')))
        self.setProperty('rating', rating)
        self.setProperty('playcount', str(self.item.get('playcount', 0)))
        self.setProperty('runtime', str(self.item.get('runtime', '')))

    def prepare_progress_control(self):
        try:
            self.progress_control = self.getControl(3014)
        except RuntimeError:  # Occurs when skin does not include progress control
            pass
        else:
            self.progress_control.setPercent(self.current_progress_percent)  # pylint: disable=no-member,useless-suppression

    def set_item(self, item):
        self.item = item

    def set_progress_step_size(self, progress_step_size):
        self.progress_step_size = progress_step_size

    def update_progress_control(self, remaining=None, runtime=None, progress=None):
        self.current_progress_percent = (self.current_progress_percent - self.progress_step_size
                                         if progress is None else max(0, min(100, progress)))
        try:
            self.progress_control = self.getControl(3014)
        except RuntimeError:  # Occurs when skin does not include progress control
            pass
        else:
            self.progress_control.setPercent(self.current_progress_percent)  # pylint: disable=no-member,useless-suppression

        if remaining is not None:
            self.setProperty('remaining', '%02d' % remaining)
        if runtime:
            self.setProperty('endtime', localize_time(datetime.now() + timedelta(seconds=runtime)))

    def set_cancel(self, cancel):
        self.cancel = cancel

    def is_cancel(self):
        return self.cancel

    def is_dismissed(self):
        return self.dismissed

    def confirm(self):
        """Handle the popup's main button (3012): Watch now, or Still watching"""
        raise NotImplementedError

    def onFocus(self, controlId):  # pylint: disable=invalid-name
        pass

    def doAction(self):  # pylint: disable=invalid-name
        pass

    def closeDialog(self):  # pylint: disable=invalid-name
        self.close()

    def onClick(self, controlId):  # pylint: disable=invalid-name
        if controlId == 3012:  # Watch now / Still watching
            self.confirm()
            self.close()
        elif controlId == 3013:  # Close / Stop
            self.set_cancel(True)
            # The playback manager owns Stop after the dialog has closed.
            self.close()

    def onAction(self, action):  # pylint: disable=invalid-name
        if action == ACTION_PLAYER_STOP:
            self.close()
        elif action == ACTION_NAV_BACK:
            self.dismissed = True
            self.set_cancel(True)
            self.close()
