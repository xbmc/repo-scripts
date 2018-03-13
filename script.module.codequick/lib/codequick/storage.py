# -*- coding: utf-8 -*-
from __future__ import absolute_import

# Standard Library Imports
from hashlib import sha1
import sys
import os

try:
    import cPickle as pickle
except ImportError:  # pragma: no cover
    import pickle

# Package imports
from codequick.script import Script
from codequick.utils import ensure_unicode

__all__ = ["PersistentDict", "PersistentList"]

# The addon profile directory
profile_dir = Script.get_info("profile")


class _PersistentBase(object):
    """
    Base class to handle persistent file handling.

    :param name: Filename of persistence storage file.
    :type name: str or unicode
    """

    def __init__(self, name):
        super(_PersistentBase, self).__init__()
        self._serializer_obj = object
        self._stream = None
        self._hash = None

        # Filename is already a fullpath
        if os.path.sep in name:
            self._filepath = ensure_unicode(name)
            data_dir = os.path.dirname(self._filepath)
        else:
            # Filename must be relative, joining profile directory with filename
            self._filepath = os.path.join(profile_dir, ensure_unicode(name))
            data_dir = profile_dir

        # Ensure that filepath is bytes when platform type is linux/bsd
        if not sys.platform.startswith("win"):  # pragma: no branch
            self._filepath = self._filepath.encode("utf8")
            data_dir = data_dir.encode("utf8")

        # Create any missing data directory
        if not os.path.exists(data_dir):
            os.makedirs(data_dir)

    def _load(self):
        """Load in existing data from disk."""
        # Load storage file if exists
        if os.path.exists(self._filepath):
            self._stream = file_obj = open(self._filepath, "rb+")
            content = file_obj.read()

            # Calculate hash of current file content
            self._hash = sha1(content).hexdigest()

            # Load content and update storage
            return pickle.loads(content)

    def flush(self):
        """
        Syncrnize data back to disk.

        Data will only be written to disk if content has changed.
        """
        # Serialize the storage data
        content = pickle.dumps(self._serialize(), protocol=2)  # Protocol 2 is used for python2/3 compatibility
        current_hash = sha1(content).hexdigest()

        # Compare saved hash with current hash, to detect if content has changed
        if self._hash is None or self._hash != current_hash:
            # Check if FileObj Needs Creating First
            if self._stream:
                self._stream.seek(0)
                self._stream.truncate(0)
            else:
                self._stream = open(self._filepath, "wb+")

            # Dump data out to disk
            self._stream.write(content)
            self._hash = current_hash
            self._stream.flush()

    def close(self):
        """Close file object."""
        if self._stream:
            self._stream.close()
            self._stream = None

    def __enter__(self):
        return self

    def __exit__(self, *_):
        self.close()

    def _serialize(self):  # pragma: no cover
        pass


class PersistentDict(_PersistentBase, dict):
    """
    Persistent storage with a :class:`dictionary<dict>` like interface.

    This class inherits all methods from the build-in data type :class:`dict`.

    :param name: Filename or path to storage file.
    :type name: str or unicode

    .. note::

        ``name`` can be the filename of a file, or the full path to a file.
        The add-on profile directory will be the default location for files, unless a full path is given.

    .. note:: This class is also designed as a context manager.

    :Example:
        >>> with PersistentDict("dictfile.pickle") as db:
        >>>     db["testdata"] = "testvalue"
        >>>     db.flush()
    """

    def __init__(self, name):
        super(PersistentDict, self).__init__(name)
        current_data = self._load()
        if current_data:
            self.update(current_data)

    def _serialize(self):
        return dict(self)


class PersistentList(_PersistentBase, list):
    """
    Persistent storage with a :class:`list` like interface.

    This class inherits all methods from the build-in data type :class:`list`.

    :param name: Filename or path to storage file.
    :type name: str or unicode

    .. note::

        ``name`` can be the filename of a file, or the full path to a file.
        The add-on profile directory will be the default location for files, unless a full path is given.

    .. note:: This class is also designed as a context manager.

    :Example:
        >>> with PersistentList("listfile.pickle") as db:
        >>>     db.append("testvalue")
        >>>     db.extend(["test1", "test2"])
        >>>     db.flush()
    """

    def __init__(self, name):
        super(PersistentList, self).__init__(name)
        current_data = self._load()
        if current_data:
            self.extend(current_data)

    def _serialize(self):
        return list(self)
