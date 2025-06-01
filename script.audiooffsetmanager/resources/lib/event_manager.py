"""Event manager module receives callback functions from Kodi regarding
playback events, filters them, and posts them to subscribers/other modules.
"""

import xbmc
import time


class EventManager(xbmc.Player):
    def __init__(self):
        super().__init__()
        self._subscribers = {}
        self.playback_state = {
            'start_time': None,
            'av_started': False,
            'last_av_change': 0,
            'last_event': None,
            'ignore_next_av': False
        }

    def subscribe(self, event_name, callback):
        if event_name not in self._subscribers:
            self._subscribers[event_name] = []
        self._subscribers[event_name].append(callback)

    def unsubscribe(self, event_name, callback):
        if event_name in self._subscribers:
            self._subscribers[event_name].remove(callback)
            if not self._subscribers[event_name]:
                del self._subscribers[event_name]

    def publish(self, event_name, *args, **kwargs):
        if event_name in self._subscribers:
            for callback in self._subscribers[event_name]:
                callback(*args, **kwargs)
        self.playback_state['last_event'] = event_name

        # Set flag to ignore the next AV change if certain events are published
        if event_name in ['PLAYBACK_SEEK', 'PLAYBACK_SEEK_CHAPTER',
                         'PLAYBACK_SPEED_CHANGED']:
            self.playback_state['ignore_next_av'] = True

    def onAVStarted(self):
        xbmc.log("AOM_EventManager: AV started", xbmc.LOGDEBUG)
        self.playback_state['start_time'] = time.time()
        self.playback_state['av_started'] = True
        self.publish('AV_STARTED')

    def _should_process_av_change(self):
        if not self.playback_state['av_started']:
            return False
            
        current_time = time.time()
        if (self.playback_state['start_time'] and 
            (current_time - self.playback_state['start_time'] < 2)):
            return False
            
        if (current_time - self.playback_state['last_av_change'] < 1):
            return False
            
        if self.playback_state['ignore_next_av']:
            self.playback_state['ignore_next_av'] = False
            return False
            
        return True

    def onAVChange(self):
        if not self._should_process_av_change():
            return
            
        self.playback_state['last_av_change'] = time.time()
        xbmc.log("AOM_EventManager: AV stream changed", xbmc.LOGDEBUG)
        self.publish('ON_AV_CHANGE')

    def onPlayBackStopped(self):
        xbmc.log("AOM_EventManager: Playback stopped", xbmc.LOGDEBUG)
        self.playback_state['start_time'] = None
        self.playback_state['av_started'] = False
        self.publish('PLAYBACK_STOPPED')

    def onPlayBackEnded(self):
        xbmc.log("AOM_EventManager: Playback ended", xbmc.LOGDEBUG)
        self.playback_state['start_time'] = None
        self.playback_state['av_started'] = False
        self.publish('PLAYBACK_ENDED')

    def onPlayBackPaused(self):
        xbmc.log("AOM_EventManager: Playback paused", xbmc.LOGDEBUG)
        self.publish('PLAYBACK_PAUSED')

    def onPlayBackResumed(self):
        xbmc.log("AOM_EventManager: Playback resumed", xbmc.LOGDEBUG)
        self.publish('PLAYBACK_RESUMED')

    def onPlayBackSeek(self, time, seekOffset):
        xbmc.log(f"AOM_EventManager: Playback seek to time {time} with offset "
                 f"{seekOffset}", xbmc.LOGDEBUG)
        self.publish('PLAYBACK_SEEK', time, seekOffset)

    def onPlayBackSeekChapter(self, chapter):
        xbmc.log(f"AOM_EventManager: Playback seek to chapter {chapter}",
                 xbmc.LOGDEBUG)
        self.publish('PLAYBACK_SEEK_CHAPTER', chapter)

    def onPlayBackSpeedChanged(self, speed):
        xbmc.log(f"AOM_EventManager: Playback speed changed to {speed}",
                 xbmc.LOGDEBUG)
        self.publish('PLAYBACK_SPEED_CHANGED', speed)
