

import os, sys
from pysqlite2 import dbapi2 as sqlite
from gamedatabase import *
import util
from elementtree.ElementTree import *
from config import ImagePlacing


class ConfigxmlUpdater:
	
	def createConfig(self, gdb, dbVersion):
		
		path = util.getConfigXmlPath()
		
		#backup config.xml
		newFileName = path +'.backup ' +dbVersion
		
		if not os.path.isfile(newFileName):
			try:
				os.rename(str(path), str(newFileName))
			except Exception, (exc):
				return -1, "Error: Cannot backup config.xml: " +str(exc)
			
		root = Element('config')			
		romCollections = SubElement(root, 'RomCollections')
		fileTypes = SubElement(root, 'FileTypes')
		imagePlacing = SubElement(root, 'ImagePlacing')
		scrapers = SubElement(root, 'Scrapers')
		
		gdb.cursor.execute("SELECT * FROM RomCollection")
		romCollectionRows = gdb.cursor.fetchall()
		for romCollectionRow in romCollectionRows:			
			romCollection = SubElement(romCollections, 'RomCollection', {'id' : str(romCollectionRow[0]), 'name' : str(romCollectionRow[1])})
			SubElement(romCollection, 'emulatorCmd').text = str(romCollectionRow[3])
			SubElement(romCollection, 'emulatorParams').text = 'please move your params here'
			
			romPathRows = gdb.cursor.execute("SELECT * FROM Path Where romCollectionId = ? and fileTypeId = \
				(Select id from FileType Where name = 'rcb_rom')", (romCollectionRow[0],))
			for romPathRow in romPathRows:
				SubElement(romCollection, 'romPath').text = str(romPathRow[1])
			
			mediaPathRows = gdb.cursor.execute("SELECT Path.name, FileType.name FROM Path, FileType \
				Where (romCollectionId = ? and fileTypeId NOT IN \
				(Select id from FileType Where (name = 'rcb_rom' OR name = 'rcb_description'))) \
				AND filetype.id = path.filetypeid", (romCollectionRow[0],))			
			for mediaPathRow in mediaPathRows:								
				SubElement(romCollection, 'mediaPath', {'type' : str(mediaPathRow[1])}).text = str(mediaPathRow[0])
				
			descParserFile = romCollectionRow[6]
			descSource = ''
			descSources = gdb.cursor.execute("SELECT * FROM Path Where romCollectionId = ? and fileTypeId = \
				(Select id from FileType Where name = 'rcb_description')", (romCollectionRow[0],))
			if(descSources != None):				
				descSourceRow = descSources.fetchone()
				if(descSourceRow != None):
					descSource = descSourceRow[1]
			
			if((descParserFile != None and descParserFile != '') and (descSource != None and descSource != '')):
				site = SubElement(scrapers, 'Site', {'name' : romCollectionRow[1]})
				SubElement(site, 'Scraper', {'parseInstruction' : descParserFile, 'source' : descSource})
				SubElement(romCollection, 'scraper', {'name' : romCollectionRow[1]})
			else:
				SubElement(romCollection, 'scraper', {'name' : 'thevideogamedb.com'})
				SubElement(romCollection, 'scraper', {'name' : 'thegamesdb.net'})
				SubElement(romCollection, 'scraper', {'name' : 'giantbomb.com'})
				SubElement(romCollection, 'scraper', {'name' : 'mobygames.com'})
																										
			SubElement(romCollection, 'imagePlacing').text = 'default'
			
			SubElement(romCollection, 'descFilePerGame').text = str(romCollectionRow[9])
			SubElement(romCollection, 'diskPrefix').text = str(romCollectionRow[10])
			SubElement(romCollection, 'allowUpdate').text = str(romCollectionRow[12])
			SubElement(romCollection, 'ignoreOnScan').text = str(romCollectionRow[13])
			SubElement(romCollection, 'searchGameByCRC').text = str(romCollectionRow[14])
			SubElement(romCollection, 'searchGameByCRCIgnoreRomName').text = str(romCollectionRow[15])
			SubElement(romCollection, 'ignoreGameWithoutDesc').text = str(romCollectionRow[16])
			SubElement(romCollection, 'xboxCreateShortcut').text = str(romCollectionRow[17])
			SubElement(romCollection, 'xboxCreateShortcutAddRomfile').text = str(romCollectionRow[18])
			SubElement(romCollection, 'xboxCreateShortcutUseShortGamename').text = str(romCollectionRow[19])
			SubElement(romCollection, 'useFoldernameAsCRC').text = str(romCollectionRow[20])
			SubElement(romCollection, 'useFilenameAsCRC').text = str(romCollectionRow[21])
			SubElement(romCollection, 'maxFolderDepth').text = str(romCollectionRow[22])
				
		fileTypeRows = gdb.cursor.execute("SELECT * FROM FileType where name not in ('rcb_rom', 'rcb_manual', 'rcb_description', 'rcb_configuration')")
		for fileTypeRow in fileTypeRows:				
			fileType = SubElement(fileTypes, 'FileType' , {'id' : str(fileTypeRow[0]), 'name' : str(fileTypeRow[1])})
			SubElement(fileType, 'type').text = str(fileTypeRow[2])
			SubElement(fileType, 'parent').text = str(fileTypeRow[3])							
									
		self.createFileTypeForElements(gdb, imagePlacing)			
		self.createOnlineScrapers(scrapers)
		
		#write file		
		try:
			util.indentXml(root)
			tree = ElementTree(root)			
			tree.write(path)
			
			return 2, ""
			
		except Exception, (exc):
			print("Error: Cannot write config.xml: " +str(exc))
			return -1, "Error: Cannot write config.xml: " +str(exc)
		
	
	def createFileTypeForElements(self, gdb, imagePlacing):
		
		#use fileTypeForControl from first RomCollection as default
		romCollectionRows = gdb.cursor.execute("SELECT * FROM RomCollection")
		romCollectionRow = romCollectionRows.fetchone()
		
		fileTypeFor = SubElement(imagePlacing, 'fileTypeFor', {'name' : 'default'})
		fileTypeForRows = gdb.cursor.execute("SELECT FileTypeForControl.control, FileType.name FROM FileTypeForControl, FileType \
				Where romCollectionId = ? AND filetype.id = FileTypeForControl.filetypeid", (romCollectionRow[0], ))
		for fileTypeForRow in fileTypeForRows: 
			if(fileTypeForRow[0] == 'gamelist'):
				property = 'fileTypeForGameList'
			elif(fileTypeForRow[0] == 'gamelistselected'):
				property = 'fileTypeForGameListSelected'				
			elif(fileTypeForRow[0] == 'mainviewbackground'):
				property = 'fileTypeForMainViewBackground'
			elif(fileTypeForRow[0] == 'mainviewgameinfobig'):
				property = 'fileTypeForMainViewGameInfoBig'
			elif(fileTypeForRow[0] == 'mainviewgameinfoupperleft'):
				property = 'fileTypeForMainViewGameInfoUpperLeft'
			elif(fileTypeForRow[0] == 'mainviewgameinfoupperright'):
				property = 'fileTypeForMainViewGameInfoUpperRight'
			elif(fileTypeForRow[0] == 'mainviewgameinfolowerleft'):
				property = 'fileTypeForMainViewGameInfoLowerLeft'
			elif(fileTypeForRow[0] == 'mainviewgameinfolowerright'):
				property = 'fileTypeForMainViewGameInfoLowerRight'
			elif(fileTypeForRow[0] == 'mainviewvideowindowsmall'):
				property = 'fileTypeForMainViewVideoWindowSmall'
			elif(fileTypeForRow[0] == 'mainviewvideowindowbig'):
				property = 'fileTypeForMainViewVideoWindowBig'
			elif(fileTypeForRow[0] == 'mainviewvideofullscreen'):
				property = 'fileTypeForMainViewVideoFullscreen'				
			elif(fileTypeForRow[0] == 'mainview1'):
				property = 'fileTypeForMainView1'
			elif(fileTypeForRow[0] == 'mainview2'):
				property = 'fileTypeForMainView2'
			elif(fileTypeForRow[0] == 'mainview3'):
				property = 'fileTypeForMainView3'				
			elif(fileTypeForRow[0] == 'gameinfoviewbackground'):
				property = 'fileTypeForGameInfoViewBackground'
			elif(fileTypeForRow[0] == 'gameinfoviewgamelist'):
				property = 'fileTypeForGameInfoViewGamelist'
			elif(fileTypeForRow[0] == 'gameinfoview1'):
				property = 'fileTypeForGameInfoView1'
			elif(fileTypeForRow[0] == 'gameinfoview2'):
				property = 'fileTypeForGameInfoView2'
			elif(fileTypeForRow[0] == 'gameinfoview3'):
				property = 'fileTypeForGameInfoView3'
			elif(fileTypeForRow[0] == 'gameinfoview4'):
				property = 'fileTypeForGameInfoView4'
			elif(fileTypeForRow[0] == 'gameinfoviewvideowindow'):
				property = 'fileTypeForGameInfoViewVideoWindow'

			SubElement(fileTypeFor, property).text = str(fileTypeForRow[1])
	
	
	def createOnlineScrapers(self, scrapers):
		#local nfo
		site = SubElement(scrapers, 'Site', {'name' : 'local nfo'})
		SubElement(site, 'Scraper', {'parseInstruction' : '00 - local nfo.xml', 'source' : 'nfo'})
		
		#thevideogamedb.com
		site = SubElement(scrapers, 'Site', {'name' : 'thevideogamedb.com'})
		SubElement(site, 'Scraper', {'parseInstruction' : '01 - thevideogamedb.xml', 'source' : 'http://thevideogamedb.com/API/GameDetail.aspx?apikey=%VGDBAPIKey%&crc=%CRC%'})		
		
		site = SubElement(scrapers, 'Site', {'name' : 'thegamesdb.net'})
		SubElement(site, 'Scraper', {'parseInstruction' : '02 - thegamesdb.xml', 'source' : 'http://thegamesdb.net/api/GetGame.php?name=%GAME%'})
		
		#giantbomb.com
		site = SubElement(scrapers, 'Site', {'name' : 'giantbomb.com'})
		SubElement(site, 'Scraper', {'parseInstruction' : '03.01 - giantbomb - search.xml', 'source' : 'http://api.giantbomb.com/search/?api_key=%GIANTBOMBAPIKey%&query=%GAME%&resources=game&field_list=api_detail_url,name&format=xml',
									'returnUrl' : 'true', 'replaceKeyString' : '%REPLACEKEYS%', 'replaceValueString' : '%REPLACEVALUES%'})
		SubElement(site, 'Scraper', {'parseInstruction' : '03.02 - giantbomb - detail.xml', 'source' : '1'})		
		
		#mobygames.com
		site = SubElement(scrapers, 'Site', {'name' : 'mobygames.com'})
		SubElement(site, 'Scraper', {'parseInstruction' : '04.01 - mobygames - gamesearch.xml', 'source' : 'http://www.mobygames.com/search/quick?game=%GAME%&p=%PLATFORM%',
									'returnUrl' : 'true', 'replaceKeyString' : '%REPLACEKEYS%', 'replaceValueString' : '%REPLACEVALUES%'})
		SubElement(site, 'Scraper', {'parseInstruction' : '04.02 - mobygames - details.xml', 'source' : '1'})				
		SubElement(site, 'Scraper', {'parseInstruction' : '04.03 - mobygames - coverlink.xml', 'source' : '1', 'returnUrl' : 'true'})
		SubElement(site, 'Scraper', {'parseInstruction' : '04.04 - mobygames - coverart.xml', 'source' : '2'})
		SubElement(site, 'Scraper', {'parseInstruction' : '04.05 - mobygames - screenshotlink.xml', 'source' : '1', 'returnUrl' : 'true'})
		#use short name on xbox
		if (os.environ.get( "OS", "xbox" ) == "xbox"):
			SubElement(site, 'Scraper', {'parseInstruction' : '04.06 - mobygames - screenoriglink.xml', 'source' : '3', 'returnUrl' : 'true'})
		else:
			SubElement(site, 'Scraper', {'parseInstruction' : '04.06 - mobygames - screenshotoriginallink.xml', 'source' : '3', 'returnUrl' : 'true'})
		SubElement(site, 'Scraper', {'parseInstruction' : '04.07 - mobygames - screenshots.xml', 'source' : '4'})						
					