from resources.lib.player import player_utils


class PlayerStatus():

    _i_timer = -1
    _state = None

    def __init__(self, i_timer: int, state: player_utils.State):
        self._i_timer = i_timer
        self._state = state

    def getTimerId(self) -> int:

        return self._i_timer

    def setTimerId(self, i_timer: int) -> None:

        self._i_timer = i_timer

    def getState(self) -> player_utils.State:

        return self._state
