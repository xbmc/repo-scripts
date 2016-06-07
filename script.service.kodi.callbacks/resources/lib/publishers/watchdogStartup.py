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
import pickle
import os
import time
from resources.lib.utils.kodipathtools import translatepath, setPathRW
libs = translatepath('special://addon/resources/lib')
sys.path.append(libs)
libs = translatepath('special://addon/resources/lib/watchdog')
sys.path.append(libs)

import xbmc
from resources.lib.events import Events
from resources.lib.watchdog.utils.dirsnapshot import DirectorySnapshot, DirectorySnapshotDiff
from resources.lib.watchdog.observers import Observer
from resources.lib.watchdog.events import PatternMatchingEventHandler, FileSystemEvent, EVENT_TYPE_CREATED, EVENT_TYPE_DELETED, EVENT_TYPE_MODIFIED, EVENT_TYPE_MOVED
from resources.lib.pubsub import Publisher, Message, Topic
from resources.lib.utils.poutil import KodiPo
kodipo = KodiPo()
_ = kodipo.getLocalizedString
from resources.lib.kodilogging import KodiLogger
klogger = KodiLogger()
log = klogger.log


class EventHandler(PatternMatchingEventHandler):
    def __init__(self, patterns, ignore_patterns, ignore_directories):
        super(EventHandler, self).__init__(patterns=patterns, ignore_patterns=ignore_patterns,
                                           ignore_directories=ignore_directories)
        self.data = {}

    def on_any_event(self, event):
        if event.is_directory:
            et = 'Dirs%s' % event.event_type.capitalize()
        else:
            et = 'Files%s' % event.event_type.capitalize()
        if et in self.data.keys():
            self.data[et].append(event.src_path)
        else:
            self.data[et] = [event.src_path]

class WatchdogStartup(Publisher):
    publishes = Events().WatchdogStartup.keys()

    def __init__(self, dispatcher, settings):
        super(WatchdogStartup, self).__init__(dispatcher)
        self.settings = settings.getWatchdogStartupSettings()

    def start(self):
        oldsnapshots = WatchdogStartup.getPickle()
        newsnapshots = {}
        for setting in self.settings:
            folder = translatepath(setting['ws_folder'])
            if os.path.exists(folder):
                newsnapshot = DirectorySnapshot(folder, recursive=setting['ws_recursive'])
                newsnapshots[folder] = newsnapshot
                if oldsnapshots is not None:
                    if folder in oldsnapshots.keys():
                        oldsnapshot = oldsnapshots[folder]
                        diff = DirectorySnapshotDiff(oldsnapshot, newsnapshot)
                        changes = self.getChangesFromDiff(diff)
                        if len(changes) > 0:
                            eh = EventHandler(patterns=setting['ws_patterns'].split(u','), ignore_patterns=setting['ws_ignore_patterns'].split(u','),
                                              ignore_directories=setting['ws_ignore_directories'])
                            observer = Observer()
                            try:
                                observer.schedule(eh, folder, recursive=setting['ws_recursive'])
                                time.sleep(0.5)
                                for change in changes:
                                    eh.dispatch(change)
                                    time.sleep(0.25)
                                try:
                                    observer.unschedule_all()
                                except Exception:
                                    pass
                            except Exception:
                                raise
                            if len(eh.data) > 0:
                                message = Message(Topic('onStartupFileChanges', setting['key']), listOfChanges=eh.data)
                                self.publish(message)
            else:
                message = Message(Topic('onStartupFileChanges', setting['key']), listOfChanges=[{'DirsDeleted':folder}])
                log(msg=_(u'Watchdog Startup folder not found: %s') % folder)
                self.publish(message)

    @staticmethod
    def getChangesFromDiff(diff):
        ret = []
        events = {'dirs_created':(EVENT_TYPE_CREATED, True), 'dirs_deleted':(EVENT_TYPE_DELETED, True), 'dirs_modified':(EVENT_TYPE_MODIFIED, True), 'dirs_moved':(EVENT_TYPE_MOVED, True),
                  'files_created':(EVENT_TYPE_CREATED, False), 'files_deleted':(EVENT_TYPE_DELETED, False), 'files_modified':(EVENT_TYPE_MODIFIED, False), 'files_moved':(EVENT_TYPE_MOVED, False)}
        for event in events.keys():
            try:
                mylist = diff.__getattribute__(event)
            except AttributeError:
                mylist = []
            if len(mylist) > 0:
                for item in mylist:
                    evt = FileSystemEvent(item)
                    evt.event_type = events[event][0]
                    evt.is_directory = events[event][1]
                    ret.append(evt)
        return ret

    def abort(self, *args):
        snapshots = {}
        for setting in self.settings:
            folder = xbmc.translatePath(setting['ws_folder'])
            if folder == u'':
                folder = setting['ws_folder']
            folder = translatepath(folder)
            if os.path.exists(folder):
                snapshot = DirectorySnapshot(folder, recursive=setting['ws_recursive'])
                snapshots[folder] = snapshot
        WatchdogStartup.savePickle(snapshots)

    def join(self, timeout=None):
        pass

    @staticmethod
    def savePickle(snapshots):
        picklepath = WatchdogStartup.getPicklePath()
        try:
            with open(picklepath, 'w') as f:
                pickle.dump(snapshots, f)
        except pickle.PicklingError:
            log(msg=_('Watchdog startup pickling error on exit'))
        except OSError:
            log(msg=_('Watchdog startup OSError on pickle attempt'))
        else:
            log(msg=_('Watchdog startup pickle saved'))

    @staticmethod
    def clearPickle():
        path = WatchdogStartup.getPicklePath()
        if os.path.exists(path):
            try:
                os.remove(path)
            except OSError:
                log(msg=_('Watchdog startup could not clear pickle'))

    @staticmethod
    def getPicklePath():
        path = translatepath('special://addondata/watchdog.pkl')
        setPathRW(os.path.split(path)[0])
        return path

    @staticmethod
    def getPickle():
        picklepath = WatchdogStartup.getPicklePath()
        if not os.path.exists(picklepath):
            return
        try:
            with open(picklepath, 'r') as f:
                oldsnapshots = pickle.load(f)
        except OSError:
            log (msg=_('Watchdog Startup could not load pickle'))
        except pickle.UnpicklingError:
            log (msg=_('Watchdog Startup unpickling error'))
        else:
            return oldsnapshots

