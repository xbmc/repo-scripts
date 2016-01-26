import xbmc, xbmcgui, xbmcaddon, sys, os

try: addonID2 = xbmcaddon.Addon().getAddonInfo("id")
except: addonID2 = "N/A"
#except Exception, TypeError: print "addonID2-TypeError: " + str(TypeError)
try: printfirst = xbmcaddon.Addon().getAddonInfo("name") + ": !@# "
except: printfirst = "N/A"
'''---------------------------'''

'''------------------------------
---DEFAULT-----------------------
------------------------------'''
space = " "
space2 = ": "
space3 = "_"
space4 = " / "
space5 = " - "
newline = "\n"
TypeError = ""
dialog = xbmcgui.Dialog()
systemplatformwindows = xbmc.getCondVisibility('System.Platform.Windows')
systemplatformlinux = xbmc.getCondVisibility('System.Platform.Linux')
systemplatformlinuxraspberrypi = xbmc.getCondVisibility('System.Platform.Linux.RaspberryPi')
systemplatformandroid = xbmc.getCondVisibility('System.Platform.Android')

if systemplatformandroid:
	pass
	from shared_subprocess import *
	
systemplatformosx = xbmc.getCondVisibility('System.Platform.OSX')
systemplatformios = xbmc.getCondVisibility('System.Platform.IOS')

systemidle0 = xbmc.getCondVisibility('System.IdleTime(0)')
systemidle1 = xbmc.getCondVisibility('System.IdleTime(1)')
systemidle3 = xbmc.getCondVisibility('System.IdleTime(3)')
systemidle7 = xbmc.getCondVisibility('System.IdleTime(7)')
systemidle10 = xbmc.getCondVisibility('System.IdleTime(10)')
systemidle40 = xbmc.getCondVisibility('System.IdleTime(40)')
systemidle120 = xbmc.getCondVisibility('System.IdleTime(120)')
systemidle300 = xbmc.getCondVisibility('System.IdleTime(300)')
systemidle5400 = xbmc.getCondVisibility('System.IdleTime(5400)') #1.5H
systemidle6900 = xbmc.getCondVisibility('System.IdleTime(6900)') #2H-5min
systemcurrentcontrol = xbmc.getInfoLabel('System.CurrentControl')
systemcurrentwindow = xbmc.getInfoLabel('System.CurrentWindow')
gh1 = 'https://github.com/'
gh2 = 'finalmakerr/featherence/raw/master/'
gh3 = 'xbmc-adult/xbmc-adult/raw/ghmaster/'
gh4 = 'cubicle-vdo/xbmc-israel/raw/master/repo/'
gh10 = 'https://offshoregit.com/'
gh11 = 'xbmchub/xbmc-hub-repo/raw/master/'
'''---------------------------'''

addon = 'script.featherence.service'
if xbmc.getCondVisibility('System.HasAddon('+ addon +')'):
	getsetting_servicefeatherence = xbmcaddon.Addon(addon).getSetting
	setsetting_servicefeatherence = xbmcaddon.Addon(addon).setSetting
	addonString_servicefeatherence = xbmcaddon.Addon(addon).getLocalizedString
	servicefeatherence_Skin_UpdateLog = getsetting_servicefeatherence('Skin_UpdateLog')
	servicefeatherence_Skin_Name = getsetting_servicefeatherence('Skin_Name') #TEMP
	servicefeatherence_General_DownloadON = getsetting_servicefeatherence('General_DownloadON')
	General_DownloadON = getsetting_servicefeatherence('General_DownloadON')
	admin = getsetting_servicefeatherence('admin')
	admin2 = "a"
	if xbmc.getInfoLabel('Network.MacAddress') == '0C:8B:FD:9D:2F:CE': admin3 = 'true'
	elif xbmc.getInfoLabel('Network.MacAddress') != "": admin3 = 'false'
	else: admin3 = 'false'
	'''---------------------------'''
else:
	servicefeatherence_Skin_UpdateLog = ""
	servicefeatherence_Skin_Name = ""
	addonString_servicefeatherence = ""
	servicefeatherence_General_DownloadON = ""
	General_DownloadON = ""
	admin3 = 'false'
	'''---------------------------'''

addon = 'script.featherence.service.debug'
if xbmc.getCondVisibility('System.HasAddon('+ addon +')'):
	getsetting_scriptfeatherencedebug         = xbmcaddon.Addon(addon).getSetting
	setsetting_scriptfeatherencedebug         = xbmcaddon.Addon(addon).setSetting
	'''---------------------------'''
	scriptfeatherencedebug_General_AllowDebug = getsetting_scriptfeatherencedebug('General_AllowDebug')
	scriptfeatherencedebug_General_ScriptON = getsetting_scriptfeatherencedebug('General_ScriptON')
	'''---------------------------'''
	scriptfeatherencedebug_Info_Bluetooth = getsetting_scriptfeatherencedebug('Info_Bluetooth')
	scriptfeatherencedebug_Info_Intel = getsetting_scriptfeatherencedebug('Info_Intel')
	scriptfeatherencedebug_Info_Model = getsetting_scriptfeatherencedebug('Info_Model')
	scriptfeatherencedebug_Info_SystemName = getsetting_scriptfeatherencedebug('Info_SystemName')
	scriptfeatherencedebug_Info_TotalMemory = getsetting_scriptfeatherencedebug('Info_TotalMemory')
	scriptfeatherencedebug_Info_TotalSpace = getsetting_scriptfeatherencedebug('Info_TotalSpace')
	'''---------------------------'''
	scriptfeatherencedebug_User_ID = getsetting_scriptfeatherencedebug('User_ID')
	scriptfeatherencedebug_User_Name = getsetting_scriptfeatherencedebug('User_Name')
	scriptfeatherencedebug_User_Email = getsetting_scriptfeatherencedebug('User_Email')
	scriptfeatherencedebug_User_Tel = getsetting_scriptfeatherencedebug('User_Tel')
	scriptfeatherencedebug_User_Issue = getsetting_scriptfeatherencedebug('User_Issue')
	'''---------------------------'''
else:
	scriptfeatherencedebug_General_AllowDebug = ""
	scriptfeatherencedebug_General_ScriptON = ""
	'''---------------------------'''
	scriptfeatherencedebug_Info_Bluetooth = ""
	scriptfeatherencedebug_Info_Intel = ""
	scriptfeatherencedebug_Info_Model = ""
	scriptfeatherencedebug_Info_SystemName = ""
	scriptfeatherencedebug_Info_TotalMemory = ""
	scriptfeatherencedebug_Info_TotalSpace = ""
	'''---------------------------'''
	scriptfeatherencedebug_User_ID = ""
	scriptfeatherencedebug_User_Name = ""
	scriptfeatherencedebug_User_Email = ""
	scriptfeatherencedebug_User_Tel = ""
	scriptfeatherencedebug_User_Issue = ""
	'''---------------------------'''
	
'''------------------------------
---Window.-----------------------
------------------------------'''

custom1115W = xbmc.getCondVisibility('Window.IsVisible(Custom1115.xml)')
custom1124W = xbmc.getCondVisibility('Window.IsVisible(Custom1124.xml)')
custom1125W = xbmc.getCondVisibility('Window.IsVisible(Custom1125.xml)')
custom1132W = xbmc.getCondVisibility('Window.IsVisible(Custom1132.xml)')
#custom1133W = xbmc.getCondVisibility('Window.IsVisible(Custom1133.xml)')
custom1134W = xbmc.getCondVisibility('Window.IsVisible(Custom1134.xml)')
custom1135W = xbmc.getCondVisibility('Window.IsVisible(Custom1135.xml)')
custom1136W = xbmc.getCondVisibility('Window.IsVisible(Custom1136.xml)')
custom1170W = xbmc.getCondVisibility('Window.IsVisible(Custom1170.xml)')
custom1171W = xbmc.getCondVisibility('Window.IsVisible(Custom1171.xml)')
custom1172W = xbmc.getCondVisibility('Window.IsVisible(Custom1172.xml)')
custom1191W = xbmc.getCondVisibility('Window.IsVisible(Custom1191.xml)')
scriptpythonslideshowW = xbmc.getCondVisibility('Window.IsVisible(script-python-slideshow.xml)')

customhomecustomizerW = xbmc.getCondVisibility('Window.IsVisible(CustomHomeCustomizer.xml)')
dialogaddoninfoW = xbmc.getCondVisibility('Window.IsVisible(DialogAddonInfo.xml)')
addonbrowserW = xbmc.getCondVisibility('Window.IsVisible(AddonBrowser.xml)')
dialogaddonsettingsW = xbmc.getCondVisibility('Window.IsVisible(DialogAddonSettings.xml)')
dialogbusyW = xbmc.getCondVisibility('Window.IsVisible(DialogBusy.xml)')
dialogcontentsettingsW = xbmc.getCondVisibility('Window.IsVisible(DialogContentSettings.xml)')
dialogcontextmenuW = xbmc.getCondVisibility('Window.IsVisible(DialogContextMenu.xml)')
dialogfavouritesW = xbmc.getCondVisibility('Window.IsVisible(DialogFavourites.xml)')
dialogfilebrowserW = xbmc.getCondVisibility('Window.IsVisible(FileBrowser.xml)')
dialogkaitoastW = xbmc.getCondVisibility('Window.IsVisible(DialogKaiToast.xml)')
dialogkeyboardW = xbmc.getCondVisibility('Window.IsVisible(DialogKeyboard.xml)') ###fix to W
dialogokW = xbmc.getCondVisibility('Window.IsVisible(DialogOk.xml)')
dialogprogressW = xbmc.getCondVisibility('Window.IsVisible(DialogProgress.xml)')
dialogselectW = xbmc.getCondVisibility('Window.IsVisible(DialogSelect.xml)')
dialogsubtitlesW = xbmc.getCondVisibility('Window.IsVisible(DialogSubtitles.xml)')
dialogtextviewerW = xbmc.getCondVisibility('Window.IsVisible(DialogTextViewer.xml)')
dialogvideoinfoW = xbmc.getCondVisibility('Window.IsVisible(DialogVideoInfo.xml)')
dialogyesnoW = xbmc.getCondVisibility('Window.IsVisible(DialogYesNo.xml)')
filemanagerW = xbmc.getCondVisibility('Window.IsVisible(FileManager.xml)')
loginscreenW = xbmc.getCondVisibility('Window.IsVisible(LoginScreen.xml)')
loginscreen_aW = xbmc.getCondVisibility('Window.IsActive(LoginScreen.xml)')
mainwindow = xbmc.getCondVisibility('Window.IsVisible(mainWindow.xml)') #OpenELEC ###fix to W
mainwindowW = xbmc.getCondVisibility('Window.IsVisible(mainWindow.xml)') #OpenELEC
mypicsW = xbmc.getCondVisibility('Window.IsVisible(MyPics.xml)')
myprogramsW = xbmc.getCondVisibility('Window.IsVisible(MyPrograms.xml)')
mymusicnavW = xbmc.getCondVisibility('Window.IsVisible(MyMusicNav.xml)')
homeW = xbmc.getCondVisibility('Window.IsVisible(Home.xml)')
myweatherW = xbmc.getCondVisibility('Window.IsVisible(MyWeather.xml)')
videoosdW = xbmc.getCondVisibility('Window.IsVisible(VideoOSD.xml)')
videoosdsettingsW = xbmc.getCondVisibility('Window.IsVisible(VideoOSDSettings.xml)')
dialogpvrchannelsosd = xbmc.getCondVisibility('Window.IsVisible(DialogPVRChannelsOSD.xml)')
mypvrchannels = xbmc.getCondVisibility('Window.IsVisible(MyPVRChannels.xml)')
mypvrguide = xbmc.getCondVisibility('Window.IsVisible(MyPVRGuide.xml)')
home_pW = xbmc.getCondVisibility('Window.Previous(0)')
home_aW = xbmc.getCondVisibility('Window.IsActive(0)')

settingsW = xbmc.getCondVisibility('Window.IsVisible(Settings.xml)')
settingscategoryW = xbmc.getCondVisibility('Window.IsVisible(SettingsCategory.xml)')
skinsettingsW = xbmc.getCondVisibility('Window.IsVisible(SkinSettings.xml)')
startupW = xbmc.getCondVisibility('Window.IsVisible(Startup.xml)')
startup_aW = xbmc.getCondVisibility('Window.IsActive(Startup.xml)')
startup_pW = xbmc.getCondVisibility('Window.Previous(Startup.xml)')
videofullscreenW = xbmc.getCondVisibility('Window.IsVisible(VideoFullScreen.xml)')
dialogvideonfoEW = xbmc.getCondVisibility('Window.IsVisible(script-ExtendedInfo Script-DialogVideoInfo.xml)')
'''---------------------------'''

'''------------------------------
---Skin.HasSetting---------------
------------------------------'''

adult = xbmc.getInfoLabel('Skin.HasSetting(Adult)')
autoview = xbmc.getInfoLabel('!Skin.HasSetting(AutoView)')
connected = xbmc.getInfoLabel('Skin.HasSetting(Connected)')
connected2 = xbmc.getInfoLabel('Skin.HasSetting(Connected2)')
connected3 = xbmc.getInfoLabel('Skin.HasSetting(Connected3)')

myfeatherence2 = xbmc.getInfoLabel('!Skin.HasSetting(myfeatherence2)')
myfeatherence3 = xbmc.getInfoLabel('Skin.HasSetting(myfeatherence3)')
allowdebug = xbmc.getInfoLabel('Skin.HasSetting(AllowDebug)') #TEMP
realdebrid = xbmc.getInfoLabel('Skin.HasSetting(RealDebrid)') #TEMP
sdarottv = xbmc.getInfoLabel('Skin.HasSetting(SdarotTV)') #TEMP
validation = xbmc.getInfoLabel('Skin.HasSetting(VALIDATION)') #TEMP
validation2 = xbmc.getInfoLabel('Skin.HasSetting(VALIDATION2)') #TEMP
validation5 = xbmc.getInfoLabel('Skin.String(VALIDATION5)') #TEMP
customgui = xbmc.getInfoLabel('Skin.HasSetting(CustomGUI)')
showdialog = xbmc.getInfoLabel('Skin.HasSetting(ShowDialog)')
customas = xbmc.getInfoLabel('Skin.HasSetting(CustomAS)')
customasources = xbmc.getInfoLabel('Skin.HasSetting(CustomSources)')
customkeymaps = xbmc.getInfoLabel('Skin.HasSetting(CustomKeymaps)')

if xbmc.getSkinDir() == 'skin.featherence':
	'''------------------------------
	---SKIN-STRINGS------------------
	------------------------------'''
	customsettingtemp = xbmc.getInfoLabel('Skin.String(Custom_Setting_Temp)') #TEMP

'''---------------------------'''
overclocklevel = xbmc.getInfoLabel('Skin.String(OverClockLevel)')
countrystr = xbmc.getInfoLabel('Skin.String(Country)')
skinnamestr = xbmc.getInfoLabel('Skin.String(Skin_Name)')

'''------------------------------
---ID----------------------------
------------------------------'''
'''idstr = USERNAME EN , id1str = USERNAME HE, id2str = INSTALLATION DATE, id3str = WARRENTY END, id4str = ADDRESS, id5str = TELEPHONE NUMBER, id6str = PAYMENT TERMS, id7str = QUESTION, id8str = TECHNICAL NAME, id9str = CODE RED, id10str = featherence'S MODEL, ID11 = MAC1, ID12 = MAC2'''
idstr = xbmc.getInfoLabel('Skin.String(User_ID)')
id1str = xbmc.getInfoLabel('Skin.String(ID1)')
id2str = xbmc.getInfoLabel('Skin.String(ID2)')
id3str = xbmc.getInfoLabel('Skin.String(ID3)')
id4str = xbmc.getInfoLabel('Skin.String(ID4)')
id5str = xbmc.getInfoLabel('Skin.String(ID5)')
id6str = xbmc.getInfoLabel('Skin.String(ID6)')
id7str = xbmc.getInfoLabel('Skin.String(ID7)')
id8str = xbmc.getInfoLabel('Skin.String(ID8)')
id9str = xbmc.getInfoLabel('Skin.String(ID9)')
id10str = xbmc.getInfoLabel('Skin.String(ID10)')
id11str = xbmc.getInfoLabel('Skin.String(ID11)')
id12str = xbmc.getInfoLabel('Skin.String(ID12)')
id40str = xbmc.getInfoLabel('Skin.HasSetting(ID40)') #TEMP
id60str = xbmc.getInfoLabel('Skin.String(ID60)') #TEMP
''''''
trial = xbmc.getInfoLabel('Skin.HasSetting(Trial)') #TEMP
trialdate = xbmc.getInfoLabel('Skin.String(TrialDate)')
trialdate2 = xbmc.getInfoLabel('Skin.String(TrialDate2)')
'''---------------------------'''
	
'''------------------------------
---Playlist----------------------
------------------------------'''
playlistlength = xbmc.getInfoLabel('Playlist.Length(video)')
playlistlengthN = int(playlistlength)
playlistposition = xbmc.getInfoLabel('Playlist.Position(video)')
playlistpositionN = int(playlistposition)
playlistrepeat = xbmc.getInfoLabel('Playlist.Repeat')
playlistrandom = xbmc.getInfoLabel('Playlist.Random')
'''---------------------------'''


'''------------------------------
---Player------------------------
------------------------------'''
playerhasvideo = xbmc.getCondVisibility('Player.HasVideo')
playerpaused = xbmc.getCondVisibility('Player.Paused')
playercache = xbmc.getInfoLabel('Player.CacheLevel')
playertitle = xbmc.getInfoLabel('Player.Title')
playerfilename = xbmc.getInfoLabel('Player.Filename')
playerhasaudio = xbmc.getCondVisibility('Player.HasAudio')
playerhasmedia = xbmc.getCondVisibility('Player.HasMedia')
playerfolderpath = xbmc.getInfoLabel('Player.FolderPath')
playertime = xbmc.getInfoLabel("Player.Time(hh)") + xbmc.getInfoLabel("Player.Time(mm)") + xbmc.getInfoLabel("Player.Time(ss)")
playertimeremaining = xbmc.getInfoLabel("Player.TimeRemaining(hh)") + xbmc.getInfoLabel("Player.TimeRemaining(mm)") + xbmc.getInfoLabel("Player.TimeRemaining(ss)")
playerduration = xbmc.getInfoLabel("Player.Duration(hh)") + xbmc.getInfoLabel("Player.Duration(mm)") + xbmc.getInfoLabel("Player.Duration(ss)")
'''---------------------------'''

'''------------------------------
---PATH--------------------------
------------------------------'''
israeltvhome = 'plugin://plugin.video.sdarot.tv/'
videorootpath = 'library://video/'
temp_path = os.path.join(xbmc.translatePath("special://temp/").decode("utf-8"))
home_path = os.path.join(xbmc.translatePath("special://home/").decode("utf-8"))
xbmc_path = os.path.join(xbmc.translatePath("special://xbmc/").decode("utf-8"))
addons_path = os.path.join(xbmc.translatePath("special://home/addons/").decode("utf-8"))
addonsDir = os.path.join(xbmc.translatePath("special://home/addons/").decode("utf-8")) #TEMP
userdata_path = os.path.join(xbmc.translatePath("special://userdata/").decode("utf-8"))
thumbnails_path = os.path.join(xbmc.translatePath("special://thumbnails").decode("utf-8"))
database_path = os.path.join(xbmc.translatePath("special://database").decode("utf-8"))	

config_path = os.path.join('/storage/','.config','')
flash_path = os.path.join('/flash', '')

library_path = os.path.join(userdata_path,'library', '')
downloads_path = os.path.join(library_path,'downloads','')
music_path = os.path.join(library_path,'music','')
pictures_path = os.path.join(library_path,'pictures','')
movies_path = os.path.join(library_path,'movies','')
tvshows_path = os.path.join(library_path,'tvshows','')
addondata_path = os.path.join(userdata_path,'addon_data','')

featherenceservice_addondata_path = os.path.join(addondata_path,'script.featherence.service', '')
if not os.path.exists(featherenceservice_addondata_path):
	try: os.mkdir(featherenceservice_addondata_path)
	except: pass
featherenceserviceaddondata_media_path = os.path.join(featherenceservice_addondata_path, 'media', '')
if not os.path.exists(featherenceserviceaddondata_media_path):
	try: os.mkdir(featherenceserviceaddondata_media_path)
	except: pass

packages_path = os.path.join(addons_path,'packages','')

#skin_path = os.path.join(xbmc.translatePath("special://skin").decode("utf-8"))
skin_path = os.path.join(addons_path,'skin.featherence','') #WIP
featherenceservice_path = os.path.join(addons_path,'script.featherence.service','')
featherenceserviceicons_path = os.path.join(featherenceservice_path, 'resources', 'icons', '')
featherenceservicecopy_path = os.path.join(featherenceservice_path,'specials','scripts','copy','')
packagesDir = os.path.join(addonsDir,'packages') #TEMP
'''---------------------------'''
if admin == 'true' and 1 + 1 == 3:
	print printfirst + "variables paths list" + space2 + \
	newline + "skin_path" + space2 + skin_path + \
	newline + "home_path" + space2 + home_path + \
	newline + "addons_path" + space2 + addons_path + \
	newline + "featherenceservice_addondata_path" + space2 + featherenceservice_addondata_path + \
	newline + "packages_path" + space2 + packages_path + \
	newline + "temp_path" + space2 + temp_path

'''------------------------------
---?--------------------------
------------------------------'''
skinlog_file = os.path.join(skin_path,'changelog.txt')
skinlog_en_file = os.path.join(skin_path,'changelog_en.txt')
sources_file = os.path.join(userdata_path,'sources.xml')
kodilog_file = os.path.join(temp_path,'kodi.log')
kodioldlog_file = os.path.join(temp_path,'kodi.old.log')
skininstalledtxt2 = os.path.join(home_path, 'Skin_Installed.txt')
guisettings_file = os.path.join(userdata_path, 'guisettings.xml')
guisettings2_file = os.path.join(featherenceservice_addondata_path, 'guisettings.xml')
guisettings3_file = os.path.join(featherenceservice_addondata_path, 'guisettings2.xml')
guisettings4_file = os.path.join(featherenceservice_addondata_path, 'guisettings_.xml')
guikeepersh_file = os.path.join(featherenceservice_path, 'specials', 'scripts', 'guikeeper.sh')
guikeepertxt_file = os.path.join(home_path, 'guikeeper.txt')
'''---------------------------'''

'''------------------------------
---Network.----------------------
------------------------------'''
dhcpaddress = xbmc.getInfoLabel('Network.DHCPAddress')
networkgatewayaddress = xbmc.getInfoLabel('Network.GatewayAddress')
networkipaddress = xbmc.getInfoLabel('Network.IPAddress')
systemhasnetwork = xbmc.getCondVisibility('System.HasNetwork')
'''---------------------------'''

'''------------------------------
---MIXED-------------------------
------------------------------'''

'''---------------------------'''

if xbmc.getSkinDir() == 'skin.featherence':
	'''------------------------------
	---$VAR--------------------------
	------------------------------'''
	startupmessage2 = xbmc.getInfoLabel('$VAR[StartupMessage2]')

'''------------------------------
---$LOCALIZE-PRIMARY-------------
------------------------------'''
str1 = xbmc.getInfoLabel('$LOCALIZE[1]').decode('utf-8') #Pictures
str2 = xbmc.getInfoLabel('$LOCALIZE[2]').decode('utf-8') #Music
str3 = xbmc.getInfoLabel('$LOCALIZE[3]').decode('utf-8') #Videos
settingslevelstr1 = xbmc.getInfoLabel('$LOCALIZE[10036]') #Basic
settingslevelstr2 = xbmc.getInfoLabel('$LOCALIZE[10037]') #Standard
settingslevelstr3 = xbmc.getInfoLabel('$LOCALIZE[10038]') #Advanced
settingslevelstr4 = xbmc.getInfoLabel('$LOCALIZE[10039]') #Expert

str20329 = xbmc.getInfoLabel('$LOCALIZE[20329]') #Movies are in separate folders that match the movie title
str20333 = xbmc.getInfoLabel('$LOCALIZE[20333]') #Set content
str20343 = xbmc.getInfoLabel('$LOCALIZE[20343]').decode('utf-8') #TV shows
str20346 = xbmc.getInfoLabel('$LOCALIZE[20346]').decode('utf-8') #Scan recursively
str20389 = xbmc.getInfoLabel('$LOCALIZE[20389]') #Music videos
falsestr = xbmc.getInfoLabel('$LOCALIZE[20424]') #False
str20442 = xbmc.getInfoLabel('$LOCALIZE[20442]') #Change content
str24056 = xbmc.getInfoLabel('$LOCALIZE[24056]').decode('utf-8') #Last updated %s
str22082 = xbmc.getInfoLabel('$LOCALIZE[22082]').decode('utf-8') #More...
str24021 = xbmc.getInfoLabel('$LOCALIZE[24021]').decode('utf-8') #Disable
str24022 = xbmc.getInfoLabel('$LOCALIZE[24022]').decode('utf-8') #Enable
str36901 = xbmc.getInfoLabel('$LOCALIZE[36901]').decode('utf-8') #movies
str36903 = xbmc.getInfoLabel('$LOCALIZE[36903]').decode('utf-8') #TV shows

systemlanguage = xbmc.getInfoLabel('System.Language')
'''---------------------------'''

if xbmc.getSkinDir() == 'skin.featherence':
	'''------------------------------
	---$LOCALIZE-SKIN----------------
	------------------------------'''

	todaystr = xbmc.getInfoLabel('$LOCALIZE[33006]') #Today (remove?)
	str70020 = xbmc.getInfoLabel('$LOCALIZE[70020]') #WOULD YOU LIKE TO ADD THIS CONTENT TO featherence?
	str72101 = xbmc.getInfoLabel('$LOCALIZE[72101]').decode('utf-8') #Today
	str72102 = xbmc.getInfoLabel('$LOCALIZE[72102]').decode('utf-8') #Yesterday
	str72103 = xbmc.getInfoLabel('$LOCALIZE[72103]').decode('utf-8') #This Week
	str73440 = xbmc.getInfoLabel('$LOCALIZE[73440]').decode('utf-8') #GoPro

	str74481 = xbmc.getInfoLabel('$LOCALIZE[74481]').decode('utf-8') #Starting a Send Report
	str74482 = xbmc.getInfoLabel('$LOCALIZE[74482]').decode('utf-8') #Sending Report (%s/%s)
	str74483 = xbmc.getInfoLabel('$LOCALIZE[74483]').decode('utf-8') #The report has been sent successfully
	str74484 = xbmc.getInfoLabel('$LOCALIZE[74484]').decode('utf-8') #Report has failed!
	str74485 = xbmc.getInfoLabel('$LOCALIZE[74485]').decode('utf-8') #featherence

	str74540 = xbmc.getInfoLabel('$LOCALIZE[74540]').decode('utf-8') #Your featherence model is %s
	str74541 = xbmc.getInfoLabel('$LOCALIZE[74541]').decode('utf-8') #This model support external media storage only!
	str74542 = xbmc.getInfoLabel('$LOCALIZE[74542]').decode('utf-8') #[CR][CR][COLOR=white2]For support please contact us by using the help button in the home screen.[/COLOR]
	str74543 = xbmc.getInfoLabel('$LOCALIZE[74543]').decode('utf-8') #This model has no support for %s
	str74544 = xbmc.getInfoLabel('$LOCALIZE[74544]').decode('utf-8') #This model has support for %s
	str74545 = xbmc.getInfoLabel('$LOCALIZE[74545]').decode('utf-8') #
	str74546 = xbmc.getInfoLabel('$LOCALIZE[74546]').decode('utf-8') #
	str74547 = xbmc.getInfoLabel('$LOCALIZE[74547]').decode('utf-8') #
	str74548 = xbmc.getInfoLabel('$LOCALIZE[74548]').decode('utf-8') #
	str74549 = xbmc.getInfoLabel('$LOCALIZE[74549]').decode('utf-8') #
	str74550 = xbmc.getInfoLabel('$LOCALIZE[74550]').decode('utf-8') #Add %s to library
	str74551 = xbmc.getInfoLabel('$LOCALIZE[74551]').decode('utf-8') #

	str79577 = xbmc.getInfoLabel('$LOCALIZE[79577]').decode('utf-8') #Update Movies and Tvshows library
	str79583 = xbmc.getInfoLabel('$LOCALIZE[79583]').decode('utf-8') #Added

'''------------------------------
---LIST--------------------------
------------------------------'''
ACTION_PREVIOUS_MENU = 10
ACTION_SELECT_ITEM = 7
'''---------------------------'''

'''------------------------------
---Window(Home).Property(key)----
------------------------------'''
windowhomeproperty_moviescount = xbmc.getInfoLabel('Window(Home).Property(Movies.Count)')
windowhomeproperty_tvshowscount = xbmc.getInfoLabel('Window(Home).Property(TVShows.Count)')
scriptfeatherenceservice_downloading = xbmc.getInfoLabel('Window(home).Property(script.featherence.service_downloading)')
scriptfeatherenceservice_random = xbmc.getInfoLabel('Window(home).Property(script.featherence.service_random)')
scriptfeatherenceservice_random1 = xbmc.getInfoLabel('Window(home).Property(script.featherence.service_random1)')
scriptfeatherenceservice_random2 = xbmc.getInfoLabel('Window(home).Property(script.featherence.service_random2)')
scriptfeatherenceservice_random3 = xbmc.getInfoLabel('Window(home).Property(script.featherence.service_random3)')
scriptfeatherenceservice_random4 = xbmc.getInfoLabel('Window(home).Property(script.featherence.service_random4)')
scriptfeatherenceservice_random5 = xbmc.getInfoLabel('Window(home).Property(script.featherence.service_random5)')
scriptfeatherenceservice_randomL = []
if scriptfeatherenceservice_random1 != "": scriptfeatherenceservice_randomL.append(scriptfeatherenceservice_random1)
if scriptfeatherenceservice_random2 != "": scriptfeatherenceservice_randomL.append(scriptfeatherenceservice_random2)
if scriptfeatherenceservice_random3 != "": scriptfeatherenceservice_randomL.append(scriptfeatherenceservice_random3)
if scriptfeatherenceservice_random4 != "": scriptfeatherenceservice_randomL.append(scriptfeatherenceservice_random4)
if scriptfeatherenceservice_random5 != "": scriptfeatherenceservice_randomL.append(scriptfeatherenceservice_random5)
'''---------------------------'''


'''------------------------------
---LISTITEM-------------
------------------------------'''
listitemduration = xbmc.getInfoLabel('ListItem.Duration')
listitemepisode = xbmc.getInfoLabel('ListItem.Episode')
listitemgenre = xbmc.getInfoLabel('ListItem.Genre')
listitempath = xbmc.getInfoLabel('ListItem.Path')
listitemrating = xbmc.getInfoLabel('ListItem.Rating')
listitemseason = xbmc.getInfoLabel('ListItem.Season')
listitemtitle = xbmc.getInfoLabel('ListItem.Title')
listitemtvshowtitle = xbmc.getInfoLabel('ListItem.TVShowTitle')
listitemlabel = xbmc.getInfoLabel('ListItem.Label')
listitemyear = xbmc.getInfoLabel('ListItem.Year')
listitemimdbnumber = xbmc.getInfoLabel('ListItem.IMDBNumber')
listitemdbid = xbmc.getInfoLabel('ListItem.DBID')
listitemdirector = xbmc.getInfoLabel('ListItem.Director')
listitemisselected = xbmc.getCondVisibility('ListItem.IsSelected')
'''---------------------------'''

'''------------------------------
---Library.----------------------
------------------------------'''
libraryhascontentmovies = xbmc.getCondVisibility('Library.HasContent(Movies)')
libraryhascontentmoviesets = xbmc.getCondVisibility('Library.HasContent(MovieSets)')
libraryhascontentmusic = xbmc.getCondVisibility('Library.HasContent(Music)')
libraryhascontentmusicvideos = xbmc.getCondVisibility('Library.HasContent(MusicVideos)')
libraryhascontenttvshows = xbmc.getCondVisibility('Library.HasContent(TVShows)')
libraryhascontentvideo = xbmc.getCondVisibility('Library.HasContent(Video)')
libraryisscanningvideo = xbmc.getCondVisibility('Library.IsScanningVideo')
libraryisscanningmusic = xbmc.getCondVisibility('Library.IsScanningMusic')
'''---------------------------'''

'''------------------------------
---EMPTY-------------------------
------------------------------'''
controlhasfocus698 = ""
controlhasfocus699 = ""

api_youtube_featherence = 'AIzaSyDkNxiwClyCildDbHdDKSWt5BkKQ6LeQqA' #AIzaSyASEuRNOghvziOY_8fWSbKGKTautNkAYz4
api_dailymotion_featherence = '3e563cafd4fbba5de0c1'
api_vimeo_featherence = '45584ad52d6951f441fd2f7c7ae690d2'
api_pastebin_featherence = '1040252c25203082ce6901fcf22e2756'
api_imagebin_featherence = 'c8LpkstmM3WBoukL+zaJdFRCJEMIWRwL'

'''------------------------------
---CONTROL-----------------------
------------------------------'''
autoplaypausebutton = (xbmc.getCondVisibility('Window.IsVisible(Home.xml)') and xbmc.getCondVisibility('Control.HasFocus(9093)')) or (xbmc.getCondVisibility('Window.IsVisible(Home.xml)') and xbmc.getCondVisibility('Control.HasFocus(111)'))
subtitleosdbutton = xbmc.getCondVisibility('Control.HasFocus(703)') #subtitleosdbutton
volumeosdbutton = xbmc.getCondVisibility('Control.HasFocus(707)') #volumeosdbutton

button99 = xbmc.getCondVisibility('Control.HasFocus(99)')
button100 = xbmc.getCondVisibility('Control.HasFocus(100)')
button101 = xbmc.getCondVisibility('Control.HasFocus(101)')
button102 = xbmc.getCondVisibility('Control.HasFocus(102)')
button103 = xbmc.getCondVisibility('Control.HasFocus(103)')
button104 = xbmc.getCondVisibility('Control.HasFocus(104)')
button105 = xbmc.getCondVisibility('Control.HasFocus(105)')

cancelbutton = xbmc.getCondVisibility('Control.HasFocus(10)') and xbmc.getCondVisibility('Window.IsActive(DialogProgress.xml)')
controlgetlabel1 = xbmc.getInfoLabel('Control.GetLabel(1)')
controlgetlabel100 = xbmc.getInfoLabel('Control.GetLabel(100)') #DialogSubtitles Service Name
controlhasfocus10 = xbmc.getCondVisibility('Control.HasFocus(10)') #No button
controlhasfocus11 = xbmc.getCondVisibility('Control.HasFocus(11)') #Yes button
controlhasfocus20 = xbmc.getCondVisibility('Control.HasFocus(20)')
controlisvisible311 = xbmc.getCondVisibility('Control.IsVisible(311)') or xbmc.getCondVisibility('Control.HasFocus(70)')
controlisvisible311S = str(controlisvisible311)
controlisvisible312 = xbmc.getCondVisibility('Control.IsVisible(312)') or xbmc.getCondVisibility('Control.HasFocus(71)')
controlisvisible312S = str(controlisvisible312)

debugbutton = xbmc.getCondVisibility('Container(50).HasFocus(5)') or (xbmc.getCondVisibility('Window.IsVisible(LoginScreen.xml)') and xbmc.getCondVisibility('Container(50).HasFocus(102)'))
'''---------------------------'''

'''------------------------------
---CONTAINER---------------------
------------------------------'''
container120numitems = xbmc.getInfoLabel('Container(120).NumItems') #DialogSubtitles
containernumitems = xbmc.getInfoLabel('Container.NumItems')
viewmode = xbmc.getInfoLabel('Container.Viewmode')
containerviewmode = xbmc.getInfoLabel('Container.Viewmode')
containerfolderpath = xbmc.getInfoLabel('Container.FolderPath')
containerfoldername = xbmc.getInfoLabel('Container.FolderName')
container50position = xbmc.getInfoLabel('Container(50).Position')
container57position = xbmc.getInfoLabel('Container(57).Position')
if homeW: container9000pos = xbmc.getInfoLabel('Container(9000).Position')
container50listitemlabel = xbmc.getInfoLabel('Container(50).ListItem.Label') #Actors #UNUSED!

'''------------------------------
---OPENELEC----------------------
------------------------------'''
openelec1 = xbmc.getInfoLabel('$ADDON[service.openelec.settings 32002]') #system
openelec2 = xbmc.getInfoLabel('$ADDON[service.openelec.settings 32000]') #network
openelec3 = xbmc.getInfoLabel('$ADDON[service.openelec.settings 32100]') #connections
openelec4 = xbmc.getInfoLabel('$ADDON[service.openelec.settings 32001]') #services
openelec5 = xbmc.getInfoLabel('$ADDON[service.openelec.settings 32331]') #bluetooth
openelec6 = xbmc.getInfoLabel('$ADDON[service.openelec.settings 32196]') #about
'''---------------------------'''

'''------------------------------
---DATES-----------------------
------------------------------'''
import datetime as dt
import time

datenow = dt.date.today()
datenowS = str(datenow)
'''---------------------------'''
dateafter = datenow + dt.timedelta(days=7)
dateafterS = str(dateafter)
'''---------------------------'''
yearnow = datenow.strftime("%Y")
yearnowS = str(yearnow)
'''---------------------------'''
daynow = datenow.strftime("%a")
daynowS = str(daynow)
timenow = dt.datetime.now()
timenowS = str(timenow)
timenow2 = timenow.strftime("%H:%M")
timenow2S = str(timenow2)
timenow2N = int(timenow2S.replace(":","",1)) #GAL CHECK # PAREMTERS WHY?
timenow3 = timenow.strftime("%H")
timenow3S = str(timenow3)
timenow3N = int(timenow3S)
timenow4 = timenow.strftime("%S")
timenow4S = str(timenow4)
timenow5 = timenow.strftime("%a %b %d %X %Y") #date and time representation
'''---------------------------'''
if timenow3N > 03 and timenow3N < 12: timezone = "A"
elif timenow3N > 11 and timenow3N < 20: timezone = "B"
elif timenow3N > 19 or timenow3N < 04: timezone = "C"
else: timezone = ""
#if admin: print printfirst + datenowS + space + daynowS + space + timenow2S + space + "timezone: " + timezone
'''---------------------------'''
if (daynowS == "Sat" and timenow2N < 2000) or (daynowS == "Fri" and timenow2N > 1900): yomshabat = "true"
else: yomshabat = "false"