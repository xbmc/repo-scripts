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
    elif args and args[0] == "preview_promo":
        # Settings > Breaks > Preview a promo, or RunScript(script.cablebox42,preview_promo,<tvshowid>)
        # (",settings": started from Settings, which it opens again when the promo is over)
        from . import promo_preview
        promo_preview.run(int(args[1]) if len(args) > 1 and args[1].isdigit() else None,
                          from_settings="settings" in args[1:])
    elif args and args[0] == "preview_ad" and len(args) > 1:
        # RunScript(script.cablebox42,preview_ad,P01): one retro ad (screenshots, checks on the box)
        from . import promo_preview
        promo_preview.run_ad(args[1])
    elif "watch" in args:
        # a Kodi shortcut, widget or RunScript(script.cablebox42,watch,7): Back goes to Kodi,
        # Menu > CableBox menu opens the main menu
        nums = [a for a in args if a.isdigit()]
        from . import tv
        if tv.run(int(nums[0]) if nums else None) == "menu":
            from . import manager
            manager.main_menu()
    elif "wizard" in args:
        # asked for by name: also with Go straight to TV on
        from . import manager
        manager.wizard()
        if manager.tv_wants_menu():
            manager.main_menu()
    elif K.setting_bool("skip_menu", False) and os.path.exists(K.CHANNELS_FILE):
        from . import tv
        if tv.run() == "menu":
            from . import manager
            manager.main_menu()
    else:
        from . import manager
        manager.main_menu()
