# -*- coding: utf-8 -*-
"""Track uninterrupted playback and the daily bedtime prompt."""
from datetime import datetime, timedelta
from time import monotonic


class WatchTimer:
    def __init__(self):
        self.elapsed = 0.0
        self.sample = None
        self.bedtime_acknowledged = None
        self.bedtime_pending = None

    def observe(self, filename, position, paused=False, now=None):
        now = monotonic() if now is None else now
        if paused:
            self.sample = None
            return
        try:
            position = float(position)
        except (ValueError, TypeError):
            self.sample = None
            return
        if self.sample:
            previous_file, previous_position, previous_time = self.sample
            wall = now - previous_time
            progress = position - previous_position
            if previous_file == filename and 0 < wall <= 3 and 0 < progress <= wall + 1:
                self.elapsed += min(wall, progress)
        self.sample = (filename, position, now)

    def suspend(self):
        self.sample = None

    def mark_bedtime(self, enabled, hour, minute, now=None):
        now = datetime.now() if now is None else now
        if not enabled:
            self.bedtime_pending = None
        elif 0 <= hour <= 23 and 0 <= minute <= 59:
            current = (now.hour, now.minute)
            bedtime = (hour, minute)
            night = None
            if current >= bedtime and (bedtime >= (6, 0) or current < (6, 0)):
                night = now.date()
            elif current < (6, 0) <= bedtime:
                night = now.date() - timedelta(days=1)
            if (night is not None and self.bedtime_acknowledged != night
                    and (self.bedtime_pending is None or night > self.bedtime_pending)):
                self.bedtime_pending = night

    def due(self, minutes, bedtime_enabled, hour, minute, *, now=None):
        now = datetime.now() if now is None else now
        self.mark_bedtime(bedtime_enabled, hour, minute, now=now)
        timed = minutes > 0 and self.elapsed >= minutes * 60
        bedtime = bedtime_enabled and self.bedtime_pending is not None
        return timed or bedtime

    def reset(self, acknowledge_bedtime=False):
        self.elapsed = 0.0
        self.sample = None
        if acknowledge_bedtime and self.bedtime_pending is not None:
            self.bedtime_acknowledged = self.bedtime_pending
            self.bedtime_pending = None
