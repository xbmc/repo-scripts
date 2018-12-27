import re

import xbmc
import xbmcgui
import kodigui
import hdhr

import util
from util import T

class RecordDialog(kodigui.BaseDialog):
    EPISODE_LIST = 201
    RECORD_BUTTON = 203
    HIDE_BUTTON = 204
    RECENT_BUTTON = 205
    PRIORITY_BUTTON = 206
    DELETE_BUTTON = 207
    WATCH_BUTTON = 208

    START_BUTTON = 215
    END_BUTTON = 216

    PADDING_OPTIONS = (('None', 0), ('Custom',-1), ('30s', 30), ('1m', 60), ('5m', 300), ('15m', 900), ('30m', 1800), ('1h', 3600))

    def __init__(self,*args,**kwargs):
        kodigui.BaseDialog.__init__(self,*args,**kwargs)
        self.parent = kwargs.get('parent')
        self.series = kwargs.get('series')
        self.episode = kwargs.get('episode')
        self.episodes = []
        self.rule = kwargs.get('rule')
        self.storageServer = kwargs.get('storage_server')
        self.results = kwargs.get('results')
        self.showHide = kwargs.get('show_hide')
        self.dialogSource = kwargs.get('source')
        self.ruleAdded = False
        self.setPriority = False
        self.onNow = None
        self.startPadding = 30
        self.endPadding = 30
        # self.teams = []

    def onFirstInit(self):
        self.episodeList = kodigui.ManagedControlList(self,self.EPISODE_LIST,20)
        self.showHideButton()
        self.setProperty('show.hasRule',self.rule and '1' or '')
        if self.rule:
            self.setProperty('record.always', self.rule.recentOnly and 'RECENT' or 'ALWAYS')
        else:
            self.setProperty('record.always',(hasattr(self.series, 'recentOnly') and self.series.recentOnly) and 'RECENT' or 'ALWAYS')
        self.setProperty('series.title',self.series.title)
        self.setProperty('synopsis.title','Synopsis')
        self.setProperty('synopsis',self.series.synopsis)
        if self.series and self.series.filter:
            self.setProperty('is.movie', 'Movies' in self.series.filter and '1' or '')
        self.updatePadding()

        focusEpisode = self.fillEpisodeList()

        if focusEpisode:
            self.setFocusId(self.EPISODE_LIST)
        elif self.onNow:
            self.setProperty('show.watch', '1')
            xbmc.sleep(100)
            self.setFocusId(self.WATCH_BUTTON)
        elif self.rule:
            self.setFocusId(self.PRIORITY_BUTTON)
        else:
            self.setFocusId(self.RECORD_BUTTON)

    def onClick(self,controlID):
        if controlID == self.RECORD_BUTTON:
            self.add()
        elif controlID == self.HIDE_BUTTON:
            self.hide()
        elif controlID == self.RECENT_BUTTON:
            self.toggleRuleRecent()
        elif controlID == self.PRIORITY_BUTTON:
            self.doSetPriority()
        elif controlID == self.DELETE_BUTTON:
            self.deleteRule()
        elif controlID == self.WATCH_BUTTON:
            self.watch()
        elif controlID == self.START_BUTTON:
            self.setStart()
        elif controlID == self.END_BUTTON:
            self.setEnd()
        # elif controlID == self.TEAMS_BUTTON:
        #     self.showTeams()
        elif controlID == self.EPISODE_LIST:
            self.recordEpisode()

    @util.busyDialog('GETTING INFO')
    def fillEpisodeList(self):
        items = []
        #teams = {}
        select = None
        self.episodes = []
        for i, r in enumerate(self.series.episodes(self.storageServer._devices.apiAuthID())):
            self.episodes.append(r)
            if self.episode and self.episode == r:
                select = i
            item = kodigui.ManagedListItem(r.title,r.synopsis,thumbnailImage=r.icon,data_source=r)
            item.setProperty('series.title',self.series.title)
            item.setProperty('episode.title',r.title)
            item.setProperty('episode.synopsis',r.synopsis)
            item.setProperty('episode.number',r.number)
            item.setProperty('channel.number',r.channelNumber)
            item.setProperty('channel.name',r.channelName)
            item.setProperty('air.date',r.displayDate())
            item.setProperty('air.time',r.displayTime())
            item.setProperty('original.date',r.displayDate(original=True))
            item.setProperty('original.time',r.displayTime(original=True))
            item.setProperty('has.rule',r.hasRule and '1' or '')
            # if r.hasTeams:
            #     for t in r.teams:
            #         teams[t] = 1
            items.append(item)
            self.onNow = self.onNow or r.onNow() and r or None

        self.episodeList.reset()
        self.episodeList.addItems(items)

        # if teams:
        #     self.setProperty('has.teams', '1')
        #     self.teams = sorted(teams.keys())

        if select is not None:
            self.episodeList.selectItem(select)
            return True

        self.episode = None

        return False

    def showHideButton(self, show=True):
        if self.series.hidden:
            show = True
        elif self.series.hasRule:
            show = False
        else:
            show = self.showHide

        if show:
            hideText = self.series.hidden and T(32841) or T(32840)
            self.setProperty('show.hide',hideText)
        else:
            self.setProperty('show.hide','')

    def updatePadding(self):
        if self.rule:
            self.setStart(self.rule.startPadding)
            self.setEnd(self.rule.endPadding)

    def add(self, episode=None, team=None):
        try:
            self.storageServer.addRule(self.series, episode=episode, team=team, StartPadding=self.startPadding, EndPadding=self.endPadding)
            if self.series:
                if not episode and not team:
                    self.rule = self.storageServer.getSeriesRule(self.series.ID) or self.rule
                    self.ruleAdded = True
        except hdhr.errors.RuleModException as e:
            util.showNotification(e.message,header=T(32832))
            return

        if self.parent:
            self.parent.fillRules(update=True)
            self.parent.delayedUpdateRecordings()
        # else:
        #     self.series['RecordingRule'] = 1

        xbmcgui.Dialog().ok(T(32800),T(32801),'',self.series.title)

        if self.rule:
            self.setProperty('show.hasRule', '1')

        if not episode:
            self.fillEpisodeList()

        self.series['RecordingRule'] = any([e.hasRule for e in self.episodes])

        self.showHideButton()


    def hide(self):
        try:
            util.withBusyDialog(self.storageServer.hideSeries,'HIDING',self.series)
        except hdhr.errors.SeriesHideException as e:
            util.showNotification(e.message,header=T(32838))
            return

        self.doClose()

    @util.busyDialog('UPDATING')
    def toggleRuleRecent(self):
        if not self.rule:
            util.LOG('RecordDialog.toggleRuleRecent(): No rule to modify')
            return

        self.rule.recentOnly = not self.rule.recentOnly
        self.setProperty('record.always',self.rule.recentOnly and 'RECENT' or 'ALWAYS')

        if self.parent:
            self.parent.fillRules(update=True)

        self.fillEpisodeList()

    def doSetPriority(self):
        self.setPriority = True
        self.doClose()

    def deleteRule(self, ep=None):
        if not self.rule and not ep:
            util.LOG('RecordDialog.deleteRule(): No rule to modify')
            return

        if self.parent:
            if ep:
                self.parent.deleteRule(self.series, ep=ep)
            else:
                self.parent.deleteRule(self.rule)
        else:
            if ep:
                self.storageServer.deleteRule(self.series, ep=ep)
            else:
                self.storageServer.deleteRule(self.rule)
                self.series['RecordingRule'] = 0

        if not ep:
            self.setProperty('show.hasRule', '')
            self.fillEpisodeList()

        self.series['RecordingRule'] = any([e.hasRule for e in self.episodes])
        self.showHideButton()

        if self.dialogSource == 'RULES':
            self.doClose()

    def watch(self):
        if not self.parent:
            return

        self.parent.playShow(self.onNow)
        self.doClose()

    def setStart(self, value=None):
        if value == None:
            choice = self.getPaddingOption()
            if not choice:
                return
            label = choice[0]
            self.startPadding = choice[1]
            if self.rule:
                self.rule.startPadding = choice[1]
        else:
            label = value and util.durationToShortText(value) or self.PADDING_OPTIONS[0][0]
            self.startPadding = value


        self.getControl(self.START_BUTTON).setLabel(label)

    def setEnd(self, value=None):
        if value == None:
            choice = self.getPaddingOption()
            if not choice:
                return
            label = choice[0]
            self.endPadding = choice[1]
            if self.rule:
                self.rule.endPadding = choice[1]
        else:
            label = value and util.durationToShortText(value) or self.PADDING_OPTIONS[0][0]
            self.endPadding = value

        self.getControl(self.END_BUTTON).setLabel(label)

    def recordEpisode(self):
        item = self.episodeList.getSelectedItem()
        ep = item.dataSource
        if ep.hasRule:
            rule = self.storageServer.getEpisodeDateTimeRule(ep, self.series)
            if not rule:
                return self.deleteTeamRules(ep)

            delete = xbmcgui.Dialog().yesno(
                'Delete',
                u'Delete record task: {0}'.format(ep.title or self.series.title),
                'scheduled at {0} on {1}'.format(ep.displayTime(), ep.displayDate()),
                '',
                'Cancel',
                'Delete'
            )
            if delete:
                self.deleteRule(ep)
            else:
                return
        else:
            if ep.hasTeams:
                options = [(True, 'Only this game')]
                options += [(t, u'{0} games'.format(t)) for t in ep.teams]
                idx = xbmcgui.Dialog().select('Record?', [o[1] for o in options])
                if idx < 0:
                    return

                choice = options[idx][0]

                if choice is True:
                    self.add(ep)
                else:
                    self.add(team=choice)
                    return
            else:
                record = xbmcgui.Dialog().yesno(
                    'Record',
                    u'Record {0}'.format(ep.title or self.series.title),
                    'at {0} on {1}'.format(ep.displayTime(), ep.displayDate()),
                    '',
                    'Cancel',
                    'Record'
                )
                if record:
                    self.add(ep)
                else:
                    return

        item.setProperty('has.rule', ep.hasRule and '1' or '')

    def deleteTeamRules(self, ep):
        rules = self.storageServer.getEpisodeTeamRules(ep, self.series)
        if not rules:
            return

        options = [(r, u'Delete: {1} - only {0} games'.format(self.series.title, r.teamOnly)) for r in rules]
        idx = xbmcgui.Dialog().select('Delete task?', [o[1] for o in options])
        if idx < 0:
            return

        choice = options[idx][0]
        self.storageServer.deleteRule(choice)

        self.episode = ep
        self.fillEpisodeList()

        self.series['RecordingRule'] = any([e.hasRule for e in self.episodes])

    def showTeams(self):
        idx = xbmcgui.Dialog().select('Record Team', self.teams)
        if idx < 0:
            return

        team = self.teams[idx]

        self.add(team=team)

    def getPaddingOption(self):
        idx = xbmcgui.Dialog().select('Padding', [x[0] for x in self.PADDING_OPTIONS])
        if idx < 0:
            return None
        result = self.PADDING_OPTIONS[idx]
        if result[1] < 0:
            return self.getCustomPadding()
        else:
            return result

    def getCustomPadding(self):
        padString = xbmcgui.Dialog().input(
            'Enter padding (ex: "4m5s", "4m", "35s")'
        )
        if not padString:
            return None

        match = re.search('(\d+)m\s*(\d+)s', padString) or re.search('(\d+)m()', padString) or re.search('()(\d+)s', padString)

        if match:
            try:
                minutes = int(match.group(1)) * 60
            except ValueError:
                minutes = 0

            try:
                seconds = int(match.group(2))
            except ValueError:
                seconds = 0

            seconds += minutes
        else:
            try:
                seconds = int(padString)
            except ValueError:
                seconds = 0


        if seconds:
            return (util.durationToMinuteText(seconds), seconds)

        return None


