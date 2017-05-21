# coding: utf-8
# Created on: 15.03.2016
# Author: Roman Miroshnychenko aka Roman V.M. (romanvm@yandex.ua)
# License: GPL v. 3 <http://www.gnu.org/licenses/gpl-3.0.en.html>

import xbmc
from libs.monitoring import UpdateMonitor, initial_prompt

initial_prompt()
update_monitor = UpdateMonitor()
service_started = False
while not update_monitor.abortRequested():
    if not service_started:
        xbmc.log('next-episode.net: service started', xbmc.LOGNOTICE)
        service_started = True
    xbmc.sleep(500)
xbmc.log('next-episode.net: service stopped', xbmc.LOGNOTICE)
