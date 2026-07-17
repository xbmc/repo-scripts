import xbmc
import xbmcgui
from jurialmunkey.parser import try_type, try_int


DIALOG_ID_EXCLUDELIST = (9999, None, )

WINDOW_IDS = {
    10000: ('Home.xml', 'Home', 'WINDOW_HOME', ),
    10001: ('MyPrograms.xml', 'Programs', 'WINDOW_PROGRAMS', ),
    10002: ('MyPics.xml', 'Pictures', 'WINDOW_PICTURES', ),
    10003: ('FileManager.xml', 'FileManager', 'WINDOW_FILES', ),
    10004: ('Settings.xml', 'Settings', 'WINDOW_SETTINGS_MENU', ),
    10007: ('SettingsSystemInfo.xml', 'SystemInfo', 'WINDOW_SYSTEM_INFORMATION', ),
    10011: ('SettingsScreenCalibration.xml', 'ScreenCalibration', 'WINDOW_SCREEN_CALIBRATION', ),
    10016: ('SettingsCategory.xml', 'SystemSettings', 'WINDOW_SETTINGS_SYSTEM', ),
    10018: ('SettingsCategory.xml', 'ServiceSettings', 'WINDOW_SETTINGS_SERVICE', ),
    10021: ('SettingsCategory.xml', 'PVRSettings', 'WINDOW_SETTINGS_MYPVR', ),
    10022: ('SettingsCategory.xml', 'GameSettings', 'WINDOW_SETTINGS_MYGAMES', ),
    10025: ('MyVideoNav.xml', 'Videos', 'WINDOW_VIDEO_NAV', ),
    10028: ('MyPlaylist.xml', 'VideoPlaylist', 'WINDOW_VIDEO_PLAYLIST', ),
    10029: ('LoginScreen.xml', 'LoginScreen', 'WINDOW_LOGIN_SCREEN', ),
    10030: ('SettingsCategory.xml', 'PlayerSettings', 'WINDOW_SETTINGS_PLAYER', ),
    10031: ('SettingsCategory.xml', 'MediaSettings', 'WINDOW_SETTINGS_MEDIA', ),
    10032: ('SettingsCategory.xml', 'InterfaceSettings', 'WINDOW_SETTINGS_INTERFACE', ),
    10034: ('SettingsProfile.xml', 'Profiles', 'WINDOW_SETTINGS_PROFILES', ),
    10035: ('SkinSettings.xml', 'SkinSettings', 'WINDOW_SKIN_SETTINGS', ),
    10040: ('AddonBrowser.xml', 'AddonBrowser', 'WINDOW_ADDON_BROWSER', ),
    10050: ('EventLog.xml', 'EventLog', 'WINDOW_EVENT_LOG', ),
    10099: ('Pointer.xml', 'Pointer', 'WINDOW_DIALOG_POINTER', ),
    10100: ('DialogConfirm.xml', 'YesNoDialog', 'WINDOW_DIALOG_YES_NO', ),
    10101: ('DialogConfirm.xml', 'ProgressDialog', 'WINDOW_DIALOG_PROGRESS', ),
    10103: ('DialogKeyboard.xml', 'VirtualKeyboard', 'WINDOW_DIALOG_KEYBOARD', ),
    10104: ('DialogVolumeBar.xml', 'VolumeBar', 'WINDOW_DIALOG_VOLUME_BAR', ),
    10105: ('DialogSubMenu.xml', 'SubMenu', 'WINDOW_DIALOG_SUB_MENU', ),
    10106: ('DialogContextMenu.xml', 'ContextMenu', 'WINDOW_DIALOG_CONTEXT_MENU', ),
    10107: ('DialogNotification.xml', 'Notification', 'WINDOW_DIALOG_KAI_TOAST', ),
    10109: ('DialogNumeric.xml', 'NumericInput', 'WINDOW_DIALOG_NUMERIC', ),
    10110: ('DialogSelect.xml', 'GamepadInput', 'WINDOW_DIALOG_GAMEPAD', ),
    10111: ('DialogButtonMenu.xml', 'ShutdownMenu', 'WINDOW_DIALOG_BUTTON_MENU', ),
    10114: ('PlayerControls.xml', 'PlayerControls', 'WINDOW_DIALOG_PLAYER_CONTROLS', ),
    10115: ('DialogSeekBar.xml', 'SeekBar', 'WINDOW_DIALOG_SEEK_BAR', ),
    10116: ('DialogPlayerProcessInfo.xml', 'PlayerProcessInfo', 'WINDOW_DIALOG_PLAYER_PROCESS_INFO', ),
    10120: ('MusicOSD.xml', 'MusicOSD', 'WINDOW_DIALOG_MUSIC_OSD', ),
    10121: ('', '', 'WINDOW_DIALOG_VIS_SETTINGS', ),
    10122: ('DialogSelect.xml', 'VisualisationPresetList', 'WINDOW_DIALOG_VIS_PRESET_LIST', ),
    10123: ('DialogSettings.xml', 'OSDVideoSettings', 'WINDOW_DIALOG_VIDEO_OSD_SETTINGS', ),
    10124: ('DialogSettings.xml', 'OSDAudioSettings', 'WINDOW_DIALOG_AUDIO_OSD_SETTINGS', ),
    10125: ('VideoOSDBookmarks.xml', 'VideoBookmarks', 'WINDOW_DIALOG_VIDEO_BOOKMARKS', ),
    10126: ('FileBrowser.xml', 'FileBrowser', 'WINDOW_DIALOG_FILE_BROWSER', ),
    10128: ('DialogSettings.xml', 'NetworkSetup', 'WINDOW_DIALOG_NETWORK_SETUP', ),
    10129: ('DialogMediaSource.xml', 'MediaSource', 'WINDOW_DIALOG_MEDIA_SOURCE', ),
    10130: ('DialogSettings.xml', 'ProfileSettings', 'WINDOW_DIALOG_PROFILE_SETTINGS', ),
    10131: ('DialogSettings.xml', 'LockSettings', 'WINDOW_DIALOG_LOCK_SETTINGS', ),
    10132: ('DialogSettings.xml', 'ContentSettings', 'WINDOW_DIALOG_CONTENT_SETTINGS', ),
    10133: ('DialogSettings.xml', 'LibexportSettings', 'WINDOW_DIALOG_LIBEXPORT_SETTINGS', ),
    10135: ('DialogMusicInfo.xml', 'SongInformation', 'WINDOW_DIALOG_SONG_INFO', ),
    10136: ('SmartPlaylistEditor.xml', 'SmartPlaylistEditor', 'WINDOW_DIALOG_SMART_PLAYLIST_EDITOR', ),
    10137: ('SmartPlaylistRule.xml', 'SmartPlaylistRule', 'WINDOW_DIALOG_SMART_PLAYLIST_RULE', ),
    10138: ('DialogBusy.xml', 'BusyDialog', 'WINDOW_DIALOG_BUSY', ),
    10139: ('DialogPictureInfo.xml', 'PictureInfo', 'WINDOW_DIALOG_PICTURE_INFO', ),
    10140: ('DialogAddonSettings.xml', 'AddonSettings', 'WINDOW_DIALOG_ADDON_SETTINGS', ),
    10142: ('DialogFullScreenInfo.xml', 'FullscreenInfo', 'WINDOW_DIALOG_FULLSCREEN_INFO', ),
    10145: ('DialogSlider.xml', 'SliderDialog', 'WINDOW_DIALOG_SLIDER', ),
    10146: ('DialogAddonInfo.xml', 'AddonInformation', 'WINDOW_DIALOG_ADDON_INFO', ),
    10147: ('DialogTextViewer.xml', 'TextViewer', 'WINDOW_DIALOG_TEXT_VIEWER', ),
    10148: ('DialogConfirm.xml', '', 'WINDOW_DIALOG_PLAY_EJECT', ),
    10149: ('DialogSelect.xml', 'Peripherals', 'WINDOW_DIALOG_PERIPHERALS', ),
    10150: ('DialogSettings.xml', 'PeripheralSettings', 'WINDOW_DIALOG_PERIPHERAL_SETTINGS', ),
    10151: ('DialogExtendedProgressBar.xml', 'ExtendedProgressDialog', 'WINDOW_DIALOG_EXT_PROGRESS', ),
    10152: ('DialogSettings.xml', 'MediaFilter', 'WINDOW_DIALOG_MEDIA_FILTER', ),
    10153: ('DialogSubtitles.xml', 'SubtitleSearch', 'WINDOW_DIALOG_SUBTITLES', ),
    10156: ('', '', 'WINDOW_DIALOG_KEYBOARD_TOUCH', ),
    10157: ('DialogSettings.xml', 'OSDCMSSettings', 'WINDOW_DIALOG_CMS_OSD_SETTINGS', ),
    10158: ('DialogSettings.xml', 'InfoproviderSettings', 'WINDOW_DIALOG_INFOPROVIDER_SETTINGS', ),
    10159: ('DialogSettings.xml', 'OSDSubtitleSettings', 'WINDOW_DIALOG_SUBTITLE_OSD_SETTINGS', ),
    10160: ('DialogBusy.xml', 'BusyDialogNoCancel', 'WINDOW_DIALOG_BUSY_NOCANCEL', ),
    10500: ('MyPlaylist.xml', 'MusicPlaylist', 'WINDOW_MUSIC_PLAYLIST', ),
    10502: ('MyMusicNav.xml', 'Music', 'WINDOW_MUSIC_NAV', ),
    10503: ('MyMusicPlaylistEditor.xml', 'MusicPlaylistEditor', 'WINDOW_MUSIC_PLAYLIST_EDITOR', ),
    10550: ('', 'Teletext', 'WINDOW_DIALOG_OSD_TELETEXT', ),
    10600: ('DialogPVRInfo.xml', 'PVRGuideInfo', 'WINDOW_DIALOG_PVR_GUIDE_INFO', ),
    10601: ('DialogPVRInfo.xml', 'PVRRecordingInfo', 'WINDOW_DIALOG_PVR_RECORDING_INFO', ),
    10602: ('DialogSettings.xml', 'PVRTimerSetting', 'WINDOW_DIALOG_PVR_TIMER_SETTING', ),
    10603: ('DialogPVRGroupManager.xml', 'PVRGroupManager', 'WINDOW_DIALOG_PVR_GROUP_MANAGER', ),
    10604: ('DialogPVRChannelManager.xml', 'PVRChannelManager', 'WINDOW_DIALOG_PVR_CHANNEL_MANAGER', ),
    10605: ('DialogPVRGuideSearch.xml', 'PVRGuideSearch', 'WINDOW_DIALOG_PVR_GUIDE_SEARCH', ),
    10606: ('none (unused)', 'PVRChannelScan', 'WINDOW_DIALOG_PVR_CHANNEL_SCAN', ),
    10607: ('none (unused)', 'PVRUpdateProgress', 'WINDOW_DIALOG_PVR_UPDATE_PROGRESS', ),
    10608: ('DialogPVRChannelsOSD.xml', 'PVROSDChannels', 'WINDOW_DIALOG_PVR_OSD_CHANNELS', ),
    10609: ('DialogPVRChannelGuide.xml', 'PVRChannelGuide', 'WINDOW_DIALOG_PVR_CHANNEL_GUIDE', ),
    10610: ('DialogPVRRadioRDSInfo.xml', 'PVRRadioRDSInfo', 'WINDOW_DIALOG_PVR_RADIO_RDS_INFO', ),
    10611: ('DialogSettings.xml', 'PVRRecordingSettings', 'WINDOW_DIALOG_PVR_RECORDING_SETTING', ),
    10612: ('DialogSettings.xml', '', 'WINDOW_DIALOG_PVR_CLIENT_PRIORITIES', ),
    10700: ('MyPVRChannels.xml', 'TVChannels', 'WINDOW_TV_CHANNELS', ),
    10701: ('MyPVRRecordings.xml', 'TVRecordings', 'WINDOW_TV_RECORDINGS', ),
    10702: ('MyPVRGuide.xml', 'TVGuide', 'WINDOW_TV_GUIDE', ),
    10703: ('MyPVRTimers.xml', 'TVTimers', 'WINDOW_TV_TIMERS', ),
    10704: ('MyPVRSearch.xml', 'TVSearch', 'WINDOW_TV_SEARCH', ),
    10705: ('MyPVRChannels.xml', 'RadioChannels', 'WINDOW_RADIO_CHANNELS', ),
    10706: ('MyPVRRecordings.xml', 'RadioRecordings', 'WINDOW_RADIO_RECORDINGS', ),
    10707: ('MyPVRGuide.xml', 'RadioGuide', 'WINDOW_RADIO_GUIDE', ),
    10708: ('MyPVRTimers.xml', 'RadioTimers', 'WINDOW_RADIO_TIMERS', ),
    10709: ('MyPVRSearch.xml', 'RadioSearch', 'WINDOW_RADIO_SEARCH', ),
    10710: ('MyPVRTimers.xml', 'TVTimerRules', 'WINDOW_TV_TIMER_RULES', ),
    10711: ('MyPVRTimers.xml', 'RadioTimerRules', 'WINDOW_RADIO_TIMER_RULES', ),
    10800: ('', 'FullscreenLiveTV', 'WINDOW_FULLSCREEN_LIVETV', ),
    10801: ('', 'FullscreenRadio', 'WINDOW_FULLSCREEN_RADIO', ),
    10802: ('', 'FullscreenLivetvPreview', 'WINDOW_FULLSCREEN_LIVETV_PREVIEW', ),
    10803: ('', 'FullscreenRadioPreview', 'WINDOW_FULLSCREEN_RADIO_PREVIEW', ),
    10804: ('', 'FullscreenLivetvInput', 'WINDOW_FULLSCREEN_LIVETV_INPUT', ),
    10805: ('', 'FullscreenRadioInput', 'WINDOW_FULLSCREEN_RADIO_INPUT', ),
    10820: ('DialogGameControllers.xml', 'GameControllers', 'WINDOW_DIALOG_GAME_CONTROLLERS', ),
    10821: ('MyGames.xml', 'Games', 'WINDOW_GAMES', ),
    10822: ('GameOSD.xml', 'GameOSD', 'WINDOW_DIALOG_GAME_OSD', ),
    10823: ('DialogSelect.xml', 'GameVideoFilter', 'WINDOW_DIALOG_GAME_VIDEO_FILTER', ),
    10824: ('DialogSelect.xml', 'GameStretchMode', 'WINDOW_DIALOG_GAME_STRETCH_MODE', ),
    10825: ('DialogSlider.xml', 'GameVolume', 'WINDOW_DIALOG_GAME_VOLUME', ),
    10826: ('DialogAddonSettings.xml', 'GameAdvancedSettings', 'WINDOW_DIALOG_GAME_ADVANCED_SETTINGS', ),
    10827: ('DialogSelect.xml', 'GameVideoRotation', 'WINDOW_DIALOG_GAME_VIDEO_ROTATION', ),
    10828: ('DialogGameControllers.xml', 'GamePorts', 'WINDOW_DIALOG_GAME_PORTS', ),
    10829: ('DialogSelect.xml', 'InGameSaves', 'WINDOW_DIALOG_IN_GAME_SAVES', ),
    10830: ('DialogSelect.xml', 'GameSaves', 'WINDOW_DIALOG_GAME_SAVES', ),
    10831: ('DialogGameControllers.xml', 'GameAgents', 'WINDOW_DIALOG_GAME_AGENTS', ),
    12000: ('DialogSelect.xml', 'SelectDialog', 'WINDOW_DIALOG_SELECT', ),
    12001: ('DialogMusicInfo.xml', 'MusicInformation', 'WINDOW_DIALOG_MUSIC_INFO', ),
    12002: ('DialogConfirm.xml', 'OKDialog', 'WINDOW_DIALOG_OK', ),
    12003: ('DialogVideoInfo.xml', 'MovieInformation', 'WINDOW_DIALOG_VIDEO_INFO', ),
    12005: ('VideoFullScreen.xml', 'FullscreenVideo', 'WINDOW_FULLSCREEN_VIDEO', ),
    12006: ('MusicVisualisation.xml', 'Visualisation', 'WINDOW_VISUALISATION', ),
    12007: ('SlideShow.xml', 'Slideshow', 'WINDOW_SLIDESHOW', ),
    12008: ('DialogColorPicker.xml', 'DialogColorPicker', 'WINDOW_DIALOG_COLOR_PICKER', ),
    12015: ('DialogSelect.xml', 'SelectVideoVersion', 'WINDOW_DIALOG_SELECT_VIDEO_VERSION', ),
    12016: ('DialogSelect.xml', 'SelectVideoExtra', 'WINDOW_DIALOG_SELECT_VIDEO_EXTRA', ),
    12004: ('DialogVideoManager.xml', 'ManageVideoVersions', 'WINDOW_DIALOG_MANAGE_VIDEO_VERSIONS', ),
    12017: ('DialogVideoManager.xml', 'ManageVideoExtras', 'WINDOW_DIALOG_MANAGE_VIDEO_EXTRAS', ),
    12600: ('MyWeather.xml', 'Weather', 'WINDOW_WEATHER', ),
    12900: ('', 'Screensaver', 'WINDOW_SCREENSAVER', ),
    12901: ('VideoOSD.xml', 'VideoOSD', 'WINDOW_DIALOG_VIDEO_OSD', ),
    12902: ('', 'VideoMenu', 'WINDOW_VIDEO_MENU', ),
    12905: ('', 'VideoTimeSeek', 'WINDOW_VIDEO_TIME_SEEK', ),
    12906: ('', 'FullscreenGame', 'WINDOW_FULLSCREEN_GAME', ),
    12997: ('', 'Splash', 'WINDOW_SPLASH', ),
    12998: ('', 'StartWindow', 'WINDOW_START', ),
    12999: ('Startup.xml', 'Startup', 'WINDOW_STARTUP_ANIM', ),
    10060: ('MyFavourites.xml', 'FavouritesBrowser', 'WINDOW_FAVOURITES', ),
}


def get_key_index(dictionary, key, idx):
    key_lower = key.lower()
    if key_lower in dictionary:
        dictionary[key] = dictionary[key_lower]
        return dictionary[key]

    collection = []
    collection_append = collection.append
    for k, v in WINDOW_IDS.items():
        if key_lower != v[idx].lower():
            continue
        collection_append(k)

    dictionary[key] = dictionary[key_lower] = tuple(collection)
    return dictionary[key]


class WindowXMLDict(dict):
    def __missing__(self, key):
        return get_key_index(self, key, 0)  # XML Stored in 0 index of tuple (use 1 for names and 2 for defs)


class WindowChecker():
    @property
    def window_xml_dict(self):
        try:
            return self._window_xml_dict
        except AttributeError:
            self._window_xml_dict = WindowXMLDict()
            return self._window_xml_dict

    def window_xml(self, key):
        if not key:
            return tuple()
        return self.window_xml_dict[key] or tuple()

    @property
    def previous_window(self):
        try:
            return self._previous_window
        except AttributeError:
            self._previous_window = -1
            return self._previous_window

    @property
    def current_window(self):
        try:
            return self._current_window
        except AttributeError:
            return self.get_current_window()

    def get_current_window(self):
        self._current_window = get_current_window()
        return self._current_window

    def is_current_window_xml(self, values):
        for i in values:
            if self.current_window in self.window_xml(i):
                return True
        return False

    def get_window_property(self, key, is_type=None, is_home=False):
        try:
            window = xbmcgui.Window(10000) if is_home else xbmcgui.Window(self.current_window)
        except RuntimeError:
            return
        if not window:
            return
        return try_type(window.getProperty(f'TMDbHelper.{key}'), is_type or str)


def get_current_window(get_dialog=True):
    dialog = xbmcgui.getCurrentWindowDialogId() if get_dialog else None
    return dialog if dialog not in DIALOG_ID_EXCLUDELIST else xbmcgui.getCurrentWindowId()


def get_property(name, set_property=None, clear_property=False, window_id=None, prefix=None, is_type=None):
    if prefix != -1:
        prefix = prefix or 'TMDbHelper'
        name = f'{prefix}.{name}'
    if window_id == 'current':
        window_id = get_current_window()
    try:
        window = xbmcgui.Window(window_id or 10000)  # Fallback to home window id=10000
    except RuntimeError:  # If window id does not exist
        return
    ret_property = set_property or window.getProperty(name)
    if clear_property:
        window.clearProperty(name)
    if set_property is not None:
        window.setProperty(name, f'{set_property}')
    return try_type(ret_property, is_type or str)


def set_to_windowprop(text, x, window_prop, window_id=None):
    if not window_prop:
        return
    if x == 0:
        xbmc.executebuiltin(f'SetProperty({window_prop},{text}{f",{window_id}" if window_id else ""})')
    xbmc.executebuiltin(f'SetProperty({window_prop}.{x},{text}{f",{window_id}" if window_id else ""})')


def clear_windowprops(window_prop, window_id=None, keys_prop=None, keys=None):
    if not window_prop:
        return

    # Default properties
    xbmc.executebuiltin(f'ClearProperty({window_prop}{f",{window_id}" if window_id else ""})')
    xbmc.executebuiltin(f'ClearProperty({window_prop}.0{f",{window_id}" if window_id else ""})')

    # Special property with list of keys for the properties that were set
    if keys_prop is not None:
        keys = xbmc.getInfoLabel(f'Window({window_id if window_id else ""}).Property({window_prop}.{keys_prop})') or ''
        keys = keys.split('||')
        xbmc.executebuiltin(f'ClearProperty({window_prop}.{keys_prop}{f",{window_id}" if window_id else ""})')

    if not keys:
        return

    for key in keys:
        xbmc.executebuiltin(f'ClearProperty({window_prop}.{key}{f",{window_id}" if window_id else ""})')


def _property_is_value(name, value):
    if not value and not get_property(name):
        return True
    if value and get_property(name) == value:
        return True
    return False


def wait_for_property(name, value=None, set_property=False, poll=1, timeout=10):
    """
    Waits until property matches value. None value waits for property to be cleared.
    Will set property to value if set_property flag is set. None value clears property.
    Returns True when successful.
    """
    xbmc_monitor = xbmc.Monitor()
    if set_property:
        get_property(name, value) if value else get_property(name, clear_property=True)
    while (
            not xbmc_monitor.abortRequested() and timeout > 0
            and not _property_is_value(name, value)):
        xbmc_monitor.waitForAbort(poll)
        timeout -= poll
    if timeout > 0:
        return True


def is_visible(window_id):
    return xbmc.getCondVisibility(f'Window.IsVisible({window_id})')


def close(window_id):
    return xbmc.executebuiltin(f'Dialog.Close({window_id})')


def activate(window_id):
    return xbmc.executebuiltin(f'ActivateWindow({window_id})')


def _is_base_active(window_id):
    if window_id and not is_visible(window_id):
        return False
    return True


def _is_updating(container_id):
    is_updating = xbmc.getCondVisibility(f"Container({container_id}).IsUpdating")
    is_numitems = try_int(xbmc.getInfoLabel(f"Container({container_id}).NumItems"))
    if is_updating or not is_numitems:
        return True


def _is_inactive(window_id, invert=False):
    if is_visible(window_id):
        return True if invert else False
    return True if not invert else False


def wait_until_active(window_id, instance_id=None, poll=1, timeout=30, invert=False, xbmc_monitor=None):
    """
    Wait for window ID to open (or to close if invert set to True). Returns window_id if successful.
    Pass instance_id if there is also a base window that needs to be open underneath
    """
    _xbmc_monitor = xbmc_monitor or xbmc.Monitor()
    while (
            not _xbmc_monitor.abortRequested() and timeout > 0
            and _is_inactive(window_id, invert)
            and _is_base_active(instance_id)):
        _xbmc_monitor.waitForAbort(poll)
        timeout -= poll
    if timeout > 0 and _is_base_active(instance_id):
        return window_id


def wait_until_updated(container_id=9999, instance_id=None, poll=1, timeout=60, xbmc_monitor=None):
    """
    Wait for container to update. Returns container_id if successful
    Pass instance_id if there is also a base window that needs to be open underneath
    """
    _xbmc_monitor = xbmc_monitor or xbmc.Monitor()
    while (
            not _xbmc_monitor.abortRequested() and timeout > 0
            and _is_updating(container_id)
            and _is_base_active(instance_id)):
        _xbmc_monitor.waitForAbort(poll)
        timeout -= poll
    if timeout > 0 and _is_base_active(instance_id):
        return container_id


class WindowProperty():
    def __init__(self, *args, prefix='TMDbHelper'):
        """ ContextManager for setting a WindowProperty over duration """
        self.property_pairs = args
        self.window_property_setter = WindowPropertySetter()
        self.prefix = prefix

        for k, v in self.property_pairs:
            if not k or not v:
                continue
            self.window_property_setter.get_property(f'{k}', set_property=f'{v}', prefix=self.prefix)

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, exc_traceback):
        for k, v in self.property_pairs:
            self.window_property_setter.get_property(f'{k}', clear_property=True, prefix=self.prefix)


class WindowPropertySetter():
    window_id = 10000

    def get_window(self):
        try:
            return xbmcgui.Window(self.window_id)
        except RuntimeError:
            return

    def get_property(self, name, set_property=None, clear_property=False, is_type=None, prefix='TMDbHelper'):
        _win = self.get_window()
        try:
            name = f'{prefix}.{name}'
            ret_property = set_property or _win.getProperty(name)
            if clear_property:
                _win.clearProperty(name)
            if set_property is not None:
                _win.setProperty(name, f'{set_property}')
        except AttributeError:  # In case no window returned
            pass
        return try_type(ret_property, is_type or str)
