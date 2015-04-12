# -*- coding: utf-8 -*-

""" Log Viewer for Kodi
    2015 fightnight"""

import xbmc,xbmcaddon,xbmcgui,xbmcplugin,urllib,os,re,sys

from lib.logviewer.lib import Logmodule
logmodule=Logmodule()

def addReload(name,mode,iconimage=''):
      return xbmcplugin.addDirectoryItem(handle=int(sys.argv[1]),url="%s?mode=%s" % (sys.argv[0],mode),listitem=xbmcgui.ListItem(name,iconImage="DefaultFolder.png", thumbnailImage=iconimage),isFolder=False)

def getinverted():
    if xbmcaddon.Addon().getSetting('inverter') == 'true': return True
    else: return False

def translate(text):
      return xbmcaddon.Addon().getLocalizedString(text).encode('utf-8')

def getlines():
    nr_lines=xbmcaddon.Addon().getSetting('nrlinhas')
    if nr_lines=='1': return 100
    elif nr_lines=='2': return 50
    elif nr_lines=='3': return 20
    else: return 0

def kodidirs():
    addReload(translate(30001),None)
    addReload(translate(30002),1)

def get_params():
      param=[]
      paramstring=sys.argv[2]
      if len(paramstring)>=2:
            params=sys.argv[2]
            cleanedparams=params.replace('?','')
            if (params[len(params)-1]=='/'):
                  params=params[0:len(params)-2]
            pairsofparams=cleanedparams.split('&')
            param={}
            for i in range(len(pairsofparams)):
                  splitparams={}
                  splitparams=pairsofparams[i].split('=')
                  if (len(splitparams))==2:
                        param[splitparams[0]]=splitparams[1]                 
      return param


params=get_params()
mode=None
try: mode=int(params["mode"])
except: pass

if 'show_log' in sys.argv[2]:
    logmodule.window(old=False,invert=getinverted(),line_number=getlines())

elif 'show_oldlog' in sys.argv[2]:
    logmodule.window(old=True,invert=getinverted(),line_number=getlines())

elif mode==None:
    logmodule.window(old=False,invert=getinverted(),line_number=getlines())
    kodidirs()
    
elif mode==1:
    logmodule.window(old=True,invert=getinverted(),line_number=0)
    kodidirs()
                       
xbmcplugin.endOfDirectory(int(sys.argv[1]))
