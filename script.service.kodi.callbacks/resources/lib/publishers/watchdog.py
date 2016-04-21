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

import sys

from resources.lib.pubsub import Publisher, Message, Topic
from resources.lib.events import Events
from resources.lib.utils.kodipathtools import translatepath
try:
    from watchdog.observers import Observer
    from watchdog.events import PatternMatchingEventHandler
except ImportError:
    libs = translatepath('special://addon/resources/lib')
    sys.path.append(libs)
    libs = translatepath('special://addon/resources/lib/watchdog')
    sys.path.append(libs)
    try:
        from resources.lib.watchdog.observers import Observer
        from resources.lib.watchdog.events import PatternMatchingEventHandler
    except ImportError:
        raise

class EventHandler(PatternMatchingEventHandler):
    def __init__(self, patterns, ignore_patterns, ignore_directories, topic, publish):
        super(EventHandler, self).__init__(patterns=patterns, ignore_patterns=ignore_patterns, ignore_directories=ignore_directories)
        self.topic = topic
        self.publish = publish

    def on_any_event(self, event):
        msg = Message(self.topic, path=event.src_path, event=event.event_type)
        self.publish(msg)

class WatchdogPublisher(Publisher):
    publishes = Events().Watchdog.keys()

    def __init__(self, dispatcher, settings):
        super(WatchdogPublisher, self).__init__(dispatcher)
        self.watchdogSettings = settings.getWatchdogSettings()
        self.event_handlers = []
        self.observersettings = []
        self.observers = []
        self.initialize()

    def initialize(self):
        for setting in self.watchdogSettings:
            patterns = setting['patterns'].split(',')
            ignore_patterns = setting['ignore_patterns'].split(',')
            eh = EventHandler(patterns=patterns, ignore_patterns=ignore_patterns,
                            ignore_directories=setting['ignore_directories'],
                            topic=Topic('onFileSystemChange', setting['key']), publish=self.publish)
            self.event_handlers.append(eh)
            folder = translatepath(setting['folder'])
            mysetting = [eh, folder, setting['recursive']]
            self.observersettings.append(mysetting)

    def start(self):
        for item in self.observersettings:
            observer = Observer()
            observer.schedule(item[0], item[1], recursive=item[2])
            observer.start()
            self.observers.append(observer)

    def abort(self, timeout=0):
        for item in self.observers:
            assert isinstance(item, Observer)
            item.stop()
        if timeout > 0:
            self.join(timeout)

    def join(self, timeout=0):
        for item in self.observers:
            if timeout > 0:
                item.join(timeout)
            else:
                item.join()


