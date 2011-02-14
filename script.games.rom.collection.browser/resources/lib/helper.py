import xbmc
import os, sys, re
import dbupdate
from gamedatabase import *
import util
from util import *
import time
import zipfile
import xbmcgui


def getFilesByControl_Cached(gdb, fileTypes, gameId, publisherId, developerId, romCollectionId, fileDict):
					
		Logutil.log("getFilesByControl gameId: " +str(gameId), util.LOG_LEVEL_DEBUG)
		Logutil.log("getFilesByControl publisherId: " +str(publisherId), util.LOG_LEVEL_DEBUG)
		Logutil.log("getFilesByControl developerId: " +str(developerId), util.LOG_LEVEL_DEBUG)
		Logutil.log("getFilesByControl romCollectionId: " +str(romCollectionId), util.LOG_LEVEL_DEBUG)
		
		mediaFiles = []
		for fileType in fileTypes:
			Logutil.log("fileType: " +str(fileType), util.LOG_LEVEL_DEBUG)
			
			parentId = None
						
			if(fileType.parent == util.FILETYPEPARENT_GAME):
				parentId = gameId			
			elif(fileType.parent == util.FILETYPEPARENT_PUBLISHER):
				parentId = publisherId
			elif(fileType.parent == util.FILETYPEPARENT_DEVELOPER):
				parentId = developerId
			elif(fileType.parent == util.FILETYPEPARENT_ROMCOLLECTION):
				parentId = romCollectionId
				
			Logutil.log("parentId: " +str(parentId), util.LOG_LEVEL_DEBUG)
				
			if(parentId != None):
				key = '%i;%i' %(parentId, int(fileType.id))
				try:								
					files = fileDict[key]				
				except:
					files = None
			else:
				files = None
			
			if(files == None):
				Logutil.log("files == None in getFilesByControl", util.LOG_LEVEL_DEBUG)
				continue
				
			for file in files:
				mediaFiles.append(file[1])
		
		return mediaFiles



def launchEmu(gdb, gui, gameId, config, settings):
		Logutil.log("Begin helper.launchEmu", util.LOG_LEVEL_INFO)
		
		gameRow = Game(gdb).getObjectById(gameId)
		if(gameRow == None):
			Logutil.log("Game with id %s could not be found in database" %gameId, util.LOG_LEVEL_ERROR)
			return
			
		romCollection = None
		try:
			romCollection = config.romCollections[str(gameRow[util.GAME_romCollectionId])]
		except:
			Logutil.log('Cannot get rom collection with id: ' +str(gameRow[util.GAME_romCollectionId]), util.LOG_LEVEL_ERROR)
			
		gui.writeMsg("Launch Game " + gameRow[util.ROW_NAME])
		
		cmd = ""
		
		#get environment OS
		env = ( os.environ.get( "OS", "win32" ), "win32", )[ os.environ.get( "OS", "win32" ) == "xbox" ]	
				
		filenameRows = File(gdb).getRomsByGameId(gameRow[util.ROW_ID])		
		
		escapeCmd = settings.getSetting(util.SETTING_RCB_ESCAPECOMMAND).upper() == 'TRUE'
		cmd = buildCmd(filenameRows, romCollection, escapeCmd)
			
		if (settings.getSetting(util.SETTING_RCB_USEEMUSOLO).upper() == 'TRUE'):
			
			#try to create autoexec.py
			writeAutoexec(gdb)

			# Remember selection
			gui.saveViewState(False)
			
			#invoke batch file that kills xbmc before launching the emulator			
			if(env == "win32"):
				#There is a problem with quotes passed as argument to windows command shell. This only works with "call"
				cmd = 'call \"' +os.path.join(util.RCBHOME, 'applaunch.bat') +'\" ' +cmd						
			else:
				cmd = os.path.join(re.escape(util.RCBHOME), 'applaunch.sh ') +cmd
		else:
			#use call to support paths with whitespaces
			if(env == "win32" and not (os.environ.get( "OS", "xbox" ) == "xbox")):
				cmd = 'call ' +cmd
		
		#update LaunchCount
		launchCount = gameRow[util.GAME_launchCount]
		Game(gdb).update(('launchCount',), (launchCount +1,) , gameRow[util.ROW_ID])
		gdb.commit()
		
		Logutil.log("cmd: " +cmd, util.LOG_LEVEL_INFO)			
		
		try:
			if (os.environ.get( "OS", "xbox" ) == "xbox"):			
				launchXbox(gui, gdb, cmd, romCollection, filenameRows)
			else:
				launchNonXbox(cmd, settings)
						
		except Exception, (exc):
			Logutil.log("Error while launching emu: " +str(exc), util.LOG_LEVEL_ERROR)
			gui.writeMsg("Error while launching emu: " +str(exc))
			
		try:
			#delete temporary files (from zip or 7z extraction
			tempDir = getTempDir()
			files = os.listdir(tempDir)
			for file in files:
				os.remove(os.path.join(tempDir, file))
		except Exception, (exc):
			Logutil.log("Error deleting files after launch emu: " +str(exc), util.LOG_LEVEL_ERROR)
			gui.writeMsg("Error deleting files after launch emu: " +str(exc))
		
		Logutil.log("End helper.launchEmu", util.LOG_LEVEL_INFO)
		
		
def saveViewState(gdb, isOnExit, selectedView, selectedGameIndex, selectedConsoleIndex, selectedGenreIndex, selectedPublisherIndex, selectedYearIndex, selectedCharacterIndex,
	selectedControlIdMainView, selectedControlIdGameInfoView, settings):
		
		Logutil.log("Begin helper.saveViewState", util.LOG_LEVEL_INFO)				
		
		if(isOnExit):
			#saveViewStateOnExit
			saveViewState = settings.getSetting(util.SETTING_RCB_SAVEVIEWSTATEONEXIT).upper() == 'TRUE'
		else:
			#saveViewStateOnLaunchEmu
			saveViewState = settings.getSetting(util.SETTING_RCB_SAVEVIEWSTATEONLAUNCHEMU).upper() == 'TRUE'
			
		rcbSetting = getRCBSetting(gdb)
		if(rcbSetting == None):
			Logutil.log("rcbSetting == None in helper.saveViewState", util.LOG_LEVEL_WARNING)
			return
		
		if(saveViewState):
			RCBSetting(gdb).update(('lastSelectedView', 'lastSelectedConsoleIndex', 'lastSelectedGenreIndex', 'lastSelectedPublisherIndex', 'lastSelectedYearIndex', 'lastSelectedGameIndex', 'lastFocusedControlMainView', 'lastFocusedControlGameInfoView', 'lastSelectedCharacterIndex'),
				(selectedView, selectedConsoleIndex, selectedGenreIndex, selectedPublisherIndex, selectedYearIndex, selectedGameIndex, selectedControlIdMainView, selectedControlIdGameInfoView, selectedCharacterIndex), rcbSetting[0])
		else:
			RCBSetting(gdb).update(('lastSelectedView', 'lastSelectedConsoleIndex', 'lastSelectedGenreIndex', 'lastSelectedPublisherIndex', 'lastSelectedYearIndex', 'lastSelectedGameIndex', 'lastFocusedControlMainView', 'lastFocusedControlGameInfoView', 'lastSelectedCharacterIndex'),
				(None, None, None, None, None, None, None, None, None), rcbSetting[util.ROW_ID])
				
		gdb.commit()
		
		Logutil.log("End helper.saveViewState", util.LOG_LEVEL_INFO)


			
def getRCBSetting(gdb):
		rcbSettingRows = RCBSetting(gdb).getAll()
		if(rcbSettingRows == None or len(rcbSettingRows) != 1):
			#TODO raise error
			return None
						
		return rcbSettingRows[util.ROW_ID]
		
		

def buildLikeStatement(selectedCharacter):
	Logutil.log("helper.buildLikeStatement", util.LOG_LEVEL_INFO)
	
	if (selectedCharacter == 'All'):		
		return "0 = 0"
	elif (selectedCharacter == '0-9'):
		
		likeStatement = '('
		for i in range (0, 10):				
			likeStatement += "name LIKE '%s'" %(str(i) +'%')
			if(i != 9):
				likeStatement += ' or '
		
		likeStatement += ')'
				
		return likeStatement
	else:		
		return "name LIKE '%s'" %(selectedCharacter +'%')
	
	
##################

# HELPER METHODS #

##################
		

		
def buildCmd(filenameRows, romCollection, escapeCmd):
	
	fileindex = int(0)
	compressedExtensions = ['7z', 'zip']
	
	emuCommandLine = romCollection.emulatorCmd
	emuParams = romCollection.emulatorParams
	
	if type(emuParams).__name__ != 'str':
		emuParams = ''
	
	#params could be: {-%I% %ROM%}
	#we have to repeat the part inside the brackets and replace the %I% with the current index
	obIndex = emuParams.find('{')
	cbIndex = emuParams.find('}')			
	replString = ''
	if obIndex > -1 and cbIndex > 1:
		replString = emuParams[obIndex+1:cbIndex]
	emuParams = emuParams.replace("{", "")
	emuParams = emuParams.replace("}", "")
	
	for fileNameRow in filenameRows:
		fileName = fileNameRow[0]			
		rom = ""
		roms = []
		#we could have multiple rom Paths - search for the correct one
		for romPath in romCollection.romPaths:
			rom = os.path.join(romPath, fileName)
			if(os.path.isfile(rom)):
				break
		if(rom == ""):
			Logutil.log("no rom file found for game: " +str(fileName), util.LOG_LEVEL_ERROR)
			return ""

		# If it's a .7z file
		filext = rom.split('.')[-1]
		
		
		if filext in compressedExtensions and not romCollection.doNotExtractZipFiles:
			Logutil.log('Treating file as a compressed archive', util.LOG_LEVEL_INFO)
			compressed = True						
		
			names = getNames(filext, rom)
			
			chosenROM = -1
			
			#check if we should handle multiple roms
			if '%I%' in emuParams and romCollection.diskPrefix in str(names):
				Logutil.log("Loading %d archives" % len(names), util.LOG_LEVEL_INFO)
				archives = getArchives(filext, rom, names)
				for archive in archives:					
					newPath = os.path.join(getTempDir(), archive[0])
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
				return ""
		
			if chosenROM != -1:
				# Extract the chosen file to %TMP%
				newPath = os.path.join(getTempDir(), names[chosenROM])
				
				Logutil.log("Putting extracted file in %s" % newPath, util.LOG_LEVEL_INFO)
				
				data = getArchives(filext, rom, [names[chosenROM]])
				fo = open(str(newPath), 'wb')
				fo.write(data[0][1])
				fo.close()
				
				# Point file name to the newly extracted file and continue
				# as usual
				roms = [newPath]
		
		if len(roms) == 0:
			roms = [rom]
		
		del rom
		
		for rom in roms:
			if fileindex == 0:
				if (escapeCmd):
					emuParams = emuParams.replace('%ROM%', re.escape(rom))
					emuCommandLine = re.escape(emuCommandLine)
				else:					
					emuParams = emuParams.replace('%ROM%', rom)
				
				if (os.environ.get( "OS", "xbox" ) == "xbox"):
					cmd = emuCommandLine.replace('%ROM%', rom)
				else:
					cmd = '\"' +emuCommandLine +'\" ' +emuParams.replace('%I%', str(fileindex))
			else:
				newrepl = replString
				if (escapeCmd):
					newrepl = newrepl.replace('%ROM%', re.escape(rom))
					emuCommandLine = re.escape(emuCommandLine)					
				else:					
					newrepl = newrepl.replace('%ROM%', rom)
				newrepl = newrepl.replace('%I%', str(fileindex))
				cmd += ' ' +newrepl		
			fileindex += 1
	
	return cmd
	
	
def writeAutoexec(gdb):
	# Backup original autoexec.py		
	autoexec = util.getAutoexecPath()
	doBackup(gdb, autoexec)			

	# Write new autoexec.py
	try:
		fh = open(autoexec,'w') # truncate to 0
		fh.write("#Rom Collection Browser autoexec\n")
		fh.write("import xbmc\n")
		fh.write("xbmc.executescript('"+ os.path.join(util.RCBHOME, 'default.py')+"')\n")
		fh.close()
	except Exception, (exc):
		Logutil.log("Cannot write to autoexec.py: " +str(exc), util.LOG_LEVEL_ERROR)
		return
		
		
def doBackup(gdb, fName):
		Logutil.log("Begin helper.doBackup", util.LOG_LEVEL_INFO)
	
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
			
			rcbSetting = getRCBSetting(gdb)
			if (rcbSetting == None):
				Logutil.log("rcbSetting == None in doBackup", util.LOG_LEVEL_WARNING)
				return
			
			RCBSetting(gdb).update(('autoexecBackupPath',), (newFileName,), rcbSetting[util.ROW_ID])
			gdb.commit()
			
		Logutil.log("End helper.doBackup", util.LOG_LEVEL_INFO)
		

def launchXbox(gui, gdb, cmd, romCollection, filenameRows):
	Logutil.log("launchEmu on xbox", util.LOG_LEVEL_INFO)
	
	#on xbox emucmd must be the path to an executable or cut file
	if (not os.path.isfile(cmd)):
		Logutil.log("Error while launching emu: File %s does not exist!" %cmd, util.LOG_LEVEL_ERROR)
		gui.writeMsg("Error while launching emu: File %s does not exist!" %cmd)
		return
					
	if (romCollection.xboxCreateShortcut):
		Logutil.log("creating cut file", util.LOG_LEVEL_INFO)
		
		cutFile = createXboxCutFile(cmd, filenameRows, romCollection)
		if(cutFile == ""):
			Logutil.log("Error while creating .cut file. Check xbmc.log for details.", util.LOG_LEVEL_ERROR)
			gui.writeMsg("Error while creating .cut file. Check xbmc.log for details.")
			return
			
		cmd = cutFile
		Logutil.log("cut file created: " +cmd, util.LOG_LEVEL_INFO)			
	
	#RunXbe always terminates XBMC. So we have to saveviewstate and write autoexec here	
	writeAutoexec(gdb)
	# Remember selection	
	gui.saveViewState(False)
		
	Logutil.log("RunXbe", util.LOG_LEVEL_INFO)
	xbmc.executebuiltin("XBMC.Runxbe(%s)" %cmd)
	Logutil.log("RunXbe done", util.LOG_LEVEL_INFO)
	time.sleep(1000)
		

def createXboxCutFile(emuCommandLine, filenameRows, romCollection):
	Logutil.log("Begin helper.createXboxCutFile", util.LOG_LEVEL_INFO)		
		
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
	
	Logutil.log("End helper.createXboxCutFile", util.LOG_LEVEL_INFO)
	return cutFile
	

def getRomfilenameForXboxCutfile(filenameRows, romCollection):
	
	if(len(filenameRows) != 1):
		Logutil.log("More than one file available for current game. Xbox version only supports one file per game atm.", util.LOG_LEVEL_ERROR)
		return ""
	
	filenameRow = filenameRows[0]
	if(filenameRow == None):
		Logutil.log("filenameRow == None in helper.createXboxCutFile", util.LOG_LEVEL_ERROR)
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
	
	
def launchNonXbox(cmd, settings):
	Logutil.log("launchEmu on non-xbox", util.LOG_LEVEL_INFO)							
				
	toggledScreenMode = False
	
	if (settings.getSetting(util.SETTING_RCB_USEEMUSOLO).upper() == 'FALSE'):
		screenMode = xbmc.executehttpapi("GetSystemInfoByName(system.screenmode)").replace("<li>","")
		Logutil.log("screenMode: " +screenMode, util.LOG_LEVEL_INFO)
		isFullScreen = screenMode.endswith("Full Screen")
		
		if(isFullScreen):
			Logutil.log("Toggle to Windowed mode", util.LOG_LEVEL_INFO)
			#this minimizes xbmc some apps seems to need it
			xbmc.executehttpapi("Action(199)")
			toggledScreenMode = True
		
	Logutil.log("launch emu", util.LOG_LEVEL_INFO)
	os.system(cmd.encode(sys.getfilesystemencoding()))
	Logutil.log("launch emu done", util.LOG_LEVEL_INFO)		
	
	if(toggledScreenMode):
		Logutil.log("Toggle to Full Screen mode", util.LOG_LEVEL_INFO)
		#this brings xbmc back
		xbmc.executehttpapi("Action(199)")
	
	
# Compressed files functions

def getNames(type, filepath):
	return {'zip' : getNamesZip,
			'7z'  : getNames7z}[type](filepath)


def getNames7z(filepath):
	
	try:
		import py7zlib
	except:
		xbmcgui.Dialog().ok(util.SCRIPTNAME, 'Error launching .7z file.', 'Please check XBMC.log for details.')
		Logutil.log("You have tried to launch a .7z file but you are missing required libraries to extract the file. You can download the latest RCB version from RCBs project page. It contains all required libraries.", util.LOG_LEVEL_ERROR)
		return
	
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
		xbmcgui.Dialog().ok(util.SCRIPTNAME, 'Error launching .7z file.', 'Please check XBMC.log for details.')
		Logutil.log("You have tried to launch a .7z file but you are missing required libraries to extract the file. You can download the latest RCB version from RCBs project page. It contains all required libraries.", util.LOG_LEVEL_ERROR)
		return
	
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


def getTempDir():
	tempDir = os.path.join(util.getAddonDataPath(), 'tmp')
	
	try:
		#check if folder exists
		if(not os.path.isdir(tempDir)):
			os.mkdir(tempDir)
		return tempDir
	except Exception, (exc):
		Logutil.log('Error creating temp dir: ' +str(exc), util.LOG_LEVEL_ERROR)
		return None
		