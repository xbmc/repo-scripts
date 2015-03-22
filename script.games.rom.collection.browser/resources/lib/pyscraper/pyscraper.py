
import config
from config import *
from gamedatabase import *
from descriptionparserfactory import *
import util
from util import *

import difflib

import xbmcgui


class PyScraper:
	
	def __init__(self):
		pass

	def scrapeResults(self, results, scraper, urlsFromPreviousScrapers, gamenameFromFile, foldername, filecrc, romFile, fuzzyFactor, updateOption, romCollection, settings):		
		Logutil.log("using parser file: " +scraper.parseInstruction, util.LOG_LEVEL_DEBUG)		
		Logutil.log("using game description: " +scraper.source, util.LOG_LEVEL_DEBUG)
		
		scraperSource = scraper.source
		
		#url to scrape may be passed from the previous scraper
		if(scraper.source.isdigit()):
			if(len(urlsFromPreviousScrapers) == 0):
				Logutil.log("Configuration error: scraper source is numeric and there is no previous scraper that returned an url to scrape.", util.LOG_LEVEL_ERROR)
				return results, urlsFromPreviousScrapers, True			
			if(len(urlsFromPreviousScrapers) < int(scraper.source)):
				Logutil.log("Configuration error: no url found at index " +str(scraper.source), util.LOG_LEVEL_ERROR)
				return results, urlsFromPreviousScrapers, True
			
			url = urlsFromPreviousScrapers[int(scraper.source) -1]
			Logutil.log("using url from previous scraper: " +str(url), util.LOG_LEVEL_INFO)
			
			if(scraper.sourceAppend != None and scraper.sourceAppend != ""):
				url = url + '/' +scraper.sourceAppend
				Logutil.log("sourceAppend = '%s'. New url = '%s'" %(scraper.sourceAppend, url), util.LOG_LEVEL_INFO)
			
			scraperSource = url
			
		if(scraper.source == 'nfo'):
			nfoFile = self.getNfoFile(settings, romCollection, gamenameFromFile, romFile)
			scraperSource = nfoFile
								
				
		tempResults = self.parseDescriptionFile(scraper, scraperSource, gamenameFromFile, foldername, filecrc)
		tempResults = self.getBestResults(tempResults, gamenameFromFile, fuzzyFactor, updateOption, scraperSource, romCollection)
		
		if(tempResults == None):
			#try again without (*) and [*]
			gamenameFromFile = re.sub('\s\(.*\)|\s\[.*\]|\(.*\)|\[.*\]', '', gamenameFromFile)
			tempResults = self.parseDescriptionFile(scraper, scraperSource, gamenameFromFile, foldername, filecrc)
			tempResults = self.getBestResults(tempResults, gamenameFromFile, fuzzyFactor, updateOption, scraperSource, romCollection)						
				
		if(tempResults == None):
			if(scraper.returnUrl):
				urlsFromPreviousScrapers.append('')
			return results, urlsFromPreviousScrapers, True
		
		if(scraper.returnUrl):
			try:								
				tempUrl = self.resolveParseResult(tempResults, 'url')
				urlsFromPreviousScrapers.append(tempUrl)
				Logutil.log("pass url to next scraper: " +str(tempUrl), util.LOG_LEVEL_INFO)
				return results, urlsFromPreviousScrapers, True
			except:
				Logutil.log("Should pass url to next scraper, but url is empty.", util.LOG_LEVEL_WARNING)
				return results, urlsFromPreviousScrapers, True
					
		if(tempResults != None):
			for resultKey in tempResults.keys():
				Logutil.log("resultKey: " +resultKey, util.LOG_LEVEL_INFO)
				resultValue = []
				resultValueOld = results.get(resultKey, [])
				resultValueNew = tempResults.get(resultKey, [])

				if(len(resultValueOld) == 0 and (len(resultValueNew) != 0 and resultValueNew != [None,] and resultValueNew != None and resultValueNew != '')):
					results[resultKey] = resultValueNew
					resultValue = resultValueNew
				else:
					resultValue = resultValueOld
				Logutil.log("resultValue: " +str(resultValue), util.LOG_LEVEL_INFO)
			del tempResults
					
		return results, urlsFromPreviousScrapers, False
	
	
	def getNfoFile(self, settings, romCollection, gamenameFromFile, romFile):
		Logutil.log("getNfoFile", util.LOG_LEVEL_INFO)
		nfoFile = ''
		nfoFolder = settings.getSetting(util.SETTING_RCB_NFOFOLDER)
		splittedname = os.path.splitext(os.path.basename(romFile))
		filename = ''
		if(len(splittedname) == 1):
			filename = splittedname[0]
		elif(len(splittedname) == 2):
			filename = splittedname[1]
			
		if(nfoFolder != '' and nfoFolder != None):
			nfoFolder = os.path.join(nfoFolder, romCollection.name)
			nfoFile = os.path.join(nfoFolder, gamenameFromFile +'.nfo')
			
			#check for exact rom name (no friendly name)	
			if (not os.path.isfile(nfoFile)):
				nfoFile = os.path.join(nfoFolder, filename +'.nfo')
				
		if (not os.path.isfile(nfoFile)):
			romDir = os.path.dirname(romFile)
			Logutil.log('Romdir: ' +str(romDir), util.LOG_LEVEL_INFO)
			nfoFile = os.path.join(romDir, gamenameFromFile +'.nfo')
			
			#check for exact rom name (no friendly name)	
			if (not os.path.isfile(nfoFile)):
				nfoFile = os.path.join(romDir, filename +'.nfo')
			
		Logutil.log('Using nfoFile: ' +str(nfoFile), util.LOG_LEVEL_INFO)
		return nfoFile
	
	
	def parseDescriptionFile(self, scraper, scraperSource, gamenameFromFile, foldername, crc):
		Logutil.log("parseDescriptionFile", util.LOG_LEVEL_INFO)
			
		scraperSource = self.prepareScraperSource(scraper, scraperSource, gamenameFromFile, foldername, crc)
		if(scraperSource == ""):
			return None
			
		try:
			parser = DescriptionParserFactory.getParser(str(scraper.parseInstruction))
			results = parser.parseDescription(scraperSource, scraper.encoding)
			del parser
		except Exception, (exc):
			Logutil.log("an error occured while parsing game description: " +scraperSource, util.LOG_LEVEL_WARNING)
			Logutil.log("Parser complains about: " +str(exc), util.LOG_LEVEL_WARNING)
			return None
				
		return results
	
	
	def prepareScraperSource(self, scraper, scraperSourceOrig, romFilename, foldername, crc):
		#replace configurable tokens
		replaceKeys = scraper.replaceKeyString.split(',')
		Logutil.log("replaceKeys: " +str(replaceKeys), util.LOG_LEVEL_DEBUG)						
		replaceValues = scraper.replaceValueString.split(',')
		Logutil.log("replaceValues: " +str(replaceValues), util.LOG_LEVEL_DEBUG)
		
		if(len(replaceKeys) != len(replaceValues)):
			Logutil.log("Configuration error: replaceKeyString (%s) and replaceValueString(%s) does not have the same number of ','-separated items." %(scraper.replaceKeyString, scraper.replaceValueString), util.LOG_LEVEL_ERROR)
			return None
		
		for i in range(0, len(replaceKeys)):
			scraperSource = scraperSourceOrig.replace(replaceKeys[i], replaceValues[i])
			#also replace in gamename for later result matching
			gamenameFromFile = romFilename.replace(replaceKeys[i], replaceValues[i])
			
		if(scraperSource.startswith('http://')):
			gamenameToParse = urllib.quote(gamenameFromFile, safe='')
		else:
			gamenameToParse = gamenameFromFile					
			
		scraperSource = scraperSource.replace("%GAME%", gamenameToParse)
		
		replaceTokens = ['%FILENAME%', '%FOLDERNAME%', '%CRC%']
		for key in util.API_KEYS.keys():
			replaceTokens.append(key)
			
		replaceValues = [gamenameFromFile, foldername, crc]
		for value in util.API_KEYS.values():
			replaceValues.append(value)
			
		for i in range(0, len(replaceTokens)):
			scraperSource = scraperSource.replace(replaceTokens[i], replaceValues[i])
		
		if(not scraperSource.startswith('http://') and not os.path.exists(scraperSource)):
			#try again with original rom filename
			scraperSource = scraperSourceOrig.replace("%GAME%", romFilename)
			if not os.path.exists(scraperSource):				
				Logutil.log("description file for game " +gamenameFromFile +" could not be found. "\
						"Check if this path exists: " +scraperSource, util.LOG_LEVEL_WARNING)			
				return ""
		
		Logutil.log("description file (tokens replaced): " +scraperSource, util.LOG_LEVEL_INFO)
		Logutil.log("Encoding: %s" % scraper.encoding, util.LOG_LEVEL_WARNING)
		return scraperSource
	
	
	def getBestResults(self, results, gamenameFromFile, fuzzyFactor, updateOption, scraperSource, romCollection):
		Logutil.log("getBestResults", util.LOG_LEVEL_INFO)
		
		digits = ['10', '9', '8', '7', '6', '5', '4', '3', '2', '1']
		romes = ['X', 'IX', 'VIII', 'VII', 'VI', 'V', 'IV', 'III', 'II', 'I']
		
		if (results != None and len(results) >= 1):
			Logutil.log('Searching for game: ' +gamenameFromFile, util.LOG_LEVEL_INFO)
			Logutil.log('%s results found. Try to find best match.' %str(len(results)), util.LOG_LEVEL_INFO)						
			
			result, highestRatio = self.matchGamename(results, gamenameFromFile, digits, romes, False, scraperSource, romCollection)
			bestMatchingGame = self.resolveParseResult(result, 'SearchKey')
			
			if(highestRatio != 1.0):
				
				#stop searching in accurate mode
				if(updateOption == util.SCRAPING_OPTION_AUTO_ACCURATE):
					Logutil.log('Ratio != 1.0 and scraping option is set to "Accurate". Result will be skipped', LOG_LEVEL_WARNING)
					return None
			
				#Ask for correct result in Interactive mode
				if(updateOption == util.SCRAPING_OPTION_INTERACTIVE):
					options = []
					options.append('Skip Game')
					for resultEntry in results:
						options.append(self.resolveParseResult(resultEntry, 'SearchKey'))
						
					resultIndex = xbmcgui.Dialog().select('Search for: ' +gamenameFromFile, options)
					if(resultIndex == 0):
						Logutil.log('No result chosen by user', util.LOG_LEVEL_INFO)
						return None
					#-1 because of "Skip Game" entry
					resultIndex = resultIndex - 1
					selectedGame = self.resolveParseResult(results[resultIndex], 'Game')
					Logutil.log('Result chosen by user: ' +str(selectedGame), util.LOG_LEVEL_INFO)
					return results[resultIndex]
				
				#check seq no in guess names mode
				seqNoIsEqual = self.checkSequelNoIsEqual(gamenameFromFile, bestMatchingGame)
				if (not seqNoIsEqual):										
					highestRatio = 0.0
			
			if(highestRatio < fuzzyFactor):
				Logutil.log('No result found with a ratio better than %s. Try again with subtitle search.' %(str(fuzzyFactor),), LOG_LEVEL_WARNING)				
				result, highestRatio = self.matchGamename(results, gamenameFromFile, digits, romes, True, scraperSource, romCollection)
				#check for sequel numbers because it could be misinteroreted as subtitle
				bestMatchingGame = self.resolveParseResult(result, 'SearchKey')
				seqNoIsEqual = self.checkSequelNoIsEqual(gamenameFromFile, bestMatchingGame)
				if (not seqNoIsEqual):					
					return None
						
			if(highestRatio < fuzzyFactor):
				Logutil.log('No result found with a ratio better than %s. Result will be skipped.' %(str(fuzzyFactor),), LOG_LEVEL_WARNING)
				return None
			
			#get name of found result
			bestMatchingGame = self.resolveParseResult(result, 'SearchKey')						
									
			Logutil.log('Using result %s' %bestMatchingGame, util.LOG_LEVEL_INFO)
			return result
		else:
			Logutil.log('No results found with current scraper', util.LOG_LEVEL_INFO)
			return None


	def matchGamename(self, results, gamenameFromFile, digits, romes, checkSubtitle, scraperSource, romCollection):
		
		highestRatio = 0.0
		bestIndex = 0		
		
		for i in range(0, len(results)):
			result = results[i]
			try:
				#check if the result has the correct platform (if needed)
				platformSearchKey = self.resolveParseResult(result, 'PlatformSearchKey')
				if(platformSearchKey != ''):
					platform = config.getPlatformByRomCollection(scraperSource, romCollection.name)
					if(platform != platformSearchKey):
						Logutil.log('Platform mismatch. %s != %s. Result will be skipped.' %(platform, platformSearchKey), util.LOG_LEVEL_INFO)
						continue
				
				searchKey = self.resolveParseResult(result, 'SearchKey')
				#keep it for later reference
				origSearchKey = searchKey
				gamenameToCheck = gamenameFromFile
				
				#searchKey is specified in parserConfig - if no one is specified first result is valid (1 file per game scenario)
				if(searchKey == ''):
					Logutil.log('No searchKey found. Using first result', util.LOG_LEVEL_INFO)
					return result, 1.0
				
				Logutil.log('Comparing %s with %s' %(gamenameToCheck, searchKey), util.LOG_LEVEL_INFO)
				if(self.compareNames(gamenameToCheck, searchKey, checkSubtitle)):
					#perfect match
					return result, 1.0
						
				#try again with normalized names		
				gamenameToCheck = self.normalizeName(gamenameToCheck)
				searchKey = self.normalizeName(searchKey)
				Logutil.log('Try normalized names. Comparing %s with %s' %(gamenameToCheck, searchKey), util.LOG_LEVEL_INFO)
				if(self.compareNames(gamenameToCheck, searchKey, checkSubtitle)):
					#perfect match
					return result, 1.0
							
				#try again with replaced sequel numbers		
				sequelGamename = gamenameToCheck
				sequelSearchKey = searchKey
				for j in range(0, len(digits)):
					sequelGamename = sequelGamename.replace(digits[j], romes[j])
					sequelSearchKey = sequelSearchKey.replace(digits[j], romes[j])
				
				Logutil.log('Try with replaced sequel numbers. Comparing %s with %s' %(sequelGamename, sequelSearchKey), util.LOG_LEVEL_INFO)
				if(self.compareNames(sequelGamename, sequelSearchKey, checkSubtitle)):
					#perfect match
					return result, 1.0
				
				#remove last char for sequel number 1 from gamename
				if(gamenameFromFile.endswith(' 1') or gamenameFromFile.endswith(' I')):
					gamenameRemovedSequel = sequelGamename[:len(sequelGamename)-1]
					Logutil.log('Try with removed sequel numbers. Comparing %s with %s' %(gamenameRemovedSequel, sequelSearchKey), util.LOG_LEVEL_INFO)
					if(self.compareNames(gamenameRemovedSequel, sequelSearchKey, checkSubtitle)):
						#perfect match											
						return result, 1.0
				
				#remove last char for sequel number 1 from result (check with gamenameFromFile because we need the ' ' again)
				if(origSearchKey.endswith(' 1') or origSearchKey.endswith(' I')):
					searchKeyRemovedSequels = sequelSearchKey[:len(sequelSearchKey)-1]
					Logutil.log('Try with removed sequel numbers. Comparing %s with %s' %(sequelGamename, searchKeyRemovedSequels), util.LOG_LEVEL_INFO)
					if(self.compareNames(sequelGamename, searchKeyRemovedSequels, checkSubtitle)):
						#perfect match											
						return result, 1.0
				
				
				ratio = difflib.SequenceMatcher(None, sequelGamename.upper(), sequelSearchKey.upper()).ratio()
				Logutil.log('No result found. Try to find game by ratio. Comparing %s with %s, ratio: %s' %(sequelGamename, sequelSearchKey, str(ratio)), util.LOG_LEVEL_INFO)						
				
				if(ratio > highestRatio):
					highestRatio = ratio
					bestIndex = i
					
			except Exception, (exc):
				Logutil.log("An error occured while matching the best result: " +str(exc), util.LOG_LEVEL_WARNING)
		
		return results[bestIndex], highestRatio


	def compareNames(self, gamename, searchkey, checkSubtitle):
		if(checkSubtitle):
			if(searchkey.find(gamename) > -1):
				Logutil.log('%s is a subtitle of %s. Using result %s' %(gamename, searchkey, searchkey), util.LOG_LEVEL_INFO)
				return True
		else:
			if(gamename == searchkey):
				Logutil.log('Perfect match. Using result %s' %searchkey, util.LOG_LEVEL_INFO)
				return True
		
		return False
		
		
	def normalizeName(self, name):

		removeChars = [', A', 'THE', ' ', '&', '-', '_', ':', '!', "'", '"', '.', ',', '#'] 		
		
		name = name.upper()
		
		for char in removeChars:
			name = name.replace(char, '')
		
		return name
		
		
	def checkSequelNoIsEqual(self, gamenameFromFile, searchKey):
		
		Logutil.log('Check sequel numbers for "%s" and "%s".' %(gamenameFromFile, searchKey), util.LOG_LEVEL_INFO)				
		
		#first check equality of last number (also works for year sequels like Fifa 98)
		numbers = re.findall(r"\d+", gamenameFromFile)
		if(len(numbers) > 0):
			numberGamename = numbers[len(numbers)-1]
		else:
			numberGamename = '1'
		
		numbers = re.findall(r"\d+", searchKey)
		if(len(numbers) > 0):
			numberSearchkey = numbers[len(numbers)-1]
		else:
			numberSearchkey = '2'
		
		if(numberGamename == numberSearchkey):
			return True
		
		digits = [' 10', ' 9', ' 8', ' 7', ' 6', ' 5', ' 4', ' 3', ' 2', ' 1']
		romes = [' X', ' IX', ' VIII', ' VII', ' VI', ' V', ' IV', ' III', ' II', ' I']
		
		indexGamename = self.getSequelNoIndex(gamenameFromFile, digits, romes)		
		indexSearchKey = self.getSequelNoIndex(searchKey, digits, romes)		
			
		if(indexGamename == -1 and indexSearchKey == -1):
			Logutil.log('"%s" and "%s" both don\'t contain a sequel number. Skip checking sequel number match.' %(gamenameFromFile, searchKey), util.LOG_LEVEL_INFO)
			return True
		
		if((indexGamename == -1 or indexSearchKey == -1) and (indexGamename == 9 or indexSearchKey == 9)):
			Logutil.log('"%s" and "%s" seem to be sequel number 1. Skip checking sequel number match.' %(gamenameFromFile, searchKey), util.LOG_LEVEL_INFO)
			return True
		
		if(indexGamename != indexSearchKey):
			Logutil.log('Sequel number index for "%s" : "%s"' %(gamenameFromFile, str(indexGamename)), util.LOG_LEVEL_INFO)
			Logutil.log('Sequel number index for "%s" : "%s"' %(searchKey, str(indexSearchKey)), util.LOG_LEVEL_INFO)
			Logutil.log('Sequel numbers don\'t match. Result will be skipped.', util.LOG_LEVEL_INFO)
			return False
		
		return True
		
		
		
	def getSequelNoIndex(self, gamename, digits, romes):		
		indexGamename = -1
		
		for i in range(0, len(digits)):	
			if(gamename.find(digits[i]) != -1):
				indexGamename = i
				break
			if(gamename.find(romes[i]) != -1):
				indexGamename = i
				break
				
		return indexGamename
		
				
	#TODO merge with method from dbupdate.py
	def resolveParseResult(self, result, itemName):
		
		resultValue = ""
		
		try:			
			resultValue = result[itemName][0]
			resultValue = util.html_unescape(resultValue)
			resultValue = resultValue.strip()
			resultValue = resultValue
									
		except Exception, (exc):
			Logutil.log("Error while resolving item: " +itemName +" : " +str(exc), util.LOG_LEVEL_WARNING)
						
		try:
			Logutil.log("Result " +itemName +" = " +resultValue, util.LOG_LEVEL_DEBUG)
		except:
			pass
				
		return resultValue
