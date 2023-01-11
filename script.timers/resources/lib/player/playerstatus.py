from resources.lib.player import player_utils
from resources.lib.timer.timer import Timer


class PlayerStatus():

    def __init__(self, timer: Timer, state: player_utils.State):
        self.timer: Timer = timer
        self.state: player_utils.State = state
        self.resuming: bool = False

    def __str__(self) -> str:

        return "PlayerStatus[timer=%s, state=%s, resuming=%s]" % (self.timer, self.state, self.resuming)
