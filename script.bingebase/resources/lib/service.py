import sys
import time

import xbmc

from resources.lib.utils import (
    get_setting, get_setting_bool, get_sync_interval_hours,
    log, log_error, notify, reload_addon
)

POLL_INTERVAL = 300  # 5 minutes


class BingebaseMonitor(xbmc.Monitor):
    def __init__(self, service):
        super().__init__()
        self.service = service

    def onSettingsChanged(self):
        log('Settings changed, reloading')
        reload_addon()
        self.service.reload_api()
        self.service.check_token_changed()

    def onScanFinished(self, library):
        if library == 'video' and get_setting_bool('sync_on_library_update'):
            log('Library scan finished, triggering sync')
            self.service.trigger_sync()


class BingebaseService:
    def __init__(self):
        self.api = None
        self.player = None
        self.monitor = None
        self.last_sync_time = 0
        self._sync_requested = False
        self._last_known_token = ''

    def reload_api(self):
        from resources.lib.api import BingebaseAPI
        token = get_setting('access_token')
        if token:
            self.api = BingebaseAPI()
            if self.player:
                self.player.api = self.api
        else:
            self.api = None

    def check_token_changed(self):
        token = get_setting('access_token')
        if token and token != self._last_known_token:
            log('Token changed, triggering sync')
            self._last_known_token = token
            self.trigger_sync()

    def trigger_sync(self):
        self._sync_requested = True

    def _do_sync(self):
        if not self.api:
            return
        try:
            from resources.lib.sync import do_sync
            do_sync(self.api)
            self.last_sync_time = time.time()
        except Exception:
            log_error('Sync error')

    def _should_scheduled_sync(self):
        interval_hours = get_sync_interval_hours()
        if interval_hours == 0:
            return False

        elapsed = time.time() - self.last_sync_time
        return elapsed >= (interval_hours * 3600)

    def run(self):
        from resources.lib.player import BingebasePlayer
        from resources.lib.auth import is_connected, start_authorization

        log('Bingebase service starting')

        self.monitor = BingebaseMonitor(self)
        self._last_known_token = get_setting('access_token')
        self.reload_api()

        if not is_connected():
            log('Not connected — showing authorization dialog')
            start_authorization()
            reload_addon()
            self._last_known_token = get_setting('access_token')
            self.reload_api()

        if self.api:
            self.player = BingebasePlayer(self.api)
        else:
            self.player = BingebasePlayer(api=None)
            log('Not connected — scrobbling disabled')

        if get_setting_bool('sync_on_startup') and self.api:
            self._do_sync()

        sync_check = 0
        while not self.monitor.abortRequested():
            self.player.update_time()

            if self._sync_requested:
                self._sync_requested = False
                self._do_sync()

            sync_check += 5
            if sync_check >= POLL_INTERVAL:
                sync_check = 0
                if self._should_scheduled_sync():
                    self._do_sync()

            if self.monitor.waitForAbort(5):
                break

        log('Bingebase service stopped')


def main():
    if len(sys.argv) > 1:
        action = sys.argv[1]

        if action == 'authorize':
            from resources.lib.auth import start_authorization
            start_authorization()
            return

        if action == 'disconnect':
            from resources.lib.auth import disconnect
            disconnect()
            return

        if action == 'sync_now':
            from resources.lib.auth import is_connected
            if is_connected():
                from resources.lib.api import BingebaseAPI
                from resources.lib.sync import do_sync
                do_sync(BingebaseAPI())
            else:
                notify('Not connected to Bingebase')
            return

    service = BingebaseService()
    service.run()
