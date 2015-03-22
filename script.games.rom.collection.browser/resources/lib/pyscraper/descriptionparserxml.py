
from xml.etree.ElementTree import *
import urllib2
import time

import util
from util import Logutil

class DescriptionParserXml:
	
	def __init__(self, grammarNode):
		self.grammarNode = grammarNode
		
	
	def prepareScan(self, descFile, descParseInstruction):
		pass
	
	
	def parseDescription(self, descFile, encoding):
		Logutil.log('parseDescription: %s' % descFile, util.LOG_LEVEL_INFO)
		
		results = None
						
		if(descFile.startswith('http://')):
			req = urllib2.Request(descFile)
			req.add_unredirected_header('User-Agent', 'Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/537.31 (KHTML, like Gecko) Chrome/26.0.1410.64 Safari/537.31')
			descFile = urllib2.urlopen(req).read()
			del req
		else:
			fh = open(str(descFile), 'r')
			descFile = fh.read()
			del fh
				
		#load xmlDoc as elementtree to check with xpaths
		tree = fromstring(descFile)
		del descFile
		if(tree == None):
			return None				
						
		rootElementXPath = self.grammarNode.attrib.get('root')
		if(not rootElementXPath):
			rootElementXPath = "."
		rootElements = tree.findall(rootElementXPath)
		del tree, rootElementXPath
		if(rootElements == None):
			return None
		
		resultList = []
		
		for rootElement in rootElements:			
			tempResults = self.parseElement(rootElement)			
			if tempResults != None:				
				results = tempResults
				del tempResults
				results = self.replaceResultTokens(results)
				resultList.append(results)
		
		return resultList
	
	
	def scanDescription(self, descFile, descParseInstruction, encoding):
		
		Logutil.log('scanDescription: %s' % descFile, util.LOG_LEVEL_INFO)
		
		if(descFile.startswith('http://')):
			req = urllib2.Request(descFile)
			req.add_unredirected_header('User-Agent', 'Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/537.31 (KHTML, like Gecko) Chrome/26.0.1410.64 Safari/537.31')
			descFile = urllib2.urlopen(req).read()
			del req
		else:
			fh = open(str(descFile), 'r')
			descFile = fh.read()
			del fh
		
		#load xmlDoc as elementtree to check with xpaths
		tree = fromstring(descFile)
		del descFile
		
		#single result as dictionary
		result = {}
					
		rootElement = self.grammarNode.attrib.get('root')
				
		for node in tree.findall(rootElement):
			result = self.parseElement(node)
			result = self.replaceResultTokens(result)
			yield result
	
	
	#TODO: make a base class and make this a base method
	def replaceResultTokens(self, resultAsDict):
				
		for key in resultAsDict.keys():
			grammarElement = self.grammarNode.find(key)
			if(grammarElement != None):
				appendResultTo = grammarElement.attrib.get('appendResultTo')
				appendResultWith = grammarElement.attrib.get('appendResultWith')
				replaceKeyString = grammarElement.attrib.get('replaceInResultKey')
				replaceValueString = grammarElement.attrib.get('replaceInResultValue')
				dateFormat = grammarElement.attrib.get('dateFormat')
				del grammarElement
														
				#TODO: avoid multiple loops
				if(appendResultTo != None or appendResultWith != None or dateFormat != None):									
					itemList = resultAsDict[key]
					for i in range(0, len(itemList)):
						try:
							item = itemList[i]
							newValue = item
							del item
							if(appendResultTo != None):								
								newValue = appendResultTo +newValue
							if(appendResultWith != None):
								newValue = newValue + appendResultWith
							if(dateFormat != None):
								if(dateFormat == 'epoch'):
									try:
										newValue = time.gmtime(int(newValue))
									except:
										print 'error converting timestamp: ' +str(newValue) 
								else:
									newValue = time.strptime(newValue, dateFormat)
							itemList[i] = newValue
						except Exception, (exc):
							print "Error while handling appendResultTo: " +str(exc)
							
					resultAsDict[key] = itemList
					del itemList
					
				if(replaceKeyString != None and replaceValueString != None):												
					replaceKeys = replaceKeyString.split(',')
					replaceValues = replaceValueString.split(',')
					
					if(len(replaceKeys) != len(replaceValues)):
						print "Configuration error: replaceKeys must be the same number as replaceValues"
					
					itemList = resultAsDict[key]
					for i in range(0, len(itemList)):
						try:							
							item = itemList[i]
							
							for j in range(len(replaceKeys)):
								replaceKey = replaceKeys[j]
								replaceValue = replaceValues[j]
															
								newValue = item.replace(replaceKey, replaceValue)
								del item							
								itemList[i] = newValue
						except:
							print "Error while handling appendResultTo"
							
					resultAsDict[key] = itemList
					del itemList
		
		return resultAsDict			

			
	def parseElement(self, sourceTree):
		#single result as dictionary
		result = {}
		
		for parserNode in self.grammarNode:
					
			resultKey = parserNode.tag
			xpath = parserNode.text
			sourceRoot = sourceTree
				
			if(xpath == None):
				continue
			
			#check if xpath uses attributes for searching
			parts = xpath.split('[@')
			
			if(len(parts) == 2):
				xpathRest = str(parts[1])
				attribnameIndex = xpathRest.find('="')
				searchedattribname = xpathRest[0:attribnameIndex]
				searchedvalue = xpathRest[attribnameIndex +2: xpathRest.find('"', attribnameIndex +2)]
				
				resultValues = []
				sourceElements = sourceRoot.findall(parts[0])
				for sourceElement in sourceElements:
					attribute = sourceElement.attrib.get(searchedattribname)
					if(attribute != searchedvalue):
						continue
										
					if xpath.find(']/') != -1:
						parts = xpath.split(']/')
						attribute = sourceElement.attrib.get(parts[1])
						resultValues.append(attribute)
					else:
						resultValues.append(sourceElement.text)
			else:
				#check if xpath targets an attribute 
				parts = xpath.split('/@')
				if(len(parts) > 2):
					print("Usage error: wrong xpath! Only 1 attribute allowed")
					continue
				
				resultValues = []
				
				#check only the first part without attribute (elementtree does not support attributes as target)			
				elements = sourceRoot.findall(parts[0])
								
				for element in elements:
					#if search for attribute
					if(len(parts) > 1):
						attribute = element.attrib.get(parts[1])
						resultValues.append(attribute)
						#print "found attribute: " +attribute
					else:
						if(element.text != None):
							resultValues.append(element.text.encode('utf-8'))					
						#print "found result: " +element.text
			
			try:
				resultEntry = result[resultKey]
				resultEntry.append(resultValues)
				result[resultKey] = resultEntry
			except:
				result[resultKey] = resultValues
									
		return result
		
		
		