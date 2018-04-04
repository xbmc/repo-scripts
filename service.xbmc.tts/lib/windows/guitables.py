# -*- coding: utf-8 -*-
import xbmc
from lib import util
T = util.T
'''
Table data format:
integer: XBMC localized string ID
string integer: controll ID
$INFO[<infolabel>]: infolabel
string: normal string
'''

winNames = {    10000: 10000, #Home
                10001: 10001, #programs
                10002: 10002, #pictures
                10003: 10003, #filemanager
                10004: 10004, #settings
                10005: 10005, #music
                10006: 10006, #video
                10007: 10007, #systeminfo
                10011: 10011, #screencalibration
                10012: 10012, #picturessettings
                10013: 10013, #programssettings
                10014: 10014, #weathersettings
                10015: 10015, #musicsettings
                10016: 10016, #systemsettings
                10017: 10017, #videossettings
                10018: 10018, #servicesettings
                10019: 10019, #appearancesettings
                10020: 10020, #scripts
                10021: T(32125), #Live TV Settings
                10024: 10024, #videofiles: Removed in Gotham
                10025: 10025, #videolibrary
                10028: 10028, #videoplaylist
                10029: 10029, #loginscreen
                10034: 10034, #profiles
                10040: 10040, #addonbrowser
                10100: 10100, #yesnodialog
                10101: 10101, #progressdialog
                10103: T(32126), #32126
                10104: T(32127), #volume bar
                10106: T(32128), #context menu
                10107: T(32129), #info dialog
                10109: T(32130), #numeric input
                10111: T(32131), #shutdown menu
                10113: u'mute bug',
                10114: T(32132), #player controls
                10115: T(32133), #seek bar
                10120: T(32134), #music OSD
                10122: T(32135), #visualisation preset list
                10123: T(32136), #OSD video settings
                10124: T(32137), #OSD audio settings
                10125: T(32138), #video bookmarks
                10126: T(32139), #file browser
                10128: T(32140), #network setup
                10129: T(32141), #media source
                10130: 10034, #profilesettings
                10131: 20043, #locksettings
                10132: 20333, #contentsettings
                10134: 1036, #favourites
                10135: 658, #songinformation
                10136: T(32142), #smart playlist editor
                10137: 21421, #smartplaylistrule
                10138: T(32143), #busy dialog
                10139: 13406, #pictureinfo
                10140: T(32144), #addon settings
                10141: 1046, #accesspoints
                10142: T(32145), #fullscreen info
                10143: T(32146), #karaoke selector
                10144: T(32147), #karaoke large selector
                10145: T(32148), #slider dialog
                10146: T(32149), #addon information
                10147: T(32150), #text viewer
                10149: 35000, #peripherals
                10150: T(32151), #peripheral settings
                10151: 10101, #extended progress dialog - using string for progress dialog
                10152: T(32152), #media filter
                10153: T(32201), #subtitles dialog
                10500: 20011, #musicplaylist
                10501: 10501, #musicfiles
                10502: 10502, #musiclibrary
                10503: 10503, #musicplaylisteditor
                10601: T(32153), #pvr
                10602: T(32154), #pvr guide info
                10603: T(32155), #pvr recording info
                10604: T(32156), #pvr timer setting
                10605: T(32157), #pvr group manager
                10606: T(32158), #pvr channel manager
                10607: T(32159), #pvr guide search
                10610: T(32160), #pvr OSD channels
                10611: T(32161), #pvr OSD guide
                10615: T(32188), #tvchannels
                10616: T(32189), #tvrecordings
                10617: T(32190), #tvguide
                10618: T(32191), #tvtimers
                10619: T(32192), #tvsearch
                10620: T(32193), #radiochannels
                10621: T(32194), #radiorecordings
                10622: T(32195), #radioguide
                10623: T(32196), #radiotimers
                10624: T(32197), #radiosearch
                11000: T(32162), #virtual keyboard
                12000: 12000, #selectdialog
                12001: 12001, #musicinformation
                12002: 12002, #okdialog
                12003: 12003, #movieinformation
                12005: 12005, #fullscreenvideo
                12006: 12006, #visualisation
                12007: 108, #slideshow
                12008: 12008, #filestackingdialog
                12009: 13327, #karaoke
                12600: 12600, #weather
                12900: 12900, #screensaver
                12901: 12901, #videoosd
                12902: T(32163), #video menu
                12999: 512, #startup
                14000: T(32164) #PVR Client Specific Settings
}

winTexts = {}

winExtraTexts = {    10000:(555,'$INFO[System.Time]',8,'$INFO[Weather.Temperature]','$INFO[Weather.Conditions]'), #Home
                    10146:(    21863, #Addon Info Dialog
                            '$INFO[ListItem.Property(Addon.Creator)]',
                            19114,
                            '$INFO[ListItem.Property(Addon.Version)]',
                            21821,'$INFO[ListItem.Property(Addon.Description)]'
                    )
}

itemExtraTexts = {    }

winListItemProperties = {        10040:('$INFO[ListItem.Property(Addon.Status)]',)

}


def getWindowAddonID(winID):
    path = xbmc.getInfoLabel('Window({0}).Property(xmlfile)'.format(winID)).decode('utf-8')
    addonID = path.replace('\\', '/').split('/addons/',1)[-1].split('/',1)[0]
    return addonID

def getWindowAddonName(winID):
    addonID = getWindowAddonID(winID)
    return xbmc.getInfoLabel('System.AddonTitle({0})'.format(addonID)) or addonID

def getWindowName(winID):
    name = None
    if winID in winNames:
        name = winNames[winID]
        if isinstance(name,int): name = xbmc.getLocalizedString(name)
    elif winID > 12999:
        return getWindowAddonName(winID)
    return name or xbmc.getInfoLabel('System.CurrentWindow').decode('utf-8') or T(32165) #T(unknown)

def convertTexts(winID,data_list):
    ret = []
    for sid in data_list:
        if isinstance(sid,int):
            sid = xbmc.getLocalizedString(sid)
        elif sid.isdigit():
            sid = xbmc.getInfoLabel('Control.GetLabel({0})'.format(sid)).decode('utf-8')
        elif sid.startswith('$INFO['):
            info = sid[6:-1]
            sid = xbmc.getInfoLabel(info).decode('utf-8')
        if sid: ret.append(sid)
    return ret

def getWindowTexts(winID,table=winTexts):
    if not winID in table: return None
    return convertTexts(winID,table[winID]) or None

def getExtraTexts(winID):
    return getWindowTexts(winID,table=winExtraTexts)

def getItemExtraTexts(winID):
    return getWindowTexts(winID,table=itemExtraTexts)

def getListItemProperty(winID):
    texts = getWindowTexts(winID,table=winListItemProperties)
    if not texts: return None
    return u','.join(texts)

def getSongInfo():
    if xbmc.getCondVisibility('ListItem.IsFolder'): return None
    title = xbmc.getInfoLabel('ListItem.Title')
    genre = xbmc.getInfoLabel('ListItem.Genre')
    duration = xbmc.getInfoLabel('ListItem.Duration')
    if not (title or genre or duration): return None
    ret = []
    if title:
        ret.append(xbmc.getLocalizedString(556))
        ret.append(title.decode('utf-8'))
    if genre:
        ret.append(xbmc.getLocalizedString(515))
        ret.append(genre.decode('utf-8'))
    if duration:
        ret.append(xbmc.getLocalizedString(180))
        ret.append(duration.decode('utf-8'))
    return ret

