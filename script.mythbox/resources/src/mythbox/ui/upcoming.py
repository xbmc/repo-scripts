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

import datetime
import logging
import odict
import time
import xbmc
import xbmcgui
import mythbox.msg as m

from mythbox.mythtv.conn import inject_conn
from mythbox.mythtv.db import inject_db
from mythbox.mythtv.domain import Channel
from mythbox.ui.schedules import ScheduleDialog
from mythbox.ui.toolkit import BaseWindow, window_busy, Action
from mythbox.util import catchall_ui, run_async, catchall, ui_locked, ui_locked2

log = logging.getLogger('mythbox.ui')

ID_PROGRAMS_LISTBOX = 600
ID_REFRESH_BUTTON = 250
ID_SORT_BY_BUTTON = 251
ID_SORT_ASCENDING_TOGGLE = 252

ONE_DAY = datetime.timedelta(days=1)
ONE_WEEK = datetime.timedelta(weeks=1)

SORT_BY = odict.odict([
    ('Date',   {'translation_id': m.DATE,    'sorter' : lambda x: x.starttimeAsTime() }), 
    ('Title',  {'translation_id': m.TITLE,   'sorter' : lambda x: '%s %s' % (x.title(), x.starttimeAsTime())}),
    ('Channel',{'translation_id': m.CHANNEL, 'sorter' : lambda x: Channel.sortableChannelNumber(x.getChannelNumber(), 0)})])

class UpcomingRecordingsWindow(BaseWindow):
    
    def __init__(self, *args, **kwargs):
        BaseWindow.__init__(self, *args, **kwargs)
        [setattr(self,k,v) for k,v in kwargs.iteritems() if k in ('settings','translator','platform','fanArt','cachesByName', 'upcoming', )]
        [setattr(self,k,v) for k,v in self.cachesByName.iteritems() if k in ('mythChannelIconCache','domainCache', )]
        
        self.programs = []                       # [RecordedProgram]
        self.channelsById = None                 # {int:Channel}
        self.tunersById = None                   # {int:Tuner}
        self.listItemsByProgram = odict.odict()  # {Program:ListItem}
        self.programsByListItem = odict.odict()  # {ListItem:Program}
        self.sortBy = self.settings.get('upcoming_sort_by')
        self.sortAscending = self.settings.getBoolean('upcoming_sort_ascending')
        self.activeRenderToken = None
        
    @catchall_ui
    def onInit(self):
        if not self.win:
            self.win = xbmcgui.Window(xbmcgui.getCurrentWindowId())
            self.programsListBox = self.getControl(600)
            self.refreshButton = self.getControl(250)
            self.refresh()
        
    @catchall_ui
    def onClick(self, controlId):
        if controlId == ID_PROGRAMS_LISTBOX:
            self.onEditSchedule()
        elif controlId == ID_REFRESH_BUTTON:
            self.refresh()
        elif controlId == ID_SORT_BY_BUTTON:
            keys = SORT_BY.keys()
            self.sortBy = keys[(keys.index(self.sortBy) + 1) % len(keys)] 
            self.applySort()
        elif controlId == ID_SORT_ASCENDING_TOGGLE:
            self.sortAscending = not self.sortAscending
            self.applySort()
    
    def applySort(self):
        self.programs.sort(key=SORT_BY[self.sortBy]['sorter'], reverse=self.sortAscending)
        self.render()
             
    def onFocus(self, controlId):
        self.lastFocusId = controlId

    @inject_db
    def onEditSchedule(self):
        log.debug('Launching edit recording schedule dialog...')
        listItem = self.programsListBox.getSelectedItem()
        program = self.programsByListItem[listItem]
        scheduleId = program.getScheduleId()
        if not scheduleId:
            xbmcgui.Dialog().ok(self.translator.get(m.ERROR), self.translator.get(m.ERR_NO_RECORDING_SCHEDULE))
            return
        
        schedules = self.db().getRecordingSchedules(scheduleId=scheduleId)
        if not schedules:
            xbmcgui.Dialog().ok(self.translator.get(m.ERROR), self.translator.get(m.ERR_SCHEDULE_NOT_FOUND) % scheduleId)
            return
        
        ScheduleDialog(
            'mythbox_schedule_dialog.xml', 
            self.platform.getScriptDir(), 
            forceFallback=True,
            schedule=schedules[0], 
            translator=self.translator,
            platform=self.platform,
            settings=self.settings,
            mythChannelIconCache=self.mythChannelIconCache).doModal()
            
    @catchall_ui
    def onAction(self, action):
        id = action.getId()
        
        if id in (Action.PREVIOUS_MENU, Action.PARENT_DIR,):
            self.closed = True
            self.settings.put('upcoming_sort_by', self.sortBy)
            self.settings.put('upcoming_sort_ascending', '%s' % self.sortAscending)
            self.close()

        elif id in (Action.ACTION_NEXT_ITEM, Action.ACTION_PREV_ITEM,):  # bottom, top
            if self.lastFocusId == ID_PROGRAMS_LISTBOX:
                self.selectListItemAtIndex(self.programsListBox, [0, self.programsListBox.size()-1][id == Action.ACTION_NEXT_ITEM])

    @inject_db
    def cacheChannels(self):
        if self.channelsById is None:
            self.channelsById = dict([(c.getChannelId(),c) for c in self.db().getChannels()])

    @inject_db
    def cacheTuners(self):
        if self.tunersById is None:
            self.tunersById = dict([(t.tunerId, t) for t in self.db().getTuners()])
    
    @window_busy  
    def refresh(self):
        self.cacheChannels()
        self.cacheTuners()
        self.programs = self.domainCache.getUpcomingRecordings()
        self.applySort()
        
    @inject_conn
    @ui_locked
    def render(self):
        self.listItemsByProgram.clear()
        self.programsByListItem.clear()
        listItems = []
        
        log.debug('Rendering %d upcoming recordings...' % len(self.programs))
        
        @ui_locked2
        def buildListItems():
            previous = None
            for i, p in enumerate(self.programs):
                listItem = xbmcgui.ListItem()
                self.setListItemProperty(listItem, 'airdate', self.formattedAirDate(previous, p))    
                self.setListItemProperty(listItem, 'title', p.title())
                self.setListItemProperty(listItem, 'description', p.formattedDescription())
                self.setListItemProperty(listItem, 'category', p.category())
                self.setListItemProperty(listItem, 'startTime', p.formattedStartTime())
                self.setListItemProperty(listItem, 'duration', p.formattedDuration())
                self.setListItemProperty(listItem, 'channelName', p.getChannelName())
                self.setListItemProperty(listItem, 'channelNumber', p.getChannelNumber())
                self.setListItemProperty(listItem, 'callSign', p.getCallSign())
                self.setListItemProperty(listItem, 'poster', 'loading.gif')
                self.setListItemProperty(listItem, 'index', str(i + 1))
                
                tuner = self.tunersById[p.getTunerId()]
                self.setListItemProperty(listItem, 'tuner', '%s %s' % (tuner.tunerType, tuner.tunerId))
                
                listItems.append(listItem)
                self.listItemsByProgram[p] = listItem
                self.programsByListItem[listItem] = p
                previous = p

        buildListItems()
        self.programsListBox.reset()
        self.programsListBox.addItems(listItems)
        self.renderNav()
        
        self.activeRenderToken = time.clock()
        self.renderChannelIcons(self.activeRenderToken)
        self.renderPosters(self.activeRenderToken)        

    def renderNav(self):
        self.setWindowProperty('sortBy', self.translator.get(m.SORT) + ': ' + self.translator.get(SORT_BY[self.sortBy]['translation_id']))
        self.setWindowProperty('sortAscending', ['false', 'true'][self.sortAscending])
        
    @run_async
    @catchall
    def renderChannelIcons(self, myRenderToken):
        for i, (program, listItem) in enumerate(self.listItemsByProgram.items()[:]):
            if self.closed or xbmc.abortRequested or myRenderToken != self.activeRenderToken: 
                return
            channel = self.channelsById[program.getChannelId()]
            if channel and channel.getIconPath() and len(listItem.getProperty('airdate')) == 0:
                self.setListItemProperty(listItem, 'channelIcon', self.mythChannelIconCache.get(channel))
        
    @run_async
    @catchall
    def renderPosters(self, myRenderToken):
        for (program, listItem) in self.listItemsByProgram.items()[:]:
            if self.closed or xbmc.abortRequested or myRenderToken != self.activeRenderToken: 
                return
            posterPath = self.fanArt.pickPoster(program)
            if posterPath is None:
                if self.channelsById[program.getChannelId()].getIconPath():
                    posterPath = self.mythChannelIconCache.get(self.channelsById[program.getChannelId()])
                else:
                    posterPath = 'mythbox.png'
            self.setListItemProperty(listItem, 'poster', posterPath)

    def formattedAirDate(self, previous, current):
        result = u''
        airDate = current.starttimeAsTime().date()
        if not previous or previous.starttimeAsTime().date() != airDate:
            today = datetime.date.today()
            if airDate == today:
                result = self.translator.get(m.TODAY)
            elif today + ONE_DAY == airDate:
                result = self.translator.get(m.TOMORROW)
            else:
                result = datetime.date.strftime(airDate, '%a, %b %d')
        return result
