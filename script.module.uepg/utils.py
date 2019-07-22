#   Copyright (C) 2019 Lunatixz
#
#
# This file is part of uEPG.
#
# uEPG is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# uEPG is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with uEPG.  If not, see <http://www.gnu.org/licenses/>.

# -*- coding: utf-8 -*-
import os, json, urllib, epg, traceback, ast, time, datetime, random, itertools, calendar
import xbmc, xbmcgui, xbmcplugin, xbmcvfs, xbmcaddon

from simplecache import SimpleCache, use_cache
from metadatautils import MetadataUtils
from pyhdhr import PyHDHR

# Plugin Info
ADDON_ID      = 'script.module.uepg'
REAL_SETTINGS = xbmcaddon.Addon(id=ADDON_ID)
ADDON_NAME    = REAL_SETTINGS.getAddonInfo('name')
ADDON_AUTHOR  = REAL_SETTINGS.getAddonInfo('author')
SETTINGS_LOC  = REAL_SETTINGS.getAddonInfo('profile')
ADDON_PATH    = REAL_SETTINGS.getAddonInfo('path').decode('utf-8')
ADDON_VERSION = REAL_SETTINGS.getAddonInfo('version')
ICON          = REAL_SETTINGS.getAddonInfo('icon')
FANART        = REAL_SETTINGS.getAddonInfo('fanart')
LANGUAGE      = REAL_SETTINGS.getLocalizedString
DEBUG         = REAL_SETTINGS.getSetting('Enable_Debugging') == 'true'

KODI_MONITOR    = xbmc.Monitor()
JSON_FILE_INTRO = '["title", "artist", "albumartist", "genre", "year", "rating", "album", "track", "duration", "comment", "lyrics", "musicbrainztrackid", "musicbrainzartistid", "musicbrainzalbumid", "musicbrainzalbumartistid", "playcount", "fanart", "director", "trailer", "tagline", "plot", "plotoutline", "originaltitle", "lastplayed", "writer", "studio", "mpaa", "cast", "country", "imdbnumber", "premiered", "productioncode", "runtime", "set", "showlink", "streamdetails", "top250", "votes", "firstaired", "season", "episode", "showtitle", "thumbnail", "file", "resume", "artistid", "albumid", "tvshowid", "setid", "watchedepisodes", "disc", "tag", "art", "genreid", "displayartist", "albumartistid", "description", "theme", "mood", "style", "albumlabel", "sorttitle", "episodeguide", "uniqueid", "dateadded", "size", "lastmodified", "mimetype", "specialsortseason", "specialsortepisode"]'
JSON_PVR_DETAIL = '["title","plot","plotoutline","starttime","endtime","runtime","progress","progresspercentage","genre","episodename","episodenum","episodepart","firstaired","hastimer","isactive","parentalrating","wasactive","thumbnail","rating","originaltitle","cast","director","writer","year","imdbnumber","hastimerrule","hasrecording","recording","isseries"]'
JSON_FILES      = ["title","artist","albumartist","genre","year","rating","album","track","duration","lyrics","playcount","fanart","director","trailer","tagline","plot","plotoutline","originaltitle","lastplayed","writer","studio","mpaa","country","imdbnumber","premiered","runtime","set","showlink","streamdetails","top250","votes","firstaired","season","episode","showtitle","thumbnail","file","resume","artistid","albumid","tvshowid","setid","watchedepisodes","disc","tag","art","genreid","displayartist","description","theme","mood","style","albumlabel","sorttitle","uniqueid","dateadded","size","lastmodified"]
JSON_ART        = ["thumb","logo","poster","fanart","banner","landscape","clearart","clearlogo"]
ITEM_TYPES      = ['genre','country','year','episode','season','sortepisode','sortseason','episodeguide','showlink','top250','setid','tracknumber','rating','userrating','watched','playcount','overlay','director','mpaa','plot','plotoutline','title','originaltitle','sorttitle','duration','studio','tagline','writer','showtitle','tvshowtitle','premiered','status','set','setoverview','tag','imdbnumber','code','aired','credits','lastplayed','album','artist','votes','path','trailer','dateadded','mediatype','dbid']
FILE_PARAMS     = ["title", "artist", "albumartist", "genre", "year", "rating", "album", "track", "duration", "comment", "lyrics", "musicbrainztrackid", "musicbrainzartistid", "musicbrainzalbumid", "musicbrainzalbumartistid", "playcount", "fanart", "director", "trailer", "tagline", "plot", "plotoutline", "originaltitle", "lastplayed", "writer", "studio", "mpaa", "cast", "country", "imdbnumber", "premiered", "productioncode", "runtime", "set", "showlink", "streamdetails", "top250", "votes", "firstaired", "season", "episode", "showtitle", "thumbnail", "file", "resume", "artistid", "albumid", "tvshowid", "setid", "watchedepisodes", "disc", "tag", "art", "genreid", "displayartist", "albumartistid", "description", "theme", "mood", "style", "albumlabel", "sorttitle", "episodeguide", "uniqueid", "dateadded", "size", "lastmodified", "mimetype", "specialsortseason", "specialsortepisode"]
PVR_PARAMS      = ["title","plot","plotoutline","starttime","endtime","runtime","progress","progresspercentage","genre","episodename","episodenum","episodepart","firstaired","hastimer","isactive","parentalrating","wasactive","thumbnail","rating","originaltitle","cast","director","writer","year","imdbnumber","hastimerrule","hasrecording","recording","isseries"]
ART_PARAMS      = ["thumb","poster","fanart","banner","landscape","clearart","clearlogo"]
ALL_PARAMS      = list(set(FILE_PARAMS+PVR_PARAMS+ART_PARAMS))
IGNORE_VALUES   = ['',[],-1,{},None]
MEDIA_TYPES     = {'SP':'video','SH':'episode','EP':'episode','MV':'movie'}
EPGGENRE_LOC    = 'epg-genres'
TIME_BAR        = 'TimeBar.png'
BUTTON_FOCUS    = 'ButtonFocus.png'
PAST_FADE       = 'PastFade.png'
FUTURE_FADE     = 'FutureFade.png'

ACTION_GESTURE_SWIPE_LEFT      = 511
ACTION_GESTURE_SWIPE_LEFT_TEN  = 520
ACTION_GESTURE_SWIPE_RIGHT     = 521
ACTION_GESTURE_SWIPE_RIGHT_TEN = 530
ACTION_GESTURE_SWIPE_UP        = 531
ACTION_GESTURE_SWIPE_UP_TEN    = 540
ACTION_GESTURE_SWIPE_DOWN      = 541
ACTION_GESTURE_SWIPE_DOWN_TEN  = 550
ACTION_TOUCH_LONGPRESS         = 411
ACTION_MOUSE_WHEEL_UP          = 104
ACTION_MOUSE_WHEEL_DOWN        = 105
ACTION_SELECT_ITEM             = [7]
ACTION_MOVE_LEFT               = [1,ACTION_GESTURE_SWIPE_LEFT]
ACTION_MOVE_RIGHT              = [2,ACTION_GESTURE_SWIPE_RIGHT]
ACTION_MOVE_UP                 = [3,ACTION_GESTURE_SWIPE_UP]
ACTION_MOVE_DOWN               = [4,ACTION_GESTURE_SWIPE_DOWN]
ACTION_PAGEUP                  = [5,ACTION_GESTURE_SWIPE_UP_TEN,ACTION_MOUSE_WHEEL_UP]
ACTION_PAGEDOWN                = [6,ACTION_GESTURE_SWIPE_DOWN_TEN,ACTION_MOUSE_WHEEL_DOWN]
ACTION_CONTEXT_MENU            = [117,ACTION_TOUCH_LONGPRESS]
ACTION_PREVIOUS_MENU           = [9, 10, 92, 247, 257, 275, 61467, 61448]

# EPG Chtype/Genre COLOR TYPES
COLOR_RED_TYPE      = ['RED','10','13', 'TV-MA', 'R', 'NC-17', 'Youtube', 'Gaming', 'Sports', 'Sport', 'Sports Event', 'Sports Talk', 'Archery', 'Rodeo', 'Card Games', 'Martial Arts', 'Basketball', 'Baseball', 'Hockey', 'Football', 'Boxing', 'Golf', 'Auto Racing', 'Playoff Sports', 'Hunting', 'Gymnastics', 'Shooting', 'Sports non-event']
COLOR_GREEN_TYPE    = ['GREEN','5', 'News', 'Public Affairs', 'Newsmagazine', 'Politics', 'Entertainment', 'Community', 'Talk', 'Interview', 'Weather']
COLOR_mdGREEN_TYPE  = ['mdGREEN','9', 'Suspense', 'Horror', 'Horror Suspense', 'Paranormal', 'Thriller', 'Fantasy']
COLOR_BLUE_TYPE     = ['BLUE','Comedy', 'Comedy-Drama', 'Romance-Comedy', 'Sitcom', 'Comedy-Romance']
COLOR_ltBLUE_TYPE   = ['ltBLUE','2', '4', '14', '15', '16', 'Movie','Movies']
COLOR_CYAN_TYPE     = ['CYAN','8', 'Documentary', 'History', 'Biography', 'Educational', 'Animals', 'Nature', 'Health', 'Science & Tech', 'Tech', 'Technology', 'Science', 'Learning & Education', 'Foreign Language']
COLOR_ltCYAN_TYPE   = ['ltCYAN','Outdoors', 'Special', 'Reality', 'Reality & Game Shows']
COLOR_PURPLE_TYPE   = ['PURPLE','Drama', 'Romance', 'Historical Drama']
COLOR_ltPURPLE_TYPE = ['ltPURPLE','12', '13', 'LastFM', 'Vevo', 'VevoTV', 'Musical', 'Music', 'Musical Comedy']
COLOR_ORANGE_TYPE   = ['ORANGE','11', 'TV-PG', 'TV-14', 'PG', 'PG-13', 'RSS', 'REDDIT', 'Animation', 'Animation & Cartoons', 'Animated', 'Anime', 'Children', 'Cartoon', 'Family','Seasonal','Kids']
COLOR_YELLOW_TYPE   = ['YELLOW','1', '3', '6', 'TV-Y7', 'TV-Y', 'TV-G', 'G', 'Classic TV', 'Action', 'Adventure', 'Action & Adventure', 'Action and Adventure', 'Action Adventure', 'Crime', 'Crime Drama', 'Mystery', 'Science Fiction', 'Series', 'Western', 'Soap', 'Soaps', 'Variety', 'War', 'Law', 'Adults Only']
COLOR_GRAY_TYPE     = ['GRAY','Auto', 'Collectibles', 'Travel', 'Shopping', 'House Garden', 'Home & Garden', 'Home and Garden', 'Gardening', 'Fitness Health', 'Fitness', 'Home Improvement', 'How-To', 'Cooking', 'Fashion', 'Beauty & Fashion', 'Aviation', 'Dance', 'Auction', 'Art', 'Exercise', 'Parenting', 'Food', 'Health & Fitness']
COLOR_ltGRAY_TYPE   = ['ltGRAY','0', '7', 'NR', 'Consumer', 'Game Show', 'Other', 'Unknown', 'Religious', 'Anthology', 'None']
GENRE_TYPES         = [COLOR_RED_TYPE,COLOR_GREEN_TYPE,COLOR_mdGREEN_TYPE,COLOR_BLUE_TYPE,COLOR_ltBLUE_TYPE,COLOR_CYAN_TYPE,COLOR_ltCYAN_TYPE,COLOR_PURPLE_TYPE,COLOR_ltPURPLE_TYPE,COLOR_ORANGE_TYPE,COLOR_YELLOW_TYPE,COLOR_GRAY_TYPE,COLOR_ltGRAY_TYPE]

# SFX
SFX_LOC     = xbmc.translatePath(os.path.join(ADDON_PATH, 'resources','sfx',''))
ALERT_SFX   = os.path.join(SFX_LOC, 'alert.wav')
BACK_SFX    = os.path.join(SFX_LOC, 'back.wav')
CONTEXT_SFX = os.path.join(SFX_LOC, 'context.wav')
ERROR_SFX   = os.path.join(SFX_LOC, 'error.wav')
FAILED_SFX  = os.path.join(SFX_LOC, 'failed.wav')
SELECT_SFX  = os.path.join(SFX_LOC, 'select.wav')
PUSH_SFX    = os.path.join(SFX_LOC, 'push.wav')

#ASCII ANIMATION
SPINNER     = itertools.cycle(['|', '/', '-', '\\']).next
WAITER      = itertools.cycle(['.', '..', '...']).next

try:
    from multiprocessing import cpu_count 
    from multiprocessing.pool import ThreadPool 
    ENABLE_POOL = True
except Exception: ENABLE_POOL = False
    
def log(msg, level=xbmc.LOGDEBUG):
    if DEBUG == False and level != xbmc.LOGERROR: return
    if level == xbmc.LOGERROR: msg += ' ,' + traceback.format_exc()
    xbmc.log(ADDON_ID + '-' + ADDON_VERSION + '-' + (msg.encode("utf-8")), level)
        
def uni(string, encoding='utf-8'):
    if isinstance(string, basestring):
        if not isinstance(string, unicode): string = unicode(string, encoding)
    return string

def ascii(string):
    if isinstance(string, basestring):
        if isinstance(string, unicode): string = string.encode('ascii', 'ignore')
    return string
       
def trimString(content, limit=250, suffix='...'):
    if len(content) <= limit: return content
    return content[:limit].rsplit(' ', 1)[0]+suffix
  
def getMeta(label, type='tvshows', yrs=''):
    metadatautils = MetadataUtils()
    metadatautils.tmdb.api_key = '9c47d05a3f5f3a00104f6586412306af'
    return metadatautils.get_tmdb_details(title=label, year=yrs, media_type=type, manual_select=False)
    
def getGenreColor(genre):
    genre = genre.split(' / ')
    if len(genre) > 5: return 'ButtonNoFocus'
    else: genre = genre[0]
    # return random.choice(GENRE_TYPES)[0] #test
    if genre in COLOR_RED_TYPE:        return 'RED'
    elif genre in COLOR_GREEN_TYPE:    return 'GREEN'
    elif genre in COLOR_mdGREEN_TYPE:  return 'mdGREEN'
    elif genre in COLOR_BLUE_TYPE:     return 'BLUE'
    elif genre in COLOR_ltBLUE_TYPE:   return 'ltBLUE'
    elif genre in COLOR_CYAN_TYPE:     return 'CYAN'
    elif genre in COLOR_ltCYAN_TYPE:   return 'ltCYAN'
    elif genre in COLOR_PURPLE_TYPE:   return 'PURPLE'
    elif genre in COLOR_ltPURPLE_TYPE: return 'ltPURPLE'
    elif genre in COLOR_ORANGE_TYPE:   return 'ORANGE'
    elif genre in COLOR_YELLOW_TYPE:   return 'YELLOW'
    elif genre in COLOR_GRAY_TYPE:     return 'GRAY'
    else:                              return 'ButtonNoFocus'
     
def getPluginMeta(plugin):
    log('getPluginMeta: ' + plugin)
    if '?' in plugin: plugin = plugin.split('?')[0]
    if plugin[0:9] == 'plugin://':
        plugin = plugin.replace("plugin://","")
        plugin = splitall(plugin)[0]
    else: plugin = plugin
    pluginID = xbmcaddon.Addon(plugin)
    return pluginID.getAddonInfo('name'), pluginID.getAddonInfo('author'), pluginID.getAddonInfo('icon'), pluginID.getAddonInfo('fanart'), pluginID.getAddonInfo('id')
 
def notificationDialog(message, header=ADDON_NAME, show=True, sound=False, time=1000, icon=ICON):
    log('notificationDialog: ' + message)
    if show == True:
        try: xbmcgui.Dialog().notification(header, message, icon, time, sound=False)
        except Exception as e:
            log("notificationDialog Failed! " + str(e), xbmc.LOGERROR)
            xbmc.executebuiltin("Notification(%s, %s, %d, %s)" % (header, message, time, icon))
    
def yesnoDialog(str1, str2='', str3='', header=ADDON_NAME, yes='', no='', custom='', autoclose=0):
    try: return xbmcgui.Dialog().yesno(header, str1, no, yes, custom, autoclose)
    except: return xbmcgui.Dialog().yesno(header, str1, str2, str3, no, yes, autoclose)
    
def okDialog(str1, str2='', str3='', header=ADDON_NAME):
    xbmcgui.Dialog().ok(header, str1, str2, str3)
    
def textViewer(str1, header=ADDON_NAME):
    xbmcgui.Dialog().textviewer(header, str1)
    
def getKodiVersion():
    return xbmc.getInfoLabel('System.BuildVersion')    
    
def splitall(path):
    allparts = []
    while 1:
        parts = os.path.split(path)
        if parts[0] == path:
            allparts.insert(0, parts[0])
            break
        elif parts[1] == path:
            allparts.insert(0, parts[1])
            break
        else:
            path = parts[0]
            allparts.insert(0, parts[1])
    return allparts
  
def loadJson(string):
    try:
        if isinstance(string,dict): return string
        elif isinstance(string,basestring): return json.loads(uni(string))
        else: return {}
    except: return ''
    
def dumpJson(mydict, sortkey=True):
    return json.dumps(mydict, sort_keys=sortkey)

def getProperty(string1):
    try: 
        state = xbmcgui.Window(10000).getProperty(string1)
        log("getProperty, string1 = " + string1 + ", state = " + state)
        return state
    except Exception as e:
        log("getProperty, Failed! " + str(e), xbmc.LOGERROR)
        return ''
          
def setProperty(string1, string2):
    log("setProperty, string1 = " + string1 + ", string2 = " + string2)
    try: xbmcgui.Window(10000).setProperty(string1, string2)
    except Exception as e: log("setProperty, Failed! " + str(e), xbmc.LOGERROR)

def clearProperty(string1):
    xbmcgui.Window(10000).clearProperty(string1)
     
def unquote(string):
    return urllib.unquote(string)
        
def quote(string):
    return urllib.quote(string)
        
def roundToHalfHour(thetime):
    n = datetime.datetime.fromtimestamp(thetime)
    delta = datetime.timedelta(minutes=30)
    if n.minute > 29: n = n.replace(minute=30, second=0, microsecond=0)
    else: n = n.replace(minute=0, second=0, microsecond=0)
    return time.mktime(n.timetuple())

def ProgressDialogBG(percent=0, control=None, string1='', header=ADDON_NAME):
    if percent == 0 and not control:
        control = xbmcgui.DialogProgressBG()
        control.create(header, string1)
    elif percent == 100 and control: return control.close()
    elif control: control.update(percent, string1)
    return control
    
def ProgressDialog(percent=0, control=None, string1='', string2='', string3='', header=ADDON_NAME):
    if percent == 0 and not control:
        control = xbmcgui.DialogProgress()
        control.create(header, string1, string2, string3)
    elif control and control.iscanceled: return False
    elif percent == 100 and control: return control.close()
    elif control: control.update(percent, string1, string2, string3)
    return control
    
def adaptiveDialog(percent, control=None, size=0, string1='', string2='', string3='', header=ADDON_NAME):
    #Dialog based on length of parsable content... ie Simple dialog for quick parse, Advanced dialog for longer parsing.
    if getProperty('uEPGSplash') == 'True': return
        # setProperty('uEPGSplash_Progress',str(int(round(percent, -1))))
        # return    
    elif getProperty('uEPGRunning') == 'True':
        if control: percent = 100
        else: return
    if size < 50: return ProgressDialogBG(percent, control, string1, header)
    else: return ProgressDialog(percent, control, string1, string2, string3, header)

def poolList(method, items):
    results = []
    if ENABLE_POOL:
        pool = ThreadPool(cpu_count())
        results = pool.imap_unordered(method, items)
        pool.close()
        pool.join()
    else:
        log('poolList, No Pool Support!')
        results = [method(item) for item in items]
    results = filter(None, results)
    return results

def poolListItem(items):
    return poolList(buildListItem, items)
    
def buildListItem(item, mType='video'):
    log('buildListItem')
    item       = dict(item)
    art        = (item.get('art','')                 or {})
    streamInfo = (dict(item).get('streamdetails','') or {})
    item.pop('art',{})
    item.pop('streamdetails',{})
    isHDHR = (item.get('ishdhomerun','False'))
    listitem = xbmcgui.ListItem()
    #todo json query returns invalid formats not compatiblity with xbmcgui.iistitems
    #clean and check json compatiblity. todo ast? eval? dict value comparison?
    for key in item.keys():
        if key.lower() not in ITEM_TYPES: item.pop(key,{})
    for key in art.keys():
        if key.lower() not in JSON_ART: art.pop(key,{})
    for key, value in streamInfo.iteritems():
        for value in value: listitem.addStreamInfo(key, value)
    listitem.addContextMenuItems(loadJson(item.get('contextmenu','[]')))
    listitem.setProperty("IsPlayable","true")
    listitem.setProperty("IsInternetStream","true")
    listitem.setProperty("IsHDHomerun",isHDHR)
    listitem.setPath(item.get('url','') or item.get('path','') or '')
    listitem.setInfo(type=mType, infoLabels=item)
    listitem.setArt(art)
    return listitem
    
    
class RPCHelper(object):
    def __init__(self):
        self.cache       = SimpleCache()
        self.channelname = ''
        self.duration    = 0
        
     
    def escapeDirJSON(self, dir_name):
        mydir = uni(dir_name)
        if (mydir.find(":")): mydir = mydir.replace("\\", "\\\\")
        return mydir

        
    def getFileList(self, path, life, media='video', ignore='false', method='random', order='ascending', end=0, start=0, filter={}):
        log('getFileList, path = ' + path)
        json_response = self.requestList(path, life, media='video', ignore='false', method='random', order='ascending', end=0, start=0, filter={})
        if 'result' in json_response and 'files' in json_response['result']:
            items = json_response['result']['files']
            return poolList(RPCHelper().buildFileList, items)
            
            
    def buildFileList(self, item):
        try:
            file     = item.get('file','')
            label    = (item.get('label','')    or item.get('title',''))
            fileType = (item.get('filetype','') or '')
            if fileType == 'file':
                item["duration"]      = int(item.get('duration','')            or item.get('runtime','')  or '0')
                try: dataTags = loadJson(unquote((item.get('tagline','')       or {})))
                except: dataTags = {}
                item["channelname"]   = (dataTags.get('channelname','')        or self.channelname)
                item["channellogo"]   = (dataTags.get('channellogo','')        or '')
                item["channelnumber"] = (dataTags.get('channelnumber','')      or '')
                item["starttime"]     = (dataTags.get('starttime','')          or '')
                item["isnew"]         = (dataTags.get('isnew','')              or False)
                item["isfavorite"]    = (dataTags.get('isfavorite','')         or False)
                item["label"]         = (dataTags.get('label','')              or label)
                item["label"]         = (dataTags.get('label','')              or label)
                item["label2"]        = (dataTags.get('label2','')             or item.get('label2','')   or '')
                item["rating"]        = float(item.get('rating','0')           or '0')
                # self.duration += item["duration"]
                return item
            elif fileType == 'directory':
                # self.duration    = 0
                self.channelname = label
                return self.getFileList(file, datetime.timedelta(minutes=15))
        except Exception as e: log("getFileList, failed! " + str(e), xbmc.LOGERROR)

        
    def requestList(self, path, life, media='video', ignore='false', method='random', order='ascending', end=0, start=0, filter={}):
        log('requestList')
        json_query = ('{"jsonrpc":"2.0","method":"Files.GetDirectory","params":{"directory":"%s","media":"%s","properties":%s,"sort":{"ignorearticle":%s,"method":"%s","order":"%s"},"limits":{"end":%s,"start":%s}},"id":1}' % (self.escapeDirJSON(path), media, JSON_FILE_INTRO, ignore, method, order, end, start))
        return loadJson(self.cacheJSON(json_query, life))

        
    def sendJSON(self, command):
        log('sendJSON')
        data = ''
        try: data = xbmc.executeJSONRPC(uni(command))
        except UnicodeEncodeError: data = xbmc.executeJSONRPC(ascii(command))
        return (uni(data))
             
             
    def cacheJSON(self, command, life=datetime.timedelta(minutes=15)):
        log('cacheJSON')
        cacheResponce = self.cache.get(ADDON_NAME + '.cacheJSON, command = %s'%(command))
        if not cacheResponce or DEBUG == True:
            data = self.sendJSON(command)
            self.cache.set(ADDON_NAME + '.cacheJSON, command = %s'%(command), ((data)), expiration=life)
        return self.cache.get(ADDON_NAME + '.cacheJSON, command = %s'%(command))
        
        
class HDHR(object):
    def __init__(self):
        self.pyHDHR = PyHDHR.PyHDHR()
        

    def hasHDHR(self):
        return len((self.pyHDHR.getTuners() or '')) > 0


    def getLiveURL(self, channel):
        return self.pyHDHR.getLiveTVURL(str(channel))


    def getChannelInfo(self, channel):
        return self.pyHDHR.getChannelInfo(str(channel))
        
        
    def getChannelItems(self):
        channels = self.pyHDHR.getChannelList()
        return poolList(HDHR().buildChannelItems, channels)
        
        
    def buildChannelItems(self, channel):
        try:
            newChannel = {}
            guidedata  = []
            chan       = self.getChannelInfo(str(channel))
            isFavorite = chan.getFavorite() == 1
            if not isFavorite: return
            isHD       = chan.getHD() == 1
            hasCC      = True
            logo       = (chan.getImageURL() or ICON)
            newChannel['channelname']   = (chan.getAffiliate() or chan.getGuideName() or chan.getGuideNumber() or 'N/A')
            newChannel['channelnumber'] = ('%f' % float(chan.getGuideNumber())).rstrip('0').rstrip('.')
            newChannel['channellogo']   = logo
            newChannel['isfavorite']    = isFavorite
            newChannel['ishdhr']        = True
            for program in chan.getProgramInfos():
                tmpdata = {}
                starttime              = float(program.getStartTime())
                endtime                = float(program.getEndTime())
                runtime                = int(endtime - starttime)
                airdate                = float(program.getOriginalAirdate())
                if (starttime + runtime) < time.time(): continue
                tmpdata['label']       = program.getTitle()
                tmpdata['title']       = '%s - %s'%(program.getTitle(), program.getEpisodeTitle()) if len(program.getEpisodeTitle() or '') > 0 else program.getTitle()
                tmpdata['endtime']     = endtime
                tmpdata['starttime']   = starttime
                tmpdata['duration']    = runtime
                try: mtype             = MTYPES[program.getEpisodeNumber()[:2]]
                except: mtype = 'episode'
                tmpdata['mediatype']   = mtype
                tmpdata['url']         = chan.getURL()
                tmpdata['label2']      = "HD" if isHD else ""
                tmpdata['aired']       = (datetime.datetime.fromtimestamp((airdate or starttime))).strftime('%Y-%m-%d')
                thumb                  = (program.getImageURL() or logo)
                tmpdata['art']         = {"thumb":thumb,"poster":thumb,"clearlogo":logo}
                tmpdata['genre']       = []
                tmpdata['plot']        = trimString(program.getSynopsis())
                tmpdata['ishdhomerun'] = 'okay'
                isNEW = False
                if airdate > 0: isNEW  = ((int(airdate)) + 48*60*60) > int(starttime)
                if "*" in tmpdata['label'] and isNEW == False: isNEW = True
                guidedata.append(tmpdata)
            newChannel['guidedata'] = guidedata
            return newChannel
        except Exception as e: log("getChannelItems failed! " + str(e), xbmc.LOGERROR)