import xbmc
import os, sys, re
import dbupdate
from gamedatabase import *
import util
from util import *


"""
import time
import zipfile
import xbmcgui
"""

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
		
		

def buildLikeStatement(selectedCharacter, searchTerm):
	Logutil.log("helper.buildLikeStatement", util.LOG_LEVEL_INFO)
	
	likeStatement = ''
	
	if (selectedCharacter == 'All'):
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
		