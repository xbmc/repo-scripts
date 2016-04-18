# coding: utf-8
# Created on: 15.03.2016
# Author: Roman Miroshnychenko aka Roman V.M. (romanvm@yandex.ua)
# License: GPL v. 3 <http://www.gnu.org/licenses/gpl-3.0.en.html>

import xbmc
from libs.monitoring import UpdateMonitor, initial_prompt
from libs.medialibrary import get_now_played, get_playcount
from libs.commands import update_single_item

initial_prompt()
update_monitor = UpdateMonitor()
service_started = False
now_played = None
while not xbmc.abortRequested:
    if xbmc.getCondVisibility('Player.HasVideo') and now_played is None:
        now_played = get_now_played()
    elif not xbmc.getCondVisibility('Player.HasVideo') and now_played is not None:
        xbmc.sleep(1000)  # Wait for Kodi to stop player and to update item's status
        if (now_played['type'] in ('movie', 'episode') and
                    now_played['playcount'] == 0 and
                    get_playcount(now_played['id'], now_played['type']) > 0):
            now_played['playcount'] = 1
            update_single_item(now_played)
        now_played = None
    if not service_started:
        xbmc.log('next-episode.net: service started', xbmc.LOGNOTICE)
        service_started = True
    xbmc.sleep(500)
xbmc.log('next-episode.net: service stopped', xbmc.LOGNOTICE)
