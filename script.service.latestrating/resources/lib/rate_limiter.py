from datetime import datetime, timedelta
import xbmc
from collections import deque

class RateLimiter:
    def __init__(self, calls_per_second=1):
        self.calls_per_second = calls_per_second
        self.calls = {}  # Dictionary to track calls for different sources

    def wait_for_token(self, source):
        """Wait until we can make another API call for the given source"""
        if source not in self.calls:
            self.calls[source] = deque(maxlen=self.calls_per_second)
            self.calls[source].append(datetime.now())
            return

        # Remove old timestamps
        now = datetime.now()
        while self.calls[source] and (now - self.calls[source][0]) > timedelta(seconds=1):
            self.calls[source].popleft()

        # If we've made too many calls in the last second, wait
        if len(self.calls[source]) >= self.calls_per_second:
            oldest_call = self.calls[source][0]
            wait_time = 1 - (now - oldest_call).total_seconds()
            if wait_time > 0:
                xbmc.sleep(int(wait_time * 1000))

    def add_call(self, source):
        """Record that we made an API call"""
        if source not in self.calls:
            self.calls[source] = deque(maxlen=self.calls_per_second)
        self.calls[source].append(datetime.now()) 