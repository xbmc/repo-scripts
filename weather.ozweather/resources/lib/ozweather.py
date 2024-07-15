# -*- coding: utf-8 -*-
import socket

# noinspection PyPackages
from .forecast import *
# noinspection PyPackages
from .locations import *
# noinspection PyPackages
from .bom.bom_location import *
# noinspection PyPackages
from .abc.abc_video import *


def run(args):
    """
    This is 'main' basically.
    TWO MAJOR MODES - SETTINGS and FORECAST RETRIEVAL

    :param args: sys.argv is passed directly through
    """

    footprints()
    socket.setdefaulttimeout(100)

    # RUN MODE - ADDON CALLED FORM Kodi SETTINGS
    # the addon is being called from the settings section where the user enters their postcodes
    if args[1].startswith('Location'):
        find_bom_location()

    # RUN MODE - ADDON CALLED FORM Kodi SETTINGS
    # the addon is being called from the settings section where the user enters their postcodes
    elif args[1].startswith('ABC'):
        scrape_and_play_abc_weather_video()

    # RUN MODE - GET WEATHER OBSERVATIONS AND FORECAST
    # script is being called in general use, not from the settings page
    # sys.argv[1] has the current location number (e.g. '1'), so fetch the weather data
    else:
        get_weather()

    # If location settings have changed, this kick-starts an update
    refresh_locations()

    # and close out...
    footprints(startup=False)
