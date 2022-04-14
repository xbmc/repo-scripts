from resources.lib.timer.period import Period
from resources.lib.timer.timer import Timer


class TimerWithPeriod:

    _timer = None
    _period = None

    def __init__(self, timer: Timer, period: Period) -> None:

        self._timer = timer
        self._period = period

    def getTimer(self) -> Timer:

        return self._timer

    def getPeriod(self) -> Period:

        return self._period
