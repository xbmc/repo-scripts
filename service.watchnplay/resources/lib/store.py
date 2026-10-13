# -*- coding: utf-8 -*-
# SPDX-License-Identifier: MIT
"""Persistenter Zustand unter addon_data.

Drei Dateien, damit Skript (default.py) und Dienst sich nicht gegenseitig ueberschreiben:
- auth.json:  Token + Name, schreiben nur Kopplung/Trennung (und der Dienst bei 401)
- state.json: Dienst-Zustand (Version, Pro-Pause, letzter Abgleich)
- queue.json: wartende Wiedergaben und Einzel-Aenderungen, ueberlebt Neustarts
"""

import json
import os

MAX_PLAYS = 1000
MAX_DELTAS = 5000


def _read(path, default):
    try:
        with open(path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        return data if isinstance(data, type(default)) else default
    except (OSError, ValueError):
        return default


def _write(path, data):
    # Zwischendatei je Prozess: Dienst und Skript schreiben sonst in dieselbe .tmp
    tmp = '%s.%d.tmp' % (path, os.getpid())
    try:
        with open(tmp, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, separators=(',', ':'))
            f.flush()
            # erst auf der Speicherkarte, dann umbenennen: nach Stromausfall keine leere Datei
            os.fsync(f.fileno())
        os.replace(tmp, path)
    except OSError:
        try:
            os.remove(tmp)
        except OSError:
            pass
        raise


class Store(object):
    def __init__(self, base_dir):
        self.base_dir = base_dir
        if not os.path.isdir(base_dir):
            os.makedirs(base_dir)
        self._auth_path = os.path.join(base_dir, 'auth.json')
        self._state_path = os.path.join(base_dir, 'state.json')
        self._queue_path = os.path.join(base_dir, 'queue.json')
        self._auth = {}
        self._auth_mtime = None
        self.state = _read(self._state_path, {})
        q = _read(self._queue_path, {})
        self.plays = q.get('plays') if isinstance(q.get('plays'), list) else []
        self.deltas = q.get('deltas') if isinstance(q.get('deltas'), dict) else {}
        self._dirty = False
        self.reload_auth(force=True)

    # --- auth ---
    def reload_auth(self, force=False):
        try:
            mtime = os.path.getmtime(self._auth_path)
        except OSError:
            mtime = None
        if force or mtime != self._auth_mtime:
            self._auth_mtime = mtime
            self._auth = _read(self._auth_path, {}) if mtime is not None else {}
        return self._auth

    @property
    def auth(self):
        return self.reload_auth()

    @property
    def token(self):
        return self.auth.get('token')

    def set_auth(self, token, user_name=None, back_sync=None):
        data = {'token': token, 'userName': user_name, 'backSync': back_sync}
        _write(self._auth_path, data)
        self.reload_auth(force=True)

    def clear_auth(self):
        try:
            os.remove(self._auth_path)
        except OSError:
            pass
        self.reload_auth(force=True)

    # --- state ---
    def save_state(self):
        _write(self._state_path, self.state)

    def reset_state(self):
        self.state = {}
        self.save_state()

    # --- queue ---
    def add_play(self, play):
        self.plays.append(play)
        if len(self.plays) > MAX_PLAYS:
            self.plays = self.plays[-MAX_PLAYS:]
        self.save_queue()

    def add_delta(self, kid, ts):
        """Merkt die Aenderung; geschrieben wird gesammelt (save_if_dirty im naechsten Takt).

        Eine ganze Staffel als gesehen markiert sind sonst hunderte Schreibvorgaenge der
        wachsenden Datei (schlecht fuer SD-Karten)."""
        self.deltas[kid] = ts
        if len(self.deltas) > MAX_DELTAS:
            oldest = sorted(self.deltas.items(), key=lambda kv: kv[1])[:len(self.deltas) - MAX_DELTAS]
            for k, _ in oldest:
                self.deltas.pop(k, None)
        self._dirty = True

    def save_if_dirty(self):
        if self._dirty:
            self.save_queue()

    def clear_queue(self):
        self.plays = []
        self.deltas = {}
        self.save_queue()

    def save_queue(self):
        self._dirty = False
        _write(self._queue_path, {'plays': self.plays, 'deltas': self.deltas})
