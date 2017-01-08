# -*- coding: utf-8 -*-

from cStringIO import StringIO
import os
import re
import shutil
import sys
import unicodedata
import urllib
import xbmc
import xbmcaddon
import xbmcgui
import xbmcplugin
import xbmcvfs
from zipfile import ZipFile



__addon__ = xbmcaddon.Addon()
__scriptid__   = __addon__.getAddonInfo('id')
__scriptname__ = __addon__.getAddonInfo('name')

__cwd__        = xbmc.translatePath(__addon__.getAddonInfo('path')).decode("utf-8")
__profile__    = xbmc.translatePath(__addon__.getAddonInfo('profile')).decode("utf-8")
__resource__   = xbmc.translatePath(os.path.join(__cwd__, 'resources', 'lib')).decode("utf-8")
__temp__       = xbmc.translatePath(os.path.join(__profile__, 'temp', '')).decode("utf-8")


BASE_URL = "http://subtitrari.regielive.ro/cauta.html?s="

if xbmcvfs.exists(__temp__):
    shutil.rmtree(__temp__)
xbmcvfs.mkdirs(__temp__)

sys.path.append (__resource__)

import requests
s = requests.Session()
ua = 'Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:50.0) Gecko/20100101 Firefox/50.0'
def Search(item):
    search_data = []
    search_data = searchsubtitles(item)
    if search_data != None:
        for item_data in search_data:
            if ((item['season'] == item_data['SeriesSeason'] and
                item['episode'] == item_data['SeriesEpisode']) or
                (item['season'] == "" and item['episode'] == "") ## for file search, season and episode == ""
                ):
                listitem = xbmcgui.ListItem(label=item_data["LanguageName"],
                                            label2=item_data["SubFileName"],
                                            iconImage=str(item_data["SubRating"]),
                                            thumbnailImage=str(item_data["ISO639"])
                                            )

                listitem.setProperty("sync", ("false", "true")[str(item_data["MatchedBy"]) == "moviehash"])
                listitem.setProperty("hearing_imp", ("false", "true")[int(item_data["SubHearingImpaired"]) != 0])
                url = "plugin://%s/?action=download&link=%s&filename=%s&format=%s&promo=%s" % (__scriptid__,
                                                                                      item_data["ZipDownloadLink"],
                                                                                      item_data["SubFileName"],
                                                                                      item_data["SubFormat"],
                                                                                      item_data["promo"]
                                                                                      )

                xbmcplugin.addDirectoryItem(handle=int(sys.argv[1]), url=url, listitem=listitem, isFolder=False)

def searchsubtitles(item):
    lists = ''
    item_orig = item['title']
    if len(item['tvshow']) > 0:
        search_string = item['tvshow'].replace(" ", "+")     
    else:
        if str(item['year']) == "":
            item['title'], item['year'] = xbmc.getCleanMovieTitle(item['title'])
    
        search_string = (re.sub('S(\d{1,2})E(\d{1,2})', '', item['title']))
        episodes = re.compile('S(\d{1,2})E(\d{1,2})', re.IGNORECASE).findall(item['title'])
        if episodes:
            item['season'] = episodes[0][0]
            item['episode'] = episodes[0][1]
        else:
            episodes = re.compile('(\d)(\d{1,2})', re.IGNORECASE).findall(item['title'])
            if episodes:
                search_string = (re.sub('(\d)(\d{1,2})', '', item['title']))
                item['season'] = episodes[0][0]
                item['episode'] = episodes[0][1]
            
    if item['mansearch']:
        s_string = urllib.unquote(item['mansearchstr'])
        search_string = s_string
        episodes = re.compile('S(\d{1,2})E(\d{1,2})', re.IGNORECASE).findall(search_string)
        if episodes:
            sezon = episodes[0][0]
            episod = episodes[0][1]
            search_string = (re.sub('S(\d{1,2})E(\d{1,2})', '', search_string, flags=re.I))
            lists = search_links(search_string, sezon=sezon, episod=episod)
        else:
            lists = search_links(search_string)
        return lists
    lists = search_links(search_string, item['year'], item['season'], item['episode'], item_orig)
    if not lists:
        if not item['file_original_path'].startswith('http') and xbmcvfs.exists(item['file_original_path']):
            head = os.path.basename(os.path.dirname(item['file_original_path']))
            lists = search_links(search_string, item['year'], item['season'], item['episode'], (re.compile(r'\[.*?\]').sub('', head)))
    return lists

def search_links(nume='', an='', sezon='', episod='', fisier=''):
    subs_list = []
    url = 'http://api.regielive.ro/kodi/cauta.php'
    api = 'API-KODI-KINGUL'
    headers = {'User-Agent': ua, 'RL-API': api}
    payload = {'nume': nume, 'an': an, 'sezon': sezon, 'episod': episod, 'fisier': fisier}
    #with open(xbmc.translatePath(os.path.join('special://temp', 'files.py')), 'wb') as f: f.write(repr(payload))
    p = s.post(url, data=payload, headers=headers)
    result = p.json()
    if not 'eroare' in result:
        codfilm = None
        for cod in result['rezultate']:
            codfilm = cod
        if codfilm:
            promo = result['promo']
            for subtitrari in result['rezultate'][codfilm]['subtitrari']:
                subs_list.append({'SeriesSeason': (item['season']), 'SeriesEpisode': item['episode'], 'LanguageName': 'Romanian',
                                'promo': promo, 'SubFileName': (subtitrari['titlu']), 'SubRating': os.path.splitext(str(subtitrari['rating']['nota']))[0],
                                'ZipDownloadLink': (subtitrari['url']), 'ISO639': 'ro', 'SubFormat': 'srt', 'MatchedBy': 'fulltext', 'SubHearingImpaired': '0'})
        return subs_list
    else:
        return None
    

def log(module, msg):
    xbmc.log((u"### [%s] - %s" % (module, msg,)).encode('utf-8'), level=xbmc.LOGDEBUG) 

def Download(link, url, format, stack=False):
    url = re.sub('download', 'descarca', url)
    url = re.sub('html', 'zip', url)
    subtitle_list = []
    exts = [".srt", ".sub", ".txt", ".smi", ".ssa", ".ass"]
    headers = {'User-Agent': ua}
    if ((__addon__.getSetting("OSuser") and
        __addon__.getSetting("OSpass"))):
        payload = {'l_username':__addon__.getSetting("OSuser"), 'l_password':__addon__.getSetting("OSpass")}
        s.post('http://www.regielive.ro/membri/login.html', data=payload, headers=headers)
        #check_login = re.compile('(User Inexistent|Parola Invalida)', re.IGNORECASE).findall(r.text)
        #if len(check_login) > 0:
            #xbmc.executebuiltin((u'Notification(%s,%s)' % (__scriptname__, check_login[0])).encode('utf-8'))
            #return None
    else:
        s.get('http://www.regielive.ro', headers=headers)
    f = s.get(url, headers=headers)
    try:
        archive = ZipFile(StringIO(f.content), 'r')
    except:
        return subtitle_list
    files = archive.namelist()
    files.sort()
    for file in files:
        contents = archive.read(file)
        if (os.path.splitext(file)[1] in exts):
            #extension = file[file.rfind('.') + 1:]
            if len(files) == 1:
                dest = os.path.join(__temp__, "%s" % (file))
            else:
                dest = os.path.join(__temp__, "%s" % (file))
            f = open(dest, 'wb')
            f.write(contents)
            f.close()
            subtitle_list.append(dest)
                
    if xbmcvfs.exists(subtitle_list[0]):
        if len(subtitle_list) > 1:
            selected = []
            subtitle_list_s = sorted(subtitle_list, key=natural_key)
            dialog = xbmcgui.Dialog()
            sel = dialog.select("%s" % ('Selecteaza o subtitrare'),
                                [((os.path.basename(os.path.dirname(x)) + '/' + os.path.basename(x))
                                  if (os.path.basename(x) == os.path.basename(subtitle_list_s[0])
                                      and os.path.basename(x) == os.path.basename(subtitle_list_s[1]))
                                  else os.path.basename(x))
                                  for x in subtitle_list_s])
            if sel >= 0:
                 selected.append(subtitle_list_s[sel])
                 return selected
            else:
                return None
        else:
            return subtitle_list
    else:
        return None

def normalizeString(str):
    return unicodedata.normalize(
                                 'NFKD', unicode(unicode(str, 'utf-8'))
                                 ).encode('ascii', 'ignore')

def natural_key(string_):
    return [int(s) if s.isdigit() else s for s in re.split(r'(\d+)', string_)]

def get_params(string=""):
    param = []
    if string == "":
        paramstring = sys.argv[2]
    else:
        paramstring = string
    if len(paramstring) >= 2:
        params = paramstring
        cleanedparams = params.replace('?', '')
        if (params[len(params)-1] == '/'):
            params = params[0:len(params)-2]
        pairsofparams = cleanedparams.split('&')
        param = {}
        for i in range(len(pairsofparams)):
            splitparams = {}
            splitparams = pairsofparams[i].split('=')
            if (len(splitparams)) == 2:
                param[splitparams[0]] = splitparams[1]

    return param

params = get_params()

if params['action'] == 'search' or params['action'] == 'manualsearch':
    item = {}
    item['temp']               = False
    item['rar']                = False
    item['mansearch']          = False
    item['year']               = xbmc.getInfoLabel("VideoPlayer.Year")                         # Year
    item['season']             = str(xbmc.getInfoLabel("VideoPlayer.Season"))                  # Season
    item['episode']            = str(xbmc.getInfoLabel("VideoPlayer.Episode"))                 # Episode
    item['tvshow']             = normalizeString(xbmc.getInfoLabel("VideoPlayer.TVshowtitle"))  # Show
    item['title']              = normalizeString(xbmc.getInfoLabel("VideoPlayer.OriginalTitle"))# try to get original title
    item['file_original_path'] = xbmc.Player().getPlayingFile().decode('utf-8')                 # Full path of a playing file
    item['3let_language']      = [] #['scc','eng']

    if 'searchstring' in params:
        item['mansearch'] = True
        item['mansearchstr'] = params['searchstring']

    for lang in urllib.unquote(params['languages']).decode('utf-8').split(","):
        if lang == "Portuguese (Brazil)":
            lan = "pob"
        elif lang == "Greek":
            lan = "ell"
        else:
            lan = xbmc.convertLanguage(lang, xbmc.ISO_639_2)

        item['3let_language'].append(lan)

    if item['title'] == "":
        item['title']  = normalizeString(xbmc.getInfoLabel("VideoPlayer.Title"))      # no original title, get just Title

    if item['episode'].lower().find("s") > -1:                                      # Check if season is "Special"
        item['season'] = "0"                                                          #
        item['episode'] = item['episode'][-1:]

    if (item['file_original_path'].find("http") > -1):
        item['temp'] = True

    elif (item['file_original_path'].find("rar://") > -1):
        item['rar']  = True
        item['file_original_path'] = os.path.dirname(item['file_original_path'][6:])

    elif (item['file_original_path'].find("stack://") > -1):
        stackPath = item['file_original_path'].split(" , ")
        item['file_original_path'] = stackPath[0][8:]

    Search(item)

elif params['action'] == 'download':
    subs = Download(params["link"], params["link"], params["format"])
    promo = params['promo']
    if subs:
        for sub in subs:
            listitem = xbmcgui.ListItem(label=sub)
            xbmcplugin.addDirectoryItem(handle=int(sys.argv[1]), url=sub, listitem=listitem, isFolder=False)
        import threading
        #bg_pub = os.path.join(__cwd__, 'resources', 'media', 'ContentPanel.png')
        class FuncThread(threading.Thread):
            def __init__(self, target, *args):
                self._target = target
                self._args = args
                threading.Thread.__init__(self)
 
            def run(self):
                self._target(*self._args)
                    
        class PubRegie(xbmcgui.WindowDialog):
            def __init__(self):
                #self.background = xbmcgui.ControlImage(0, 70, 800, 100, 'ContentPanel.png')
                self.background = xbmcgui.ControlImage(10, 70, 1000, 100, "")
                self.text = xbmcgui.ControlLabel(10, 70, 1000, 100, '', textColor='0xff000000', alignment=0)
                self.text2 = xbmcgui.ControlLabel(8, 68, 1000, 100, '', alignment=0)
                self.addControls((self.text, self.text2))
            def sP(self, promo):
                self.show()
                #self.background.setImage("")
                #self.background.setImage(bg_pub)
                self.text.setLabel(chr(10) + "[B]%s[/B]" % promo)
                self.text2.setLabel(chr(10) + "[B]%s[/B]" % promo)
                self.text.setAnimations([('WindowOpen', 'effect=fade start=0 end=100 time=250 delay=125 condition=true'),
                                            ('WindowClose', 'effect=fade start=100 end=0 time=250 condition=true')])
                self.background.setAnimations([('WindowOpen', 'effect=fade start=0 end=100 time=250 delay=125 condition=true'),
                                            ('WindowClose', 'effect=fade start=100 end=0 time=250 condition=true')])
                xbmc.sleep(4500)
                self.close()
                del self   
        t1 = FuncThread((PubRegie().sP), promo)
        t1.start()

xbmcplugin.endOfDirectory(int(sys.argv[1]))
