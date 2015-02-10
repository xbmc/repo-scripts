#
#  MythBox for XBMC - http://mythbox.googlecode.com
#  Copyright (C) 2011 analogue@yahoo.com
#
#  This program is free software; you can redistribute it and/or
#  modify it under the terms of the GNU General Public License
#  as published by the Free Software Foundation; either version 2
#  of the License, or (at your option) any later version.
#
#  This program is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with this program; if not, write to the Free Software
#  Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301, USA.
#
import copy
import logging
import odict
import time
import xbmc
import xbmcgui
import mythbox.msg as m

from mythbox.mythtv.conn import inject_conn 
from mythbox.mythtv.db import inject_db 
from mythbox.mythtv.enums import CheckForDupesIn, CheckForDupesUsing, EpisodeFilter, ScheduleType
from mythbox.ui.toolkit import BaseDialog, BaseWindow, window_busy, Action 
from mythbox.util import catchall_ui, catchall, run_async, safe_str

log = logging.getLogger('mythbox.ui')

ID_SCHEDULES_LISTBOX = 600
ID_REFRESH_BUTTON = 250
ID_SORT_BY_BUTTON = 251


SORT_BY = odict.odict([
    ('Title',          {'translation_id': m.TITLE,              'sorter' : lambda rs: safe_str(rs.title())                                 }), 
    ('# Recorded',     {'translation_id': m.NUM_RECORDED,       'sorter' : lambda rs: '%05d %s' % (rs.numRecorded(), safe_str(rs.title())) }), 
    ('Priority',       {'translation_id': m.RECORDING_PRIORITY, 'sorter' : lambda rs: '%05d %s' % (rs.getPriority(), safe_str(rs.title())) })])


class SchedulesWindow(BaseWindow):
    
    def __init__(self, *args, **kwargs):
        BaseWindow.__init__(self, *args, **kwargs)
        [setattr(self,k,v) for k,v in kwargs.iteritems() if k in ('settings','translator','platform','fanArt','cachesByName',)]
        [setattr(self,k,v) for k,v in self.cachesByName.iteritems() if k in ('mythChannelIconCache', 'domainCache',)]
        
        self.schedules = []                       # [RecordingSchedule]
        self.listItemsBySchedule = odict.odict()  # {RecordingSchedule:ListItem}
        self.channelsById = None                  # {int:Channel}
        self.lastFocusId = ID_SCHEDULES_LISTBOX
        self.lastSelected = int(self.settings.get('schedules_last_selected'))
        self.sortBy = self.settings.get('schedules_sort_by')
        self.activeRenderToken = None
        
    @catchall
    def onInit(self):
        if not self.win:
            self.win = xbmcgui.Window(xbmcgui.getCurrentWindowId())
            self.schedulesListBox = self.getControl(ID_SCHEDULES_LISTBOX)
            self.refreshButton = self.getControl(ID_REFRESH_BUTTON)
            self.refresh()

    @catchall_ui
    def onClick(self, controlId):
        if controlId == ID_SCHEDULES_LISTBOX: 
            self.goEditSchedule()
        elif controlId == ID_REFRESH_BUTTON:
            self.refresh(force=True)
        elif controlId == ID_SORT_BY_BUTTON:
            keys = SORT_BY.keys()
            self.sortBy = keys[(keys.index(self.sortBy) + 1) % len(keys)] 
            self.applySort()
             
    def onFocus(self, controlId):
        self.lastFocusId = controlId
        #if controlId == ID_SCHEDULES_LISTBOX:
        #    self.lastSelected = self.schedulesListBox.getSelectedPosition()

    @catchall
    def onAction(self, action):
        id = action.getId()
        
        if id in Action.GO_BACK:
            self.closed = True
            self.settings.put('schedules_last_selected', '%d'%self.schedulesListBox.getSelectedPosition())
            self.settings.put('schedules_sort_by', self.sortBy)
            self.close()

        elif id in (Action.ACTION_NEXT_ITEM, Action.ACTION_PREV_ITEM,):  # bottom, top
            if self.lastFocusId == ID_SCHEDULES_LISTBOX:
                self.selectListItemAtIndex(self.schedulesListBox, [0, self.schedulesListBox.size()-1][id == Action.ACTION_NEXT_ITEM])

    def applySort(self):
        self.schedules.sort(key=SORT_BY[self.sortBy]['sorter'], reverse=False)
        self.render()
            
    def goEditSchedule(self):
        self.lastSelected = self.schedulesListBox.getSelectedPosition()
        editScheduleDialog = ScheduleDialog(
            'mythbox_schedule_dialog.xml',
            self.platform.getScriptDir(), 
            forceFallback=True,
            schedule=self.schedules[self.schedulesListBox.getSelectedPosition()], 
            translator=self.translator,
            platform=self.platform,
            settings=self.settings,
            mythChannelIconCache=self.mythChannelIconCache)
        editScheduleDialog.doModal()
        if editScheduleDialog.shouldRefresh:
            self.refresh()
             
    @inject_db
    def cacheChannels(self):
        if not self.channelsById:
            self.channelsById = {}
            for channel in self.domainCache.getChannels():
                self.channelsById[channel.getChannelId()] = channel
        
    @window_busy
    @inject_db
    def refresh(self, force=False):
        self.cacheChannels()
        self.schedules = self.domainCache.getRecordingSchedules(force=force)
        self.applySort()
        self.render()
        
    def render(self):
        log.debug('Rendering....')
        self.listItemsBySchedule.clear()
        listItems = []
        
        def buildListItems():
            for i, s in enumerate(self.schedules):
                li = xbmcgui.ListItem()
                self.setListItemProperty(li, 'title', s.title())
                self.setListItemProperty(li, 'scheduleType', s.formattedScheduleType())
                self.setListItemProperty(li, 'fullTitle', s.fullTitle())
                self.setListItemProperty(li, 'priority', '%s' % s.getPriority())
                self.setListItemProperty(li, 'poster', 'loading.gif')
                self.setListItemProperty(li, 'index', str(i+1))
                self.setListItemProperty(li, 'numRecorded', '%s' % s.numRecorded())                

                # protect against deleted channels/tuners
                if s.getChannelId() in self.channelsById:

                    if s.getChannelName():
                        self.setListItemProperty(li, 'channelName', s.getChannelName())
                    
                    channel = self.channelsById[s.getChannelId()]
                    if channel.getIconPath():
                        channelIcon = self.mythChannelIconCache.get(channel)
                        if channelIcon:
                            self.setListItemProperty(li, 'channelIcon', channelIcon)
                elif s.station():
                    self.setListItemProperty(li, 'channelName', s.station())
                
                if self.fanArt.hasPosters(s):
                    s.needsPoster = False
                    self.setListItemProperty(li, 'poster', self.lookupPoster(s))
                else:
                    s.needsPoster = True
                
                listItems.append(li)
                self.listItemsBySchedule[s] = li

        buildListItems()
        self.schedulesListBox.reset()
        self.schedulesListBox.addItems(listItems)
        self.schedulesListBox.selectItem(self.lastSelected)
        self.renderNav()
        
        self.activeRenderToken = time.clock()
        self.renderPosters(self.activeRenderToken)

    def renderNav(self):
        self.setWindowProperty('sortBy', self.translator.get(m.SORT) + ': ' + self.translator.get(SORT_BY[self.sortBy]['translation_id']))

    @run_async
    @catchall
    def renderPosters(self, myRenderToken):
        for schedule, listItem in self.listItemsBySchedule.items():
            if self.closed or xbmc.abortRequested or myRenderToken != self.activeRenderToken: 
                return
            if schedule.needsPoster:
                try:
                    schedule.needsPoster = False
                    self.setListItemProperty(listItem, 'poster', self.lookupPoster(schedule))
                except Exception, ex:
                    log.exception('renderPosters')
                
    def lookupPoster(self, schedule):
        try:
            posterPath = self.fanArt.pickPoster(schedule)
            if not posterPath:
                channel =  self.channelsById[schedule.getChannelId()]
                if channel.getIconPath():
                    posterPath = self.mythChannelIconCache.get(channel)
        except:
            posterPath = self.platform.getMediaPath('mythbox.png')
        
        return posterPath
        

class ScheduleDialog(BaseDialog):
    """Create new and edit existing recording schedules"""
        
    def __init__(self, *args, **kwargs):
        BaseDialog.__init__(self, *args, **kwargs)
        [setattr(self,k,v) for k,v in kwargs.iteritems() if k in ('settings','translator','platform','mythChannelIconCache',)]
        
        # Leave passed in schedule untouched; work on a copy of it 
        # in case the user cancels the operation.
        self.schedule = copy.copy(kwargs['schedule'])
        self.shouldRefresh = False
        
    @catchall
    def onInit(self):
        self.win = xbmcgui.Window(xbmcgui.getCurrentWindowDialogId())
        self.enabledCheckBox = self.getControl(212)
        self.autoCommFlagCheckBox = self.getControl(205)
        self.autoExpireCheckBox = self.getControl(207)
        self.autoTranscodeCheckBox = self.getControl(218)
        self.recordNewExpireOldCheckBox = self.getControl(213) 
        self.userJob1CheckBox = self.getControl(214)
        self.userJob2CheckBox = self.getControl(215)
        self.userJob3CheckBox = self.getControl(216)
        self.userJob4CheckBox = self.getControl(217)
        
        self.saveButton = self.getControl(250)
        self.deleteButton = self.getControl(251)
        self.cancelButton = self.getControl(252)
        
        self._updateView()

    def onFocus(self, controlId):
        self.lastFocusId = controlId
        
    @catchall_ui 
    def onAction(self, action):
        if action.getId() in Action.GO_BACK:
            self.close() 

    @catchall_ui
    @inject_conn
    @inject_db
    def onClick(self, controlId):
        t = self.translator.get
        log.debug('onClick %s ' % controlId)
        source = self.getControl(controlId)
        s = self.schedule
 
        # NOTE: Don't let user select ScheduleType.NOT_RECORDING -- remove from translation list
        scheduleTypeMinusNotRecording = odict.odict(ScheduleType.long_translations)
        del scheduleTypeMinusNotRecording[ScheduleType.NOT_RECORDING]        
        if controlId == 201: self._chooseFromList(scheduleTypeMinusNotRecording, t(m.RECORD_WHEN), 'scheduleType', s.setScheduleType)
        
        elif controlId == 202:
            priority = self._enterNumber(t(m.RECORDING_PRIORITY), s.getPriority(), -99, 99)
            s.setPriority(priority)
            self.setWindowProperty('priority', str(priority))
        
        elif self.autoCommFlagCheckBox == source: 
            s.setAutoCommFlag(self.autoCommFlagCheckBox.isSelected())
        
        elif self.autoExpireCheckBox == source: 
            s.setAutoExpire(self.autoExpireCheckBox.isSelected())
        
        elif self.enabledCheckBox == source: 
            s.setEnabled(self.enabledCheckBox.isSelected())
        
        elif self.autoTranscodeCheckBox == source: 
            s.setAutoTranscode(self.autoTranscodeCheckBox.isSelected())
        
        elif self.recordNewExpireOldCheckBox == source: 
            s.setRecordNewAndExpireOld(self.recordNewExpireOldCheckBox.isSelected())    
        
        elif self.userJob1CheckBox == source:
            s.setAutoUserJob1(self.userJob1CheckBox.isSelected())

        elif self.userJob2CheckBox == source:
            s.setAutoUserJob2(self.userJob2CheckBox.isSelected())
        
        elif self.userJob3CheckBox == source:
            s.setAutoUserJob3(self.userJob3CheckBox.isSelected())
            
        elif self.userJob4CheckBox == source:
            s.setAutoUserJob4(self.userJob4CheckBox.isSelected())
            
        elif controlId == 203: self._chooseFromList(CheckForDupesUsing.translations, t(m.CHECK_FOR_DUPES_USING), 'checkForDupesUsing', s.setCheckForDupesUsing)            
        elif controlId == 204: self._chooseFromList(CheckForDupesIn.translations, t(m.CHECK_FOR_DUPES_IN), 'checkForDupesIn', s.setCheckForDupesIn)
        elif controlId == 208: self._chooseFromList(EpisodeFilter.translations, t(m.EPISODE_FILTER), 'episodeFilter', s.setEpisodeFilter)
        elif controlId == 219: 
            fakeTr = odict.odict()
            for name in self.db().getRecordingProfileNames():
                fakeTr[name] = name
            self._chooseFromList(fakeTr, t(m.RECORDING_PROFILE), 'recordingProfile', s.setRecordingProfile)
                
        elif controlId == 206:
            maxEpisodes = self._enterNumber(t(m.KEEP_AT_MOST), s.getMaxEpisodes(), 0, 99)
            s.setMaxEpisodes(maxEpisodes)
            self.setWindowProperty('maxEpisodes', (t(m.N_EPISODES) % maxEpisodes, t(m.ALL_EPISODES))[maxEpisodes == 0])

        elif controlId == 209:
            minutes = self._enterNumber(t(m.START_RECORDING_EARLY), s.getStartOffset(), 0, 60) 
            s.setStartOffset(minutes)
            self.setWindowProperty('startEarly', (t(m.N_MINUTES_EARLY) % minutes, t(m.ON_TIME))[minutes == 0]) 
             
        elif controlId == 210:
            minutes = self._enterNumber(t(m.END_RECORDING_LATE), s.getEndOffset(), 0, 60) 
            s.setEndOffset(minutes)
            self.setWindowProperty('endLate', (t(m.N_MINUTES_LATE) % minutes, t(m.ON_TIME))[minutes == 0])
             
        elif self.saveButton == source:
            log.debug("Save button clicked")
            self.conn().saveSchedule(self.schedule)
            self.shouldRefresh = True
            self.close()
            
        elif self.deleteButton == source:
            log.debug('Delete button clicked')
            self.conn().deleteSchedule(self.schedule)
            self.shouldRefresh = True
            self.close()
            
        elif self.cancelButton == source:
            log.debug("Cancel button clicked")
            self.close()

    def _updateView(self):
        s = self.schedule
        t = self.translator.get

        if s.getScheduleId() is None:
            self.setWindowProperty('heading', t(m.NEW_SCHEDULE))
            self.deleteButton.setEnabled(False)
        else:
            self.setWindowProperty('heading', t(m.EDIT_SCHEDULE))

        logo = 'mythbox-logo.png'    
        try:
            if s.getIconPath() and self.mythChannelIconCache.get(s):
                logo = self.mythChannelIconCache.get(s)
        except:
            log.exception('setting channel logo in schedules dialog box')
        self.setWindowProperty('channel_logo', logo)
        
        self.setWindowProperty('channel', s.getChannelNumber())
        self.setWindowProperty('station', s.station())    
        
        # TODO: Find root cause
        try:
            self.setWindowProperty('startTime', s.formattedTime())
        except:
            log.exception("HACK ALERT: s.formattedTime() blew up. Known issue.")
            self.setWindowProperty('startTime', t(m.UNKNOWN))
            
        self.setWindowProperty('title', s.title())    
        self.setWindowProperty('startDate', s.formattedStartDate())    
        self.setWindowProperty('scheduleType', s.formattedScheduleTypeDescription())
        self.setWindowProperty('priority', str(s.getPriority()))

        self.autoCommFlagCheckBox.setLabel(t(m.AUTOFLAG_COMMERCIALS))
        self.autoCommFlagCheckBox.setSelected(s.isAutoCommFlag())
        
        self.autoExpireCheckBox.setLabel(t(m.AUTO_EXPIRE))
        self.autoExpireCheckBox.setSelected(s.isAutoExpire())
        
        self.setWindowProperty('checkForDupesUsing', t(CheckForDupesUsing.translations[s.getCheckForDupesUsing()]))
        self.setWindowProperty('checkForDupesIn', t(CheckForDupesIn.translations[s.getCheckForDupesIn()]))
        self.setWindowProperty('episodeFilter', t(EpisodeFilter.translations[s.getEpisodeFilter()])) 
        
        self.autoTranscodeCheckBox.setSelected(s.isAutoTranscode())
        self.recordNewExpireOldCheckBox.setSelected(s.isRecordNewAndExpireOld())
        
        self.setWindowProperty('maxEpisodes', (t(m.N_EPISODES) % s.getMaxEpisodes(), t(m.ALL_EPISODES))[s.getMaxEpisodes() == 0])
        self.setWindowProperty('startEarly', (t(m.N_MINUTES_EARLY) % s.getStartOffset(), t(m.ON_TIME))[s.getStartOffset() == 0])
        self.setWindowProperty('endLate', (t(m.N_MINUTES_LATE) % s.getEndOffset(), t(m.ON_TIME))[s.getEndOffset() == 0])
        
        self.setWindowProperty('recordingProfile', s.getRecordingProfile())
        
        self.enabledCheckBox.setSelected(s.isEnabled())
        self.renderUserJobs(s, t)
        
    @inject_db
    def renderUserJobs(self, s, t):
        jobs = {
            'UserJob1': {'control':self.userJob1CheckBox, 'text':m.USERJOB1_ENABLED, 'descColumn':'UserJobDesc1', 'getter':s.isAutoUserJob1}, 
            'UserJob2': {'control':self.userJob2CheckBox, 'text':m.USERJOB2_ENABLED, 'descColumn':'UserJobDesc2', 'getter':s.isAutoUserJob2},
            'UserJob3': {'control':self.userJob3CheckBox, 'text':m.USERJOB3_ENABLED, 'descColumn':'UserJobDesc3', 'getter':s.isAutoUserJob3}, 
            'UserJob4': {'control':self.userJob4CheckBox, 'text':m.USERJOB4_ENABLED, 'descColumn':'UserJobDesc4', 'getter':s.isAutoUserJob4}
        }
        
        for jobName in jobs.keys():
            jobCommand = self.db().getMythSetting(jobName)
            checkBox = jobs[jobName]['control']
            if jobCommand is None or len(jobCommand) == 0:
                checkBox.setVisible(False)
            else:
                checkBox.setLabel(self.db().getMythSetting(jobs[jobName]['descColumn']))    
                checkBox.setSelected(jobs[jobName]['getter']())
        
    def _chooseFromList(self, translations, title, property, setter):
        """
        Boiler plate code that presents the user with a dialog box to select a value from a list.
        Once selected, the setter method on the Schedule is called to reflect the selection.
        
        @param translations: odict of {enumerated type:translation index}
        @param title: Dialog box title
        @param property: Window property name 
        @param setter: method on Schedule to 'set' selected item from chooser
        """
        pickList = self.translator.toList(translations)
        selected = xbmcgui.Dialog().select(title, pickList)
        if selected >= 0:
            self.setWindowProperty(property, pickList[selected])
            setter(translations.keys()[selected])
            
    def _enterNumber(self, heading, current, min=None, max=None):
        """
        Prompt user to enter a valid number with optional min/max bounds.
        
        @param heading: Dialog title as string
        @param current: current value as int
        @param min: Min value of number as int
        @param max: Max value of number as int
        @return: entered number as int
        """
        t = self.translator.get
        value = xbmcgui.Dialog().numeric(0, heading, str(current))
        if value is None or value == str(current):
            return current

        result = int(value)
        
        if min is not None and result < min:
            xbmcgui.Dialog().ok(t(m.ERROR), t(m.ERR_VALUE_BETWEEN) % (min, max))
            result = current
            
        if max is not None and result > max:
            xbmcgui.Dialog().ok(t(m.ERROR), t(m.ERR_VALUE_BETWEEN) % (min, max))
            result = current
            
        return result             