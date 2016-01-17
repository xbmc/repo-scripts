# -*- coding: utf-8 -*-

import os
import shutil
import sys
import urllib
import xbmc
import xbmcaddon
import xbmcgui,xbmcplugin
import xbmcvfs
import urllib2, socket, cookielib, re, os, shutil
import cookielib, json


# Globals
addon = xbmcaddon.Addon()
base_url = sys.argv[0]
addon_handle = int(sys.argv[1])
addonID = addon.getAddonInfo('id')
translation = addon.getLocalizedString
profile    = xbmc.translatePath( addon.getAddonInfo('profile') ).decode("utf-8")
temp       = xbmc.translatePath( os.path.join( profile, 'temp', '') ).decode("utf-8")
cwd        = xbmc.translatePath( addon.getAddonInfo('path') ).decode("utf-8")
resource   = xbmc.translatePath( os.path.join( cwd, 'resources', 'lib' ) ).decode("utf-8")
icon = xbmc.translatePath('special://home/addons/'+addonID+'/icon.png')
subdir=xbmc.translatePath( os.path.join( temp, 'subs', '') ).decode("utf-8")
subdownload=xbmc.translatePath( os.path.join( temp, 'download', '') ).decode("utf-8")
subtitlefile="subcentral"
global cj
cj = cookielib.CookieJar()
mainUrl="https://www.subcentral.de"



# Anlegen von Directorys
if xbmcvfs.exists(subdir):
  shutil.rmtree(subdir)
xbmcvfs.mkdirs(subdir)

if xbmcvfs.exists(subdownload):
  shutil.rmtree(subdownload)
xbmcvfs.mkdirs(subdownload)


if xbmcvfs.exists(temp):
  shutil.rmtree(temp)

xbmcvfs.mkdirs(temp)
xbmcvfs.mkdirs(subdir)
xbmcvfs.mkdirs(subdownload)

# Logging
def debug(content):
    log(content, xbmc.LOGDEBUG)
    
def notice(content):
    log(content, xbmc.LOGNOTICE)

def log(msg, level=xbmc.LOGNOTICE):
    addon = xbmcaddon.Addon()
    addonID = addon.getAddonInfo('id')
    xbmc.log('%s: %s' % (addonID, msg), level) 

def ersetze(inhalt):
   inhalt=inhalt.replace('&#39;','\'')  
   inhalt=inhalt.replace('&quot;','"')    
   inhalt=inhalt.replace('&gt;','>')      
   inhalt=inhalt.replace('&amp;','&') 
   return inhalt
    
# Einstellungen Lesen    
def getSettings():
  global user
  user=addon.getSetting("user")
  global pw
  pw=addon.getSetting("pw")
  global backNav

# Url Parameter Einlesen  
def get_params(string=""):
  param=[]
  if string == "":
    paramstring=sys.argv[2]
  else:
    paramstring=string
  if len(paramstring)>=2:
    params=paramstring
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

# Einloggen  
def login():
  debug("Starte Login")  
  xy=getUrl(mainUrl+"/index.php?form=UserLogin", data="loginUsername="+urllib.quote_plus(user)+"&loginPassword="+urllib.quote_plus(pw))
  
# Url einlesen  
def getUrl(url,data="X"):
        url=url.replace("http://www.subcentral.de/","")        
        url=url.replace("https://www.subcentral.de/https://www.subcentral.de/","https://www.subcentral.de/")        
        debug("Subcentral: Get Url: " +url)
        opener = urllib2.build_opener(urllib2.HTTPCookieProcessor(cj))
        userAgent = "Mozilla/5.0 (Windows NT 6.2; WOW64; rv:23.0) Gecko/20100101 Firefox/23.0"
        opener.addheaders = [('User-Agent', userAgent)]
        if data!="x" :
          content=opener.open(url,data=data).read()         
        else:
          content=opener.open(url).read() 
        opener.close()
        return content

        # Titel Beeinigen
def clean_serie(title):
        title=title.lower().replace('the ','') 
        title=title.replace('.','')
        title=title.replace("'","")
        title=title.replace("&amp;","")
        return title

# Liste Aller Serien Holen        
def lies_serien():
        debug("Subcentral: Starte ShowAllSeries")
        content = getUrl(mainUrl+"/index.php")
        content = content[content.find('<option value=""> Serien-QuickJump </option>')+1:]
        content = content[:content.find('</form>')]
        # Serie Suchen
        match=re.compile('<option value="([0-9]+?)">([^<>]+?)</option>', re.DOTALL).findall(content)
        threadIDs = []
        threadNames = []
        threadNamesclean = []
        for id, title in match:
          threadIDs.append(id)
          # Clean wird gebraucht damit "The und ohen The Serien Matchen"
          threadNamesclean.append(clean_serie(title))   
          threadNames.append(ersetze(title)) 
        threadIDs, threadNames,threadNamesclean = (list(x) for x in zip(*sorted(zip(threadNames, threadIDs,threadNamesclean))))
        return threadIDs, threadNames,threadNamesclean

      
# Einlesen der Alten Threads    
def oldthread(url,staffel,old=1):
    debug("Starte oldtread mit : "+ url +" staffel "+ str(staffel) + " old "+str(old))
    episode_ar=[]
    name_ar=[]
    file_ar=[]
    gruppe_ar=[]
    sprache_ar=[]
    folge_ar=[]
    qualitaet_ar=[]
    content=getUrl(url)
    contentx = content[content.find('<!-- /Imformationsmodul -->'):]        
    if len(contentx)>10:
      content=contentx
    else:
       content = content[content.find('<!-- Hier Bilderserie (Bilder-Modul) einfügen. [Optinal] -->'):]    
    debug("________"+ content)
    content = content[content.find('<div class="baseSC">'):]
    content = content[:content.find('<div class="bhinweis">')]
    content = content[:content.find('<div class="txtb afgtxtb">')]
    if old==1:
      spl = content.split('<!-- Spaltenbreite (und -gruppierung) - Nur einmal pro Tabellen-Modul -->')
    else:
       spl = content.split('<div class="baseSC">')
    gefunden=0
    for i in range(1, len(spl), 1):
       
       element=spl[i]         
       #HEADER
       header=element[element.find('<thead>')+1:]
       header = header[:header.find('</thead>')]
       h1 = header.split('<th')
       namenliste= []
       sprache=""
       for i2 in range(2, len(h1), 1):         
         ele=h1[i2]             
         if "creative/bilder/flags/usa.png" in ele or "creative/bilder/flags/ca.png" in ele or "creative/bilder/flags/uk.png" in ele:
             sprache="en"
         if "creative/bilder/flags/de.png" in ele  :
             sprache="de"             
         subn=re.compile('>([^<]+)<', re.DOTALL).findall(ele)
         subname=subn[0]                               
         namenliste.append(subname)
       if(old==0):
         if "<h2>Englische Untertitel:</h2>" in element:
            sprache="en"
         if "<h2>Deutsche Untertitel:</h2>" in element:
             sprache="de"        
       #SUBS
       subs_element=element[element.find('<!-- /Zeilen-Modul - Titel -->')+1:]
       subs_element = subs_element[:subs_element.find('<!-- /Tabellen-Modul -->')]
       zeilen = subs_element.split('<tr')
       
       for zeile in range(1, len(zeilen), 1):              
           z_elemet=zeilen[zeile]
           spalten = z_elemet.split('<td')
           for spalte in range(0, len(spalten)-1, 1):                
             s_element=spalten[spalte]                 
             name_array=re.compile('class="release">([^<]+)<', re.DOTALL).findall(s_element)                             
             if name_array:               
               name=name_array[0]
             file=""
             gruppe="" 
             sub_array=re.compile('<a href="([^"]+)">([^<]+)', re.DOTALL).findall(s_element)             
             if sub_array:
               for file,gruppe in sub_array:              
                     
                  folge_extract=re.compile('E([0-9]+) -.*', re.DOTALL).findall(name)     
                  if(folge_extract) :
                     folgee_nr=int(folge_extract[0])
                  else :
                      folge_extract=re.compile('([^-]+) -.*', re.DOTALL).findall(name)
                      folgee_nr=folge_extract[0]
                  episode_ar.append(folgee_nr)
                  name_ar.append(name)
                  file_ar.append(mainUrl+"/"+file)
                  gruppe_ar.append(gruppe)
                  sprache_ar.append(sprache)                  
                  folge_ar.append(folgee_nr)
                  if video['episode']:
                    if int(video['episode'])==folgee_nr:
                      gefunden=1
                  debug("-------")
                  debug("Liste :" +str(i))
                  debug("gruppe :"+gruppe)
                  debug("Folge: "+ str(folgee_nr))
                  debug("Sprache: "+ sprache)
                  debug("file : "+ file)
                  debug("name: "+ name)                  
                  debug("gefunden: "+ str(gefunden))
                  debug("spalte :" +str(spalte))
                  debug(namenliste)
                  debug("Qualitaet: "+namenliste[spalte-2])
                  debug(sub_array)
                  qualitaet_ar.append(namenliste[spalte-2])
    folge_ar,sprache_ar,qualitaet_ar,gruppe_ar,file_ar = (list(x) for x in zip(*sorted(zip(folge_ar,sprache_ar,qualitaet_ar,gruppe_ar,file_ar))))                             
    for folgenr in range(0, len(folge_ar), 1):
#      debug("+++++++++++++++")
#      debug("gruppe_ar[folgenr] "+ gruppe_ar[folgenr])
#      debug("str(folge_ar[folgenr]) "+ str(folge_ar[folgenr]))
#      debug("sprache_ar[folgenr] "+ sprache_ar[folgenr])
#      debug("qualitaet_ar[folgenr] "+ qualitaet_ar[folgenr])
#      debug("gefunden "+ str(gefunden))
      if gefunden == 1 :
         if int(video['episode'])==folge_ar[folgenr] :
           addLink( "Staffel "+ str(staffel) + " Folge "+ str(folge_ar[folgenr])+ " "+ gruppe_ar[folgenr]+" ( "+ qualitaet_ar[folgenr] + " ) ", file_ar[folgenr], "download", "", duration="", desc="", genre='',lang=sprache_ar[folgenr])                  
      else:
         addLink( "Staffel "+ str(staffel) + " Folge "+ str(folge_ar[folgenr])+ " "+ gruppe_ar[folgenr]+" ( "+ qualitaet_ar[folgenr] + " ) ", file_ar[folgenr], "download", "", duration="", desc="", genre='',lang=sprache_ar[folgenr])             
    xbmcplugin.endOfDirectory(addon_handle)
    

    
# Einen Link Erzeugen
def addLink(name, url, mode, icon="", duration="", desc="", genre='',lang=""):
  u = sys.argv[0]+"?url="+urllib.quote_plus(url)+"&mode="+str(mode)
  ok = True
  iconl=""
  if lang=="de":
    sprache=translation(30110)
    iconl="de"
  if lang=="en":
    sprache=translation(30111)
    iconl="en"
  liz = xbmcgui.ListItem(label2=name,thumbnailImage=iconl,label=sprache)
  debug("ICONXXX:'"+icon+"'")
  ok = xbmcplugin.addDirectoryItem(handle=int(sys.argv[1]), url=u, listitem=liz)
  return ok
  


# Alle Folgen  Holen je nachdem ob englisch oder Deutsch
def list_folgen(url,staffel):
  debug("list_folgen: "+ url)
  content=getUrl(url)    
  if '<blockquote class="bedankhinweisSC quoteBox hide">' in content:
                dialog = xbmcgui.Dialog()
                nr=dialog.select("Bedanken", ["Bedanken"+"..."])
                debug("NR :"+str(nr))
                if nr>=0:
                    contentThanks=content
                    match=re.compile("SID_ARG_2ND	= '([^']*)';", re.DOTALL).findall(contentThanks)
                    arg2=match[0]
                    match=re.compile("SECURITY_TOKEN = '([^']*)';", re.DOTALL).findall(contentThanks)
                    stoken=match[0]
                    match=re.compile('objectID: ([0-9]+),', re.DOTALL).findall(contentThanks)
                    threadid=match[0]
                    
                    #<script type="text/javascript">thankOmat.showHideThankUser(178392);</script>
                    urln=mainUrl+"/index.php?action=Thank&output=xml&postID=" +threadid+ "&t=" +stoken +  arg2
                    debug("URL DANKE:"+ urln)
                    data=getUrl(urln)
                    debug("++++\n"+ data)
                    content=getUrl(url)
  if "reative/bilder/flags" in content :
     oldthread(url,staffel,1)
  elif "<!-- Englische Untertitel -->" in content or "<h2>Englische Untertitel:</h2>" in content:
    oldthread(url,staffel,0)
  else :
     oldthread(url,staffel,1)
    

# Alle Staffeln Holen    
def get_staffeln(id):
    debug("Hole Staffeln")
    serienpage=mainUrl+"/index.php?page=Board&boardID="+id
    debug("get_staffeln URL:"+ serienpage)
    content=getUrl(serienpage)
    content = content[content.find('<h3>Wichtige Themen</h3>')+1:]
    content = content[:content.find('</table>')]
    linklist= []
    staffellist=[]
    gefunden=0
    spl = content.split('<div class="statusDisplayIcons">')
    for i in range(0, len(spl), 1):
        entry = spl[i]
        if "<strong>[Subs]</strong>" in entry :
           entry = entry[entry.find('<p id="threadTitl')+1:]
           entry = entry[:entry.find('</p>')]
           match = re.compile('<a href="([^"]+)">(.+)[\ ]+-[\ ]+Staffel ([0-9]+)[^<]+</a>', re.DOTALL).findall(entry)
           for link,dummy,staffel in match:
             debug("L0RE::::: "+ link +"++"+ staffel+":::::::")
             debug("suche staffel:"+ video['season']+"X")
             if video['season']:
                # Wenn Gefunden Lsite für die Staffel alle Folgen
                debug("YYY"+video['season'])
                if int(staffel.strip()) == int( video['season'].strip()):
                    gefunden=1
                    list_folgen(mainUrl+"/"+ersetze(link),int( video['season'].strip())) 
                else :
                    staffellist.append("Staffel "+ staffel)
                    linklist.append(mainUrl+"/"+ersetze(link))
             else :
                 staffellist.append("Staffel "+ staffel)
                 linklist.append(ersetze(link))       
    # Wenn keine Passende Staffel gefunden
    if gefunden==0 :
      staffellist,linklist = (list(x) for x in zip(*sorted(zip(staffellist, linklist))))
      # Zeige Alle Staffeln an
      dialog = xbmcgui.Dialog()
      nr=dialog.select("subcentral.de", staffellist)
      seite=linklist[nr]
      video['season']=staffellist[nr]
      if nr>=0:              
        list_folgen(mainUrl+"/"+seite,staffellist[nr])
                
#Suche  
def search():
  debug("Start search")
  error=0
  # Suche Serie
  serien_complete,ids,serien=lies_serien()
  show=clean_serie(video['tvshow'])
  # Wenn keine Serien Gibt es error=1 anosnten wird die ID rausgesucht
  if not show == '':
    try:
      index=serien.index(show)
      id=ids[index]
      # Hack Wenn man abbricht ist id=0, so wird nr auf 0 gesetzt
      nr=id
      debug("ID : "+ str(id))
    except:
       error=1
  else :
        error=1
  # Wenn keine Serie gefunden
  if error==1:
    dialog = xbmcgui.Dialog()
    nr=dialog.select("subcentral.de", serien_complete)
    id=ids[nr]
   # Nur wenn etwas ausgewählt wurde staffeln anzeigen    
  if nr>=0 :
     get_staffeln(id) 
  
# Hole Infos uir Folge die grade läuft aus Datenbank oder Filename
def resivefile():
  currentFile = xbmc.Player().getPlayingFile()
  try:
     cf=currentFile.replace("\\","/")
     all=cf.split("/")  
     dirName=all[-2].lower()
     fileName=all[-1].lower()
     debug("Dirname: "+dirname)
     debug ("Filename: "+filename)
  except:
     pass
  if video['episode']=="":
    matchDir=re.compile('\\.s([0-9]+?)e([0-9]+?)\\.', re.DOTALL).findall(dirName)
    matchFile=re.compile('\\.s([0-9]+?)e([0-9]+?)\\.', re.DOTALL).findall(fileName)
    if len(matchDir)>0:
      video['season'] =matchDir[0][0]
      video['episode']=matchDir[0][1]
    elif len(matchFile)>0:
      video['season'] =matchFile[0][0]
      video['episode']=matchFile[0][1]
  if video['episode']=="":
      match=re.compile('(.+?)- s(.+?)e(.+?) ', re.DOTALL).findall(xbmc.getInfoLabel('VideoPlayer.Title').lower())
      if len(match)>0:
         video['season']=match[0][1]
         video['episode']=match[0][2]

  video['release']=""
  if "-" in fileName:
     video['release']=(fileName.split("-")[-1]).lower()
  if "." in video['release']:
    video['release']=video['release'][:video['release'].find(".")]
  elif "-" in dirName:
    video['release']=(dirName.split("-")[-1]).lower()
  title=video['tvshow']
  if title=="" or video['season']=="":
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
  video['tvshow']=title

# Parameter einlese  
params = get_params()
getSettings() 

# Alle Temporaeren files loeschen bevor ein neuer Untertitel Kommt
def clearSubTempDir(pfad):

        files = os.listdir(pfad)
        for file in files:
          try:
            os.remove(xbmc.translatePath(pfad+"/"+file))
          except:
            pass
#Neue Untertitel Holen            
def setSubtitle(subUrl):  
        subtitle_list = []    
        debug("SUB: " + subUrl)  
        downloadfile=xbmc.translatePath(subdownload+subtitlefile)
        clearSubTempDir(subdownload)
        clearSubTempDir(subdir)
        rarContent = getUrl(subUrl)
        if rarContent.startswith("Rar"):
          ext="rar"
        else:
          ext="zip"        
        Paket=downloadfile+"."+ext
        debug ("Hole File:" +Paket)
        fh = open(Paket, 'wb')
        fh.write(rarContent)
        fh.close()
        debug("Versuche file zu entpacken in "+ subdir)
        xbmc.executebuiltin("XBMC.Extract("+Paket+", "+subdir+")",True)
        for file in xbmcvfs.listdir(subdir)[1]:
           file = os.path.join(subdir, file)
           subtitle_list.append(file)
        for sub in subtitle_list:
             debug("XXYX: "+ sub)
             listitem = xbmcgui.ListItem(label=sub)
             xbmcplugin.addDirectoryItem(handle=int(sys.argv[1]),url=sub,listitem=listitem,isFolder=False)
        xbmcplugin.endOfDirectory(addon_handle)




# Wenn keine Kennung einegtragen ist diese Verlangen
while (user=="" or pw==""):
  addon.openSettings()
  getSettings()

# STARTZ  
login()
global video
video ={}
video['year']               = xbmc.getInfoLabel("VideoPlayer.Year")                         # Year
video['season']             = str(xbmc.getInfoLabel("VideoPlayer.Season"))                  # Season
video['episode']            = str(xbmc.getInfoLabel("VideoPlayer.Episode"))                 # Episode
video['tvshow']             = xbmc.getInfoLabel("VideoPlayer.TVshowtitle")  # Show
video['title']              = xbmc.getInfoLabel("VideoPlayer.OriginalTitle") # try to get original title
video['file_original_path'] = xbmc.Player().getPlayingFile().decode('utf-8')                 # Full path of a playing file
video['3let_language']      = [] #['scc','eng']
video['release']            = ""
PreferredSub		      = params.get('preferredlanguage')
if video['title'] == "":
    debug(  "tvshow.OriginalTitle not found")
    video['title']  = xbmc.getInfoLabel("VideoPlayer.Title")    # no original title, get just Title
# Fehlende Daten aus File
resivefile()

url = urllib.unquote_plus(params.get('url', ''))  

  

if params['action'] == 'search' :
  search()
    
if params['action'] == 'download' :
  setSubtitle(url)


#xbmc.executebuiltin('runaddon(script.tv4user)')
