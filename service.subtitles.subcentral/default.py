#!/usr/bin/python
# -*- coding: utf-8 -*-
import xbmc, xbmcgui, xbmcaddon, urllib, urllib2, socket, cookielib, re, os, shutil, base64, xbmcvfs

addon = xbmcaddon.Addon()
socket.setdefaulttimeout(60)
addonID = addon.getAddonInfo('id')
translation = addon.getLocalizedString
addonUserDataFolder=xbmc.translatePath("special://profile/addon_data/"+addonID)
#addonUserDataFolder=xbmc.translatePath("special://temp/"+addonID)
subTempDir=xbmc.translatePath("special://profile/addon_data/"+addonID+"/srtTemp/")
icon = xbmc.translatePath('special://home/addons/'+addonID+'/icon.png')
rarFile=xbmc.translatePath(addonUserDataFolder+"/sub.")
subFile=xbmc.translatePath(addonUserDataFolder+"/sub.srt")
favFile=xbmc.translatePath(addonUserDataFolder+"/favourites")
apiKeyFile=xbmc.translatePath(addonUserDataFolder+"/api.key")

if not os.path.isdir(addonUserDataFolder):
  os.makedirs(addonUserDataFolder)
if not os.path.isdir(subTempDir):
  os.makedirs(subTempDir)

if os.path.exists(apiKeyFile):
  fh = open(apiKeyFile, 'r')
  ownKey = fh.read()
  fh.close()
else:
  ownKey=""

user=""
pw=""
backNav=""
pause=""
saveSub=""
language=""

def getSettings():
  global user
  user=addon.getSetting("user")
  global pw
  pw=addon.getSetting("pw")
  global backNav
  backNav=addon.getSetting("backNav")
  global pause
  pause=addon.getSetting("pause")
  global saveSub
  saveSub=addon.getSetting("saveSub")
  global language
  language=addon.getSetting("language")
  global debuging
  debuging=addon.getSetting("debug")

getSettings()
if debuging=="true":
  xbmc.log("Subcentral: pruefe ob Pause gesetzt werden soll")
if pause=="true" and xbmc.Player().isPlayingVideo():
  if debuging=="true":
    xbmc.log("Subcentral: Video wird angehalten")
  xbmc.Player().pause()
if debuging=="true":
 xbmc.log("Subcentral: Lese Playliste ein")
playlist = xbmc.PlayList(xbmc.PLAYLIST_VIDEO)
if debuging=="true":
  xbmc.log("Subcentral: Momentan spielt Video Nr: "+ str(playlist.getposition()) +" ab")
  xbmc.log("Subcentral: Lese Titel des Videos ein")
if playlist.getposition()>=0:
  if debuging=="true":
    xbmc.log("Subcentral: Lese Titel des Videos ein")
  currentTitle = playlist[playlist.getposition()].getdescription()

if debuging=="true":
  xbmc.log("Subcentral: Lese Aktuelles VideoFile ein")
try:
  currentFile = xbmc.Player().getPlayingFile()
except:
      dialog = xbmcgui.Dialog()
      nr=dialog.select("SubCentral.de", [translation(30109)])
      xbmc.log("Subcentral: Es Leuft kein Video")  
      quit()
if debuging=="true":
  xbmc.log("Subcentral: Logge ein")
cj = cookielib.CookieJar()
mainUrl = "http://www.subcentral.de"
opener = urllib2.build_opener(urllib2.HTTPCookieProcessor(cj))
userAgent = "Mozilla/5.0 (Windows NT 6.2; WOW64; rv:23.0) Gecko/20100101 Firefox/23.0"
opener.addheaders = [('User-Agent', userAgent)]
opener.open(mainUrl+"/index.php?form=UserLogin", data="loginUsername="+urllib.quote_plus(user)+"&loginPassword="+urllib.quote_plus(pw))

while (user=="" or pw==""):
  addon.openSettings()
  getSettings()

currentEpisode=""
currentSeason=""
currentEpisode=xbmc.getInfoLabel('VideoPlayer.Episode')
currentSeason=xbmc.getInfoLabel('VideoPlayer.Season')

dirName = ""
try:
  cf=currentFile.replace("\\","/")
  all=cf.split("/")
  #dirName=(currentFile.split(os.sep)[-2]).lower()
  dirName=all[-2].lower()
  fileName=all[-1].lower()
except:
  pass

if currentEpisode=="":
  matchDir=re.compile('\\.s(.+?)e(.+?)\\.', re.DOTALL).findall(dirName)
  matchFile=re.compile('\\.s(.+?)e(.+?)\\.', re.DOTALL).findall(fileName)
  if len(matchDir)>0:
    currentSeason=matchDir[0][0]
    currentEpisode=matchDir[0][1]
  elif len(matchFile)>0:
    currentSeason=matchFile[0][0]
    currentEpisode=matchFile[0][1]

if currentEpisode=="":
  match=re.compile('(.+?)- s(.+?)e(.+?) ', re.DOTALL).findall(xbmc.getInfoLabel('VideoPlayer.Title').lower())
  if len(match)>0:
    currentSeason=match[0][1]
    currentEpisode=match[0][2]

if len(currentEpisode)==1:
  currentEpisode="0"+currentEpisode
if len(currentSeason)==1:
  currentSeason="0"+currentSeason

currentRelease=""
if "-" in fileName:
  currentRelease=(fileName.split("-")[-1]).lower()
  if "." in currentRelease:
    currentRelease=currentRelease[:currentRelease.find(".")]
elif "-" in dirName:
  currentRelease=(dirName.split("-")[-1]).lower()

def main():
        global mainType
        mainType = ""
        if debuging=="true":
          xbmc.log("Subcentral: Starte Main")
          xbmc.log("Subcentral: Zeige Auswahl an")
        dialog = xbmcgui.Dialog()
        nr=dialog.select("SubCentral.de", [translation(30013),translation(30001),translation(30002),translation(30011)])
        if nr==0:
          search()
        elif nr==1:
          mainType="fav"
          showFavourites()
        elif nr==2:
          mainType="all"
          showAllSeries()
        elif nr==3:
          addon.openSettings()
          getSettings()
          main()
        else:
          if pause=="true" and xbmc.Player().isPlayingVideo():
            xbmc.Player().pause()

def search():
        title=xbmc.getInfoLabel('VideoPlayer.TVShowTitle')
        season=currentSeason
        episode=currentEpisode
        release=currentRelease
        if debuging=="true":
          xbmc.log("Subcentral: Starte Suche")
        
        if title=="" or season=="":
          matchDir=re.compile('(.+?)\\.s(.+?)e(.+?)\\.', re.DOTALL).findall(dirName)
          matchFile=re.compile('(.+?)\\.s(.+?)e(.+?)\\.', re.DOTALL).findall(fileName)
          matchTitle=re.compile('(.+?)- s(.+?)e(.+?) ', re.DOTALL).findall(xbmc.getInfoLabel('VideoPlayer.Title').lower())
          if len(matchDir)>0:
            title=matchDir[0][0]
          elif len(matchFile)>0:
            title=matchFile[0][0]
          elif len(matchTitle)>0:
            title=matchTitle[0][0].strip()
        
        title=title.replace("."," ")
        if "(" in title:
          title=title[:title.find("(")].strip()
        
        if title=="" or season=="" or episode=="":
          xbmc.executebuiltin('XBMC.Notification(SubCentral.de:,'+translation(30014)+'!,3000,'+icon+')')
          main()
        else:
          if season[0:1]=="0":
            season=season[1:]

          general=base64.b64decode("QUl6YVN5RGJtNzRTNlZia1VjWmNQeC1HTTFtU1B5N2ZYU0R2Vy1J")
          global ownKey
          if ownKey=="":
            ownKey=general
          searchString1='intitle:"[subs] '+title+' - staffel '+season+'|0'+season+'"'
          searchString2='intitle:"[subs] The '+title+' - staffel '+season+'|0'+season+'"'
          fullUrl="https://www.googleapis.com/customsearch/v1?key="+ownKey+"&cx=016144106520845837387:lj4yjfpwyna&q="+urllib.quote_plus(searchString1)+"|"+urllib.quote_plus(searchString2)+"&alt=json"
          xbmc.log("SCDE Addon Log - Search: "+title+"#"+season)
          content = getUrl(fullUrl)
          if '"items"' in content:
            content = content[content.find('"items"'):]
            spl=content.split('"kind"')
            finalUrl=""
            for i in range(1,len(spl),1):
              entry=spl[i]
              match=re.compile('"title": "(.+?)"', re.DOTALL).findall(entry)
              title=match[0]
              match=re.compile('"link": "(.+?)"', re.DOTALL).findall(entry)
              url=match[0]
              if "staffel" in title.lower() and "subs:" in title.lower() and "postID=" not in url and "boardID=" not in url:
                finalUrl=url
                break
            if finalUrl=="":
              for i in range(1,len(spl),1):
                entry=spl[i]
                match=re.compile('"title": "(.+?)"', re.DOTALL).findall(entry)
                title=match[0]
                match=re.compile('"link": "(.+?)"', re.DOTALL).findall(entry)
                url=match[0]
                if "staffel" in title.lower() and "postID=" not in url and "boardID=" not in url:
                  finalUrl=url
                  break
            
            if len(season)==1:
              season="0"+season
            
            if finalUrl!="":
              threadID = finalUrl[finalUrl.find("&threadID=")+10:]
              if "&" in threadID:
                  threadID = threadID[:threadID.find("&")]
              content = opener.open("http://www.subcentral.de/index.php?page=Thread&threadID="+threadID).read()
              if 'class="bedankhinweisSC' in content:
                contentThanks=content
                contentThanks=contentThanks[contentThanks.find('class="bedankhinweisSC'):]
                match=re.compile('href="index.php\\?action=Thank(.+?)"', re.DOTALL).findall(contentThanks)
                matchID=re.compile('name="threadID" value="(.+?)"', re.DOTALL).findall(contentThanks)
                dialog = xbmcgui.Dialog()
                nr=dialog.select(title, [translation(30005)+"..."])
                if nr>=0:
                  opener.open(mainUrl+"/index.php?action=Thank"+match[0].replace("&amp;","&"))
                  content = opener.open(mainUrl+"/index.php?page=Thread&threadID="+matchID[0]).read()
              
              attachments = []
              titles = []
              
              match=re.compile('<title>(.+?)-', re.DOTALL).findall(content)
              tvShowTitle=match[0].replace("[Subs]","").strip()
              
              content = content[content.find("quoteData.set('post-")+1:]
              content = content[:content.find("quoteData.set('post-")]
              contentDE=content
              contentEN=""
              if '<img src="creative/bilder/flags/usa.png"' in content:
                contentDE=content[:content.find('<img src="creative/bilder/flags/usa.png"')]
                contentEN=content[content.find('<img src="creative/bilder/flags/usa.png"'):]
              elif '<img src="creative/bilder/flags/uk.png"' in content:
                contentDE=content[:content.find('<img src="creative/bilder/flags/uk.png"')]
                contentEN=content[content.find('<img src="creative/bilder/flags/uk.png"'):]
              elif '<img src="creative/bilder/flags/ca.png"' in content:
                contentDE=content[:content.find('<img src="creative/bilder/flags/ca.png"')]
                contentEN=content[content.find('<img src="creative/bilder/flags/ca.png"'):]
              elif '<img src="creative/bilder/flags/de.png"' in content:
                contentDE=content[content.find('<img src="creative/bilder/flags/de.png"')]
                contentEN=content[:content.find('<img src="creative/bilder/flags/de.png"'):]
              
              if language=="0":
                tempDE=appendSubInfo(tvShowTitle,season,episode,release,contentDE,"DE")
                attachments += tempDE[0]
                titles += tempDE[1]
                if contentEN!="":
                  tempEN=appendSubInfo(tvShowTitle,season,episode,release,contentEN,"EN")
                  attachments += tempEN[0]
                  titles += tempEN[1]
              elif language=="1":
                tempDE=appendSubInfo(tvShowTitle,season,episode,release,contentDE,"DE")
                attachments += tempDE[0]
                titles += tempDE[1]
              elif language=="2" and contentEN!="":
                tempEN=appendSubInfo(tvShowTitle,season,episode,release,contentEN,"EN")
                attachments += tempEN[0]
                titles += tempEN[1]
              
              if len(titles)>0:
                titles, attachments = (list(x) for x in zip(*sorted(zip(titles, attachments))))
              dialog = xbmcgui.Dialog()
              nr=dialog.select(os.path.basename(currentFile), titles)
              if nr>=0:
                subUrl=mainUrl+"/index.php?page=Attachment&attachmentID="+attachments[nr]
                setSubtitle(subUrl)
              elif backNav=="true":
                main()
            else:
              xbmc.executebuiltin('XBMC.Notification(SubCentral.de:,'+translation(30015)+'!,3000,'+icon+')')
              main()
          elif '"totalResults": "0"' in content:
            xbmc.executebuiltin('XBMC.Notification(SubCentral.de:,'+translation(30015)+'!,3000,'+icon+')')
            main()
          else:
            xbmc.executebuiltin('XBMC.Notification(SubCentral.de:,'+translation(30016)+'!,10000,'+icon+')')
            main()

def getEpisodes(entry):
        if debuging=="true":
          xbmc.log("Subcentral: Starte GetEpisodes")
        ep=ep2=""
        match=re.compile('>E(.+?) -', re.DOTALL).findall(entry,0,10)
        match2=re.compile('>(.+?)x(.+?) -', re.DOTALL).findall(entry,0,10)
        match3=re.compile('>(.+?)\\. ', re.DOTALL).findall(entry,0,10)
        match4=re.compile('>(.+?) -', re.DOTALL).findall(entry,0,10)
        match5=re.compile('>(.+?)<', re.DOTALL).findall(entry,0,10)
        if "- komplett<" in entry.lower():
          ep=ep2=" - Komplett"
        else:
          if len(match)>0:
            ep=match[0]
          elif len(match2):
            ep=match2[0][1]
          elif len(match3):
            ep=match3[0]
          elif len(match4):
            ep=match4[0]
          elif len(match5):
            ep=match5[0]
          else:
            ep="00"
          ep2="E"+ep
        return [ep,ep2]

def appendSubInfo(tvShowTitle,season,episode,release,content,lang):
        if debuging=="true":
          xbmc.log("Subcentral: AppendSubinfo")
        attachments1 = []
        titles1 = []
        content2=content.replace('<span class="&nbsp; Stil36 Stil31">','').replace('<span class="Stil37">','')
        match=re.compile('<div align="center"><a href="http://www.subcentral.de/index.php\\?page=Attachment&attachmentID=(.+?)">▪ E(.+?) \\((.+?)\\)</a>', re.DOTALL).findall(content2)
        for attach, ep, rel in match:
          ep2="E"+ep
          if episode==ep:
            check = release==""
            if release!="":
              check = release==rel.lower()
            if check:
              if attach not in attachments1:
                attachments1.append(attach)
                titles1.append(lang+" - "+tvShowTitle+" - S"+season+ep2+" - "+rel.replace("</span>",""))
        if len(attachments1)==0:
          match=re.compile('<div align="center"><a href="http://www.subcentral.de/index.php\\?page=Attachment&attachmentID=(.+?)">▪ E(.+?) \\((.+?)\\)</a>', re.DOTALL).findall(content2)
          for attach, ep, rel in match:
            ep2="E"+ep
            if episode==ep:
              if attach not in attachments1:
                attachments1.append(attach)
                titles1.append(lang+" - "+tvShowTitle+" - S"+season+ep2+" - "+rel.replace("</span>",""))
        if len(attachments1)==0:
          match=re.compile('<div align="center"><a href="http://www.subcentral.de/index.php\\?page=Attachment&attachmentID=(.+?)">▪ E(.+?) \\((.+?)\\)</a>', re.DOTALL).findall(content2)
          for attach, ep, rel in match:
            ep2="E"+ep
            if attach not in attachments1:
              attachments1.append(attach)
              titles1.append(lang+" - "+tvShowTitle+" - S"+season+ep2+" - "+rel.replace("</span>",""))
        attachments2 = []
        titles2 = []
        splitStr = ""
        if 'class="release"' in content:
          splitStr = 'class="release"'
        elif 'class="Stil9"' in content:
          splitStr = 'class="Stil9"'
        if splitStr:
          spl=content.split(splitStr)
          for i in range(1,len(spl),1):
            entry=spl[i].replace("<strong>","").replace("</strong>","").replace('<span style="font-size: 8pt">','')
            temp = getEpisodes(entry)
            ep = temp[0]
            ep2 = temp[1]
            match=re.compile('index.php\\?page=Attachment&attachmentID=(.+?)">(.+?)</a>', re.DOTALL).findall(entry)
            for attach, rel in match:
              if episode==ep:
                check = release==""
                if release!="":
                  check = release==rel.lower()
                if check:
                  if attach not in attachments2:
                    attachments2.append(attach)
                    titles2.append(lang+" - "+tvShowTitle+" - S"+season+ep2+" - "+rel.replace("</span>",""))
          if len(attachments2)==0:
            spl=content.split(splitStr)
            for i in range(1,len(spl),1):
              entry=spl[i].replace("<strong>","").replace("</strong>","").replace('<span style="font-size: 8pt">','')
              temp = getEpisodes(entry)
              ep = temp[0]
              ep2 = temp[1]
              match=re.compile('index.php\\?page=Attachment&attachmentID=(.+?)">(.+?)</a>', re.DOTALL).findall(entry)
              for attach, rel in match:
                if episode==ep:
                  if attach not in attachments2:
                    attachments2.append(attach)
                    titles2.append(lang+" - "+tvShowTitle+" - S"+season+ep2+" - "+rel.replace("</span>",""))
          if len(attachments2)==0:
            spl=content.split(splitStr)
            for i in range(1,len(spl),1):
              entry=spl[i].replace("<strong>","").replace("</strong>","").replace('<span style="font-size: 8pt">','')
              temp = getEpisodes(entry)
              ep = temp[0]
              ep2 = temp[1]
              match=re.compile('index.php\\?page=Attachment&attachmentID=(.+?)">(.+?)</a>', re.DOTALL).findall(entry)
              for attach, rel in match:
                if attach not in attachments2:
                  attachments2.append(attach)
                  titles2.append(lang+" - "+tvShowTitle+" - S"+season+ep2+" - "+rel.replace("</span>",""))
        return [attachments1+attachments2,titles1+titles2]

def showFavourites():
        if debuging=="true":
          xbmc.log("Subcentral: Starte ShowFavourites")
        ids = []
        titles = []
        counter = 0
        if os.path.exists(favFile):
          fh = open(favFile, 'r')
          for line in fh:
            id = line[:line.find("#")]
            title = line[line.find("#")+1:]
            title = title[:title.find("#END")]
            ids.append(id)
            titles.append(title)
            counter=counter+1
          fh.close()
        if (counter > 0):
         titles, ids = (list(x) for x in zip(*sorted(zip(titles, ids))))
         dialog = xbmcgui.Dialog()
         nr=dialog.select(translation(30001), titles)
         if nr>=0:
           id=ids[nr]
           title=titles[nr]
           showSeries(id)
         elif backNav=="true":
           main()
        else:
		  dialog2 = xbmcgui.Dialog()
		  nr=dialog2.select(translation(30108), [translation(30108)])
		  main()

def showAllSeries():
        if debuging=="true":
          xbmc.log("Subcentral: Starte ShowAllSeries")
        content = opener.open(mainUrl+"/index.php").read()
        content = content[content.find('<option value=""> Serien QuickJump </option>')+1:]
        content = content[:content.find('</form>')]
        match=re.compile('<option value="([0-9]+?)">([^<>]+?)</option>', re.DOTALL).findall(content)
        threadIDs = []
        threadNames = []
        for id, title in match:
          threadIDs.append(id)
          threadNames.append(title)
        dialog = xbmcgui.Dialog()
        nr=dialog.select(translation(30002), threadNames)
        if nr>=0:
          id=threadIDs[nr]
          title=threadNames[nr]
          showSeries(id)
        elif backNav=="true":
          main()

def showSeries(seriesID):
        if debuging=="true":
          xbmc.log("Subcentral: Start showSeries")
        content = opener.open(mainUrl+"/index.php?page=Board&boardID="+seriesID).read()
        match=re.compile('<title>(.+?) -', re.DOTALL).findall(content)
        SeriesTitle=match[0]
        content = content[content.find("<h3>Wichtige Themen</h3>"):]
        content = content[:content.find('</table>')]
        spl=content.split('<p id="threadTitle')
        threadIDs = []
        threadNames = []
        season=currentSeason
        if season[0:1]=="0":
          season=season[1:]

        for i in range(1,len(spl),1):
          entry=spl[i]
          match=re.compile('<a href="index.php\\?page=Thread&amp;threadID=(.+?)">(.+?)</a>', re.DOTALL).findall(entry)
          if ("staffel "+season in match[0][1].lower() or "staffel 0"+season in match[0][1].lower()) and "subs" in match[0][1].lower():
            threadIDs.append(match[0][0])
            threadNames.append(cleanTitle(match[0][1]))
        if len(threadIDs)==0:
          for i in range(1,len(spl),1):
            entry=spl[i]
            match=re.compile('<a href="index.php\\?page=Thread&amp;threadID=(.+?)">(.+?)</a>', re.DOTALL).findall(entry)
            if "subs" in match[0][1].lower():
              threadIDs.append(match[0][0])
              threadNames.append(cleanTitle(match[0][1]))
        threadNames, threadIDs = (list(x) for x in zip(*sorted(zip(threadNames, threadIDs))))
        content=""
        if os.path.exists(favFile):
          fh = open(favFile, 'r')
          content=fh.read()
          fh.close()
        if seriesID+"#" not in content:
          threadNames.append(translation(30003))
        else:
          threadNames.append(translation(30004))
        dialog = xbmcgui.Dialog()
        nr=dialog.select(os.path.basename(currentFile), threadNames)
        if nr>=0:
          if nr==len(threadNames)-1:
            if threadNames[nr]==translation(30003):
              addToFavourites(seriesID,SeriesTitle)
            elif threadNames[nr]==translation(30004):
              removeFromFavourites(seriesID,SeriesTitle)
            showSeries(seriesID)
          else:
            id=threadIDs[nr]
            showSubtitles(seriesID,id)
        elif backNav=="true":
          if mainType=="all":
            showAllSeries()
          elif mainType=="fav":
            showFavourites()

def showSubtitles(seriesID,id):
        if debuging=="true":
          xbmc.log("Subcentral: Starte showSubtitles")
        content = opener.open(mainUrl+"/index.php?page=Thread&threadID="+id).read()
        match=re.compile('<title>(.+?)</title>', re.DOTALL).findall(content)
        title=match[0]
        if 'class="bedankhinweisSC' in content:
          contentThanks=content
          contentThanks=contentThanks[contentThanks.find('class="bedankhinweisSC'):]
          match=re.compile('href="index.php\\?action=Thank(.+?)"', re.DOTALL).findall(contentThanks)
          matchID=re.compile('name="threadID" value="(.+?)"', re.DOTALL).findall(contentThanks)
          dialog = xbmcgui.Dialog()
          nr=dialog.select(title, [translation(30005)+"..."])
          if nr>=0:
            opener.open(mainUrl+"/index.php?action=Thank"+match[0].replace("&amp;","&"))
            content = opener.open(mainUrl+"/index.php?page=Thread&threadID="+id).read()
          elif backNav=="true":
            showSeries(seriesID)
        attachments = []
        titles = []
        
        match=re.compile('<title>(.+?)-', re.DOTALL).findall(content)
        tvShowTitle=match[0].replace("[Subs]","").strip()
        match=re.compile('Staffel (.+?) ', re.DOTALL).findall(content)
        season=match[0]
        if len(season)==1:
          season="0"+season
        
        content = content[content.find("quoteData.set('post-")+1:]
        content = content[:content.find("quoteData.set('post-")]
        contentDE=content
        contentEN=""
        if '<img src="creative/bilder/flags/usa.png"' in content:
          contentDE=content[:content.find('<img src="creative/bilder/flags/usa.png"')]
          contentEN=content[content.find('<img src="creative/bilder/flags/usa.png"'):]
        elif '<img src="creative/bilder/flags/uk.png"' in content:
          contentDE=content[:content.find('<img src="creative/bilder/flags/uk.png"')]
          contentEN=content[content.find('<img src="creative/bilder/flags/uk.png"'):]
        elif '<img src="creative/bilder/flags/ca.png"' in content:
          contentDE=content[:content.find('<img src="creative/bilder/flags/ca.png"')]
          contentEN=content[content.find('<img src="creative/bilder/flags/ca.png"'):]
        elif '<img src="creative/bilder/flags/de.png"' in content:
          contentDE=content[content.find('<img src="creative/bilder/flags/de.png"')]
          contentEN=content[:content.find('<img src="creative/bilder/flags/de.png"'):]
        
        if language=="0":
          tempDE=appendSubInfo(tvShowTitle,season,currentEpisode,currentRelease,contentDE,"DE")
          attachments += tempDE[0]
          titles += tempDE[1]
          if contentEN!="":
            tempEN=appendSubInfo(tvShowTitle,season,currentEpisode,currentRelease,contentEN,"EN")
            attachments += tempEN[0]
            titles += tempEN[1]
        elif language=="1":
          tempDE=appendSubInfo(tvShowTitle,season,currentEpisode,currentRelease,contentDE,"DE")
          attachments += tempDE[0]
          titles += tempDE[1]
        elif language=="2" and contentEN!="":
          tempEN=appendSubInfo(tvShowTitle,season,currentEpisode,currentRelease,contentEN,"EN")
          attachments += tempEN[0]
          titles += tempEN[1]
        
        if len(titles)>0:
          titles, attachments = (list(x) for x in zip(*sorted(zip(titles, attachments))))
        dialog = xbmcgui.Dialog()
        nr=dialog.select(os.path.basename(currentFile), titles)
        if nr>=0:
          subUrl=mainUrl+"/index.php?page=Attachment&attachmentID="+attachments[nr]
          setSubtitle(subUrl)
        elif backNav=="true":
          showSeries(seriesID)

def setSubtitle(subUrl):
        if debuging=="true":
          xbmc.log("Subcentral: Starte setSubtitle")
        global subFile
        clearSubTempDir()
        rarContent = opener.open(subUrl).read()
        if rarContent.startswith("Rar"):
          ext="rar"
        else:
          ext="zip"
        global rarFile
        rarFile=rarFile+ext
        fh = open(rarFile, 'wb')
        fh.write(rarContent)
        fh.close()
        xbmc.executebuiltin("XBMC.Extract("+rarFile+", "+subTempDir+")",True)
        files = os.listdir(subTempDir)
        tempFile=""
        if len(files)>1:
          dialog = xbmcgui.Dialog()
          nr=dialog.select(currentTitle, files)
          if nr>=0:
            tempFile = xbmc.translatePath(subTempDir+"/"+files[nr])
          else:
            clearSubTempDir()
            if backNav=="true":
              main()
        elif len(files)!=0:
          tempFile = xbmc.translatePath(subTempDir+"/"+files[0])
        else:
          xbmc.executebuiltin('XBMC.Notification(SubCentral.de:,'+translation(30017)+'!,3000,'+icon+')')
          if pause=="true" and xbmc.Player().isPlayingVideo():
            xbmc.Player().pause()
        if tempFile!="":
          shutil.copyfile(tempFile, subFile)
          if saveSub=="true" and "http://" not in currentFile and "plugin://" not in currentFile:
            try:
              extLength = len(currentFile.split(".")[-1])
              archiveFile = currentFile[:-extLength]+"srt"
              xbmcvfs.copy(tempFile, archiveFile)
              subFile = archiveFile
            except:
              pass
          clearSubTempDir()
          xbmc.Player().setSubtitles(subFile)
          xbmc.executebuiltin('XBMC.Notification(SubCentral.de:,'+translation(30012)+'!,2000,'+icon+')')
          if pause=="true" and xbmc.Player().isPlayingVideo():
            xbmc.Player().pause()

def clearSubTempDir():
        if debuging=="true":
          xbmc.log("Subcentral: Starte clearSubTempdir")
        files = os.listdir(subTempDir)
        for file in files:
          try:
            os.remove(xbmc.translatePath(subTempDir+"/"+file))
          except:
            pass

def addToFavourites(seriesID,title):
        if debuging=="true":
          xbmc.log("Subcentral: Starte addToFavourites")
        entry=seriesID+"#"+title+"#END"
        if os.path.exists(favFile):
          fh = open(favFile, 'r')
          content=fh.read()
          fh.close()
          if entry not in content:
            fh=open(favFile, 'a')
            fh.write(entry+"\n")
            fh.close()
            xbmc.executebuiltin('XBMC.Notification(SubCentral.de:,'+title+': '+translation(30008)+',3000,'+icon+')')
        else:
          fh=open(favFile, 'a')
          fh.write(entry+"\n")
          fh.close()

def removeFromFavourites(seriesID,title):
        if debuging=="true":
          xbmc.log("Subcentral: removeFromFavourites")
        newContent=""
        fh = open(favFile, 'r')
        for line in fh:
          if seriesID+"#" not in line:
             newContent+=line
        fh.close()
        fh=open(favFile, 'w')
        fh.write(newContent)
        fh.close()
        xbmc.executebuiltin('XBMC.Notification(SubCentral.de:,'+title+': '+translation(30009)+',3000,'+icon+')')

def getUrl(url):
        if debuging=="true":
          xbmc.log("Subcentral: Get Url")
        req = urllib2.Request(url)
        req.add_header('User-Agent', 'Mozilla/5.0 (Windows NT 6.1; rv:23.0) Gecko/20100101 Firefox/23.0')
        response = urllib2.urlopen(req)
        content=response.read()
        response.close()
        return content

def cleanTitle(title):
        if debuging=="true":
          xbmc.log("Subcentral: cleanTitle")
        title=title.replace("&lt;","<").replace("&gt;",">").replace("&amp;","&").replace("&#039;","'").replace("&quot;","\"").replace("&szlig;","ß").replace("&ndash;","-")
        title=title.replace("&Auml;","Ä").replace("&Uuml;","Ü").replace("&Ouml;","Ö").replace("&auml;","ä").replace("&uuml;","ü").replace("&ouml;","ö")
        title=title.strip()
        return title

main()
