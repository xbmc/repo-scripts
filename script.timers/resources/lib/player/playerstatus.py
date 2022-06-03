from resources.lib.player import player_utils
from resources.lib.timer.timer import Timer


class PlayerStatus():

    _timer = None
    _state = None
    _resuming = False

    def __init__(self, timer: Timer, state: player_utils.State):
        self._timer = timer
        self._state = state
        self._resuming = False

    def setTimer(self, timer: Timer) -> None:

        self._timer = timer

    def getTimer(self) -> Timer:

        return self._timer

    def getState(self) -> player_utils.State:

        return self._state

    def isResuming(self) -> bool:

        return self._resuming

    def setResuming(self, resuming: bool) -> None:

        self._resuming = resuming
