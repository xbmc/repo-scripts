# -*- coding: utf-8 -*-
import xbmc

from base import DefaultWindowReader, NullReader, KeymapKeyInputReader
from progressdialog import ProgressDialogReader
from virtualkeyboard import VirtualKeyboardReader
from virtualkeyboard import PVRSGuideSearchDialogReader
from pvrguideinfo import PVRGuideInfoReader
from textviewer import TextViewerReader
from busydialog import BusyDialogReader
from contextmenu import ContextMenuReader
from pvr import PVRWindowReader
from pvr import PVRGuideWindowReader
from pvr import PVRChannelsWindowReader
from pvr import PVRRecordingsWindowReader
from pvr import PVRTimersWindowReader
from pvr import PVRSearchWindowReader
from libraryviews import VideoLibraryWindowReader
from weather import WeatherReader
from playerstatus import PlayerStatusReader
from settings import SettingsReader
from selectdialog import SelectDialogReader
from yesnodialog import YesNoDialogReader
from videoinfodialog import VideoInfoDialogReader
from subtitlesdialog import SubtitlesDialogReader
READERS = (
    KeymapKeyInputReader,
    DefaultWindowReader,
    NullReader,
    ProgressDialogReader,
    VirtualKeyboardReader,
    PVRSGuideSearchDialogReader,
    PVRGuideInfoReader,
    TextViewerReader,
    BusyDialogReader,
    ContextMenuReader,
    PVRWindowReader,
    PVRGuideWindowReader,
    PVRChannelsWindowReader,
    PVRRecordingsWindowReader,
    PVRTimersWindowReader,
    PVRSearchWindowReader,
    VideoLibraryWindowReader,
    WeatherReader,
    PlayerStatusReader,
    SettingsReader,
    YesNoDialogReader,
    VideoInfoDialogReader,
    SelectDialogReader,
    SubtitlesDialogReader
)

READERS_WINID_MAP = {
                10004: SettingsReader, #settings
                10012: SettingsReader, #picturesettings
                10013: SettingsReader, #programsettings
                10014: SettingsReader, #weathersettings
                10015: SettingsReader, #musicsettings
                10016: SettingsReader, #systemsettings
                10017: SettingsReader, #videosettings
                10018: SettingsReader, #servicesettings
                10019: SettingsReader, #appearancesettings
                10021: SettingsReader, #livetvsettings
                10025: VideoLibraryWindowReader, #videolibrary
                10030: SettingsReader, #SettingsCategory.xml
                10031: SettingsReader, #SettingsCategory.xml
                10032: SettingsReader, #SettingsCategory.xml
                10034: SettingsReader, #profilesettings
                10035: SettingsReader, #SettingsCategory.xml
                14000: SettingsReader, #pvrclientspecificsettings
                10100: YesNoDialogReader, #yesnodialog
                10101: ProgressDialogReader,
                10103: VirtualKeyboardReader,
                10106: ContextMenuReader,
                10109: VirtualKeyboardReader,
                10120: PlayerStatusReader, #musicosd
                10123: SettingsReader, #osdvideosettings
                10124: SettingsReader, #osdaudiosettings
                10131: SettingsReader, #locksettings
                10132: SettingsReader, #contentsettings
                10135: VideoInfoDialogReader, #songinformation
                10138: BusyDialogReader,
                10140: SettingsReader, #addonsettings
                10147: TextViewerReader,
                10150: SettingsReader, #peripheralsettings
                10153: SubtitlesDialogReader, #subtitlesdialog
                10501: VideoLibraryWindowReader, #musicsongs
                10502: VideoLibraryWindowReader, #musiclibrary
                10601: PVRWindowReader, #pvr - Pre-Helix
                10602: PVRGuideInfoReader,
                10607: PVRSGuideSearchDialogReader,
                10615: PVRChannelsWindowReader, #tvchannels
                10616: PVRRecordingsWindowReader, #tvrecordings
                10617: PVRGuideWindowReader, #tvguide
                10618: PVRTimersWindowReader, #tvtimers
                10619: PVRSearchWindowReader, #tvsearch
                10620: PVRChannelsWindowReader, #radiochannels
                10621: PVRRecordingsWindowReader, #radiorecordings
                10622: PVRGuideWindowReader, #radioguide
                10623: PVRTimersWindowReader, #radiotimers
                10624: PVRSearchWindowReader, #radiosearch
                11102: TextViewerReader,
                12000: SelectDialogReader,
                12002: YesNoDialogReader,
                12003: VideoInfoDialogReader, #videoinfodialog
                12005: PlayerStatusReader, #fullscreenvideo
                12006: PlayerStatusReader, #visualization
                12600: WeatherReader,
                12901: SettingsReader, #videoosd
}

READERS_MAP = {}
for r in READERS: READERS_MAP[r.ID] = r

def getWindowReader(winID):
    reader = xbmc.getInfoLabel('Window({0}).Property(TTS.READER)'.format(winID))
    if reader and reader in READERS_MAP:
        return READERS_MAP[reader]
    return READERS_WINID_MAP.get(winID,DefaultWindowReader)