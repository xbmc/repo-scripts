import os
import time
import sys

import xbmc
import xbmcgui
import xbmcaddon
import xbmcvfs

# --- addon import path guard (keep this above any `resources.*` import) ------------
# RunScript(<file path>) runs this "without an addon", so Kodi puts every installed
# add-on's library directory on sys.path ahead of ours and a foreign top-level
# `resources` package shadows ours. See test_connection.py for the full story
# (issue #39). tests/test_runscript_entrypoints.py fails if this block goes missing.
_addon_path = os.path.dirname(os.path.abspath(__file__))
sys.path = [p for p in sys.path if os.path.normpath(p) != _addon_path]
sys.path.insert(0, _addon_path)
# Only evict a *foreign* `resources`; re-importing our own would duplicate its classes.
_res = sys.modules.get("resources")
if _res is not None and not any(os.path.normpath(p).startswith(_addon_path)
                                for p in getattr(_res, "__path__", [])):
    for _module in [m for m in list(sys.modules) if m == "resources" or m.startswith("resources.")]:
        del sys.modules[_module]
# -----------------------------------------------------------------------------------

from resources.lib.cache import Cache, sync_cache_stats_setting
from resources.lib.utilities import TEMP_MAX_AGE_SECONDS

__addon__ = xbmcaddon.Addon("service.subtitles.opensubtitles-com")
__addon_name__ = __addon__.getAddonInfo("name")
__version__ = __addon__.getAddonInfo("version")
__icon__ = xbmcvfs.translatePath(os.path.join(__addon__.getAddonInfo("path"), "resources", "media", "os_logo_512x512.png"))

def clear_cache():
    total_items = 0
    total_bytes = 0

    # Clear memory cache across all prefixes used by provider and add-on
    for prefix in ("os_com", "OpenSubtitles", "os_library", ""):
        cache = Cache(prefix)
        items, b = cache.clear()
        total_items += items
        total_bytes += b

    # Also clean temporary subtitle downloads directory
    profile_temp = xbmcvfs.translatePath(os.path.join(__addon__.getAddonInfo("profile"), "temp"))
    oss_temp = xbmcvfs.translatePath("special://temp/oss/")
    files_deleted = 0
    for temp_dir in (profile_temp, oss_temp):
        if xbmcvfs.exists(temp_dir):
            dirs, files = xbmcvfs.listdir(temp_dir)
            for f in files:
                file_path = os.path.join(temp_dir, f)
                try:
                    # never delete a file inside the downloader's safety
                    # window - Kodi may not have consumed the subtitle yet,
                    # and deleting it leaves the selected item pointing at a
                    # missing file (same constant the downloader cleanup uses)
                    try:
                        if time.time() - os.path.getmtime(file_path) < TEMP_MAX_AGE_SECONDS:
                            continue
                    except OSError:
                        pass
                    xbmcvfs.delete(file_path)
                    files_deleted += 1
                except Exception:
                    pass

    kb_cleared = round(total_bytes / 1024, 2)
    # recount instead of hardcoding "0 items": entries written by a concurrent
    # invocation during the clear legitimately survive and must stay counted
    sync_cache_stats_setting()
    msg = f"Cache cleared: {total_items} items ({kb_cleared} KB freed)"
    if files_deleted:
        msg += f" | {files_deleted} temp files deleted"
    xbmcgui.Dialog().notification(f"{__addon_name__} v{__version__}", msg, __icon__, 3500, False)

if __name__ == "__main__":
    try:
        clear_cache()
    finally:
        xbmc.executebuiltin(f"Addon.OpenSettings({__addon__.getAddonInfo('id')})")
