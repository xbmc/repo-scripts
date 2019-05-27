# -*- coding: utf-8 -*-
import urllib
import urllib2
import socket
import xbmc
import xbmcplugin
import xbmcaddon
import xbmcvfs
import re
import sys
from StringIO import StringIO
import gzip
temp = xbmc.translatePath(xbmcaddon.Addon().getAddonInfo('profile')+'temp').decode('utf-8')
dict = xbmc.translatePath(xbmcaddon.Addon().getAddonInfo('profile')+'dict.py').decode('utf-8')

socket.setdefaulttimeout(30)

try:
    from urllib.request import Request, urlopen, build_opener, BaseHandler
except ImportError:
    from urllib2 import Request, urlopen, build_opener, BaseHandler


def log(msg):
	xbmc.log(msg)

def getTranslation(id,addonid='script.module.libmediathek3'):
	return xbmcaddon.Addon(id=addonid).getLocalizedString(id)
	
def getUrl(url,headers=False,post=False):
	log(url)
	return _request(url,headers,post)
	try:
		return _request(url,headers,post)
	except:#fast retry hack
		return _request(url,headers,post)
def _request(url,headers,post):
	log(url)
	if post:
		#log(urllib.urlencode(post))
		#log(urllib.quote(post))
		#log(post)
		#req = urllib2.Request(url,urllib.urlencode(post))
		#req = urllib2.Request(url,urllib.quote(post))
		req = urllib2.Request(url,post)
	else:
		req = urllib2.Request(url)
	if headers:
		for key in headers:
			req.add_header(key, headers[key])
		#req.add_header('Content-Type','application/json')
		req.has_header = lambda header_name: (True if header_name == 'Content-Length' else Request.has_header(req, header_name))
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
	#ISO-8859-1?!?!?! oh how i hate the friggin encoding
	s = s.replace("&apos;","'")
	s = s.replace("&#43;","\"")
	s = s.strip()
	return s
	
def pathUserdata(path):
	special = xbmcaddon.Addon().getAddonInfo('profile')+path
	special = special.replace('//','/').replace('special:/','special://')
	return special
	
def pathAddon(path):
	special = xbmc.validatePath(xbmcaddon.Addon().getAddonInfo('path').replace('\\','/')+path.replace('\\','/'))
	special = special.replace('//','/').replace('special:/','special://')
	return special
	
def f_open(path):
	try:
		f = xbmcvfs.File(path)
		result = f.read()
	except: pass
	finally:
		f.close()
	return result

def f_write(path,data):
	try:
		#f_mkdir(path)
		f = xbmcvfs.File(path, 'w')
		result = f.write(data)
	except: pass
	finally:
		f.close()
	return True

def f_remove(path):
	return xbmcvfs.delete(path)
	
def f_exists(path):
	exists = xbmcvfs.exists(path)
	if exists == 0:
		return False
	elif exists == False:
		return False
	else:
		return True
	
def f_mkdir(path):
	return xbmcvfs.mkdir(path)
	
def searchWorkaroundWrite(searchword):
	f_write(pathUserdata('/search.lock'),searchword)
def searchWorkaroundRead():
	return f_open(pathUserdata('/search.lock'))
def searchWorkaroundExists():
	return f_exists(pathUserdata('/search.lock'))
def searchWorkaroundRemove():
	log('###Krypton workaround: removing lock...')
	f_remove(pathUserdata('/search.lock'))

def setSetting(k,v):
	return xbmcplugin.setSetting(int(sys.argv[1]), k, v)
	
def getSetting(k):
	return xbmcplugin.getSetting(int(sys.argv[1]), id=k)
	