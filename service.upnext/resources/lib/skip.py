# -*- coding: utf-8 -*-
# GNU General Public License v2.0 (see COPYING or https://www.gnu.org/licenses/gpl-2.0.txt)
"""Skip intros and recaps an add-on marked in its upnext_data.

An add-on sends ``skip_segments``, a list of ``{"kind", "start", "end"}`` in
seconds of the playing file. While playback is inside an intro or recap, a
Skip button appears; pressing it jumps to the segment's end. A kind may occur
more than once: each range is skipped on its own, never the gap between.
Credits are left to the Up Next popup, which ``notification_offset`` times.
"""

from platform import machine
from xbmcgui import WindowXMLDialog
from utils import addon_path, get_setting_bool, localize, log as ulog

SKIPPABLE = ('intro', 'recap')
LABELS = {'intro': 30052, 'recap': 30053}
AUTO_SKIP_SETTINGS = {'intro': 'autoSkipIntro', 'recap': 'autoSkipRecap'}
# No button for the last second of a range: the skip would land where playback already is.
END_MARGIN = 1.0
ACTION_NAV_BACK = 92
ACTION_PREVIOUS_MENU = 10
BUTTON = 3010
OS_MACHINE = machine()


def log(msg, level=2):
    ulog(msg, name='Skip', level=level)


def parse_segments(data):
    """Valid, skippable segments from upnext_data, as sorted (kind, start, end)."""
    segments = []
    for segment in (data or {}).get('skip_segments') or []:
        try:
            # Both bounds must be given: a range with no start must not
            # become one from zero and skip the opening of the episode.
            kind = segment['kind']
            start, end = float(segment['start']), float(segment['end'])
        except (KeyError, TypeError, ValueError):
            continue
        if kind in SKIPPABLE and 0 <= start < end:
            segments.append((kind, start, end))
    return sorted(segments, key=lambda segment: segment[1])


def active_segment(segments, play_time):
    for segment in segments:
        if segment[1] <= play_time < segment[2] - END_MARGIN:
            return segment
    return None


class SkipButton(WindowXMLDialog):
    """A small, non-modal button over the video."""

    def __init__(self, *args, **kwargs):
        self.on_skip = kwargs.pop('on_skip', None)
        self.label = kwargs.pop('label', '')
        self.dismissed = False
        if OS_MACHINE[0:5] == 'armv7':
            WindowXMLDialog.__init__(self)
        else:
            WindowXMLDialog.__init__(self, *args, **kwargs)

    def onInit(self):  # pylint: disable=invalid-name
        self.setProperty('label', self.label)

    def onClick(self, controlId):  # pylint: disable=invalid-name
        if controlId == BUTTON:
            if self.on_skip:
                self.on_skip()
            self.close()

    def onAction(self, action):  # pylint: disable=invalid-name
        if action.getId() in (ACTION_NAV_BACK, ACTION_PREVIOUS_MENU):
            self.dismissed = True
            self.close()


def make_button(label, on_skip):
    return SkipButton('script-upnext-skip.xml', addon_path(), 'default', '1080i', label=label, on_skip=on_skip)


class Skipper:
    """Called once a second by the monitor with the playing position."""

    def __init__(self, player, button_factory=make_button):
        self.player = player
        self.button_factory = button_factory
        self.button = None
        self.current = None
        self.handled = set()  # segments skipped or dismissed during this playback

    def reset(self):
        self.hide()
        self.current = None
        self.handled = set()

    def hide(self):
        if self.button is not None:
            self.button.close()
            self.button = None

    def skip(self, segment):
        self.handled.add(segment)
        try:
            now = self.player.getTime()
        except RuntimeError:
            now = None
        if now is not None and now >= segment[2] - END_MARGIN:
            # The range has passed (a button left open while the Up Next
            # popup held the monitor): skipping now would jump backwards.
            log('Not skipping %s: playback is already past %.0f s' % (segment[0], segment[2]))
            return
        log('Skipping %s from %.0f to %.0f s' % segment)
        self.player.seekTime(segment[2])

    def update(self, data, play_time):
        if not get_setting_bool('enableSkipSegments', default=True):
            self.hide()
            return
        segment = active_segment(parse_segments(data), play_time)
        if segment != self.current:
            self.hide()
            self.current = segment
        if segment is None or segment in self.handled:
            return
        if self.button is not None and self.button.dismissed:
            self.handled.add(segment)
            self.hide()
            return
        if get_setting_bool(AUTO_SKIP_SETTINGS[segment[0]], default=False):
            self.skip(segment)
            return
        if self.button is None:
            self.button = self.button_factory(localize(LABELS[segment[0]]), lambda: self.skip(segment))
            self.button.show()
