# -*- coding: utf-8 -*-

import xbmcgui
import socket

from .common import *
from .forecast import *
from .locations import *


def run(args):
    """
    This is 'main' basically.
    TWO MAJOR MODES - SETTINGS and FORECAST RETRIEVAL

    @param args: sys.argv is passed through to here...
    """

    footprints()
    socket.setdefaulttimeout(100)

    # SETTINGS
    # the addon is being called from the settings section where the user enters their postcodes
    if args[1].startswith('Location'):
        find_location()

    # FORECAST
    # script is being called in general use, not from the settings page
    # sys.argv[1] has the current location number, so get the currently selected location and grab it's forecast
    else:
        get_forecast()

    # Refresh the locations
    refresh_locations()

    # and close out...
    footprints(startup=False)
