# -*- coding: iso-8859-15 -*-

import os, sys, re
import codecs

from pyparsing import *
from string import lowercase

from xml.dom.minidom import parseString, Node, Document

#Add support for unicode chars in commaseparated lists
_mynoncomma = "".join( [ c for c in printables + alphas8bit if c != "," ] )
_mycommasepitem = Combine(OneOrMore(Word(_mynoncomma) +
				  Optional( Word(" \t") +
				  ~Literal(",") + ~LineEnd() ) ) ).streamline().setName("mycommaItem")
mycommaSeparatedList = delimitedList( Optional( quotedString | _mycommasepitem, default="") ).setName("mycommaSeparatedList")


class DescriptionParser:
	
	def parseDescription(self, descFile, descParseInstruction, gamename):
		
		#configFile = os.path.join(databaseDir, 'parserConfig.xml')
		fh=open(descParseInstruction,"r")
		xmlDoc = fh.read()
		fh.close()
		
		xmlDoc = parseString(xmlDoc)
		
		gameGrammar = xmlDoc.getElementsByTagName('GameGrammar')
		if(gameGrammar == None):
			return "";
			
		grammarNode = gameGrammar[0]
		attributes = grammarNode.attributes
		
		attrNode = attributes.get('type')
		if(attrNode == None):
			return "";
			
		parserType = attrNode.nodeValue
		if(parserType == 'multiline'):
			results = self.parseMultiline(descFile, grammarNode, gamename)
			
		return results
		
		
	def getGameGrammar(self, descParseInstruction, gamename):
		
		#configFile = os.path.join(databaseDir, 'parserConfig.xml')
		fh=open(descParseInstruction,"r")
		xmlDoc = fh.read()
		fh.close()
		
		xmlDoc = parseString(xmlDoc)
		
		gameGrammar = xmlDoc.getElementsByTagName('GameGrammar')
		if(gameGrammar == None):
			return "";
			
		grammarNode = gameGrammar[0]
		attributes = grammarNode.attributes
		attrNode = attributes.get('type')
		if(attrNode == None):
			return "";
			
		parserType = attrNode.nodeValue
		if(parserType == 'multiline'):
			results = self.buildGameGrammar(grammarNode, gamename)
			
		return results
		
		
	def parseMultiline(self, descFile, grammarNode, gamename):
		
		grammar = self.buildGameGrammar(grammarNode, gamename)
				
		gameGrammar = Group(grammar)		
		
		all = OneOrMore(gameGrammar)		
		fh = open(str(descFile), 'r')
		fileAsString = fh.read()		
		fileAsString = fileAsString.decode('iso-8859-15')
		
		results = all.parseString(fileAsString)
		
		return results		
		
		
	def buildGameGrammar(self, grammarNode, gamename):
		
		grammarList = []
		rolGrammar = SkipTo(LineEnd()) +Suppress(LineEnd())
	
		appendNextNode = False
		appendToPreviousNode = False
		lastNodeGrammar = Empty()
		
		for node in grammarNode.childNodes:
			if (node.nodeType != Node.ELEMENT_NODE):
				continue
			#appendToPreviousNode was set at the end of the last loop
			if(appendToPreviousNode):				
				nodeGrammar = lastNodeGrammar
			else:					
				nodeGrammar = Empty()
			
			lineEndReplaced = False
			
			literal = None
			if (node.hasChildNodes()):
				nodeValue = node.firstChild.nodeValue				
				literal = self.replaceTokens(nodeValue, ('LineStart', 'LineEnd'))
				if(nodeValue.find('LineEnd') >= 0):
					lineEndReplaced = True			
			rol = node.attributes.get('restOfLine')
			if(rol != None and rol.nodeValue == 'true'):
				isRol = True
				#appendNextNode is used in the current loop
				appendNextNode = False
			else:
				isRol = False
				appendNextNode = True						
				
			skipTo = node.attributes.get('skipTo')
			if(skipTo != None):
				skipToGrammar = self.replaceTokens(skipTo.nodeValue, ('LineStart', 'LineEnd'))
				if(nodeGrammar == None):
					nodeGrammar = SkipTo(skipToGrammar)
				else:
					nodeGrammar += SkipTo(skipToGrammar)
				if(skipTo.nodeValue.find('LineEnd') >= 0):
					#print "LineEnd found in: "  +skipTo.nodeValue
					lineEndReplaced = True

			if(node.nodeName == 'SkippableContent'):
				if(literal != None):	
					if(nodeGrammar == None):
						nodeGrammar = Suppress(literal)
					else:
						nodeGrammar += Suppress(literal)
						
			delimiter = node.attributes.get('delimiter')
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
					
			nodeGrammar = nodeGrammar.setResultsName(node.nodeName)
						
			if(appendNextNode == False or lineEndReplaced):
				optional = node.attributes.get('optional')
				if(optional != None and optional.nodeValue == 'true'):
					nodeGrammar = Optional(nodeGrammar)
				
				grammarList.append(nodeGrammar)	
				
			#check if we replaced a LineEnd in skipTo or nodeValue
			if(isRol == True or lineEndReplaced):
				appendToPreviousNode = False
				lastNodeGrammar = None
			else:
				appendToPreviousNode = True
				if(lastNodeGrammar == None):
					lastNodeGrammar = nodeGrammar
				else:
					lastNodeGrammar += nodeGrammar
					
		grammar = ParserElement()
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
