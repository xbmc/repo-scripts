# -*- coding: utf-8 -*-
import xbmc
import xbmcplugin
import xbmcgui
import xbmcaddon
import xbmcvfs


def log(msg):
	xbmc.log(msg)

def getTranslation(id):
	return xbmcaddon.Addon().getLocalizedString(id)
			
def pathUserdata(path):
	if not f_exists(xbmcaddon.Addon().getAddonInfo('profile')):
		f_mkdir(xbmcaddon.Addon().getAddonInfo('profile'))
	return xbmcvfs.validatePath(xbmcaddon.Addon().getAddonInfo('profile')+path)
	
def f_open(path):
	with xbmcvfs.File(path) as f:
		result = f.read()
	return result

def f_write(path,data):
	with xbmcvfs.File(path, 'w') as f:
		f.write(data)
	return True

def f_remove(path):
	return xbmcvfs.delete(path)
	
def f_exists(path):
	return xbmcvfs.exists(path)
	
def f_mkdir(path):
	return xbmcvfs.mkdir(path)

def setSetting(k,v):
	return xbmcaddon.Addon().setSetting(k,v)
	
def getSetting(k):
	return xbmcaddon.Addon().getSetting(k)

def executeJSONRPC(cmd):
	xbmc.executeJSONRPC(cmd)
	
def getISO6391():
	return xbmc.getLanguage(xbmc.ISO_639_1) 

def displayMsg(a,b):
	xbmcgui.Dialog().notification(a,b,time=10000)
	