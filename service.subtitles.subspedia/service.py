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
import json
import re

addon = xbmcaddon.Addon()
scriptid = addon.getAddonInfo('id')
scriptname = addon.getAddonInfo('name')
language = addon.getLocalizedString
profile= xbmc.translatePath( addon.getAddonInfo('profile') ).decode("utf-8")
temp = xbmc.translatePath( os.path.join( profile, 'temp','') ).decode("utf-8")

def Search(item):
    if 'ita' in item['3let_language'] and item['tvshow']:
        urlgetid="https://www.subspedia.tv/API/elenco_serie"
        urlgetsub="https://www.subspedia.tv/API/sottotitoli_serie?serie="
        idserie=checkexp(item['tvshow'])
        linkdownload=""
        eptitolo=""  
        if idserie==0:
            response = urllib2.urlopen(urlgetid)
            data = json.loads(response.read())
            for series in data:
                if item['tvshow'].lower()==series['nome_serie'].lower():
                    idserie=series["id_serie"]
                    break
        if idserie!=0:
            urlgetsub=urlgetsub+str(idserie)
            response = urllib2.urlopen(urlgetsub)
            data=json.loads(response.read())
            for season in data:
                num_stagione=str(season["num_stagione"])
                num_episodio=str(season["num_episodio"])
                if (item['season']==num_stagione)and(item['episode']==num_episodio):
                    eptitolo=season["ep_titolo"]
                    linkdownload=season["link_file"]
                    break
            if linkdownload!="":
                log("Fetching subtitles using url %s" % linkdownload)
                content= urllib2.urlopen(linkdownload).read()
                if content:
                    log('File downloaded')
                    if xbmcvfs.exists(temp):
                        shutil.rmtree(temp)
                        #log("elimino temp")
                    xbmcvfs.mkdirs(temp)
                    #log("ricreo temp")
                    local_tmp_file = os.path.join(temp, 'subspedia.xxx')
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
                        local_tmp_file = os.path.join(temp, 'subspedia.' + typeid)
                        os.rename(os.path.join(temp, 'subspedia.xxx'), local_tmp_file)
                        log("Saving to %s" % local_tmp_file)
                    except:
                        #log("Failed to save subtitle to %s" % local_tmp_file)
                        return []
                    if packed:
                        xbmc.sleep(500)
                        dirtemp=temp+"unpack"
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
                            if (os.path.isdir(path_rec) and file!="__MACOSX" ):
                                dirs_rec = os.listdir(path_rec)
                                for file_rec in dirs_rec:
                                    filen=cleanName(file_rec)
                                    url = "plugin://%s/?action=download&file=%s&type=%s" % (scriptid,os.path.join(file,file_rec),"pack")
                                    xbmcplugin.addDirectoryItem(handle=int(sys.argv[1]),url=url,listitem=make_listItem(filen),isFolder=False)
                            elif(file!="__MACOSX"):
                                filen=cleanName(file)      
                                url = "plugin://%s/?action=download&file=%s&type=%s" % (scriptid, file,"pack")
                                xbmcplugin.addDirectoryItem(handle=int(sys.argv[1]),url=url,listitem=make_listItem(filen),isFolder=False)
                        
                    else:
                        labeltitle=item['tvshow']+" "+item['season']+"x"+item['episode']+" "+eptitolo            
                        url = "plugin://%s/?action=download&file=%s&type=%s" % (scriptid,local_tmp_file,"unpack")
                        xbmcplugin.addDirectoryItem(handle=int(sys.argv[1]),url=url,listitem=make_listItem(labeltitle),isFolder=False)
                else:
                    log('Failed to download the file')
                    return []
            else:
                notify(language(32004))
                log('Subs not found')
        else:
            notify(language(32003))
            log('Tvshow not found')
    else:
        notify(language(32001))
        log('Subspedia only works with italian subs. Skipped')

def checkexp(tvshow):
    exp=[["Marvel's Agents of S.H.I.E.L.D.",5],
         ["Marvel's Daredevil",246],
         ["Marvel's Jessica Jones",333],
         ["Marvel's Agent Carter",4],
         ["DC's Legends of Tomorrow",345]]
    for expl in exp:
        if tvshow == expl[0]:
            return expl[1]
    return 0

def make_listItem(filen):
    listitem = xbmcgui.ListItem(label="Italian",label2=filen,thumbnailImage='it')
    listitem.setProperty( "sync",'false')
    listitem.setProperty('hearing_imp', 'false')
    return listitem

def parseSearchString(str):
    res=re.findall('(.*\d*?) s?0?(\d{1,3})x?e?0?(\d{1,3})', urllib.unquote(str), re.IGNORECASE)
    item={}
    if res:
        item['tvshow']=res[0][0]
        lres=len(item['tvshow'])
        if item['tvshow'][lres-1:lres]==" ":
            item['tvshow']=item['tvshow'][0:lres-1]
        item['season']=res[0][1]
        item['episode']=res[0][2]
    return item

def cleanName(file):
    filen=file.replace("subspedia","")
    filen=filen.replace("Subspedia","")
    filen=filen.replace(".srt","")
    filen=filen.replace("."," ")
    filen=filen.replace("_"," ")
    return filen
  
def notify(msg):
    xbmc.executebuiltin((u'Notification(%s,%s)' % (scriptname , msg)).encode('utf-8'))            

def Download(link,type):
    subtitle_list = []
    if type=="pack":
        dirtemp=temp+"unpack\\"
        link=os.path.join(dirtemp,link)    
    subtitle_list.append(link)
    return subtitle_list
 
def normalizeString(str):
    return unicodedata.normalize('NFKD', unicode(unicode(str, 'utf-8'))).encode('ascii','ignore')    

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
    item['3let_language']      = []
  
    for lang in urllib.unquote(params['languages']).decode('utf-8').split(","):
        item['3let_language'].append(xbmc.convertLanguage(lang,xbmc.ISO_639_2))
    
    if not item['tvshow']:
        item['title']  = normalizeString(xbmc.getInfoLabel("VideoPlayer.Title"))      # no original title, get just Title
        toParse = item['title'].lower().replace('.', " ")
        infoFromTitle = parseSearchString(toParse)
        if infoFromTitle:
            item['tvshow'] = infoFromTitle['tvshow']
            item['season']= infoFromTitle['season']
            item['episode']= infoFromTitle['episode']
        else:
            notify(language(32002))
      
    if item['episode'].lower().find("s") > -1:                                      # Check if season is "Special"
        item['season'] = "0"                                                          #
        item['episode'] = item['episode'][-1:]
  
    Search(item)  
elif params['action'] == 'manualsearch':
    item = parseSearchString(params['searchstring'])
    if item:
        langstring = urllib.unquote(params['languages']).decode('utf-8')
        item['3let_language'] = [xbmc.convertLanguage(lang,xbmc.ISO_639_2) for lang in langstring.split(",")]
        Search(item)
    else:
        notify(language(32002))
elif params['action'] == 'download':
    ## we pickup all our arguments sent from def Search()
    subs = Download(params["file"],params["type"])
    ## we can return more than one subtitle for multi CD versions, for now we are still working out how to handle that in XBMC core
    for sub in subs:
        listitem = xbmcgui.ListItem(label=sub)
        xbmcplugin.addDirectoryItem(handle=int(sys.argv[1]),url=sub,listitem=listitem,isFolder=False)
xbmcplugin.endOfDirectory(int(sys.argv[1])) ## send end of directory to XBMC