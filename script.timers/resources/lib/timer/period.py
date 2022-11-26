from datetime import timedelta


class Period:

    def __init__(self, start: timedelta, end: timedelta) -> None:

        self.start: timedelta = start
        self.end: timedelta = end
