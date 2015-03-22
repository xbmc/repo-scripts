import xbmc, xbmcgui
import os, sys, re
import json


import dbupdate
from gamedatabase import *
import util
from util import *
import config


def cacheFiles(fileRows):
		
	Logutil.log("Begin cacheFiles" , util.LOG_LEVEL_DEBUG)
	
	fileDict = {}
	for fileRow in fileRows:
		key = '%i;%i' % (fileRow[util.FILE_parentId] , fileRow[util.FILE_fileTypeId])
		item = None
		try:
			item = fileDict[key]
		except:
			pass
		if(item == None):
			fileRowList = []
			fileRowList.append(fileRow)
			fileDict[key] = fileRowList
		else:				
			fileRowList = fileDict[key]
			fileRowList.append(fileRow)
			fileDict[key] = fileRowList
			
	Logutil.log("End cacheFiles" , util.LOG_LEVEL_DEBUG)
	return fileDict


def cacheYears(gdb):
	Logutil.log("Begin cacheYears" , util.LOG_LEVEL_DEBUG)
	yearRows = Year(gdb).getAll()
	if(yearRows == None):
		Logutil.log("yearRows == None in cacheYears", util.LOG_LEVEL_WARNING)
		return
	yearDict = {}
	for yearRow in yearRows:
		yearDict[yearRow[util.ROW_ID]] = yearRow
		
	Logutil.log("End cacheYears" , util.LOG_LEVEL_DEBUG)
	return yearDict
	
	
def cacheReviewers(gdb):
	Logutil.log("Begin cacheReviewers" , util.LOG_LEVEL_DEBUG)
	reviewerRows = Reviewer(gdb).getAll()
	if(reviewerRows == None):
		Logutil.log("reviewerRows == None in cacheReviewers", util.LOG_LEVEL_WARNING)
		return
	reviewerDict = {}
	for reviewerRow in reviewerRows:
		reviewerDict[reviewerRow[util.ROW_ID]] = reviewerRow
		
	Logutil.log("End cacheReviewers" , util.LOG_LEVEL_DEBUG)
	return reviewerDict
	

def cachePublishers(gdb):
	Logutil.log("Begin cachePublishers" , util.LOG_LEVEL_DEBUG)
	publisherRows = Publisher(gdb).getAll()
	if(publisherRows == None):
		Logutil.log("publisherRows == None in cachePublishers", util.LOG_LEVEL_WARNING)
		return
	publisherDict = {}
	for publisherRow in publisherRows:
		publisherDict[publisherRow[util.ROW_ID]] = publisherRow
		
	Logutil.log("End cachePublishers" , util.LOG_LEVEL_DEBUG)
	return publisherDict
	
	
def cacheDevelopers(gdb):
	Logutil.log("Begin cacheDevelopers" , util.LOG_LEVEL_DEBUG)
	developerRows = Developer(gdb).getAll()
	if(developerRows == None):
		Logutil.log("developerRows == None in cacheDevelopers", util.LOG_LEVEL_WARNING)
		return
	developerDict = {}
	for developerRow in developerRows:
		developerDict[developerRow[util.ROW_ID]] = developerRow
		
	Logutil.log("End cacheDevelopers" , util.LOG_LEVEL_DEBUG)
	return developerDict
	

def cacheGenres(gdb):
	
	Logutil.log("Begin cacheGenres" , util.LOG_LEVEL_DEBUG)
			
	genreGameRows = GenreGame(gdb).getAll()
	if(genreGameRows == None):
		Logutil.log("genreRows == None in cacheGenres", util.LOG_LEVEL_WARNING)
		return
	genreDict = {}
	for genreGameRow in genreGameRows:
		key = genreGameRow[util.GENREGAME_gameId]
		item = None
		try:
			item = genreDict[key]
			continue
		except:
			pass
			
		genreRows = Genre(gdb).getGenresByGameId(genreGameRow[util.GENREGAME_gameId])
		for i in range(0, len(genreRows)):
			if(i == 0):
				genres = genreRows[i][util.ROW_NAME]	
				genreDict[key] = genres
			else:				
				genres = genreDict[key]					
				genres = genres + ', ' + genreRows[i][util.ROW_NAME]					
				genreDict[key] = genres
			
	Logutil.log("End cacheGenres" , util.LOG_LEVEL_DEBUG)
	return genreDict


def saveReadString(property):
						
		try:
			result = str(property)
		except:
			result = ""
			
		return result


def getPropertyFromCache(dataRow, dict, key, index):
		
	result = ""
	try:
		itemRow = dict[dataRow[key]]
		result = itemRow[index]
	except:
		pass
		
	return result


def getFilesByControl_Cached(gdb, fileTypes, gameId, publisherId, developerId, romCollectionId, fileDict):
					
	Logutil.log("getFilesByControl gameId: " +str(gameId), util.LOG_LEVEL_DEBUG)
	Logutil.log("getFilesByControl publisherId: " +str(publisherId), util.LOG_LEVEL_DEBUG)
	Logutil.log("getFilesByControl developerId: " +str(developerId), util.LOG_LEVEL_DEBUG)
	Logutil.log("getFilesByControl romCollectionId: " +str(romCollectionId), util.LOG_LEVEL_DEBUG)
	
	mediaFiles = []
	for fileType in fileTypes:
		Logutil.log("fileType: " +str(fileType.name), util.LOG_LEVEL_DEBUG)
		
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
			(selectedView, selectedConsoleIndex, selectedGenreIndex, selectedPublisherIndex, selectedYearIndex, selectedGameIndex, selectedControlIdMainView, selectedControlIdGameInfoView, selectedCharacterIndex), rcbSetting[0], True)
	else:
		RCBSetting(gdb).update(('lastSelectedView', 'lastSelectedConsoleIndex', 'lastSelectedGenreIndex', 'lastSelectedPublisherIndex', 'lastSelectedYearIndex', 'lastSelectedGameIndex', 'lastFocusedControlMainView', 'lastFocusedControlGameInfoView', 'lastSelectedCharacterIndex'),
			(None, None, None, None, None, None, None, None, None), rcbSetting[util.ROW_ID], True)
			
	gdb.commit()
	
	Logutil.log("End helper.saveViewState", util.LOG_LEVEL_INFO)


			
def getRCBSetting(gdb):
	rcbSettingRows = RCBSetting(gdb).getAll()
	if(rcbSettingRows == None or len(rcbSettingRows) != 1):
		#TODO raise error
		return None
					
	return rcbSettingRows[util.ROW_ID]
		
		

def buildLikeStatement(selectedCharacter, searchTerm):
	Logutil.log("helper.buildLikeStatement", util.LOG_LEVEL_INFO)
	
	likeStatement = ''
	
	if (selectedCharacter == util.localize(32120)):
		likeStatement = "0 = 0"
	elif (selectedCharacter == '0-9'):
		
		likeStatement = '('
		for i in range (0, 10):				
			likeStatement += "name LIKE '%s'" %(str(i) +'%')
			if(i != 9):
				likeStatement += ' or '
		
		likeStatement += ')'
	else:		
		likeStatement = "name LIKE '%s'" %(selectedCharacter +'%')
	
	if(searchTerm != ''):
		likeStatement += " AND name LIKE '%s'" %('%' +searchTerm +'%')
	
	return likeStatement


def builMissingFilterStatement(config):

	if(config.showHideOption.lower() == util.localize(32157)):
		return ''
		
	statement = ''
	
	andStatementInfo = buildInfoStatement(config.missingFilterInfo.andGroup, ' AND ')
	if(andStatementInfo != ''):
		statement = andStatementInfo
		
	orStatementInfo =  buildInfoStatement(config.missingFilterInfo.orGroup, ' OR ')
	if(orStatementInfo != ''):
		if (statement != ''):
			statement = statement +' OR '
		statement = statement + orStatementInfo
		
	andStatementArtwork = buildArtworkStatement(config, config.missingFilterArtwork.andGroup, ' AND ')
	if(andStatementArtwork != ''):
		if (statement != ''):
			statement = statement +' OR '
		statement = statement + andStatementArtwork
	
	orStatementArtwork =  buildArtworkStatement(config, config.missingFilterArtwork.orGroup, ' OR ')
	if(orStatementArtwork != ''):
		if (statement != ''):
			statement = statement +' OR '
		statement = statement + orStatementArtwork
	
	if(statement != ''):
		statement = '(%s)' %(statement)
		if(config.showHideOption.lower() == util.localize(32161)):
			statement = 'NOT ' +statement
	
	return statement


def buildInfoStatement(group, operator):
	statement = ''
	for item in group:
		if statement == '':
			statement = '('
		else:
			statement = statement + operator
		statement = statement + config.gameproperties[item][1]
	if(statement != ''):
		statement = statement + ')'
	
	return statement


def buildArtworkStatement(config, group, operator):
	statement = ''
	for item in group:
		if statement == '':
			statement = '('
		else:
			statement = statement + operator
			
		typeId = ''
						
		fileTypeRows = config.tree.findall('FileTypes/FileType')
		for element in fileTypeRows:
			if(element.attrib.get('name') == item):
				typeId = element.attrib.get('id')
				break
		statement = statement + 'Id NOT IN (SELECT ParentId from File Where fileTypeId = %s)' %str(typeId) 
	
	if(statement != ''):
		statement = statement + ')'
	
	return statement



def getGamenameFromFilename(filename, romCollection):
					
	Logutil.log("current rom file: " + filename, util.LOG_LEVEL_INFO)

	#build friendly romname
	if(not romCollection.useFoldernameAsGamename):
		gamename = os.path.basename(filename)
	else:
		gamename = os.path.basename(os.path.dirname(filename))
		
	Logutil.log("gamename (file): " +gamename, util.LOG_LEVEL_INFO)
			
	#use regular expression to find disk prefix like '(Disk 1)' etc.		
	match = False
	if(romCollection.diskPrefix != ''):
		match = re.search(romCollection.diskPrefix.lower(), gamename.lower())
	
	if match:
		gamename = gamename[0:match.start()]
	else:
		gamename = os.path.splitext(gamename)[0]					
	
	gamename = gamename.strip()
	
	Logutil.log("gamename (friendly): " +gamename, util.LOG_LEVEL_INFO)		
	
	return gamename


def isRetroPlayerSupported():
	#HACK: if this json call fails, we are not in RetroPlayer branch
	addonsJson = xbmc.executeJSONRPC('{ "jsonrpc": "2.0", "id": 1, "method": "Addons.GetAddons", "params": { "type": "xbmc.gameclient"} }')
	jsonResult = json.loads(addonsJson)
	if (str(jsonResult.keys()).find('error') >= 0):
		Logutil.log("Error while reading gameclient addons via json. Assume that we are not in RetroPlayer branch.", util.LOG_LEVEL_WARNING)
		return False
	return True


def retroPlayerSupportsPythonIntegration():
	#HACK: if this fails, RetroPlayer branch does not support python integration
	addon = xbmcaddon.Addon(id=util.SCRIPTID)
	try:
		platforms = addon.getAddonInfo('platforms')
	except RuntimeError:
		Logutil.log("Error while reading platforms from addon. Assume that we are not in RetroPlayer branch.", util.LOG_LEVEL_WARNING)
		return False
	return True


def selectlibretrocore(platform):
		
	selectedCore = ''
	addons = ['None']
	
	success, installedAddons = readLibretroCores("all", True, platform)
	if(not success):
		return False, ""
	addons.extend(installedAddons)
	
	success, uninstalledAddons = readLibretroCores("uninstalled", False, platform)
	if(not success):
		return False, ""
	addons.extend(uninstalledAddons)
	
	dialog = xbmcgui.Dialog()
	index = dialog.select('Select libretro core', addons)
	print "index = " +str(index)
	if(index == -1):
		return False, ""
	elif(index == 0):
		print "return success"
		return True, ""
	else:
		selectedCore = addons[index]
		return True, selectedCore


def readLibretroCores(enabledParam, installedParam, platform):
	
	Logutil.log("readLibretroCores", util.LOG_LEVEL_INFO)
		
	addons = []
	addonsJson = xbmc.executeJSONRPC('{ "jsonrpc": "2.0", "id": 1, "method": "Addons.GetAddons", "params": { "type": "xbmc.gameclient", "enabled": "%s" } }' %enabledParam)
	jsonResult = json.loads(addonsJson)	
	if (str(jsonResult.keys()).find('error') >= 0):
		Logutil.log("Error while reading gameclient addons via json. Assume that we are not in RetroPlayer branch.", util.LOG_LEVEL_WARNING)
		return False, None
			
	try:
		for addonObj in jsonResult[u'result'][u'addons']:
			id = addonObj[u'addonid']
			addon = xbmcaddon.Addon(id, installed=installedParam)
			# extensions and platforms are "|" separated, extensions may or may not have a leading "."
			addonPlatformStr = addon.getAddonInfo('platforms')
			addonPlatforms = addonPlatformStr.split("|")
			for addonPlatform in addonPlatforms:
				if(addonPlatform == platform):
					addons.append(id)
	except KeyError:
		#no addons installed or found
		return True, addons
	Logutil.log("addons: %s" %str(addons), util.LOG_LEVEL_INFO)
	return True, addons
