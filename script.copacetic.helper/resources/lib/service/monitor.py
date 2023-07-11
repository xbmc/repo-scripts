# author: realcopacetic

import xml.etree.ElementTree as ET

import xbmc

from resources.lib.service.art import ImageEditor, SlideshowMonitor
from resources.lib.service.player import PlayerMonitor
from resources.lib.service.settings import SettingsMonitor
from resources.lib.utilities import (CROPPED_FOLDERPATH, LOOKUP_XML,
                                     TEMP_FOLDERPATH, condition, create_dir,
                                     get_cache_size, infolabel, log,
                                     log_and_execute, split,
                                     split_random_return, validate_path,
                                     window_property)

XMLSTR = '''<?xml version="1.0" encoding="utf-8"?>
<data>
    <clearlogos />
</data>
'''


class Monitor(xbmc.Monitor):
    def __init__(self):
        # Poller
        self.start = True
        self.idle = False
        self.check_settings, self.check_cache = True, True
        self.position, self.dbid, self.dbtype = False, False, False
        # Setup
        self.cropped_folder = CROPPED_FOLDERPATH
        self.temp_folder = TEMP_FOLDERPATH
        self.lookup = LOOKUP_XML
        # Monitors
        self.player_monitor = None
        self.settings_monitor = SettingsMonitor()
        self.art_monitor = SlideshowMonitor()
        self._clearlogo_cropper = ImageEditor().clearlogo_cropper
        # Run
        self._create_dirs()
        self._on_start()

    def _create_dirs(self):
        if not validate_path(self.cropped_folder):
            create_dir(self.cropped_folder)
        if not validate_path(self.temp_folder):
            create_dir(self.temp_folder)
        if not validate_path(self.lookup):
            root = ET.fromstring(XMLSTR)
            ET.ElementTree(root).write(
                self.lookup, xml_declaration=True, encoding="utf-8")

    def _on_start(self):
        if self.start:
            log('Monitor started', force=True)
            self.start = False
            self.player_monitor = PlayerMonitor()
        else:
            log('Monitor resumed', force=True) if self._conditions_met() else None
        while not self.abortRequested() and self._conditions_met():
            self.poller()
        self._on_stop()

    def _conditions_met(self):
        return (
            self._get_skindir() and not self.idle and
            (
                condition('!Skin.HasSetting(Background_Disabled)') or
                condition('Skin.HasSetting(Crop_Clearlogos)')
            )
        )

    def _get_skindir(self):
        skindir = xbmc.getSkinDir()
        if 'skin.copacetic' in skindir:
            return True

    def _get_info(self):
        split_random_return(
            infolabel('ListItem.Director'), name='RandomDirector')
        split_random_return(
            infolabel('ListItem.Genre'), name='RandomGenre')
        split(infolabel('ListItem.Writer'), name='WriterSplit')
        split(infolabel('ListItem.Studio'), name='StudioSplit')

    def poller(self):
        # video playing fullscreen
        if condition(
            'VideoPlayer.IsFullscreen'
        ):
            self.waitForAbort(1)

        # info screen visible and main menu selected
        elif condition(
            '[Window.Is(movieinformation) | '
            'Window.Is(musicinformation) | '
            'Window.Is(songinformation)] + !['
            'Control.HasFocus(3201) | '
            'Control.HasFocus(3202) | '
            'Control.HasFocus(3203) | '
            'Control.HasFocus(3204) | '
            'Control.HasFocus(3205) | '
            'Control.HasFocus(3206) | '
            'Control.HasFocus(3207) | '
            'Control.HasFocus(3208) | '
            'Control.HasFocus(3209)]'
        ):
            self._on_scroll(crop=False, return_color=False, get_info=True)
            self.waitForAbort(0.2)

        # secondary list has focus and clearlogo view visible
        elif condition(
            'Skin.HasSetting(Crop_Clearlogos) + '
            'Control.HasFocus(3100) + ['
            'Control.IsVisible(501) | Control.IsVisible(502) | Control.IsVisible(504)]'
        ):
            self._on_scroll(key='3100', return_color=False)
            self.waitForAbort(0.2)

        # clearlogo view visible
        elif condition(
            'Skin.HasSetting(Crop_Clearlogos) + ['
            'Control.IsVisible(501) | '
            'Control.IsVisible(502) | '
            'Control.IsVisible(504)]'
        ):
            self._on_scroll()
            self.waitForAbort(0.2)

        # home widgets has clearlogo visible
        elif condition(
            'Window.Is(home) + '
            'Skin.HasSetting(Crop_Clearlogos) + ['
            'Control.HasFocus(3201) | '
            'Control.HasFocus(3202) | '
            'Control.HasFocus(3203) | '
            'Control.HasFocus(3204) | '
            'Control.HasFocus(3205) | '
            'Control.HasFocus(3206) | '
            'Control.HasFocus(3207) | '
            'Control.HasFocus(3208) | '
            'Control.HasFocus(3209)]'
        ):
            widget = infolabel('System.CurrentControlID')
            self._on_scroll(key=widget)
            self.waitForAbort(0.2)

        # slideshow window is visible run SlideshowMonitor()
        elif condition(
            '!Skin.HasSetting(Background_Disabled) + ['
            'Window.IsVisible(home) | '
            'Window.IsVisible(settings) | '
            'Window.IsVisible(skinsettings) | '
            'Window.IsVisible(appearancesettings) | '
            'Window.IsVisible(mediasettings) | '
            'Window.IsVisible(playersettings) | '
            'Window.IsVisible(servicesettings) | '
            'Window.IsVisible(systemsettings) | '
            'Window.IsVisible(pvrsettings) | '
            'Window.IsVisible(gamesettings) | '
            'Window.IsVisible(profiles) | '
            'Window.IsVisible(systeminfo) | '
            'Window.IsVisible(filemanager) | '
            'Window.IsVisible(addonsettings) + !String.IsEmpty(ListItem.Art(fanart)) | '
            'Window.IsVisible(addonbrowser) + !Container.Content(addons) | '
            'Window.IsVisible(mediasource) | '
            'Window.IsVisible(smartplaylisteditor) | '
            'Window.IsVisible(musicplaylisteditor) | '
            'Window.IsVisible(mediasource) | '
            'Container.Content(genres) | '
            'Container.Content(years) | '
            'Container.Content(playlists) | '
            'Container.Content(sources) | '
            'Container.Content(studios) | '
            'Container.Content(directors) | '
            'Container.Content(tags) | '
            'Container.Content(countries) | '
            'Container.Content(roles) | '
            'Container.Content() + [Window.Is(videos) | Window.Is(music)]]'
        ):
            self.art_monitor.background_slideshow()
            self._on_skinsettings()
            self._on_recommendedsettings()
            self.waitForAbort(1)

        # else wait for next poll
        else:
            self.check_cache = True
            self.check_settings = True
            self.waitForAbort(1)

    def _on_scroll(self, key='ListItem', crop=True, return_color=True, get_info=False):
        path, current_item, current_dbid, current_dbtype = self._current_item(
            key)
        if (
            current_item != self.position or
            current_dbid != self.dbid or
            current_dbtype != self.dbtype
        ) and not self._container_scrolling(key):
            if crop:
                self._clearlogo_cropper(
                    source=key, return_color=return_color, reporting=window_property)
            if get_info:
                self._get_info()
            self.position = current_item
            self.dbid = current_dbid
            self.dbtype = current_dbtype

    def _on_skinsettings(self):
        if condition('Window.Is(skinsettings)') and self.check_cache:
            get_cache_size()
            self.check_cache = False
        elif condition('!Window.Is(skinsettings)'):
            self.check_cach = True

    def _on_recommendedsettings(self):
        if condition('Window.Is(skinsettings)') and self.check_settings:
            self.settings_monitor.get_default()
            self.check_settings = False
        elif not condition('Window.Is(skinsettings)'):
            self.check_settings = True
        if condition('Skin.HasSetting(run_set_default)'):
            self.settings_monitor.set_default()
            self.check_settings = True
            log_and_execute('Skin.ToggleSetting(run_set_default)')

    def _on_stop(self):
        log(f'Monitor idle', force=True)
        while not self.abortRequested() and not self._conditions_met():
            self.waitForAbort(2)
        if not self.abortRequested():
            self._on_start()
        else:
            del self.player_monitor
            del self.settings_monitor
            del self.art_monitor
            log(f'Monitor stopped', force=True)

    def _current_item(self, key='ListItem'):
        container = 'Container' if key == 'ListItem' else f'Container({key})'
        item = infolabel(f'{container}.CurrentItem')
        dbid = infolabel(f'{container}.ListItem.DBID')
        dbtype = infolabel(f'{container}.ListItem.DBType')
        return (container, item, dbid, dbtype)

    def _container_scrolling(self, key='ListItem'):
        container = 'Container' if key == 'ListItem' else f'Container({key})'
        return condition(f'{container}.Scrolling')

    def onScreensaverActivated(self):
        self.idle = True

    def onScreensaverDeactivated(self):
        self.idle = False
