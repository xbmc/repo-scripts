"""Script entry point (called from default.py)."""
import os
import sys

from . import kodiutil as K


def run(args):
    K.ensure_dirs()
    if sys.argv and sys.argv[0].startswith("plugin://"):
        # A skin/home-menu widget is asking for a content listing
        # - answer with the channel list instead of opening the menu.
        from . import widget
        widget.run(sys.argv)
        return
    args = [a.lower() for a in args]
    if args and args[0] == "tool":
        # a button on the Settings > Tools page
        from . import manager
        manager.run_tool(args[1] if len(args) > 1 else "")
    elif "watch" in args:
        nums = [a for a in args if a.isdigit()]
        from . import tv
        tv.run(int(nums[0]) if nums else None)
    elif K.setting_bool("skip_menu", False) and os.path.exists(K.CHANNELS_FILE):
        from . import tv
        tv.run()
    elif "wizard" in args:
        from . import manager
        manager.wizard()
    else:
        from . import manager
        manager.main_menu()
