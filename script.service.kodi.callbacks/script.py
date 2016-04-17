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
scriptdebug = False  # TODO: check
testTasks = False  # TODO: check

import os
import sys

import resources.lib.pubsub as PubSub_Threaded
import xbmc
import xbmcgui
from default import branch
from resources.lib.kodilogging import KodiLogger
from resources.lib.settings import Settings
from resources.lib.subscriberfactory import SubscriberFactory
from resources.lib.utils.debugger import startdebugger
from resources.lib.utils.kodipathtools import translatepath
from resources.lib.utils.poutil import KodiPo


def notify(msg):
    dialog = xbmcgui.Dialog()
    dialog.notification('Kodi Callabacks', msg, xbmcgui.NOTIFICATION_INFO, 5000)


kodipo = KodiPo()
_ = kodipo.getLocalizedString
log = KodiLogger.log


def test(key):
    global log
    log = KodiLogger.log
    import resources.lib.tests.direct_test as direct_test
    from resources.lib.events import Events
    import traceback
    log(msg=_('Running Test for Event: %s') % key)
    events = Events().AllEvents
    settings = Settings()
    settings.getSettings()
    if settings.general['elevate_loglevel'] is True:
        KodiLogger.setLogLevel(xbmc.LOGNOTICE)
    else:
        KodiLogger.setLogLevel(xbmc.LOGDEBUG)
    log(msg=_('Settings for test read'))
    evtsettings = settings.events[key]
    topic = settings.topicFromSettingsEvent(key)
    task_key = settings.events[key]['task']
    tasksettings = settings.tasks[task_key]
    testlogger = direct_test.TestLogger()
    log(msg=_('Creating subscriber for test'))
    subscriberfactory = SubscriberFactory(settings, testlogger)
    subscriber = subscriberfactory.createSubscriber(key)
    if subscriber is not None:
        log(msg=_('Test subscriber created successfully'))
        try:
            kwargs = events[evtsettings['type']]['expArgs']
        except KeyError:
            kwargs = {}
        testRH = direct_test.TestHandler(direct_test.testMsg(subscriber.taskmanagers[0], tasksettings, kwargs))
        subscriber.taskmanagers[0].returnHandler = testRH.testReturnHandler
        # Run test
        log(msg=_('Running test'))
        nMessage = PubSub_Threaded.Message(topic=topic, **kwargs)
        try:
            subscriber.notify(nMessage)
        except Exception:
            msg = _('Unspecified error during testing')
            e = sys.exc_info()[0]
            if hasattr(e, 'message'):
                msg = str(e.message)
            msg = msg + '\n' + traceback.format_exc()
            log(msg=msg)
            msgList = msg.split('\n')
            import resources.lib.dialogtb as dialogtb
            dialogtb.show_textbox('Error', msgList)
    else:
        log(msg=_('Test subscriber creation failed due to errors'))
        msgList = testlogger.retrieveLogAsList()
        import resources.lib.dialogtb as dialogtb
        dialogtb.show_textbox('Error', msgList)

    xbmc.sleep(2000)


if __name__ == '__main__':
    dryrun = False
    addonid = 'script.service.kodi.callbacks'

    if len(sys.argv) > 1:
        if scriptdebug is True:
            startdebugger()
            dryrun = True

        if sys.argv[1] == 'regen':
            from resources.lib.kodisettings.generate_xml import generate_settingsxml

            generate_settingsxml()
            dialog = xbmcgui.Dialog()
            msg = _('Settings Regenerated')
            dialog.ok(_('Kodi Callbacks'), msg)

        elif sys.argv[1] == 'test':
            KodiLogger.setLogLevel(KodiLogger.LOGNOTICE)
            from resources.lib.tests.testTasks import testTasks

            tt = testTasks()
            tt.runTests()
            dialog = xbmcgui.Dialog()
            msg = _('Native Task Testing Complete - see log for results')
            dialog.notification(_('Kodi Callbacks'), msg, xbmcgui.NOTIFICATION_INFO, 5000)

        elif sys.argv[1] == 'updatefromzip':
            from resources.lib.utils.updateaddon import UpdateAddon

            KodiLogger.setLogLevel(KodiLogger.LOGNOTICE)
            dialog = xbmcgui.Dialog()
            zipfn = dialog.browse(1, _('Locate zip file'), 'files', '.zip', False, False, translatepath('~'))
            if zipfn != translatepath('~'):
                if os.path.isfile(zipfn):
                    ua = UpdateAddon(addonid)
                    ua.installFromZip(zipfn, updateonly=True, dryrun=dryrun)
                else:
                    dialog.ok(_('Kodi Callbacks'), _('Incorrect path'))

        elif sys.argv[1] == 'restorebackup':
            KodiLogger.setLogLevel(KodiLogger.LOGNOTICE)
            dialog = xbmcgui.Dialog()
            zipfn = dialog.browse(1, _('Locate backup zip file'), 'files', '.zip', False, False,
                                  translatepath('special://addondata/backup/'))
            if zipfn != translatepath('special://addondata/backup/'):
                from resources.lib.utils.updateaddon import UpdateAddon

                ua = UpdateAddon(addonid)
                ua.installFromZip(zipfn, updateonly=False, dryrun=dryrun)

        elif sys.argv[1] == 'lselector':
            from resources.lib.utils.selector import selectordialog

            try:
                result = selectordialog(sys.argv[2:])
            except (SyntaxError, TypeError) as e:
                xbmc.log(msg='Error: %s' % str(e), level=xbmc.LOGERROR)

        elif sys.argv[1] == 'logsettings':
            KodiLogger.setLogLevel(KodiLogger.LOGNOTICE)
            settings = Settings()
            settings.getSettings()
            settings.logSettings()
            dialog = xbmcgui.Dialog()
            msg = _('Settings written to log')
            dialog.ok(_('Kodi Callbacks'), msg)

        elif branch != 'master' and sys.argv[1] == 'checkupdate':
            try:
                from resources.lib.utils.githubtools import processargs
            except ImportError:
                pass
            else:
                processargs(sys.argv)

        else:
            # Direct Event/Task Testing
            KodiLogger.setLogLevel(KodiLogger.LOGNOTICE)
            eventId = sys.argv[1]
            test(eventId)

    elif testTasks:
        KodiLogger.setLogLevel(KodiLogger.LOGNOTICE)
        startdebugger()
        from resources.lib.tests.testTasks import testTasks

        tt = testTasks()
        tt.runTests()
