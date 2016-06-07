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

import xbmcaddon
from resources.lib import taskdict
from resources.lib.events import Events
from resources.lib.events import requires_subtopic
from resources.lib.kodilogging import KodiLogger
from resources.lib.pubsub import Topic
from resources.lib.utils.kodipathtools import translatepath
from resources.lib.utils.poutil import PoDict

podict = PoDict()
podict.read_from_file(translatepath('special://addon/resources/language/English/strings.po'))


def getEnglishStringFromId(msgctxt):
    status, ret = podict.has_msgctxt(msgctxt)
    if status is True:
        return ret
    else:
        return ''


_ = getEnglishStringFromId

try:
    addonid = xbmcaddon.Addon('script.service.kodi.callbacks').getAddonInfo('id')
except RuntimeError:
    addonid = 'script.service.kodi.callbacks'
else:
    if addonid == '':
        addonid = 'script.service.kodi.callbacks'

kl = KodiLogger()
log = kl.log


def get(settingid, var_type):
    t = xbmcaddon.Addon(addonid).getSetting(settingid)
    if var_type == 'text' or var_type == 'file' or var_type == 'folder' or var_type == 'sfile' or var_type == 'sfolder' or var_type == 'labelenum':
        try:
            t = unicode(t, 'utf-8', errors='ignore')
        except UnicodeDecodeError:
            pass
        return t
    elif var_type == 'int':
        try:
            return int(t)
        except TypeError:
            log(msg='TYPE ERROR for variable %s. Expected int got "%s"' % (settingid, t))
            return 0
    elif var_type == 'bool':
        if t == 'false':
            return False
        else:
            return True
    else:
        log(msg='ERROR Could not process variable %s = "%s"' % (settingid, t))
        return None


class Settings(object):
    allevents = Events().AllEvents
    taskSuffixes = {'general': [['maxrunning', 'int'], ['maxruns', 'int'], ['refractory', 'int']],
                    }
    eventsReverseLookup = None

    def __init__(self):
        self.tasks = {}
        self.events = {}
        self.general = {}
        rl = {}
        for key in Settings.allevents.keys():
            evt = Settings.allevents[key]
            rl[evt['text']] = key
        Settings.eventsReverseLookup = rl

    def logSettings(self):
        import pprint
        settingspp = {'Tasks': self.tasks, 'Events': self.events, 'General': self.general}
        pp = pprint.PrettyPrinter(indent=2)
        msg = pp.pformat(settingspp)
        kl = KodiLogger()
        kl.log(msg=msg)

    def getSettings(self):
        self.getTaskSettings()
        self.getEventSettings()
        self.getGeneralSettings()

    def getTaskSettings(self):
        for i in xrange(1, 11):
            pid = u'T%s' % unicode(i)
            tsk = self.getTaskSetting(pid)
            if tsk is not None:
                self.tasks[pid] = tsk

    @staticmethod
    def getTaskSetting(pid):
        tsk = {}
        tasktype = get(u'%s.type' % pid, 'text')
        if tasktype == 'none':
            return None
        else:
            tsk['type'] = tasktype
            for suff in Settings.taskSuffixes['general']:
                tsk[suff[0]] = get(u'%s.%s' % (pid, suff[0]), suff[1])
            for var in taskdict[tasktype]['variables']:
                tsk[var['id']] = get(u'%s.%s' % (pid, var['id']), var['settings']['type'])
            return tsk

    def getEventSettings(self):
        for i in xrange(1, 11):
            pid = u"E%s" % unicode(i)
            evt = self.getEventSetting(pid)
            if evt is not None:
                self.events[pid] = evt

    @staticmethod
    def getEventSetting(pid):
        evt = {}
        et = get(u'%s.type' % pid, 'text')
        if et == podict.has_msgid('None')[1]:
            return
        else:
            et = _(et)
            et = Settings.eventsReverseLookup[et]
            evt['type'] = et
        tsk = get(u'%s.task' % pid, 'text')
        if tsk == u'' or tsk.lower() == u'none':
            return None
        evt['task'] = u'T%s' % int(tsk[5:])
        for ri in Settings.allevents[et]['reqInfo']:
            evt[ri[0]] = get(u'%s.%s' % (pid, ri[0]), ri[1])
        evt['userargs'] = get(u'%s.userargs' % pid, 'text')
        return evt

    @staticmethod
    def getTestEventSettings(taskId):
        evt = {'type': 'onTest', 'task': taskId}
        for oa in Settings.allevents['onTest']['optArgs']:
            evt[oa] = True
        evt['eventId'] = True
        evt['taskId'] = True
        return evt

    def getGeneralSettings(self):
        polls = ['LoopFreq', 'LogFreq', 'TaskFreq']
        self.general['Notify'] = get('Notify', 'bool')
        for p in polls:
            self.general[p] = get(p, 'int')
        self.general['elevate_loglevel'] = get('loglevel', 'bool')

    def getOpenwindowids(self):
        ret = {}
        for evtkey in self.events.keys():
            evt = self.events[evtkey]
            if evt['type'] == 'onWindowOpen':
                ret[evt['windowIdO']] = evtkey
        return ret

    def getClosewindowids(self):
        ret = {}
        for evtkey in self.events.keys():
            evt = self.events[evtkey]
            if evt['type'] == 'onWindowClose':
                ret[evt['windowIdC']] = evtkey
        return ret

    def getEventsByType(self, eventType):
        ret = []
        for key in self.events.keys():
            evt = self.events[key]
            if evt['type'] == eventType:
                evt['key'] = key
                ret.append(evt)
        return ret

    def getIdleTimes(self):
        idleEvts = self.getEventsByType('onIdle')
        ret = {}
        for evt in idleEvts:
            ret[evt['key']] = int(evt['idleTime'])
        return ret

    def getAfterIdleTimes(self):
        idleEvts = self.getEventsByType('afterIdle')
        ret = {}
        for evt in idleEvts:
            ret[evt['key']] = int(evt['afterIdleTime'])
        return ret

    def getJsonNotifications(self):
        jsonEvts = self.getEventsByType('onNotification')
        ret = []
        dic = {}
        for evt in jsonEvts:
            dic['eventId'] = evt['key']
            dic['sender'] = evt['reqInfo']['sender']
            dic['method'] = evt['regInfo']['method']
            dic['data'] = evt['reqInfo']['data']
            ret.append(dic)
        return ret

    def getLogSimples(self):
        evts = self.getEventsByType('onLogSimple')
        ret = []
        for evt in evts:
            ret.append({'matchIf': evt['matchIf'], 'rejectIf': evt['rejectIf'], 'eventId': evt['key']})
        return ret

    def getLogRegexes(self):
        evts = self.getEventsByType('onLogRegex')
        ret = []
        for evt in evts:
            ret.append({'matchIf': evt['matchIf'], 'rejectIf': evt['rejectIf'], 'eventId': evt['key']})
        return ret

    def getWatchdogSettings(self):
        evts = self.getEventsByType('onFileSystemChange')
        return evts

    def getWatchdogStartupSettings(self):
        evts = self.getEventsByType('onStartupFileChanges')
        return evts

    def topicFromSettingsEvent(self, key):
        top = self.events[key]['type']
        if top in requires_subtopic():
            return Topic(top, key)
        else:
            return Topic(top)
