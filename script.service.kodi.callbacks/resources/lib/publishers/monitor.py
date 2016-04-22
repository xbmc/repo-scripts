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
import threading
import xbmc
from resources.lib.pubsub import Publisher, Topic, Message
from resources.lib.events import Events
from resources.lib.utils.poutil import KodiPo
kodipo = KodiPo()
_ = kodipo.getLocalizedString

class MonitorPublisher(threading.Thread, Publisher):
    publishes = Events().Monitor.keys()

    def __init__(self, dispatcher, settings):
        Publisher.__init__(self, dispatcher)
        threading.Thread.__init__(self, name='MonitorPublisher')
        self.dispatcher = dispatcher
        self._abortevt = threading.Event()
        self._abortevt.clear()
        self.jsoncriteria = settings.getJsonNotifications()

    def run(self):
        publish = super(MonitorPublisher, self).publish
        monitor = _Monitor()
        monitor.jsoncriteria = self.jsoncriteria
        monitor.publish = publish
        while not self._abortevt.is_set():
            xbmc.sleep(500)
        del monitor

    def abort(self, timeout=0):
        self._abortevt.set()
        if timeout > 0:
            self.join(timeout)
            if self.is_alive():
                xbmc.log(msg=_('Could not stop MonitorPublisher T:%i') % self.ident)

class _Monitor(xbmc.Monitor):
    def __init__(self):
        super(_Monitor, self).__init__()
        self.publish = None
        self.jsoncriteria = None

    def onCleanFinished(self, library):
        topic = Topic('onCleanFinished')
        kwargs = {'library':library}
        self.publish(Message(topic, **kwargs))

    def onCleanStarted(self, library):
        topic = Topic('onCleanStarted')
        kwargs = {'library':library}
        self.publish(Message(topic, **kwargs))

    def onDPMSActivated(self):
        topic = Topic('onDPMSActivated')
        kwargs = {}
        self.publish(Message(topic, **kwargs))

    def onDPMSDeactivated(self):
        topic = Topic('onDPMSDeactivated')
        kwargs = {}
        self.publish(Message(topic, **kwargs))

    def onNotification(self, sender, method, data):
        for criterion in self.jsoncriteria:
            if criterion['sender'] == sender and criterion['method'] == method and criterion['data'] == data:
                topic = Topic('onNotification', criterion['eventId'])
                kwargs = {'sender':sender, 'method':method, 'data':data}
                self.publish(Message(topic, **kwargs))

    def onScanStarted(self, library):
        topic = Topic('onScanStarted')
        kwargs = {'library':library}
        self.publish(Message(topic, **kwargs))

    def onScanFinished(self, library):
        topic = Topic('onScanFinished')
        kwargs = {'library':library}
        self.publish(Message(topic, **kwargs))

    def onScreensaverActivated(self):
        topic = Topic('onScreensaverActivated')
        kwargs = {}
        self.publish(Message(topic, **kwargs))

    def onScreensaverDeactivated(self):
        topic = Topic('onScreensaverDeactivated')
        kwargs = {}
        self.publish(Message(topic, **kwargs))

