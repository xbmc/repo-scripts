# -*- coding: utf-8 -*- 

import os
import sys
import xbmc
import urllib
import xbmcvfs
import xbmcaddon
import xbmcgui
import xbmcplugin
import shutil
import unicodedata
import urllib.parse
import time
import re
from difflib import SequenceMatcher
from resources.lib.Subscene import *

ADD_ON = xbmcaddon.Addon()
SCRIPT_ID = ADD_ON.getAddonInfo('id')
SCRIPT_NAME = ADD_ON.getAddonInfo('name')
PROFILE = xbmc.translatePath(ADD_ON.getAddonInfo('profile'))
TEMP = xbmc.translatePath(PROFILE)
START_TIME = time.time()
DOMAIN_NAME = ADD_ON.getSetting("SDomain")


subscene_languages = {
    'Armenian':                 {'3let': 'arm', '2let': 'am'},
    'Albanian':                 {'3let': 'alb', '2let': 'sq'},
    'Arabic':                   {'3let': 'ara', '2let': 'ar'},
    'Big 5 code':               {'3let': 'chi', '2let': 'zh'},
    'Brazillian Portuguese':    {'3let': 'por', '2let': 'pb'},
    'Bulgarian':                {'3let': 'bul', '2let': 'bg'},
    'Chinese BG code':          {'3let': 'chi', '2let': 'zh'},
    'Croatian':                 {'3let': 'hrv', '2let': 'hr'},
    'Czech':                    {'3let': 'cze', '2let': 'cs'},
    'Danish':                   {'3let': 'dan', '2let': 'da'},
    'Dutch':                    {'3let': 'dut', '2let': 'nl'},
    'English':                  {'3let': 'eng', '2let': 'en'},
    'Estonian':                 {'3let': 'est', '2let': 'et'},
    'Farsi/Persian':            {'3let': 'per', '2let': 'fa'},
    'Finnish':                  {'3let': 'fin', '2let': 'fi'},
    'French':                   {'3let': 'fre', '2let': 'fr'},
    'German':                   {'3let': 'ger', '2let': 'de'},
    'Greek':                    {'3let': 'gre', '2let': 'el'},
    'Hebrew':                   {'3let': 'heb', '2let': 'he'},
    'Hungarian':                {'3let': 'hun', '2let': 'hu'},
    'Icelandic':                {'3let': 'ice', '2let': 'is'},
    'Indonesian':               {'3let': 'ind', '2let': 'id'},
    'Italian':                  {'3let': 'ita', '2let': 'it'},
    'Japanese':                 {'3let': 'jpn', '2let': 'ja'},
    'Korean':                   {'3let': 'kor', '2let': 'ko'},
    'Lithuanian':               {'3let': 'lit', '2let': 'lt'},
    'Malay':                    {'3let': 'may', '2let': 'ms'},
    'Norwegian':                {'3let': 'nor', '2let': 'no'},
    'Polish':                   {'3let': 'pol', '2let': 'pl'},
    'Portuguese':               {'3let': 'por', '2let': 'pt'},
    'Romanian':                 {'3let': 'rum', '2let': 'ro'},
    'Russian':                  {'3let': 'rus', '2let': 'ru'},
    'Serbian':                  {'3let': 'scc', '2let': 'sr'},
    'Slovak':                   {'3let': 'slo', '2let': 'sk'},
    'Slovenian':                {'3let': 'slv', '2let': 'sl'},
    'Spanish':                  {'3let': 'spa', '2let': 'es'},
    'Swedish':                  {'3let': 'swe', '2let': 'sv'},
    'Thai':                     {'3let': 'tha', '2let': 'th'},
    'Turkish':                  {'3let': 'tur', '2let': 'tr'},
    'Vietnamese':               {'3let': 'vie', '2let': 'vi'}
}

subscene_episode_numbers = {
    '1' : ['First Season', 'First', 'first'],
    '2' : ['Second Season', 'Second', 'second'],
    '3' : ['Third Season', 'Third', 'third'],
    '4' : ['Fourth Season', 'Fourth', 'fourth'],
    '5' : ['Fifth Season', 'Fifth', 'fifth'],
    '6' : ['Sixth Season', 'Sixth', 'sixth'],
    '7' : ['Seventh Season', 'Seventh', 'seventh'],
    '8' : ['Eighth Season', 'Eighth', 'eighth'],
    '9' : ['Ninth Season', 'Ninth', 'ninth'],
    '10' : ['Tenth Season', 'Tenth', 'tenth'],
    '11' : ['Eleventh Season', 'Eleventh', 'eleventh'],
    '12' : ['Twelfth Season', 'Twelfth', 'twelfth'],
    '13' : ['Thirteenth Season', 'Thirteenth', 'thirteenth'],
    '14' : ['Fourteenth Season', 'Fourteenth', 'fourteenth'],
    '15' : ['Fifteenth Season', 'Fifteenth', 'fifteenth'],
    '16' : ['Sixteenth Season', 'Sixteenth', 'sixteenth'],
}

def log(module, msg):
    global START_TIME
    xbmc.log((u"### [%s] %f - %s" % (module, time.time() - START_TIME, msg,)), level=xbmc.LOGDEBUG)

def _xmbc_localized_string_utf8(string_id):
    return ADD_ON.getLocalizedString(string_id)

def _xbmc_notification(string_id, heading=SCRIPT_NAME, icon=xbmcgui.NOTIFICATION_INFO):
    message = _xmbc_localized_string_utf8(string_id)
    xbmcgui.Dialog().notification(heading, message, icon)

class Subtitle:
    def __init__(self, href, lang, name, no_of_files, hearing_imp, author, comment):
        self.href = href

        # first search in standard languages.
        self.lang = lang
        self.lang_2let = xbmc.convertLanguage(lang.strip(), xbmc.ISO_639_1)
        self.lang_3let = xbmc.convertLanguage(lang.strip(), xbmc.ISO_639_2)
        if self.lang_2let == "":
            try:
                self.lang_2let = subscene_languages[lang.strip()]['2let']
                self.lang_3let = subscene_languages[lang.strip()]['3let']
            except:
                log("Language", "Error identifying language %s" % lang.strip())
                pass

        self.name = name
        self.no_of_files = no_of_files
        self.hearing_imp = hearing_imp
        self.author = author
        self.comment = comment
        self.score = 0
    
    def compute_score(self, item):
        filename = item['file_original_path'].split("/")[-1]
        score = SequenceMatcher(None, filename, self.name).ratio()

        if not item['season']:
            # This is a movie.
            self.score = score
        else:
            # This is a tv show.
            self.score = score * 0.4
            season = int(item['season'])
            episode = int(item['episode'])

            # Try to find some marks to match season and episode.
            marks = [
                "Season%02dEpisode%02d" % (season, episode),
                "S%02dE%02d" % (season, episode),
                "%02dx%02d" % (season, episode)
            ]

            for mark in marks:
                if mark in self.name:
                    self.score += 0.6
                    return
    
    def __lt__(self, other):
        return self.score > other.score

    def rate(self):
        if self.score < 0.2:
            return "1"
        if self.score < 0.4:
            return "2"
        if self.score < 0.6:
            return "3"
        if self.score < 0.8:
            return "4"
        return "5"


def Search(item):
    tvshow = False
    service = SubsceneSubtitleService(DOMAIN_NAME)
    if item['manualsearch']:
        movies = service.SearchMovie(item['manualsearchstring'], item['year'])
    elif item['tvshow']:
        tvshow = True
        movies = service.SearchMovie(item['tvshow'], item['year'])
    else:
        movies = service.SearchMovie(item['title'], item['year'])
    year = item['year']
    # import web_pdb; web_pdb.set_trace()

    matches = []

    if not tvshow:
        # Searching in movies
        # Match for exact title
        if len(movies[TYPE_MATCH_EXACT]) > 0:
            for movie in movies[TYPE_MATCH_EXACT]:
                m = re.match(r"^.*\(([0-9\s]*)\).*", movie[0])
                if year.strip() == m.group(1).strip():
                    matches.append(movie)

        if len(matches) == 0:
            # No exact match, search for the most popular
            if len(movies[TYPE_MATCH_POPULAR]) > 0:
                for movie in movies[TYPE_MATCH_POPULAR]:
                    m = re.match(r"^.*\(([0-9\s]*)\).*", movie[0])
                    if year.strip() == m.group(1).strip():
                        matches.append(movie)
    else:
        # Searching tvshows
        if len(movies[TYPE_MATCH_TVSERIES]) > 0:
            for movie in movies[TYPE_MATCH_TVSERIES]:
                if subscene_episode_numbers[item['season']][0] in movie[0]:
                    matches.insert(0, movie)
                else:
                    matches.append(movie)


    if len(matches) == 0:
        idx = -1
    elif len(matches) == 1:
        idx = 0
    else:
        if not tvshow:
            title = _xmbc_localized_string_utf8(32004)
        else:
            title = _xmbc_localized_string_utf8(32005)
        idx = xbmcgui.Dialog().select(title, [m[0] for m in matches])

    if idx < 0:
        return

    url = matches[idx][1]
    allsubs = service.EnumSubtitles(DOMAIN_NAME + url)

    if allsubs is None:
        return

    # Filter subtitles based on their language
    filtered_subs = []
    for s in allsubs:
        subtitle = Subtitle(s[0], s[1], s[2], s[3], s[4], s[5], s[6])

        if subtitle.lang_3let not in item['3let_language']:
            continue
        subtitle.compute_score(item)
        filtered_subs.append(subtitle)

    
    # time to remove duplicates 
    mapped_subs = {}
    for subtitle in filtered_subs:
        if subtitle.href not in mapped_subs:
            # Add subtitle to dict
            mapped_subs[subtitle.href] = subtitle
        else:
            # Subtitle already exists, so we check the score, if this one has a higher score, it should replace the other one.
            if mapped_subs[subtitle.href].score < subtitle.score:
                mapped_subs[subtitle.href] = subtitle
    
    uniq_subs = []
    for v in list(mapped_subs.values()):
        uniq_subs.append(v)

    # sort uniq_subs based on their score.
    uniq_subs.sort()
            
    for subtitle in uniq_subs:
        listitem = xbmcgui.ListItem(
            label = subtitle.lang,  # language name for the found subtitle
            label2 = subtitle.name, # file name for the found subtitle
        )

        listitem.setArt({
            'icon': subtitle.rate(),    # rating for the subtitle, string 0-5
            'thumb': subtitle.lang_2let # language flag, ISO_639_1 language
        })
                                                        
        # indicates that sub is 100 Comaptible
        if subtitle.score == 1.0:
            listitem.setProperty( "sync", '{0}'.format(True).lower() )

        listitem.setProperty( "hearing_imp", '{0}'.format(subtitle.hearing_imp).lower() ) # set to "true" if subtitle is for hearing impared

        # below arguments are optional, it can be used to pass any info needed in download function
        # anything after "action=download&" will be sent to addon once user clicks listed subtitle to downlaod
        url = "plugin://%s/?action=download&link=%s&lang=%s" % (
            SCRIPT_ID,
            subtitle.href,
            subtitle.lang_2let
        )
        # add it to list, this can be done as many times as needed for all subtitles found
        xbmcplugin.addDirectoryItem(handle=int(sys.argv[1]),url=url,listitem=listitem,isFolder=False) 


def Download(subtitle_link):
    service = SubsceneSubtitleService(DOMAIN_NAME)
    sub_content = service.DownloadSubtitle(subtitle_link)

    subtitle_list = []
    if sub_content is None:
        _xbmc_notification(32002, xbmcgui.NOTIFICATION_WARNING)
        return subtitle_list

    # Cleanup temp dir, we recomend you download/unzip your subs in temp folder and
    # pass that to XBMC to copy and activate
    log("Download", "Removing temp dir %s" % (TEMP))
    if xbmcvfs.exists(TEMP):
        shutil.rmtree(TEMP)
    xbmcvfs.mkdirs(TEMP)

    tmp_file = os.path.join(TEMP, sub_content[0])
    file_handle = xbmcvfs.File(tmp_file, "wb")
    file_handle.write(sub_content[1])
    file_handle.close()
    
    # Extract subtitle.
    if os.path.splitext(tmp_file)[1].lower() in [".rar", ".zip"]:
        urlpath = urllib.parse.quote_plus(tmp_file)
        _, files = xbmcvfs.listdir('archive://%s' % (urlpath))
        for f in files:
            src = 'archive://' + urlpath + '/' + f
            dest = os.path.join(TEMP, f)
            xbmcvfs.copy(src, dest)

    extentions = [".srt", ".sub", ".txt", ".smi", ".ssa", ".ass"]
    for f in xbmcvfs.listdir(TEMP)[1]:
        if os.path.splitext(f)[1].lower() in extentions:
            path = os.path.join(TEMP, f)
            subtitle_list.append(path)

    if len(subtitle_list) == 0:
        _xbmc_notification(32002, xbmcgui.NOTIFICATION_WARNING)
    else:
        _xbmc_notification(32001)

    return subtitle_list
 
def normalizeString(string):
    return unicodedata.normalize('NFKD', string).encode('ascii','ignore')       
 
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

def GetCurrentItem():
    item = {}
    item['manualsearch'] = False
    item['year'] = xbmc.getInfoLabel("VideoPlayer.Year")                            # Year
    item['season'] = str(xbmc.getInfoLabel("VideoPlayer.Season"))                   # Season
    item['episode'] = str(xbmc.getInfoLabel("VideoPlayer.Episode"))                 # Episode
    item['tvshow'] = normalizeString(xbmc.getInfoLabel("VideoPlayer.TVshowtitle"))  # Show
    item['title']  = normalizeString(xbmc.getInfoLabel("VideoPlayer.Title"))        # Title 
    item['3let_language'] = []
    
    for lang in urllib.parse.unquote(params['languages']).split(","):
        item['3let_language'].append(xbmc.convertLanguage(lang,xbmc.ISO_639_2))
        
    if item['episode'].lower().find("s") > -1: # Check if season is "Special"
        item['season'] = "0"
        item['episode'] = item['episode'][-1:]

    item['file_original_path'] = urllib.parse.unquote(xbmc.Player().getPlayingFile())
    
    return item


# PLUGIN STARTS HERE
params = get_params()

if params['action'] == 'search' or params['action'] == 'manualsearch':
    item = GetCurrentItem() 
    if 'searchstring' in params:
        item['manualsearch'] = True
        item['manualsearchstring'] = params['searchstring']
    Search(item)    

elif params['action'] == 'download':
    # we pickup all our arguments sent from def Search()
    subs = Download(params["link"])
    sub = None
    if len(subs) == 1:
        sub = subs[0]
    elif len(subs) > 1:
        title = _xmbc_localized_string_utf8(32003)
        idx = xbmcgui.Dialog().select(title, [s.split("/")[-1] for s in subs])
        if idx >= 0:
            sub = subs[idx]
    if sub is not None:
        listitem = xbmcgui.ListItem(label=sub)
        xbmcplugin.addDirectoryItem(handle=int(sys.argv[1]),url=sub,listitem=listitem,isFolder=False)
        xbmcplugin.endOfDirectory(int(sys.argv[1])) ## send end of directory to XBMC
