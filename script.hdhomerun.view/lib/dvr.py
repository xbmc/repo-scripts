# -*- coding: utf-8 -*-
import time
import xbmc, xbmcgui
import kodigui
import hdhr
import skin

import util
from util import T

class RecordDialog(kodigui.BaseDialog):
    EPISODE_LIST = 201
    RECORD_BUTTON = 203
    HIDE_BUTTON = 204

    def __init__(self,*args,**kwargs):
        kodigui.BaseDialog.__init__(self,*args,**kwargs)
        self.series = kwargs.get('series')
        self.storageServer = kwargs.get('storage_server')
        self.results = kwargs.get('results')
        self.showHide = kwargs.get('show_hide') or self.series.hidden
        self.ruleAdded = False

    def onFirstInit(self):
        self.episodeList = kodigui.ManagedControlList(self,self.EPISODE_LIST,20)
        hideText = self.series.hidden and T(32841) or T(32840)
        self.setProperty('show.hide',self.showHide and hideText or '')
        self.setProperty('hide.record',self.series.hasRule and '1' or '')
        self.setProperty('series.title',self.series.title)
        self.setProperty('synopsis.title','Synopsis')
        self.setProperty('synopsis',self.series.synopsis)
        self.fillEpisodeList()

    def onClick(self,controlID):
        if controlID == self.RECORD_BUTTON:
            self.add()
        elif controlID == self.HIDE_BUTTON:
            self.hide()

    @util.busyDialog('GETTING INFO')
    def fillEpisodeList(self):
        items = []
        for r in self.series.episodes(self.storageServer._devices.apiAuthID()):
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
            items.append(item)

        self.episodeList.addItems(items)

    def add(self):
        try:
            self.storageServer.addRule(self.series)
        except hdhr.errors.RuleModException, e:
            util.showNotification(e.message,header=T(32832))
            return

        xbmcgui.Dialog().ok(T(32800),T(32801),'',self.series.title)
        self.ruleAdded = True
        self.doClose()

    def hide(self):
        try:
            util.withBusyDialog(self.storageServer.hideSeries,'HIDING',self.series)
        except hdhr.errors.SeriesHideException, e:
            util.showNotification(e.message,header=T(32838))
            return

        self.doClose()


class EpisodesDialog(kodigui.BaseDialog):
    RECORDING_LIST_ID = 101

    def __init__(self,*args,**kwargs):
        kodigui.BaseDialog.__init__(self,*args,**kwargs)
        self.groupID = kwargs.get('group_id')
        self.storageServer = kwargs.get('storage_server')
        self.sortMode = util.getSetting('episodes.sort.mode','AIRDATE')
        self.sortASC = util.getSetting('episodes.sort.asc',True)
        self.play = None

    def onFirstInit(self):
        self.setWindowProperties()
        self.recordingList = kodigui.ManagedControlList(self,self.RECORDING_LIST_ID,10)
        self.fillRecordings()

    def onAction(self,action):
        try:
            if action == xbmcgui.ACTION_CONTEXT_MENU:
                self.doContextMenu()
            elif action.getButtonCode() in (61575, 61486):
                return self.doDelete()
        except:
            kodigui.BaseDialog.onAction(self,action)
            raise
            return

        kodigui.BaseDialog.onAction(self,action)

    def onClick(self,controlID):
        if controlID == self.RECORDING_LIST_ID:
            self.done()
        elif controlID == 301:
            self.sort('NAME')
        elif controlID == 302:
            self.sort('ORIGINAL')
        elif controlID == 303:
            self.sort('AIRDATE')

    def doContextMenu(self):
        items = [('delete', T(32809))]
        idx = xbmcgui.Dialog().select(T(32810),[i[1] for i in items])
        if idx < 0:
            return

        choice = items[idx][0]

        if choice == 'delete':
            self.doDelete()

    def doDelete(self):
        item = self.recordingList.getSelectedItem()
        if not item: return
        yes = xbmcgui.Dialog().yesno(T(32035),T(32036))
        if yes:
            self.storageServer.deleteRecording(item.dataSource)

    def setWindowProperties(self):
        self.setProperty('sort.mode',self.sortMode)
        self.setProperty('sort.asc',self.sortASC and '1' or '')

    def sort(self,key):
        if self.sortMode == key:
            self.sortASC = not self.sortASC
        else:
            self.sortASC = True

        self.sortMode = key

        util.setSetting('episodes.sort.mode',key)
        util.setSetting('episodes.sort.asc',self.sortASC)

        self.setWindowProperties()

        self.sortItems(self.recordingList)

    def sortItems(self,items):
        if self.sortMode == 'NAME':
            if self.seriesID:
                items.sort(key=lambda x: util.sortTitle(x.dataSource.episodeTitle), reverse=not self.sortASC)
            else:
                items.sort(key=lambda x: util.sortTitle(x.dataSource.seriesTitle), reverse=not self.sortASC)
        elif self.sortMode == 'ORIGINAL':
            items.sort(key=lambda x: x.dataSource.originalTimestamp, reverse=self.sortASC)
        else:
            items.sort(key=lambda x: x.dataSource.startTimestamp, reverse=self.sortASC)


    def fillRecordings(self):
        items = []
        for r in self.storageServer.recordings:
            if self.groupID and not r.displayGroupID == self.groupID: continue
            item = kodigui.ManagedListItem(r.episodeTitle,r.synopsis,thumbnailImage=r.icon,data_source=r)
            item.setProperty('series.title',r.seriesTitle)
            item.setProperty('episode.number',r.episodeNumber)
            #item.setProperty('channel.number',r.channelNumber)
            #item.setProperty('channel.name',r.channelName)
            item.setProperty('air.date',r.displayDate())
            item.setProperty('air.time',r.displayTime())
            item.setProperty('original.date',r.displayDate(original=True))
            items.append(item)

        self.sortItems(items)

        self.recordingList.reset()
        self.recordingList.addItems(items)
        self.setFocusId(self.RECORDING_LIST_ID)

    def done(self):
        self.setProperty('staring.recording','1')
        item = self.recordingList.getSelectedItem()
        self.play = item.dataSource
        self.doClose()

class DVRBase(util.CronReceiver):
    SHOW_LIST_ID = 101
    SEARCH_PANEL_ID = 201
    SEARCH_EDIT_ID = 204
    SEARCH_EDIT_BUTTON_ID = 204
    RULE_LIST_ID = 301
    WATCH_BUTTON = 103
    SEARCH_BUTTON = 203
    RULES_BUTTON = 303

    RECORDINGS_REFRESH_INTERVAL = 600
    SEARCH_REFRESH_INTERVAL = 600

    def __init__(self,*args,**kwargs):
        self._BASE.__init__(self,*args,**kwargs)
        self.main = kwargs.get('main')
        self.init()

    @property
    def mode(self):
        return util.getGlobalProperty('DVR_MODE')

    @mode.setter
    def mode(self,val):
        if util.getGlobalProperty('DVR_MODE') == 'RULES' and val != 'RULES':
            self.moveRule(None)

        util.setGlobalProperty('DVR_MODE',val)

        if val == 'SEARCH':
            if time.time() - self.lastSearchRefresh > self.SEARCH_REFRESH_INTERVAL:
                self.fillSearchPanel()

    def onFirstInit(self):
        self.start()

    @util.busyDialog('LOADING DVR')
    def init(self):
        self.started = False
        self.showList = None
        self.searchPanel = None
        self.ruleList = None
        self.searchTerms = ''
        self.play = None
        self.options = None
        self.devices = self.main.devices
        self.storageServer = hdhr.storageservers.StorageServers(self.devices)
        self.lineUp = self.main.lineUp
        self.cron = self.main.cron
        self.lastRecordingsRefresh = 0
        self.lastSearchRefresh = 0
        self.movingRule = None
        self.mode = 'WATCH'
        util.setGlobalProperty('NO_RESULTS',T(32802))
        util.setGlobalProperty('NO_RECORDINGS',T(32803))
        util.setGlobalProperty('NO_RULES',T(32804))

    def start(self):
        if self.showList:
            self.showList.reInit(self,self.SHOW_LIST_ID)
        else:
            self.showList = kodigui.ManagedControlList(self,self.SHOW_LIST_ID,5)
            self.fillShows()

        self.searchPanel = kodigui.ManagedControlList(self,self.SEARCH_PANEL_ID,6)
        self.fillSearchPanel()

        self.ruleList = kodigui.ManagedControlList(self,self.RULE_LIST_ID,10)
        self.fillRules()

        if self.showList.size():
            self.setFocusId(self.SHOW_LIST_ID)
        else:
            self.setMode('SEARCH')

        self.cron.registerReceiver(self)

    def onAction(self,action):
        try:
            if action == xbmcgui.ACTION_GESTURE_SWIPE_LEFT:
                if self.mode == 'RULES':
                    self.switchToLiveTV()
                elif self.mode == 'SEARCH':
                    return self.setMode('RULES')
                elif self.mode == 'WATCH':
                    return self.setMode('SEARCH')
            elif action == xbmcgui.ACTION_GESTURE_SWIPE_RIGHT:
                if self.mode == 'SEARCH':
                    return self.setMode('WATCH')
                elif self.mode == 'RULES':
                    return self.setMode('SEARCH')
            elif action == xbmcgui.ACTION_CONTEXT_MENU:
                if self.getFocusId() == self.RULE_LIST_ID:
                    return self.doRuleContext()
                elif self.getFocusId() == self.SEARCH_PANEL_ID:
                    return self.setFocusId(self.SEARCH_EDIT_BUTTON_ID)
            elif action == xbmcgui.ACTION_MOVE_DOWN or action == xbmcgui.ACTION_MOVE_UP or action == xbmcgui.ACTION_MOVE_RIGHT or action == xbmcgui.ACTION_MOVE_LEFT:
                if self.mode == 'WATCH':
                    if self.getFocusId() != self.SHOW_LIST_ID: self.setFocusId(self.SHOW_LIST_ID)
                elif self.mode == 'SEARCH':
                    if not xbmc.getCondVisibility('ControlGroup(550).HasFocus(0)') and self.getFocusId() != self.SEARCH_PANEL_ID:
                        #self.searchEdit.setText('')
                        self.setFocusId(self.SEARCH_EDIT_ID)
                elif self.mode == 'RULES':
                    if self.getFocusId() != self.RULE_LIST_ID:
                        if self.ruleList.size():
                            self.setFocusId(self.RULE_LIST_ID)
                    if self.movingRule and action == xbmcgui.ACTION_MOVE_DOWN or action == xbmcgui.ACTION_MOVE_UP:
                        self.moveRule(True)
            elif action == xbmcgui.ACTION_SELECT_ITEM and self.getFocusId() == self.RULE_LIST_ID:
                self.moveRule()
            elif action == xbmcgui.ACTION_PREVIOUS_MENU or action == xbmcgui.ACTION_NAV_BACK:
                util.setGlobalProperty('dvr.active','')
                self.options = True
                #self.main.showOptions(from_dvr=True)
                self.doClose()
            elif action == xbmcgui.ACTION_MOUSE_LEFT_CLICK:
                if self.getFocusId() == self.RULE_LIST_ID:
                    if 1094 < action.getAmount1() < 1251:
                        self.toggleRuleRecent()
                    elif action.getAmount1() < 1095:
                        self.moveRule()
            elif action == xbmcgui.ACTION_MOUSE_MOVE and self.getFocusId() == self.RULE_LIST_ID:
                if self.movingRule:
                    self.moveRule(True)
            elif action.getButtonCode() in (61575, 61486):
                if self.getFocusId() == self.RULE_LIST_ID:
                    return self.deleteRule()
                elif self.getFocusId() == self.SEARCH_PANEL_ID:
                    return self.removeSeries()

        except:
            self._BASE.onAction(self,action)
            raise
            return

        self._BASE.onAction(self,action)

    def onClick(self,controlID):
        #print 'click: {0}'.format(controlID)
        if controlID == self.SHOW_LIST_ID:
            self.openEpisodeDialog()
        elif controlID == self.SEARCH_PANEL_ID:
            self.openRecordDialog()
        # elif controlID == self.RULE_LIST_ID:
        #     self.toggleRuleRecent()
        elif controlID == self.WATCH_BUTTON:
            self.setMode('WATCH')
        elif controlID == self.SEARCH_BUTTON:
            if self.mode == 'SEARCH':
                self.setSearch()
            self.setMode('SEARCH')
        elif controlID == self.RULES_BUTTON:
            self.setMode('RULES')
        elif controlID == self.SEARCH_EDIT_BUTTON_ID:
            self.setSearch()
        elif 204 < controlID < 208:
            idx = controlID - 205
            self.setSearch(category=('series','movie','sport')[idx])

    def onFocus(self,controlID):
        #print 'focus: {0}'.format(controlID)
        if xbmc.getCondVisibility('ControlGroup(100).HasFocus(0)'):
            self.mode = 'WATCH'
        elif xbmc.getCondVisibility('ControlGroup(200).HasFocus(0)'):
            self.mode = 'SEARCH'
        elif xbmc.getCondVisibility('ControlGroup(300).HasFocus(0)'):
            self.mode = 'RULES'

    def tick(self):
        if time.time() - self.lastRecordingsRefresh > self.RECORDINGS_REFRESH_INTERVAL:
            self.updateRecordings()

    def setMode(self,mode):
        self.mode == mode
        if mode == 'WATCH':
            self.setFocusId(100)
        elif mode == 'SEARCH':
            self.setFocusId(200)
        elif mode == 'RULES':
            self.setFocusId(300)

    def updateRecordings(self):
        util.DEBUG_LOG('DVR: Refreshing recordings')
        self.storageServer.updateRecordings()
        self.fillShows(update=True)

    def delayedUpdateRecordings(self):
        self.lastRecordingsRefresh = (time.time() - self.RECORDINGS_REFRESH_INTERVAL) + 5

    @util.busyDialog('LOADING SHOWS')
    def fillShows(self, update=False):
        self.lastRecordingsRefresh = time.time()

        groupItems = []
        seriesItems = []
        groups = {}

        for r in self.storageServer.recordings:
            if r.displayGroupID in groups:
                item = groups[r.displayGroupID]
                ct = int(item.getProperty('show.count'))
                ct += 1
                item.setProperty('show.count',str(ct))
            else:
                item = kodigui.ManagedListItem(r.displayGroupTitle,r.seriesSynopsis,thumbnailImage=r.icon,data_source=r)
                item.setProperty('show.count','1')
                item.setProperty('groupID',r.displayGroupID)
                groups[r.displayGroupID] = item
                if r.groupIsSeries:
                    seriesItems.append(item)
                else:
                    groupItems.append(item)


        groupItems.sort(key=lambda x: util.sortTitle(x.dataSource.displayGroupTitle))
        seriesItems.sort(key=lambda x: util.sortTitle(x.dataSource.displayGroupTitle))

        items = groupItems + seriesItems

        if not items:
            util.setGlobalProperty('NO_RECORDINGS',self.storageServer.getRecordingsFailed and '[COLOR 80FF0000]{0}[/COLOR]'.format(T(32829)) or T(32803))
        else:
            util.setGlobalProperty('NO_RECORDINGS','')

        allItem = kodigui.ManagedListItem('ALL RECORDINGS', thumbnailImage='script-hdhomerun-view-dvr_all.png')
        items.insert(0,allItem)

        if update:
            self.showList.replaceItems(items)
        else:
            self.showList.reset()
            self.showList.addItems(items)

    @util.busyDialog('LOADING GUIDE')
    def fillSearchPanel(self,category='Series'):
        self.lastSearchRefresh = time.time()

        items = []

        if self.searchTerms:
            category = ''

        try:
            searchResults = hdhr.guide.search(self.devices.apiAuthID(),category=category,terms=self.searchTerms) or []
        except:
            e = util.ERROR()
            util.showNotification(e,header=T(32831))

        util.setGlobalProperty('NO_RESULTS',not searchResults and T(32802) or '')

        for r in searchResults:
            item = kodigui.ManagedListItem(r.title,r.synopsis,thumbnailImage=r.icon,data_source=r)
            item.setProperty('series.title',r.title)
            item.setProperty('channel.number',r.channelNumber)
            item.setProperty('channel.name',r.channelName)
            item.setProperty('channel.icon',r.channelIcon)
            item.setProperty('has.rule',r.hasRule and '1' or '')
            item.setProperty('hidden',r.hidden and '1' or '')
            items.append(item)

        self.searchPanel.reset()
        self.searchPanel.addItems(items)

    @util.busyDialog('LOADING RULES')
    def fillRules(self,update=False):
        if update: self.storageServer.updateRules()
        items = []
        for r in self.storageServer.rules:
            item = kodigui.ManagedListItem(r.title,data_source=r)
            item.setProperty('rule.recent_only',r.recentOnly and T(32805) or T(32806))
            items.append(item)

        if not items:
            util.setGlobalProperty('NO_RULES',self.storageServer.getRulesFailed and '[COLOR 80FF0000]{0}[/COLOR]'.format(T(32830)) or T(32804))
        else:
            util.setGlobalProperty('NO_RULES','')

        items.sort(key=lambda x: x.dataSource.priority)

        self.ruleList.reset()
        self.ruleList.addItems(items)

    def doRuleContext(self):
        options = [T(32807),T(32809)]
        idx = xbmcgui.Dialog().select(T(32810),options)
        if idx < 0: return
        try:
            if idx == 0:
                self.toggleRuleRecent()
            # elif idx == 1:
                # item = self.ruleList.getSelectedItem()
                # priority = xbmcgui.Dialog().input(T(32811),str(item.dataSource.priority))
                # try:
                #     item.dataSource.priority = int(priority)
                #     #item.setLabel2(str(item.dataSource.priority))
                # except ValueError:
                #     return
                # self.fillRules(update=True)
            elif idx == 1:
                self.deleteRule()

        except hdhr.errors.RuleModException, e:
            util.showNotification(e.message,header=T(32827))
        except hdhr.errors.RuleDelException, e:
            util.showNotification(e.message,header=T(32828))

    @util.busyDialog('UPDATING')
    def toggleRuleRecent(self):
        item = self.ruleList.getSelectedItem()
        if not item:
            return

        item.dataSource.recentOnly = not item.dataSource.recentOnly
        self.fillRules(update=True)

    def deleteRule(self):
        item = self.ruleList.getSelectedItem()
        if not item:
            return

        yes = xbmcgui.Dialog().yesno(T(32035),T(32037))
        if not yes:
            return

        util.withBusyDialog(self.storageServer.deleteRule,'DELETING',item.dataSource)
        for sitem in self.searchPanel:
            if item.dataSource.seriesID == sitem.dataSource.ID:
                sitem.setProperty('has.rule','')

        self.fillRules(update=True)

    def moveRule(self,move=False):
        if not move:
            if self.movingRule:
                util.setGlobalProperty('moving.rule','')
                self.movingRule = None
                self.updateRulePriorities()
            elif move is not None:
                item = self.ruleList.getSelectedItem()
                if not item:
                    return
                self.movingRule = item
                util.setGlobalProperty('moving.rule','1')

        else:
            if not self.movingRule: return
            pos = self.ruleList.getSelectedPosition()
            self.ruleList.moveItem(self.movingRule,pos)

    @util.busyDialog('UPDATING')
    def updateRulePriorities(self):
        for i, item in enumerate(self.ruleList):
            try:
                item.dataSource.priority = i
            except ValueError:
                util.ERROR()
                return

        self.fillRules(update=True)

    def setSearch(self,category=None):
        #self.searchTerms = self.getControl(self.SEARCH_EDIT_ID).getText() or ''
        if category:
            self.searchTerms = ''
            catDisplay = {'series':'Shows','movie':'Movies','sport':'Sports'}
            util.setGlobalProperty('search.terms',catDisplay[category])
            self.fillSearchPanel(category=category)
        else:
            self.searchTerms = xbmcgui.Dialog().input(T(32812),self.searchTerms)
            util.setGlobalProperty('search.terms',self.searchTerms)
            self.fillSearchPanel()

        if util.getGlobalProperty('NO_RESULTS'):
            self.setFocusId(202)
        else:
            self.setFocusId(201)

    def openRecordDialog(self):
        item = self.searchPanel.getSelectedItem()
        if not item: return
        path = skin.getSkinPath()
        series = item.dataSource
        d = RecordDialog(
            skin.DVR_RECORD_DIALOG,
            path,
            'Main',
            '1080i',
            series=series,
            storage_server=self.storageServer,
            show_hide=not self.searchTerms
        )

        d.doModal()

        if d.ruleAdded:
            self.fillRules(update=True)
            item.setProperty('has.rule','1')
            self.delayedUpdateRecordings()

        self.removeSeries(series)

        del d

    def openEpisodeDialog(self):
        item = self.showList.getSelectedItem()
        if not item: return
        path = skin.getSkinPath()
        groupID = item.dataSource and item.dataSource.displayGroupID or None
        d = EpisodesDialog(skin.DVR_EPISODES_DIALOG,path,'Main','1080i',group_id=groupID,storage_server=self.storageServer)
        d.doModal()
        self.play = d.play
        del d
        if self.play:
            util.setGlobalProperty('window.animations','')
            self.doClose()

    def removeSeries(self, series=None):
        if not series:
            mli = self.searchPanel.getSelectedItem()
            if not mli: return
            series = mli.dataSource
            # if not xbmcgui.Dialog().yesno(T(32035),mli.dataSource.title,'',T(32839)):
            #     return
            util.withBusyDialog(self.storageServer.hideSeries,'HIDING',series)

        for (i, mli) in enumerate(self.searchPanel):
            if mli.dataSource.ID == series.ID:
                if series.hidden:
                    self.searchPanel.removeItem(i)
                else:
                    mli.setProperty('hidden','')
                break
        #self.fillSearchPanel(update=True)

class DVRWindow(DVRBase,kodigui.BaseWindow):
    _BASE = kodigui.BaseWindow

class DVRDialog(DVRBase,kodigui.BaseDialog):
    _BASE = kodigui.BaseDialog