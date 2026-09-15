from datetime import datetime

import os
import sys

import xbmc
import xbmcaddon
import xbmcvfs

# --- addon import path guard (keep this above any `resources.*` import) ------------
# Kodi launches this file with RunScript(<file path>), which it treats as a script
# "invoked without an addon". It then appends *every* installed add-on's library
# directory to sys.path and puts ours LAST, so another add-on shipping a top-level
# `resources` package wins `import resources` and our own modules become invisible:
#   ModuleNotFoundError: No module named 'resources.lib.osclient'
# (issue #39, support ticket #168978). Deleting this block silently reintroduces that
# bug for anyone with a conflicting add-on installed - it already happened once, so
# tests/test_runscript_entrypoints.py now fails if it goes missing again.
_addon_path = os.path.dirname(os.path.abspath(__file__))
sys.path = [p for p in sys.path if os.path.normpath(p) != _addon_path]
sys.path.insert(0, _addon_path)
# If a *foreign* `resources` was already imported, evict it so ours wins. Leave an
# already-correct one alone: re-importing it would create a second set of exception
# classes, and `except ServiceUnavailable` would stop matching the one raised.
_res = sys.modules.get("resources")
if _res is not None and not any(os.path.normpath(p).startswith(_addon_path)
                                for p in getattr(_res, "__path__", [])):
    for _module in [m for m in list(sys.modules) if m == "resources" or m.startswith("resources.")]:
        del sys.modules[_module]
# -----------------------------------------------------------------------------------

import xbmcgui
from requests.exceptions import RequestException

from resources.lib.exceptions import (
    AuthenticationError,
    BadUsernameError,
    ConfigurationError,
    ProviderError,
    ServiceUnavailable,
    TooManyRequests,
)
from resources.lib.osclient.provider import OpenSubtitlesProvider

__addon__ = xbmcaddon.Addon("service.subtitles.opensubtitles-com")
__addon_name__ = __addon__.getAddonInfo("name")
__language__ = __addon__.getLocalizedString


def test_connection():
    username = __addon__.getSetting("OSuser")
    password = __addon__.getSetting("OSpass")
    api_key = __addon__.getSetting("APIKey")
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M")

    if not username or not password:
        __addon__.setSetting("account_status", "Not Verified (Missing credentials)")
        __addon__.setSetting("account_details", "Please enter username and password")
        __addon__.setSetting("account_checked_at", now_str)
        __addon__.setSetting("account_verified_at", "0")
        xbmcgui.Dialog().ok(__addon_name__, __language__(32012))
        return

    try:
        provider = OpenSubtitlesProvider(api_key, username, password)
        provider.login()
        user_info = provider.get_user_info()
    except AuthenticationError as e:
        __addon__.setSetting("account_status", "Error 401 (Invalid credentials)")
        __addon__.setSetting("account_details", "Check username and password")
        __addon__.setSetting("account_checked_at", now_str)
        __addon__.setSetting("account_verified_at", "0")
        xbmcgui.Dialog().ok(__addon_name__, f"{__language__(32003)}\n\n[I]{e}[/I]")
        return
    except BadUsernameError as e:
        __addon__.setSetting("account_status", "Error 400 (Bad username)")
        __addon__.setSetting("account_details", "Use username, not email address")
        __addon__.setSetting("account_checked_at", now_str)
        __addon__.setSetting("account_verified_at", "0")
        xbmcgui.Dialog().ok(__addon_name__, __language__(32214))
        return
    except TooManyRequests as e:
        __addon__.setSetting("account_status", "Error 429 (Rate limit exceeded)")
        __addon__.setSetting("account_details", "Please wait before trying again")
        __addon__.setSetting("account_checked_at", now_str)
        __addon__.setSetting("account_verified_at", "0")
        xbmcgui.Dialog().ok(__addon_name__, f"{__language__(32007)}\n\n[I]{e}[/I]")
        return
    except ServiceUnavailable as e:
        __addon__.setSetting("account_status", "Error (Server/Network issue)")
        __addon__.setSetting("account_details", "OpenSubtitles.com is currently unreachable")
        __addon__.setSetting("account_checked_at", now_str)
        __addon__.setSetting("account_verified_at", "0")
        xbmcgui.Dialog().ok(__addon_name__, f"{__language__(32008)}\n\n[I]{e}[/I]")
        return
    except (ConfigurationError, ProviderError, RequestException) as e:
        __addon__.setSetting("account_status", "Error (Connection failed)")
        __addon__.setSetting("account_details", str(e)[:45])
        __addon__.setSetting("account_checked_at", now_str)
        __addon__.setSetting("account_verified_at", "0")
        xbmcgui.Dialog().ok(__addon_name__, str(e))
        return

    now = datetime.now()
    now_str = now.strftime("%Y-%m-%d %H:%M")
    now_epoch = int(now.timestamp())

    level = user_info.get("level", "User")
    vip = "Yes" if user_info.get("vip") else "No"
    remaining = user_info.get("remaining_downloads", "N/A")
    allowed = user_info.get("allowed_downloads", "N/A")
    downloads_count = user_info.get("downloads_count", "N/A")

    vip_badge = "VIP" if user_info.get("vip") else "Free User"
    __addon__.setSetting("account_status", f"OK ({vip_badge})")
    __addon__.setSetting("account_details", f"Quota: {remaining}/{allowed} left | Level: {level}")
    __addon__.setSetting("account_checked_at", now_str)
    __addon__.setSetting("account_verified_at", str(now_epoch))

    version = __addon__.getAddonInfo("version")
    # Compact on purpose (backported from 2.0.0): the ok-dialog shows ~3 lines
    # before it scrolls and cannot be resized (skin-owned). "Remaining" is
    # implied by X / Y, and the level line duplicated the VIP flag.
    info_text = (
        f"Username: [B]{username}[/B]  |  VIP: [B]{vip}[/B]\n"
        f"Downloads today: [B]{downloads_count} / {allowed}[/B]"
    )

    xbmcgui.Dialog().ok(f"{__addon_name__} v{version}", info_text)


if __name__ == "__main__":
    try:
        test_connection()
    finally:
        # Kodi saved the settings and closed the dialog before starting this script (see
        # <close> in settings.xml), which is what lets us read credentials the user has only
        # just typed. Put them back where they were once they dismiss the result.
        xbmc.executebuiltin(f"Addon.OpenSettings({__addon__.getAddonInfo('id')})")
