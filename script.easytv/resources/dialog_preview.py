#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Dialog Preview Script — quickly cycle through all custom dialogs.

Usage from Kodi:
    RunScript(script.easytv,dialog_preview)

Or from the Kodi debug console / JSON-RPC:
    {"jsonrpc":"2.0","method":"Addons.ExecuteAddon",
     "params":{"addonid":"script.easytv","params":["dialog_preview"]},"id":1}
"""

import xbmcgui
import xbmcaddon

addon = xbmcaddon.Addon('script.easytv')
script_path = addon.getAddonInfo('path')

dialog = xbmcgui.Dialog()


def preview_confirm():
    """Show the themed ConfirmDialog."""
    from resources.lib.ui.dialogs import show_confirm
    result = show_confirm(
        "Confirm Dialog Preview",
        "This is a test message.\nDo you want to continue?",
        yes_label="Accept",
        no_label="Decline"
    )
    dialog.notification("EasyTV Preview", "Confirm result: %s" % result)


def preview_select():
    """Show the themed SelectDialog."""
    from resources.lib.ui.dialogs import show_select
    items = [
        "First Option",
        "Second Option",
        "Third Option",
        "Fourth Option",
        "Fifth Option",
        "Sixth Option",
        "Seventh Option",
        "Eighth Option",
    ]
    result = show_select("Select Dialog Preview", items)
    dialog.notification("EasyTV Preview", "Selected index: %s" % result)


def preview_show_selector():
    """Show the themed ShowSelectorDialog with fake data."""
    from resources.lib.ui.dialogs import ShowSelectorDialog

    fake_shows = [
        ("Breaking Bad", 1, ""),
        ("Better Call Saul", 2, ""),
        ("The Wire", 3, ""),
        ("Fargo", 4, ""),
        ("The Sopranos", 5, ""),
        ("True Detective", 6, ""),
        ("Ozark", 7, ""),
        ("Dark", 8, ""),
        ("Succession", 9, ""),
        ("The Americans", 10, ""),
        ("Mindhunter", 11, ""),
        ("Peaky Blinders", 12, ""),
    ]

    selector = ShowSelectorDialog(
        "script-easytv-showselector.xml",
        script_path,
        'Default',
        heading="Show Selector Preview",
        all_shows_data=fake_shows,
        current_list=[1, 3, 5, 7],
        logger=None,
    )
    selector.doModal()
    if selector.saved:
        dialog.notification("EasyTV Preview",
                            "Saved %d shows" % len(selector.selected_ids))
    else:
        dialog.notification("EasyTV Preview", "Cancelled")
    del selector


def preview_countdown():
    """Show the themed CountdownDialog (playlist continuation style)."""
    from resources.lib.ui.dialogs import CountdownDialog
    cd = CountdownDialog(
        "script-easytv-countdown.xml",
        script_path,
        'Default',
        heading="Countdown Preview",
        message="Continue watching playlist?",
        subtitle="",
        yes_label="Continue",
        no_label="Stop",
        duration=15,
        timer_template="(auto-closing in %s seconds)",
        default_yes=True,
        poster="",
        logger=None,
    )
    cd.doModal()
    dialog.notification("EasyTV Preview",
                        "Countdown result: %s" % cd.result)
    del cd


def preview_nextepisode():
    """Show the themed CountdownDialog (next episode prompt style)."""
    from resources.lib.ui.dialogs import CountdownDialog
    cd = CountdownDialog(
        "script-easytv-nextepisode.xml",
        script_path,
        'Default',
        heading="Next Episode Preview",
        message="Play next episode?",
        subtitle="S02E05 - The Test Episode",
        yes_label="Play",
        no_label="Don't Play",
        duration=10,
        timer_template="(auto-closing in %s seconds)",
        default_yes=True,
        poster="",
        logger=None,
    )
    cd.doModal()
    dialog.notification("EasyTV Preview",
                        "Next episode result: %s" % cd.result)
    del cd


def preview_browse_views():
    """Info about browse view testing."""
    dialog.ok("EasyTV Preview",
              "Browse views require the service to be running with episode data.\n"
              "Change the view style in Settings > Episode List > Appearance\n"
              "and open EasyTV normally to preview each view.")


def Main():
    options = [
        "1. Confirm Dialog",
        "2. Select Dialog",
        "3. Show Selector Dialog",
        "4. Countdown Dialog",
        "5. Next Episode Prompt",
        "6. Browse Views (info)",
        "7. All Dialogs (cycle through)",
    ]

    choice = dialog.select("EasyTV Dialog Preview", options)  # type: ignore[arg-type]

    if choice == 0:
        preview_confirm()
    elif choice == 1:
        preview_select()
    elif choice == 2:
        preview_show_selector()
    elif choice == 3:
        preview_countdown()
    elif choice == 4:
        preview_nextepisode()
    elif choice == 5:
        preview_browse_views()
    elif choice == 6:
        preview_confirm()
        preview_select()
        preview_show_selector()
        preview_countdown()
        preview_nextepisode()
        preview_browse_views()
