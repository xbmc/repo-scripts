import re, urllib2, urllib, httplib, sys, os, time
import xbmc 
import xbmcgui 
import xbmcaddon
import simplejson
import json

try:
    from hashlib import sha1
except ImportError:
    from sha import new as sha1

__settings__ = xbmcaddon.Addon()
__language__ = __settings__.getLocalizedString
c_refresh = __settings__.getSetting("32012")
c_runasservice = __settings__.getSetting("32011")
sleeptime = int(c_refresh)*3600000
micronap = 60000

#I want my strings back please
def _getstr(id):
    return str(__language__(id))

if len(sys.argv) != 2:
    xbmc.sleep(1000)
    xbmc.log(msg=_getstr(30002),level=xbmc.LOGNOTICE)

###################################################################
############################ FUNCTIONS ############################
###################################################################
#test for interwebs
def internet_test(url):
    try:
        response=urllib2.urlopen(url,timeout=1)
        return True
    except urllib2.URLError as err: pass
    if len(sys.argv) == 2:
        dialog = xbmcgui.Dialog() 
        ok = dialog.ok(_getstr(30000),url + _getstr(30001))
    xbmc.log(msg= "TAG-GEN: " + url + _getstr(30001),level=xbmc.LOGNOTICE)
    sys.exit(url + _getstr(30001))

#stops the music
def stopmusic():
    playlist = xbmc.PlayList( xbmc.PLAYLIST_MUSIC )
    playlist.clear()
    xbmc.Player().stop()

# cancels script and stops the music
def ifcancel():
    if len(sys.argv) == 2:
        if (pDialog.iscanceled()):
            if "true" in c_bgmusic:
                stopmusic()
            xbmc.log(msg= _getstr(30003),level=xbmc.LOGNOTICE)
            sys.exit(_getstr(30003))

#starts the music
def playmusic():
    path=__settings__.getAddonInfo('path')
    file = path + "/music.mp3"
    playlist = xbmc.PlayList( xbmc.PLAYLIST_MUSIC )
    playlist.clear()
    playlist.add(file)
    playlist.add(file)
    playlist.add(file)
    playlist.add(file)
    playlist.add(file)
    xbmc.Player().play( playlist)

#def to make a debug log
def debuglog(string):
    if "true" in c_debug:
        xbmc.log(msg=string,level=xbmc.LOGNOTICE)

#make lists sorted and unique
def unique(it):
    return dict(map(None,it,[])).keys()
def sorted(it):
    alist = [item for item in it]
    alist.sort()
    return alist

# A function to overwrite EVERY tag found in the database with a blank [] tag.    
def wipealltags():
    counter = 0
    Medialist = getxbmcdb()
    for movie in Medialist:
        ifcancel()
        json_query = '{"jsonrpc": "2.0", "id": "libMovies", "method": "VideoLibrary.SetMovieDetails", "params": {"movieid" : replaceid, "tag":[]}}'
        json_query = unicode(json_query, 'utf-8', errors='ignore')
        xbmcid = (json.dumps(movie.get('xbmcid','')))
        json_query = re.sub('replaceid', xbmcid, json_query)
        jsonobject=simplejson.loads(xbmc.executeJSONRPC(json_query))
        if len(sys.argv) == 2:
            counter = counter + 1
            percent = (100 * int(counter) / int(len(Medialist)))
            pDialog.update (percent," ",_getstr(30005) + str(counter) + "/" + str(len(Medialist)) + _getstr(30006))
    return counter

# dump the entire XBMC library to a big fat python list of dicts
def getxbmcdb():
    if "true" in wipeout:
        pDialog.update (0,_getstr(30007)," "," ")
    elif len(sys.argv) == 2:
        pDialog.update (0,_getstr(30008)," "," ")
    json_query = xbmc.executeJSONRPC('{"jsonrpc": "2.0", "method": "VideoLibrary.GetMovies","params": {"properties" : ["tag","imdbnumber"], "sort": { "order": "ascending", "method": "label", "ignorearticle": true } }, "id": "libMovies"}')
    json_query = unicode(json_query, 'utf-8', errors='ignore')
    jsonobject = simplejson.loads(json_query)
    Medialist = []
    if jsonobject['result'].has_key('movies'):
        for item in jsonobject['result']['movies']:
            ifcancel()
            Medialist.append({'xbmcid': item.get('movieid',''),'imdbid': item.get('imdbnumber',''),'name': item.get('label',''),'tag': item.get('tag','')})
    return Medialist

#def to fetch the names of the custom trakt lists
def gettraktlists(traktuser, traktpass):
    if len(sys.argv) == 2:
        pDialog.update (0,_getstr(30009)," "," ")
    listurl = "https://api.trakt.tv/user/lists.json/b6135e0f7510a44021fac8c03c36c81a17be35d9/" + traktuser
    debuglog(_getstr(30090) + listurl)
    list_args = {'username': traktuser, 'password': traktpass}
    listdata = urllib.urlencode(list_args)
    listrequest = urllib2.Request(listurl, listdata)
    listresponse = urllib2.urlopen(listrequest)
    listhtml = listresponse.read()
    listjson = simplejson.loads(listhtml)
    traktlistinfo = []
    if len(listjson) > 0:
        for item in listjson:
            ifcancel()
            traktlistinfo.append({'listname': item.get('name',''),'listslug': item.get('slug','')})
            debuglog(_getstr(30091) + (json.dumps(item.get('name',''))) + _getstr(30092) + (json.dumps(item.get('slug',''))))
    return traktlistinfo

#def to return the contents of a custom Trakt list
def readtraktlists(traktuser, traktpass, slug):
    if len(sys.argv) == 2:
        pDialog.update (0,_getstr(30010) + slug," "," ")
    ifcancel()
    listurl = "https://api.trakt.tv/user/list.json/b6135e0f7510a44021fac8c03c36c81a17be35d9/" + traktuser + "/" + slug[1:-1]
    debuglog(_getstr(30011) + listurl)
    list_args = {'username': traktuser, 'password': traktpass}
    listdata = urllib.urlencode(list_args)
    listrequest = urllib2.Request(listurl, listdata)
    listresponse = urllib2.urlopen(listrequest)
    listhtml = listresponse.read()
    listjson = simplejson.loads(listhtml)
    traktlist = []
    for item in listjson['items']:
        ifcancel()
        traktlist.append({'imdbid': item['movie'].get('imdb_id',''),'name': item['movie'].get('title','')})
        debuglog(_getstr(30012) + (json.dumps(item['movie'].get('title',''))) + " " + listurl)
    return traktlist

#def to fetch Trakt movies from primary Movie watchlist
def gettrakt(traktuser, traktpass):
    if len(sys.argv) == 2:
        pDialog.update (0,_getstr(30013)," "," ")
    movieurl = "https://api.trakt.tv/user/watchlist/movies.json/b6135e0f7510a44021fac8c03c36c81a17be35d9/" + traktuser
    movie_args = {'username': traktuser, 'password': traktpass}
    moviedata = urllib.urlencode(movie_args)
    movierequest = urllib2.Request(movieurl, moviedata)
    movieresponse = urllib2.urlopen(movierequest)
    moviehtml = movieresponse.read()
    moviejson = simplejson.loads(moviehtml)
    traktlist = []
    for item in moviejson:
        ifcancel()
        traktlist.append({'imdbid': item.get('imdb_id',''),'name': item.get('title','')})
        debuglog(_getstr(30012) + (json.dumps(item.get('title',''))) + _getstr(30015) + movieurl)
    return traktlist

# write tags for locally found movies given a Trakt watchlist, local media list and the new tag to write
def writetrakttags(traktlist, Medialist, newtrakttag):
    if len(sys.argv) == 2:
        pDialog.update (0,_getstr(30016)," "," ")
    moviecount = 0
    counter = 0
    for traktitem in traktlist:
        ifcancel()
        traktimdbid = (json.dumps(traktitem.get('imdbid','')))
        counter = counter + 1
        for movie in Medialist:
            xbmcimdbid = (json.dumps(movie.get('imdbid','')))
            xbmcid = (json.dumps(movie.get('xbmcid','')))
            xbmctag = (json.dumps(movie.get('tag','')))
            xbmcname = (json.dumps(movie.get('name','')))
            if (traktimdbid in xbmcimdbid) and (newtrakttag not in xbmctag):
                moviecount = moviecount + 1
                percent = (100 * int(counter) / int(len(traktlist)))
                if len(sys.argv) == 2:
                    pDialog.update (percent,"","",_getstr(30017) + str(newtrakttag) + _getstr(30018) + str(moviecount) + _getstr(30025))
                debuglog(_getstr(30017) + newtrakttag + _getstr(30020) + xbmcname)
                writetags(xbmcid, newtrakttag, xbmctag[1:-1])
            else:
                percent = (100 * int(counter) / int(len(traktlist)))
                debuglog(_getstr(30021) + newtrakttag + _getstr(30022) + xbmcname + _getstr(30023) + xbmctag)
            if len(sys.argv) == 2:
                pDialog.update (percent,"",_getstr(30024) + str(counter) + "/" + str(len(traktlist)) + _getstr(30025))
    return moviecount

# def to write tags via json. Requires the xbmcid, the existing xbmctag and the new tag
def writetags(xbmcid, newtag, xbmctag):
    ifcancel()
    jsonurl='{"jsonrpc": "2.0", "id": 1, "method": "VideoLibrary.SetMovieDetails", "params": {"movieid" : replaceid, "tag":replacetag}}'
    jsonurl=re.sub('replaceid', xbmcid, jsonurl)
    if len(xbmctag) > 2:
        jsonurl=re.sub('replacetag', '[' + xbmctag + "," + '"' + newtag + '"]', jsonurl)
    else:
        jsonurl=re.sub('replacetag', '["' + newtag + '"]', jsonurl)
    jsonresponse=simplejson.loads(xbmc.executeJSONRPC(jsonurl))

# Scrapes IMDB given a URL and a scrape count (counter for how many times it has run)
def scrapeimdb(imdburl, scrapecount):
    if len(sys.argv) == 2:
        pDialog.update (0,_getstr(30026)," ", " ")
    ifcancel()
    listid=imdburl.split('/')[4]
    opener = urllib2.build_opener()
    opener.addheaders = [('User-agent', 'Mozilla/5.0')]
    infile = opener.open(imdburl)
    imdbpage=infile.read()
    infile.close()
    global imdbuser
    imdbuser = re.findall(r'<title>IMDb: (.+?)&#x27;s Watchlist</title>', imdbpage)
    imdblist = re.findall(r'<a href="/title/(tt[0-9]{7})/">.+?</a>', imdbpage)
    imdblist = sorted(unique(imdblist))
    debuglog(_getstr(30027) + str(imdbuser) + _getstr(30028) + str(imdburl) + ": " + str(imdblist))
    return imdblist

# Scrapes IMDB given a URL and a scrape count (counter for how many times it has run)
def scrapeimdbrss(imdburl, scrapecount):
    internet_test("http://rss.imdb.com")
    if len(sys.argv) == 2:
        pDialog.update (0,_getstr(30026)," ", " ")
    ifcancel()
    try:
        listid=imdburl.split('/')[4]
        opener = urllib2.build_opener()
        opener.addheaders = [('User-agent', 'Mozilla/5.0')]
        infile = opener.open(imdburl)
        imdbpage=infile.read()
        infile.close()
        global imdbuser
        imdbuser = re.findall(r'<link>.+/(ur[0-9]{8})/.+/link>', imdbpage)
        imdblist = re.findall(r'<guid>.+(tt[0-9]{7})/</guid>', imdbpage)
        imdblist = sorted(unique(imdblist))
        debuglog(_getstr(30027) + str(imdbuser) + _getstr(30028) + str(imdburl) + ": " + str(imdblist))
        return imdblist
    except:
        if len(sys.argv) == 2:
            dialog = xbmcgui.Dialog()
            ok = dialog.ok(_getstr(30000),imdburl + _getstr(30029))
        xbmc.log(msg= "TAG-GEN: " + imdburl + _getstr(30029),level=xbmc.LOGNOTICE)
        sys.exit(imdburl + _getstr(30029))

# write tags for locally found movies given an imdb watchlist, local media list and the new tag to write
def writeimdbtags(imdblist, Medialist, newimdbtag):
    if len(sys.argv) == 2:
        pDialog.update (0,_getstr(30030) + str(imdbuser)[2:-2] + _getstr(30031))
    moviecount = 0
    counter = 0
    for webimdbid in imdblist:
        ifcancel()
        counter = counter + 1
        for movie in Medialist:
            xbmcimdbid = (json.dumps(movie.get('imdbid','')))
            xbmcid = (json.dumps(movie.get('xbmcid','')))
            xbmctag = (json.dumps(movie.get('tag','')))
            xbmcname = (json.dumps(movie.get('name','')))
            if (webimdbid in xbmcimdbid) and (newimdbtag not in xbmctag):
                moviecount = moviecount + 1
                debuglog(_getstr(30032) + newimdbtag + _getstr(30033) + xbmcname + _getstr(30034) + str(imdbuser)[2:-2] + _getstr(30035))
                percent = (100 * int(counter) / int(len(imdblist)))
                if len(sys.argv) == 2:
                    pDialog.update (percent,"","",_getstr(30036) + str(newimdbtag) + _getstr(30037) + str(moviecount) + _getstr(30038))
                writetags(xbmcid, newimdbtag, xbmctag[1:-1])
            else:
                percent = (100 * int(counter) / int(len(imdblist)))
                debuglog(_getstr(30039) + newimdbtag + _getstr(30040) + xbmcname + _getstr(30041) + xbmctag + _getstr(30042) + str(imdbuser)[2:-2] + _getstr(30043))
            if len(sys.argv) == 2:
                pDialog.update (percent,"",_getstr(30044) + str(counter) + "/" + str(len(imdblist)) + _getstr(30045))
    return moviecount

# Scrapes Wikipedia URLs for comedian names given a single url
def scrapewiki():
    internet_test("http://en.wikipedia.org")
    if len(sys.argv) == 2:
        pDialog.update (0,_getstr(30046)," "," ")
    comiclist = []
    for wikiurl in wikiurllist:
        ifcancel()
        try:
            opener = urllib2.build_opener()
            opener.addheaders = [('User-agent', 'Mozilla/5.0')]
            infile = opener.open(wikiurl)
            page=infile.read()
            infile.close()
            results = (re.findall(r'<li><a href="/wiki/.+?" title=".+?">((?!.*List.*|.*rticle.*|.*omedian.*)\b.+?\b.+?)</a></li>', page))
            for comic in results:
                ifcancel()
                debuglog(_getstr(30047) + comic + _getstr(30048) + wikiurl)
                comiclist.append(comic)
            comiclist = sorted(unique(comiclist))
        except:
            if len(sys.argv) == 2:
                dialog = xbmcgui.Dialog()
                ok = dialog.ok(_getstr(30000),wikiurl + _getstr(30049))
            xbmc.log(msg= "TAG-GEN: " + wikiurl + _getstr(30049),level=xbmc.LOGNOTICE)
            sys.exit(wikiurl + _getstr(30049))
    return comiclist

# write tags for locally found Stand-up movies given list of comedians, local media list and the new tag to write
def writestanduptags(comiclist, Medialist, newwikitag):
    if len(sys.argv) == 2:
        pDialog.update (0,_getstr(30050)," "," ")
    comicmatches = 0
    counter = 0
    for comic in comiclist:
        ifcancel()
        counter = counter + 1
        for movie in Medialist:
            xbmcname = (json.dumps(movie.get('name','')))
            xbmcid = (json.dumps(movie.get('xbmcid','')))
            xbmctag = (json.dumps(movie.get('tag','')))
            if (comic in xbmcname) and (newwikitag not in xbmctag):
                comicmatches = comicmatches + 1
                debuglog(_getstr(30051) + comic + _getstr(30052) + xbmcname + _getstr(30053))
                xbmctag = xbmctag[1:-1]
                percent = (100 * int(counter) / int(len(comiclist)))
                if len(sys.argv) == 2:
                    pDialog.update (percent,"","",_getstr(30054) + str(newwikitag) + _getstr(30055) + str(comicmatches) + _getstr(30056))
                    pDialog.update (percent,"",_getstr(30057) + str(counter) + "/" + str(len(comiclist)) + _getstr(30058))
                    writetags(xbmcid, newwikitag, xbmctag)
            else:
                percent = (100 * int(counter) / int(len(comiclist)))
                debuglog(_getstr(30059) + comic + _getstr(30060) + xbmcname + _getstr(30061) + xbmctag)
                if len(sys.argv) == 2:
                    pDialog.update (percent,"",_getstr(30057) + str(counter) + "/" + str(len(comiclist)) + _getstr(30058))
    return comicmatches

###################################################################
########################## END FUNCTIONS ##########################
###################################################################

# These are the URLs that we will be searching for comedians
wikiurllist=["http://en.wikipedia.org/wiki/List_of_British_stand-up_comedians",
"http://en.wikipedia.org/wiki/List_of_stand-up_comedians",
"http://en.wikipedia.org/wiki/List_of_Australian_stand-up_comedians",
"http://en.wikipedia.org/wiki/List_of_Canadian_stand-up_comedians",
"http://en.wikipedia.org/wiki/List_of_United_States_stand-up_comedians"]

monitor = xbmc.Monitor()
while not monitor.abortRequested():
    if (c_runasservice != "true") and len(sys.argv) != 2:
        xbmc.log(msg= _getstr(30062),level=xbmc.LOGNOTICE)
        sys.exit(_getstr(30062))
    xbmc.log(msg= _getstr(30063),level=xbmc.LOGNOTICE)
    URLID=32050
    TAGID=32080
    comiccount = 0
    moviecount = 0
    c_imdburl = __settings__.getSetting(str(URLID))
    c_imdbtag = __settings__.getSetting(str(TAGID))
    c_standup = __settings__.getSetting("32015")
    c_standuptag = __settings__.getSetting("32016")
    c_plusurl = __settings__.getSetting("32013")
    c_minusurl = __settings__.getSetting("32014")
    c_urlcount =  __settings__.getSetting("32099")
    c_useimdb =  __settings__.getSetting("32020")
    #c_bgmusic = __settings__.getSetting("32021")
    c_bgmusic = "false"
    c_usetrakt = "false"
    #c_usetrakt = __settings__.getSetting("32023")
    # c_trakttag = __settings__.getSetting("32024")
    #c_traktuser = __settings__.getSetting("32025")
    # c_traktpass = sha1(__settings__.getSetting("32026")).hexdigest()
    # c_usetraktlists = __settings__.getSetting("32029")
    c_usetraktlists="false"
    c_debug = __settings__.getSetting("32030")
    manual = "false"
    wipeout = "false"

# Initialise IMDB URL list, add extra to list if specified by settings.xml. 
# Also make a list out of the user-defined tags
    listurlcount = int(c_urlcount)
    imdburllist = []
    imdbtaglist = []
    while listurlcount > -1:
        imdburllist.append(c_imdburl)
        imdbtaglist.append(c_imdbtag)
        URLID=URLID+1
        TAGID=TAGID+1
        c_imdburl = __settings__.getSetting(str(URLID))
        c_imdbtag = __settings__.getSetting(str(TAGID))
        listurlcount = listurlcount -1

#command line arguments for manual/tag delete executions
    if len(sys.argv) == 2:
        if "manual" in sys.argv[1]:
            if "true" in c_bgmusic:
                playmusic()
            manual = "true"
            pDialog = xbmcgui.DialogProgress()
            ret = pDialog.create("Tag Generator", _getstr(30064))
        elif "wipeout" in sys.argv[1]:
            if "true" in c_bgmusic:
                playmusic()
                wipeout = "true"
            if xbmcgui.Dialog().yesno("Tag Generator", _getstr(30065)):
                if xbmcgui.Dialog().yesno("Tag Generator", _getstr(30066)):
                    if "true" in c_bgmusic:
                        playmusic()
                    pDialog = xbmcgui.DialogProgress()
                    pDialog.create("Tag Generator", _getstr(30067))
                    xbmc.log(msg= _getstr(30068),level=xbmc.LOGNOTICE)
                    wipedcount = wipealltags()
                    xbmc.log(msg= _getstr(30093),level=xbmc.LOGNOTICE)
                    sys.exit(_getstr(30093))
                else:
                    stopmusic()
                    xbmc.log(msg= _getstr(30069),level=xbmc.LOGNOTICE)
                    sys.exit(_getstr(30069))
            else:
                stopmusic()
                xbmc.log(msg= _getstr(30069),level=xbmc.LOGNOTICE)
                sys.exit(_getstr(30069))
        elif "trakt" in sys.argv[1]:
            pDialog = xbmcgui.DialogProgress()
            ret = pDialog.create("Tag Generator", _getstr(30064))
            if "true" in c_bgmusic:
                playmusic()
            xbmc.log(msg= _getstr(30070),level=xbmc.LOGNOTICE)
            Medialist = getxbmcdb()
            if "true" in c_usetrakt:
                traktlist = gettrakt(c_traktuser, c_traktpass)
                moviecount = writetrakttags(traktlist, Medialist, c_trakttag)
            if "true" in c_usetraktlists:
                traktlistinfo = gettraktlists(c_traktuser, c_traktpass)
                if len (traktlistinfo) > 0:
                    for item in traktlistinfo:
                        slug = (json.dumps(item.get('listslug','')))
                        name = (json.dumps(item.get('listname','')))
                        traktlist = readtraktlists(c_traktuser, c_traktpass, slug)
                        moviecount = writetrakttags(traktlist, Medialist, name[1:-1])
                else:
                    xbmc.log(msg= _getstr(30071),level=xbmc.LOGNOTICE)
            stopmusic()
            sys.exit(_getstr(30072))
        elif "standup" in sys.argv[1]:
            pDialog = xbmcgui.DialogProgress()
            ret = pDialog.create("Tag Generator", _getstr(30064))
            if "true" in c_bgmusic:
                playmusic()
            xbmc.log(msg= _getstr(30073),level=xbmc.LOGNOTICE)
            Medialist = getxbmcdb()
            newwikitag = c_standuptag
            comedians = scrapewiki()
            comiccount = writestanduptags(comedians, Medialist, newwikitag)
            stopmusic()
            sys.exit(_getstr(30075))
        elif "imdb" in sys.argv[1]:
            pDialog = xbmcgui.DialogProgress()
            ret = pDialog.create("Tag Generator", _getstr(30064))
            if "true" in c_bgmusic:
                playmusic()
            xbmc.log(msg= _getstr(30074),level=xbmc.LOGNOTICE)
            Medialist = getxbmcdb()
            scrapecount = 0
            for imdburl in imdburllist:
                newimdbtag = imdbtaglist[scrapecount]
                imdblist = scrapeimdbrss(imdburl, scrapecount)
                moviecount = writeimdbtags(imdblist, Medialist, newimdbtag)
                scrapecount = scrapecount + 1
            stopmusic()
            sys.exit(_getstr(30076))
        else:
            xbmc.log(msg= _getstr(30077),level=xbmc.LOGNOTICE)

#### Read the local XBMC DB ####
    Medialist = getxbmcdb()

#### IMDB tag writing ####
    if ("true" in c_useimdb) and ("false" in wipeout):
        xbmc.log(msg= _getstr(30074),level=xbmc.LOGNOTICE)
        scrapecount = 0
        moviecount = 0
        for imdburl in imdburllist:
            newimdbtag = imdbtaglist[scrapecount]
            imdblist = scrapeimdbrss(imdburl, scrapecount)
            moviecount = moviecount + writeimdbtags(imdblist, Medialist, newimdbtag)
            scrapecount = scrapecount + 1
    else:
        xbmc.log(msg= _getstr(30078),level=xbmc.LOGNOTICE)
        moviecount = 0

#### Stand-up Comedy tag writing ####
    if ("true" in c_standup) and ("false" in wipeout):
        newwikitag = c_standuptag
        xbmc.log(msg= _getstr(30073),level=xbmc.LOGNOTICE)
        comedians = scrapewiki()
        comiccount = writestanduptags(comedians, Medialist, newwikitag)
    else:
        xbmc.log(msg= _getstr(30079),level=xbmc.LOGNOTICE)

#### Trakt movies tag writing ####
    if ("true" in c_usetrakt or c_usetraktlists) and ("false" in wipeout):
        if "true" in c_usetrakt:
            traktlist = gettrakt(c_traktuser, c_traktpass)
            moviecount = moviecount + writetrakttags(traktlist, Medialist, c_trakttag)
        if "true" in c_usetraktlists:
            traktlistinfo = gettraktlists(c_traktuser, c_traktpass)
            if len (traktlistinfo) > 0:
                for item in traktlistinfo:
                    slug = (json.dumps(item.get('listslug','')))
                    name = (json.dumps(item.get('listname','')))
                    traktlist = readtraktlists(c_traktuser, c_traktpass, slug)
                    moviecount = moviecount + writetrakttags(traktlist, Medialist, name[1:-1])
            else:
                xbmc.log(msg= _getstr(30071),level=xbmc.LOGNOTICE)
    else:
        xbmc.log(msg= _getstr(30080),level=xbmc.LOGNOTICE)

    if "true" in manual:
        if "true" in c_bgmusic:
            stopmusic()
        dialog = xbmcgui.Dialog()
        ok = dialog.ok("Tag Generator", _getstr(30081)+str(moviecount)+_getstr(30082) + str(comiccount)+_getstr(30083))
        xbmc.log(msg= _getstr(30084),level=xbmc.LOGNOTICE)
        sys.exit(_getstr(30084))
   
    elif "true" in wipeout:
        if "true" in c_bgmusic:
            stopmusic()
            dialog = xbmcgui.Dialog()
            ok = dialog.ok("Tag Generator", _getstr(30085)+str(wipedcount)+_getstr(30086))
            xbmc.log(msg= _getstr(30087),level=xbmc.LOGNOTICE)
            sys.exit(_getstr(30087))
   
    else:
        xbmc.log(msg= _getstr(30088)+str(c_refresh)+_getstr(30089),level=xbmc.LOGNOTICE)
        while (sleeptime > 0 and not monitor.abortRequested()):
            xbmc.sleep(micronap)
            sleeptime = sleeptime - micronap 
