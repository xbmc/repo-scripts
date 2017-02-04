# -*- coding: utf-8 -*-
import mediathekxmlservicelisting as listing
import mediathekxmlserviceplay as play
import urllib

params = {}

def getNew(baseUrl,modePrefix):
	return listing.getXML(baseUrl+'/xmlservice/web/aktuellste?maxLength=50&id=%5FSTARTSEITE',modePrefix)
def getMostViewed(baseUrl,modePrefix):
	return listing.getXML(baseUrl+'/xmlservice/web/meistGesehen?maxLength=50&id=%5FGLOBAL',modePrefix)
def getRubrics(baseUrl):
	return listing.getXML(baseUrl+'/xmlservice/web/rubriken')
def getTopics(baseUrl):
	return listing.getXML(baseUrl+'/xmlservice/web/themen')
def getAZ(baseUrl,letter):
	list = listing.getXML(baseUrl+'/xmlservice/web/sendungenAbisZ?characterRangeEnd='+letter+'&detailLevel=2&characterRangeStart='+letter)
	if letter.lower() == "d":
		l = []
		for dict in list:
			name = dict["name"].lower()
			if name.startswith("der ") or name.startswith("die ") or name.startswith("das "):
				if name[4] == 'd':
					l.append(dict)
			else:
				l.append(dict)
		list = l
	return list
def getSearch(baseUrl,search_string):
	return listing.getXML(baseUrl+'/xmlservice/web/detailsSuche?maxLength=50&types=Video&properties=HD%2CUntertitel%2CRSS&searchString='+urllib.quote_plus(search_string))
	
def getXML(url,modePrefix=False,type=False):
	return listing.getXML(url,modePrefix,type)

def getVideoUrl(url):
	return play.getVideoUrl(url)
	