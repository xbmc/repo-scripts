"""Script entry point (called from default.py)."""
import os

from . import kodiutil as K


def run(args):
    K.ensure_dirs()
    args = [a.lower() for a in args]
    if "watch" in args or (K.setting_bool("skip_menu", False) and os.path.exists(K.CHANNELS_FILE)):
        from . import tv
        tv.run()
    elif "wizard" in args:
        from . import manager
        manager.wizard()
    else:
        from . import manager
        manager.main_menu()
