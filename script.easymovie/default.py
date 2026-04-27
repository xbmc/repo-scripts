"""
EasyMovie entry point.

Dispatches to the main UI flow or handles special
command-line arguments (selector, clone, set_icon).

Logging:
    Logger: 'default'
    Key events:
        - launch.crash (ERROR): Unhandled error caught at top level
    See LOGGING.md for full guidelines.
"""
from resources.lib.ui.main import main, _handle_entry_args

try:
    if not _handle_entry_args("script.easymovie"):
        main()
except SystemExit:
    pass
except Exception:
    try:
        from resources.lib.utils import get_logger
        log = get_logger('default')
        log.exception("Unhandled error in EasyMovie", event="launch.crash")
    except Exception:
        import traceback
        import xbmc
        xbmc.log(
            f"[EasyMovie] Unhandled error: {traceback.format_exc()}",
            xbmc.LOGERROR,
        )
