#!/usr/bin/python
# -*- coding: utf-8 -*-
#
#     Copyright (C) 2014 KenV99
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
#   MEANT TO BE RUN USING NOSE

import xbmc
import os
import sys
from resources.lib.publishers.log import LogPublisher
import resources.lib.publishers.loop as loop
import resources.lib.publishers.log as log
from resources.lib.publishers.loop import LoopPublisher
from resources.lib.publishers.watchdog import WatchdogPublisher
from resources.lib.publishers.watchdogStartup import WatchdogStartup
from resources.lib.publishers.schedule import SchedulePublisher
from resources.lib.pubsub import Dispatcher, Subscriber, Message, Topic
from resources.lib.settings import Settings
from resources.lib.utils.kodipathtools import translatepath, setPathRW
from flexmock import flexmock
import Queue
import threading
import time
import nose


# from nose.plugins.skip import SkipTest

def printlog(msg,level=0):
    print msg, level


flexmock(xbmc, log=printlog)


def sleep(xtime):
    time.sleep(xtime / 1000.0)


class MockSubscriber(Subscriber):
    def __init__(self):
        super(MockSubscriber, self).__init__()
        self.testq = Queue.Queue()

    def notify(self, message):
        self.testq.put(message)

    def retrieveMessages(self):
        messages = []
        while not self.testq.empty():
            try:
                message = self.testq.get(timeout=1)
            except Queue.Empty:
                pass
            else:
                messages.append(message)
        return messages

    def waitForMessage(self, count=1, timeout=30):
        loopcount = 0
        while loopcount < timeout:
            msgcount = self.testq.qsize()
            if msgcount >= count:
                return
            else:
                time.sleep(1)
                loopcount += 1


# @SkipTest
class testWatchdogStartup(object):
    def __init__(self):
        self.publisher = None
        self.dispatcher = None
        self.subscriber = None
        self.topic = None
        self.folder = None
        self.saveduserpickle = None

    def setup(self):
        self.folder = translatepath('special://addon/resources/lib/tests')
        watchdogStartupSettings = [
            {'ws_folder': self.folder, 'ws_patterns': '*', 'ws_ignore_patterns': '', 'ws_ignore_directories': True,
             'ws_recursive': False, 'key': 'E1'}]
        self.saveduserpickle = WatchdogStartup.getPickle()
        self.dispatcher = Dispatcher()
        self.subscriber = MockSubscriber()
        self.topic = Topic('onStartupFileChanges', 'E1')
        self.subscriber.addTopic(self.topic)
        self.dispatcher.addSubscriber(self.subscriber)
        settings = Settings()
        flexmock(settings, getWatchdogStartupSettings=watchdogStartupSettings)
        self.publisher = WatchdogStartup(self.dispatcher, settings)
        self.dispatcher.start()

    def teardown(self):
        WatchdogStartup.savePickle(self.saveduserpickle)
        self.publisher.abort()
        self.dispatcher.abort()
        del self.publisher
        del self.dispatcher

    def testWatchdogPublisherCreate(self):
        fn = os.path.join(self.folder, 'test.txt')
        if os.path.exists(fn):
            os.remove(fn)
        self.publisher.start()
        self.publisher.abort()
        time.sleep(1)
        self.subscriber.testq = Queue.Queue()
        with open(fn, 'w') as f:
            f.writelines('test')
        time.sleep(1)
        self.publisher.start()
        self.subscriber.waitForMessage(count=2, timeout=2)
        self.publisher.abort()
        self.dispatcher.abort()
        os.remove(fn)
        messages = self.subscriber.retrieveMessages()
        found = False
        for message in messages:
            assert isinstance(message, Message)
            assert 'listOfChanges' in message.kwargs.keys()
            tmp = message.kwargs['listOfChanges']
            if 'FilesCreated' in tmp.keys() and [fn] in tmp.values():
                found = True
                assert message.topic == self.topic
        assert found == True
        if len(messages) > 1:
            raise AssertionError('Warning: Too many messages found for Watchdog Startup Create')


# @SkipTest
class testWatchdog(object):
    def __init__(self):
        self.publisher = None
        self.dispatcher = None
        self.subscriber = None
        self.topic = None
        self.folder = None

    def setup(self):
        self.folder = translatepath('special://addon/resources/lib/tests')
        setPathRW(self.folder)
        watchdogSettings = [{'folder': self.folder, 'patterns': '*', 'ignore_patterns': '', 'ignore_directories': True,
                             'recursive': False, 'key': 'E1'}]
        self.dispatcher = Dispatcher()
        self.subscriber = MockSubscriber()
        self.topic = Topic('onFileSystemChange', 'E1')
        self.subscriber.addTopic(self.topic)
        self.dispatcher.addSubscriber(self.subscriber)
        settings = Settings()
        flexmock(settings, getWatchdogSettings=watchdogSettings)
        self.publisher = WatchdogPublisher(self.dispatcher, settings)
        self.dispatcher.start()

    def teardown(self):
        self.publisher.abort()
        self.dispatcher.abort()
        del self.publisher
        del self.dispatcher

    def testWatchdogPublisherCreate(self):
        fn = os.path.join(self.folder, 'test.txt')
        if os.path.exists(fn):
            os.remove(fn)
        time.sleep(1)
        self.publisher.start()
        time.sleep(1)
        with open(fn, 'w') as f:
            f.writelines('test')
        self.subscriber.waitForMessage(count=2, timeout=2)
        self.publisher.abort()
        self.dispatcher.abort()
        time.sleep(1)
        os.remove(fn)
        messages = self.subscriber.retrieveMessages()
        foundc = False
        foundm = False
        fmesgc = None
        fmesgm = None
        for message in messages:
            assert isinstance(message, Message)
            if message.kwargs['event'] == 'created':
                foundc = True
                fmesgc = message
            elif message.kwargs['event'] == 'modified':
                foundm = True
                fmesgm = message
        assert foundc is True
        assert fmesgc.topic == self.topic
        assert fmesgc.kwargs['path'] == fn
        assert foundm is True
        assert fmesgm.topic == self.topic, 'Warning Only'
        assert fmesgm.kwargs['path'] == fn, 'Warning Only'
        if len(messages) > 2:
            raise AssertionError('Warning: Too many messages found for Watchdog Create')

    def testWatchdogPublisherDelete(self):
        fn = os.path.join(self.folder, 'test.txt')
        if os.path.exists(fn) is False:
            with open(fn, 'w') as f:
                f.writelines('test')
        time.sleep(1)
        self.publisher.start()
        time.sleep(2)
        os.remove(fn)
        self.subscriber.waitForMessage(count=1, timeout=2)
        self.publisher.abort()
        self.dispatcher.abort()
        messages = self.subscriber.retrieveMessages()
        found = False
        fmesg = None
        for message in messages:
            assert isinstance(message, Message)
            if message.kwargs['event'] == 'deleted':
                found = True
                fmesg = message
        assert found is True
        assert fmesg.topic == self.topic
        assert fmesg.kwargs['path'] == fn
        if len(messages) > 1:
            raise AssertionError('Warning: Too many messages found for Watchdog Delete')

    def testWatchdogPublisherModify(self):
        fn = os.path.join(self.folder, 'test.txt')
        if os.path.exists(fn) is False:
            with open(fn, 'w') as f:
                f.writelines('test')
        time.sleep(1)
        self.publisher.start()
        time.sleep(1)
        with open(fn, 'a') as f:
            f.writelines('test2')
        self.subscriber.waitForMessage(count=1, timeout=2)
        self.publisher.abort()
        self.dispatcher.abort()
        os.remove(fn)
        messages = self.subscriber.retrieveMessages()
        found = False
        fmesg = None
        for message in messages:
            assert isinstance(message, Message)
            if message.kwargs['event'] == 'modified':
                found = True
                fmesg = message
        assert found is True
        assert fmesg.topic == self.topic
        assert fmesg.kwargs['path'] == fn
        if len(messages) > 1:
            raise AssertionError('Warning: Too many messages found for Watchdog Modify')


# @SkipTest
class testLoop(object):
    def __init__(self):
        self.publisher = None
        self.dispatcher = None
        self.subscriber = None
        self.globalidletime = None
        self.starttime = None
        self.topics = None

    def getGlobalIdleTime(self):
        if self.globalidletime is None:
            self.starttime = time.time()
            self.globalidletime = 0
            return 0
        else:
            self.globalidletime = int(time.time() - self.starttime)
            return self.globalidletime

    def getStereoMode(self):
        if self.getGlobalIdleTime() < 2:
            return 'off'
        else:
            return 'split_vertical'

    def getCurrentWindowId(self):
        git = self.getGlobalIdleTime()
        if git < 2:
            return 10000
        elif 2 <= git < 4:
            return 10001
        else:
            return 10002

    def getProfileString(self):
        if self.getGlobalIdleTime() < 2:
            return 'Bob'
        else:
            return 'Mary'

    def setup(self):
        flexmock(loop.xbmc, getGlobalIdleTime=self.getGlobalIdleTime)
        flexmock(loop.xbmc, sleep=sleep)
        flexmock(loop, getStereoscopicMode=self.getStereoMode)
        flexmock(loop, getProfileString=self.getProfileString)
        flexmock(loop.xbmc.Player, isPlaying=False)
        flexmock(loop.xbmcgui, getCurrentWindowId=self.getCurrentWindowId)
        self.dispatcher = Dispatcher()
        self.subscriber = MockSubscriber()

    def teardown(self):
        self.publisher.abort()
        self.dispatcher.abort()
        del self.publisher
        del self.dispatcher

    def testLoopIdle(self):
        self.topics = [Topic('onIdle', 'E1'), Topic('onIdle', 'E2')]
        for topic in self.topics:
            self.subscriber.addTopic(topic)
        self.dispatcher.addSubscriber(self.subscriber)
        idleSettings = {'E1': 3, 'E2': 5}
        settings = Settings()
        flexmock(settings, getIdleTimes=idleSettings)
        flexmock(settings, general={'LoopFreq': 100})
        self.publisher = LoopPublisher(self.dispatcher, settings)
        self.dispatcher.start()
        self.publisher.start()
        self.subscriber.waitForMessage(count=2, timeout=7)
        self.publisher.abort()
        self.dispatcher.abort()
        messages = self.subscriber.retrieveMessages()
        msgtopics = [msg.topic for msg in messages]
        for topic in self.topics:
            assert topic in msgtopics

    def testStereoModeChange(self):
        self.topics = [Topic('onStereoModeChange')]
        self.subscriber.addTopic(self.topics[0])
        self.dispatcher.addSubscriber(self.subscriber)
        settings = Settings()
        flexmock(settings, general={'LoopFreq': 100})
        self.publisher = LoopPublisher(self.dispatcher, settings)
        self.dispatcher.start()
        self.publisher.start()
        self.subscriber.waitForMessage(count=1, timeout=5)
        self.publisher.abort()
        self.dispatcher.abort()
        messages = self.subscriber.retrieveMessages()
        msgtopics = [msg.topic for msg in messages]
        for topic in self.topics:
            assert topic in msgtopics

    def testOnWindowOpen(self):
        self.topics = [Topic('onWindowOpen', 'E1')]
        self.subscriber.addTopic(self.topics[0])
        self.dispatcher.addSubscriber(self.subscriber)
        settings = Settings()
        flexmock(settings, general={'LoopFreq': 100})
        flexmock(settings, getOpenwindowids={10001: 'E1'})
        self.publisher = LoopPublisher(self.dispatcher, settings)
        self.dispatcher.start()
        self.publisher.start()
        self.subscriber.waitForMessage(count=1, timeout=5)
        self.publisher.abort()
        self.dispatcher.abort()
        messages = self.subscriber.retrieveMessages()
        msgtopics = [msg.topic for msg in messages]
        for topic in self.topics:
            assert topic in msgtopics

    def testOnWindowClose(self):
        self.topics = [Topic('onWindowClose', 'E1')]
        self.subscriber.addTopic(self.topics[0])
        self.dispatcher.addSubscriber(self.subscriber)
        settings = Settings()
        flexmock(settings, general={'LoopFreq': 100})
        flexmock(settings, getClosewindowids={10001: 'E1'})
        self.publisher = LoopPublisher(self.dispatcher, settings)
        self.dispatcher.start()
        self.publisher.start()
        self.subscriber.waitForMessage(count=1, timeout=5)
        self.publisher.abort()
        self.dispatcher.abort()
        messages = self.subscriber.retrieveMessages()
        msgtopics = [msg.topic for msg in messages]
        for topic in self.topics:
            assert topic in msgtopics

    def testProfileChange(self):
        self.topics = [Topic('onProfileChange')]
        self.subscriber.addTopic(self.topics[0])
        self.dispatcher.addSubscriber(self.subscriber)
        settings = Settings()
        flexmock(settings, general={'LoopFreq': 100})
        self.publisher = LoopPublisher(self.dispatcher, settings)
        self.dispatcher.start()
        self.publisher.start()
        self.subscriber.waitForMessage(count=1, timeout=5)
        self.publisher.abort()
        self.dispatcher.abort()
        messages = self.subscriber.retrieveMessages()
        msgtopics = [msg.topic for msg in messages]
        for topic in self.topics:
            assert topic in msgtopics


# @SkipTest
class testLog(object):
    path = translatepath('special://addondata')
    if not os.path.exists(path):
        os.mkdir(path)
    setPathRW(path)
    fn = translatepath('special://addondata/kodi.log')

    def __init__(self):
        self.publisher = None
        self.dispatcher = None
        self.subscriber = None
        self.globalidletime = None
        self.starttime = None
        self.topics = None

    @staticmethod
    def logSimulate():
        import random, string
        randomstring = ''.join(random.choice(string.lowercase) for _ in range(30)) + '\n'
        targetstring = '%s%s%s' % (randomstring[:12], 'kodi_callbacks', randomstring[20:])
        for i in xrange(0, 10):
            with open(testLog.fn, 'a') as f:
                if i == 5:
                    f.writelines(targetstring)
                else:
                    f.writelines(randomstring)
            time.sleep(0.25)

    def setup(self):
        flexmock(log, logfn=testLog.fn)
        flexmock(log.xbmc, log=printlog)
        flexmock(log.xbmc, sleep=sleep)
        self.dispatcher = Dispatcher()
        self.subscriber = MockSubscriber()

    def teardown(self):
        self.publisher.abort()
        self.dispatcher.abort()
        del self.publisher
        del self.dispatcher

    def testLogSimple(self):
        self.topics = [Topic('onLogSimple', 'E1')]
        xsettings = [{'matchIf': 'kodi_callbacks', 'rejectIf': '', 'eventId': 'E1'}]
        settings = Settings()
        flexmock(settings, getLogSimples=xsettings)
        flexmock(settings, general={'LogFreq': 100})
        self.publisher = LogPublisher(self.dispatcher, settings)
        try:
            os.remove(testLog.fn)
        except OSError:
            pass
        finally:
            with open(testLog.fn, 'w') as f:
                f.writelines('')
        self.subscriber.addTopic(self.topics[0])
        self.dispatcher.addSubscriber(self.subscriber)
        self.dispatcher.start()
        self.publisher.start()
        xthread = threading.Thread(target=testLog.logSimulate)
        xthread.start()
        xthread.join()
        self.publisher.abort()
        self.dispatcher.abort()
        self.subscriber.waitForMessage(count=1, timeout=2)
        try:
            os.remove(testLog.fn)
        except OSError:
            pass
        messages = self.subscriber.retrieveMessages()
        msgtopics = [msg.topic for msg in messages]
        for topic in self.topics:
            assert topic in msgtopics

    def testLogRegex(self):
        self.topics = [Topic('onLogRegex', 'E1')]
        xsettings = [{'matchIf': 'kodi_callbacks', 'rejectIf': '', 'eventId': 'E1'}]
        settings = Settings()
        flexmock(settings, getLogRegexes=xsettings)
        flexmock(settings, general={'LogFreq': 100})
        self.publisher = LogPublisher(self.dispatcher, settings)
        try:
            os.remove(testLog.fn)
        except OSError:
            pass
        finally:
            with open(testLog.fn, 'w') as f:
                f.writelines('')
        self.subscriber.addTopic(self.topics[0])
        self.dispatcher.addSubscriber(self.subscriber)
        self.dispatcher.start()
        self.publisher.start()
        t = threading.Thread(target=testLog.logSimulate)
        t.start()
        t.join()
        self.publisher.abort()
        self.dispatcher.abort()
        self.subscriber.waitForMessage(count=1, timeout=2)
        try:
            os.remove(testLog.fn)
        except OSError:
            pass
        messages = self.subscriber.retrieveMessages()
        msgtopics = [msg.topic for msg in messages]
        for topic in self.topics:
            assert topic in msgtopics

# @SkipTest
class TestSchedule(object):
    def __init__(self):
        self.publisher = None
        self.dispatcher = None
        self.subscriber = None
        self.topics = None

    def setup(self):
        flexmock(log.xbmc, log=printlog)
        flexmock(log.xbmc, sleep=sleep)
        self.dispatcher = Dispatcher()
        self.subscriber = MockSubscriber()

    def teardown(self):
        self.publisher.abort()
        self.dispatcher.abort()
        del self.publisher
        del self.dispatcher

    def testDailyAlarm(self):
        from time import strftime
        self.topics = [Topic('onDailyAlarm', 'E1')]
        hour, minute = strftime('%H:%M').split(':')
        xsettings = [{'hour': int(hour), 'minute': int(minute) + 1, 'key': 'E1'}]
        settings = Settings()
        flexmock(settings, getEventsByType=xsettings)
        self.publisher = SchedulePublisher(self.dispatcher, settings)
        self.publisher.intervalAlarms = []
        self.publisher.sleep = time.sleep
        self.publisher.sleepinterval = 1
        self.subscriber.addTopic(self.topics[0])
        self.dispatcher.addSubscriber(self.subscriber)
        self.dispatcher.start()
        self.publisher.start()
        self.subscriber.waitForMessage(count=1, timeout=65)
        self.publisher.abort()
        self.dispatcher.abort()
        messages = self.subscriber.retrieveMessages()
        msgtopics = [msg.topic for msg in messages]
        time.sleep(1)
        for topic in self.topics:
            assert topic in msgtopics

    def testIntervalAlarm(self):
        self.topics = [Topic('onIntervalAlarm', 'E1')]
        xsettings = [{'hours': 0, 'minutes': 0, 'seconds': 10, 'key': 'E1'}]
        settings = Settings()
        self.dispatcher = Dispatcher()
        self.subscriber = MockSubscriber()
        flexmock(settings, getEventsByType=xsettings)
        self.publisher = SchedulePublisher(self.dispatcher, settings)
        self.publisher.dailyAlarms = []
        self.publisher.sleep = time.sleep
        self.publisher.sleepinterval = 1
        self.subscriber.testq = Queue.Queue()
        self.subscriber.addTopic(self.topics[0])
        self.dispatcher.addSubscriber(self.subscriber)
        self.dispatcher.start()
        self.publisher.start()
        self.subscriber.waitForMessage(count=1, timeout=20)
        self.publisher.abort()
        self.dispatcher.abort()
        messages = self.subscriber.retrieveMessages()
        msgtopics = [msg.topic for msg in messages]
        for topic in self.topics:
            assert topic in msgtopics


def main():
    module_name = sys.modules[__name__].__file__
    result = nose.run(
        argv=[sys.argv[0],
              module_name]
    )
    return result


if __name__ == '__main__':
    main()
