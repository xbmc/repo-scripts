# -*- coding: utf-8 -*-
import time, threading
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
    RECENT_BUTTON = 205
    PRIORITY_BUTTON = 206
    DELETE_BUTTON = 207
    WATCH_BUTTON = 208

    def __init__(self,*args,**kwargs):
        kodigui.BaseDialog.__init__(self,*args,**kwargs)
        self.parent = kwargs.get('parent')
        self.series = kwargs.get('series')
        self.rule = kwargs.get('rule')
        self.storageServer = kwargs.get('storage_server')
        self.results = kwargs.get('results')
        self.showHide = (kwargs.get('show_hide') or self.series.hidden) and not self.series.hasRule
        self.ruleAdded = False
        self.setPriority = False
        self.onNow = None

    def onFirstInit(self):
        self.episodeList = kodigui.ManagedControlList(self,self.EPISODE_LIST,20)
        self.showHideButton(self.showHide)
        self.setProperty('show.hasRule',self.series.hasRule and '1' or '')
        self.setProperty('record.always',(hasattr(self.series, 'recentOnly') and self.series.recentOnly) and 'RECENT' or 'ALWAYS')
        self.setProperty('series.title',self.series.title)
        self.setProperty('synopsis.title','Synopsis')
        self.setProperty('synopsis',self.series.synopsis)
        self.fillEpisodeList()

        if self.onNow:
            self.setProperty('show.watch', '1')
            xbmc.sleep(100)
            self.setFocusId(self.WATCH_BUTTON)
        elif self.series.hasRule:
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
            self.onNow = self.onNow or r.onNow() and r or None

        self.episodeList.addItems(items)

    def showHideButton(self, show=True):
        self.showHide = show
        if show:
            hideText = self.series.hidden and T(32841) or T(32840)
            self.setProperty('show.hide',hideText)
        else:
            self.setProperty('show.hide','')

    def add(self):
        try:
            self.rule = self.storageServer.addRule(self.series)
        except hdhr.errors.RuleModException, e:
            util.showNotification(e.message,header=T(32832))
            return

        self.ruleAdded = True
        self.parent.fillRules(update=True)
        self.parent.delayedUpdateRecordings()

        xbmcgui.Dialog().ok(T(32800),T(32801),'',self.series.title)

        self.setProperty('show.hasRule', '1')
        self.showHideButton(False)

    def hide(self):
        try:
            util.withBusyDialog(self.storageServer.hideSeries,'HIDING',self.series)
        except hdhr.errors.SeriesHideException, e:
            util.showNotification(e.message,header=T(32838))
            return

        self.doClose()

    @util.busyDialog('UPDATING')
    def toggleRuleRecent(self):
        if not self.rule:
            util.LOG('RecordDialog.toggleRuleRecent(): No rule to modify')

        self.rule.recentOnly = not self.rule.recentOnly
        self.setProperty('record.always',self.rule.recentOnly and 'RECENT' or 'ALWAYS')

        if self.parent:
            self.parent.fillRules(update=True)

    def doSetPriority(self):
        self.setPriority = True
        self.doClose()

    def deleteRule(self):
        if not self.rule:
            util.LOG('RecordDialog.deleteRule(): No rule to modify')
            return
        self.parent.deleteRule(self.rule)
        self.setProperty('show.hasRule', '')

        self.showHideButton()

    def watch(self):
        self.parent.playShow(self.onNow)
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
        return
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

class ActionHandler(object):
    def __init__(self,callback):
        self.callback = callback
        self.event = threading.Event()
        self.event.clear()
        self.timer = None
        self.delay = 0.005

    def onAction(self,action):
        if self.timer: self.timer.cancel()
        if self.event.isSet(): return
        self.timer = threading.Timer(self.delay,self.doAction,args=[action])
        self.timer.start()

    def doAction(self,action):
        self.event.set()
        try:
            self.callback(action)
        finally:
            self.event.clear()

    def clear(self):
        if self.timer: self.timer.cancel()
        return self.event.isSet()

class DVRBase(util.CronReceiver):
    SHOW_LIST_ID = 101
    SEARCH_PANEL_ID = 201

    NOW_SHOWING_PANEL1_ID = 271
    NOW_SHOWING_PANEL1_DOWN_BUTTON_ID = 281
    NOW_SHOWING_PANEL1_UP_BUTTON_ID = 283
    NOW_SHOWING_PANEL2_ID = 272
    NOW_SHOWING_PANEL2_DOWN_BUTTON_ID = 282
    NOW_SHOWING_PANEL2_UP_BUTTON_ID = 284

    SEARCH_EDIT_ID = 204
    SEARCH_EDIT_BUTTON_ID = 204
    RULE_LIST_ID = 301
    WATCH_BUTTON = 103
    SEARCH_BUTTON = 203
    RULES_BUTTON = 303

    RECORDINGS_REFRESH_INTERVAL = 600
    SEARCH_REFRESH_INTERVAL = 3600
    RULES_REFRESH_INTERVAL = 3660

    def __init__(self,*args,**kwargs):
        self._BASE.__init__(self,*args,**kwargs)
        self.main = kwargs.get('main')
        self.actionHandler = ActionHandler(self.checkMouseWheel)
        self.init()

    @property
    def mode(self):
        return util.getGlobalProperty('DVR_MODE')

    @mode.setter
    def mode(self,val):
        if util.getGlobalProperty('DVR_MODE') == 'RULES' and val != 'RULES':
            self.moveRule(None)

        util.setGlobalProperty('DVR_MODE',val)

    def onFirstInit(self):
        self.start()

    @util.busyDialog('LOADING DVR')
    def init(self):
        self.started = False
        self.showList = None
        self.searchPanel = None
        self.ruleList = None
        self.searchTerms = ''
        self.category = 'series'
        self.play = None
        self.options = None
        self.devices = self.main.devices
        self.storageServer = hdhr.storageservers.StorageServers(self.devices)
        self.lineUp = self.main.lineUp
        self.cron = self.main.cron
        self.lastRecordingsRefresh = 0
        self.lastSearchRefresh = 0
        self.lastRulesRefresh = 0
        self.nowShowing = None
        self.nowShowingHalfHour = None
        self.nsPanel2 = False
        self.nowShowingPanel1LastItem = None
        self.nowShowingPanel2LastItem = None
        self.wheelIgnore = False
        self.movingRule = None
        self.mode = 'WATCH'
        util.setGlobalProperty('now.showing','')
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

        self.nowShowingPanel1 = kodigui.ManagedControlList(self,self.NOW_SHOWING_PANEL1_ID,6)
        self.nowShowingPanel2 = kodigui.ManagedControlList(self,self.NOW_SHOWING_PANEL2_ID,6)

        self.ruleList = kodigui.ManagedControlList(self,self.RULE_LIST_ID,10)
        self.fillRules()

        if self.showList.size():
            self.setFocusId(self.SHOW_LIST_ID)
        else:
            self.setMode('SEARCH')

        self.cron.registerReceiver(self)

    def onAction(self,action):
        try:
            if action == xbmcgui.ACTION_PREVIOUS_MENU or action == xbmcgui.ACTION_NAV_BACK:
                util.setGlobalProperty('dvr.active','')
                self.moveRule(None)
                self.options = True
                #self.main.showOptions(from_dvr=True)
                self.doClose()
            elif self.mode == 'SEARCH':
                return self.onActionSearch(action)
            elif self.mode == 'WATCH':
                return self.onActionWatch(action)
            elif self.mode == 'RULES':
                return self.onActionRules(action)
        except:
            self._BASE.onAction(self,action)
            util.ERROR()
            return

        self._BASE.onAction(self,action)

    def onActionSearch(self, action):
        if action == xbmcgui.ACTION_GESTURE_SWIPE_LEFT:
            return self.setMode('RULES')
        elif action == xbmcgui.ACTION_GESTURE_SWIPE_RIGHT:
            return self.setMode('WATCH')
        elif action == xbmcgui.ACTION_CONTEXT_MENU:
            if xbmc.getCondVisibility('ControlGroup(551).HasFocus(0) | Control.HasFocus(201)'):
                return self.setFocusId(self.SEARCH_EDIT_BUTTON_ID)
        elif action == xbmcgui.ACTION_MOVE_DOWN or action == xbmcgui.ACTION_MOVE_UP or action == xbmcgui.ACTION_MOVE_RIGHT or action == xbmcgui.ACTION_MOVE_LEFT:
            if not xbmc.getCondVisibility('ControlGroup(550).HasFocus(0) | ControlGroup(551).HasFocus(0) | ControlGroup(552).HasFocus(0) | Control.HasFocus(201)'):
                return self.setFocusId(self.SEARCH_EDIT_ID)
        elif action in (xbmcgui.ACTION_MOUSE_WHEEL_DOWN, xbmcgui.ACTION_MOUSE_WHEEL_UP):
            return self.checkMouseWheelInitial(action)
        elif action == xbmcgui.ACTION_PAGE_UP:
            if self.getFocusId() == self.NOW_SHOWING_PANEL1_ID:
                return self.onFocus(self.NOW_SHOWING_PANEL1_UP_BUTTON_ID, from_action=True)
            elif self.getFocusId() == self.NOW_SHOWING_PANEL2_ID:
                return self.onFocus(self.NOW_SHOWING_PANEL2_UP_BUTTON_ID, from_action=True)
        elif action == xbmcgui.ACTION_PAGE_DOWN:
            if self.getFocusId() == self.NOW_SHOWING_PANEL1_ID:
                return self.onFocus(self.NOW_SHOWING_PANEL1_DOWN_BUTTON_ID, from_action=True)
            elif self.getFocusId() == self.NOW_SHOWING_PANEL2_ID:
                return self.onFocus(self.NOW_SHOWING_PANEL2_DOWN_BUTTON_ID, from_action=True)
        elif action.getButtonCode() in (61575, 61486):
            if self.getFocusId() in (self.SEARCH_PANEL_ID, self.NOW_SHOWING_PANEL1_ID, self.NOW_SHOWING_PANEL2_ID):
                return self.removeSeries()

    def onActionWatch(self, action):
        if action == xbmcgui.ACTION_GESTURE_SWIPE_LEFT:
            return self.setMode('SEARCH', focus=self.SEARCH_EDIT_ID)
        elif action == xbmcgui.ACTION_MOVE_DOWN or action == xbmcgui.ACTION_MOVE_UP or action == xbmcgui.ACTION_MOVE_RIGHT or action == xbmcgui.ACTION_MOVE_LEFT:
            if self.getFocusId() != self.SHOW_LIST_ID and not util.getGlobalProperty('NO_RECORDINGS'):
                return self.setFocusId(self.SHOW_LIST_ID)

    def onActionRules(self, action):
        # if action == xbmcgui.ACTION_GESTURE_SWIPE_RIGHT:
        #     return self.setMode('SEARCH', focus=self.SEARCH_EDIT_ID)
        # elif action == xbmcgui.ACTION_CONTEXT_MENU:
        #     if self.getFocusId() == self.RULE_LIST_ID:
        #         return self.doRuleContext()
        if action == xbmcgui.ACTION_MOVE_DOWN or action == xbmcgui.ACTION_MOVE_UP or action == xbmcgui.ACTION_MOVE_RIGHT or action == xbmcgui.ACTION_MOVE_LEFT:
            if self.getFocusId() != self.RULE_LIST_ID:
                if self.ruleList.size():
                    self.setFocusId(self.RULE_LIST_ID)
            if self.movingRule and action == xbmcgui.ACTION_MOVE_DOWN or action == xbmcgui.ACTION_MOVE_UP:
                self.moveRule(True)
        # elif action == xbmcgui.ACTION_SELECT_ITEM and self.getFocusId() == self.RULE_LIST_ID:
        #     self.moveRule()
        # elif action == xbmcgui.ACTION_MOUSE_LEFT_CLICK:
        #     if self.getFocusId() == self.RULE_LIST_ID:
        #         #print action.getAmount1()
        #         if 620 < action.getAmount1() < 710:
        #             self.toggleRuleRecent()
        #         elif action.getAmount1() < 619:
        #             self.moveRule()
        elif action == xbmcgui.ACTION_MOUSE_MOVE and self.getFocusId() == self.RULE_LIST_ID:
            if self.movingRule:
                self.moveRule(True)
        elif action.getButtonCode() in (61575, 61486):
            if self.getFocusId() == self.RULE_LIST_ID:
                return self.deleteRule()

    def onClick(self,controlID):
        #print 'click: {0}'.format(controlID)
        if controlID == self.SHOW_LIST_ID:
            self.openEpisodeDialog()
        elif controlID == self.SEARCH_PANEL_ID:
            self.openRecordDialog('SEARCH')
        elif controlID == self.RULE_LIST_ID:
            if self.movingRule:
                self.moveRule()
            else:
                self.openRecordDialog('RULES')
        elif controlID == self.NOW_SHOWING_PANEL1_ID or controlID == self.NOW_SHOWING_PANEL2_ID:
            self.openRecordDialog('NOWSHOWING')
            # self.nowShowingClicked(controlID)
        # elif controlID == self.RULE_LIST_ID:
        #     self.toggleRuleRecent()
        elif controlID == self.WATCH_BUTTON:
            self.setMode('WATCH')
        elif controlID == self.SEARCH_BUTTON:
            if self.mode == 'SEARCH':
                self.setSearch()
            else:
                return self.setMode('SEARCH', focus=self.SEARCH_EDIT_ID)
        elif controlID == self.RULES_BUTTON:
            self.setMode('RULES')
        elif controlID == self.SEARCH_EDIT_BUTTON_ID:
            self.setSearch()
        elif 290 < controlID < 295:
            self.nowShowingTimeClicked(controlID)
        elif 204 < controlID < 209:
            idx = controlID - 205
            self.setSearch(category=('series','movie','sport', 'nowshowing')[idx])

    def onFocus(self,controlID, from_action=False, from_scroll=False):
        #print 'focus: {0}'.format(controlID)
        if xbmc.getCondVisibility('ControlGroup(100).HasFocus(0)'):
            self.mode = 'WATCH'
        elif xbmc.getCondVisibility('ControlGroup(200).HasFocus(0)'):
            if self.mode != 'SEARCH':
                return self.setMode('SEARCH', focus=self.SEARCH_EDIT_ID)
            self.mode = 'SEARCH'
        elif xbmc.getCondVisibility('ControlGroup(300).HasFocus(0)'):
            self.mode = 'RULES'

        if controlID == self.NOW_SHOWING_PANEL2_DOWN_BUTTON_ID:
            self.nsPanel2 = False
            self.fillNowShowing(next_section=True, fix_selection=not from_action)

        elif controlID == self.NOW_SHOWING_PANEL1_DOWN_BUTTON_ID:
            self.nsPanel2 = True
            self.fillNowShowing(next_section=True, fix_selection=not from_action)

        elif controlID == self.NOW_SHOWING_PANEL2_UP_BUTTON_ID:
            if not self.nowShowing:
                return

            self.nowShowing.pos -= 1
            if self.nowShowing.pos < 0:
                self.nowShowing.pos = 0
                self.setFocusId(self.NOW_SHOWING_PANEL2_ID) # Touch focus on the panel so that it's focus will be remembered in the 551 control group
                if not from_action and not from_scroll:
                    self.setFocusId(self.SEARCH_EDIT_BUTTON_ID)
                return
            self.nsPanel2 = False
            self.fillNowShowing(prev_section=True, fix_selection=not from_action)

        elif controlID == self.NOW_SHOWING_PANEL1_UP_BUTTON_ID:
            if not self.nowShowing:
                return

            self.nowShowing.pos -= 1
            if self.nowShowing.pos < 0:
                self.nowShowing.pos = 0
                self.setFocusId(self.NOW_SHOWING_PANEL1_ID) # Touch focus on the panel so that it's focus will be remembered in the 551 control group
                if not from_action and not from_scroll:
                    self.setFocusId(self.SEARCH_EDIT_BUTTON_ID)
                return
            self.nsPanel2 = True
            self.fillNowShowing(prev_section=True, fix_selection=not from_action)

    def tick(self):
        now = time.time()
        if now - self.lastRecordingsRefresh > self.RECORDINGS_REFRESH_INTERVAL:
            self.updateRecordings()
        if now - self.lastSearchRefresh > self.SEARCH_REFRESH_INTERVAL:
            if self.category != 'nowshowing':
                self.fillSearchPanel(update=True)
        if now - self.lastRulesRefresh > self.RULES_REFRESH_INTERVAL:
            self.fillRules(update=True)

        if self.nowShowing:
            if self.nowShowing.checkTime():
                self.updateNowShowing()

    # def halfHour(self):
    #     self.updateNowShowing()

    def setMode(self,mode, focus=None):
        self.mode = mode
        if mode == 'WATCH':
            self.setFocusId(focus or 100)
        elif mode == 'SEARCH':
            self.setFocusId(focus or 200)
        elif mode == 'RULES':
            self.setFocusId(focus or 300)


    def checkMouseWheelInitial(self, action):
        if self.category != 'nowshowing':
            return

        try:
            if self.getFocusId() == self.NOW_SHOWING_PANEL1_ID:
                item = self.nowShowingPanel1.getSelectedItem()
                if item == self.nowShowingPanel1LastItem:
                    self.actionHandler.onAction(action)
                self.nowShowingPanel1LastItem = item
                return True
            elif self.getFocusId() == self.NOW_SHOWING_PANEL2_ID:
                item = self.nowShowingPanel2.getSelectedItem()
                if item == self.nowShowingPanel2LastItem:
                    self.actionHandler.onAction(action)
                self.nowShowingPanel2LastItem = item
                return True
        except RuntimeError: # Get this (Index out of range) when the list has changed since being triggered
            pass

        return False

    def checkMouseWheel(self, action):
        if action == xbmcgui.ACTION_MOUSE_WHEEL_DOWN:
            if self.getFocusId() == self.NOW_SHOWING_PANEL1_ID:
                self.onFocus(self.NOW_SHOWING_PANEL1_DOWN_BUTTON_ID, from_scroll=True)
            elif self.getFocusId() == self.NOW_SHOWING_PANEL2_ID:
                self.onFocus(self.NOW_SHOWING_PANEL2_DOWN_BUTTON_ID, from_scroll=True)

        elif action == xbmcgui.ACTION_MOUSE_WHEEL_UP:
            if self.getFocusId() == self.NOW_SHOWING_PANEL1_ID:
                self.onFocus(self.NOW_SHOWING_PANEL1_UP_BUTTON_ID, from_scroll=True)
            elif self.getFocusId() == self.NOW_SHOWING_PANEL2_ID:
                self.onFocus(self.NOW_SHOWING_PANEL2_UP_BUTTON_ID, from_scroll=True)

    def nowShowingTimeClicked(self, controlID):
        if controlID == 291:
            self.onFocus(self.NOW_SHOWING_PANEL1_UP_BUTTON_ID, from_action=True)
        elif controlID == 293:
            self.onFocus(self.NOW_SHOWING_PANEL1_DOWN_BUTTON_ID, from_action=True)
        if controlID == 292:
            self.onFocus(self.NOW_SHOWING_PANEL2_UP_BUTTON_ID, from_action=True)
        elif controlID == 294:
            self.onFocus(self.NOW_SHOWING_PANEL2_DOWN_BUTTON_ID, from_action=True)

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
            util.setGlobalProperty('NO_RECORDINGS',self.storageServer.getRecordingsFailed and u'[COLOR 80FF0000]{0}[/COLOR]'.format(T(32829)) or T(32803))
        else:
            util.setGlobalProperty('NO_RECORDINGS','')

        if items:
            allItem = kodigui.ManagedListItem('ALL RECORDINGS', thumbnailImage='script-hdhomerun-view-dvr_all.png')
            items.insert(0,allItem)

        if update:
            self.showList.replaceItems(items)
        else:
            self.showList.reset()
            self.showList.addItems(items)

    @util.busyDialog('LOADING GUIDE')
    def fillSearchPanel(self, update=False):
        self.lastSearchRefresh = time.time()

        items = []

        try:
            searchResults = hdhr.guide.search(self.devices.apiAuthID(),category=self.category,terms=self.searchTerms) or []
        except:
            searchResults = []
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
        if update:
            self.searchPanel.replaceItems(items)
        else:
            self.searchPanel.reset()
            self.searchPanel.addItems(items)

    @util.busyDialog('LOADING NOW SHOWING')
    def fillNowShowing(self, next_section=False, prev_section=False, fix_selection=True, current=False):
        if not self.nowShowing:
            self.nowShowing = hdhr.guide.NowShowing(self.devices)

        if current:
            if self.nowShowing.pos > 0:
                self.nsPanel2 = bool(self.nowShowing.pos % 2)
                prev_section = True

        if next_section:
            self.nowShowing.pos  += 1

            try:
                searchResults, nextDisp, footerDisp = self.nowShowing.upNext()
            except hdhr.guide.EndOfNowShowingException:
                self.nowShowing.pos -= 1
                if self.nsPanel2:
                    self.setFocusId(self.NOW_SHOWING_PANEL1_ID)
                    util.setGlobalProperty('ns.panel1.footer', 'END')
                else:
                    self.setFocusId(self.NOW_SHOWING_PANEL2_ID)
                    util.setGlobalProperty('ns.panel2.footer', 'END')
                self.nsPanel2 = not self.nsPanel2
                return

            if self.nsPanel2:
                util.setGlobalProperty('ns.panel2.heading', nextDisp)
                util.setGlobalProperty('ns.panel2.footer', footerDisp)
                self.fillNSPanel2(searchResults)

                if fix_selection:
                    off1 = self.nowShowingPanel1.getSelectedPosition() % 4
                    if self.nowShowingPanel2.positionIsValid(off1):
                        self.nowShowingPanel2.selectItem(off1)

                self.setFocusId(self.NOW_SHOWING_PANEL2_ID)
                self.slideNSUp()
            else:
                util.setGlobalProperty('ns.panel1.heading', nextDisp)
                util.setGlobalProperty('ns.panel1.footer', footerDisp)
                self.fillNSPanel1(searchResults)

                if fix_selection:
                    off2 = self.nowShowingPanel2.getSelectedPosition() % 4
                    if self.nowShowingPanel1.positionIsValid(off2):
                        self.nowShowingPanel1.selectItem(off2)

                self.setFocusId(self.NOW_SHOWING_PANEL1_ID)
                self.slideNSUp()
        elif prev_section:
            searchResults, prevDisp, footerDisp = self.nowShowing.upNext()

            if self.nsPanel2:
                util.setGlobalProperty('ns.panel2.heading', prevDisp)
                util.setGlobalProperty('ns.panel2.footer', footerDisp)
                self.fillNSPanel2(searchResults)

                if fix_selection:
                    off1 = (self.nowShowingPanel1.getSelectedPosition() + 1) % 4
                    off2 = self.nowShowingPanel2.size() % 4
                    if off1 < off2:
                        self.nowShowingPanel2.selectItem((self.nowShowingPanel2.size() - 1) - (off2 - off1))
                    elif off2 < off1:
                        self.nowShowingPanel2.selectItem((self.nowShowingPanel2.size() - 5) + (off1 - off2))
                    else:
                        self.nowShowingPanel2.selectItem((self.nowShowingPanel2.size() - 1))

                self.setFocusId(self.NOW_SHOWING_PANEL2_ID)
                self.slideNSDown()
            else:
                util.setGlobalProperty('ns.panel1.heading', prevDisp)
                util.setGlobalProperty('ns.panel1.footer', footerDisp)
                self.fillNSPanel1(searchResults)

                if fix_selection:
                    off1 = self.nowShowingPanel1.size() % 4
                    off2 = (self.nowShowingPanel2.getSelectedPosition() + 1) % 4
                    if off2 < off1:
                        self.nowShowingPanel1.selectItem((self.nowShowingPanel1.size() - 1) - (off1 - off2))
                    elif off1 < off2:
                        self.nowShowingPanel1.selectItem((self.nowShowingPanel1.size() - 5) + (off2 - off1))
                    else:
                        self.nowShowingPanel1.selectItem((self.nowShowingPanel1.size() - 1))

                self.setFocusId(self.NOW_SHOWING_PANEL1_ID)
                self.slideNSDown()
        else:
            self.nowShowing.pos = 0
            searchResults, nowDisp, nextDisp = self.nowShowing.nowShowing()
            util.setGlobalProperty('ns.panel1.heading', 'NOW SHOWING')
            self.nsPanel2 = False

            util.setGlobalProperty('ns.panel2.heading', nextDisp)
            util.setGlobalProperty('ns.panel1.footer', nextDisp)

            self.fillNSPanel1(searchResults)
            self.slideNSUp(1)
            self.setFocusId(self.NOW_SHOWING_PANEL1_ID)

        util.setGlobalProperty('NO_RESULTS',not searchResults and T(32802) or '')

    def updateNowShowing(self):
        if not self.category == 'nowshowing':
            return

        util.DEBUG_LOG('UPDATING NOW SHOWING')

        selectedSeries = None
        try:
            panel = self.currentNowShowingPanel()
            if panel.size():
                selectedSeries = panel.getSelectedItem().dataSource
        except:
            util.ERROR()

        self.fillNowShowing(current=True)

        panel = self.currentNowShowingPanel()
        for item in panel:
            if item.dataSource.ID == selectedSeries.ID:
                panel.selectItem(item.pos())
                return

    def currentNowShowingPanel(self):
        if self.nsPanel2:
            return self.nowShowingPanel2
        else:
            return self.nowShowingPanel1

    def slideNSUp(self, duration=400):
        self.getControl(self.nsPanel2 and 262 or 261).setAnimations([
            ('conditional', 'effect=slide start=0,985 end=0,0 time={0} condition=true'.format(duration))
        ])
        self.getControl(self.nsPanel2 and 261 or 262).setAnimations([
            ('conditional', 'effect=fade start=100 end=0 time={0} condition=true'.format(duration)),
            ('conditional', 'effect=slide start=0,0 end=0,-985 time={0} condition=true'.format(duration))
        ])

    def slideNSDown(self, duration=400):
        self.getControl(self.nsPanel2 and 262 or 261).setAnimations([
            ('conditional', 'effect=slide start=0,-985 end=0,0 time={0} condition=true'.format(duration))
        ])
        self.getControl(self.nsPanel2 and 261 or 262).setAnimations([
            ('conditional', 'effect=fade start=100 end=0 time={0} condition=true'.format(duration)),
            ('conditional', 'effect=slide start=0,0 end=0,985 time={0} condition=true'.format(duration))
        ])

    def fillNSPanel1(self, searchResults, now=False):
        now = self.nowShowing.pos == 0 and '1' or ''
        self.fillNSPanel(self.nowShowingPanel1, searchResults, now)

    def fillNSPanel2(self, searchResults):
        self.fillNSPanel(self.nowShowingPanel2, searchResults)

    def fillNSPanel(self, panel, searchResults, on_now=''):
        items = []
        for r in searchResults:
            if r.hidden:
                continue
            item = kodigui.ManagedListItem(r.title,r.synopsis,thumbnailImage=r.icon,data_source=r)
            item.setProperty('series.title',r.title)
            item.setProperty('channel.number',r.channelNumber)
            item.setProperty('channel.name',r.channelName)
            item.setProperty('channel.icon',r.channelIcon)
            item.setProperty('has.rule',r.hasRule and '1' or '')
            item.setProperty('hidden',r.hidden and '1' or '')
            item.setProperty('on.now',on_now)
            items.append(item)

        panel.reset()
        panel.addItems(items)

    @util.busyDialog('LOADING RULES')
    def fillRules(self,update=False):
        self.lastRulesRefresh = time.time()
        if update: self.storageServer.updateRules()

        items = []
        for r in self.storageServer.rules:
            item = kodigui.ManagedListItem(r.title,data_source=r)
            item.setProperty('rule.recent_only',r.recentOnly and T(32805) or T(32806))
            item.setProperty('seriesID', r.seriesID)
            #print '{0} {1}'.format(r.ruleID, r.title)
            items.append(item)

        if not items:
            util.setGlobalProperty('NO_RULES',self.storageServer.getRulesFailed and u'[COLOR 80FF0000]{0}[/COLOR]'.format(T(32830)) or T(32804))
        else:
            util.setGlobalProperty('NO_RULES','')

        self.ruleList.reset()
        self.ruleList.addItems(items)

    def doRuleContext(self):
        options = [T(32807),T(32809)]
        idx = xbmcgui.Dialog().select(T(32810),options)
        if idx < 0: return
        try:
            if idx == 0:
                self.toggleRuleRecent()
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

    def deleteRule(self, rule=None):
        if not rule:
            item = self.ruleList.getSelectedItem()
            if not item:
                return
            rule = item.dataSource

        yes = xbmcgui.Dialog().yesno(T(32035),T(32037))
        if not yes:
            return

        util.withBusyDialog(self.storageServer.deleteRule,'DELETING',rule)

        def update(sitem):
            if rule.seriesID == sitem.dataSource.ID:
                sitem.dataSource['RecordingRule'] = ''
                sitem.setProperty('has.rule','')

        for sItem in self.searchPanel:
            update(sItem)

        for sItem in self.nowShowingPanel1:
            update(sItem)

        for sItem in self.nowShowingPanel2:
            update(sItem)

        self.fillRules(update=True)

    def moveRule(self,move=False):
        if not move:
            if self.movingRule:
                util.setGlobalProperty('moving.rule','')
                if move is not None:
                    self.updateRulePriority()
                self.movingRule = None
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
    def updateRulePriority(self):
        pos = self.movingRule.pos()
        if pos == 0:
            afterRuleID = 0
        else:
            pos -= 1
            afterRuleID = self.ruleList.getListItem(pos).dataSource.ruleID

        self.movingRule.dataSource.move(afterRuleID)
        self.fillRules(update=True)

    def setSearch(self,category=None):
        #self.searchTerms = self.getControl(self.SEARCH_EDIT_ID).getText() or ''
        if category:
            self.searchTerms = ''
            self.category = category
            catDisplay = {'series':'Shows','movie':'Movies','sport':'Sports','nowshowing':'Now Showing'}
            util.setGlobalProperty('search.terms',catDisplay[category])
            if category == 'nowshowing':
                util.setGlobalProperty('now.showing','1')
                self.fillNowShowing()
            else:
                if self.nowShowing:
                    self.nowShowing.pos = 0
                util.setGlobalProperty('now.showing','')
                self.fillSearchPanel()
        else:
            self.searchTerms = xbmcgui.Dialog().input(T(32812),self.searchTerms)
            if not self.searchTerms:
                return

            util.setGlobalProperty('now.showing','')
            self.category = ''
            util.setGlobalProperty('search.terms',self.searchTerms)
            self.fillSearchPanel()

        if util.getGlobalProperty('NO_RESULTS'):
            self.setFocusId(202)
        else:
            if category != 'nowshowing':
                self.setFocusId(201)

    def openRecordDialog(self, source, item=None):
        rule = None
        if source == 'SEARCH':
            item = item or self.searchPanel.getSelectedItem()
            for ritem in self.ruleList:
                if ritem.dataSource.ID == item.dataSource.ID:
                    rule = ritem.dataSource
                    break
        elif source == 'RULES':
            item = item or self.ruleList.getSelectedItem()
            rule = item.dataSource
        elif source == 'NOWSHOWING':
            panel = self.currentNowShowingPanel()
            item = item or panel.getSelectedItem()
            for ritem in self.ruleList:
                if ritem.dataSource.ID == item.dataSource.ID:
                    rule = ritem.dataSource
                    break

        if not item: return
        path = skin.getSkinPath()
        series = item.dataSource
        try:
            d = RecordDialog(
                skin.DVR_RECORD_DIALOG,
                path,
                'Main',
                '1080i',
                parent=self,
                series=series,
                rule=rule,
                storage_server=self.storageServer,
                show_hide=not self.searchTerms and source != 'RULES'
            )

            d.doModal()

            if d.setPriority:
                self.setMode('RULES')
                item = self.ruleList.getListItemByProperty('seriesID', series.ID)
                if not item or not rule:
                    util.LOG('openRecordDialog() - setPriority: No item or no rule')
                    return
                self.ruleList.selectItem(item.pos())
                self.moveRule()
            elif d.ruleAdded:
                if source == 'SEARCH' or source == 'NOWSHOWING':
                    item.setProperty('has.rule','1')

            self.removeSeries(series)

        finally:
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
            if self.getFocusId() == self.SEARCH_PANEL_ID:
                panel = self.searchPanel
            elif self.getFocusId() == self.NOW_SHOWING_PANEL1_ID:
                panel = self.nowShowingPanel1
            elif self.getFocusId() == self.NOW_SHOWING_PANEL2_ID:
                panel = self.nowShowingPanel2

            mli = panel.getSelectedItem()
            if not mli: return
            series = mli.dataSource
            # if not xbmcgui.Dialog().yesno(T(32035),mli.dataSource.title,'',T(32839)):
            #     return
            util.withBusyDialog(self.storageServer.hideSeries,'HIDING',series)

        for panel in (self.searchPanel, self.nowShowingPanel1, self.nowShowingPanel2):
            self.removeSeriesFromPanel(panel, series)

        if not series.hidden and self.nowShowing:
            self.nowShowing.unHide(series)


        #self.fillSearchPanel(update=True)

    def removeSeriesFromPanel(self, panel, series):
        for (i, mli) in enumerate(panel):
            if mli.dataSource.ID == series.ID:
                if series.hidden:
                    panel.removeItem(i)
                else:
                    mli.setProperty('hidden','')
                break

    def playShow(self, series):
        self.play = series
        self.doClose()

class DVRWindow(DVRBase,kodigui.BaseWindow):
    _BASE = kodigui.BaseWindow

class DVRDialog(DVRBase,kodigui.BaseDialog):
    _BASE = kodigui.BaseDialog