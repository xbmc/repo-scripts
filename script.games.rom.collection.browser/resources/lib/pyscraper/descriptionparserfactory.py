# -*- coding: iso-8859-15 -*-


from xml.etree.ElementTree import *
from descriptionparserxml import *
from descriptionparserflatfile import *


class DescriptionParserFactory:

	@classmethod
	def getParser(self, descParseInstruction):
		
		fp = open(descParseInstruction, 'r')
		tree = fromstring(fp.read())
		fp.close()
		del fp
					
		grammarNode = tree.find('GameGrammar')
		del tree
		if(grammarNode == None):
			print "no valid parserConfig"
			return None
					
		attributes = grammarNode.attrib
		
		parserType = attributes.get('type')
		del attributes		
		if(parserType == 'multiline'):
			return DescriptionParserFlatFile(grammarNode)			
		elif(parserType == 'xml'):
			return DescriptionParserXml(grammarNode)
		else:
			print "Unknown parser: " +parserType
			return None
		
		
	
