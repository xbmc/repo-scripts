# -*- coding: utf-8 -*-
import requests
import urllib
import time
import guide
import errors
from lib import util

MY = 'my'

HIDE_SERIES_URL = 'http://%s.hdhomerun.com/api/search_hide?DeviceAuth={deviceAuth}&SeriesID={seriesID}' % MY
SUGGEST_URL = 'http://%s.hdhomerun.com/api/suggest?DeviceAuth={deviceAuth}&Cmd={command}&SeriesID={seriesID}' % MY

RULES_URL = 'http://%s.hdhomerun.com/api/recording_rules?DeviceAuth={deviceAuth}' % 'mytest'

RULES_ADD_URL = RULES_URL + '&Cmd=add&SeriesID={seriesID}'
RULES_ADD_TEAM_URL = RULES_URL + '&Cmd=add&TeamOnly={team}'
RULES_CHANGE_RECENT_URL = RULES_URL + '&Cmd=change&RecordingRuleID={ruleID}&RecentOnly={recentOnly}'
RULES_MOVE_URL = RULES_URL + '&Cmd=change&RecordingRuleID={ruleID}&AfterRecordingRuleID={afterRecordingRuleID}'
RULES_DELETE_URL = RULES_URL + '&Cmd=delete&RecordingRuleID={ruleID}'
RULES_DELETE_DATETIME_URL = RULES_URL + '&Cmd=delete&SeriesID={seriesID}&DateTimeOnly={timestamp}'
RULES_CHANGE_URL = RULES_URL + '&Cmd=change&RecordingRuleID={ruleID}&'


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
    def dateTimeOnly(self):
        return self.get('DateTimeOnly')

    @property
    def teamOnly(self):
        return self.get('TeamOnly')

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
    def startPadding(self):
        return self.get('StartPadding') or 0

    @startPadding.setter
    def startPadding(self, val):
        if self.get('StartPadding') == val:
            return

        self['StartPadding'] = val
        self.change(StartPadding=val)

    @property
    def endPadding(self):
        return self.get('EndPadding') or 0

    @endPadding.setter
    def endPadding(self, val):
        if self.get('EndPadding') == val:
            return

        self['EndPadding'] = val
        self.change(EndPadding=val)

    @property
    def hidden(self):
        return False

    @property
    def filter(self): # Dummy to match guide.Series
        return None

    @property
    def recentOnly(self):
        return bool(self.get('RecentOnly'))

    @recentOnly.setter
    def recentOnly(self,val):
        if self.get('RecentOnly') == val: return
        self['RecentOnly'] = val and 1 or 0
        self.changeRecentOnly()

    def init(self,storage_server):
        self['STORAGE_SERVER'] = storage_server
        return self

    @property
    def hasRule(self):
        return True

    def displayDateDTO(self):
        return time.strftime('%b %d, %Y',time.localtime(self.dateTimeOnly))

    def displayTimeDTO(self):
        return time.strftime('%I:%M %p',time.localtime(self.dateTimeOnly))

    def episodes(self,device_auth):
        return guide.episodes(device_auth, self.seriesID)

    @classmethod
    def _modify(self, url, mtype):
        util.DEBUG_LOG('{0} rule: {1}'.format(mtype.title(), url))
        try:
            req = requests.get(url)
            util.DEBUG_LOG('{0} rule response: {1}'.format(mtype.title(), repr(req.text)))
        except:
            e = util.ERROR()
            raise errors.RuleModException(e)

        return req.json()

    def modify(self, url, mtype):
        json = self._modify(url, mtype)

        self['STORAGE_SERVER'].pingUpdateRules()

        return json

    def modifyAndUpdate(self, url, mtype):
        try:
            new = self.modify(url, mtype)[-1]
        except:
            new = None
            util.ERROR()

        if new:
            self.update(new)

        return self

    def add(self, **kwargs):
        url = RULES_ADD_URL.format(
            deviceAuth=urllib.quote(self['STORAGE_SERVER']._devices.apiAuthID(), ''),
            seriesID=self.seriesID,
        )

        if kwargs:
            url += '&' + urllib.urlencode(kwargs)

        self.modifyAndUpdate(url, 'add')
        return None

    def change(self, **kwargs):
        url = RULES_CHANGE_URL.format(
            deviceAuth=urllib.quote(self['STORAGE_SERVER']._devices.apiAuthID(), ''),
            ruleID=self.ruleID
        )

        url += '&' + urllib.urlencode(kwargs)

        self.modify(url, 'add')

        return self

    def changeRecentOnly(self):
        url = RULES_CHANGE_RECENT_URL.format(
            deviceAuth=urllib.quote(self['STORAGE_SERVER']._devices.apiAuthID(), ''),
            ruleID=self.ruleID,
            recentOnly=self.get('RecentOnly') or 0
        )

        return self.modifyAndUpdate(url, 'change')

    def move(self, after_rule_id):
        url = RULES_MOVE_URL.format(
            deviceAuth=urllib.quote(self['STORAGE_SERVER']._devices.apiAuthID(), ''),
            ruleID=self.ruleID,
            afterRecordingRuleID=after_rule_id
        )

        return self.modifyAndUpdate(url, 'add')

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

    @property
    def cmdURL(self):
        return self.get('CmdURL', '')


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

    def getSeriesRule(self, series_id):
        url = RULES_URL.format(deviceAuth=urllib.quote(self._devices.apiAuthID(), '')) + '&SeriesID={0}'.format(series_id)
        util.DEBUG_LOG('Get series rule URL: {0}'.format(url))
        req = requests.get(url)
        util.DEBUG_LOG('Get series rule response: {0}'.format(repr(req.text)))
        data = req.json()
        if not data:
            return None

        for r in data:
            if not 'DateTimeOnly' in r and not 'TeamOnly' in r:
                return RecordingRule(r).init(self)

        return None

    def getEpisodeDateTimeRule(self, ep, series):
        for rule in self._rules:
            if not rule.dateTimeOnly:
                continue

            if series.ID == rule.seriesID and ep.startTimestamp == rule.dateTimeOnly:
                return rule

        return None

    def getEpisodeTeamRules(self, ep, series):
        rules = []

        if not ep.hasTeams:
            return []

        for rule in self._rules:
            if not rule.teamOnly:
                continue

            if series.ID == rule.seriesID and rule.teamOnly in ep.teams:
                rules.append(rule)

        return rules

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

    def addRule(self, result=None, episode=None, team=None, **kwargs):
        if episode:
            kwargs['DateTimeOnly'] = episode.startTimestamp
        elif team:
            kwargs['TeamOnly'] = team

        RecordingRule(result).init(self).add(**kwargs)
        self.updateRules()

        try:
            if episode:
                episode['RecordingRule'] = 1
            elif not team:
                result['RecordingRule'] = 1
        finally:
            self.pingUpdateRules()


    def addTeamRule(self, team, **kwargs):
        url = RULES_ADD_TEAM_URL.format(
            deviceAuth=urllib.quote(self._devices.apiAuthID(), ''),
            team=team
        )

        if kwargs:
            url += '&' + urllib.urlencode(kwargs)

        util.DEBUG_LOG('Team rule add URL: {0}'.format(url))

        resp = RecordingRule._modify(url, 'add')

        util.DEBUG_LOG('Team rule add response: {0}'.format(repr(resp)))

    def deleteRule(self, rule, ep=None):
        if ep:
            url = RULES_DELETE_DATETIME_URL.format(deviceAuth=urllib.quote(self._devices.apiAuthID(), ''), seriesID=rule.ID, timestamp=ep.startTimestamp)
            util.DEBUG_LOG('Delete episode rule URL: {0}'.format(url))
            try:
                req = requests.get(url)
                if 'RecordingRule' in ep:
                    del ep['RecordingRule']
                util.DEBUG_LOG('Episode rule delete response: {0}'.format(repr(req.text)))
            except:
                e = util.ERROR()
                raise errors.RuleDelException(e)
            self.updateRules()
            return

        self._removeRule(rule.ID)
        rule.delete()
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

    def deleteRecording(self, recording, rerecord=False):
        try:
            url = recording.cmdURL + '&cmd=delete' + (rerecord and '&rerecord=1' or '')
            util.DEBUG_LOG('Delete recording URL: {0}'.format(url))
            req = requests.get(url)
            util.DEBUG_LOG('Delete recording response: {0}'.format(repr(req.text)))
            self.updateRecordings()
            return True
        except:
            e = util.ERROR()
            raise errors.RecordingDelException(e)

    def getRuleById(self, ruleID):
        for rule in self._rules:
            if rule.ID == ruleID:
                return rule
        return None

    def _removeRule(self, ruleID):
        rule = self.getRuleById(ruleID)
        if not rule:
            util.DEBUG_LOG('StorageServers: Attempted to remove rule not in list')
            return
        self._rules.pop(self._rules.index(rule))

    def pingUpdateRules(self):
        for d in self._devices.storageServers:
            try:
                d.syncRules()
            except:
                util.ERROR()
