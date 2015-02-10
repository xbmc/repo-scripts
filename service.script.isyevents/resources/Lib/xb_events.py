from log import log
import myCollections as mc
import xbmc
import xbmcJSON as json


class xbmcEvents(object):
    # settings
    _wait = 0.5

    # event definitions
    _events = {'onStart': [],
               'onQuit': [],
               'onPlayMovie': [],
               'onPlayMusic': [],
               'onStopMovie': [],
               'onStopMusic': [],
               'onPauseMovie': [],
               'onPauseMusic': [],
               'onResumeMovie': [],
               'onResumeMusic': [],
               'onScreenSaverOn': [],
               'onScreenSaverOff': []}

    # current status
    _playingMovie = mc.histlist(False)
    _playingMusic = mc.histlist(False)
    _paused = mc.histlist(False)
    _screenSaver = mc.histlist(False)

    def __init__(self):
        pass

    def ListEvents(self):
        return self._events.keys()

    def AddHandler(self, event, fun):
        if fun is not None:
            if event in self._events.keys():
                self._events[event].append(fun)
                return len(self._events[event]) - 1
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

    def RunMainLoop(self, wait=_wait):
        # set loop wait time
        self._wait = wait

        # connect to xbmc
        player = xbmc.Player()

        # raise xbmc started event
        self.RaiseEvent('onStart')

        while(not xbmc.abortRequested):
            # check screen saver status
            self._screenSaver.set(bool(
                xbmc.getCondVisibility("System.ScreenSaverActive")))

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
                if player_id is not None and player_speed is not None:
                    self._paused.set(player_speed == 0)
            else:
                self._paused.set(False)

            # check for events
            if self._screenSaver.step_on():
                # raise screen saver on event
                self.RaiseEvent('onScreenSaverOn')
            if self._screenSaver.step_off():
                # raise screen saver off event
                self.RaiseEvent('onScreenSaverOff')
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
