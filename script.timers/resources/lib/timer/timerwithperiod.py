from resources.lib.timer.period import Period
from resources.lib.timer.timer import Timer


class TimerWithPeriod:

    def __init__(self, timer: Timer, period: Period) -> None:
        self.timer: Timer = timer
        self.period: Period = period
