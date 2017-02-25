# -*- coding: utf-8 -*-
import urllib
import urllib2
import socket
import xbmc
import xbmcaddon
import xbmcvfs
import re
from StringIO import StringIO
import gzip
temp = xbmc.translatePath(xbmcaddon.Addon().getAddonInfo('profile')+'temp').decode('utf-8')
dict = xbmc.translatePath(xbmcaddon.Addon().getAddonInfo('profile')+'dict.py').decode('utf-8')


def log(msg):
	xbmc.log(msg)

def getTranslation(id):
	return xbmcaddon.Addon(id='script.module.libMediathek2').getLocalizedString(id)
	
def getUrl(url,headers=False):
	xbmc.log(url)
	req = urllib2.Request(url)
	if headers:
		for key in headers:
			req.add_header(key, headers[key])
	else:
		req.add_header('User-Agent', 'Mozilla/5.0 (Windows NT 6.1; rv:25.0) Gecko/20100101 Firefox/25.0')
		req.add_header('Accept-Encoding','gzip, deflate')
	response = urllib2.urlopen(req)
	compressed = response.info().get('Content-Encoding') == 'gzip'
	link = response.read()
	response.close()
	if compressed:
		buf = StringIO(link)
		f = gzip.GzipFile(fileobj=buf)
		link = f.read()
	return link
	

def clearString(s):
	s = s.replace("&lt;", "<").replace("&gt;", ">").replace("&amp;", "&").replace("&#034;", "\"").replace("&#039;", "'").replace("&quot;", "\"").replace("&szlig;", "ß").replace("&ndash;", "-")
	s = s.replace("&Auml;", "Ä").replace("&Uuml;", "Ü").replace("&Ouml;", "Ö").replace("&auml;", "ä").replace("&uuml;", "ü").replace("&ouml;", "ö").replace("&eacute;", "é").replace("&egrave;", "è")
	s = s.replace("&#x00c4;","Ä").replace("&#x00e4;","ä").replace("&#x00d6;","Ö").replace("&#x00f6;","ö").replace("&#x00dc;","Ü").replace("&#x00fc;","ü").replace("&#x00df;","ß")
	s = s.replace("&apos;","'").strip()
	return s
		
	
def f_open(path):
	f = xbmcvfs.File(path)
	result = f.read()
	f.close()
	return result

def f_write(path,data):
	print 'writing to '+path
	f = xbmcvfs.File(path, 'w')
	result = f.write(data)
	f.close()
	return True
	
def f_mkdir(path):
	return xbmcvfs.mkdir(path)