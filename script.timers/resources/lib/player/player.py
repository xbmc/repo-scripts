from datetime import timedelta

import xbmc
from resources.lib.player import player_utils
from resources.lib.player.mediatype import AUDIO, PICTURE, TYPES, VIDEO
from resources.lib.player.playerstatus import PlayerStatus
from resources.lib.player.playlist import PlayList
from resources.lib.timer.notification import showNotification
from resources.lib.timer.timer import Timer
from resources.lib.utils import datetime_utils
from resources.lib.utils.vfs_utils import (convert_to_playlist,
                                           get_files_and_type,
                                           get_longest_common_path)


class Player(xbmc.Player):

    _MAX_TRIES = 10
    _RESPITE = 3000

    def __init__(self) -> None:
        super().__init__()

        self._seek_delayed_timer = False
        self._default_volume: int = 100
        self._recent_volume: int = None

        self._paused: bool = False

        self._seektime: float = None
        self._playlist_timeline: 'list[float]' = list()
        self._playlist: PlayList = None
        self._skip_next_stop_event_until_started = False

        self._resume_status: 'dict[PlayerStatus]' = dict()

        self._running_stop_at_end_timer: 'tuple[Timer, bool]' = (None, False)

    def playTimer(self, timer: Timer, dtd: datetime_utils.DateTimeDelta) -> None:

        def _save_resume(_timer: Timer) -> None:

            for _type in player_utils.get_types_replaced_by_type(_timer.media_type):

                _resume_status = self._getResumeStatus(_type)
                if _timer.is_resuming_timer():
                    _active_players = self.getActivePlayersWithPlaylist(
                        type=_type)
                    if not _resume_status or _resume_status.resuming:
                        self._resume_status[_type] = PlayerStatus(
                            _timer, state=_active_players[_type] if _type in _active_players else None)

                    else:
                        _resume_status.timer = _timer

                elif _resume_status:
                    self.resetResumeStatus(_type)

        def _get_delay_for_seektime(_timer: Timer, _dtd: datetime_utils.DateTimeDelta) -> timedelta:

            seektime = None
            if self._seek_delayed_timer and _timer.is_play_at_start_timer():
                if timer.current_period:
                    seektime = datetime_utils.abs_time_diff(
                        _dtd.td, timer.current_period.start)
                    seektime = None if seektime * 1000 <= self._RESPITE else seektime

            return seektime

        _save_resume(timer)

        path, state_from_path = player_utils.parse_player_state_from_path(
            timer.path)

        files, type = self._getFilesAndType(
            path, type=timer.media_type)

        if self._isPlaying(files, type, repeat=player_utils.REPEAT_ALL if timer.repeat else player_utils.REPEAT_OFF):
            return

        if state_from_path:
            seektime = state_from_path.time
        else:
            seektime = _get_delay_for_seektime(timer, dtd)

        if type == PICTURE:
            stayTime = self._getSlideshowStaytime()
            beginSlide = files[(seektime // stayTime) %
                               len(files)] if seektime else None

            if timer.is_stop_at_end_timer():
                amountOfSlides = datetime_utils.abs_time_diff(
                    timer.current_period.end, dtd.td) // stayTime + 1
            else:
                amountOfSlides = 0

            self._playSlideShow(path=path,
                                shuffle=timer.shuffle, beginSlide=beginSlide, amount=amountOfSlides)

        else:
            playlist = self._buildPlaylist(
                paths=files, type=type, label=timer.label)

            if timer.shuffle:
                playlist.shuffle()

            self._playAV(playlist=playlist,
                         startpos=state_from_path.position if state_from_path and state_from_path.position > 0 else 0,
                         seektime=seektime,
                         repeat=player_utils.REPEAT_ALL if timer.repeat else player_utils.REPEAT_OFF,
                         shuffled=timer.shuffle)

            if timer.is_stop_at_end_timer():
                self._running_stop_at_end_timer = (timer, False)

    def _playAV(self, playlist: PlayList, startpos=0, seektime=None, repeat=player_utils.REPEAT_OFF, shuffled=False, speed=1.0) -> None:

        self._playlist = playlist
        self._seektime = seektime
        self._skip_next_stop_event_until_started = True

        if playlist.getPlayListId() == TYPES.index(VIDEO):
            self.stopPlayer(PICTURE)

        self.setRepeat(repeat)
        self.setShuffled(shuffled)
        self.setSpeed(speed)
        xbmc.executebuiltin("CECActivateSource")
        self.play(playlist.directUrl or playlist, startpos=startpos)

    def _playSlideShow(self, path: str, beginSlide=None, shuffle=False, amount=0) -> None:

        player_utils.play_slideshow(
            path=path, beginSlide=beginSlide, shuffle=shuffle, amount=amount)

    def _isPlaying(self, files, type, repeat=player_utils.REPEAT_OFF) -> bool:

        ap = self.getActivePlayersWithPlaylist(type)
        return type in ap and files == [e["file"] for e in ap[type].playlist] and ap[type].repeat == repeat

    def _getFilesAndType(self, path: str, type=None) -> 'tuple[list[str],str]':

        return get_files_and_type(path)

    def _buildPlaylist(self, paths: 'list[str]', type: str, label: str) -> 'xbmc.PlayList':

        return convert_to_playlist(paths=paths, type=type, label=label)

    def stopPlayer(self, type: str) -> 'player_utils.State':

        return player_utils.stop_player(type)

    def onPlayBackStarted(self) -> None:

        self._paused = False

    def onAVStarted(self) -> None:

        self._paused = False
        self._skip_next_stop_event_until_started = False
        if self._recent_volume == None:
            self._recent_volume = self.getVolume()
        self._seekRetroactivly()

    def onPlayBackStopped(self) -> None:

        self._paused = False
        if self._skip_next_stop_event_until_started:
            self._skip_next_stop_event_until_started = False

        else:
            _rst = self._running_stop_at_end_timer
            self._reset()
            if _rst[0] and not _rst[1]:
                self._running_stop_at_end_timer = (_rst[0], True)
                showNotification(_rst[0], msg_id=32289)

    def onPlayBackEnded(self) -> None:

        self._paused = False
        if VIDEO in self._resume_status:
            self._resumeFormer(type=VIDEO, keep=True)

        elif AUDIO in self._resume_status:
            self._resumeFormer(type=AUDIO, keep=True)

        else:
            self._reset()

    def onPlayBackError(self) -> None:

        self._reset()

    def onPlayBackPaused(self) -> None:

        self._paused = True

    def onPlayBackResumed(self) -> None:

        self._paused = False

    def isPaused(self) -> bool:

        return self._paused

    def resumeFormerOrStop(self, timer: Timer) -> None:

        if not timer.is_resuming_timer() or not self._resumeFormer(type=timer.media_type, keep=False):
            if timer.media_type == PICTURE:
                self.stopPlayer(PICTURE)
            elif timer != self._running_stop_at_end_timer[0] or not self._running_stop_at_end_timer[1]:
                self.stop()

            self._reset(type=timer.media_type)
            xbmc.sleep(self._RESPITE)

        self.resetResumeOfTimer(timer)

    def _resumeFormer(self, type: str, keep=False) -> bool:

        resuming = False
        for _type in player_utils.get_types_replaced_by_type(type):

            resumeState = self._getResumeStatus(_type)
            if resumeState and resumeState.state:
                state = resumeState.state
                if not keep:
                    self.resetResumeStatus(_type)

                if not resumeState.resuming:
                    xbmc.sleep(self._RESPITE)
                    paths = [item["file"] for item in state.playlist]
                    if self._isPlaying(files=paths, type=_type, repeat=state.repeat):
                        pass

                    elif _type in [VIDEO, AUDIO]:
                        label = state.playlist[state.position]["label"] if state.position < len(
                            state.playlist) else ""
                        playlist = self._buildPlaylist(
                            paths=paths, type=state.type, label=label)
                        self._playAV(
                            playlist,
                            startpos=state.position,
                            seektime=state.time,
                            repeat=state.repeat,
                            shuffled=state.shuffled,
                            speed=state.speed)

                    elif _type == PICTURE:
                        path = get_longest_common_path(paths)
                        if path:
                            beginSlide = state.playlist[state.position % len(
                                state.playlist)]["file"]
                            self._playSlideShow(
                                path=path, shuffle=state.shuffled, beginSlide=beginSlide)

                    if keep:
                        resumeState.resuming = True

                resuming = True

        return resuming

    def getActivePlayersWithPlaylist(self, type=None) -> 'dict[str, player_utils.State]':

        return player_utils.get_active_players_with_playlist(type=type)

    def _getResumeStatus(self, type: str) -> PlayerStatus:

        if type in self._resume_status:
            return self._resume_status[type]

        else:
            return None

    def resetResumeOfTimer(self, timer: Timer) -> None:

        typesToRemove = list()
        for type in self._resume_status:
            resumeState = self._getResumeStatus(type)
            if resumeState and resumeState.timer.id == timer.id:
                typesToRemove.append(type)

        for type in typesToRemove:
            self.resetResumeStatus(type)

    def resetResumeStatus(self, type=None) -> None:

        if type:
            if type in self._resume_status:
                self._resume_status.pop(type)

        else:
            self._resume_status = dict()

    def _seekRetroactivly(self) -> None:

        def _seekTimeInPlaylist() -> None:

            _totalTime = self.getTotalTime()
            self._playlist_timeline.append(_totalTime)
            if self._playlist.getposition() < self._playlist.size() - 1:
                self._seektime -= _totalTime
                self._skip_next_stop_event_until_started = True
                self.playnext()

            else:
                _activePlayer = self.getActivePlayersWithPlaylist(
                    TYPES[self._playlist.getPlayListId()])
                if _activePlayer and _activePlayer[TYPES[self._playlist.getPlayListId()]].repeat == player_utils.REPEAT_ALL:
                    i = 0
                    while self._seektime > self._playlist_timeline[i]:
                        self._seektime -= self._playlist_timeline[i]
                        i = (i + 1) % len(self._playlist_timeline)

                    _state = _activePlayer[TYPES[self._playlist.getPlayListId()]]
                    self._playAV(playlist=self._playlist, startpos=i,
                                 seektime=self._seektime, repeat=player_utils.REPEAT_ALL,
                                 shuffled=_state.shuffled,
                                 speed=_state.speed)
                else:
                    self.stop()
                    self._resetSeek()

        if not self._seektime:
            self._resetSeek()
            return

        self.setVolume(0)

        tries = 0
        xbmc.sleep(500)
        while not self.isPlaying() and tries < self._MAX_TRIES:
            xbmc.sleep(300)
            tries += 1

        _totalTime = self.getTotalTime()
        if tries == self._MAX_TRIES or _totalTime < 10:
            self._resetSeek()

        elif self._playlist.size() and self._seektime >= _totalTime:
            _seekTimeInPlaylist()

        else:
            seektime = self._seektime
            self._resetSeek()
            self.seekTime(seektime)

    def setSeekDelayedTimer(self, _seek_delayed_timer: bool) -> None:

        self._seek_delayed_timer = _seek_delayed_timer

    def _resetSeek(self) -> None:

        if self._recent_volume:
            self.setVolume(self._recent_volume)
        self._recent_volume = None
        self._seektime = None
        self._playlist_timeline = list()

    def _reset(self, type=None) -> None:

        self._paused = False
        self._playlist = None
        self._skip_next_stop_event_until_started = False
        self._resetSeek()
        self.resetResumeStatus(type)

        self.setRepeat(player_utils.REPEAT_OFF)
        self.setShuffled(False)
        self._running_stop_at_end_timer = (None, False)

    def getVolume(self) -> int:

        return player_utils.get_volume(or_default=self._default_volume)

    def setVolume(self, volume: int) -> None:

        player_utils.set_volume(volume)

    def getDefaultVolume(self) -> int:

        return self._default_volume

    def setDefaultVolume(self, volume) -> None:

        self._default_volume = volume

    def setRepeat(self, mode: str) -> None:

        player_utils.set_repeat(mode)

    def setShuffled(self, value: bool) -> None:

        player_utils.set_shuffled(value)

    def setSpeed(self, speed: float) -> None:

        player_utils.set_speed(speed)

    def _getSlideshowStaytime(self) -> int:

        return player_utils.get_slideshow_staytime()

    def __str__(self) -> str:
        return "Player[_seek_delayed_timer=%s, _default_volume=%i, _recent_volume=%i, _paused=%s, _seektime=%f, _running_stop_at_end_timer=%s, _resume_status=[%s]]" % (self._seek_delayed_timer,
                                                                                                                                                                        self._default_volume or -1,
                                                                                                                                                                        self._recent_volume or -1,
                                                                                                                                                                        self._paused,
                                                                                                                                                                        self._seektime or 0,
                                                                                                                                                                        str(
                                                                                                                                                                            self._running_stop_at_end_timer),
                                                                                                                                                                        ", ".join(["%s=%s" % (k, self._resume_status[k]) for k in self._resume_status]))
