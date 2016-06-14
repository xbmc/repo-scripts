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


debug = False  # TODO: check
testdebug = False  # TODO: check
testTasks = False  # TODO: check
branch = 'master'
build = '1018'

from resources.lib.utils.debugger import startdebugger

if debug:
    startdebugger()

import os
import sys
import threading
import xbmc
import xbmcaddon
import resources.lib.pubsub as PubSub_Threaded
from resources.lib.kodilogging import KodiLogger
from resources.lib.publisherfactory import PublisherFactory
from resources.lib.subscriberfactory import SubscriberFactory
from resources.lib.settings import Settings
from resources.lib.utils.poutil import KodiPo
import xbmcgui

kodipo = KodiPo()
_ = kodipo.getLocalizedString
log = KodiLogger.log

try:
    _addonversion_ = xbmcaddon.Addon().getAddonInfo('version')
except RuntimeError:
    try:
        _addonversion_ = xbmcaddon.Addon('script.service.kodi.callbacks').getAddonInfo('version')
    except RuntimeError:
        _addonversion_ = 'ERROR getting version'


class Cache(object):
    publishers = None
    dispatcher = None


class MainMonitor(xbmc.Monitor):
    def __init__(self):
        super(MainMonitor, self).__init__()

    def onSettingsChanged(self):
        dialog = xbmcgui.Dialog()
        msg = _('If improperly implemented, running user tasks can damage your system.\nThe user assumes all risks and liability for running tasks.').split('\n')
        dialog.ok(_('Kodi Callbacks'), line1=msg[0], line2=msg[1])
        log(msg=_('Settings change detected - attempting to restart'))
        abortall()
        start()


def abortall():
    for p in Cache.publishers:
        try:
            p.abort()
        except threading.ThreadError as e:
            log(msg=_('Error aborting: %s - Error: %s') % (str(p), str(e)))
    Cache.dispatcher.abort()
    for p in Cache.publishers:
        p.join(0.5)
    Cache.dispatcher.join(0.5)
    if len(threading.enumerate()) > 1:
        main_thread = threading.current_thread()
        log(msg=_('Enumerating threads to kill others than main (%i)') % main_thread.ident)
        for t in threading.enumerate():
            if t is not main_thread and t.is_alive():
                log(msg=_('Attempting to kill thread: %i: %s') % (t.ident, t.name))
                try:
                    t.abort(0.5)
                except (threading.ThreadError, AttributeError):
                    log(msg=_('Error killing thread'))
                else:
                    if not t.is_alive():
                        log(msg=_('Thread killed succesfully'))
                    else:
                        log(msg=_('Error killing thread'))


def start():
    global log
    settings = Settings()
    settings.getSettings()
    kl = KodiLogger()
    if settings.general['elevate_loglevel'] is True:
        kl.setLogLevel(xbmc.LOGNOTICE)
    else:
        kl.setLogLevel(xbmc.LOGDEBUG)
    log = kl.log
    log(msg=_('Settings read'))
    Cache.dispatcher = PubSub_Threaded.Dispatcher(interval=settings.general['TaskFreq'], sleepfxn=xbmc.sleep)
    log(msg=_('Dispatcher initialized'))

    subscriberfactory = SubscriberFactory(settings, kl)
    subscribers = subscriberfactory.createSubscribers()
    for subscriber in subscribers:
        Cache.dispatcher.addSubscriber(subscriber)
    publisherfactory = PublisherFactory(settings, subscriberfactory.topics, Cache.dispatcher, kl, debug)
    publisherfactory.createPublishers()
    Cache.publishers = publisherfactory.ipublishers

    Cache.dispatcher.start()
    log(msg=_('Dispatcher started'))

    for p in Cache.publishers:
        try:
            p.start()
        except threading.ThreadError:
            raise
    log(msg=_('Publisher(s) started'))


def main():
    msg = _(u'$$$ [kodi.callbacks] - Staring kodi.callbacks ver: %s (%s:build %s) python: %s').encode('utf-8') % (str(_addonversion_), branch, build, sys.version)
    xbmc.log(msg=msg, level=xbmc.LOGNOTICE)
    if branch != 'master':
        xbmcaddon.Addon().setSetting('installed branch', branch)
    start()
    Cache.dispatcher.q_message(PubSub_Threaded.Message(PubSub_Threaded.Topic('onStartup')))
    monitor = MainMonitor()
    log(msg=_('Entering wait loop'))
    monitor.waitForAbort()

    # Shutdown tasks
    Cache.dispatcher.q_message(PubSub_Threaded.Message(PubSub_Threaded.Topic('onShutdown'), pid=os.getpid()))
    log(msg=_('Shutdown started'))
    abortall()
    log(msg='Shutdown complete')


if __name__ == '__main__':

    if testTasks:
        KodiLogger.setLogLevel(KodiLogger.LOGNOTICE)
        startdebugger()
        from resources.lib.tests.testTasks import testTasks

        tt = testTasks()
        tt.runTests()
    else:
        if branch != 'master':
            try:
                from resources.lib.utils.githubtools import processargs
            except ImportError:
                pass
            else:
                processargs(sys.argv)
        main()
