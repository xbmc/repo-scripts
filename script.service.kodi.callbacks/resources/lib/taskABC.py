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

import threading
import Queue
import abc
import re
import copy
from resources.lib.kodilogging import KodiLogger
from resources.lib.pubsub import TaskReturn
from resources.lib.events import Events
import xbmcgui

events = Events()

def notify(msg):
    dialog = xbmcgui.Dialog()
    dialog.notification('Kodi Callbacks', msg, xbmcgui.NOTIFICATION_INFO, 5000)


class AbstractTask(threading.Thread):
    """
    Abstract class for command specific workers to follow
    """
    __metaclass__ = abc.ABCMeta
    tasktype = 'abstract'
    lock = threading.RLock()

    def __init__(self, logger=KodiLogger.log, name='AbstractTask'):
        super(AbstractTask, self).__init__(name=name)
        self.cmd_str = ''
        self.userargs = ''
        self.log = logger
        self.runtimeargs = []
        self.taskKwargs = {}
        self.publisherKwargs = {}
        self.topic = None
        self.type = ''
        self.taskId = ''
        self.returnQ = Queue.Queue()
        self.delimitregex = re.compile(r'\s+,\s+|,\s+|\s+')


    def processUserargs(self, kwargs):
        if self.userargs == '':
            return []
        ret = copy.copy(self.userargs)
        ret = ret.replace(ur'%%', u'{@literal%@}')
        if self.tasktype == 'script' or self.tasktype == 'python':
            tmp = self.delimitregex.sub(ur'{@originaldelim@}', ret)
            ret = tmp
        try:
            varArgs = events.AllEvents[self.topic.topic]['varArgs']
        except KeyError:
            pass
        else:
            for key in varArgs.keys():
                try:
                    kw = unicode(kwargs[varArgs[key]])
                    kw = kw.replace(u" ", u'%__')
                    ret = ret.replace(key, kw)
                except KeyError:
                    pass
                except UnicodeError:
                    pass
        ret = ret.replace(u'%__', u" ")
        ret = ret.replace(u'%_', u",")
        ret = ret.replace(u'{@literal%@}', ur'%')
        if self.tasktype == 'script' or self.tasktype == 'python':
            ret = ret.split(u'{@originaldelim@}') # need to split first to avoid unicode error
            # if self.tasktype == 'script':
            #     fse = sys.getfilesystemencoding()
            #     ret = []
            #     for r in ret2:
            #         ret.append(r.encode(fse))
            # else:
            #     ret = ret2
        return ret

    @staticmethod
    @abc.abstractmethod
    def validate(taskKwargs, xlog=KodiLogger.log):
        pass

    def t_start(self, topic, taskKwargs, **kwargs):
        with AbstractTask.lock:
            self.topic = topic
            self.taskKwargs = taskKwargs
            self.userargs = taskKwargs['userargs']
            self.taskId = taskKwargs['taskid']
            self.publisherKwargs = kwargs
            self.runtimeargs = self.processUserargs(kwargs)
        self.start()

    @abc.abstractmethod
    def run(self):
        err = None  # True if error occured
        msg = ''    # string containing error message or return message
        self.threadReturn(err, msg)

    def threadReturn(self, err, msg):
        taskReturn = TaskReturn(err, msg)
        taskReturn.eventId = str(self.topic)
        taskReturn.taskId = self.taskId
        self.returnQ.put(taskReturn)
