import os
import sys

import xbmc
import xbmcgui

from client import Client
from conf import Conf, get_plugin_id, DATA_PATH
from kodi_controller import action_map
from pair import pair
from utils import debug


if __name__ == '__main__':
    debug('sys.argv = %s' % str(sys.argv))
    if xbmcgui.Window(10000).getProperty(get_plugin_id() + '_running') == "True":
        debug('Service already running')
        sys.exit()
    else:
        debug('No other service is running - moving on')

    monitor = xbmc.Monitor()

    conf = Conf()

    client = Client(conf, action_map)
    client.connect_in_background()

    xbmcgui.Window(10000).setProperty(get_plugin_id() + '_running', 'True')

    # pair_if_first_run(conf, client)

    while not monitor.abortRequested():
        if conf.repair_asked:
            pair(client)
            conf.close_repair_request()

        # Sleep/wait for abort for 1 seconds
        if monitor.waitForAbort(1):
            # Abort was requested while waiting. We should exit
            break

    debug('Miracle service is aborting')

    xbmcgui.Window(10000).setProperty(get_plugin_id() + '_running', 'False')

    client.shut_down()
