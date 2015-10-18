# -*- coding: utf-8 -*-
import requests
import urllib
import guide
import errors
from lib import util

MY = 'my'

HIDE_SERIES_URL = 'http://%s.hdhomerun.com/api/search_hide?DeviceAuth={deviceAuth}&SeriesID={seriesID}' % MY
SUGGEST_URL = 'http://%s.hdhomerun.com/api/suggest?DeviceAuth={deviceAuth}&Cmd={command}&SeriesID={seriesID}' % MY

RULES_URL = 'http://%s.hdhomerun.com/api/recording_rules?DeviceAuth={deviceAuth}' % 'mytest'

RULES_ADD_URL = RULES_URL + '&Cmd=add&SeriesID={seriesID}'
RULES_CHANGE_RECENT_URL = RULES_URL + '&Cmd=change&RecordingRuleID={ruleID}&RecentOnly={recentOnly}'
RULES_MOVE_URL = RULES_URL + '&Cmd=change&RecordingRuleID={ruleID}&AfterRecordingRuleID={afterRecordingRuleID}'
RULES_DELETE_URL = RULES_URL + '&Cmd=delete&RecordingRuleID={ruleID}'


class RecordingRule(dict):
    @property
    def ruleID(self):
        return self.get('RecordingRuleID')

    @property
    def ID(self):
        return self.get('SeriesID')

    @property
    def seriesID(self):
        return self.get('SeriesID')

    @property
    def title(self):
        return self.get('Title','')

    @property
    def synopsis(self):
        return self.get('Synopsis','')

    @property
    def icon(self):
        return self.get('ImageURL','')

    @property
    def originalTimestamp(self):
        return int(self.get('OriginalAirdate',0))

    @property
    def hidden(self):
        return False

    @property
    def recentOnly(self):
        return bool(self.get('RecentOnly'))

    @recentOnly.setter
    def recentOnly(self,val):
        if self.get('RecentOnly') == val: return
        self['RecentOnly'] = val and 1 or 0
        self.changeRecentOnly()

    def init(self,storage_server,add=False):
        self['STORAGE_SERVER'] = storage_server
        if add: return self.add()
        return self

    @property
    def hasRule(self):
        return True

    def episodes(self,device_auth):
        return guide.episodes(device_auth, self.seriesID)

    def modify(self, url, mtype):
        util.DEBUG_LOG('{0} rule: {1}'.format(mtype.title(), url))
        try:
            req = requests.get(url)
            util.DEBUG_LOG('{0} rule response: {1}'.format(mtype.title(), repr(req.text)))
        except:
            e = util.ERROR()
            raise errors.RuleModException(e)
        self['STORAGE_SERVER'].pingUpdateRules()

        return req.json()

    def add(self):
        url = RULES_ADD_URL.format(
            deviceAuth=urllib.quote(self['STORAGE_SERVER']._devices.apiAuthID(), ''),
            seriesID=self.seriesID,
        )

        self.modify(url, 'add')

        return self

    def changeRecentOnly(self):
        url = RULES_CHANGE_RECENT_URL.format(
            deviceAuth=urllib.quote(self['STORAGE_SERVER']._devices.apiAuthID(), ''),
            ruleID=self.ruleID,
            recentOnly=self.get('RecentOnly') or 0
        )
        self.modify(url, 'change')

        return self

    def move(self, after_rule_id):
        url = RULES_MOVE_URL.format(
            deviceAuth=urllib.quote(self['STORAGE_SERVER']._devices.apiAuthID(), ''),
            ruleID=self.ruleID,
            afterRecordingRuleID=after_rule_id
        )
        self.modify(url, 'move')

        return self

    def delete(self):
        url = RULES_DELETE_URL.format(
            deviceAuth=urllib.quote(self['STORAGE_SERVER']._devices.apiAuthID(), ''),
            ruleID=self.ruleID
        )
        self.modify(url, 'delete')

        return self

#"ChannelAffiliate":"CBS",
#"ChannelImageURL":"http://my.hdhomerun.com/fyimediaservices/v_3_3_6_1/Station.svc/2/765/Logo/120x120",
#"ChannelName":"KIRO-DT",
#"ChannelNumber":"7.1",
#"EndTime":"1428638460",
#"EpisodeNumber":"106",
#"EpisodeTitle":"Heal Thyself",
#"ImageURL":"http://my.hdhomerun.com/fyimediaservices/v_3_3_6_1/Program.svc/96/2111966/Primary",
#"OriginalAirdate":"1428537600",
#"ProgramID":"11920222",
#"SeriesID":"11920222",
#"StartTime":"1428636660",
#"Synopsis":"While at a doctor's visit, Oscar decides to pursue Felix's physician, Sharon, but winds up inadvertently kicking Felix's hypochondria into high gear.",
#"Title":"The Odd Couple",
#"PlayURL":"http://192.168.1.24:40172/play?id=1a7249c1"


class Recording(guide.Episode):
    @property
    def playURL(self):
        return self.get('PlayURL', '')

    @property
    def programID(self):
        return self.get('ProgramID')

    @property
    def seriesTitle(self):
        return self.get('Title', '')

    @property
    def seriesSynopsis(self):
        return self.get('SeriesSynopsis', '')

    @property
    def seriesID(self):
        return self.get('SeriesID')

    @property
    def episodeTitle(self):
        return self.get('EpisodeTitle', '')

    @property
    def episodeSynopsis(self):
        return self.get('Synopsis', '')

    @property
    def episodeNumber(self):
        return self.get('EpisodeNumber', '')

    @property
    def displayGroupID(self):
        return self.get('DisplayGroupID')

    @property
    def displayGroupTitle(self):
        return self.get('DisplayGroupTitle', '')

    @property
    def groupIsSeries(self):
        return self.get('DisplayGroupID') == self.get('SeriesID')

    def progress(self,sofar):
        duration = self.duration
        if not duration: return 0
        return int((sofar/float(self.duration))*100)

class StorageServers(object):
    def __init__(self,devices):
        self._devices = devices
        self._recordings = []
        self._rules = []
        self.getRecordingsFailed = False
        self.getRulesFailed = False
        self._init()

    def _init(self):
        try:
            self._getRecordings()
        except:
            self.getRecordingsFailed = True
            util.ERROR()

        try:
            self._getRules()
        except:
            self.getRulesFailed = True
            util.ERROR()

    def _getRecordings(self):
        self._recordings = []
        err = None
        for d in self._devices.storageServers:
            try:
                recs = d.recordings()
                if recs: self._recordings += [Recording(r) for r in recs]
            except:
                err = util.ERROR()

        if self._recordings:
            self.getRecordingsFailed = False
        elif err:
            self.getRecordingsFailed = True

    def _getRules(self):
        url = RULES_URL.format(deviceAuth=urllib.quote(self._devices.apiAuthID(), ''))
        util.DEBUG_LOG('Getting recording rules: {0}'.format(url))
        #req = requests.get(url,headers={'Cache-Control':'no-cache'})
        req = requests.get(url)
        data = req.json()
        if not data:
            return []
        self._rules = [RecordingRule(r).init(self) for r in data]
        self.getRulesFailed = False

    @property
    def recordings(self):
        return self._recordings

    @property
    def rules(self):
        return self._rules

    def getRecordingByPlayURL(self,play_url):
        for r in self.recordings:
            if play_url == r.playURL:
                return r

    def updateRecordings(self):
        self._getRecordings()

    def updateRules(self):
        self._getRules()

    def addRule(self,result):
        rule = RecordingRule(result).init(self,add=True)
        self._rules.append(rule)
        result['RecordingRule'] = 1
        self.pingUpdateRules()
        return rule

    def deleteRule(self,rule):
        if not rule in self._rules: return False

        self._rules.pop(self._rules.index(rule.delete()))
        return True

    def hideSeries(self,series):
        try:
            url = SUGGEST_URL.format(deviceAuth=urllib.quote(self._devices.apiAuthID(), ''),command=series.hidden and 'unhide' or 'hide',seriesID=series.ID)
            util.DEBUG_LOG('Series hide URL: {0}'.format(url))
            req = requests.get(url)

            if 'SuggestHide' in series:
                del series['SuggestHide']
            else:
                series['SuggestHide'] = 1

            util.DEBUG_LOG('Series hide response: {0}'.format(repr(req.text)))
        except:
            e = util.ERROR()
            raise errors.SeriesHideException(e)

    def deleteRecording(self,recording):
        util.LOG('delteRecording() - NOT IMPLEMENTED')

    def pingUpdateRules(self):
        for d in self._devices.storageServers:
            try:
                d.syncRules()
            except:
                util.ERROR()
