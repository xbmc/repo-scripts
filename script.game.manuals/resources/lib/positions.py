# -*- coding: utf-8 -*-
"""The page each manual was left open at."""

import json

#: Enough for every manual anyone reads more than once; the oldest go first
KEPT = 500


class Positions(object):
    def __init__(self, path, read, write):
        """read(path) gives the file's text or None; write(path, text) saves it."""
        self.path = path
        self.write_text = write
        try:
            self.pages = json.loads(read(path) or "{}")
        except ValueError:
            self.pages = {}
        if not isinstance(self.pages, dict):
            self.pages = {}

    def page(self, manual):
        value = self.pages.get(manual)
        return value if isinstance(value, int) and value >= 0 else 0

    def remember(self, manual, page):
        # Kept in the order last read, so the oldest are the ones dropped
        self.pages.pop(manual, None)
        if page > 0:
            self.pages[manual] = page
        while len(self.pages) > KEPT:
            self.pages.pop(next(iter(self.pages)))
        self.write_text(self.path, json.dumps(self.pages))
