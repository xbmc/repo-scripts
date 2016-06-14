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

import sys
import traceback
import xbmc
from resources.lib.taskABC import AbstractTask, KodiLogger, notify
from resources.lib.utils.poutil import KodiPo
kodipo = KodiPo()
_ = kodipo.getLocalizedString
__ = kodipo.getLocalizedStringId

class TaskBuiltin(AbstractTask):
    tasktype = 'builtin'
    variables = [
        {
            'id':u'builtin',
            'settings':{
                'default':u'',
                'label':u'Kodi Builtin Function',
                'type':'text'
            }
        },
    ]

    def __init__(self):
        super(TaskBuiltin, self).__init__(name='Builtin')

    @staticmethod
    def validate(taskKwargs, xlog=KodiLogger.log):
        return True

    def run(self):
        if self.taskKwargs['notify'] is True:
            notify(_('Task %s launching for event: %s') % (self.taskId, str(self.topic)))
        err = False
        msg = ''
        args = ' %s' % ' '.join(self.runtimeargs)
        # noinspection PyBroadException,PyBroadException,PyBroadException
        try:
            if len(self.runtimeargs) > 0:
                result = xbmc.executebuiltin('%s, %s' % (self.taskKwargs['builtin'], args))
            else:
                result = xbmc.executebuiltin('%s' % self.taskKwargs['builtin'])
            if result is not None:
                msg = result
                if result != '':
                    err = True
        except Exception:
            e = sys.exc_info()[0]
            err = True
            if hasattr(e, 'message'):
                msg = str(e.message)
            msg = msg + '\n' + traceback.format_exc()
        self.threadReturn(err, msg)
