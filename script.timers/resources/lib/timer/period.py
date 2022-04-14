from datetime import timedelta


class Period:

    _start = None
    _end = None

    def __init__(self, start: timedelta, end: timedelta) -> None:

        self._start = start
        self._end = end

    def getStart(self) -> timedelta:

        return self._start

    def getEnd(self) -> timedelta:

        return self._end
