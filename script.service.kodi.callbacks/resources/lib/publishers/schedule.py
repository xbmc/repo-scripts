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
from resources.lib import schedule
import xbmc
import threading
from resources.lib.pubsub import Publisher, Message, Topic
from resources.lib.events import Events
from resources.lib.utils.poutil import KodiPo
kodipo = KodiPo()
_ = kodipo.getLocalizedString

class SchedulePublisher(threading.Thread, Publisher):
    publishes = Events().Schedule.keys()

    def __init__(self, dispatcher, settings):
        Publisher.__init__(self, dispatcher)
        threading.Thread.__init__(self, name='SchedulePublisher')
        self.dailyAlarms = settings.getEventsByType('onDailyAlarm')
        self.intervalAlarms = settings.getEventsByType('onIntervalAlarm')
        self.abortEvt = threading.Event()
        self.abortEvt.clear()
        self.sleep = xbmc.sleep
        self.sleepinterval = 1000
        self.schedules = []

    def run(self):
        for alarm in self.dailyAlarms:
            hour = str(alarm['hour']).zfill(2)
            minute = str(alarm['minute']).zfill(2)
            stime = ':'.join([hour, minute])
            schedule.every().day.at(stime).do(self.prePublishDailyAlarm, key=alarm['key'])
        for alarm in self.intervalAlarms:
            interval = alarm['hours'] * 3600 + alarm['minutes'] * 60 + alarm['seconds']
            if interval > 0:
                schedule.every(interval).seconds.do(self.prePublishIntervalAlarm, key=alarm['key'])
            else:
                xbmc.log(msg=_('onIntervalAlarm interval cannot be zero'))

        while not self.abortEvt.is_set():
            schedule.run_pending()
            self.sleep(self.sleepinterval)
        schedule.clear()

    def prePublishDailyAlarm(self, key):
        meseage = Message(Topic('onDailyAlarm', key))
        self.publish(meseage)

    def prePublishIntervalAlarm(self, key):
        meseage = Message(Topic('onIntervalAlarm', key))
        self.publish(meseage)

    def abort(self, timeout=0):
        self.abortEvt.set()
        if timeout > 0:
            self.join(timeout)
            if self.is_alive():
                xbmc.log(msg=_('Could not stop SchedulePublisher T:%i') % self.ident)
