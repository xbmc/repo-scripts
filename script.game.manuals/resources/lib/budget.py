# -*- coding: utf-8 -*-
"""Keeps the manuals this add-on downloaded within a size the player chose.

A manual runs from a few hundred kilobytes to well over a hundred megabytes,
and a large collection would otherwise fill a disk one download at a time.

Only manuals this add-on fetched are tracked, and only tracked manuals are
ever deleted. A manual the player put beside their games is never in here, so
it can never be removed - which matters, because these files live in the
player's own games folders rather than somewhere the add-on owns.

The least recently opened go first, not the oldest: a manual worth keeping is
one that gets referred back to.
"""

import json

MEGABYTE = 1024 * 1024


class Budget(object):
    def __init__(self, path, read, write):
        """read(path) gives the file's text or None; write(path, text) saves it."""
        self.path = path
        self.write_text = write
        try:
            manuals = json.loads(read(path) or "{}")
        except ValueError:
            manuals = {}
        self.manuals = {}
        for manual, entry in (manuals.items() if isinstance(manuals, dict) else []):
            if isinstance(entry, dict) and isinstance(entry.get("bytes"), int):
                self.manuals[manual] = {"bytes": entry["bytes"], "opened": float(entry.get("opened") or 0)}

    def add(self, manual, size, now):
        """A manual this add-on just downloaded."""
        self.manuals[manual] = {"bytes": int(size), "opened": now}
        self._save()

    def opened(self, manual, now):
        """A manual was read; does nothing for one the player supplied."""
        if manual in self.manuals:
            self.manuals[manual]["opened"] = now
            self._save()

    def total(self):
        return sum(entry["bytes"] for entry in self.manuals.values())

    def enforce(self, limit, keep, exists, delete):
        """Delete tracked manuals, least recently opened first, until within limit bytes.

        keep is spared - the manual about to be read. A tracked manual that has
        gone is forgotten rather than counted. Returns what was deleted.
        """
        for manual in [m for m in self.manuals if not exists(m)]:
            del self.manuals[manual]
        deleted = []
        for manual in sorted(self.manuals, key=lambda m: self.manuals[m]["opened"]):
            if self.total() <= limit:
                break
            if manual == keep:
                continue
            if delete(manual):
                deleted.append(manual)
                del self.manuals[manual]
        self._save()
        return deleted

    def _save(self):
        self.write_text(self.path, json.dumps(self.manuals))
