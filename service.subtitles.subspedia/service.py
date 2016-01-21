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
from fileinput import filename

__addon__ = xbmcaddon.Addon()
__author__ = __addon__.getAddonInfo('author')
__scriptid__ = __addon__.getAddonInfo('id')
__scriptname__ = __addon__.getAddonInfo('name')
__version__= __addon__.getAddonInfo('version')
__language__ = __addon__.getLocalizedString

__cwd__= xbmc.translatePath( __addon__.getAddonInfo('path') ).decode("utf-8")
__profile__= xbmc.translatePath( __addon__.getAddonInfo('profile') ).decode("utf-8")
__resource__ = xbmc.translatePath( os.path.join( __cwd__, 'resources', 'lib' ) ).decode("utf-8")
__temp__ = xbmc.translatePath( os.path.join( __profile__, 'temp','') ).decode("utf-8")
sys.path.append (__resource__)
def Search(item):
    if 'ita' in item['3let_language'] and item['tvshow']:
        urlgetid="http://www.subspedia.tv/API/getAllSeries.php"
        urlgetsub="http://www.subspedia.tv/API/getBySerie.php?serie="
        idserie=checkexp(item['tvshow'])
        linkdownload=""
        eptitolo=""  
        response = urllib2.urlopen(urlgetid)
        data = json.loads(response.read())
        if idserie==0:
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
                    if xbmcvfs.exists(__temp__):
                        shutil.rmtree(__temp__)
                        log("elimino temp")
                    xbmcvfs.mkdirs(__temp__)
                    log("ricreo temp")
                    local_tmp_file = os.path.join(__temp__, 'subspedia.xxx')
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
                        local_tmp_file = os.path.join(__temp__, 'subspedia.' + typeid)
                        os.rename(os.path.join(__temp__, 'subspedia.xxx'), local_tmp_file)
                        log("Saving to %s" % local_tmp_file)
                    except:
                        #log("Failed to save subtitle to %s" % local_tmp_file)
                        return []
                    if packed:
                        xbmc.sleep(500)
                        dirtemp=__temp__ +"unpack"
                        log("dirtemp %s "%dirtemp)
                        if not os.path.exists(dirtemp):
                            os.makedirs(dirtemp)
                        else:
                            shutil.rmtree(dirtemp)
                            os.makedirs(dirtemp)
                        xbmc.executebuiltin(('XBMC.Extract(' + local_tmp_file + ',' + dirtemp +')').encode('utf-8'), True)
                        dirs = os.listdir(dirtemp)
                        for file in dirs:
                            filen=file.replace("subspedia","")
                            filen=filen.replace("Subspedia","")
                            filen=filen.replace(".srt","")
                            filen=filen.replace("."," ")
                            filen=filen.replace("_"," ")
                            listitem = xbmcgui.ListItem(label="Italian",label2=filen,thumbnailImage='it')
                            listitem.setProperty( "sync",'false')                
                            listitem.setProperty('hearing_imp', 'false') # set to "true" if subtitle is for hearing impared              
                            url = "plugin://%s/?action=download&file=%s&type=%s" % (__scriptid__, file,"pack")
                            xbmcplugin.addDirectoryItem(handle=int(sys.argv[1]),url=url,listitem=listitem,isFolder=False)
                        
                    else:
                        labeltitle=item['tvshow']+" "+item['season']+"x"+item['episode']+" "+eptitolo
                        listitem = xbmcgui.ListItem(label="Italian",label2=labeltitle,thumbnailImage='it')
                        listitem.setProperty( "sync",'false')                
                        listitem.setProperty('hearing_imp', 'false') # set to "true" if subtitle is for hearing impared              
                        url = "plugin://%s/?action=download&file=%s&type=%s" % (__scriptid__,local_tmp_file,"unpack")
                        xbmcplugin.addDirectoryItem(handle=int(sys.argv[1]),url=url,listitem=listitem,isFolder=False)
                else:
                    log('Failed to download the file')
                    return []
            else:
                notify(__language__(32004))
                log('Subs not found')
        else:
            notify(__language__(32003))
            log('Tvshow not found')
    else:
        notify(__language__(32001))
        log('Subspedia only works with italian subs. Skipped')

def checkexp(tvshow):
    exp=[["Marvel's Agents of S.H.I.E.L.D.",5],["Marvel's Daredevil",246],["Marvel's Jessica Jones",333],["Marvel's Agent Carter",4]]
    for expl in exp:
        if tvshow == expl[0]:
            return expl[1]
    return 0
    
def notify(msg):
    xbmc.executebuiltin((u'Notification(%s,%s)' % (__scriptname__ , msg)).encode('utf-8'))            

def Download(link,type):
    subtitle_list = []
    if type=="pack":
        dirtemp=__temp__ +"unpack\\"
        link=dirtemp+link      
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

print params


if params['action'] == 'search':
    item = {}
    item['temp']               = False
    item['rar']                = False
    item['year']               = xbmc.getInfoLabel("VideoPlayer.Year")                           # Year
    item['season']             = str(xbmc.getInfoLabel("VideoPlayer.Season"))                    # Season
    item['episode']            = str(xbmc.getInfoLabel("VideoPlayer.Episode"))                   # Episode
    item['tvshow']             = normalizeString(xbmc.getInfoLabel("VideoPlayer.TVshowtitle"))   # Show
    item['title']              = normalizeString(xbmc.getInfoLabel("VideoPlayer.OriginalTitle")) # try to get original title
    item['file_original_path'] = urllib.unquote(xbmc.Player().getPlayingFile().decode('utf-8'))  # Full path of a playing file
    item['3let_language']      = []
  
    for lang in urllib.unquote(params['languages']).decode('utf-8').split(","):
        item['3let_language'].append(xbmc.convertLanguage(lang,xbmc.ISO_639_2))
    
    if item['title'] == "":
        item['title']  = normalizeString(xbmc.getInfoLabel("VideoPlayer.Title"))      # no original title, get just Title
      
    if item['episode'].lower().find("s") > -1:                                      # Check if season is "Special"
        item['season'] = "0"                                                          #
        item['episode'] = item['episode'][-1:]
    
    if ( item['file_original_path'].find("http") > -1 ):
        item['temp'] = True
    
    elif ( item['file_original_path'].find("rar://") > -1 ):
        item['rar']  = True
        item['file_original_path'] = os.path.dirname(item['file_original_path'][6:])
    
    elif ( item['file_original_path'].find("stack://") > -1 ):
        stackPath = item['file_original_path'].split(" , ")
        item['file_original_path'] = stackPath[0][8:]
  
    Search(item)  
elif params['action'] == 'manualsearch':
    res=re.findall('(.*?)(\d{1,3})x(\d{1,3})', urllib.unquote(params['searchstring']), re.IGNORECASE)
    if res:
        item = {}
        item['tvshow']=res[0][0]
        lres=len(item['tvshow'])
        if item['tvshow'][lres-1:lres]==" ":
            item['tvshow']=item['tvshow'][0:lres-1]
        item['season']=res[0][1]
        item['episode']=res[0][2]
        item['3let_language']=[]
        for lang in urllib.unquote(params['languages']).decode('utf-8').split(","):
            item['3let_language'].append(xbmc.convertLanguage(lang,xbmc.ISO_639_2))
        Search(item) 
    else:
        notify(__language__(32002))      
elif params['action'] == 'download':
    ## we pickup all our arguments sent from def Search()
    subs = Download(params["file"],params["type"])
    ## we can return more than one subtitle for multi CD versions, for now we are still working out how to handle that in XBMC core
    for sub in subs:
        listitem = xbmcgui.ListItem(label=sub)
        xbmcplugin.addDirectoryItem(handle=int(sys.argv[1]),url=sub,listitem=listitem,isFolder=False)
xbmcplugin.endOfDirectory(int(sys.argv[1])) ## send end of directory to XBMC