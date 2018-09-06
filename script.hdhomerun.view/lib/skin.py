# -*- coding: utf-8 -*-
import os
import json
import xbmc, xbmcvfs
import util

#Skins that work without font modification:
#
# skin.aeon.nox.5
# skin.xperience1080
# skin.mimic
# skin.neon <- No font30, but I'll leave it for now
# skin.bello

FONT_TRANSLATIONS = {
    'skin.maximinimalism':{'font10':'smallMedium',            'font13':'regular',         'font30':'large'},
    'skin.back-row':      {'font10':'font12',                 'font13':'special14',       'font30':'special16'},
    'skin.box':           {'font10':'Panel_ItemChooser',      'font13':'List_Focused',    'font30':'Panel_Description_Title'},
    'skin.titan':         {'font10':'Reg24',                  'font13':'font13',          'font30':'Reg42'},
    'skin.rapier':        {'font10':'ListFont5',              'font13':'WeatherCurrentReadingFont2', 'font30':'FullMediaInfoTitleFont3'},
    'skin.sio2':          {'font10':'size22',                 'font13':'size28',          'font30':'size38'},
    'skin.blackglassnova':{'font10':'rss',                    'font13':'SmallButtonFont', 'font30':'WindowTitleFont'},
    'skin.nebula':        {'font10':'BadgeFont',              'font13':'SmallButtonFont', 'font30':'InfoTitleFont'},
    'skin.transparency':  {'font10':'font-15',                'font13':'font13',          'font30':'font-30'},
    'skin.arctic.zephyr': {'font10':'Mini',                   'font13':'font13',          'font30':'Large'},
    'skin.apptv':         {'font10':'font10',                 'font13':'font10',          'font30':'font18'}, #No font10 equivalent
    'skin.eminence':      {'font10':'Font-RSS',               'font13':'font13',          'font30':'Font-ViewCategory'},
    'skin.amber':         {'font10':'GridItems',              'font13':'Details',         'font30':'MainLabelBigTitle'}, #Old gui API level - alignment flaws
    'skin.metropolis':    {'font10':'METF_DialogVerySmall',   'font13':'font13',          'font30':'METF_TitleTextLarge'},
    'skin.quartz':        {'font10':'size14',                 'font13':'font13',          'font30':'size28'}, #Old gui API level - alignment flaws
    'skin.estuary':       {'font10':'font20_title',                 'font13':'font12',          'font30':'font30'}
}

#helix skins to check =  [' skin.refocus', ' skin.1080xf', ' skin.conq']

FONTS = ('font10','font13','font30')

VERSION = util.ADDON.getAddonInfo('version')
VERSION_FILE = os.path.join(xbmc.translatePath(util.ADDON.getAddonInfo('profile')).decode('utf-8'),'skin','version')
KODI_VERSION_FILE = os.path.join(xbmc.translatePath(util.ADDON.getAddonInfo('profile')).decode('utf-8'),'skin','kodi_version')

def skinningAPIisOld():
    try:
        return util.Version(util.xbmcaddon.Addon('xbmc.gui').getAddonInfo('version')) < util.Version('5.2.0')
    except:
        util.ERROR()
        return False

OLD_API = skinningAPIisOld()


OVERLAY = 'script-hdhomerun-view-overlay.xml'
CHANNEL_ENTRY = 'script-hdhomerun-view-channel_entry.xml'
DVR_WINDOW = "script-hdhomerun-view-dvr.xml"

DVR_RECORD_DIALOG = "script-hdhomerun-view-dvr_record_dialog.xml"
DVR_EPISODES_DIALOG = "script-hdhomerun-view-dvr_episodes_dialog.xml"
OPTIONS_DIALOG = "script-hdhomerun-view-options.xml"


SKINS_XMLS = (OVERLAY,CHANNEL_ENTRY,DVR_WINDOW,DVR_RECORD_DIALOG,DVR_EPISODES_DIALOG,OPTIONS_DIALOG)

def copyTree(source,target):
	pct = 0
	mod = 5
	if not source or not target: return
	if not os.path.isdir(source): return
	sourcelen = len(source)
	if not source.endswith(os.path.sep): sourcelen += 1
	for path, dirs, files in os.walk(source): #@UnusedVariable
		subpath = path[sourcelen:]
		xbmcvfs.mkdir(os.path.join(target,subpath))
		for f in files:
			xbmcvfs.copy(os.path.join(path,f),os.path.join(target,subpath,f))
			pct += mod
			if pct > 100:
				pct = 95
				mod = -5
			elif pct < 0:
				pct = 5
				mod = 5

def currentKodiSkin():
    skinPath = xbmc.translatePath('special://skin').rstrip('/\\')
    return os.path.basename(skinPath)

def setupDynamicSkin():
    import shutil
    targetDir = os.path.join(xbmc.translatePath(util.ADDON.getAddonInfo('profile')).decode('utf-8'),'skin','resources')
    target = os.path.join(targetDir,'skins')

    if os.path.exists(target):
        shutil.rmtree(target,True)
    if not os.path.exists(targetDir): os.makedirs(targetDir)

    source = os.path.join(xbmc.translatePath(util.ADDON.getAddonInfo('path')).decode('utf-8'),'resources','skins')
    copyTree(source,target)

def customizeSkinXML(skin,xml):
    source = os.path.join(xbmc.translatePath(util.ADDON.getAddonInfo('path')).decode('utf-8'),'resources','skins','Main','1080i',xml)
    target = os.path.join(xbmc.translatePath(util.ADDON.getAddonInfo('profile')).decode('utf-8'),'skin','resources','skins','Main','1080i',xml)
    with open(source,'r') as s:
        data = s.read()

    for font in FONTS:
        data = data.replace(font,'@{0}@'.format(font))
    for font in FONTS:
        data = data.replace('@{0}@'.format(font),FONT_TRANSLATIONS[skin][font])

    if kodiHasNewStringInfoLabels():
        util.DEBUG_LOG('Updating skins for new InfoLabels')
        data = data.replace('IsEmpty', 'String.IsEmpty')
        data = data.replace('StringCompare', 'String.IsEqual')
        # SubString(info,string[,Left|Right])
        # data.replace('SubString', 'String.StartsWith')
        # data.replace('SubString', 'String.EndsWith')
        # data.replace('SubString', 'String.Contains')

    with open(target,'w') as t:
        t.write(data)

def updateNeeded():
    if not os.path.exists(VERSION_FILE): return True
    if not os.path.exists(KODI_VERSION_FILE): return True
    with open(VERSION_FILE, 'r') as f:
        version = f.read()
    if version != '{0}:{1}:{2}'.format(currentKodiSkin(),VERSION,OLD_API and ':old' or ''): return True
    return False

def kodiHasNewStringInfoLabels():
    return getKodiVersion()['major'] > 17

def getKodiVersion():
    json_query = xbmc.executeJSONRPC('{ "jsonrpc": "2.0", "method": "Application.GetProperties", "params": {"properties": ["version", "name"]}, "id": 1 }')
    json_query = unicode(json_query, 'utf-8', errors='ignore')
    json_query = json.loads(json_query)
    return json_query['result']['version']

def getSkinPath():
    skin = currentKodiSkin()
    default = util.ADDON.getAddonInfo('path')
    if skin == 'skin.confluence': return default
    if not skin in FONT_TRANSLATIONS: return default
    if updateNeeded():
        util.DEBUG_LOG('Updating custom skin')
        try:
            setupDynamicSkin()

            for xml in SKINS_XMLS:
                customizeSkinXML(skin,xml)
            with open(VERSION_FILE, 'w') as f:
                f.write('{0}:{1}:{2}'.format(currentKodiSkin(),VERSION,OLD_API and ':old' or ''))
            with open(KODI_VERSION_FILE, 'w') as f:
                f.write(json.dumps(getKodiVersion()))
        except:
            util.ERROR()
            return default

    util.DEBUG_LOG('Using custom fonts for: {0}'.format(skin))

    return os.path.join(xbmc.translatePath(util.ADDON.getAddonInfo('profile')).decode('utf-8'),'skin')
