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
import os
import threading
import time
import xbmc
import xbmcgui
import mythbox.msg as m
import mythbox.ui.toolkit as toolkit

from mythbox.ui.toolkit import showPopup
from mythbox.util import formatSeconds, BoundedEvictingQueue, safe_str, catchall
from mythbox.mythtv.db import inject_db

log = logging.getLogger('mythbox.ui')
mlog = logging.getLogger('mythbox.method')

mythPlayer = None

# Interval in millis to sleep when we're waiting around for 
# async xbmc events to take complete
SLEEP_MILLIS = 250


class BasePlayer(xbmc.Player):
    
    def __init__(self, *args, **kwargs):
        xbmc.Player.__init__(self, *args, **kwargs)    
        self.active = True
        self.tracker = PositionTracker(self)
        
    def buildPlaybackUrl(self):
        raise Exception('Abstract method')

    def buildPlayList(self):
        raise Exception('Abstract method')

    def playRecording(self, commSkipper):
        raise Exception('Abstract method')
        
    @catchall
    def onPlayBackStarted(self):
        if self.active:
            log.debug('> base:onPlayBackStarted %s' % self)
            for target in (self.bookmarker, self.tracker, self.commSkipper):
                try:
                    target.onPlayBackStarted()
                except:
                    log.exception('onPlayBackStarted')
            log.debug('< base:onPlayBackStarted %s' % self)

    def onPlayBackStopped(self):
        if self.active:
            self.active = False
            log.debug('> onPlayBackStopped')
            for target in (self.tracker, self.commSkipper, self.bookmarker):
                try:
                    target.onPlayBackStopped()
                except:
                    log.exception('onPlayBackStopped')
            log.debug('< onPlayBackStopped')

    def onPlayBackEnded(self):
        if self.active:
            self.active = False
            log.debug('> onPlayBackEnded')
            for target in (self.tracker, self.commSkipper, self.bookmarker):
                try:
                    target.onPlayBackEnded()
                except:
                    log.exception('onPlayBackStopped')
            log.debug('< onPlayBackEnded')


class MountedPlayer(BasePlayer):
    '''Plays mythtv recordings with support for bookmarks, commercial skipping, etc'''
    
    def __init__(self, *args, **kwargs):
        BasePlayer.__init__(self, *args, **kwargs)    
        [setattr(self,k,v) for k,v in kwargs.iteritems() if k in ('translator', 'mythThumbnailCache', 'program', 'platform')]
        self.bookmarker = MythBookmarker(self, self.program, self.translator)
        self._playbackCompletedLock = threading.Event()
        self._playbackCompletedLock.clear()
        
    def buildPlaybackUrl(self):
        return self.program.getLocalPath()
    
    def playRecording(self, commSkipper):
        """
        Plays the given program. Blocks until playback is stopped or until the 
        end of the recording is reached
        """
        mlog.debug('> playRecording(%s)' % safe_str(self.program.title()))
        assert not self.isPlaying(), 'Player is already playing a video'
        
        self.commSkipper = commSkipper
        self.play(self.buildPlaybackUrl(), self.buildPlayList(), windowed=False)
        
        self.waitForPlaybackCompleted()
        self.active = False
        mlog.debug('< playRecording(...)')

    # Callbacks ---------------------------------------------------------------


    @catchall    
    def onPlayBackStopped(self):
        if self.active:
            try:
                super(MountedPlayer, self).onPlayBackStopped()
            finally:
                self._playbackCompletedLock.set()
    
    @catchall            
    def onPlayBackEnded(self):
        if self.active:
            try:
                super(MountedPlayer, self).onPlayBackEnded()
            finally:
                self._playbackCompletedLock.set()

    # Private -----------------------------------------------------------------
    
    def waitForPlaybackCompleted(self):
        while not self._playbackCompletedLock.isSet():
            #log.debug('Waiting for playback completed...')
            xbmc.sleep(SLEEP_MILLIS)

    def buildPlayList(self):
        mlog.debug("> _buildPlayList")
        
        playlistItem = xbmcgui.ListItem()
        title = self.program.fullTitle()
        comms = self.program.getCommercials()
        if len(comms) > 0:
            title += '(%s breaks - %s)' % (len(comms), ', '.join(map(lambda c: formatSeconds(c.start), comms)))
                
        playlistItem.setInfo(
            "video", {
                "Genre"  : self.program.category(), 
                "Studio" : self.program.formattedChannel(), 
                "Title"  : title, 
                "Plot"   : self.program.formattedDescription()
            })
        
        # TODO: Set start offset if a comm break starts at 0.0 
        #  playlistItem.setProperty('StartOffset', '256.4')

        mlog.debug("< _buildPlayList")
        return playlistItem


class StreamingPlayer(BasePlayer):
    """Use xbmcs built in myth support to stream the recording over the network."""

    def __init__(self, *args, **kwargs):
        BasePlayer.__init__(self, *args, **kwargs)    
        [setattr(self,k,v) for k,v in kwargs.iteritems() if k in ('settings', 'translator', 'mythThumbnailCache', 'program', 'platform')]
        self.bookmarker = MythBookmarker(self, self.program, self.translator)
        
    @inject_db        
    def buildPlaybackUrl(self):
        backend = self.db().toBackend(self.program.hostname())

        # myth://dbuser:dbpassword@mythbackend_hostname:mythbackend_port/recordings/filename.mpg
        url = 'myth://%s:%s@%s:%s/recordings/%s' % (
            self.settings.get('mysql_database'),
            self.settings.get('mysql_password'),
            backend.ipAddress,
            backend.port,
            self.program.getBareFilename())
        log.debug('Playback url: %s' % url)
        return url
    
    def playRecording(self, commSkipper):
        """
        Plays the given program. Blocks until playback is stopped or until the 
        end of the recording is reached
        """
        mlog.debug('> playRecording %s' % safe_str(self.program.title()))
        assert not self.isPlaying(), 'Player is already playing a video'
        self.commSkipper = commSkipper
        self.play(self.buildPlaybackUrl(), self.buildPlayList())
        mlog.debug('< playRecording')

    def buildPlayList(self):
        playlistItem = xbmcgui.ListItem()
        comms = self.program.getCommercials()
        title = self.program.fullTitle()
        if len(comms) > 0: 
            # times are invalid when streaming so only show cardinality
            title += u' (%d breaks)' % len(comms)        
        
        playlistItem.setInfo(
            "video", {
                "Genre"  : self.program.category(), 
                "Studio" : self.program.formattedChannel(), 
                "Title"  : title, 
                "Plot"   : self.program.formattedDescription()
            })
        return playlistItem


class Bookmarker(object):
    pass


class XbmcBookmarker(Bookmarker):
    '''When using a myth:// style URL for playback, defer to XBMC's built in 
    resume from last postion functionality'''
    
    def __init__(self, *args, **kwargs):
        pass
    
    def onPlayBackStarted(self):
        pass
        
    def onPlayBackStopped(self):
        pass
        
    def onPlayBackEnded(self):
        pass
    
    
class MythBookmarker(Bookmarker):
    '''Mimics XBMC video player's builtin auto resume functionality'''
    
    def __init__(self, player, program, translator):
        self.player = player
        self.program = program
        self.translator = translator
        #self.fps = None
                
    def onPlayBackStarted(self):
        self._resumeFromBookmark()
        
    def onPlayBackStopped(self):
        self._saveLastPositionAsBookmark()
        
    def onPlayBackEnded(self):
        self._clearBookmark()

    def _clearBookmark(self):
        if self.program.isBookmarked():
            self.program.setBookmark(0.0) 

    def _resumeFromBookmark(self):
        log.debug('bookmarker : before wait for gotFPS')
        
        bookmarkSecs = self.program.getBookmark()
        if bookmarkSecs > 0 and bookmarkSecs < (self.program.getDuration() * 60):
            fb = formatSeconds(bookmarkSecs)
            log.debug('Resuming recording at bookmarked position of %s' % fb)
            showPopup(self.program.title(), self.translator.get(m.RESUMING_AT) % fb)
            self.player.seekTime(bookmarkSecs)
            while self.player.getTime() < bookmarkSecs:
                log.debug('Waiting for player time %s to seek past bookmark of %s' %(formatSeconds(self.player.getTime()), fb))
                xbmc.sleep(SLEEP_MILLIS)
        else:
            log.debug('Recording has no bookmark or bookmark exceeds program length')

    def _saveLastPositionAsBookmark(self):
        lastPos = self.player.tracker.getLastPosition()
        log.debug('Setting bookmark on %s to %s' %(safe_str(self.program.title()), formatSeconds(lastPos)))
        try:
            self.program.setBookmark(lastPos)
        except:
            log.exception('_saveLastPositionAsBookmark catchall')


class PositionTracker(object):
    """
    Tracks the last position of the player. This is necessary because 
    Player.getTime() is not valid after the callback to 
    Player.onPlayBackStopped() has completed.  
    """
    
    HISTORY_SECS = 5  # Number of seconds of history to keep around

    def __init__(self, player):
        self._player = player
        self._lastPos = 0.0
        self._tracker = BoundedEvictingQueue((1000/SLEEP_MILLIS) * self.HISTORY_SECS)
        self._history = []
        
    def onPlayBackStarted(self):
        log.debug('Starting position tracker...')
        self._tracker = threading.Thread(
            name='Position Tracker', 
            target = self._trackPosition)
        self._tracker.start()
    
    def onPlayBackStopped(self):
        if self._tracker.isAlive():
            log.debug('Position tracker stop called. Still alive = %s' % self._tracker.isAlive())
        else:
            log.debug('Position tracker thread already dead.')

    def onPlayBackEnded(self):
        self.onPlayBackStopped()
        
    def getHistory(self, howFarBack):
        """Returns a list of TrackerSamples from 'howFarBack' seconds ago."""
        endPos = self._lastPos
        startPos = endPos - howFarBack
        slice = []
        for sample in self._history:
            if startPos <= sample.pos and sample.pos <= endPos:
                slice.append(sample)
        log.debug('Tracker history for %s secs = [%s] %s' % (howFarBack, len(slice), slice))
        return slice
    
    def getLastPosition(self):
        return self._lastPos
    
    def _trackPosition(self):
        """Method run in a separate thread. Tracks last position of player as long as it is playing"""
        try:
            while self._player.isPlaying():
                self._lastPos = self._player.getTime()
                self._history.append(TrackerSample(time.time(), self._lastPos))
                #log.debug('Tracker time = %s' % self._lastPos)
                xbmc.sleep(SLEEP_MILLIS)
            log.debug('Position tracker thread exiting with lastPos = %s' % self.getLastPosition())
        except:
            log.exception('_trackPosition catchall')


class TrackerSample(object):
    
    def __init__(self, time, pos):
        self.time = time
        self.pos  = pos
    
    def __repr__(self):
        return 'Sample {time = %s, pos = %s}' % (self.time, self.pos)         
            

class ICommercialSkipper(object):
    """Common interface for commercial skipping implementations."""
    
    def __init__(self, player, program, translator):
        self.player = player
        self.program = program
        self.translator = translator
        
    def onPlayBackStarted(self):
        raise NotImplementedError, 'Abstract base class'
    
    def onPlayBackStopped(self):
        raise NotImplementedError, 'Abstract base class'

    def onPlayBackEnded(self):
        raise NotImplementedError, 'Abstract base class'
    

class NoOpCommercialSkipper(ICommercialSkipper):

    def __init__(self, player=None, program=None, translator=None):
        ICommercialSkipper.__init__(self, player, program, translator)

    def onPlayBackStarted(self):
        pass
    
    def onPlayBackStopped(self):
        pass

    def onPlayBackEnded(self):
        pass


class TrackingCommercialSkipper(ICommercialSkipper):
    """
    Commercial skipper that monitors the position of the currently playing file
    and skips commercials accordingly.
    """
    
    def __init__(self, player, program, translator):
        ICommercialSkipper.__init__(self, player, program, translator)
        
    def onPlayBackStarted(self):
        log.debug('program in skipper = %s' % safe_str(self.program.title()))
        
        # don't want changes to commbreak.skipped to stick beyond the scope of 
        # this player instance so use a deepcopy
        self._breaks = copy.deepcopy(self.program.getCommercials())
        
        # Has a value when video position falls in a comm break
        self._currentBreak = None  

        for b in self._breaks:
            log.debug('break = %s' % b)
 
        self._skipper = threading.Thread(name='Tracking Commercial Skipper', target = self._trackCommercials)
        self._skipper.start()
    
    def onPlayBackStopped(self):
        if self._skipper.isAlive():
            log.debug('Commercial tracker stop called. Still alive = %s' % self._skipper.isAlive())
        else:
            log.debug('Commercial tracker thread already dead')
    
    def onPlayBackEnded(self):
        self.onPlayBackStopped()    

    def _isInBreak(self, pos):
        for b in self._breaks:
            if b.isDuring(pos):
                self._currentBreak = b
                return True
        self._currentBreak = None
        return False    
    
    def _trackCommercials(self):
        """Method run in a separate thread to skip over commercials"""
        try:
            if len(self._breaks) == 0:
                log.debug('Recording %s has no comm breaks, exiting comm tracker' % safe_str(self.program.title()))
                return
            
            while self.player.isPlaying():
                pos = self.player.getTime()
                if self._isInBreak(pos) and not self._currentBreak.skipped:
                    log.debug('entered comm break = %s' % self._currentBreak)
                    if self._isCloseToStartOfCommercial(pos) and not self._wasUserSkippingAround(pos): 
                        log.debug('Comm skip activated!')
                        showPopup(self.program.title(), self.translator.get(m.SKIPPING_COMMERCIAL) % formatSeconds(self._currentBreak.duration()), 3000)
                        self.player.seekTime(self._currentBreak.end)
                        self._waitForPlayerToPassCommercialBreak()
                        self._currentBreak.skipped = True
                        
                    if self._landedInCommercial(pos):
                        log.debug("Landed in comm break and want to skip forward")  
                        showPopup(self.program.title(), self.translator.get(m.FORWARDING_THROUGH) % formatSeconds(self._currentBreak.duration()), 3000)
                        self.player.seekTime(self._currentBreak.end)
                        self._waitForPlayerToPassCommercialBreak()
                        self._currentBreak.skipped = True
                xbmc.sleep(SLEEP_MILLIS)
            log.debug('Commercial tracker thread exiting')
        except:
            log.exception('_trackCommercials catchall')
            
    def _landedInCommercial(self, currPos):
        #samplesInCommercial = 4  # In commercial for 2 seconds
        secondsToSample = 4
        samples = self.player.tracker.getHistory(secondsToSample)
        samplesInCommercial = len(filter(lambda x: self._currentBreak.isDuring(x.pos), samples))
        log.debug('Samples in commercial = %d' % samplesInCommercial)
        return samplesInCommercial > 8 and samplesInCommercial < 12
    
    def _wasUserSkippingAround(self, currPos):
        """
        Check last 2 seconds of history for number of samples.
        A high number of samples indicates that user was probably 
        not skipping around in the video hence the comm skip would 
        be a good thing.
        """
        wasSkipping = False
        samplePeriodSecs = 2 # TODO: Pass in as param to method call

        # If currPos is too close to the start of the video..assume not 
        # skipping around
        if currPos > samplePeriodSecs:
            requiredSamples = 6  # TODO: Derive as percentage instead of hardcoding
            numSamples = len(self.player.tracker.getHistory(samplePeriodSecs))
            log.debug('Samples in last %s seconds = %s' %(samplePeriodSecs, numSamples))
            wasSkipping = numSamples < requiredSamples

        log.debug('User was skipping around = %s' % wasSkipping)
        return wasSkipping
    
    def _isCloseToStartOfCommercial(self, currPos):
        """
        check that the current pos is close in proximity to the start of the
        commercial break. assumes that comm break is skipped only if the user
        played directly into the commercial vs. landing inside the commercial
        via ffwd, rewind, etc.
        """
        windowStart = self._currentBreak.start - 1
        windowEnd = self._currentBreak.start + 2
        isClose = currPos >= windowStart and currPos <= windowEnd
        log.debug('User close to start of comm break = %s' % isClose) 
        return isClose

    def _waitForPlayerToPassCommercialBreak(self):
        # TODO: What if user stops playing while in this loop? Add isPlaying() to loop invariant
        # wait for player pos to pass current break
        while self._currentBreak.isDuring(self.player.getTime()):
            xbmc.sleep(SLEEP_MILLIS)
