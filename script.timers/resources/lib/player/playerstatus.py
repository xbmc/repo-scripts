from resources.lib.player import player_utils
from resources.lib.timer.timer import Timer


class PlayerStatus():

    def __init__(self, timer: Timer, state: player_utils.State):
        self.timer: Timer = timer
        self.state: player_utils.State = state
        self.resuming: bool = False
