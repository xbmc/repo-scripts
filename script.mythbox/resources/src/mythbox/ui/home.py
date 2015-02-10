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
import logging
import xbmc
import xbmcgui
import mythbox.msg as m

from mythbox import pool
from mythbox.bus import Event
from mythbox.mythtv.db import MythDatabaseFactory
from mythbox.mythtv.domain import StatusException
from mythbox.mythtv.enums import JobStatus, JobType
from mythbox.mythtv.conn import inject_conn, inject_db, ConnectionFactory
from mythbox.settings import SettingsException
from mythbox.ui.player import MountedPlayer, TrackingCommercialSkipper,\
    StreamingPlayer, NoOpCommercialSkipper
from mythbox.ui.toolkit import BaseWindow, Action, window_busy, showPopup
from mythbox.util import catchall_ui, catchall, run_async, coalesce, safe_str 
from mythbox.util import hasPendingWorkers, waitForWorkersToDie, formatSize, to_kwargs
from mythbox.mythtv.publish import MythEventPublisher

log = logging.getLogger('mythbox.ui')

ID_COVERFLOW_GROUP    = 499
ID_COVERFLOW_WRAPLIST = 500
ID_COVERFLOW_POPUP    = 300
MAX_COVERFLOW         = 6


class HomeWindow(BaseWindow):
    
    def __init__(self, *args, **kwargs):
        BaseWindow.__init__(self, *args, **kwargs)
        [setattr(self,k,v) for k,v in kwargs.iteritems() if k in ('settings', 'translator', 'platform', 'fanArt', 'cachesByName', 'bus', 'feedHose',)]
        [setattr(self,k,v) for k,v in self.cachesByName.iteritems() if k in ('mythChannelIconCache', 'mythThumbnailCache', 'httpCache', 'domainCache')]

        # merge cachesByName into deps dict
        self.deps = dict(kwargs.items() + self.cachesByName.items())
        self.t = self.translator.get
        self.lastFocusId = None
        self.shutdownPending = False
        self.bus.register(self)
        
    def onFocus(self, controlId):
        log.debug('lastfocusid = %s' % controlId)
        self.lastFocusId = controlId
    
    @catchall_ui
    def onInit(self):
        if not self.win:
            self.win = xbmcgui.Window(xbmcgui.getCurrentWindowId())
            self.tunersListBox = self.getControl(249)
            self.jobsListBox = self.getControl(248)
            self.coverFlow = self.getControl(ID_COVERFLOW_WRAPLIST)
            self.coverFlowPopup = self.getControl(ID_COVERFLOW_POPUP)
            
            # button ids -> funtion ptr
            self.dispatcher = {
                250 : self.goWatchRecordings,
                251 : self.goWatchTv,
                252 : self.goTvGuide,
                253 : self.goRecordingSchedules,
                254 : self.goUpcomingRecordings,
                256 : self.goSettings,
                255 : self.refreshOnInit,
                301 : self.deleteRecording,
                302 : self.rerecordRecording,
                ID_COVERFLOW_WRAPLIST : self.goPlayRecording
            }
            
            self.initCoverFlow()
            self.startup()
            self.refreshOnInit()
        else:
            self.refresh()
   
    def initCoverFlow(self):
        coverItems = []
        for _ in range(MAX_COVERFLOW):
            coverItem = xbmcgui.ListItem(iconImage='loading.gif', thumbnailImage='loading.gif')
            self.updateListItemProperty(coverItem, 'thumb', 'loading.gif')
            coverItems.append(coverItem)
        self.coverFlow.addItems(coverItems)
   
    def isCoverFlowPopupActive(self):
        buttonIds = [ID_COVERFLOW_POPUP,301,302]
        return self.getFocusId() in buttonIds
    
    @catchall_ui
    def onAction(self, action):
        if self.shutdownPending:
            return
        
        id = action.getId()
        
        if id in Action.GO_BACK:
            if self.isCoverFlowPopupActive():
                self.setFocus(self.coverFlow)
            else:
                self.shutdown()
                self.close()
        
        elif id == Action.CONTEXT_MENU and self.lastFocusId in (ID_COVERFLOW_GROUP, ID_COVERFLOW_WRAPLIST):
            self.setFocus(self.coverFlowPopup)
            
        #elif id == Action.DOWN and self.lastFocusId == ID_COVERFLOW_WRAPLIST:
        #    log.debug('activate popup menu') 
        
        else:
            pass #log.debug('Unhandled action: %s  lastFocusId = %s' % (id, self.lastFocusId))

    @window_busy
    @inject_conn
    def deleteRecording(self):
        yes = True
        if self.settings.isConfirmOnDelete():
            yes = xbmcgui.Dialog().yesno(self.t(m.CONFIRMATION), self.t(m.ASK_DELETE_RECORDING))
            
        if yes:
            program = self.recordings[self.coverFlow.getSelectedPosition()]
            self.conn().deleteRecording(program)

    @window_busy
    @inject_conn
    def rerecordRecording(self):
        yes = True
        if self.settings.isConfirmOnDelete():
            yes = xbmcgui.Dialog().yesno(self.t(m.CONFIRMATION), self.t(m.ASK_RERECORD_RECORDING))
            
        if yes:
            program = self.recordings[self.coverFlow.getSelectedPosition()]
            self.conn().rerecordRecording(program)

    @catchall_ui
    def onClick(self, controlId):
        try:
            self.dispatcher[controlId]()
        except KeyError:
            log.exception('onClick')
   
    @window_busy
    def startup(self):
        """
        @return: True if startup successful, False otherwise
        """
        self.settingsOK = False
        try:
            self.settings.verify()
            self.settingsOK = True
        except SettingsException, se:
            showPopup(self.t(m.ERROR), safe_str(se), 7000)
            self.goSettings()
            try:
                self.settings.verify() # TODO: optimize unnecessary re-verify
                self.settingsOK = True
            except SettingsException:
                self.shutdown()
                self.close()
                return False
            
        if self.settingsOK:
            pool.pools['dbPool'] = pool.EvictingPool(MythDatabaseFactory(**self.deps), maxAgeSecs=10*60, reapEverySecs=10)
            pool.pools['connPool'] = pool.Pool(ConnectionFactory(**self.deps))
            
            self.dumpBackendInfo()
            
            self.publisher = MythEventPublisher(**self.deps)
            self.publisher.startup()
            
            self.mythThumbnailCache.reap()

            
        return self.settingsOK
        
    @inject_db
    def dumpBackendInfo(self):
        backends = [self.db().getMasterBackend()]
        backends.extend(self.db().getSlaveBackends())
        log.info('Backend info')
        for b in backends:
            log.info('\t' + str(b))
            
    def shutdown(self):
        if self.shutdownPending:
            xbmc.log("Mythbox shutdown already in progress...")
            return
        
        self.shutdownPending = True
        self.setBusy(True)
        self.bus.deregister(self)
        try:
            self.settings.save()
        except:
            log.exception('Saving settings on exit')

        xbmc.log('Before fanart shutdown')
        self.fanArt.shutdown()
        
        xbmc.log('Before bus.publish')
        self.bus.publish({'id':Event.SHUTDOWN})
        
        try:
            self.publisher.shutdown()
        except:
            log.exception('shutting down publisher')
            
        xbmc.log('Before reaping')
        
        try:
            # HACK ALERT:
            #   Pool reaper thread is @run_async so we need to 
            #   allow it to die before we start waiting for the 
            #   worker threads to exit in waitForWorkersToDie(). 
            #   pool.shutdown() is the normal way to do it but we can't shut
            #   down the pools until theads (which may have 
            #   refs to pooled resources) have all exited.
            #   
            # TODO: 
            #   Fix is to refactor EvictingPool to not use
            #   the @run_async decorator
            
            #for (poolName, poolInstance) in pool.pools.items():
            #    poolInstance.stopReaping = True
            pool.pools['dbPool'].stopReaping = True
            
            if hasPendingWorkers():
                waitForWorkersToDie(30.0) # in seconds
        except:
            log.exception('Waiting for worker threads to die')

        xbmc.log('Before pools')
        try:
            # print pool stats and shutdown
            for (poolName, poolInstance) in pool.pools.items():
                log.info('Pool %s: available = %d  size = %d' % (poolName, poolInstance.available(), poolInstance.size()))
                poolInstance.shutdown()
        except:
            log.exception('Error while shutting down')

        xbmc.log('Before logging shutdown')
        try:
            log.info('Goodbye!')
            logging.shutdown()
        except Exception, e:
            xbmc.log('%s' % str(e))            
        
    def goWatchTv(self):
        from mythbox.ui.livetv import LiveTvWindow 
        LiveTvWindow('mythbox_livetv.xml', self.platform.getScriptDir(), **self.deps).doModal()

    @inject_conn
    def canStream(self):
        # TODO: Merge with duplicate method in RecordingDetailsWindow
        if not self.conn().protocol.supportsStreaming(self.platform):
            xbmcgui.Dialog().ok(self.t(m.ERROR), 
                'Streaming from a MythTV %s backend to XBMC' % self.conn().protocol.mythVersion(), 
                '%s is broken. Try playing again after deselecting' % self.platform.xbmcVersion(),
                'MythBox > Settings > MythTV > Enable Streaming')
            return False
        return True

    @window_busy
    def goPlayRecording(self):
        program=self.recordings[self.coverFlow.getSelectedPosition()]
        
        if self.settings.getBoolean('streaming_enabled'):
            if not self.canStream():
                return 
            p = StreamingPlayer(program=program, **to_kwargs(self, ['settings', 'mythThumbnailCache', 'translator', 'platform']))
            p.playRecording(NoOpCommercialSkipper())
        else:    
            p = MountedPlayer(program=program, **to_kwargs(self, ['mythThumbnailCache', 'translator', 'platform']))
            p.playRecording(TrackingCommercialSkipper(p, program, self.translator))
        del p
            
    def goWatchRecordings(self):
        from mythbox.ui.recordings import RecordingsWindow
        RecordingsWindow('mythbox_recordings.xml', self.platform.getScriptDir(), **self.deps).doModal()
        
    def goTvGuide(self):
        from tvguide import TvGuideWindow 
        TvGuideWindow('mythbox_tvguide.xml', self.platform.getScriptDir(), **self.deps).doModal() 
    
    def goRecordingSchedules(self):
        from schedules import SchedulesWindow 
        SchedulesWindow('mythbox_schedules.xml', self.platform.getScriptDir(), **self.deps).doModal()
            
    def goUpcomingRecordings(self):
        from upcoming import UpcomingRecordingsWindow
        UpcomingRecordingsWindow('mythbox_upcoming.xml', self.platform.getScriptDir(), **self.deps).doModal()
        
    def goSettings(self):
        from uisettings import SettingsWindow
        SettingsWindow('mythbox_settings.xml', self.platform.getScriptDir(), **self.deps).doModal() 

    @window_busy
    def refresh(self):
        if self.settingsOK:
            self.renderTuners()
            self.renderJobs()
            self.renderStats()

    @window_busy
    def refreshOnInit(self):
        if self.settingsOK:
            #self.initCoverFlow()
            self.renderTuners()
            self.renderJobs()
            self.renderStats()
            self.renderCoverFlow()
            self.renderNewsFeed()
            
    @run_async
    @catchall
    @inject_conn
    @coalesce
    def renderCoverFlow(self, exclude=None):
        log.debug('>>> renderCoverFlow begin')
        self.recordings = self.conn().getAllRecordings()
        
        if exclude:
            try:
                self.recordings.remove(exclude)
            except:
                pass
        
        self.coverItems = []
            
        for i, r in enumerate(self.recordings[:MAX_COVERFLOW]):
            log.debug('Coverflow %d/%d: %s' % (i+1, MAX_COVERFLOW, safe_str(r.title())))
            listItem = xbmcgui.ListItem() 
            self.setListItemProperty(listItem, 'title', r.title())
            self.setListItemProperty(listItem, 'description', r.description())
            
            cover = self.fanArt.pickPoster(r)
            if not cover:
                cover = self.mythThumbnailCache.get(r)
                if not cover:
                    cover = 'mythbox-logo.png'
            self.updateListItemProperty(listItem, 'thumb', cover)
            self.coverItems.append(listItem)

        # NOTE: apparently, updating listitem properties broke in eden creating dupes.
        #       reset as a workaround for the time being.
        self.coverFlow.reset()
        self.coverFlow.addItems(self.coverItems)
        log.debug('<<< renderCoverFlow end')
        
    @run_async
    @catchall
    @coalesce
    def renderTuners(self):
        tuners = self.domainCache.getTuners()
        
        for t in tuners:
            t.listItem = xbmcgui.ListItem()
            self.setListItemProperty(t.listItem, 'tuner', '%s %s' % (t.tunerType, t.tunerId))
            self.setListItemProperty(t.listItem, 'hostname', t.hostname)
            self.setListItemProperty(t.listItem, 'status', t.formattedTunerStatus())

        if len(tuners) > 2:    
            
            def nextToRecordFirst(t1, t2):
                r1 = t1.getNextScheduledRecording()
                r2 = t2.getNextScheduledRecording()
                
                if not r1 or not r2:
                    return 0
                elif r1 and not r2:
                    return 1
                elif not r1 and r2:
                    return -1
                else:
                    return cmp(r1.starttimeAsTime(), r2.starttimeAsTime())
                
            def idleTunersLast(t1, t2):
                t1Idle = t1.listItem.getProperty('status').startswith(self.t(m.IDLE))
                t2Idle = t2.listItem.getProperty('status').startswith(self.t(m.IDLE))

                if t1Idle and t2Idle:
                    return nextToRecordFirst(t1,t2)
                elif t1Idle and not t2Idle:
                    return 1
                elif not t1Idle and t2Idle:
                    return -1
                else:
                    return cmp(t1.listItem.getProperty('tuner'), t2.listItem.getProperty('tuner'))            

            tuners.sort(idleTunersLast)

        self.tunersListBox.addItems(map(lambda t: t.listItem, tuners))

    @run_async
    @catchall
    @inject_db
    @coalesce
    def renderJobs(self):
        t = self.translator.get
        running = self.db().getJobs(program=None, jobType=None, jobStatus=JobStatus.RUNNING)
        queued = self.db().getJobs(program=None, jobType=None, jobStatus=JobStatus.QUEUED)
        listItems = []

        def getTitle(job):
            if job.getProgram(): 
                return job.getProgram().title()
            else:
                return t(m.UNKNOWN)

        def getJobStats(job):
            if job.jobStatus == JobStatus.QUEUED:
                position, numJobs = job.getPositionInQueue() 
                return t(m.QUEUED_N_OF_M) % (position, numJobs)
            elif job.jobStatus == JobStatus.RUNNING:
                try:
                    return t(m.COMPLETED_N_AT_M_FPS) % ('%d%%' % job.getPercentComplete(), '%2.0f' % job.getCommFlagRate())
                except StatusException:
                    return job.comment
            else:                                    
                return job.formattedJobStatus()
        
        def getHostInfo(job):
            commFlagBackend = self.db().toBackend(job.hostname)
            return [u'', u' %s %s' % (t(m.ON), commFlagBackend.hostname)][commFlagBackend.slave] 
            
        i = 1    
        for j in running:
            listItem = xbmcgui.ListItem()
            self.setListItemProperty(listItem, 'jobNumber', '%d'%i)
            title = getTitle(j)
            
            if j.jobType == JobType.COMMFLAG:
                status = u'%s %s%s. %s' % (t(m.COMM_FLAGGING), title, getHostInfo(j), getJobStats(j))
            elif j.jobType == JobType.TRANSCODE: 
                status = u'%s %s' % (t(m.TRANSCODING), title)
            else:
                status = u'%s %s %s' % (j.formattedJobType(), t(m.PROCESSING), title)
                
            self.setListItemProperty(listItem, 'status', status)
            listItems.append(listItem)
            i += 1

        for j in queued:
            listItem = xbmcgui.ListItem()
            self.setListItemProperty(listItem, 'jobNumber', '%d'%i)
            title = getTitle(j)

            if j.jobType == JobType.COMMFLAG: 
                status = u'%s %s' % (t(m.WAITING_COMM_FLAG), title)
            elif j.jobType == JobType.TRANSCODE: 
                status = u'%s %s' % (t(m.WAITING_TRANSCODE), title)
            else: 
                status = t(m.WAITING_TO_RUN_JOB) % (j.formattedJobType(), title)
                
            self.setListItemProperty(listItem, 'status', status)
            listItems.append(listItem)
            i+=1
        
        self.jobsListBox.addItems(listItems)
               
    @run_async
    @catchall     
    @inject_conn
    @coalesce
    def renderStats(self):
        return
        log.debug('renderStats enter')
        du = self.conn().getDiskUsage()
        self.setWindowProperty('spaceFree', formatSize(du['free'], True))
        self.setWindowProperty('spaceTotal', formatSize(du['total'], True))
        self.setWindowProperty('spaceUsed', formatSize(du['used'], True))

        load = self.conn().getLoad()
        self.setWindowProperty('load1', load['1'])
        self.setWindowProperty('load5', load['5'])
        self.setWindowProperty('load15', load['15'])

        self.setWindowProperty('guideDataStatus', self.conn().getGuideDataStatus())
        self.setWindowProperty('guideData', self.conn().getGuideData())
        log.debug('renderStats exit')
        
    @run_async
    @catchall
    @coalesce
    def renderNewsFeed(self):
        log.debug('renderNewsFeed enter')
        t = u'' 
        entries = self.feedHose.getLatestEntries()
        if len(entries) > 0:
            for entry in entries:
                t += u'[COLOR=ffe2ff43]%s[/COLOR] [COLOR=white]%s[/COLOR]       ' % (entry.username, entry.text)
            t = (u' ' *300) + t
        
        t = t.replace('\n', '')
        t = t.replace('\r', '')
        t = t.replace('|', '')

        self.setWindowProperty('newsfeed', t)
        log.debug('renderNewsFeed exit')
        
    def onEvent(self, event):
        log.debug('ONEVENT: home window received event: %s' % event)
        id = event['id']
        
        if id == Event.RECORDING_DELETED: # TODO: Add RECORDING_STARTED
            self.renderCoverFlow(exclude=event['program'])
        
        elif id == Event.SETTING_CHANGED and event['tag'] == 'feeds_twitter':
            self.renderNewsFeed()
        
        elif id in (Event.SCHEDULER_RAN, Event.SCHEDULE_CHANGED,):
            self.renderTuners()
            
        elif id in (Event.COMMFLAG_START,):
            self.renderJobs()