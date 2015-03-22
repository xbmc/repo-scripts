
from pyparsing import *
from xml.etree.ElementTree import *
import urllib2
import time
import util
from util import Logutil
#from xml.dom.minidom import parseString, Node, Document


#Add support for unicode chars in commaseparated lists
_mynoncomma = "".join( [ c for c in printables + alphas8bit if c != "," ] )
_mycommasepitem = Combine(OneOrMore(Word(_mynoncomma) +
				  Optional( Word(" \t") +
				  ~Literal(",") + ~LineEnd() ) ) ).streamline().setName("mycommaItem")
mycommaSeparatedList = delimitedList( Optional( quotedString | _mycommasepitem, default="") ).setName("mycommaSeparatedList")


class DescriptionParserFlatFile:
	
	def __init__(self, grammarNode):
		self.grammarNode = grammarNode
		
	
	def parseDescription(self, descFile, encoding):
		
		grammar = self.buildGameGrammar(self.grammarNode)
				
		gameGrammar = Group(grammar)
		del grammar		
		
		all = OneOrMore(gameGrammar)				
						
		fileAsString = self.openDescFile(descFile)
		
		fileAsString = fileAsString.decode(encoding).encode('utf-8')
		
		
		results = all.parseString(fileAsString)
		del all, fileAsString
		# Logutil.log('parseDescription Results!: %s' % results, util.LOG_LEVEL_INFO)	
		
		if(len(results) == 0 or results == Empty()):
			print "Parser Error: parseDescription returned 0 results. Check your parseInstruction"
			return None
						
		resultList = []
		for result in results:
			if (result != Empty() and result != None):
				resultAsDict = result.asDict()
				resultAsDict = self.replaceResultTokens(resultAsDict)
				resultList.append(resultAsDict)
		return resultList
			
	
	def scanDescription(self, descFile, descParseInstruction, encoding):
				
		fileAsString = self.openDescFile(descFile)
		
		fileAsString = fileAsString.decode(encoding).encode('utf-8')
		
		
		#Logutil.log('scanDescription: %s' % fileAsString, util.LOG_LEVEL_INFO)	
		
		self.gameGrammar = self.getGameGrammar(str(descParseInstruction))
				
		for result,start,end in self.gameGrammar.scanString(fileAsString):
			resultAsDict = result.asDict()
			resultAsDict = self.replaceResultTokens(resultAsDict)
			yield resultAsDict
			
			
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
							if(appendResultTo != None):								
								newValue = appendResultTo +newValue
							if(appendResultWith != None):
								newValue = newValue + appendResultWith
							if(dateFormat != None):
								newValue = time.strptime(newValue, dateFormat)
							itemList[i] = newValue
						except:
							print "Error while handling appendResultTo"
							
					resultAsDict[key] = itemList
					
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
								itemList[i] = newValue
						except:
							print "Error while handling appendResultTo"
							
					resultAsDict[key] = itemList
		
		return resultAsDict
			
	
	def openDescFile(self, descFile):
		
		fileAsString = ''
		
		if(descFile.startswith('http://')):
			req = urllib2.Request(descFile)
			req.add_unredirected_header('User-Agent', 'Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/537.31 (KHTML, like Gecko) Chrome/26.0.1410.64 Safari/537.31')
			fileAsString = urllib2.urlopen(req).read()
			del req
		else:
			fh = open(str(descFile), 'r')
			fileAsString = fh.read()
			del fh
			
		return fileAsString
	
	
	def getGameGrammar(self, descParseInstruction):				
		
		#load xmlDoc as elementtree to check with xpaths
		#tree = ElementTree().parse(descParseInstruction)
		fp = open(descParseInstruction, 'r')
		tree = fromstring(fp.read())
		fp.close()
		del fp
		
		grammarNode = tree.find('GameGrammar')
		if(grammarNode == None):
			return "";
					
		results = self.buildGameGrammar(grammarNode)
			
		return results
		
		
	def buildGameGrammar(self, grammarNode):
		
		grammarList = []
		rolGrammar = SkipTo(LineEnd()) +Suppress(LineEnd())
	
		#appendNextNode = False
		appendToPreviousNode = False
		lastNodeGrammar = Empty()
		
		for node in grammarNode:
			#appendToPreviousNode was set at the end of the last loop
			if(appendToPreviousNode):				
				nodeGrammar = lastNodeGrammar
			else:					
				nodeGrammar = Empty()
			
			lineEndReplaced = False
			
			literal = None
			nodeValue = node.text
			if(nodeValue != None):				
				literal = self.replaceTokens(nodeValue, ('LineStart', 'LineEnd'))
				if(nodeValue.find('LineEnd') >= 0):
					lineEndReplaced = True
					
			if(node.tag == 'SkippableContent'):
				if(literal != None):	
					if(nodeGrammar == None):
						nodeGrammar = Suppress(literal)
					else:
						nodeGrammar += Suppress(literal)		
			
			rol = node.attrib.get('restOfLine')
			if(rol != None and rol == 'true'):
				isRol = True
				#appendNextNode is used in the current loop
				#appendNextNode = False
			else:
				isRol = False
				#appendNextNode = True						
				
			skipTo = node.attrib.get('skipTo')
			if(skipTo != None):
				skipToGrammar = self.replaceTokens(skipTo, ('LineStart', 'LineEnd'))
				if(nodeGrammar == None):
					nodeGrammar = SkipTo(skipToGrammar)
				else:
					nodeGrammar += SkipTo(skipToGrammar)
				if(skipTo.find('LineEnd') >= 0):
					#print "LineEnd found in: "  +skipTo.nodeValue
					lineEndReplaced = True
						
			delimiter = node.attrib.get('delimiter')
			if(delimiter != None):
				if(nodeGrammar == None):
					nodeGrammar = (Optional(~LineEnd() +mycommaSeparatedList))				
				else:
					nodeGrammar += (Optional(~LineEnd() +mycommaSeparatedList))
			elif (isRol):
				if(nodeGrammar == None):
					nodeGrammar = rolGrammar
				else:
					nodeGrammar += rolGrammar
					
			nodeGrammar = nodeGrammar.setResultsName(node.tag)
						
			#if(appendNextNode == False or lineEndReplaced):
			optional = node.attrib.get('optional')
			if(optional != None and optional == 'true'):
				nodeGrammar = Optional(nodeGrammar)			
				
			
			closeStmnt = node.attrib.get('closeStmnt')
			if(closeStmnt != None and closeStmnt == 'true'):
				isRol = True									
			
			#check if we replaced a LineEnd in skipTo or nodeValue
			if(isRol == True or lineEndReplaced):
				appendToPreviousNode = False
				lastNodeGrammar = None
				grammarList.append(nodeGrammar)				
			else:
				appendToPreviousNode = True
				if(lastNodeGrammar == None):
					lastNodeGrammar = nodeGrammar
				else:
					lastNodeGrammar += nodeGrammar												
		
		grammar = ParserElement()
		if(len(grammarList)) == 0:
			return None
		
		for grammarItem in grammarList:			
			grammar += grammarItem
				
		return grammar		
		
		
	def replaceTokens(self, inputString, tokens):
		grammar = Empty()
		tokenFound = False
		tokenCount = 0
		# count the occurance of all tokens
		for token in tokens:
			tokenCount += inputString.count(token)			
			if(inputString.find(token) >= 0):				
				tokenFound = True
				
		#print "inputString: " +inputString
		#print "tokencount: " +str(tokenCount)
				
		if(not tokenFound):
			#print "inputString: " +inputString
			return Literal(inputString)
			
		#loop all found tokens
		for i in range(0, tokenCount):
			tokenIndex = -1
			nextToken = ''
			#search for the next matching token
			for token in tokens:
				#print "currentToken: " +token
				index = inputString.find(token)
				#print "index: " +str(index)
				#print "index: " +str(tokenIndex)
				if(index != -1 and (index <= tokenIndex or tokenIndex == -1)):
					tokenIndex = index
					nextToken = token
				else:
					#print "token not found"
					continue
					
			#print "nextToken: " +nextToken
			#print "currentIndex: " +str(tokenIndex)
			strsub = inputString[0:tokenIndex]
			if(strsub != ''):
				#print "adding Literal: " +strsub
				grammar += Literal(strsub)
			inputString = inputString.replace(nextToken, '', 1)
			
			#TODO only LineStart and LineEnd implemented
			if(nextToken == 'LineStart'):
				grammar += LineStart()
			elif(nextToken == 'LineEnd'):
				grammar += LineEnd()
			tokenIndex = -1
			
		return grammar