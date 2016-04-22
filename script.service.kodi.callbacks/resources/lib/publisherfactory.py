#!/usr/bin/python
# -*- coding: utf-8 -*-
#
#     Copyright (C) 2016 KenV99
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with this program. If not, see <http://www.gnu.org/licenses/>.
#

from resources.lib.publishers.log import LogPublisher
from resources.lib.publishers.loop import LoopPublisher
from resources.lib.publishers.monitor import MonitorPublisher
from resources.lib.publishers.player import PlayerPublisher
from resources.lib.publishers.schedule import SchedulePublisher
from resources.lib.kodilogging import KodiLogger
kl = KodiLogger()
log = kl.log
from resources.lib.utils.poutil import KodiPo
kodipo = KodiPo()
_ = kodipo.getLocalizedString
try:
    from resources.lib.publishers.watchdog import WatchdogPublisher
except ImportError as e:
    from resources.lib.publishers.dummy import WatchdogPublisherDummy as WatchdogPublisher
    log(msg=_('Error importing Watchdog: %s') % str(e), loglevel=KodiLogger.LOGERROR)
try:
    from resources.lib.publishers.watchdogStartup import WatchdogStartup
except ImportError as e:
    from resources.lib.publishers.dummy import WatchdogPublisherDummy as WatchdogStartup
    log(msg=_('Error importing Watchdog: %s') % str(e), loglevel=KodiLogger.LOGERROR)



class PublisherFactory(object):

    def __init__(self, settings, topics, dispatcher, logger, debug=False):
        self.settings = settings
        self.logger = logger
        self.topics = topics
        self.debug = debug
        self.dispatcher = dispatcher
        self.publishers = {LogPublisher:_('Log Publisher initialized'),
                           LoopPublisher:_('Loop Publisher initialized'),
                           MonitorPublisher:_('Monitor Publisher initialized'),
                           PlayerPublisher:_('Player Publisher initialized'),
                           WatchdogPublisher:_('Watchdog Publisher initialized'),
                           WatchdogStartup:_('Watchdog Startup Publisher initialized'),
                           SchedulePublisher:_('Schedule Publisher initialized')
                           }
        self.ipublishers = []

    def createPublishers(self):
        for publisher in self.publishers.keys():
            if not set(self.topics).isdisjoint(publisher.publishes) or self.debug is True:
                ipublisher = publisher(self.dispatcher, self.settings)
                self.ipublishers.append(ipublisher)
                self.logger.log(msg=_(self.publishers[publisher]))


