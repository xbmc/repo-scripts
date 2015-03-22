import xbmc, xbmcgui
import os, sys, re
import dbupdate, util, helper
from gamedatabase import *
from util import *
import time, zipfile, glob, shutil


def launchEmu(gdb, gui, gameId, config, settings, listitem):
	Logutil.log("Begin launcher.launchEmu", util.LOG_LEVEL_INFO)
	
	gameRow = Game(gdb).getObjectById(gameId)
	if(gameRow == None):
		Logutil.log("Game with id %s could not be found in database" %gameId, util.LOG_LEVEL_ERROR)
		return
		
	romCollection = None
	try:
		romCollection = config.romCollections[str(gameRow[util.GAME_romCollectionId])]
	except:
		Logutil.log('Cannot get rom collection with id: ' +str(gameRow[util.GAME_romCollectionId]), util.LOG_LEVEL_ERROR)
		gui.writeMsg(util.localize(32034))
		return
			
	gui.writeMsg(util.localize(32163)+ " " +gameRow[util.ROW_NAME])
	
	# Remember viewstate
	gui.saveViewState(False)
	
	cmd = ""
	precmd = ""
	postcmd = ""
	
	#get environment OS
	env = util.getEnvironment()
			
	filenameRows = File(gdb).getRomsByGameId(gameRow[util.ROW_ID])
	Logutil.log("files for current game: " +str(filenameRows), util.LOG_LEVEL_INFO)
		
	escapeCmd = settings.getSetting(util.SETTING_RCB_ESCAPECOMMAND).upper() == 'TRUE'
	cmd, precmd, postcmd, roms = buildCmd(filenameRows, romCollection, gameRow, escapeCmd, False)
	
	if (not romCollection.useBuiltinEmulator):
		if(cmd == ''):
			Logutil.log('No cmd created. Game will not be launched.', util.LOG_LEVEL_INFO)
			return
		if(precmd.strip() == '' or precmd.strip() == 'call'):
			Logutil.log('No precmd created.', util.LOG_LEVEL_INFO)
			
		if(postcmd.strip() == '' or postcmd.strip() == 'call'):
			Logutil.log('No postcmd created.', util.LOG_LEVEL_INFO)
			
		#solo mode
		if (romCollection.useEmuSolo):
			
			copyLauncherScriptsToUserdata(settings)
			
			#check if we should use xbmc.service (Eden) or autoexec.py (Dharma)
			if(not gui.useRCBService):
				#try to create autoexec.py
				writeAutoexec(gdb)
			else:
				#communicate with service via settings
				settings.setSetting(util.SETTING_RCB_LAUNCHONSTARTUP, 'true')
			
			#invoke script file that kills xbmc before launching the emulator
			basePath = os.path.join(util.getAddonDataPath(), 'scriptfiles')
			#xbmc needs other script files than kodi
			xbmcFilenameSuffix = "_xbmc"
			if(int(gui.xbmcversionNo) >= util.XBMC_VERSION_HELIX):
				xbmcFilenameSuffix = ""
						
			if(env == "win32"):
				if(settings.getSetting(util.SETTING_RCB_USEVBINSOLOMODE).lower() == 'true'):
					#There is a problem with quotes passed as argument to windows command shell. This only works with "call"
					#use vb script to restart xbmc
					cmd = 'call \"' +os.path.join(basePath, 'applaunch-vbs%s.bat' %xbmcFilenameSuffix) +'\" ' +cmd
				else:					
					#There is a problem with quotes passed as argument to windows command shell. This only works with "call"
					cmd = 'call \"' +os.path.join(basePath, 'applaunch%s.bat' %xbmcFilenameSuffix) +'\" ' +cmd						
			else:
				cmd = os.path.join(basePath, 'applaunch%s.sh ' %xbmcFilenameSuffix) +cmd
		else:
			#use call to support paths with whitespaces
			if(env == "win32" and not (os.environ.get( "OS", "xbox" ) == "xbox")):
				cmd = 'call ' +cmd
	
	#update LaunchCount
	launchCount = gameRow[util.GAME_launchCount]
	Game(gdb).update(('launchCount',), (launchCount +1,) , gameRow[util.ROW_ID], True)
	gdb.commit()
	
	Logutil.log("cmd: " +cmd, util.LOG_LEVEL_INFO)	
	Logutil.log("precmd: " +precmd, util.LOG_LEVEL_INFO)
	Logutil.log("postcmd: " +postcmd, util.LOG_LEVEL_INFO)
	
	try:
		if (os.environ.get( "OS", "xbox" ) == "xbox"):			
			launchXbox(gui, gdb, cmd, romCollection, filenameRows)
		else:
			launchNonXbox(cmd, romCollection, gameRow, settings, precmd, postcmd, roms, gui, listitem)
	
		gui.writeMsg("")
					
	except Exception, (exc):
		Logutil.log("Error while launching emu: " +str(exc), util.LOG_LEVEL_ERROR)
		gui.writeMsg(util.localize(32035) +": " +str(exc))
	
	Logutil.log("End launcher.launchEmu", util.LOG_LEVEL_INFO)
		


##################

# HELPER METHODS #

##################
		
		
def buildCmd(filenameRows, romCollection, gameRow, escapeCmd, calledFromSkin):		
	Logutil.log('launcher.buildCmd', util.LOG_LEVEL_INFO)
		
	compressedExtensions = ['7z', 'zip']
	
	cmd = ""
	precmd = ""
	postcmd = ""
	
	emuCommandLine = romCollection.emulatorCmd
	Logutil.log('emuCommandLine: ' +emuCommandLine, util.LOG_LEVEL_INFO)
	Logutil.log('preCmdLine: ' +romCollection.preCmd, util.LOG_LEVEL_INFO)
	Logutil.log('postCmdLine: ' +romCollection.postCmd, util.LOG_LEVEL_INFO)

	#handle savestates	
	stateFile = checkGameHasSaveStates(romCollection, gameRow, filenameRows, escapeCmd)
		
	if(stateFile == ''):
		emuParams = romCollection.emulatorParams
	else:		
		emuParams = romCollection.saveStateParams
		if(escapeCmd):
			stateFile = re.escape(stateFile)
		emuParams = emuParams.replace('%statefile%', stateFile)
		emuParams = emuParams.replace('%STATEFILE%', stateFile)
		emuParams = emuParams.replace('%Statefile%', stateFile)
	
	#params could be: {-%I% %ROM%}
	#we have to repeat the part inside the brackets and replace the %I% with the current index
	emuParams, partToRepeat = prepareMultiRomCommand(emuParams)

	#ask for disc number if multidisc game
	diskName = ""
	if(romCollection.diskPrefix != '' and not '%I%' in emuParams):
		Logutil.log("Getting Multiple Disc Parameter", util.LOG_LEVEL_INFO)
		options = []
		for disk in filenameRows:
			gamename = os.path.basename(disk[0])
			match = re.search(romCollection.diskPrefix.lower(), str(gamename).lower())
			if(match):
				disk = gamename[match.start():match.end()]
				options.append(disk)
		if(len(options) > 1 and not calledFromSkin):
			diskNum = xbmcgui.Dialog().select(util.localize(32164) +': ', options)
			if(diskNum < 0):
				#don't launch game
				Logutil.log("No disc was chosen. Won't launch game", util.LOG_LEVEL_INFO)
				return "", "", "", None
			else:
				diskName = options[diskNum]
				Logutil.log('Chosen Disc: %s' % diskName, util.LOG_LEVEL_INFO)

	#insert game specific command
	gameCmd = ''
	if(gameRow[util.GAME_gameCmd] != None):
		gameCmd = str(gameRow[util.GAME_gameCmd])
	#be case insensitive with (?i)
	emuParams = re.sub('(?i)%gamecmd%', gameCmd, emuParams)
	
	Logutil.log('emuParams: ' +emuParams, util.LOG_LEVEL_INFO)
	
	fileindex = int(0)
	for fileNameRow in filenameRows:
		rom = fileNameRow[0]
		Logutil.log('rom: ' +str(rom), util.LOG_LEVEL_INFO)
		
		if romCollection.makeLocalCopy:
			localDir = os.path.join(util.getTempDir(), romCollection.name)
			if os.path.exists(localDir):
				Logutil.log("Trying to delete local rom files", util.LOG_LEVEL_INFO)    
				files = os.listdir(localDir)
				for file in files:
					os.remove(os.path.join(localDir, file))
			localRom = os.path.join(localDir, os.path.basename(str(rom)))
			Logutil.log('Creating local copy: ' + str(localRom), util.LOG_LEVEL_INFO)
			if xbmcvfs.copy(rom, localRom):
				Logutil.log('Local copy created', util.LOG_LEVEL_INFO)
			rom = localRom

		# If it's a .7z file
		# Don't extract zip files in case of savestate handling and when called From skin
		filext = rom.split('.')[-1]
		roms = [rom]
		if filext in compressedExtensions and not romCollection.doNotExtractZipFiles and stateFile == '' and not calledFromSkin:
			roms = handleCompressedFile(filext, rom, romCollection, emuParams)
			print "roms compressed = " +str(roms)
			if len(roms) == 0:
				return "", "", "", None
			
		#no use for complete cmd as we just need the game name
		if (romCollection.useBuiltinEmulator):
			print "roms = " +str(roms)
			return "", "", "", roms
		
		del rom
				
		for rom in roms:
			precmd = ""
			postcmd = ""
			if fileindex == 0:
				emuParams = replacePlaceholdersInParams(emuParams, rom, romCollection, gameRow, escapeCmd)
				if (escapeCmd):
					emuCommandLine = re.escape(emuCommandLine)				
				
				if (os.environ.get( "OS", "xbox" ) == "xbox"):
					cmd = replacePlaceholdersInParams(emuCommandLine, rom, romCollection, gameRow, escapeCmd)
				elif (romCollection.name == 'Linux' or romCollection.name == 'Macintosh' or romCollection.name == 'Windows'):
					cmd = replacePlaceholdersInParams(emuCommandLine, rom, romCollection, gameRow, escapeCmd)
				else:
					cmd = '\"' +emuCommandLine +'\" ' +emuParams.replace('%I%', str(fileindex))
			else:
				newrepl = partToRepeat
				newrepl = replacePlaceholdersInParams(newrepl, rom, romCollection, gameRow, escapeCmd)
				if (escapeCmd):
					emuCommandLine = re.escape(emuCommandLine)

				newrepl = newrepl.replace('%I%', str(fileindex))
				cmd += ' ' +newrepl
				
			cmdprefix = ''
			env = ( os.environ.get( "OS", "win32" ), "win32", )[ os.environ.get( "OS", "win32" ) == "xbox" ]
			if(env == "win32"):
				cmdprefix = 'call '
				
			precmd = cmdprefix + replacePlaceholdersInParams(romCollection.preCmd, rom, romCollection, gameRow, escapeCmd)
			postcmd = cmdprefix + replacePlaceholdersInParams(romCollection.postCmd, rom, romCollection, gameRow, escapeCmd)
						
			fileindex += 1

	#A disk was chosen by the user, select it here
	if (diskName):
		Logutil.log("Choosing Disk: " +str(diskName),util.LOG_LEVEL_INFO)
		match = re.search(romCollection.diskPrefix.lower(), cmd.lower())
		replString = cmd[match.start():match.end()]
		cmd = cmd.replace(replString, diskName)
		
			
	return cmd, precmd, postcmd, roms


def checkGameHasSaveStates(romCollection, gameRow, filenameRows, escapeCmd):
	
	if(romCollection.saveStatePath == ''):
		return ''
		
	rom = filenameRows[0][0]
	saveStatePath = replacePlaceholdersInParams(romCollection.saveStatePath, rom, romCollection, gameRow, escapeCmd)
		
	saveStateFiles = glob.glob(saveStatePath)
	
	stateFile = ''
	if(len(saveStateFiles) == 0):
		return ''
	elif(len(saveStateFiles) >= 1):
		Logutil.log('saveStateFiles found: ' +str(saveStateFiles), util.LOG_LEVEL_INFO)
		
		#don't select savestatefile if ASKNUM is requested in Params
		if(re.search('(?i)%ASKNUM%', romCollection.saveStateParams)):
			return saveStateFiles[0]
				
		options = [util.localize(32165)]
		for file in saveStateFiles:
			options.append(os.path.basename(file))
		selectedFile = xbmcgui.Dialog().select(util.localize(32166), options)
		#If selections is canceled or "Don't launch statefile" option
		if(selectedFile < 1):
			return ''
		else:
			stateFile = saveStateFiles[selectedFile -1]
	
	return stateFile


def prepareMultiRomCommand(emuParams):
	obIndex = emuParams.find('{')
	cbIndex = emuParams.find('}')			
	partToRepeat = ''
	if obIndex > -1 and cbIndex > 1:
		partToRepeat = emuParams[obIndex+1:cbIndex]
	emuParams = emuParams.replace("{", "")
	emuParams = emuParams.replace("}", "")
	
	return emuParams, partToRepeat


def handleCompressedFile(filext, rom, romCollection, emuParams):
	
	#Note: Trying to delete temporary files (from zip or 7z extraction) from last run
	#Do this before launching a new game. Otherwise game could be deleted before launch
	tempDir = os.path.join(util.getTempDir(), 'extracted')
	#check if folder exists
	if(not os.path.isdir(tempDir)):
		os.mkdir(tempDir)
	
	try:		
		if os.path.exists(tempDir):
			Logutil.log("Trying to delete temporary rom files", util.LOG_LEVEL_INFO)
			files = os.listdir(tempDir)
			for file in files:
				os.remove(os.path.join(tempDir, file))
	except Exception, (exc):
		Logutil.log("Error deleting files after launch emu: " +str(exc), util.LOG_LEVEL_ERROR)
		gui.writeMsg(util.localize(32036) +": " +str(exc))
		
	
	roms = []
	
	Logutil.log('Treating file as a compressed archive', util.LOG_LEVEL_INFO)
	compressed = True						

	try:
		names = getNames(filext, rom)
	except Exception, (exc):
		Logutil.log('Error handling compressed file: ' +str(exc), util.LOG_LEVEL_ERROR)
		return []
	
	if(names == None):
		Logutil.log('Error handling compressed file', util.LOG_LEVEL_ERROR)
		return []
	
	chosenROM = -1
	
	#check if we should handle multiple roms
	match = False
	if(romCollection.diskPrefix != ''):
		match = re.search(romCollection.diskPrefix.lower(), str(names).lower())
	
	if '%I%' in emuParams and match:
		Logutil.log("Loading %d archives" % len(names), util.LOG_LEVEL_INFO)
		
		try:
			archives = getArchives(filext, rom, names)
		except Exception, (exc):
			Logutil.log('Error handling compressed file: ' +str(exc), util.LOG_LEVEL_ERROR)
			return []		
		
		if(archives == None):
			Logutil.log('Error handling compressed file', util.LOG_LEVEL_WARNING)
			return []
		for archive in archives:					
			newPath = os.path.join(tempDir, archive[0])
			fp = open(newPath, 'wb')
			fp.write(archive[1])
			fp.close()
			roms.append(newPath)
		
	elif len(names) > 1:
		Logutil.log("The Archive has %d files" % len(names), util.LOG_LEVEL_INFO)
		chosenROM = xbmcgui.Dialog().select('Choose a ROM', names)
	elif len(names) == 1:
		Logutil.log("Archive only has one file inside; picking that one", util.LOG_LEVEL_INFO)
		chosenROM = 0
	else:
		Logutil.log("Archive had no files inside!", util.LOG_LEVEL_ERROR)
		return []

	if chosenROM != -1:
		# Extract all files to %TMP%
		archives = getArchives(filext, rom, names)
		if(archives == None):
			Logutil.log('Error handling compressed file', util.LOG_LEVEL_WARNING)
			return []
		for archive in archives:
			newPath = os.path.join(tempDir, archive[0])
			Logutil.log("Putting extracted file in %s" % newPath, util.LOG_LEVEL_INFO)			
			fo = open(str(newPath), 'wb')
			fo.write(archive[1])
			fo.close()
		
		# Point file name to the chosen file and continue as usual
		roms = [os.path.join(tempDir, names[chosenROM])]
		
	return roms


def replacePlaceholdersInParams(emuParams, rom, romCollection, gameRow, escapeCmd):
		
	if(escapeCmd):
		rom = re.escape(rom)
		
	#TODO: Wanted to do this with re.sub:
	#emuParams = re.sub(r'(?i)%rom%', rom, emuParams)
	#--> but this also replaces \r \n with linefeed and newline etc.
	
	#full rom path ("C:\Roms\rom.zip")	
	emuParams = emuParams.replace('%rom%', rom) 
	emuParams = emuParams.replace('%ROM%', rom)
	emuParams = emuParams.replace('%Rom%', rom)
	
	#romfile ("rom.zip")
	romfile = os.path.basename(rom)
	emuParams = emuParams.replace('%romfile%', romfile)
	emuParams = emuParams.replace('%ROMFILE%', romfile)
	emuParams = emuParams.replace('%Romfile%', romfile)
	
	#romname ("rom")
	romname = os.path.splitext(os.path.basename(rom))[0]
	emuParams = emuParams.replace('%romname%', romname)
	emuParams = emuParams.replace('%ROMNAME%', romname)
	emuParams = emuParams.replace('%Romname%', romname)
	
	#gamename	
	gamename = str(gameRow[util.ROW_NAME])
	emuParams = emuParams.replace('%game%', gamename)
	emuParams = emuParams.replace('%GAME%', gamename)
	emuParams = emuParams.replace('%Game%', gamename)
	
	#ask num
	if(re.search('(?i)%ASKNUM%', emuParams)):
		options = ['0', '1', '2', '3', '4', '5', '6', '7', '8', '9']
		number = str(xbmcgui.Dialog().select(util.localize(32167), options))
		emuParams = emuParams.replace('%asknum%', number)
		emuParams = emuParams.replace('%ASKNUM%', number)
		emuParams = emuParams.replace('%Asknum%', number)
		
	#ask text
	if(re.search('(?i)%ASKTEXT%', emuParams)):
		
		keyboard = xbmc.Keyboard()
		keyboard.setHeading(util.localize(32168))
		keyboard.doModal()
		command = ''
		if (keyboard.isConfirmed()):
			command = keyboard.getText()
		
		emuParams = emuParams.replace('%asktext%', command)
		emuParams = emuParams.replace('%ASKTEXT%', command)
		emuParams = emuParams.replace('%Asktext%', command)
		
	
	return emuParams


def copyLauncherScriptsToUserdata(settings):
	
	Logutil.log('copyLauncherScriptsToUserdata', util.LOG_LEVEL_INFO)
	
	oldBasePath = os.path.join(util.getAddonInstallPath(), 'resources', 'scriptfiles')
	newBasePath = os.path.join(util.getAddonDataPath(), 'scriptfiles')
	
	if(util.getEnvironment() == 'win32'):
		oldPath = os.path.join(oldBasePath, 'applaunch.bat')
		newPath = os.path.join(newBasePath, 'applaunch.bat')
	else:
		oldPath = os.path.join(oldBasePath, 'applaunch.sh')
		newPath = os.path.join(newBasePath, 'applaunch.sh')
		
	util.copyFile(oldPath, newPath)
	
	#copy VBS files
	if(util.getEnvironment() == 'win32' and settings.getSetting(util.SETTING_RCB_USEVBINSOLOMODE).lower() == 'true'):
		oldPath = os.path.join(oldBasePath, 'applaunch-vbs.bat')
		newPath = os.path.join(newBasePath, 'applaunch-vbs.bat')
		util.copyFile(oldPath, newPath)
		
		oldPath = os.path.join(oldBasePath, 'LaunchXBMC.vbs')
		newPath = os.path.join(newBasePath, 'LaunchXBMC.vbs')
		util.copyFile(oldPath, newPath)
		
		oldPath = os.path.join(oldBasePath, 'Sleep.vbs')
		newPath = os.path.join(newBasePath, 'Sleep.vbs')
		util.copyFile(oldPath, newPath)


def writeAutoexec(gdb):
	# Backup original autoexec.py		
	autoexec = util.getAutoexecPath()
	backupAutoexec(gdb, autoexec)

	# Write new autoexec.py
	try:
		path = os.path.join(util.RCBHOME, 'default.py')
		if(util.getEnvironment() == 'win32'):
			#HACK: There is an error with "\a" in autoexec.py on windows, so we need "\A"
			path = path.replace('\\addons', '\\Addons')
			
		fh = open(autoexec,'w') # truncate to 0
		fh.write("#Rom Collection Browser autoexec\n")
		fh.write("import xbmc\n")
		fh.write("xbmc.executescript('"+ path+"')\n")
		fh.close()
	except Exception, (exc):
		Logutil.log("Cannot write to autoexec.py: " +str(exc), util.LOG_LEVEL_ERROR)
		return
	
	
def backupAutoexec(gdb, fName):
	Logutil.log("Begin launcher.backupAutoexec", util.LOG_LEVEL_INFO)

	if os.path.isfile(fName):			
		newFileName = os.path.join(util.getAddonDataPath(), 'autoexec.py.bak') 			
		
		if os.path.isfile(newFileName):
			Logutil.log("Cannot backup autoexec.py: File exists.", util.LOG_LEVEL_ERROR)
			return
		
		try:
			os.rename(fName, newFileName)
		except Exception, (exc):
			Logutil.log("Cannot rename autoexec.py: " +str(exc), util.LOG_LEVEL_ERROR)
			return
		
		rcbSetting = helper.getRCBSetting(gdb)
		if (rcbSetting == None):
			Logutil.log("rcbSetting == None in backupAutoexec", util.LOG_LEVEL_WARNING)
			return
		
		RCBSetting(gdb).update(('autoexecBackupPath',), (newFileName,), rcbSetting[util.ROW_ID], True)
		gdb.commit()
		
	Logutil.log("End launcher.backupAutoexec", util.LOG_LEVEL_INFO)
		

def launchXbox(gui, gdb, cmd, romCollection, filenameRows):
	Logutil.log("launchEmu on xbox", util.LOG_LEVEL_INFO)
	
	#on xbox emucmd must be the path to an executable or cut file
	if (not os.path.isfile(cmd)):
		Logutil.log("Error while launching emu: File %s does not exist!" %cmd, util.LOG_LEVEL_ERROR)
		gui.writeMsg(util.localize(32037) %cmd)
		return
					
	if (romCollection.xboxCreateShortcut):
		Logutil.log("creating cut file", util.LOG_LEVEL_INFO)
		
		cutFile = createXboxCutFile(cmd, filenameRows, romCollection)
		if(cutFile == ""):
			Logutil.log("Error while creating .cut file. Check xbmc.log for details.", util.LOG_LEVEL_ERROR)
			gui.writeMsg(util.localize(32038))
			return
			
		cmd = cutFile
		Logutil.log("cut file created: " +cmd, util.LOG_LEVEL_INFO)			
	
	#RunXbe always terminates XBMC. So we have to write autoexec here	
	writeAutoexec(gdb)
		
	Logutil.log("RunXbe", util.LOG_LEVEL_INFO)
	xbmc.executebuiltin("XBMC.Runxbe(%s)" %cmd)
	Logutil.log("RunXbe done", util.LOG_LEVEL_INFO)
	time.sleep(1000)
		

def createXboxCutFile(emuCommandLine, filenameRows, romCollection):
	Logutil.log("Begin launcher.createXboxCutFile", util.LOG_LEVEL_INFO)		
		
	cutFile = os.path.join(util.getAddonDataPath(), 'temp.cut')

	# Write new temp.cut
	try:
		fh = open(cutFile,'w') # truncate to 0
		fh.write("<shortcut>\n")
		fh.write("<path>%s</path>\n" %emuCommandLine)
				
		if (romCollection.xboxCreateShortcutAddRomfile):	
			filename = getRomfilenameForXboxCutfile(filenameRows, romCollection)
			if(filename == ""):
				return ""			
			fh.write("<custom>\n")
			fh.write("<game>%s</game>\n" %filename)
			fh.write("</custom>\n")
			
		fh.write("</shortcut>\n")
		fh.write("\n")
		fh.close()
	except Exception, (exc):
		Logutil.log("Cannot write to temp.cut: " +str(exc), util.LOG_LEVEL_ERROR)
		return ""			
	
	Logutil.log("End launcher.createXboxCutFile", util.LOG_LEVEL_INFO)
	return cutFile
	

def getRomfilenameForXboxCutfile(filenameRows, romCollection):
	
	if(len(filenameRows) != 1):
		Logutil.log("More than one file available for current game. Xbox version only supports one file per game atm.", util.LOG_LEVEL_ERROR)
		return ""
	
	filenameRow = filenameRows[0]
	if(filenameRow == None):
		Logutil.log("filenameRow == None in launcher.createXboxCutFile", util.LOG_LEVEL_ERROR)
		return ""
		
	filename = filenameRow[0]
		
	if (not os.path.isfile(filename)):
		Logutil.log("Error while launching emu: File %s does not exist!" %filename, util.LOG_LEVEL_ERROR)		
		return ""	
	
	if (not romCollection.xboxCreateShortcutUseShortGamename):
		return filename
		
	basename = os.path.basename(filename)
	filename = os.path.splitext(basename)[0]
	return filename
	
	
def launchNonXbox(cmd, romCollection, gameRow, settings, precmd, postcmd, roms, gui, listitem):
	Logutil.log("launchEmu on non-xbox", util.LOG_LEVEL_INFO)							
				
	screenModeToggled = False
		
	encoding = 'utf-8'
	#HACK: sys.getfilesystemencoding() is not supported on all systems (e.g. Android)
	try:
		encoding = sys.getfilesystemencoding()
	except:
		pass
		 
	
	#use libretro core to play game
	if(romCollection.useBuiltinEmulator):
		Logutil.log("launching game with internal emulator", util.LOG_LEVEL_INFO)
		rom = roms[0]
		gameclient = romCollection.gameclient
		#HACK: use alternateGameCmd as gameclient
		if(gameRow[util.GAME_alternateGameCmd] != None and gameRow[util.GAME_alternateGameCmd] != ""):
			gameclient = str(gameRow[util.GAME_alternateGameCmd])
		Logutil.log("Preferred gameclient: " +gameclient, util.LOG_LEVEL_INFO)
		Logutil.log("Setting platform: " +romCollection.name, util.LOG_LEVEL_INFO)
		
		if(listitem == None):
			listitem = xbmcgui.ListItem(rom, "0", "", "")
		
		parameters = { "platform": romCollection.name }
		if(gameclient != ""):
			parameters["gameclient"] = gameclient
		listitem.setInfo( type="game", infoLabels=parameters)
		Logutil.log("launching rom: " +rom, util.LOG_LEVEL_INFO)		
		gui.player.play(rom, listitem)
		#xbmc.executebuiltin('PlayMedia(\"%s\", platform=%s, gameclient=%s)' %(rom, romCollection.name, romCollection.gameclient))
		return
	
	if (not romCollection.useEmuSolo):
		#screenMode = xbmc.executehttpapi("GetSystemInfoByName(system.screenmode)").replace("<li>","")
		screenMode = xbmc.getInfoLabel("System.Screenmode")
		Logutil.log("screenMode: " +screenMode, util.LOG_LEVEL_INFO)
		isFullScreen = screenMode.endswith("Full Screen")
		
		toggleScreenMode = settings.getSetting(util.SETTING_RCB_TOGGLESCREENMODE).upper() == 'TRUE'
		
		if(isFullScreen and toggleScreenMode):
			Logutil.log("Toggle to Windowed mode", util.LOG_LEVEL_INFO)
			#this minimizes xbmc some apps seems to need it
			try:
				xbmc.executehttpapi("Action(199)")
			except:
				xbmc.executeJSONRPC('{"jsonrpc":"2.0","method":"Input.ExecuteAction","params":{"action":"togglefullscreen"},"id":"1"}')
			
			screenModeToggled = True
		
	Logutil.log("launch emu", util.LOG_LEVEL_INFO)
	
	#pre launch command
	if(precmd.strip() != '' and precmd.strip() != 'call'):
		Logutil.log("Got to PRE", util.LOG_LEVEL_INFO)
		os.system(precmd.encode(encoding))
	
	preDelay = settings.getSetting(SETTING_RCB_PRELAUNCHDELAY)
	if(preDelay != ''):
		preDelay = int(float(preDelay))
		xbmc.sleep(preDelay)
	
	#change working directory
	path = os.path.dirname(romCollection.emulatorCmd)
	if(os.path.isdir(path)):
		try:
			os.chdir(path)
		except:
			pass
	
		
	#pause audio
	suspendAudio = settings.getSetting(util.SETTING_RCB_SUSPENDAUDIO).upper() == 'TRUE'
	if(suspendAudio):
		xbmc.executebuiltin("PlayerControl(Stop)")
		xbmc.enableNavSounds(False)
		xbmc.audioSuspend()
	
	if(romCollection.usePopen):
		import subprocess
		process = subprocess.Popen(cmd.encode(encoding), shell=True)
		process.wait()
	else:
		try:
			os.system(cmd.encode(encoding))
		except:
			os.system(cmd.encode('utf-8'))
	
	Logutil.log("launch emu done", util.LOG_LEVEL_INFO)		
	
	postDelay = settings.getSetting(SETTING_RCB_POSTLAUNCHDELAY)
	if(postDelay != ''):
		postDelay = int(float(postDelay))
		xbmc.sleep(postDelay)
	
	#resume audio
	if(suspendAudio):
		xbmc.audioResume()
		xbmc.enableNavSounds(True)
	
	#post launch command
	if(postcmd.strip() != '' and postcmd.strip() != 'call'):
		Logutil.log("Got to POST: " + postcmd.strip(), util.LOG_LEVEL_INFO)
		os.system(postcmd.encode(encoding))
	
	if(screenModeToggled):
		Logutil.log("Toggle to Full Screen mode", util.LOG_LEVEL_INFO)
		#this brings xbmc back
		try:
			xbmc.executehttpapi("Action(199)")
		except:
			xbmc.executeJSONRPC('{"jsonrpc":"2.0","method":"Input.ExecuteAction","params":{"action":"togglefullscreen"},"id":"1"}')

	
# Compressed files functions

def getNames(type, filepath):
	return {'zip' : getNamesZip,
			'7z'  : getNames7z}[type](filepath)


def getNames7z(filepath):
	
	try:
		import py7zlib
	except Exception, (exc):
		xbmcgui.Dialog().ok(util.SCRIPTNAME, util.localize(32039), util.localize(32129))
		Logutil.log("You have tried to launch a .7z file but you are missing required libraries to extract the file. You can download the latest RCB version from RCBs project page. It contains all required libraries.", util.LOG_LEVEL_ERROR)
		Logutil.log("Error: " +str(exc), util.LOG_LEVEL_ERROR)
		return None
	
	fp = open(str(filepath), 'rb')
	archive = py7zlib.Archive7z(fp)
	names = archive.getnames()
	fp.close()
	return names

	
def getNamesZip(filepath):
	fp = open(str(filepath), 'rb')
	archive =  zipfile.ZipFile(fp)
	names = archive.namelist()
	fp.close()
	return names

	
def getArchives(type, filepath, archiveList):
	return {'zip' : getArchivesZip,
			'7z'  : getArchives7z}[type](filepath, archiveList)
			
				
def getArchives7z(filepath, archiveList):
	
	try:
		import py7zlib
	except:
		xbmcgui.Dialog().ok(util.SCRIPTNAME, util.localize(32039), util.localize(32129))
		Logutil.log("You have tried to launch a .7z file but you are missing required libraries to extract the file. You can download the latest RCB version from RCBs project page. It contains all required libraries.", util.LOG_LEVEL_ERROR)
		return None
	
	fp = open(str(filepath), 'rb')
	archive = py7zlib.Archive7z(fp)
	archivesDecompressed =  [(name, archive.getmember(name).read())for name in archiveList]
	fp.close()
	return archivesDecompressed


def getArchivesZip(filepath, archiveList):
	fp = open(str(filepath), 'rb')
	archive = zipfile.ZipFile(fp)
	archivesDecompressed = [(name, archive.read(name)) for name in archiveList]
	fp.close()
	return archivesDecompressed