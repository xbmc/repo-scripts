import json
import os

import xbmcgui
import xbmcvfs

# noinspection PyPackages
from .constants import PROFILE
# noinspection PyPackages
from .logger import Logger
# noinspection PyPackages
from .notify import Notify


def title_key(title):
    """
    The key a TV show can be stored under: its title, ignoring case and surrounding whitespace.

    :param title: the show's title, as Kodi reports it
    :return: the normalised key
    """
    return title.strip().casefold()


class ShowList:
    """
    A persistent list of TV shows, kept as a small JSON file (a dict of key -> display title) in the
    calling addon's profile folder - e.g. shows to ignore, or to treat specially. The key is used for
    lookups (the caller chooses it - a library id, or title_key()), the title is used for display.
    """

    def __init__(self, filename):
        """
        :param filename: the name of the JSON file, inside the calling addon's profile folder
        """
        self.path = os.path.join(PROFILE, filename)
        self._shows = {}
        # Set if the file was unreadable and couldn't be backed up - save() then refuses to overwrite it
        self._save_blocked = False
        self.load()

    def __len__(self):
        return len(self._shows)

    def __contains__(self, key):
        return self.contains(key)

    def exists(self):
        """
        :return: True if the list's file is on disk
        """
        return xbmcvfs.exists(self.path)

    def load(self):
        """
        (Re)load the list from disk - a missing file just gives an empty list, and an unreadable one
        also does, but is first copied to <name>.bad so the next save() can't destroy it (and if that
        copy fails, save() refuses to write until a load() succeeds).
        """
        self._shows = {}
        self._save_blocked = False
        previous_path = self.path + '.old'
        if not xbmcvfs.exists(self.path) and xbmcvfs.exists(previous_path):
            # A save was interrupted while replacing the file (see save()) - put the last good list back
            Logger.warning(f'Recovering show list {self.path} from {previous_path}')
            xbmcvfs.rename(previous_path, self.path)
        if not xbmcvfs.exists(self.path):
            return
        try:
            with xbmcvfs.File(self.path) as f:
                data = json.loads(f.read())
            if not isinstance(data, dict):
                raise ValueError('not a JSON object')
        except (OSError, ValueError) as e:
            if xbmcvfs.copy(self.path, self.path + '.bad'):
                Logger.warning(f'Could not load show list {self.path}: {e} - kept a copy as {self.path}.bad')
            else:
                self._save_blocked = True
                Logger.error(f'Could not load show list {self.path}: {e} - and could not back it up, so it will not be overwritten')
            return
        self._shows = {str(key): str(title) for key, title in data.items()}

    def save(self):
        """
        Write the list to disk, via a temporary file so a half-written file never replaces the saved one.

        :return: True if the list was saved
        """
        if self._save_blocked:
            Logger.error(f'Not saving show list {self.path}: the unreadable file there could not be backed up')
            return False
        folder = os.path.dirname(self.path)
        if not xbmcvfs.exists(folder):
            xbmcvfs.mkdirs(folder)
        temporary_path = self.path + '.tmp'
        with xbmcvfs.File(temporary_path, 'w') as f:
            written = f.write(json.dumps(self._shows, ensure_ascii=False, indent=2))
        if not written:
            Logger.error(f'Could not write show list {temporary_path} - the saved list is unchanged')
            xbmcvfs.delete(temporary_path)
            return False
        if not xbmcvfs.rename(temporary_path, self.path):
            # Some platforms won't rename over an existing file, so move the old list aside (rather than
            # deleting it) until the new one is definitely in place
            previous_path = self.path + '.old'
            xbmcvfs.delete(previous_path)
            if not xbmcvfs.rename(self.path, previous_path) or not xbmcvfs.rename(temporary_path, self.path):
                if not xbmcvfs.exists(self.path) and xbmcvfs.exists(previous_path):
                    xbmcvfs.rename(previous_path, self.path)
                Logger.error(f'Could not replace show list {self.path} - the saved list is unchanged')
                return False
            xbmcvfs.delete(previous_path)
        return True

    def contains(self, key):
        """
        :param key: the show's key
        :return: True if the show is on the list
        """
        return str(key) in self._shows

    def add(self, key, title):
        """
        Add a show (or update its title) - call save() to keep the change.
        """
        self._shows[str(key)] = str(title)

    def update(self, shows):
        """
        Add several shows (or update their titles) - call save() to keep the change.

        :param shows: a dict of key -> title
        """
        for key, title in shows.items():
            self.add(key, title)

    def remove(self, keys):
        """
        Remove shows - call save() to keep the change.

        :param keys: the key of the show to remove, or a list of keys
        """
        if isinstance(keys, (str, int)):
            keys = [keys]
        for key in keys:
            self._shows.pop(str(key), None)

    def clear(self):
        """
        Remove every show - call save() to keep the change.
        """
        self._shows = {}

    def get(self, key, default=None):
        """
        :param key: the show's key
        :param default: what to return if the show isn't on the list
        :return: the show's title
        """
        return self._shows.get(str(key), default)

    def keys(self):
        """
        :return: the keys, sorted by title
        """
        return [key for key, _ in self.items()]

    def items(self):
        """
        :return: (key, title) pairs, sorted by title
        """
        return sorted(self._shows.items(), key=lambda pair: (pair[1].casefold(), pair[0]))

    def manage(self, heading, empty_message):
        """
        Show a dialog listing the shows, and remove the ones the user selects.

        :param heading: the dialog heading
        :param empty_message: what to tell the user if there's nothing on the list
        :return: the (key, title) pairs that were removed - empty (so falsy) if nothing was
        """
        self.load()
        items = self.items()
        if not items:
            Notify.info(empty_message)
            return []

        selected = xbmcgui.Dialog().multiselect(heading, [title for _, title in items])
        if not selected:
            return []

        removed = [items[index] for index in selected]
        Logger.info(f'Removing from {self.path}: {[title for _, title in removed]}')
        self.remove([key for key, _ in removed])
        if not self.save():
            self.load()
            return []
        return removed
