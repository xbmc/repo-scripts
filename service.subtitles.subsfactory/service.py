# -*- coding: utf-8 -*-

import os
import sys
import xbmc
from xbmc import log
import urllib
import urllib2
import xbmcvfs
import xbmcaddon
import xbmcgui
import xbmcplugin
import shutil
import unicodedata
from bs4 import BeautifulSoup
import re

addon = xbmcaddon.Addon()
scriptid   = addon.getAddonInfo('id')
scriptname = addon.getAddonInfo('name')
language   = addon.getLocalizedString
profile    = xbmc.translatePath( addon.getAddonInfo('profile') ).decode("utf-8")
temp       = xbmc.translatePath( os.path.join( profile, 'temp','') ).decode("utf-8")

def Search(item):
    if 'ita' in item['3let_language'] and item['tvshow']:
        urlsearch="http://www.subsfactory.it/archivio/?download_search="
        home="http://www.subsfactory.it"
        urlsearch=urlsearch+item['tvshow'].replace(" ","+")+"+"+str(item['season'])+"x"
        if len(item['episode'])==1:
            eps="0"+str(item['episode'])
        else:
            eps=str(item['episode'])
        urlsearch=urlsearch+eps
        page=urllib2.urlopen(urlsearch)
        html=BeautifulSoup(page)
        ul=html.find(id="download-page").find('ul')
        if ul is not None:
            tr=ul.find('table').find('tbody').find_all('tr')
            if tr is not None:
                sublist=[]
                first=0
                for td in tr:
                    if first!=0:
                        a=td.find('td' ,class_='tdleft').find('a')
                        sublist.append([a.contents[0].replace("\n",""),home+a.get('href')])
                    else:
                        first=1
                showlist(sublist)
        else:
            notify(language(32002))
    else:
        notify(language(32001))
        log('Subsfactory only works with italian subs. Skipped')

def checkexp(tvshow):
    exp=[
         ["Marvel's Agents of S.H.I.E.L.D.","Agents of Shield"],
         ["Marvel's Daredevil","Daredevil"],
         ["Marvel's Agent Carter","Agent Carter"],
         ["Doctor Who (2005)","Doctor Who"],
         ["NCIS: Los Angeles","NCIS Los Angeles"],
         ["Castle (2009)","Castle"],
         ["Marvel's Jessica Jones","Jessica Jones"],
         ["The Flash (2014)","The Flash"],
         ["Marvel's Luke Cage","Luke Cage"]]
    for expl in exp:
        if tvshow == expl[0]:
            return expl[1]
    return tvshow

def showlist(list):
    if xbmcvfs.exists(temp):
        shutil.rmtree(temp)
        #log("elimino temp")
    xbmcvfs.mkdirs(temp)
    #log("ricreo temp")
    i=0
    for sub in list:
        log("Fetching subtitles using url %s" % sub[1])
        content= urllib2.urlopen(sub[1]).read()
        si=str(i)
        if content:
            log('File downloaded')
            local_tmp_file = os.path.join(temp, 'subsfactory'+si+'.xxx')
            try:
                log("Saving subtitles to '%s'" % local_tmp_file)
                local_file_handle = open(local_tmp_file, 'wb')
                local_file_handle.write(content)
                local_file_handle.close()
                #Check archive type (rar/zip/else) through the file header (rar=Rar!, zip=PK)
                myfile = open(local_tmp_file, 'rb')
                myfile.seek(0)
                if myfile.read(1) == 'R':
                    typeid = 'rar'
                    packed = True
                    log('Discovered RAR Archive')
                else:
                    myfile.seek(0)
                    if myfile.read(1) == 'P':
                        typeid = 'zip'
                        packed = True
                        log('Discovered ZIP Archive')
                    else:
                        myfile.seek(0)
                        typeid = 'srt'
                        packed = False
                        log('Discovered a non-archive file')
                myfile.close()
                local_tmp_file = os.path.join(temp, 'subsfactory'+si+'.' + typeid)
                os.rename(os.path.join(temp, 'subsfactory'+si+'.xxx'), local_tmp_file)
                log("Saving to %s" % local_tmp_file)
            except:
                #log("Failed to save subtitle to %s" % local_tmp_file)
                return []
            if packed:
                xbmc.sleep(500)
                dirtemp=temp+"unpack"+si
                #log("dirtemp %s "%dirtemp)
                if not os.path.exists(dirtemp):
                    os.makedirs(dirtemp)
                else:
                    shutil.rmtree(dirtemp)
                    os.makedirs(dirtemp)
                xbmc.executebuiltin(('XBMC.Extract(' + local_tmp_file + ',' + dirtemp +')').encode('utf-8'), True)
                dirs = os.listdir(dirtemp)
                for file in dirs:
                    path_rec=os.path.join(dirtemp,file)
                    if (os.path.isdir(path_rec)):
                        dirs_rec = os.listdir(path_rec)
                        for file_rec in dirs_rec:
                            filen=cleanName(file_rec)
                            url = "plugin://%s/?action=download&file=%s&type=%s&si=%s" % (scriptid,os.path.join(file,file_rec),"pack",si)
                            xbmcplugin.addDirectoryItem(handle=int(sys.argv[1]),url=url,listitem=make_listItem(filen),isFolder=False)
                    else:
                        filen=cleanName(file)
                        url = "plugin://%s/?action=download&file=%s&type=%s&si=%s" % (scriptid,file,"pack",si)
                        xbmcplugin.addDirectoryItem(handle=int(sys.argv[1]),url=url,listitem=make_listItem(filen),isFolder=False)
            else:
                url = "plugin://%s/?action=download&file=%s&type=%s&si=no" % (scriptid,local_tmp_file,"unpack")
                xbmcplugin.addDirectoryItem(handle=int(sys.argv[1]),url=url,listitem=make_listItem(sub[0]),isFolder=False)
        i=i+1

def make_listItem(filen):
    listitem = xbmcgui.ListItem(label="Italian",label2=filen,thumbnailImage='it')
    listitem.setProperty( "sync",'false')
    listitem.setProperty('hearing_imp', 'false')
    return listitem

def cleanName(file):
    filen=file.replace(".srt","")
    filen=filen.replace("sub.ita","")
    filen=filen.replace("subsfactory","")
    filen=filen.replace("Subsfactory","")
    filen=filen.replace("."," ")
    filen=filen.replace("_"," ")
    return filen

def Download(link,type,si):
    subtitle_list=[]
    if type=="pack" and si!="no":
        dirtemp=temp+"unpack"+si+"\\"
        link=os.path.join(dirtemp,link)
    subtitle_list.append(link)
    return subtitle_list

def notify(msg):
    xbmc.executebuiltin((u'Notification(%s,%s)' % (scriptname , msg)).encode('utf-8'))

def normalizeString(str):
  return unicodedata.normalize(
         'NFKD', unicode(unicode(str, 'utf-8'))
         ).encode('ascii','ignore')

def parseSearchString(str):
    res=re.findall('(.*\d*?) s?0?(\d{1,3})x?e?0?(\d{1,3})', urllib.unquote(str), re.IGNORECASE)
    item={}
    if res:
        item['tvshow']=res[0][0]
        item['tvshow']=checkexp(item['tvshow'])
        lres=len(item['tvshow'])
        if item['tvshow'][lres-1:lres]!=" ":
            item['tvshow']=item['tvshow']+" "
        item['season']=res[0][1]
        item['episode']=res[0][2]
    return item

def get_params():
  param=[]
  paramstring=sys.argv[2]
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

params = get_params()

if params['action'] == 'search':
  item = {}
  item['season']             = str(xbmc.getInfoLabel("VideoPlayer.Season"))                    # Season
  item['episode']            = str(xbmc.getInfoLabel("VideoPlayer.Episode"))                   # Episode
  item['tvshow']             = normalizeString(xbmc.getInfoLabel("VideoPlayer.TVshowtitle"))   # Show
  item['tvshow']=checkexp(item['tvshow'])
  
  langstring = urllib.unquote(params['languages']).decode('utf-8')
  item['3let_language'] = [xbmc.convertLanguage(lang,xbmc.ISO_639_2) for lang in langstring.split(",")]
        
  if not item['tvshow']:
    item['title']  = normalizeString(xbmc.getInfoLabel("VideoPlayer.Title"))      # no original title, get just Title
    toParse = item['title'].lower().replace('.', " ")
    infoFromTitle = parseSearchString(toParse)
    if infoFromTitle:
        item['tvshow'] = infoFromTitle['tvshow']
        item['season']= infoFromTitle['season']
        item['episode']= infoFromTitle['episode']
    else:
        notify(language(32003))

  if "s" in item['episode'].lower():                                      # Check if season is "Special"
    item['season'] = "0"
    item['episode'] = item['episode'][-1:]

  Search(item)

elif params['action'] == 'manualsearch':
    item = parseSearchString(params['searchstring'])
    if item:
        langstring = urllib.unquote(params['languages']).decode('utf-8')
        item['3let_language'] = [xbmc.convertLanguage(lang,xbmc.ISO_639_2) for lang in langstring.split(",")]
        Search(item)
    else:
        notify(language(32003))
elif params['action'] == 'download':
  ## we pickup all our arguments sent from def Search()
  subs = Download(params["file"],params["type"],params["si"])
  ## we can return more than one subtitle for multi CD versions, for now we are still working out how to handle that in XBMC core
  for sub in subs:
    listitem = xbmcgui.ListItem(label=sub)
    xbmcplugin.addDirectoryItem(handle=int(sys.argv[1]),url=sub,listitem=listitem,isFolder=False)

xbmcplugin.endOfDirectory(int(sys.argv[1])) ## send end of directory to XBMC
