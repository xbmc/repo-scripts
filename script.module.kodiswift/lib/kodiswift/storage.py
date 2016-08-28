# -*- coding: utf-8 -*-
"""
kodiswift.storage
-----------------

This module contains persistent storage classes.

:copyright: (c) 2012 by Jonathan Beluch
:license: GPLv3, see LICENSE for more details.
"""
from __future__ import absolute_import

import collections
import json
import os
import time
import shutil
from datetime import datetime

try:
    import cPickle as pickle
except ImportError:
    import pickle

__all__ = ['Formats', 'PersistentStorage', 'TimedStorage', 'UnknownFormat']


class UnknownFormat(Exception):
    pass


class Formats(object):
    PICKLE = 'pickle'
    JSON = 'json'


class PersistentStorage(collections.MutableMapping):
    def __init__(self, file_path, file_format=Formats.PICKLE):
        """
        Args:
            file_path (str):
            file_format (Optional[kodiswift.Formats]):
        """
        super(PersistentStorage, self).__init__()
        self.file_path = file_path
        self.file_format = file_format
        self._store = {}
        self._loaded = False

    def __getitem__(self, key):
        return self._store[key]

    def __setitem__(self, key, value):
        self._store[key] = value

    def __delitem__(self, key):
        del self._store[key]

    def __iter__(self):
        return iter(self._store)

    def __len__(self):
        return len(self._store)

    def __enter__(self):
        self.load()
        self.sync()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.sync()

    def __repr__(self):
        return '%s(%r)' % (self.__class__.__name__, self._store)

    def items(self):
        return self._store.items()

    def load(self):
        """Load the file from disk.

        Returns:
            bool: True if successfully loaded, False if the file
                doesn't exist.

        Raises:
            UnknownFormat: When the file exists but couldn't be loaded.
        """

        if not self._loaded and os.path.exists(self.file_path):
            with open(self.file_path, 'rb') as f:
                for loader in (pickle.load, json.load):
                    try:
                        f.seek(0)
                        self._store = loader(f)
                        self._loaded = True
                        break
                    except pickle.UnpicklingError:
                        pass
            # If the file exists and wasn't able to be loaded, raise an error.
            if not self._loaded:
                raise UnknownFormat('Failed to load file')
        return self._loaded

    def close(self):
        self.sync()

    def sync(self):
        temp_file = self.file_path + '.tmp'
        try:
            with open(temp_file, 'wb') as f:
                if self.file_format == Formats.PICKLE:
                    pickle.dump(self._store, f, 2)
                elif self.file_format == Formats.JSON:
                    json.dump(self._store, f, separators=(',', ':'))
                else:
                    raise NotImplementedError(
                        'Unknown file format ' + repr(self.file_format))
        except Exception:
            if os.path.exists(temp_file):
                os.remove(temp_file)
            raise
        shutil.move(temp_file, self.file_path)


class TimedStorage(PersistentStorage):
    """A dict with the ability to persist to disk and TTL for items."""

    def __init__(self, file_path, ttl=None, **kwargs):
        """
        Args:
            file_path (str):
            ttl (Optional[int]):
        """
        super(TimedStorage, self).__init__(file_path, **kwargs)
        self.ttl = ttl

    def __setitem__(self, key, value):
        self._store[key] = (value, time.time())

    def __getitem__(self, item):
        val, timestamp = self._store[item]
        ttl_diff = datetime.utcnow() - datetime.utcfromtimestamp(timestamp)
        if self.ttl and ttl_diff > self.ttl:
            del self._store[item]
            raise KeyError
        return val

    def __repr__(self):
        return '%s(%r)' % (self.__class__.__name__,
                           dict((k, v[0]) for k, v in self._store.items()))

    def items(self):
        items = []
        for k in self._store.keys():
            try:
                items.append((k, self[k]))
            except KeyError:
                pass
        return items

    def sync(self):
        super(TimedStorage, self).sync()
