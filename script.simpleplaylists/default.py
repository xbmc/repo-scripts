#!/usr/bin/python
# -*- coding: utf-8 -*-
import xbmc, xbmcplugin, xbmcgui, xbmcaddon, locale, sys, urllib, urllib2, re, os, datetime, base64
from operator import itemgetter

useJson=True

pluginhandle=int(sys.argv[1])
addonID = "script.simpleplaylists"
addon_work_folder=xbmc.translatePath("special://profile/addon_data/"+addonID)
settings = xbmcaddon.Addon(id=addonID)
translation = settings.getLocalizedString
lastContentTypeFile=xbmc.translatePath("special://profile/addon_data/"+addonID+"/lastContentType")

lastContentType = xbmc.getInfoLabel('Container.FolderPath')
if lastContentType=="addons://sources/video/":
  lastContentType="Video"
  fh=open(lastContentTypeFile, 'w')
  fh.write(lastContentType)
  fh.close()
elif lastContentType=="addons://sources/audio/":
  lastContentType="Audio"
  fh=open(lastContentTypeFile, 'w')
  fh.write(lastContentType)
  fh.close()
elif lastContentType=="addons://sources/image/":
  lastContentType="Image"
  fh=open(lastContentTypeFile, 'w')
  fh.write(lastContentType)
  fh.close()

if not os.path.isdir(addon_work_folder):
  os.mkdir(addon_work_folder)

useAlternatePlaylistPath=settings.getSetting("useAlternatePlDir")
showKeyboard=settings.getSetting("showKeyboard")
showConfirmation=settings.getSetting("showConfirmation")

if useAlternatePlaylistPath=="true":
  playListFile=xbmc.translatePath(settings.getSetting("alternatePlDir")+"/SimplePlaylists.spl")
  playListNames=xbmc.translatePath(settings.getSetting("alternatePlDir")+"/playlists")
  playListSubNames=xbmc.translatePath(settings.getSetting("alternatePlDir")+"/subfolders")
else:
  playListFile=xbmc.translatePath("special://profile/addon_data/"+addonID+"/SimplePlaylists.spl")
  playListNames=xbmc.translatePath("special://profile/addon_data/"+addonID+"/playlists")
  playListSubNames=xbmc.translatePath("special://profile/addon_data/"+addonID+"/subfolders")

myPlaylists=[]
if os.path.exists(playListNames):
  fh = open(playListNames, 'r')
  for line in fh:
    plType=line[:line.find("=")]
    names=line[line.find("=")+1:]
    spl=names.split(";")
    for name in spl:
      if name!="" and name!="\n":
        myPlaylists.append(plType+": "+name)
  fh.close()
myPlaylists.append("- "+translation(30017))
myPlaylists.append("- "+translation(30019))

def selectMode():
        dialog = xbmcgui.Dialog()
        typeArray = [translation(30022),translation(30032)]
        nr=dialog.select("SimplePlaylists", typeArray)
        if nr>=0:
          type = typeArray[nr]
          if type==translation(30022):
            addCurrentUrl()
          elif type==translation(30032):
            showPlaylists()

def remove(url):
        spl=url.split(";;;")
        mode=spl[0]
        name=spl[1]
        pl=spl[2]
        newContent=""
        fh = open(playListFile, 'r')
        for line in fh:
          if mode=="removePlaylist":
            if line.find("###PLAYLIST###="+name)==-1:
               newContent+=line
          elif mode=="removeFromPlaylist":
            if line.find(name)>=0 and line.find("###PLAYLIST###="+pl+"###")>=0:
              pass
            else:
              newContent+=line
          elif mode=="removeAllPlaylists":
            if line.find("###PLAYLIST###="+name)==-1:
               newContent+=line
        fh.close()
        fh=open(playListFile, 'w')
        fh.write(newContent)
        fh.close()
        xbmc.executebuiltin("Container.Refresh")

def rename(url):
        spl=url.split(";;;")
        name=spl[0]
        pl=spl[1]
        kb = xbmc.Keyboard(name, translation(30033))
        kb.doModal()
        newName=""
        if kb.isConfirmed():
          newName = kb.getText()
        newContent=""
        fh = open(playListFile, 'r')
        for line in fh:
          if line.find("###TITLE###="+name+"###")>=0 and line.find("###PLAYLIST###="+pl+"###")>=0:
            newContent+=line.replace(name,newName)
          else:
            newContent+=line
        fh.close()
        fh=open(playListFile, 'w')
        fh.write(newContent)
        fh.close()
        xbmc.executebuiltin("Container.Refresh")

def managePlaylists():
        dialog = xbmcgui.Dialog()
        typeArray = [translation(30026),translation(30027)]
        nr=dialog.select(translation(30025), typeArray)
        if nr>=0:
          type = typeArray[nr]
          if type==translation(30026):
            if os.path.exists(playListNames):
              types=[]
              fh = open(playListNames, 'r')
              for line in fh:
                types.append(line[:line.find("=")])
              fh.close()
              dialog = xbmcgui.Dialog()
              nr=dialog.select(type, types)
              if nr>=0:
                fullTemp=""
                type = types[nr]
                fh = open(playListNames, 'r')
                for line in fh:
                  temp=line
                  if line.find(type)==0:
                    temp=line[line.find("=")+1:].replace("\n","")
                    kb = xbmc.Keyboard(temp[:len(temp)-1], type)
                    kb.doModal()
                    if kb.isConfirmed():
                      temp = type+"="+kb.getText()
                      if temp[len(temp)-1:]!=";" and kb.getText()!="":
                        temp+=";"
                      temp+="\n"
                    else:
                      temp=line
                  fullTemp+=temp
                fh.close()
                fh=open(playListNames, 'w')
                fh.write(fullTemp)
                fh.close()
            else:
              xbmc.executebuiltin('XBMC.Notification(Info:,'+str(translation(30023))+'!,5000)')
          elif type==translation(30027):
            if os.path.exists(playListSubNames):
              pls=[]
              fh = open(playListSubNames, 'r')
              for line in fh:
                pls.append(line[:line.find("=")])
              fh.close()
              dialog = xbmcgui.Dialog()
              nr=dialog.select(translation(30026), pls)
              if nr>=0:
                fullTemp=""
                playlistTemp = pls[nr]
                fh = open(playListSubNames, 'r')
                for line in fh:
                  temp=line
                  if line.find(playlistTemp)==0:
                    temp=line[line.find("=")+1:].replace("\n","")
                    kb = xbmc.Keyboard(temp[:len(temp)-1], translation(30029)+" "+playlistTemp)
                    kb.doModal()
                    if kb.isConfirmed():
                      temp = playlistTemp+"="+kb.getText()
                      if temp[len(temp)-1:]!=";" and kb.getText()!="":
                        temp+=";"
                      temp+="\n"
                    else:
                      temp=line
                  fullTemp+=temp
                fh.close()
                fh=open(playListSubNames, 'w')
                fh.write(fullTemp)
                fh.close()
            else:
              xbmc.executebuiltin('XBMC.Notification(Info:,'+str(translation(30028))+'!,5000)')

def showPlaylists():
        dialog = xbmcgui.Dialog()
        plTypes=[translation(30001),translation(30002),translation(30003)]
        nr=dialog.select("SimplePlaylists", plTypes)
        if nr >=0:
          plType = plTypes[nr]
          if plType==translation(30001):
            fh=open(lastContentTypeFile, 'w')
            fh.write("Video")
            fh.close()
            xbmc.executebuiltin('XBMC.ActivateWindow(10025,plugin://script.simpleplaylists/?mode=playListMain)')
          elif plType==translation(30002):
            fh=open(lastContentTypeFile, 'w')
            fh.write("Audio")
            fh.close()
            xbmc.executebuiltin('XBMC.ActivateWindow(10502,plugin://script.simpleplaylists/?mode=playListMain)')
          elif plType==translation(30003):
            fh=open(lastContentTypeFile, 'w')
            fh.write("Image")
            fh.close()
            xbmc.executebuiltin('XBMC.ActivateWindow(10002,plugin://script.simpleplaylists/?mode=playListMain)')

def addCurrentUrl():
        addModePlaying="false"
        url = xbmc.getInfoLabel('ListItem.FileNameAndPath')
        path = xbmc.getInfoLabel('ListItem.Path')
        title = xbmc.getInfoLabel('ListItem.Title')
        label = xbmc.getInfoLabel('ListItem.Label')
        plot = xbmc.getInfoLabel('Listitem.Plot')
        genre = xbmc.getInfoLabel('Listitem.Genre')
        year = xbmc.getInfoLabel('Listitem.Year')
        runtime = xbmc.getInfoLabel('Listitem.Duration')
        director = xbmc.getInfoLabel('Listitem.Director')
        rating = xbmc.getInfoLabel('Listitem.Rating')
        tvshowTitle = xbmc.getInfoLabel('Listitem.TVShowTitle')
        fanart = xbmc.getInfoLabel("Listitem.Property(Fanart_Image)")
        artist = xbmc.getInfoLabel('ListItem.Artist')
        picPath = xbmc.getInfoLabel('ListItem.PicturePath')
        isPlayable = xbmc.getInfoLabel('ListItem.Property(IsPlayable)')
        album = xbmc.getInfoLabel('ListItem.Album')
        thumb = xbmc.getInfoLabel('ListItem.Thumb')
        cast = xbmc.getInfoLabel('ListItem.CastAndRole')
        country = xbmc.getInfoLabel('ListItem.Country')
        studio = xbmc.getInfoLabel('ListItem.Studio')
        trailer = xbmc.getInfoLabel('ListItem.Trailer')
        writer = xbmc.getInfoLabel('ListItem.Writer')
        isDir=False
        if isPlayable=="" and fanart=="" and director=="" and picPath=="" and artist=="":
          isDir=True
        if isPlayable=="" and url=="" and path!="":
          isDir=True
          url=path
        isAlbum=False
        if title=="":
          title=label
        if artist!="":
          title = artist+" - "+title
        if artist!="" and album !="" and url=="":
          isAlbum=True
          isDir=True
        if url=="" and isAlbum==False:
          addModePlaying="true"
          if xbmc.Player().isPlayingVideo():
            playlist = xbmc.PlayList(xbmc.PLAYLIST_VIDEO)
            if playlist.getposition()>=0:
              title = playlist[playlist.getposition()].getdescription()
              url = playlist[playlist.getposition()].getfilename()
              thumb=xbmc.getInfoImage('VideoPlayer.Cover')
          elif xbmc.Player().isPlayingAudio():
            title = xbmc.Player().getMusicInfoTag().getArtist()+" - "+xbmc.Player().getMusicInfoTag().getTitle()
            url = xbmc.Player().getMusicInfoTag().getURL()
            thumb=xbmc.getInfoImage('MusicPlayer.Cover')
        if url!="" and addModePlaying=="true":
          isDir=False
          plot = xbmc.getInfoLabel('VideoPlayer.Plot')
          genre = xbmc.getInfoLabel('VideoPlayer.Genre')
          year = xbmc.getInfoLabel('VideoPlayer.Year')
          runtime = xbmc.getInfoLabel('VideoPlayer.Duration')
          director = xbmc.getInfoLabel('VideoPlayer.Director')
          rating = xbmc.getInfoLabel('VideoPlayer.Rating')
          tvshowTitle = xbmc.getInfoLabel('VideoPlayer.TVShowTitle')
          cast = xbmc.getInfoLabel('VideoPlayer.CastAndRole')
          country = xbmc.getInfoLabel('VideoPlayer.Country')
          studio = xbmc.getInfoLabel('VideoPlayer.Studio')
          trailer = xbmc.getInfoLabel('VideoPlayer.Trailer')
          writer = xbmc.getInfoLabel('VideoPlayer.Writer')
          artist = xbmc.getInfoLabel('MusicPlayer.Artist')
          if useJson==True:
              json_result = xbmc.executeJSONRPC('{"jsonrpc": "2.0", "method": "VideoLibrary.GetMovies", "params": {"properties": ["file", "fanart"]}, "id": 1}' )
              if json_result.find('"fanart":')>=0:
                spl=json_result.split('"fanart":')
                for i in range(1,len(spl),1):
                    entry=spl[i]
                    match=re.compile('"(.+?)"', re.DOTALL).findall(entry)
                    fanartNew=match[0]
                    match=re.compile('"file":"(.+?)"', re.DOTALL).findall(entry)
                    urlNew=match[0].replace("\\\\","\\")
                    if url==urlNew:
                      fanart=fanartNew
              if fanart=="":
                json_result = xbmc.executeJSONRPC('{"jsonrpc": "2.0", "method": "VideoLibrary.GetEpisodes", "params": {"properties": ["file", "fanart"]}, "id": 1}' )
                if json_result.find('"episodeid":')>=0:
                  spl=json_result.split('"episodeid":')
                  for i in range(1,len(spl),1):
                      entry=spl[i]
                      match=re.compile('"fanart":"(.+?)"', re.DOTALL).findall(entry)
                      fanartNew=match[0]
                      match=re.compile('"file":"(.+?)"', re.DOTALL).findall(entry)
                      urlNew=match[0].replace("\\\\","\\")
                      if url==urlNew:
                        fanart=fanartNew
        if isAlbum==True:
          if useJson==True:
            json_result = xbmc.executeJSONRPC('{"jsonrpc": "2.0", "method": "AudioLibrary.GetAlbums", "params": {"properties": ["artist"]}, "id": 1}' )
            if json_result.find('"albumid":')>=0:
              spl=json_result.split('"albumid"')
              for i in range(1,len(spl),1):
                  entry=spl[i]
                  match=re.compile(':(.+?),', re.DOTALL).findall(entry)
                  albumID=match[0]
                  match=re.compile('"artist":"(.+?)"', re.DOTALL).findall(entry)
                  artistNew=match[0].replace("\\\\","\\")
                  match=re.compile('"label":(.+?)"', re.DOTALL).findall(entry)
                  albumNew=match[0].replace("\"","")
                  if artist==artistNew and album==albumNew:
                    url="musicdb://3/"+albumID
                    title=artistNew+" - "+title
        cast=cast.replace("\n","/")
        if tvshowTitle!="" and title!=tvshowTitle:
          title=tvshowTitle+" - "+title
        if url!="":
          if title.find("////")>=0:
            title = title[:title.find("////")]
          if showKeyboard=="true":
            kb = xbmc.Keyboard(title, "Title")
            kb.doModal()
            if kb.isConfirmed():
              title = kb.getText()
          date=str(datetime.datetime.now())
          date=date[:date.find(".")]
          plType=""
          if director=="" and artist=="" and picPath=="":
            dialog = xbmcgui.Dialog()
            plTypes=[translation(30001),translation(30002),translation(30003)]
            nr=dialog.select(translation(30022), plTypes)
            if nr>=0:
              plType = plTypes[nr]
              if plType==translation(30001):
                plType="Video"
              elif plType==translation(30002):
                plType="Audio"
              elif plType==translation(30003):
                plType="Image"
          elif artist!="":
            plType="Audio"
          elif picPath!="":
            plType="Image"
          elif director!="":
            plType="Video"
          if plType!="":
            myPlaylistsTemp=[]
            for plTemp in myPlaylists:
              if plTemp.find(plType)==0 or plTemp.find("- "+translation(30017))==0 or plTemp.find("- "+translation(30019))==0:
                myPlaylistsTemp.append(plTemp)
            myPlaylistsTemp2=[]
            for plTemp in myPlaylistsTemp:
              myPlaylistsTemp2.append(plTemp.replace(plType+": ",""))
            dialog = xbmcgui.Dialog()
            nr=dialog.select(translation(30004), myPlaylistsTemp2)
            if nr>=0:
              pl = myPlaylistsTemp[nr]
              if pl=="- "+translation(30017):
                kb = xbmc.Keyboard("", translation(30017))
                kb.doModal()
                if kb.isConfirmed():
                  kbText=kb.getText()
                  pl = plType+": "+kbText
                  if os.path.exists(playListNames):
                    fh = open(playListNames, 'r')
                    content=fh.read()
                    fh.close()
                    if content.find(plType+"=")>=0:
                      fh = open(playListNames, 'r')
                      newPl=""
                      for line in fh:
                        newLine=line
                        if line.find(plType)==0:
                          newLine=line.replace("\n",kbText+";\n")
                        newPl+=newLine
                      fh.close()
                      fh = open(playListNames, 'w')
                      fh.write(newPl)
                      fh.close()
                    else:
                      fh = open(playListNames, 'a')
                      fh.write(plType+"="+kbText+";"+"\n")
                      fh.close()
                  else:
                    fh = open(playListNames, 'w')
                    fh.write(plType+"="+kbText+";"+"\n")
                    fh.close()
              elif pl=="- "+translation(30019):
                myPlaylistsTemp=[]
                for plTemp in myPlaylists:
                  if plTemp.find(plType)==0:
                    myPlaylistsTemp.append(plTemp)
                myPlaylistsTemp2=[]
                for plTemp in myPlaylistsTemp:
                  myPlaylistsTemp2.append(plTemp.replace(plType+": ",""))
                if len(myPlaylistsTemp2)>0:
                  dialog = xbmcgui.Dialog()
                  nr=dialog.select(translation(30004), myPlaylistsTemp2)
                  if nr>=0:
                    plForCat = myPlaylistsTemp[nr]
                    kb = xbmc.Keyboard("", translation(30020))
                    kb.doModal()
                    if kb.isConfirmed():
                      kbText=kb.getText()
                      pl = plForCat+";"+kbText
                      if os.path.exists(playListSubNames):
                        fh = open(playListSubNames, 'r')
                        content=fh.read()
                        fh.close()
                        if content.find(plForCat)>=0:
                          fh = open(playListSubNames, 'r')
                          newPl=""
                          for line in fh:
                            newLine=line
                            if line.find(plForCat)==0:
                              newLine=line.replace("\n",kbText+";\n")
                            newPl+=newLine
                          fh.close()
                          fh = open(playListSubNames, 'w')
                          fh.write(newPl)
                          fh.close()
                        else:
                          fh = open(playListSubNames, 'a')
                          fh.write(plForCat+"="+kbText+";"+"\n")
                          fh.close()
                      else:
                        fh = open(playListSubNames, 'w')
                        fh.write(plForCat+"="+kbText+";"+"\n")
                        fh.close()
                else:
                  xbmc.executebuiltin('XBMC.Notification(Info:,'+str(translation(30023))+'!,5000)')
              else:
                cats=[]
                cats.append(pl.replace(plType+": ",""))
                if os.path.exists(playListSubNames):
                  fh = open(playListSubNames, 'r')
                  for line in fh:
                    if line.find(pl)==0:
                      temp=line[line.find("=")+1:]
                      spl=temp.split(";")
                      for cat in spl:
                        if cat!="\n":
                          if not cat in cats:
                            cats.append(" - "+cat)
                  fh.close()
                cats.append(translation(30019))
                if len(cats)>2:
                  dialog = xbmcgui.Dialog()
                  nr=dialog.select(translation(30004), cats)
                  if nr>=0:
                    if cats[nr]==pl.replace(plType+": ",""):
                      pass
                    elif cats[nr]==translation(30019):
                      plForCat = pl
                      kb = xbmc.Keyboard("", translation(30020))
                      kb.doModal()
                      if kb.isConfirmed():
                        kbText=kb.getText()
                        pl = plForCat+";"+kbText
                        if os.path.exists(playListSubNames):
                          fh = open(playListSubNames, 'r')
                          content=fh.read()
                          fh.close()
                          if content.find(plForCat)>=0:
                            fh = open(playListSubNames, 'r')
                            newPl=""
                            for line in fh:
                              newLine=line
                              if line.find(plForCat)==0:
                                newLine=line.replace("\n",kbText+";\n")
                              newPl+=newLine
                            fh.close()
                            fh = open(playListSubNames, 'w')
                            fh.write(newPl)
                            fh.close()
                          else:
                            fh = open(playListSubNames, 'a')
                            fh.write(plForCat+"="+kbText+";"+"\n")
                            fh.close()
                        else:
                          fh = open(playListSubNames, 'w')
                          fh.write(plForCat+"="+kbText+";"+"\n")
                          fh.close()
                    else:
                      pl = pl+";"+cats[nr][3:]
                  else:
                    pl=""
              pl=str(pl)
              if pl!="" and pl!="- "+translation(30017) and pl!=translation(30019) and pl!="- "+translation(30019):
                playlistEntry="###TITLE###="+title+"###DATE###="+date+"###URL###="+url+"###FANART###="+fanart+"###ISDIR###="+str(isDir)+"###THUMB###="+thumb+"###PLOT###="+plot+"###GENRE###="+genre+"###DIRECTOR###="+director+"###RATING###="+rating+"###COUNTRY###="+country+"###TRAILER###="+trailer+"###CAST###="+cast+"###STUDIO###="+studio+"###WRITER###="+writer+"###YEAR###="+year+"###RUNTIME###="+runtime+"###PLAYLIST###="+pl+"###END###"
                if os.path.exists(playListFile):
                  fh = open(playListFile, 'r')
                  content=fh.read()
                  fh.close()
                  if content.find(playlistEntry[playlistEntry.find("###URL###="):])==-1:
                    fh=open(playListFile, 'a')
                    fh.write(playlistEntry+"\n")
                    fh.close()
                  else:
                    xbmc.executebuiltin('XBMC.Notification(Info:,'+str(translation(30016))+'!,5000)')
                else:
                  fh=open(playListFile, 'a')
                  fh.write(playlistEntry+"\n")
                  fh.close()
                if showConfirmation=="true":
                  xbmc.executebuiltin('XBMC.Notification(Info:,'+str(translation(30030))+'!,2000)')
        else:
          xbmc.executebuiltin('XBMC.Notification(Info:,'+str(translation(30005))+'!,5000)')

def playListMain():
        lastContentType=""
        xbmcplugin.addSortMethod(pluginhandle, xbmcplugin.SORT_METHOD_LABEL)
        playlists=[]
        if os.path.exists(playListFile):
          fh = open(playListFile, 'r')
          for line in fh:
            pl=line[line.find("###PLAYLIST###=")+15:]
            pl=pl[:pl.find("###")]
            if pl.find(";")>=0:
              pl=pl[:pl.find(";")]
            if not pl in playlists:
              if os.path.exists(lastContentTypeFile):
                fh = open(lastContentTypeFile, 'r')
                lastContentType=fh.read()
                fh.close()
                if pl.find(lastContentType)==0:
                  playlists.append(pl)
              else:
                playlists.append(pl)
          fh.close()
          for pl in playlists:
            titleNew=pl;
            if lastContentType!="":
              titleNew=pl.replace(lastContentType+": ","")
            if os.path.exists(playListSubNames):
              fh = open(playListSubNames, 'r')
              content=fh.read()
              fh.close()
              if content.find(pl)>=0:
                addDir(titleNew,pl,'showSubfolders',"")
              else:
                addDir(titleNew,pl,'showPlaylist',"")
            else:
              addDir(titleNew,pl,'showPlaylist',"")
        xbmcplugin.endOfDirectory(pluginhandle)

def showSubfolders(playlist):
        xbmcplugin.addSortMethod(pluginhandle, xbmcplugin.SORT_METHOD_LABEL)
        cats=[]
        fh = open(playListFile, 'r')
        for line in fh:
          if line.find("###PLAYLIST###="+playlist+";")>=0:
            pl=line[line.find("###PLAYLIST###="+playlist+";")+len(playlist)+16:]
            pl=pl[:pl.find("###")]
            if not pl in cats:
              cats.append(pl)
        fh.close()
        for cat in cats:
          addSubDir(cat,playlist+";"+cat,'showPlaylist',"")
        showPlaylist(playlist)
        xbmcplugin.endOfDirectory(pluginhandle)

def showPlaylist(playlist):
        allEntrys=[]
        fh = open(playListFile, 'r')
        all_lines = fh.readlines()
        for line in all_lines:
          pl=line[line.find("###PLAYLIST###=")+15:]
          pl=pl[:pl.find("###")]
          url=line[line.find("###URL###=")+10:]
          url=url[:url.find("###")]
          fanart=line[line.find("###FANART###=")+13:]
          fanart=fanart[:fanart.find("###")]
          plot=line[line.find("###PLOT###=")+11:]
          plot=plot[:plot.find("###")]
          director=line[line.find("###DIRECTOR###=")+15:]
          director=director[:director.find("###")]
          genre=line[line.find("###GENRE###=")+12:]
          genre=genre[:genre.find("###")]
          rating=line[line.find("###RATING###=")+13:]
          rating=rating[:rating.find("###")]
          year=line[line.find("###YEAR###=")+11:]
          year=year[:year.find("###")]
          runtime=line[line.find("###RUNTIME###=")+14:]
          runtime=runtime[:runtime.find("###")]
          title=line[line.find("###TITLE###=")+12:]
          title=title[:title.find("###")]
          isDir=line[line.find("###ISDIR###=")+12:]
          isDir=isDir[:isDir.find("###")]  
          thumb=line[line.find("###THUMB###=")+12:]
          thumb=thumb[:thumb.find("###")]
          date=line[line.find("###DATE###=")+11:]
          date=date[:date.find("###")]
          cast=line[line.find("###CAST###=")+11:]
          cast=cast[:cast.find("###")]
          writer=line[line.find("###WRITER###=")+13:]
          writer=writer[:writer.find("###")]
          studio=line[line.find("###STUDIO###=")+13:]
          studio=studio[:studio.find("###")]
          country=line[line.find("###COUNTRY###=")+14:]
          country=country[:country.find("###")]
          trailer=line[line.find("###TRAILER###=")+14:]
          trailer=trailer[:trailer.find("###")]
          castNew=[]
          spl=cast.split("/")
          for temp in spl:
            castNew.append(temp)
          if plot=="":
            plot=date
          if pl==playlist:
            entry=[title,url,date,pl,fanart,plot,genre,year,runtime,director,rating,isDir,thumb,castNew,writer,studio,country,trailer]
            allEntrys.append(entry)
        fh.close()
        allEntrys=sorted(allEntrys, key=itemgetter(2), reverse=True)
        for entry in allEntrys:
          if entry[11]=="True":
            addLinkDir(entry[0],entry[1],entry[3],entry[12])
          else:
            addLink(entry[0],entry[1],'playMediaFromPlaylist',entry[12],entry[5],entry[3],entry[4],entry[6],entry[7],entry[8],entry[9],entry[10],entry[13],entry[14],entry[15],entry[16],entry[17])
        xbmcplugin.endOfDirectory(pluginhandle)

def playMediaFromPlaylist(url):
        listitem = xbmcgui.ListItem(path=urllib.unquote_plus(url))
        return xbmcplugin.setResolvedUrl(pluginhandle, True, listitem)

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

def addLink(name,url,mode,iconimage,plot,pl,fanart,genre,year,runtime,director,rating,cast,writer,studio,country,trailer):
        ok=True
        liz=xbmcgui.ListItem(name, iconImage="DefaultVideo.png", thumbnailImage=iconimage)
        type="Video"
        if pl.find("Image:")==0:
          type="Image"
        elif pl.find("Audio:")==0:
          type="Audio"
        if year!="":
          year=int(year)
        if type=="Video":
          liz.setInfo( type=type, infoLabels={ "Title": name, "plot": plot, "genre": genre, "year": year, "director": director, "rating": rating, "duration": runtime, "cast": cast, "writer": writer, "studio": studio, "country": country, "trailer": trailer } )
        liz.setProperty('IsPlayable', 'true')
        liz.setProperty('fanart_image', fanart)
        liz.addContextMenuItems([(translation(30033), 'RunPlugin(plugin://script.simpleplaylists/?mode=rename&url='+urllib.quote_plus(name+";;;"+pl)+')'),(translation(30013), 'RunPlugin(plugin://script.simpleplaylists/?mode=remove&url='+urllib.quote_plus("removeFromPlaylist;;;"+name+";;;"+pl)+')')])
        ok=xbmcplugin.addDirectoryItem(handle=int(sys.argv[1]),url=url,listitem=liz)
        return ok

def addDir(name,url,mode,iconimage):
        u=sys.argv[0]+"?url="+urllib.quote_plus(url)+"&mode="+str(mode)
        ok=True
        liz=xbmcgui.ListItem(name, iconImage="DefaultFolder.png", thumbnailImage=iconimage)
        liz.setInfo( type="Video", infoLabels={ "Title": name } )
        liz.addContextMenuItems([(translation(30014), 'RunPlugin(plugin://script.simpleplaylists/?mode=remove&url='+urllib.quote_plus("removePlaylist;;;"+url+";;;")+')'),(translation(30015), 'RunPlugin(plugin://script.simpleplaylists/?mode=remove&url='+urllib.quote_plus("removeAllPlaylists;;;"+url[:url.find(":")]+";;;")+')'),(translation(30025), 'RunPlugin(plugin://script.simpleplaylists/?mode=managePlaylists)')])
        ok=xbmcplugin.addDirectoryItem(handle=int(sys.argv[1]),url=u,listitem=liz,isFolder=True)
        return ok

def addSubDir(name,url,mode,iconimage):
        u=sys.argv[0]+"?url="+urllib.quote_plus(url)+"&mode="+str(mode)
        ok=True
        liz=xbmcgui.ListItem(name, iconImage="DefaultFolder.png", thumbnailImage=iconimage)
        liz.setInfo( type="Video", infoLabels={ "Title": name } )
        liz.addContextMenuItems([(translation(30034), 'RunPlugin(plugin://script.simpleplaylists/?mode=remove&url='+urllib.quote_plus("removePlaylist;;;"+url+";;;")+')'),(translation(30035), 'RunPlugin(plugin://script.simpleplaylists/?mode=managePlaylists)')])
        ok=xbmcplugin.addDirectoryItem(handle=int(sys.argv[1]),url=u,listitem=liz,isFolder=True)
        return ok

def addLinkDir(name,url,pl,thumb):
        ok=True
        liz=xbmcgui.ListItem(name, iconImage="DefaultFolder.png", thumbnailImage=thumb)
        liz.setInfo( type="Video", infoLabels={ "Title": name } )
        liz.addContextMenuItems([(translation(30033), 'RunPlugin(plugin://script.simpleplaylists/?mode=rename&url='+urllib.quote_plus(name+";;;"+pl)+')'),(translation(30013), 'RunPlugin(plugin://script.simpleplaylists/?mode=remove&url='+urllib.quote_plus("removeFromPlaylist;;;"+name+";;;"+pl)+')')])
        ok=xbmcplugin.addDirectoryItem(handle=int(sys.argv[1]),url=url,listitem=liz,isFolder=True)
        return ok

params=parameters_string_to_dict(sys.argv[2])
mode=params.get('mode')
url=params.get('url')
if type(url)==type(str()):
  url=urllib.unquote_plus(url)

if mode == 'addCurrentUrl':
    addCurrentUrl()
elif mode == 'showPlaylists':
    showPlaylists()
elif mode == 'showPlaylist':
    showPlaylist(url)
elif mode == 'showSubfolders':
    showSubfolders(url)
elif mode == 'playMediaFromPlaylist':
    playMediaFromPlaylist(url)
elif mode == 'managePlaylists':
    managePlaylists()
elif mode == 'playListMain':
    playListMain()
elif mode == 'selectMode':
    selectMode()
elif mode == 'remove':
    remove(url)
elif mode == 'rename':
    rename(url)
else:
    playListMain()