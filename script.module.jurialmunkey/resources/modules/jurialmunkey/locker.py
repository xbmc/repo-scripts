import xbmcvfs
from jurialmunkey.tmdate import get_timestamp, set_timestamp


class _MutexLock():
    def __init__(self, lockfile, timeout=10, polling=0.05, kodi_log=None):
        """ ContextManager for mutex lock """
        self._timeout = timeout
        self._polling = polling
        self._lockfile = lockfile
        self._kodi_log = kodi_log
        self.lock_aquire()

    @property
    def monitor(self):
        try:
            return self._monitor
        except AttributeError:
            from xbmc import Monitor
            self._monitor = Monitor()
            return self._monitor

    @property
    def kodi_log(self):
        try:
            return self._kodi_log
        except AttributeError:
            from jurialmunkey.logger import Logger
            self._kodi_log = Logger('[script.module.jurialmunkey]\n')
            return self._kodi_log

    @property
    def time_exp(self):
        try:
            return self._time_exp
        except AttributeError:
            self._time_exp = set_timestamp(self._timeout)
            return self._time_exp

    def lock_return(self):
        # Aquire lock if available
        if not self.lock_exists():
            return self.lock_create()

        # Early exit: System abort
        if self.monitor.abortRequested():
            return -1

        # Early exit: Timed out while waiting
        if not get_timestamp(self.time_exp):
            self.kodi_log(f'{self._lockfile} Timeout!', 1)
            return -1

        return 1

    def lock_aquire(self):
        # Check if we can aquire lock and return to do function if we can
        self.lockstate = self.lock_return()
        if self.lockstate == self._lockfile:
            return

        # If we cant get lock then wait in loop until we can (or abort or timeout)
        while self.lockstate == 1:
            self.monitor.waitForAbort(self._polling)
            self.lockstate = self.lock_return()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, exc_traceback):
        self.lock_delete()


class MutexFileLock(_MutexLock):

    def lock_exists(self):
        with xbmcvfs.File(self._lockfile, 'r') as f:
            data = f.read()
        if data == '1':
            return self._lockfile

    def lock_create(self):
        with xbmcvfs.File(self._lockfile, 'w') as f:
            f.write('1')
        return self._lockfile

    def lock_delete(self):
        with xbmcvfs.File(self._lockfile, 'w') as f:
            f.write('0')


class MutexPropLock(_MutexLock):

    @property
    def window(self):
        try:
            return self._window
        except AttributeError:
            from jurialmunkey.window import WindowPropertySetter
            self._window = WindowPropertySetter()
            return self._window

    def lock_exists(self):
        if self.window.get_property(self._lockfile):
            return self._lockfile

    def lock_create(self):
        self.window.get_property(self._lockfile, set_property='locked')
        return self._lockfile

    def lock_delete(self):
        if not self.lock_exists():
            return
        self.window.get_property(self._lockfile, clear_property=True)
