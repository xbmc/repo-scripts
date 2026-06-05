import json
import os
import time
import xbmc
import xbmcaddon
import xbmcgui
import xbmcvfs

ADDON = xbmcaddon.Addon()
ADDON_ID = ADDON.getAddonInfo('id')
ADDON_PATH = ADDON.getAddonInfo('path')

ACTION_PREVIOUS_MENU = 10
ACTION_NAV_BACK = 92


def log(message, level=xbmc.LOGDEBUG):
    xbmc.log(f'[{ADDON_ID}] {message}', level)


HOME = xbmcgui.Window(10000)
PROP_PREFIX = 'Skiptro.'
ALL_PROPERTIES = ('HasData', 'HasIntro', 'HasCredits', 'HasStinger',
                  'InIntro', 'InCredits', 'DialogVisible', 'Skipping')


def set_property(name, value='true'):
    HOME.setProperty(PROP_PREFIX + name, value)


def clear_property(name):
    HOME.clearProperty(PROP_PREFIX + name)


def clear_all_properties():
    for name in ALL_PROPERTIES:
        clear_property(name)


_skip_init_monotonic = None


def seek_with_property(player, target):
    global _skip_init_monotonic
    _skip_init_monotonic = time.monotonic()
    set_property('Skipping')
    player.seekTime(target)


class SkiptroDialog(xbmcgui.WindowXMLDialog):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.skip_type = None
        self.seek_target = None
        self.stinger_target = None
        self.last_action_monotonic = time.monotonic()
        self.is_open = True

    def close(self):
        self.is_open = False
        super().close()

    def set_skip_info(self, skip_type, seek_target=None, stinger_target=None):
        self.skip_type = skip_type
        self.seek_target = seek_target
        self.stinger_target = stinger_target

    def onInit(self):
        if self.skip_type == 'intro':
            self.setFocusId(101)
        elif self.skip_type == 'credits':
            self.setFocusId(103 if self.stinger_target else 102)

    def onClick(self, controlId):
        player = xbmc.Player()

        try:
            if controlId == 101 and self.skip_type == 'intro':
                if self.seek_target is not None:
                    log(f'Skipping intro, seeking to {self.seek_target}s')
                    seek_with_property(player, self.seek_target)

            elif controlId == 102 and self.skip_type == 'credits':
                total_time = player.getTotalTime()
                seek_to = max(0, total_time - 2)
                log(f'Skipping credits, seeking to {seek_to}s')
                seek_with_property(player, seek_to)

            elif controlId == 103 and self.skip_type == 'credits':
                if self.stinger_target is not None:
                    log(f'Skipping to stinger at {self.stinger_target}s')
                    seek_with_property(player, self.stinger_target)
        except RuntimeError as e:
            log(f'Skip failed: {e}', xbmc.LOGWARNING)

        self.close()

    def onAction(self, action):
        self.last_action_monotonic = time.monotonic()
        if action.getId() in (ACTION_PREVIOUS_MENU, ACTION_NAV_BACK):
            log('Dialog dismissed by user')
            self.close()


class SkiptroPlayer(xbmc.Player):
    def __init__(self):
        super().__init__()
        self.skiptro_data = None
        self.current_file = None

    def onAVStarted(self):
        self.skiptro_data = None
        self._load_skiptro_data()

    def onPlayBackStopped(self):
        self._reset()

    def onPlayBackEnded(self):
        self._reset()

    def _reset(self):
        global _skip_init_monotonic
        log('Playback ended, resetting state')
        _skip_init_monotonic = None
        self.skiptro_data = None
        self.current_file = None
        clear_all_properties()

    def _load_skiptro_data(self):
        folder = xbmc.getInfoLabel('Player.Folderpath')
        filename = xbmc.getInfoLabel('Player.Filename')

        if not folder or not filename:
            log('Could not get folder/filename from InfoLabels', xbmc.LOGWARNING)
            return

        self.current_file = folder + filename
        base, _ = os.path.splitext(filename)
        skiptro_path = folder + base + '.skiptro.json'

        log(f'Checking for skiptro data: {skiptro_path}')

        if not xbmcvfs.exists(skiptro_path):
            log('No skiptro file found')
            self.skiptro_data = None
            clear_all_properties()
            return

        try:
            with xbmcvfs.File(skiptro_path, 'r') as f:
                self.skiptro_data = json.loads(f.read())
            log(f'Loaded skiptro data: {self.skiptro_data}')
            self._validate_skiptro_data()
            self._update_data_properties()
        except json.JSONDecodeError as e:
            log(f'Invalid JSON in skiptro file: {e}', xbmc.LOGWARNING)
            self.skiptro_data = None
            clear_all_properties()
        except Exception as e:
            log(f'Error reading skiptro file: {e}', xbmc.LOGWARNING)
            self.skiptro_data = None
            clear_all_properties()

    def _update_data_properties(self):
        if not self.skiptro_data:
            clear_all_properties()
            return
        set_property('HasData')
        if 'intro' in self.skiptro_data:
            set_property('HasIntro')
        else:
            clear_property('HasIntro')
        if 'credits' in self.skiptro_data:
            set_property('HasCredits')
        else:
            clear_property('HasCredits')
        if 'stinger' in self.skiptro_data:
            set_property('HasStinger')
        else:
            clear_property('HasStinger')

    def _validate_skiptro_data(self):
        if not self.skiptro_data:
            return

        intro = self.skiptro_data.get('intro')
        if intro:
            start = intro.get('start', 0)
            end = intro.get('end', 0)
            if start < 0 or end < 0:
                log('Invalid intro times: negative values', xbmc.LOGWARNING)
                del self.skiptro_data['intro']
            elif end <= start:
                log('Invalid intro times: end must be after start', xbmc.LOGWARNING)
                del self.skiptro_data['intro']

        credits = self.skiptro_data.get('credits')
        if credits:
            start = credits.get('start', 0)
            if start < 0:
                log('Invalid credits time: negative value', xbmc.LOGWARNING)
                del self.skiptro_data['credits']
            else:
                intro = self.skiptro_data.get('intro')
                if intro and start < intro.get('end', 0):
                    log('Invalid credits time: overlaps intro', xbmc.LOGWARNING)
                    del self.skiptro_data['credits']

        stinger = self.skiptro_data.get('stinger')
        if stinger:
            start = stinger.get('start', 0)
            if start < 0:
                log('Invalid stinger time: negative value', xbmc.LOGWARNING)
                del self.skiptro_data['stinger']
            else:
                credits = self.skiptro_data.get('credits')
                if credits and start <= credits.get('start', 0):
                    log('Invalid stinger time: must be after credits start', xbmc.LOGWARNING)
                    del self.skiptro_data['stinger']


class SkiptroService:
    SKIPPING_MIN = 2.0

    def __init__(self):
        self.monitor = xbmc.Monitor()
        self.player = SkiptroPlayer()
        self.active_ranges = set()
        self.prompted_ranges = set()
        self.auto_skipped_ranges = set()
        self._last_file = None
        self._dialog = None
        self._dialog_window_end = None
        self._dialog_autoclose_seconds = 10

    def _update_skipping(self, skip_init):
        global _skip_init_monotonic
        if skip_init is None:
            return
        if time.monotonic() - skip_init < self.SKIPPING_MIN:
            return
        if xbmc.getCondVisibility('Player.HasPerformedSeek(2) | Player.Caching'):
            return
        if _skip_init_monotonic == skip_init:
            clear_property('Skipping')
            _skip_init_monotonic = None

    def _close_dialog(self):
        if self._dialog is None:
            return
        if self._dialog.is_open:
            self._dialog.close()
        self._dialog = None
        self._dialog_window_end = None
        clear_property('DialogVisible')

    def _update_dialog_lifecycle(self, current_time):
        if self._dialog is None:
            return
        if not self._dialog.is_open:
            self._close_dialog()
            return
        idle = time.monotonic() - self._dialog.last_action_monotonic
        if idle >= self._dialog_autoclose_seconds:
            log('Dialog auto-closed after timeout')
            self._close_dialog()
            return
        if self._dialog_window_end is not None and current_time >= self._dialog_window_end:
            log('Dialog closed - playback past skip window')
            self._close_dialog()

    def run(self):
        log('Service started')

        while not self.monitor.abortRequested():
            if self.monitor.waitForAbort(0.5):
                break

            if not self.player.isPlayingVideo():
                self._close_dialog()
                if self.active_ranges or self.prompted_ranges or self.auto_skipped_ranges:
                    self.active_ranges.clear()
                    self.prompted_ranges.clear()
                    self.auto_skipped_ranges.clear()
                    self._last_file = None
                continue

            data = self.player.skiptro_data
            current_file = self.player.current_file
            skip_init = _skip_init_monotonic

            if current_file != self._last_file:
                self._last_file = current_file
                self.active_ranges.clear()
                self.prompted_ranges.clear()
                self.auto_skipped_ranges.clear()

            self._update_skipping(skip_init)

            if data is None:
                continue

            try:
                current_time = self.player.getTime()
            except RuntimeError:
                continue

            self._update_dialog_lifecycle(current_time)
            if _skip_init_monotonic is None:
                self._check_skiptro_ranges(current_time, data)

        self._close_dialog()
        clear_all_properties()
        log('Service stopped')

    def _check_skiptro_ranges(self, current_time, data):
        currently_active = set()

        intro = data.get('intro')
        if intro:
            start = intro.get('start', 0)
            end = intro.get('end', 0)
            if current_time < start:
                self.auto_skipped_ranges.discard('intro')
            elif current_time < end:
                currently_active.add('intro')

        credits = data.get('credits')
        if credits:
            start = credits.get('start', 0)
            if current_time >= start:
                currently_active.add('credits')

        new_ranges = currently_active - self.active_ranges
        past_ranges = self.active_ranges - currently_active
        self.prompted_ranges -= past_ranges
        self.active_ranges = currently_active

        for name in new_ranges:
            set_property('In' + name.capitalize())
        for name in past_ranges:
            clear_property('In' + name.capitalize())

        for range_type in currently_active:
            if range_type not in self.prompted_ranges:
                if range_type == 'intro':
                    end = intro.get('end', 0)
                    if ADDON.getSettingBool('auto_skip_intro'):
                        self.prompted_ranges.add('intro')
                        if 'intro' not in self.auto_skipped_ranges:
                            self.auto_skipped_ranges.add('intro')
                            log(f'Auto-skipping intro, seeking to {end}s')
                            seek_with_property(self.player, end)
                    else:
                        self._show_dialog('intro', seek_target=end, window_end=end)
                elif range_type == 'credits':
                    stinger = data.get('stinger')
                    stinger_target = stinger.get('start') if stinger else None
                    self._show_dialog('credits', stinger_target=stinger_target)
                return

    def _show_dialog(self, skip_type, seek_target=None, stinger_target=None,
                      window_end=None):
        self._close_dialog()
        self.prompted_ranges.add(skip_type)

        autoclose_seconds = ADDON.getSettingInt('autoclose_seconds')

        log(f'Showing {skip_type} dialog (autoclose: {autoclose_seconds}s)')

        dialog = SkiptroDialog(
            'service.skiptro-SkipDialog.xml',
            ADDON_PATH,
            'default',
            '1080i'
        )
        dialog.set_skip_info(skip_type, seek_target, stinger_target)
        set_property('DialogVisible')
        dialog.show()

        self._dialog = dialog
        self._dialog_autoclose_seconds = autoclose_seconds
        self._dialog_window_end = window_end


def main():
    SkiptroService().run()
