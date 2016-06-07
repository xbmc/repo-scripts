#!/usr/bin/python
# -*- coding: utf-8 -*-
#
#     Copyright (C) 2015 KenV99
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

import xbmc
import threading
from Queue import Queue, Empty
import re
import codecs
from resources.lib.pubsub import Publisher, Topic, Message
from resources.lib.events import Events
from resources.lib.utils.poutil import KodiPo
kodipo = KodiPo()
_ = kodipo.getLocalizedString

logfn = xbmc.translatePath(r'special://logpath/kodi.log')

class LogMonitor(threading.Thread):
    def __init__(self, interval=100):
        super(LogMonitor, self).__init__(name='LogMonitor')
        self.logfn = logfn
        self.__abort_evt = threading.Event()
        self.__abort_evt.clear()
        self.ouputq = Queue()
        self.interval = interval

    def run(self):
        with codecs.open(self.logfn, 'r', encoding='utf-8', errors='ignore') as f:
            f.seek(0, 2)           # Seek @ EOF
            fsize_old = f.tell()
            while not self.__abort_evt.is_set():
                f.seek(0, 2)           # Seek @ EOF
                fsize = f.tell()        # Get Size
                if fsize > fsize_old:
                    f.seek(fsize_old, 0)
                    lines = f.readlines()       # Read to end
                    for line in lines:
                        self.ouputq.put(line, False)
                    fsize_old = f.tell()
                xbmc.sleep(self.interval)

    def abort(self, timeout=0):
        self.__abort_evt.set()
        if timeout > 0:
            self.join(timeout)
            if self.is_alive():
                xbmc.log(msg=_('Could not stop LogMonitor T:%i') % self.ident)

class LogPublisher(threading.Thread, Publisher):

    publishes = Events.Log.keys()

    def __init__(self, dispatcher, settings):
        Publisher.__init__(self, dispatcher)
        threading.Thread.__init__(self, name='LogPublisher')
        self._checks_simple = []
        self._checks_regex = []
        self.abort_evt = threading.Event()
        self.abort_evt.clear()
        self.interval_checker = settings.general['LogFreq']
        self.interval_monitor = settings.general['LogFreq']
        self.add_simple_checks(settings.getLogSimples())
        self.add_regex_checks(settings.getLogRegexes())

    def add_simple_checks(self, simpleList):
        for chk in simpleList:
            self.add_simple_check(chk['matchIf'], chk['rejectIf'], chk['eventId'])

    def add_regex_checks(self, regexList):
        for chk in regexList:
            self.add_re_check(chk['matchIf'], chk['rejectIf'], chk['eventId'])

    def add_simple_check(self, match, nomatch, subtopic):
        self._checks_simple.append(LogCheckSimple(match, nomatch, subtopic, self.publish))

    def add_re_check(self, match, nomatch, subtopic):
        self._checks_regex.append(LogCheckRegex(match, nomatch, subtopic, self.publish))

    def run(self):
        lm = LogMonitor(interval=self.interval_monitor)
        lm.start()
        for chk in self._checks_simple:
            chk.start()
        for chk in self._checks_regex:
            chk.start()
        while not self.abort_evt.is_set():
            while not lm.ouputq.empty():
                try:
                    line = lm.ouputq.get_nowait()
                except Empty:
                    continue
                for chk in self._checks_simple:
                    chk.queue.put(line, False)
                for chk in self._checks_regex:
                    chk.queue.put(line, False)
                if self.abort_evt.is_set():
                    continue
            xbmc.sleep(self.interval_checker)
        for chk in self._checks_simple:
            chk.abort()
        for chk in self._checks_regex:
            chk.abort()
        lm.abort()

    def abort(self, timeout=0):
        self.abort_evt.set()
        if timeout > 0:
            self.join(timeout)
            if self.is_alive():
                xbmc.log(msg=_('Could not stop LogPublisher T:%i') % self.ident)

class LogCheck(object):
    def __init__(self, match, nomatch, callback, param):
        self.match = match
        self.nomatch = nomatch
        self.callback = callback
        self.param = param

class LogCheckSimple(threading.Thread):
    def __init__(self, match, nomatch, subtopic, publish):
        super(LogCheckSimple, self).__init__(name='LogCheckSimple')
        self.match = match
        self.nomatch = nomatch
        self.publish = publish
        self.queue = Queue()
        self._abort_evt = threading.Event()
        self._abort_evt.clear()
        self.topic = Topic('onLogSimple', subtopic)

    def run(self):
        while not self._abort_evt.is_set():
            while not self.queue.empty():
                try:
                    line = self.queue.get_nowait()
                except Empty:
                    continue
                if self.match in line:
                    if self.nomatch != '':
                        if (self.nomatch in line) is not True:
                            msg = Message(self.topic, line=line)
                            self.publish(msg)
                    else:
                        msg = Message(self.topic, line=line)
                        self.publish(msg)

    def abort(self, timeout=0):
        self._abort_evt.set()
        if timeout > 0:
            self.join(timeout)
            if self.is_alive():
                xbmc.log(msg=_('Could not stop LogCheckSimple T:%i') % self.ident)

class LogCheckRegex(threading.Thread):
    def __init__(self, match, nomatch, subtopic, publish):
        super(LogCheckRegex, self).__init__(name='LogCheckRegex')
        try:
            re_match = re.compile(match, flags=re.IGNORECASE)
        except re.error:
            raise
        if nomatch != '':
            try:
                re_nomatch = re.compile(nomatch, flags=re.IGNORECASE)
            except re.error:
                raise
        else:
            re_nomatch = None
        self.match = re_match
        self.nomatch = re_nomatch
        self.publish = publish
        self.queue = Queue()
        self._abort_evt = threading.Event()
        self._abort_evt.clear()
        self.topic = Topic('onLogRegex', subtopic)

    def run(self):
        while not self._abort_evt.is_set():
            while not self.queue.empty():
                try:
                    line = self.queue.get_nowait()
                except Empty:
                    continue
                if self.match.search(line):
                    if self.nomatch is not None:
                        if (self.nomatch.search(line)) is None:
                            msg = Message(self.topic, line=line)
                            self.publish(msg)
                    else:
                        msg = Message(self.topic, line=line)
                        self.publish(msg)

    def abort(self, timeout=0):
        self._abort_evt.set()
        if timeout > 0:
            self.join(timeout)
            if self.is_alive():
                xbmc.log(msg=_('Could not stop LogCheckRegex T:%i') % self.ident)