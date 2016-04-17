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

    def __init__(self, logger=KodiLogger.log):
        super(AbstractTask, self).__init__(name='Worker')
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
        ret = ret.replace(r'%%', '{@literal%@}')
        if self.tasktype == 'script' or self.tasktype == 'python':
            tmp = self.delimitregex.sub(r'{@originaldelim@}', ret)
            ret = tmp
        try:
            varArgs = events.AllEvents[self.topic.topic]['varArgs']
        except KeyError:
            pass
        else:
            for key in varArgs.keys():
                try:
                    kw = str(kwargs[varArgs[key]])
                    kw = kw.replace(" ", '%__')
                    ret = ret.replace(key, kw)
                except KeyError:
                    pass
        ret = ret.replace('%__', " ")
        ret = ret.replace('%_', ",")
        ret = ret.replace('{@literal%@}', r'%')
        if self.tasktype == 'script' or self.tasktype == 'python':
            ret = ret.split('{@originaldelim@}')
            return ret
        else:
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
