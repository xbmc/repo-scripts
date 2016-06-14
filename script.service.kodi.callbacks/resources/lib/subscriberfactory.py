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

from resources.lib import taskdict
from resources.lib.pubsub import TaskManager, Subscriber, TaskReturn
from resources.lib.kodilogging import KodiLogger
from resources.lib.utils.poutil import KodiPo
kl = KodiLogger()
log = kl.log
kodipo = KodiPo()
_ = kodipo.getLocalizedString

def returnHandler(taskReturn):
    assert isinstance(taskReturn, TaskReturn)
    if taskReturn.iserror is False:
        msg = _(u'Command for Task %s, Event %s completed succesfully!') % (taskReturn.taskId, taskReturn.eventId)
        if taskReturn.msg.strip() != '':
            msg += _(u'\nThe following message was returned: %s') % taskReturn.msg
        log(msg=msg)
    else:
        msg = _(u'ERROR encountered for Task %s, Event %s\nERROR mesage: %s') % (
            taskReturn.taskId, taskReturn.eventId, taskReturn.msg)
        log(loglevel=kl.LOGERROR, msg=msg)


class SubscriberFactory(object):

    def __init__(self, settings, logger):
        self.settings = settings
        self.topics = []
        self.logger = logger

    def createSubscribers(self, retHandler=returnHandler):
        subscribers = []
        for key in self.settings.events.keys():
            subscriber = self.createSubscriber(key, retHandler)
            if subscriber is not None:
                subscribers.append(subscriber)
        return subscribers

    def createSubscriber(self, eventkey, retHandler=returnHandler):
        task_key = self.settings.events[eventkey]['task']
        evtsettings = self.settings.events[eventkey]
        topic = self.settings.topicFromSettingsEvent(eventkey)
        self.topics.append(topic.topic)
        task = self.createTask(task_key)
        if task is not None:
            tm = TaskManager(task, taskid=evtsettings['task'], userargs=evtsettings['userargs'],
                                         **self.settings.tasks[task_key])
            tm.returnHandler = retHandler
            tm.taskKwargs['notify'] = self.settings.general['Notify']
            subscriber = Subscriber(logger=self.logger)
            subscriber.addTaskManager(tm)
            subscriber.addTopic(topic)
            self.logger.log(msg=_('Subscriber for event: %s, task: %s created') % (str(topic), task_key))
            return subscriber
        else:
            self.logger.log(loglevel=self.logger.LOGERROR,
                msg=_('Subscriber for event: %s, task: %s NOT created due to errors') % (str(topic), task_key))
            return None

    def createTask(self, taskkey):
        tasksettings = self.settings.tasks[taskkey]
        mytask = taskdict[tasksettings['type']]['class']
        if mytask.validate(tasksettings, xlog=self.logger.log) is True:
            return mytask
        else:
            return None

