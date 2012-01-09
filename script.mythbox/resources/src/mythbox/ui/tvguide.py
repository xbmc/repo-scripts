#
#  MythBox for XBMC - http://mythbox.googlecode.com
#  Copyright (C) 2011 analogue@yahoo.com
#  Copyright (C) 2005 Tom Warkentin <tom@ixionstudios.com>
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

#  
# The inherited TVGuide code is a disaster. No amount of refactoring 
# will prove to be time well spent. Needs a complete rewrite...
#

import logging
import xbmc
import xbmcgui
import mythbox.msg as m
import mythbox.ui.toolkit as ui
import Queue

from datetime import datetime, timedelta
from mythbox.mythtv.conn import inject_conn
from mythbox.mythtv.db import inject_db
from mythbox.mythtv.domain import RecordingSchedule, Channel
from mythbox.mythtv.enums import Upcoming
from mythbox.ui.schedules import ScheduleDialog
from mythbox.ui.toolkit import Action, Align, AspectRatio, window_busy
from mythbox.util import catchall_ui, timed, catchall, safe_str, run_async
from mythbox.bus import Event

log = logging.getLogger('mythbox.ui')


class ProgramCell(object):
    
    def __init__(self, *args, **kwargs):
        self.chanid     = None   # string
        self.program    = None   # Program 
        self.nodata     = None   # boolean 
        self.starttime  = None   # ??? 
        self.title      = None   # string 
        self.start      = None   # int - starting x coordinate 
        self.end        = None   # int - ending x coord 
        self.control    = None   # ControlButton 
        self.label      = None   # ControlLabel
        self.hdOverlay  = None   # ControlImage
        self.scheduleId = None  # int


class ChannelCell(object):
    
    def __init__(self, *args, **kwargs):
        self.icon    = None   # ControlImage if channel has icon, otherwise None
        self.label   = None   # ControlLabel of channel name and callsign
        self.shade   = None   # ControlImage of background shade 


class Pager(object):
    
    def __init__(self, numChannels, channelsPerPage):
        self.nc = numChannels
        self.cpp = channelsPerPage
        
    def pageUp(self, currentPosition):
        pp = ((currentPosition // self.cpp) - 1)
        if pp == -1:
            pp = (self.nc // self.cpp)
            if (pp * self.cpp) >= self.nc:
                pp -=1
        return pp * self.cpp
        
    def pageDown(self, currentPosition):
        np = (currentPosition // self.cpp) + 1
        if np * self.cpp >= self.nc:
            np = 0
        return np * self.cpp


WIDTH_CHANNEL_ICON = 40


class TvGuideWindow(ui.BaseWindow):
    """
    @todo: Don't re-render channels when scrolling page left/right
    @todo: possible rendering optimizations - reuse widgets instead of creating them over and over
    """
    
    def __init__(self, *args, **kwargs):
        ui.BaseWindow.__init__(self, *args, **kwargs)
        [setattr(self,k,v) for k,v in kwargs.iteritems() if k in ('settings','translator','platform','fanArt','cachesByName', 'bus')]
        [setattr(self,k,v) for k,v in self.cachesByName.iteritems()]

        self._upcomingByProgram = None
        self._upcomingStale = True
        
        # =============================================================

        self.gridCells = []      # ProgramCell[] for grid of visible programs
        self.startTime = None    # datetime - start time for visibile grid
        self.endTime   = None    # datetime - end time for visible grid
        
        self.startChan = None    # int - index into channels[] of starting channel in visible grid
        self.endChan = None      # int - index info channels[] of ending channel in visible grid
        self.channelsPerPage = 8 # int - number of visible rows aka channels in grid 
        self.channels = None     # Channel[] for all tuners
        
        self.hoursPerPage = 2.0  # float - number of hours visible on grid
        self.channelCells = []   # ChannelCell[] for column visible channels
        self.timeLabels = []     # ControlLabel[] for row of visible time
        self.topCtls = []
        self.bottomCtls = []
        self.leftCtls = []
        self.rightCtls = []
        
        self.prevFocus = None       # gridCell.control aka button
        self.prevButtonInfo = None  # gridCell
        self.pager = None           # Pager
        self.initialized = False
        
        self.program = None         # currently focused
        self.bannerQueue = Queue.LifoQueue()
        self.episodeQueue = Queue.LifoQueue()
        self.episodeCache = {}
        self.bus.register(self)
        

    def onEvent(self, event):
        if event['id'] == Event.SCHEDULER_RAN:
            self._upcomingStale = True
            
    def upcomingByProgram(self):
        if self._upcomingStale:
            self._upcomingStale = False
            self._upcomingByProgram = {} 
            for p in self.domainCache.getUpcomingRecordings():
                self._upcomingByProgram[p] = p
        return self._upcomingByProgram
        
    @catchall_ui
    def onInit(self):
        log.debug('onInit')
        if self.win is None:
            self.win = xbmcgui.Window(xbmcgui.getCurrentWindowId())
            self.bannerThread()
            self.episodeThread()
            self.loadGuide()
            
    @catchall_ui
    @timed
    @inject_db
    @inject_conn
    def loadGuide(self):
        """
        Method to load and display the tv guide information.  If this is
        the first time being called, it initializes the tv guide
        parameters.
        """
        log.debug('Loading tv guide..')

        if self.prevFocus:
            for c in self.gridCells:
                if c.control == self.prevFocus:
                    self.prevButtonInfo = c
                    self.prevFocus = None
                    break

        if not self.initialized:
            self.channel_x = 60       
            self.channel_h = 40       
            self.channel_w = 340 - 120 + WIDTH_CHANNEL_ICON 
            self.channel_dx = 5       
            self.time_y = 140         
            self.time_h = 40          
            self.guide_x = 310        
            self.guide_dx = 12        
            self.guide_dy = 1         
            self.guide_y = self.time_y + self.time_h + self.guide_dy 
            self.guide_w = 1220 - 280 
            self.guide_h = 530 - 140 - self.time_h - self.guide_dy 

            # calculate pixels per hour used repeatedly
            self.widthPerHour = self.guide_w / self.hoursPerPage 

            # calculate channels per page based on guide height
            # self.channelsPerPage = int(self.guide_h / (self.guide_dy+self.channel_h) )
            log.debug("channelSpan=%d" % self.channelsPerPage)

            # allocate the remainder to vertical spacing between channels
            # TODO: Fix gaps betweek rows: 
            #remainder = self.guide_h // (self.guide_dy+self.channel_h)
            remainder = 0
            log.debug('remainder = ' + str(remainder))
            self.guide_dy += (remainder / self.channelsPerPage)

            # retrieve, consolidate, and sort channels
            self.channels = Channel.mergeChannels(self.domainCache.getChannels())
            self.channels.sort(key=Channel.getSortableChannelNumber)
            self.pager = Pager(len(self.channels), self.channelsPerPage)
            
            self.setChannel(int(self.settings.get('tv_guide_last_selected')))
            self.setTime(datetime.now() - timedelta(minutes=30))
            self.initialized = True

        self._render()

        if not self.prevButtonInfo:
            # set focus to the first control on the screen
            if len(self.gridCells) > 0:
                self.prevFocus = self.gridCells[0].control
                self.setFocus(self.prevFocus)
            else:
                raise Exception, self.translator.get(m.NO_EPG_DATA)

    @catchall_ui
    def onAction(self, action):
        log.debug('onAction %s', action.getId())
        #log.debug('Key got hit: %s   Current focus: %s' % (ui.toString(action), self.getFocusId()))
        
        if not self.initialized:
            return
        
        ctl = None
        try:
            ctl = self.getFocus()
        except:
            pass
        
        actionConsumed = False
        
        if action.getId() in Action.GO_BACK:
            self.closed = True
            self.settings.put('tv_guide_last_selected', '%s' % self.startChan)
            self.bus.deregister(self)
            self.close()
        elif action == Action.DOWN       : actionConsumed = self._checkPageDown(self.prevFocus)
        elif action == Action.UP         : actionConsumed = self._checkPageUp(self.prevFocus)
        elif action == Action.LEFT       : actionConsumed = self._checkPageLeft(self.prevFocus)
        elif action == Action.RIGHT      : actionConsumed = self._checkPageRight(self.prevFocus)
        elif action == Action.PAGE_UP    : self.scrollPreviousPage(); actionConsumed = True
        elif action == Action.PAGE_DOWN  : self.scrollNextPage(); actionConsumed = True
        elif action == Action.FORWARD    : self.scrollRightPage(); actionConsumed = True  # F on keyboard
        elif action == Action.REWIND     : self.scrollLeftPage(); actionConsumed = True   # R on keyboard
        elif action == Action.SELECT_ITEM: self.onControlHook(ctl) 
        else: log.debug('Unconsumed key: %s' % action.getId())

        if not actionConsumed and ctl:
            self.prevFocus = ctl

    def scrollPreviousPage(self):
        log.debug('scrollPreviousPage')
        self.setChannel(self.pager.pageUp(self.startChan))
        self.loadGuide()
        #self.prevFocus = self.gridCells[0].control
        self.setFocus(self.gridCells[0].control)
    
    def scrollNextPage(self):
        log.debug('scrollNextPage')
        self.setChannel(self.pager.pageDown(self.startChan))
        self.loadGuide()
        #self.prevFocus = self.gridCells[0].control
        self.setFocus(self.gridCells[0].control)
             
    def scrollRightPage(self, focusTopLeft=True):
        log.debug('scrollRightPage')
        self.setTime(self.startTime + timedelta(hours=self.hoursPerPage))
        self.loadGuide()
        if focusTopLeft:
            self.setFocus(self.gridCells[0].control)
    
    def scrollLeftPage(self, focusTopLeft=True):
        log.debug('scrollLeftPage')
        self.setTime(self.startTime - timedelta(hours=self.hoursPerPage))
        self.loadGuide()
        if focusTopLeft:
            self.setFocus(self.gridCells[0].control)
    
    @catchall
    def onFocus(self, controlId):
        log.debug('onFocus')
        if not self.initialized:
            return
        
        log.debug('lastfocusid = %s' % controlId)
        self.lastFocusId = controlId
        
        try:
            control = self.getControl(controlId)
            if isinstance(control, xbmcgui.ControlButton):
            #if self.cellsByButton.has_key(control):
                matches = filter(lambda c: c.control == control, self.gridCells)
                #cell = self.cellsByButton[control]
                if matches:
                    self.renderProgramInfo(matches[0].program)
        except TypeError, te:
            if 'Non-Existent Control' in str(te):
                log.warn('onFocus: ' + str(te))
            else:
                raise

    def renderEpisode(self, program):
        cached = self.episodeCache.get(program, None)
        if cached is None:
            self.setWindowProperty('seasonAndEpisode', u'...')
            self.episodeQueue.put(program)
        else:
            season, episode = cached
            self.setWindowProperty('seasonAndEpisode', [u'-', u'%sx%s' % (season, episode)][bool(season) and bool(episode)])
 
    def renderProgramInfo(self, program):
        self.program = program
        if program:
            log.debug('Show info for ' + safe_str(program.title()))
            self.setWindowProperty('title', program.fullTitle())
            self.setWindowProperty('category', program.category())
            self.setWindowProperty('description', program.description())
            self.setWindowProperty('subtitle', program.subtitle())
            self.setWindowProperty('airtime', program.formattedAirTime())
            self.setWindowProperty('duration', program.formattedDuration())
            self.setWindowProperty('originalAirDate', program.formattedOriginalAirDate())

            self.renderEpisode(program)
                
            self.setWindowProperty('banner', u'')
            self.bannerQueue.put(program)
        else:
            self.setWindowProperty('title', u'')
            self.setWindowProperty('category', u'')
            self.setWindowProperty('description', u'')
            self.setWindowProperty('subtitle', u'')
            self.setWindowProperty('airtime', u'')
            self.setWindowProperty('duration', u'')
            self.setWindowProperty('originalAirDate', u'')
            self.setWindowProperty('banner', u'')
            self.setWindowProperty('seasonAndEpisode', u'')

    @run_async
    def bannerThread(self):
        while not self.closed and not xbmc.abortRequested:
            try:
                if not self.bannerQueue.empty():
                    log.debug('Banner queue size: %d' % self.bannerQueue.qsize())
                program = self.bannerQueue.get(block=True, timeout=1)
                
                try:
                    bannerPath = self.fanArt.pickBanner(program)
                    if program == self.program:
                        self.setWindowProperty('banner', [u'',bannerPath][bannerPath is not None])
                except:
                    # don't let failures affect queue processing
                    log.exception('bannerThread')
            except Queue.Empty:
                pass

    @run_async
    def episodeThread(self):
        while not self.closed and not xbmc.abortRequested:
            try:
                if not self.episodeQueue.empty():
                    log.debug('Episode queue size: %d' % self.episodeQueue.qsize())
                program = self.episodeQueue.get(block=True, timeout=1)
                try:
                    season, episode = self.fanArt.getSeasonAndEpisode(program)
                    self.episodeCache[program] = (season, episode)
                    if program == self.program:
                        self.renderEpisode(program)
                except:
                    # don't let failures affect queue processing
                    log.exception('episodeThread')
            except Queue.Empty:
                pass

    @window_busy
    @inject_conn
    def watchLiveTv(self, program):

        if not self.conn().protocol.supportsStreaming(self.platform):
            xbmcgui.Dialog().ok(self.translator.get(m.ERROR), 
                'Watching Live TV is currently not supported', 
                'with your configuration of MythTV %s and' % self.conn().protocol.mythVersion(), 
                'XBMC %s. Should be working in XBMC 11.0+' % self.platform.xbmcVersion())
            return
        
        channel = filter(lambda c: c.getChannelId() == program.getChannelId(), self.channels).pop()
        brain = self.conn().protocol.getLiveTvBrain(self.settings, self.translator)
        try:
            brain.watchLiveTV(channel)
        except Exception, e:
            log.exception(e)
            xbmcgui.Dialog().ok(self.translator.get(m.ERROR), '', str(e))
            
    @catchall_ui
    @inject_db
    def onControlHook(self, control):
        actionConsumed = True
        
        id = control.getId()
        program = None
        for c in self.gridCells:
            if c.control == control:
                program = c.program
                break
        
        if program:
            if program.isShowing():
                log.debug('launching livetv')
                self.watchLiveTv(program)
            else:
                log.debug('launching edit schedule dialog')
                
                # scheduled recording
                if c.scheduleId:
                    schedule = self.db().getRecordingSchedules(scheduleId=c.scheduleId).pop()
                
                # not scheduled but happens to have an existing recording schedule
                schedule = self.scheduleForTitle(program)

                # new recording schedule
                if schedule is None:
                    schedule = RecordingSchedule.fromProgram(program, self.translator)
                
                d = ScheduleDialog(
                    'mythbox_schedule_dialog.xml',
                    self.platform.getScriptDir(),
                    forceFallback=True,
                    schedule=schedule,
                    translator=self.translator,
                    platform=self.platform,
                    settings=self.settings,
                    mythChannelIconCache=self.mythChannelIconCache)
                d.doModal()

        return actionConsumed

    def scheduleForTitle(self, program):
        for schedule in self.domainCache.getRecordingSchedules():
            if schedule.title() == program.title():
                return schedule
        return None

    def _addGridCell(self, program, cell, relX, relY, width, height):
        """ 
        Adds a control (button overlayed with a label) for a program in the guide
        
        @param program: Program
        @param cell: dict with keys ('chanid')
        @param relX: relative x position as int
        @param relY: relative y position as int
        @return: ControlLabel created for the passed in program and cell.
        @postcondition: cell[] keys are
            'chanid'    is ???, 
            'program'   is Program, 
            'nodata'    is boolean, 
            'starttime' is ???, 
            'title'     is string, 
            'start'     is int starting x coord, 
            'end'       is int ending x coord, 
            'control'   is ControlButton, 
            'label'     is ControlLabel
        """
        cell.program = program
        
        if program is None:
            cell.nodata = True
            cell.starttime = None
            cell.title = self.translator.get(m.NO_DATA)
            category = None
        else:
            cell.nodata = False
            cell.starttime = program.starttime()
            cell.title = program.title()
            category = program.category()
            
        cell.start = relX
        cell.end = relX + width
        
        # Create a button for navigation and hilighting. For some reason, button labels don't get truncated properly.
        cell.control = xbmcgui.ControlButton(
            int(relX + self.guide_x), 
            int(relY + self.guide_y), 
            int(width-2),       # hack for cell dividers 
            int(height), 
            label='',      # Text empty on purpose. Label overlay responsible for this
            focusTexture=self.platform.getMediaPath('gradient_cell.png'),
            noFocusTexture=self.platform.getMediaPath('gradient_grid.png'),
            alignment=Align.CENTER_Y|Align.TRUNCATED)

        if program in self.upcomingByProgram():
            cell.title = '[B][COLOR=ffe2ff43]' + cell.title + '[/COLOR][/B]'
            cell.scheduleId = self.upcomingByProgram()[program].getScheduleId()
        
        # Create a label to hold the name of the program with insets  
        # Label text seems to get truncated correctly...
        cell.label = xbmcgui.ControlLabel(
            int(relX + self.guide_x + 12), # indent 12 px for bumper 
            int(relY + self.guide_y), 
            int(width - 12 - 12),          # reverse-indent 12px for bumper
            int(height),
            cell.title,
            font='font11',
            alignment=Align.CENTER_Y|Align.TRUNCATED)

        self.addControl(cell.control)
        self.addControl(cell.label)

        if program and program.isHD() and width > 50:
            overlayWidth = 40
            overlayHeight = 15
            cell.hdOverlay = xbmcgui.ControlImage(
                int(relX + self.guide_x + width - overlayWidth - 5), 
                int(relY + self.guide_y + 2), 
                overlayWidth, 
                overlayHeight, 
                self.platform.getMediaPath('OverlayHD.png'),
                aspectRatio=1)
            self.addControl(cell.hdOverlay)
        
        self.gridCells.append(cell)

    def _checkPageUp(self, focusControl):
        paged = False
        if focusControl in self.topCtls:
            log.debug('page up detected')
            paged = True
            self.scrollPreviousPage()

            # check if we need to fix focus
            if not self.prevFocus:
                # find the control in the bottom row where previous button's
                # start falls within start/end range of control
                chanid = self.gridCells[-1].chanid
                start = self.prevButtonInfo.start
                for c in reversed(self.gridCells):
                    if chanid == c.chanid:
                        if start >= c.start and start < c.end:
                            self.prevFocus = c.control
                            self.setFocus(self.prevFocus)
                            break
                    else:
                        break
        return paged

    def _checkPageDown(self, focusControl):
        paged = False
        if focusControl in self.bottomCtls:
            log.debug('page down detected')
            paged = True
            self.scrollNextPage()

            # check if we need to fix focus
            if not self.prevFocus:
                # find the control in the top row where previous button's start
                # falls within start/end range of control
                chanid = self.gridCells[0].chanid
                start = self.prevButtonInfo.start
                for c in self.gridCells:
                    if chanid == c.chanid:
                        if start >= c.start and start < c.end:
                            self.prevFocus = c.control
                            self.setFocus(self.prevFocus)
                            break
                    else:
                        break
        return paged

    def _checkPageLeft(self, focusControl):
        paged = False
        if focusControl in self.leftCtls:
            log.debug("page left detected")
            paged = True
            self.scrollLeftPage(focusTopLeft=False)

            # check if we need to fix focus
            if not self.prevFocus:
                chanid = self.prevButtonInfo.chanid
                found = False
                prev = None
                # find the right most program on the same channel
                for c in self.gridCells:
                    if not found and c.chanid == chanid:
                        found = True
                    elif found and c.chanid != chanid:
                        break
                    prev = c
                self.prevFocus = prev.control
                self.setFocus(self.prevFocus)
                self.prevButtonInfo = None
        return paged

    def _checkPageRight(self, focusControl):
        paged = False
        if focusControl in self.rightCtls:
            log.debug('page right detected')
            paged = True
            self.scrollRightPage(focusTopLeft=False)

            # check if we need to fix focus
            if not self.prevFocus:
                chanid = self.prevButtonInfo.chanid
                found = False
                prev = None
                # find the left most program on the same channel
                for c in reversed(self.gridCells):
                    if not found and c.chanid == chanid:
                        found = True
                    elif found and c.chanid != chanid:
                        break
                    prev = c
                self.prevFocus = prev.control
                self.setFocus(self.prevFocus)
                self.prevButtonInfo = None
        return paged

    def _doNavigation(self):
        """
        Method to do navigation between controls and store lists of top,
        bottom, left, and right controls to detect when page changes must
        occur.
        """
        count = 0
        self.topCtls = []
        self.bottomCtls = []
        self.leftCtls = []
        self.rightCtls = []
        topChanId = None
        prevChanId = None
        prevCtl = None
        
        #
        # Loop through all buttons doing left to right, right to left, and
        # top to bottom navigation. Also keep track of top, left, and right
        # controls that are used to detect page up, left, and right.
        #
        log.debug('Gridcell cnt1 = %s' % len(self.gridCells))
        
        for c in self.gridCells:
            
            #log.debug("title=%s"%c.title)
            if not topChanId:
                topChanId = c.chanid
                
            if c.chanid == topChanId:
                # first row of controls are top controls
                self.topCtls.append(c.control)
                #log.debug("top ctl=%s"%c.control)

            # do left to right and right to left navigation
            if not prevChanId:
                prevChanId = c.chanid
            elif prevChanId != c.chanid:
                # changed channel rows so previous control is a control on right edge
                self.rightCtls.append(prevCtl)
                prevCtl = None
                prevChanId = c.chanid
                
            if prevCtl:
                prevCtl.controlRight(c.control)
                c.control.controlLeft(prevCtl)
                prevCtl = c.control
                
            if not prevCtl:
                # control not set so this must be a control on left edge
                self.leftCtls.append(c.control)
                prevCtl = c.control

            # now find the appropriate control below current one
            chanid = None
            found = False
            for c2 in self.gridCells:
                if not found and c2.control == c.control:
                    found = True
                elif found and not chanid and c2.chanid != c.chanid:
                    chanid = c2.chanid
                    
                if found and chanid and chanid == c2.chanid:
                    if c.start >= c2.start and c.start < c2.end:
                        c.control.controlDown(c2.control)
                        #log.debug("%s VVV %s"%(c.title, c2.title))
                        count += 1
                        break
                elif found and chanid and chanid != c2.chanid:
                    break
                
        log.debug("down count=%d"%count)
        count = 0
        
        log.debug('Gridcell cnt2 = %s' % len(self.gridCells))
        #cells = list(self.gridCells)
        #cells = cells.reverse()
        bottomChanId = None

        #log.debug('Gridcell cnt3 = %s' % len(cells))
        
        #
        # Loop through all buttons in reverse to do bottom to top navigation.
        #
        for c in reversed(self.gridCells):
            
            #log.debug("title=%s"%c.title)
            if not bottomChanId:
                bottomChanId = c.chanid
                
            if c.chanid == bottomChanId:
                # first row of controls are bottom controls
                self.bottomCtls.append(c.control)
                #log.debug("bottom ctl=%s"%c.control)

            # now find the control that is above the current one
            chanid = None
            found = False
            
            for c2 in reversed(self.gridCells):
                if not found and c2.control == c.control:
                    found = True
                elif found and not chanid and c2.chanid != c.chanid:
                    chanid = c2.chanid
                    
                if found and chanid and chanid == c2.chanid:
                    if c.start >= c2.start and c.start < c2.end:
                        c.control.controlUp(c2.control)
                        #log.debug("%s ^^^ %s"%(c.title, c2.title))
                        count += 1
                        break
                elif found and chanid and chanid != c2.chanid:
                    break
        log.debug( "up count=%d"%count )

        # if we have any controls, then the very last control on right edge
        # was missed in first loop (right controls are detected by row changes
        # but the last row quits the loop before detecting the control)
        if len(self.gridCells) > 0:
            # Note: This grabs last control from the reverse list of controls.
            self.rightCtls.append(self.gridCells[-1].control)
        #log.debug("right ctl=%s"%cells[0].control)

        log.debug("top count    = %d" % len(self.topCtls))
        log.debug("bottom count = %d" % len(self.bottomCtls))
        log.debug("left count   = %d" % len(self.leftCtls))
        log.debug("right count  = %d" % len(self.rightCtls))

    def _render(self):
        """
        Method to draw all the dynamic controls that represent the program
        guide information.
        """
        self.renderChannels()
        self.renderHeader()
        self._renderPrograms()
        self._doNavigation()

    def renderChannels(self):
        
        # deallocate current channel cells
        for c in self.channelCells:
            if c.icon:  self.removeControl(c.icon)
            if c.label: self.removeControl(c.label)
            if c.shade: self.removeControl(c.shade)
            del c
        
        self.channelCells = []
        
        x = self.channel_x
        y = self.guide_y
        h = (self.guide_h - self.channelsPerPage * self.guide_dy) / self.channelsPerPage
        iconW = h
        labelW = self.channel_w - iconW - self.guide_dx
        
        for i in range(self.startChan, self.endChan + 1):
            c = ChannelCell()
            
            # create shade image around channel label/icon
            #c.shade = xbmcgui.ControlImage(
            #    x, 
            #    y, 
            #    self.channel_w, 
            #    h, 
            #    "shade_50.png")
            #
            #self.addControl(c.shade)

            # create label control
            labelText = '%s %s' % (self.channels[i].getChannelNumber(), '') # self.channels[i].getCallSign())
            label2Text = '%s' % self.channels[i].getCallSign()
            #label2Text = "%s" % self.channels[i].getChannelName()
            
            c.label = xbmcgui.ControlButton(
                x + iconW + self.channel_dx, 
                y, 
                labelW,        # hack for cell dividers 
                h, 
                label=labelText,      # Text empty on purpose. Label overlay responsible for this
                #focusTexture=self.platform.getMediaPath('gradient_maroon.png'),
                noFocusTexture=self.platform.getMediaPath('gradient_channel.png'),
                #textXOffset=2,
                #textYOffset=0,
                alignment=Align.CENTER_Y|Align.TRUNCATED)
            
            c.label.setLabel(label=labelText, label2=label2Text)
            self.addControl(c.label)

            # create channel icon image if icon exists
            try:
                if self.channels[i].getIconPath():
                    iconFile = self.mythChannelIconCache.get(self.channels[i])
                    if iconFile:
                        hackW = iconW * 2
                        c.icon = xbmcgui.ControlImage(x + self.channel_w - hackW - 15, y, hackW, h, iconFile, AspectRatio.SCALE_DOWN)
                        c.label.setLabel(label=labelText, label2='')
                        self.addControl(c.icon)
            except:
                log.exception('channel = %s' % self.channels[i])
            
            self.channelCells.append(c)
            y += h + self.guide_dy
    
    @timed
    @inject_db
    def _renderPrograms(self):
        """
        Method to draw the program buttons.  Also manufactures buttons for missing guide data.
        """
        programs = self.db().getTVGuideDataFlattened(self.startTime, self.endTime, self.channels[self.startChan : self.endChan + 1])
        log.debug("Num programs = %s" % len(programs))

        # dealloc existing grid cells...
        for cell in self.gridCells:
            self.removeControl(cell.control)
            del cell.control
            self.removeControl(cell.label)
            del cell.label
            if cell.hdOverlay:
                self.removeControl(cell.hdOverlay)
            del cell
                
        self.gridCells = []

        self.widthPerHour = self.guide_w / self.hoursPerPage 
        chanH = (self.guide_h - self.channelsPerPage * self.guide_dy) / self.channelsPerPage

        # Loop through each channel filling the tv guide area with cells.
        for i in range(self.startChan, self.endChan + 1):
            noData = False
            chanX = 0
            chanY = (i - self.startChan) * (chanH + self.guide_dy)
            chanid = self.channels[i].getChannelId()
        
            # loop until we've filled the row for the channel
            while chanX < self.guide_w:
                cell = ProgramCell()
                cell.chanid = chanid
                p = None
                if not noData:
                    # find the next program for the channel - this assumes
                    # programs are sorted in ascending time order for the channel
                    for prog in programs:
                        if prog.getChannelId() == chanid:
                            p = prog
                            programs.remove(prog)
                            break
                if not p:
                    # no program found - create a no data control for the rest of the row
                    noData = True
                    w = self.guide_w - chanX
                    self._addGridCell(
                        program=None,
                        cell=cell, 
                        relX=chanX, 
                        relY=chanY, 
                        width=w, 
                        height=chanH)
                    chanX += w
                else:
                    # found a program but we don't know if it starts at the current spot in the row for the channel

                    # trunc start time
                    start = p.starttimeAsTime()
                    if start < self.startTime:
                        start = self.startTime

                    # trunc end time
                    end = p.endtimeAsTime()
                    if end > self.endTime:
                        end = self.endTime

                    # calculate x coord and width of label
                    start = start - self.startTime
                    progX = start.seconds / (60.0*60.0) * self.widthPerHour
                    
                    end = end - self.startTime
                    progEndX = end.seconds / (60.0*60.0) * self.widthPerHour
                    progW = progEndX - progX

                    #log.debug("cell startx=%s endx=%s"%(start,end))
                    
                    # check if we need a 'No data' spacer before this cell 
                    if progX != chanX:
                        self._addGridCell(
                            program=None,
                            cell=cell,    # TODO: Doesn't make sense why setting info for 'no data' cell to cell
                            relX=chanX, 
                            relY=chanY,
                            width=(progX - chanX), 
                            height=chanH)
                        
                        chanX = progX
                        cell = ProgramCell()
                        cell.chanid = chanid

                    # add the control for the program
                    self._addGridCell(
                        program=p,
                        cell=cell,
                        relX=progX, 
                        relY=chanY, 
                        width=progW, 
                        height=chanH)
                    
                    chanX += progW

    def renderHeader(self):
        numCols = int(self.hoursPerPage * 2)
        x = self.guide_x
        y = self.time_y
        h = self.time_h
        w = (self.guide_w - numCols * self.guide_dx) / numCols
        t = self.startTime
        lastDay = t.day
        i = 0
        log.debug("numCols=%d guide_w=%d"%(numCols, self.guide_w))

        if len(self.timeLabels) == 0:
            c = xbmcgui.ControlButton(
                self.channel_x + self.channel_dx + WIDTH_CHANNEL_ICON + 2, 
                y, 
                self.channel_w - self.channel_dx - WIDTH_CHANNEL_ICON - 14, 
                h, 
                label='', 
                font='font13', 
                noFocusTexture=self.platform.getMediaPath('gradient_header.png'))
            self.timeLabels.append(c)
            self.addControl(c)
                                                  
            for i in xrange(numCols):
                c = xbmcgui.ControlButton(
                    x, y, w+10, h, label='', 
                    font='font13', 
                    noFocusTexture=self.platform.getMediaPath('gradient_header.png'))
                self.timeLabels.append(c)
                self.addControl(c)
                x = x + w + self.guide_dx
                
        for i,c in enumerate(self.timeLabels):
            if i == 0:
                c.setLabel(label='', label2=t.strftime('%a %m/%d'))
            else: 
                label = ('%d' % int(t.strftime('%I'))) + t.strftime(':%M %p') 
                if t.day != lastDay:
                    label += '+1'
                t += timedelta(minutes=30)
                lastDay = t.day
                c.setLabel(label)
        
    def setTime(self, startTime):
        """
        Method to change the starting time of the tv guide.  This is used
        to change pages horizontally.
        """
        self.startTime = startTime - timedelta(seconds=startTime.second, microseconds=startTime.microsecond)
        min = self.startTime.minute
        if min != 0:
            if min > 30:
                delta = 60 - min
            else:
                delta = 30 - min
            self.startTime = self.startTime + timedelta(minutes=delta)
        self.endTime = self.startTime + timedelta(hours=self.hoursPerPage)
        log.debug("startTime = %s endTime = %s" % (self.startTime, self.endTime))
        
    def setChannel(self, chanIndex):
        """
        Method to change the starting channel index of the tv guide.
        This is used to change pages vertically.
        """
        self.startChan = chanIndex
        if self.startChan < 0 or self.startChan > len(self.channels)-1:
            self.startChan = 0
        self.endChan = self.startChan + self.channelsPerPage - 1
        if self.endChan > len(self.channels)-1:
            self.endChan = len(self.channels)-1
        log.debug("start channels[%d] = %s" % (self.startChan, self.channels[self.startChan].getChannelNumber()))
        log.debug("end   channels[%d] = %s" % (self.endChan, self.channels[self.endChan].getChannelNumber()))
        