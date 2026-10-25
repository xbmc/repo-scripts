# SPDX-License-Identifier: GPL-2.0-only
"""What the add-on's script entry point runs, chosen by its arguments.

Kodi passes RunScript arguments in sys.argv after the script path. With none, the viewer
dialog opens, which is what the existing settings action relies on. CrossWatch's Link comes
through Addons.ExecuteAddon as key=value arguments, action=link first.

Each screen is imported only when chosen: a settings script runs in a fresh interpreter, and
the viewer dialog should not pay for the pairing code's imports.
"""

REMEMBERED = "remembered"
PAIR = "pair"
UNPAIR = "unpair"


def dispatch(argv: list[str]) -> None:
    arguments = argv[1:]
    if any(arg.startswith("action=") for arg in arguments):
        from resources.lib import connect

        parsed = connect.parse_arguments(arguments)
        # Any other action is from a caller this add-on does not know; opening a screen for
        # it would put a dialog on the TV that nobody asked for.
        if parsed.get("action") == "link":
            connect.link_main(parsed)
        return
    if PAIR in arguments:
        from resources.lib.connect import pair_main

        pair_main()
        return
    if UNPAIR in arguments:
        from resources.lib.connect import unpair_main

        unpair_main()
        return
    if REMEMBERED in arguments:
        from resources.lib.remembered import main as remembered_main

        remembered_main()
        return
    from resources.lib.viewer_config import main as viewers_main

    viewers_main()

