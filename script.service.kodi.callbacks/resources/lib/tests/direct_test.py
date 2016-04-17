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

from resources.lib.pubsub import TaskReturn
from resources.lib.utils.poutil import KodiPo
from resources.lib.kodilogging import KodiLogger
kl = KodiLogger()
log = kl.log
kodipo = KodiPo()
_ = kodipo.getLocalizedString

def testMsg(taskManager, taskSettings, kwargs):
    msg = [_('Testing for task type: %s') % taskSettings['type'], _('Settings: %s') % str(taskManager.taskKwargs),
           _('Runtime kwargs: %s') % str(kwargs)]
    return msg

class TestHandler(object):
    testMessage = []

    def __init__(self, testMessage):
        TestHandler.testMessage = testMessage

    @staticmethod
    def testReturnHandler(taskReturn):
        assert isinstance(taskReturn, TaskReturn)
        from resources.lib.dialogtb import show_textbox
        if taskReturn.iserror is False:
            TestHandler.testMessage.append(_('Command for Task %s, Event %s completed succesfully!') % (taskReturn.taskId, taskReturn.eventId))
            if taskReturn.msg != '':
                TestHandler.testMessage.append(_('The following message was returned: %s') % taskReturn.msg)
                log(msg='\n'.join(TestHandler.testMessage), loglevel=kl.LOGNOTICE)
        else:
            TestHandler.testMessage.append(_('ERROR encountered for Task %s, Event %s\nERROR mesage: %s') % (taskReturn.taskId, taskReturn.eventId, taskReturn.msg))
            log(msg='\n'.join(TestHandler.testMessage), loglevel=kl.LOGERROR)
        show_textbox('Test Results', TestHandler.testMessage)

class TestLogger(object):
    def __init__(self):
        self._log = []

    def log(self, level=1, msg=''):
        assert isinstance(level, int)
        msg_list = msg.split('\n')
        if not isinstance(msg_list, list):
            msg_list = [msg]
        self._log.extend(msg_list)

    def retrieveLogAsList(self):
        return self._log
