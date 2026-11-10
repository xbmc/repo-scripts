# -*- coding: utf-8 -*-
# GNU General Public License v2.0 (see COPYING or https://www.gnu.org/licenses/gpl-2.0.txt)
"""Behaviour shared by the Up Next and Still Watching popups"""

from datetime import datetime, timedelta
from math import ceil
from xbmcgui import WindowXMLDialog, getCurrentWindowDialogId
from utils import get_global_setting, is_armv7, localize_date, localize_time

ACTION_PLAYER_STOP = 13
ACTION_NAV_BACK = 92
RING_STEPS = 30  # media/nextupicons has a countdown ring image for 00 to 30
# Kodi's "Show information for unwatched items" (videolibrary.showunwatchedplots) options
SHOW_UNWATCHED_MOVIE_PLOT = 0
SHOW_UNWATCHED_EPISODE_PLOT = 1
SHOW_UNWATCHED_EPISODE_THUMB = 2
# Where each popup image comes from, best first: the show's own art, then art an add-on sent
# without the tvshow. prefix, then the season's
ART_SOURCES = {
    'fanart': ('tvshow.fanart', 'fanart', 'season.fanart'),
    'landscape': ('tvshow.landscape', 'landscape', 'season.landscape'),
    'clearart': ('tvshow.clearart', 'clearart'),
    'clearlogo': ('tvshow.clearlogo', 'clearlogo'),
    'poster': ('tvshow.poster', 'poster', 'season.poster'),
}


class Popup(WindowXMLDialog):
    item = None
    cancel = False
    dismissed = False
    progress_step_size = 0
    current_progress_percent = 100
    progress_control = None
    countdown_duration = None
    playback_dialog_id = None

    def __init__(self, *args, **kwargs):
        self.action_exitkeys_id = [10, 13]
        self.progress_control = None
        if is_armv7():
            WindowXMLDialog.__init__(self)
        else:
            WindowXMLDialog.__init__(self, *args, **kwargs)

    def onInit(self):  # pylint: disable=invalid-name
        self.playback_dialog_id = getCurrentWindowDialogId()
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

        show_plot, show_thumb = spoilers_allowed(self.item)
        art = popup_art(self.item.get('art') or {}, show_thumb)
        for art_type in ('fanart', 'landscape', 'clearart', 'clearlogo', 'poster', 'thumb'):
            self.setProperty(art_type, art[art_type])
        self.setProperty('plot', self.item.get('plot', '') if show_plot else '')
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
            self.set_remaining(remaining)
        if runtime:
            self.setProperty('endtime', localize_time(datetime.now() + timedelta(seconds=runtime)))

    def set_remaining(self, remaining):
        """Show the time left before the popup acts, in seconds and as m:ss for popups opened earlier"""
        remaining = max(0, int(remaining))
        if self.countdown_duration is None:
            self.countdown_duration = remaining
        self.setProperty('remaining', '%02d' % remaining)
        self.setProperty('remaining_time', format_remaining(remaining))
        self.setProperty('remaining_icon', '%02d' % ring_step(remaining, self.countdown_duration))

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


def spoilers_allowed(item):
    """Return whether the plot and the thumbnail of the next item may be shown, following Kodi's
       "Show information for unwatched items" setting for items not watched yet"""
    # Library lookups and add-ons give episodes; playlists can also hold movies and plain files
    media_type = item.get('type') or 'episode'
    if item.get('playcount') or media_type not in ('episode', 'movie'):
        return True, True
    shown = get_global_setting('videolibrary.showunwatchedplots')
    if not isinstance(shown, list):  # Not available: Kodi shows everything by default
        return True, True
    if media_type == 'movie':
        # Kodi only hides the thumbnails of episodes
        return SHOW_UNWATCHED_MOVIE_PLOT in shown, True
    return SHOW_UNWATCHED_EPISODE_PLOT in shown, SHOW_UNWATCHED_EPISODE_THUMB in shown


def popup_art(art, show_thumb=True):
    """Return the popup's images, each from the first art type the item has"""
    images = {
        art_type: next((art[source] for source in sources if art.get(source)), '')
        for art_type, sources in ART_SOURCES.items()
    }
    if show_thumb:
        images['thumb'] = art.get('thumb', '')
    else:
        # Show art in place of the episode's own picture, like Kodi does for hidden thumbnails
        images['thumb'] = images['landscape'] or images['fanart']
    return images


def format_remaining(seconds):
    """Return seconds as m:ss, or h:mm:ss from an hour"""
    minutes, seconds = divmod(int(seconds), 60)
    hours, minutes = divmod(minutes, 60)
    if hours:
        return '%d:%02d:%02d' % (hours, minutes, seconds)
    return '%d:%02d' % (minutes, seconds)


def ring_step(remaining, duration):
    """Return the countdown ring image for the time left: one per second in the last 30 seconds,
       or spread over the whole countdown when the popup opened earlier"""
    if not duration or duration <= RING_STEPS:
        return min(RING_STEPS, int(remaining))
    return min(RING_STEPS, int(ceil(RING_STEPS * remaining / duration)))
