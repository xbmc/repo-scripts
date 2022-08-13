from datetime import timedelta

import xbmc
from resources.lib.player import player_utils
from resources.lib.player.mediatype import AUDIO, PICTURE, TYPES, VIDEO
from resources.lib.player.playerstatus import PlayerStatus
from resources.lib.timer.timer import Timer
from resources.lib.utils import datetime_utils
from resources.lib.utils.vfs_utils import (convert_to_playlist,
                                           get_files_and_type,
                                           get_longest_common_path)


class Player(xbmc.Player):

    _MAX_TRIES = 10
    _RESPITE = 3000

    _seek_delayed_timer = False
    _default_volume = 100
    _recent_volume = None

    _seektime = None
    _playlist_timeline = list()
    _playlist = None
    _skip_next_stop_event_until_started = False

    _resume_status = dict()

    def playTimer(self, timer: Timer) -> None:

        def _save_resume(_timer: Timer) -> None:

            for _type in player_utils.get_types_replaced_by_type(_timer.media_type):

                _resume_status = self._getResumeStatus(_type)
                if _timer.is_resuming_timer():
                    _active_players = self.getActivePlayersWithPlaylist(type=_type)
                    if not _resume_status or _resume_status.isResuming():
                        self._resume_status[_type] = PlayerStatus(
                            _timer, state=_active_players[_type] if _type in _active_players else None)

                    else:
                        _resume_status.setTimer(_timer)

                elif _resume_status:
                    self.resetResumeStatus(_type)

        def _get_delay_for_seektime(_timer: Timer) -> timedelta:

            seektime = None
            if self._seek_delayed_timer and _timer.is_play_at_start_timer():
                td_now = self._getNow()
                period = timer.get_matching_period(td_now)
                if period:
                    seektime = datetime_utils.abs_time_diff(
                        td_now, period.getStart())
                    seektime = None if seektime * 1000 <= self._RESPITE else seektime

            return seektime

        _save_resume(timer)

        path, state_from_path = player_utils.parse_player_state_from_path(timer.path)

        files, type = self._getFilesAndType(
            path, type=timer.media_type)

        if self._isPlaying(files, type, repeat=player_utils.REPEAT_ALL if timer.repeat else player_utils.REPEAT_OFF):
            return

        if state_from_path:
            seektime = state_from_path.time
        else:
            seektime = _get_delay_for_seektime(timer)

        if type == PICTURE:
            beginSlide = files[(seektime // self._getSlideshowStaytime()) %
                               len(files)] if seektime else None
            self._playSlideShow(path=path,
                                shuffle=timer.shuffle, beginSlide=beginSlide)

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

    def _playAV(self, playlist: xbmc.PlayList, startpos=0, seektime=None, repeat=player_utils.REPEAT_OFF, shuffled=False, speed=1.0) -> None:

        self._playlist = playlist
        self._seektime = seektime
        self._skip_next_stop_event_until_started = True

        if playlist.getPlayListId() == TYPES.index(VIDEO):
            self.stopPlayer(PICTURE)

        self.setRepeat(repeat)
        self.setShuffled(shuffled)
        self.setSpeed(speed)
        xbmc.executebuiltin("CECActivateSource")
        self.play(playlist, startpos=startpos)

    def _playSlideShow(self, path: str, beginSlide=None, shuffle=False) -> None:

        player_utils.play_slideshow(
            path=path, beginSlide=beginSlide, shuffle=shuffle)

    def _isPlaying(self, files, type, repeat=player_utils.REPEAT_OFF) -> bool:

        ap = self.getActivePlayersWithPlaylist(type)
        return type in ap and files == [e["file"] for e in ap[type].playlist] and ap[type].repeat == repeat

    def _getFilesAndType(self, path: str, type=None) -> 'tuple[list[str],str]':

        return get_files_and_type(path)

    def _buildPlaylist(self, paths: 'list[str]', type: str, label: str) -> 'xbmc.PlayList':

        return convert_to_playlist(paths=paths, type=type, label=label)

    def stopPlayer(self, type: str) -> 'player_utils.State':

        return player_utils.stop_player(type)

    def onAVStarted(self) -> None:

        self._skip_next_stop_event_until_started = False
        if self._recent_volume == None:
            self._recent_volume = self.getVolume()
        self._seekRetroactivly()

    def onPlayBackStopped(self) -> None:

        if self._skip_next_stop_event_until_started:
            self._skip_next_stop_event_until_started = False

        else:
            self._reset()

    def onPlayBackEnded(self) -> None:

        if VIDEO in self._resume_status:
            self._resumeFormer(type=VIDEO, keep=True)

        elif AUDIO in self._resume_status:
            self._resumeFormer(type=AUDIO, keep=True)

    def onPlayBackError(self) -> None:

        self._reset()

    def resumeFormerOrStop(self, timer: Timer) -> None:

        if not timer.is_resuming_timer() or not self._resumeFormer(type=timer.media_type, keep=False):
            if timer.media_type == PICTURE:
                self.stopPlayer(PICTURE)
            else:
                self.stop()

            self._reset(type=timer.media_type)
            xbmc.sleep(self._RESPITE)

        self.resetResumeOfTimer(timer)

    def _resumeFormer(self, type: str, keep=False) -> bool:

        resuming = False

        for _type in player_utils.get_types_replaced_by_type(type):

            resumeState = self._getResumeStatus(_type)
            if resumeState and resumeState.getState():
                state = resumeState.getState()
                if not keep:
                    self.resetResumeStatus(_type)

                if not resumeState.isResuming():
                    xbmc.sleep(self._RESPITE)
                    paths = [item["file"] for item in state.playlist]
                    if self._isPlaying(files=paths, type=_type, repeat=state.repeat):
                        pass

                    elif _type in [VIDEO, AUDIO]:
                        label = state.playlist[state.position]["label"] if state.position < len(state.playlist) else ""
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
                        resumeState.setResuming(True)

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
            if resumeState and resumeState.getTimer().id == timer.id:
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
            if self._playlist and self._playlist.getposition() < self._playlist.size() - 1:
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
        if tries == self._MAX_TRIES or _totalTime < 1:
            self._resetSeek()

        elif self._seektime >= _totalTime:
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

        self._playlist = None
        self._skip_next_stop_event_until_started = False
        self._resetSeek()
        self.resetResumeStatus(type)

        self.setRepeat(player_utils.REPEAT_OFF)
        self.setShuffled(False)

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

    def _getNow(self) -> timedelta:

        dt_now, td_now = datetime_utils.get_now()
        return td_now
