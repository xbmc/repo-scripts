#!/usr/bin/python
# -*- coding: utf-8 -*-
import xbmc, xbmcgui, xbmcplugin, xbmcaddon, locale, sys, urllib, urllib2, re, os

addonID = "script.categories"
pluginhandle = int(sys.argv[1])
addon_work_folder=xbmc.translatePath("special://profile/addon_data/"+addonID)
addonsFolder=xbmc.translatePath('special://home/addons/')
catsFile=xbmc.translatePath(addon_work_folder+'/categories.list')
addon = xbmcaddon.Addon(id=addonID)
translation = addon.getLocalizedString
forceViewMode=addon.getSetting("forceViewMode")
viewMode=str(addon.getSetting("viewMode"))
if not os.path.isdir(addon_work_folder):
  os.mkdir(addon_work_folder)

def indexMain():
        dialog = xbmcgui.Dialog()
        plTypes=[translation(30006),translation(30007),translation(30008)]
        nr=dialog.select("Categories", plTypes)
        if nr >=0:
          plType = plTypes[nr]
          if plType==translation(30006):
            xbmc.executebuiltin('XBMC.ActivateWindow(10025,plugin://script.categories/?content_type=video)')
          elif plType==translation(30007):
            xbmc.executebuiltin('XBMC.ActivateWindow(10501,plugin://script.categories/?content_type=audio)')
          elif plType==translation(30008):
            xbmc.executebuiltin('XBMC.ActivateWindow(10002,plugin://script.categories/?content_type=image)')

def index(cType):
        addDir(translation(30001), "all", "listCat", "")
        cats = []
        if os.path.exists(catsFile):
          json_result = xbmc.executeJSONRPC('{"jsonrpc": "2.0", "method": "Addons.GetAddons", "params": {"content": "'+cType+'"}, "id": 1}' )
          fh = open(catsFile, 'r')
          if '"Method not found."' in json_result:
            for line in fh:
              id = line[:line.find("#")]
              currentAddon = xbmcaddon.Addon(id=id)
              path = xbmc.translatePath('special://home/addons/'+id+'/addon.xml')
              fh = open(path, 'r')
              xml = fh.read()
              fh.close()
              match=re.compile('<provides>(.+?)</provides>', re.DOTALL).findall(xml)
              types=match[0]
              cat = line[line.find("#")+1:]
              cat = cat[:cat.find("#END")]
              if cType in types and cat not in cats:
                cats.append(cat)
          else:
            for line in fh:
              id = line[:line.find("#")]
              if id in json_result:
                cat = line[line.find("#")+1:]
                cat = cat[:cat.find("#END")]
                if cat not in cats:
                  cats.append(cat)
          fh.close()
          for cat in cats:
            addRDir(cat, cat, "listCat", "")
        xbmcplugin.endOfDirectory(pluginhandle)

def listCat(cat,cType):
        xbmcplugin.addSortMethod(pluginhandle, xbmcplugin.SORT_METHOD_LABEL)
        addons = os.listdir(addonsFolder)
        json_result = xbmc.executeJSONRPC('{"jsonrpc": "2.0", "method": "Addons.GetAddons", "params": {"content": "'+cType+'"}, "id": 1}' )
        if '"Method not found."' in json_result:
          if cat == "all":
            for a in addons:
              path = xbmc.translatePath('special://home/addons/'+a+'/addon.xml')
              try:
                fh = open(path, 'r')
                xml = fh.read()
                fh.close()
                match=re.compile('<provides>(.+?)</provides>', re.DOTALL).findall(xml)
                types=match[0]
              except:
                types=""
              if a!="script.categories" and cType in types:
                try:
                  currentAddon = xbmcaddon.Addon(id=a)
                  desc = "Version: "+currentAddon.getAddonInfo('version')+" ("+currentAddon.getAddonInfo('author')+")\n"+currentAddon.getAddonInfo('description')
                  addAddonDir(currentAddon.getAddonInfo('name'),a,currentAddon.getAddonInfo('icon'),desc,cType)
                except:
                  pass
          else:
            if os.path.exists(catsFile):
              fh = open(catsFile, 'r')
              content=fh.read()
              fh.close()
              for a in addons:
                path = xbmc.translatePath('special://home/addons/'+a+'/addon.xml')
                try:
                  fh = open(path, 'r')
                  xml = fh.read()
                  fh.close()
                  match=re.compile('<provides>(.+?)</provides>', re.DOTALL).findall(xml)
                  types=match[0]
                except:
                  types=""
                if a!="script.categories" and cType in types and a+"#"+cat in content:
                  try:
                    currentAddon = xbmcaddon.Addon(id=a)
                    desc = "Version: "+currentAddon.getAddonInfo('version')+" ("+currentAddon.getAddonInfo('author')+")\n"+currentAddon.getAddonInfo('description')
                    addAddonRDir(currentAddon.getAddonInfo('name'),a,currentAddon.getAddonInfo('icon'),cat,desc)
                  except:
                    pass

        else:
          match=re.compile('"addonid":"(.+?)","type":"(.+?)"', re.DOTALL).findall(json_result)
          if cat == "all":
            for addonid, temp in match:
              try:
                if addonid!="script.categories":
                  currentAddon = xbmcaddon.Addon(id=addonid)
                  desc = "Version: "+currentAddon.getAddonInfo('version')+" ("+currentAddon.getAddonInfo('author')+")\n"+currentAddon.getAddonInfo('description')
                  addAddonDir(currentAddon.getAddonInfo('name'),addonid,currentAddon.getAddonInfo('icon'),desc,cType)
              except:
                pass
          else:
            if os.path.exists(catsFile):
              fh = open(catsFile, 'r')
              content=fh.read()
              fh.close()
              for addonid, temp in match:
                if addonid+"#"+cat in content:
                  try:
                    if addonid!="script.categories":
                      currentAddon = xbmcaddon.Addon(id=addonid)
                      desc = "Version: "+currentAddon.getAddonInfo('version')+" ("+currentAddon.getAddonInfo('author')+")\n"+currentAddon.getAddonInfo('description')
                      addAddonRDir(currentAddon.getAddonInfo('name'),addonid,currentAddon.getAddonInfo('icon'),cat,desc)
                  except:
                    pass
        xbmcplugin.endOfDirectory(pluginhandle)
        if forceViewMode=="true":
          xbmc.executebuiltin('Container.SetViewMode('+viewMode+')')

def addAddon(args):
        cType=args[:args.find("#")]
        addonID=args[args.find("#")+1:]
        playlistsTemp=[]
        catsCount=20
        for i in range(0,catsCount,1):
          playlistsTemp.append(addon.getSetting("cat_"+cType+"_"+str(i)))
        playlists=[]
        for pl in playlistsTemp:
          if pl!="":
            playlists.append(pl)
        playlists.append("- "+translation(30005))
        if len(playlists)==0:
          addon.openSettings()
          playlistsTemp=[]
          for i in range(0,catsCount,1):
            playlistsTemp.append(addon.getSetting("cat_"+cType+"_"+str(i)))
          playlists=[]
          for pl in playlistsTemp:
            if pl!="":
              playlists.append(pl)
          playlists.append("- "+translation(30005))
        dialog = xbmcgui.Dialog()
        index=dialog.select(translation(30004), playlists)
        if index>=0:
          pl = playlists[index]
          while ("- "+str(translation(30005)) in pl):
            addon.openSettings()
            playlistsTemp=[]
            for i in range(0,catsCount,1):
              playlistsTemp.append(addon.getSetting("cat_"+cType+"_"+str(i)))
            playlists=[]
            for pl in playlistsTemp:
              if pl!="":
                playlists.append(pl)
            playlists.append("- "+translation(30005))
            dialog = xbmcgui.Dialog()
            index=dialog.select(translation(30004), playlists)
            if index>=0:
              pl = playlists[index]
          if pl!="":
            playlistEntry=addonID+"#"+pl+"#END"
            if os.path.exists(catsFile):
              fh = open(catsFile, 'r')
              content=fh.read()
              fh.close()
              if content.find(playlistEntry)==-1:
                fh=open(catsFile, 'a')
                fh.write(playlistEntry+"\n")
                fh.close()
            else:
              fh=open(catsFile, 'a')
              fh.write(playlistEntry+"\n")
              fh.close()

def deleteAddon(args):
        fh = open(catsFile, 'r')
        content=fh.read()
        fh.close()
        fh=open(catsFile, 'w')
        fh.write(content.replace(args+"\n",""))
        fh.close()
        xbmc.executebuiltin("Container.Refresh")

def deleteCat(args):
        dialog = xbmcgui.Dialog()
        ok = dialog.ok('Info:', translation(30010)+"?")
        if ok==True:
          newContent=""
          fh = open(catsFile, 'r')
          for line in fh:
            if args+"#END" not in line:
               newContent+=line
          fh.close()
          fh=open(catsFile, 'w')
          fh.write(newContent)
          fh.close()
          xbmc.executebuiltin("Container.Refresh")

def renameCat(args):
        keyboard = xbmc.Keyboard(args, translation(30011)+" "+args)
        keyboard.doModal()
        if keyboard.isConfirmed() and keyboard.getText():
          newName = keyboard.getText()
          fh=open(catsFile, 'r')
          content=fh.read()
          fh.close()
          fh=open(catsFile, 'w')
          fh.write(content.replace(args+"#END",newName+"#END"))
          fh.close()
          xbmc.executebuiltin("Container.Refresh")

def parameters_string_to_dict(parameters):
        ''' Convert parameters encoded in a URL to a dict. '''
        paramDict = {}
        if parameters:
            paramPairs = parameters[1:].split("&")
            for paramsPair in paramPairs:
                paramSplits = paramsPair.split('=')
                if (len(paramSplits)) == 2:
                    paramDict[paramSplits[0]] = paramSplits[1]
        return paramDict

def addLink(name,url,mode,iconimage,desc="",duration=""):
        u=sys.argv[0]+"?url="+urllib.quote_plus(url)+"&mode="+str(mode)+"&content_type="+str(contentType)
        ok=True
        liz=xbmcgui.ListItem(name, iconImage="DefaultVideo.png", thumbnailImage=iconimage)
        liz.setInfo( type="Video", infoLabels={ "Title": name, "Plot": desc, "Duration": duration } )
        liz.setProperty('IsPlayable', 'true')
        ok=xbmcplugin.addDirectoryItem(handle=int(sys.argv[1]),url=u,listitem=liz)
        return ok

def addDir(name,url,mode,iconimage):
        u=sys.argv[0]+"?url="+urllib.quote_plus(url)+"&mode="+str(mode)+"&content_type="+str(contentType)
        ok=True
        liz=xbmcgui.ListItem(name, iconImage="DefaultFolder.png", thumbnailImage=iconimage)
        liz.setInfo( type="Video", infoLabels={ "Title": name } )
        ok=xbmcplugin.addDirectoryItem(handle=int(sys.argv[1]),url=u,listitem=liz,isFolder=True)
        return ok

def addAddonDir(name,url,iconimage,desc="",cType=""):
        ok=True
        liz=xbmcgui.ListItem(name, iconImage="DefaultFolder.png", thumbnailImage=iconimage)
        liz.setInfo( type="Video", infoLabels={ "Title": name, "Plot": desc } )
        liz.addContextMenuItems([(translation(30002), 'RunPlugin(plugin://script.categories/?mode=addAddon&url='+urllib.quote_plus(cType+"#"+url)+')',)])
        ok=xbmcplugin.addDirectoryItem(handle=int(sys.argv[1]),url="plugin://"+url+"/",listitem=liz,isFolder=True)
        return ok

def addAddonRDir(name,url,iconimage,cat,desc=""):
        ok=True
        liz=xbmcgui.ListItem(name, iconImage="DefaultFolder.png", thumbnailImage=iconimage)
        liz.setInfo( type="Video", infoLabels={ "Title": name, "Plot": desc } )
        liz.addContextMenuItems([(translation(30003), 'RunPlugin(plugin://script.categories/?mode=deleteAddon&url='+urllib.quote_plus(url+"#"+cat+"#END")+')',)])
        ok=xbmcplugin.addDirectoryItem(handle=int(sys.argv[1]),url="plugin://"+url+"/",listitem=liz,isFolder=True)
        return ok

def addRDir(name,url,mode,iconimage):
        u=sys.argv[0]+"?url="+urllib.quote_plus(url)+"&mode="+str(mode)+"&content_type="+str(contentType)
        ok=True
        liz=xbmcgui.ListItem(name, iconImage="DefaultFolder.png", thumbnailImage=iconimage)
        liz.setInfo( type="Video", infoLabels={ "Title": name } )
        liz.addContextMenuItems([(translation(30009), 'RunPlugin(plugin://script.categories/?mode=deleteCat&url='+urllib.quote_plus(name)+')',),(translation(30012), 'RunPlugin(plugin://script.categories/?mode=renameCat&url='+urllib.quote_plus(name)+')',)])
        ok=xbmcplugin.addDirectoryItem(handle=int(sys.argv[1]),url=u,listitem=liz,isFolder=True)
        return ok

params=parameters_string_to_dict(sys.argv[2])
mode=params.get('mode')
url=params.get('url')
contentType=params.get('content_type')

if contentType!="video" and contentType!="audio" and contentType!="image":
  contentType=""
  folder = xbmc.getInfoLabel('Container.FolderPath')
  if 'video' in folder:
    contentType = "video"
  elif 'audio' in folder:
    contentType = "audio"
  elif 'image' in folder:
    contentType = "image"

if type(url)==type(str()):
  url=urllib.unquote_plus(url)

if contentType == "":
    indexMain()
elif mode == 'listCat':
    listCat(url,contentType)
elif mode == 'addAddon':
    addAddon(url)
elif mode == 'deleteAddon':
    deleteAddon(url)
elif mode == 'deleteCat':
    deleteCat(url)
elif mode == 'renameCat':
    renameCat(url)
else:
    index(contentType)
