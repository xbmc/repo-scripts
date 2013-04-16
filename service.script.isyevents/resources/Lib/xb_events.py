'''
    ISY Event Engine for XBMC (xb_events)
    Copyright (C) 2012 Ryan M. Kraus

    LICENSE:
    This program is free software: you can redistribute it and/or modify
    it under the terms of the GNU General Public License as published by
    the Free Software Foundation, either version 2 of the License, or
    (at your option) any later version.

    This program is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU General Public License for more details.

    You should have received a copy of the GNU General Public License
    along with this program.  If not, see <http://www.gnu.org/licenses/>.
    
    DESCRIPTION:
    This Python Module contains the event engine used by the 
    XBMC addon, ISY Events.
    
    WRITTEN:    11/2012
'''

# imports
# xbmc
import xbmc
# custom
import xbmcJSON as json
import myCollections as mc
from log import log

class xbmcEvents(object):
    # settings
    _wait = 0.5

    # event definitions
    _events = {'onStart': [], \
        'onQuit': [], \
        'onPlayMovie': [], \
        'onPlayMusic': [], \
        'onStopMovie': [], \
        'onStopMusic': [], \
        'onPauseMovie': [], \
        'onPauseMusic': [], \
        'onResumeMovie': [], \
        'onResumeMusic':[]}
        
    # current status
    _playingMovie = mc.histlist(False)
    _playingMusic = mc.histlist(False)
    _paused = mc.histlist(False)
    
    def __init__(self):
        pass
    
    def ListEvents(self):
        return self._events.keys()
    
    def AddHandler(self, event, fun):
        if fun != None:
            if event in self._events.keys():
                self._events[event].append(fun)
                return len(self._events[event])-1
            else:
                raise InvalidEventName(event)
                
    def AddHandlers(self, events):
        for event in events.keys(): 
            self.AddHandler(event, events[event])
        
    def RemoveHandler(self, event, id):
        if event in self._events.keys():
            self._events[event].pop(id)
        else:
            raise InvalidEventName(event)
            
    def RaiseEvent(self, event):
        log(event)
        for fun in self._events[event]:
            fun()
            
    def RunMainLoop(self, wait = _wait):
        # set loop wait time
        self._wait = wait
    
        # connect to xbmc
        player = xbmc.Player()
    
        # raise xbmc started event
        self.RaiseEvent('onStart')
        
        while(not xbmc.abortRequested):
            # check movie playing status
            self._playingMovie.set(player.isPlayingVideo())
            
            # check music playing status
            self._playingMusic.set(player.isPlayingAudio())
            
            # check paused status
            if self._playingMovie.get() or self._playingMusic.get():
                # get player speed
                player_id = json.GetPlayerID()
                player_speed = json.GetPlayerSpeed(player_id)
                # paused if player speed is 0
                self._paused.set(player_speed == 0)
            else:
                self._paused.set(False)
                        
            # check for events
            if self._playingMovie.step_on():
                # raise started playing movie
                self.RaiseEvent('onPlayMovie')
            elif self._playingMovie.step_off():
                # raise stopped playing movie
                self.RaiseEvent('onStopMovie')
            elif self._paused.step_on() and self._playingMovie.get():
                # raise movie paused
                self.RaiseEvent('onPauseMovie')
            elif self._paused.step_off() and self._playingMovie.get():
                # raise movie resumed
                self.RaiseEvent('onResumeMovie')
                
            elif self._playingMusic.step_on():
                # raise started playing music
                self.RaiseEvent('onPlayMusic')
            elif self._playingMusic.step_off():
                # raise stopped playing music
                self.RaiseEvent('onStopMusic')
            elif self._paused.step_on() and self._playingMusic.get():
                # raise music paused
                self.RaiseEvent('onPauseMusic')
            elif self._paused.step_off() and self._playingMusic.get():
                # raise music resumed
                self.RaiseEvent('onResumeMusic')
                
            # wait sleep time
            xbmc.sleep(int(self._wait * 1000))
            
        # raise xbmc quit event
        self.RaiseEvent('onQuit')
    
    
class InvalidEventName(Exception):
    pass