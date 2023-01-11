from datetime import timedelta


class Period:

    def __init__(self, start: timedelta, end: timedelta) -> None:

        self.start: timedelta = start
        self.end: timedelta = end

    def __str__(self) -> str:
        return "Period[start=%s, end=%s]" % (self.start, self.end)
