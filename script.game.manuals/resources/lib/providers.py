# -*- coding: utf-8 -*-
"""Add-ons that find manuals, and how they are asked.

A provider is an ordinary plugin, called the way Kodi calls a subtitle service,
with a directory listing for an answer:

  plugin://<provider>/?action=search&path=<game>&title=<name>

Each result's path is the manual itself, to be copied wherever it is wanted.
A plugin is one when its id starts with plugin.game.manuals., the way a
subtitle service's starts with service.subtitles.
"""

from urllib.parse import urlencode

from . import manuals

PREFIX = "plugin.game.manuals."

# Offered for installing when none is installed, so finding a manual doesn't
# start with a search of the add-on browser
KNOWN = ("plugin.game.manuals.regvault",)


def is_provider(addon_id):
    """Whether an add-on is a manual provider, going by its id."""
    return addon_id.startswith(PREFIX)


def search_url(addon_id, game_path, title=""):
    """What to list to ask a provider for this game's manual."""
    # The path is what settles it: how a provider decides what matches is its
    # own business, and the title is only a hint
    query = urlencode({"action": "search", "path": game_path,
                       "title": title or manuals.display_title(game_path)})
    return "plugin://%s/?%s" % (addon_id, query)
