import os, xbmc, xbmcgui, xbmcvfs, dialogs
from distutils.version import StrictVersion
from util import LOG, ERROR, getSetting, setSetting, __addon__, T

DEBUG = None
CACHE_PATH = None

def copyKeyboardModImages(skinPath):
	dst = os.path.join(skinPath,'media','forum-browser-keyboard')
	#if os.path.exists(dst): return
	if not os.path.exists(dst): os.makedirs(dst)
	src = os.path.join(xbmc.translatePath(__addon__.getAddonInfo('path')),'keyboard','images')
	for f in os.listdir(src):
		s = os.path.join(src,f)
		d = os.path.join(dst,f)
		if not os.path.exists(d) and not f.startswith('.'): xbmcvfs.copy(s,d)

def copyFont(sourceFontPath,skinPath):
	dst = os.path.join(skinPath,'fonts','ForumBrowser-DejaVuSans.ttf')
	if os.path.exists(dst): return
	xbmcvfs.copy(sourceFontPath,dst)
	
def copyTree2(source,target):
	try:
		import distutils.dir_util
		copyTree = distutils.dir_util.copy_tree
	except:
		import shutil
		copyTree = shutil.copytree
		
	copyTree(source, target)
		
def copyTree(source,target,dialog=None):
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
			if dialog: dialog.update(pct,T(32478),f)
			xbmcvfs.copy(os.path.join(path,f),os.path.join(target,subpath,f))
			pct += mod
			if pct > 100:
				pct = 95
				mod = -5
			elif pct < 0:
				pct = 5
				mod = 5

def getSkinVersion(skin_path):
	addon = os.path.join(skin_path,'addon.xml')
	if not os.path.exists(addon): return '0.0.0'
	acontent = open(addon,'r').read()
	return acontent.split('<addon',1)[-1].split('version="',1)[-1].split('"',1)[0]
	

def getSkinFilePath(skinPath,skinFile):
	skinPath = os.path.join(skinPath,'720p',skinFile)
	if not os.path.exists(skinPath): skinPath = os.path.join(skinPath,'1080i',skinFile)
	if not os.path.exists(skinPath): return None
	return skinPath
	
def checkKBModRemove(skinPath):
		backupPath = getSkinFilePath(skinPath,'DialogKeyboard.xml.FBbackup')
		dialogPath = getSkinFilePath(skinPath,'DialogKeyboard.xml')
		if backupPath and dialogPath:
			xbmcvfs.delete(dialogPath)
			xbmcvfs.rename(backupPath,dialogPath)
			dialogs.showMessage(T(32476),T(32476),' ',T(32477))
			return True
				
def checkForSkinMods():
	skinPath = xbmc.translatePath('special://skin')
	if skinPath.endswith(os.path.sep): skinPath = skinPath[:-1]
	skinName = os.path.basename(skinPath)
	version = getSkinVersion(skinPath)
	LOG('XBMC Skin (In Use): %s %s' % (skinName,version))
	localAddonsPath = os.path.join(xbmc.translatePath('special://home'),'addons')
	localSkinPath = os.path.join(localAddonsPath,skinName)
	version2 = getSkinVersion(localSkinPath)
	LOG('XBMC Skin   (Home): %s %s' % (skinName,version2))
	if __addon__.getSetting('use_skin_mods') != 'true':
		LOG('Skin mods disabled')
		return checkKBModRemove(localSkinPath)
	font = os.path.join(localSkinPath,'fonts','ForumBrowser-DejaVuSans.ttf')
	install = True
	if os.path.exists(font):
		if StrictVersion(version2) >= StrictVersion(version):
			fontsXmlFile = os.path.join(localSkinPath,'720p','Font.xml')
			if not os.path.exists(fontsXmlFile): fontsXmlFile = os.path.join(localSkinPath,'1080i','Font.xml')
			if os.path.exists(fontsXmlFile):
				contents = open(fontsXmlFile,'r').read()
				if 'Forum Browser' in contents:
					LOG('Fonts mod detected')
					install = False
	if not install and not getSetting('use_keyboard_mod',False):
		LOG('Keyboard mod disabled')
		return checkKBModRemove(localSkinPath)
	
	dialogPath = os.path.join(localSkinPath,'720p','DialogKeyboard.xml')
	if not os.path.exists(dialogPath): dialogPath = os.path.join(localSkinPath,'1080i','DialogKeyboard.xml')
	if os.path.exists(dialogPath):
		keyboardcontents = open(dialogPath,'r').read()
		if 'Forum Browser' in keyboardcontents:
			LOG('Keyboard mod detected')
			return
	
	dialogs.showInfo('skinmods')
	yes = xbmcgui.Dialog().yesno(T(32479),T(32480),T(32481),T(32482))
	if not yes:
		__addon__.setSetting('use_skin_mods','false')
		dialogs.showMessage(T(32482),T(32484),' ',T(32485))
		return
	LOG('Installing Skin Mods')
	return installSkinMods()

def installSkinMods(update=False):
	if not getSetting('use_skin_mods',False): return
		
	#restart = False
	fbPath = xbmc.translatePath(__addon__.getAddonInfo('path'))
	localAddonsPath = os.path.join(xbmc.translatePath('special://home'),'addons')
	skinPath = xbmc.translatePath('special://skin')
	if skinPath.endswith(os.path.sep): skinPath = skinPath[:-1]
	currentSkin = os.path.basename(skinPath)
	localSkinPath = os.path.join(localAddonsPath,currentSkin)
	#LOG(localSkinPath)
	#LOG(skinPath)
	version = getSkinVersion(skinPath)
	version2 = getSkinVersion(localSkinPath)
	
	if not os.path.exists(localSkinPath) or StrictVersion(version2) < StrictVersion(version):
		yesno = xbmcgui.Dialog().yesno(T(32486),T(32487).format(currentSkin),T(32488),T(32489))
		if not yesno: return
		dialog = xbmcgui.DialogProgress()
		dialog.create(T(32490),T(32491))
		try:
			copyTree(skinPath,localSkinPath,dialog)
		except:
			err = ERROR('Failed to copy skin to user directory')
			dialogs.showMessage(T(32050),err,T(32492),error=True)
			return
		finally:
			dialog.close()
		#restart = True
		dialogs.showMessage(T(32304),T(32493),T(32494),success=True)
		
	skinPath = localSkinPath
	sourceFontXMLPath = os.path.join(fbPath,'keyboard','Font-720p.txt')
	sourceFontPath = os.path.join(fbPath,'keyboard','ForumBrowser-DejaVuSans.ttf')
	dialogPath = os.path.join(skinPath,'720p','DialogKeyboard.xml')
	backupPath = os.path.join(skinPath,'720p','DialogKeyboard.xml.FBbackup')
	fontPath = os.path.join(skinPath,'720p','Font.xml')
	fontBackupPath = os.path.join(skinPath,'720p','Font.xml.FBbackup')
	if not os.path.exists(dialogPath):
		dialogPath = dialogPath.replace('720p','1080i')
		backupPath = backupPath.replace('720p','1080i')
		fontPath = fontPath.replace('720p','1080i')
		fontBackupPath = fontBackupPath.replace('720p','1080i')
		sourceFontXMLPath = sourceFontXMLPath.replace('720p','1080i')
	
	LOG('Local Addons Path: %s' % localAddonsPath)
	LOG('Current skin: %s' % currentSkin)
	LOG('Skin path: %s' % skinPath)
	LOG('Keyboard target path: %s' % dialogPath)
	
	copyFont(sourceFontPath,skinPath)
	fontcontents = open(fontPath,'r').read()
	if not os.path.exists(fontBackupPath) or not 'Forum Browser' in fontcontents:
		LOG('Creating backup of original Font.xml file: ' + fontBackupPath)
		open(fontBackupPath,'w').write(fontcontents)
		
	if not 'Forum Browser' in fontcontents or update:
		LOG('Modifying contents of Font.xml with: ' + sourceFontXMLPath)
		original = open(fontPath,'r').read()
		modded = original.replace('<font>',open(sourceFontXMLPath,'r').read() + '<font>',1)
		open(fontPath,'w').write(modded)
	dialogs.showMessage(T(32052),'',T(32495))
	
	if update and not getSetting('use_keyboard_mod',False): return True
	
	yes = xbmcgui.Dialog().yesno(T(32496),T(32497),T(32498))
	setSetting('use_keyboard_mod',yes and 'true' or 'false')
	
	if yes:
		keyboardFile = chooseKeyboardFile(fbPath,currentSkin)
		if not keyboardFile: return True
		sourcePath = os.path.join(fbPath,'keyboard',keyboardFile)
		LOG('Keyboard source path: %s' % sourcePath)
		copyKeyboardModImages(skinPath)
		keyboardcontents = open(dialogPath,'r').read()
		if not os.path.exists(backupPath) or not 'Forum Browser' in keyboardcontents:
			LOG('Creating backup of original DialogKeyboard.xml file: ' + backupPath)
			open(backupPath,'w').write(open(dialogPath,'r').read())
		
		if not 'Forum Browser' in keyboardcontents or update:
			LOG('Replacing DialogKeyboard.xml with: ' + sourcePath)
			os.remove(dialogPath)
			open(dialogPath,'w').write(open(sourcePath,'r').read())
		dialogs.showMessage(T(32052),'',T(32499))
	else:
		dialogs.showMessage(T(32483),T(32521),' ',T(32522))
	return True

def chooseKeyboardFile(fbPath,currentSkin):
	files = os.listdir(os.path.join(fbPath,'keyboard'))
	skins = []
	for f in files:
		if f.startswith('DialogKeyboard-'):
			skinName = f.split('-',1)[-1].rsplit('.',1)[0].lower()
			if skinName in currentSkin.lower() or skinName == 'generic': skins.append(skinName.title())
	idx = xbmcgui.Dialog().select(T(32523),skins)
	if idx < 0: return None
	return 'DialogKeyboard-%s.xml' % skins[idx].lower()