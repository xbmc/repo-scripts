import socket

# noinspection PyPackages
from .bom.bom_location import find_bom_location
# noinspection PyPackages
from .abc.abc_video import scrape_and_play_abc_weather_video
# noinspection PyPackages
from .forecast import get_weather
# noinspection PyPackages
from .locations import refresh_locations

from bossanova808.logger import Logger


def run(args):
    """
    This is 'main' basically.
    TWO MAJOR MODES - SETTINGS and FORECAST RETRIEVAL

    :param args: sys.argv is passed directly through
    """

    Logger.start()
    try:
        socket.setdefaulttimeout(100)

        arg = args[1] if len(args) > 1 else ""

        # RUN MODE - ADDON CALLED FORM Kodi SETTINGS
        # the addon is being called from the settings section where the user enters their postcodes
        if arg.startswith('Location'):
            find_bom_location()

        # RUN MODE - ADDON CALLED FROM Kodi SETTINGS
        # the addon is being called from the settings section where the user enters their postcodes
        elif arg.startswith('ABC'):
            scrape_and_play_abc_weather_video()

        # RUN MODE - GET WEATHER OBSERVATIONS AND FORECAST
        # script is being called in general use, not from the settings page
        # sys.argv[1] has the current location number (e.g. '1'), so fetch the weather data
        else:
            get_weather()

        # If location settings have changed, this kick-starts an update
        refresh_locations()

    # and close out...
    finally:
        Logger.stop()
