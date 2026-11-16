"""What a skin's lyrics button runs.

It runs in its own interpreter, so it only raises a property for the service
to act on. ``notify_no_lyrics`` is the toast the service (and the presenter)
show when that press found nothing.
"""

import time

import xbmcaddon
import xbmcgui

from . import lyrics as source

PROP_SUMMON = "kofin.lyric.summon"

STRING_NO_LYRICS = 30011
NOTIFY_MS = 3000


def notify_no_lyrics() -> None:
    """Tell the viewer the button found nothing to show: the song is not
    kofin's, Jellyfin has no lyrics for it, or they are untimed and turned
    off. Without this the button does nothing visible."""
    try:
        addon = xbmcaddon.Addon()
        xbmcgui.Dialog().notification(
            addon.getAddonInfo("name"),
            addon.getLocalizedString(STRING_NO_LYRICS),
            addon.getAddonInfo("icon"),
            NOTIFY_MS,
            False,
        )
    except Exception:  # Addon() throws during teardown
        pass


def summon() -> None:
    # Left to the service's next tick: has_lyrics() is a snapshot that is
    # false while kofin fetches, and the button also closes the OSD, which
    # is still up for anything done from here. Timestamped so a second press
    # still counts.
    xbmcgui.Window(source.HOME_WINDOW).setProperty(PROP_SUMMON, str(time.time()))
