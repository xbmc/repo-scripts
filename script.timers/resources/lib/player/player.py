import xbmc
from resources.lib.player import player_utils
from resources.lib.player.playerstatus import PlayerStatus
from resources.lib.timer.timer import Timer
from resources.lib.utils import datetime_utils, vfs_utils


class Player(xbmc.Player):

    _MAX_TRIES = 10
    _RESPITE = 3000

    _seek_delayed_timer = False
    _default_volume = 100

    _seektime = None
    _playlist = None
    _resume_status = None
    _skip_next_stop_event_until_started = False

    def playTimer(self, timer: Timer) -> None:

        def _save_resume(_timer: Timer) -> None:

            if _timer.b_resume and _timer.is_play_at_start_timer() and _timer.is_stop_at_end_timer():
                if not self._resume_status:
                    self._resume_status = PlayerStatus(
                        _timer.i_timer, player_utils.get_active_player_with_playlist())

                else:
                    self._getResumeStatus().setTimerId(_timer.i_timer)

            else:
                self._resume_status = None

        def _get_delay_for_seektime(_timer: Timer) -> None:

            if self._seek_delayed_timer and _timer.is_play_at_start_timer():
                t_now, td_now = datetime_utils.get_now()
                td_start = datetime_utils.parse_time(
                    _timer.s_start, t_now.tm_wday)
                seektime = datetime_utils.abs_time_diff(
                    td_now, td_start)
            else:
                seektime = None

            return seektime

        _save_resume(timer)

        playlist = vfs_utils.build_playlist_from_url(timer.s_filename)
        seektime = _get_delay_for_seektime(timer)
        self._playExtra(playlist=playlist,
                        seektime=seektime,
                        repeat=player_utils.REPEAT_ALL if timer.b_repeat else player_utils.REPEAT_OFF)

    def _getResumeStatus(self) -> PlayerStatus:

        return self._resume_status

    def _playExtra(self, playlist, startpos=0, seektime=None, repeat=player_utils.REPEAT_OFF, shuffled=False, speed=1.0) -> None:

        self._playlist = playlist
        self._seektime = seektime
        self._skip_next_stop_event_until_started = True

        xbmc.executebuiltin("CECActivateSource")
        self.play(playlist, startpos=startpos)
        player_utils.set_repeat(repeat)
        player_utils.set_shuffled(shuffled)
        player_utils.set_speed(speed)

    def onAVStarted(self) -> None:

        self._skip_next_stop_event_until_started = False
        self._seekRetroactivly()

    def onPlayBackStopped(self) -> None:

        if self._skip_next_stop_event_until_started:
            self._skip_next_stop_event_until_started = False

        else:
            self._reset()

    def onPlayBackError(self) -> None:

        self._reset()

    def _seekRetroactivly(self) -> None:

        if not self._seektime:
            return

        tries = 0
        xbmc.sleep(500)
        while not self.isPlaying() and tries < self._MAX_TRIES:
            xbmc.sleep(300)
            tries += 1

        if tries == self._MAX_TRIES or self.getTotalTime() < 1:
            self._seektime = None

        elif self._seektime >= self.getTotalTime():
            if self._playlist and self._playlist.getposition() < self._playlist.size() - 1:
                self._seektime -= self.getTotalTime()
                self._skip_next_stop_event_until_started = True
                self.playnext()
            else:
                self._seektime = None

        else:
            seektime = self._seektime
            self._seektime = None
            self.seekTime(seektime)

    def resumeFormerOrStop(self) -> None:

        resumState = self._getResumeStatus()
        if resumState and resumState.getState():
            state = resumState.getState()
            urls = list(
                map(lambda item: item["file"], state.playlist))
            playlist = vfs_utils.build_playlist_from_urls(
                urls, type=state.type)
            self._resume_status = None

            xbmc.sleep(self._RESPITE)
            self._playExtra(
                playlist,
                startpos=state.position,
                seektime=state.time,
                repeat=state.repeat,
                shuffled=state.shuffled,
                speed=state.speed)

        else:
            self.stop()
            self._reset()
            xbmc.sleep(self._RESPITE)

    def set_seek_delayed_timer(self, _seek_delayed_timer: bool) -> None:

        self._seek_delayed_timer = _seek_delayed_timer

    def reset_resume_of_timer(self, timer: Timer):

        resumState = self._getResumeStatus()
        if resumState and resumState.getTimerId() == timer.i_timer:
            self._resume_status = None

    def resetResumeStatus(self) -> None:

        self._resume_status = None

    def _reset(self) -> None:

        self._playlist = None
        self._seektime = None
        self._resume_status = None
        self._skip_next_stop_event_until_started = False

        player_utils.set_repeat(player_utils.REPEAT_OFF)

    def get_volume(self) -> int:

        return player_utils.get_volume(or_default=self._default_volume)

    def set_volume(self, volume: int) -> None:

        return player_utils.set_volume(volume)

    def get_default_volume(self) -> int:

        return self._default_volume

    def set_default_volume(self, volume) -> None:

        self._default_volume = volume
