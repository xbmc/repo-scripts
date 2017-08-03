import re, urllib2, urllib, httplib, sys, os, time
import xbmc 
import xbmcgui 
import xbmcaddon
import json
try:
    import simplejson
    import trakt
    from trakt import users
except:
    if os.name == "nt":
        slash = "\\"
    else:
        slash = "/"
    sys.path.append(os.path.abspath(os.path.dirname(__file__)+slash+"resources"+slash+"lib"))
    import simplejson
    import trakt
    from trakt import users

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

# cancels script
def ifcancel():
    if len(sys.argv) == 2:
        if (pDialog.iscanceled()):
            xbmc.log(msg= _getstr(30003),level=xbmc.LOGNOTICE)
            sys.exit(_getstr(30003))

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

# write tags for locally found movies given a Trakt watchlist, local media list and the new tag to write
def write_trakt_tags(traktlist, Medialist, newtrakttag):
    if len(sys.argv) == 2:
        pDialog.update (0,_getstr(30016)," "," ")
    moviecount = 0
    counter = 0
    for traktimdbid in traktlist:
        ifcancel()
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

    
# return imdb ids for movies in a given trakt list. Requires oauth token.    
def get_trakt_movies(user_name, list_name, token):
    trakt.core.AUTH_METHOD = trakt.core.OAUTH_AUTH
    trakt.core.OAUTH_TOKEN = token
    trakt.core.CLIENT_ID = trakt_client_id
    trakt.core.CLIENT_SECRET = trakt_client_secret
    target_list = list()
    if list_name.lower() == "watchlist":
        target_list = users.User(user_name).watchlist_movies
    else:
        target_list = users.User(user_name).get_list(list_name).get_items()
    found_ids = list()
    for item in target_list:
        imdb_id = item.ids["ids"]["imdb"]
        if not imdb_id in found_ids:
            found_ids.append(imdb_id)
            debuglog(_getstr(30012) + (str(item)) + _getstr(30015) + list_name)
    return found_ids

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
    internet_test("https://en.wikipedia.org")
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
wikiurllist=["https://en.wikipedia.org/wiki/List_of_British_stand-up_comedians",
"https://en.wikipedia.org/wiki/List_of_stand-up_comedians",
"https://en.wikipedia.org/wiki/List_of_Australian_stand-up_comedians",
"https://en.wikipedia.org/wiki/List_of_Canadian_stand-up_comedians",
"https://en.wikipedia.org/wiki/List_of_United_States_stand-up_comedians"]

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
    c_usetrakt = __settings__.getSetting("32023")
    trakt_list_start=32120
    trakt_tag_start=32140
    trakt_user_start=32160
    c_trakt_list = __settings__.getSetting(str(trakt_list_start))
    c_trakt_tag = __settings__.getSetting(str(trakt_tag_start))
    c_trakt_user = __settings__.getSetting(str(trakt_user_start))
    trakt.core.APPLICATION_ID = '12265'
    trakt_client_id = '8bc9b1371d9594b451c863bea2c95aa96ac5e5bf9ecee274daa23c0790386afe'
    trakt_client_secret = '6087cbfb47b8f0cdc1c0fc491ec52524c9d23bf37a8480a8c2827ea91312cbad'
    c_trakt_token = __settings__.getSetting("32031")
    c_trakt_list_count = __settings__.getSetting("32098")
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

# init trakt lists and tags        
    trakt_list_count = int(c_trakt_list_count)
    trakt_lists = list()
    trakt_tags = list()
    trakt_users = list()
    while trakt_list_count > -1:
        trakt_lists.append(c_trakt_list)
        trakt_tags.append(c_trakt_tag)
        trakt_users.append(c_trakt_user)
        trakt_list_start+=1
        trakt_tag_start+=1
        c_trakt_list = __settings__.getSetting(str(trakt_list_start))
        c_trakt_tag = __settings__.getSetting(str(trakt_tag_start))
        c_trakt_user = __settings__.getSetting(str(trakt_user_start))
        trakt_list_count -= 1
        
#command line arguments for manual/tag delete executions
    if len(sys.argv) == 2:
        if "manual" in sys.argv[1]:
            manual = "true"
            pDialog = xbmcgui.DialogProgress()
            ret = pDialog.create("Tag Generator", _getstr(30064))
        elif "wipeout" in sys.argv[1]:
            wipeout = "true"
            if xbmcgui.Dialog().yesno("Tag Generator", _getstr(30065)):
                if xbmcgui.Dialog().yesno("Tag Generator", _getstr(30066)):
                    pDialog = xbmcgui.DialogProgress()
                    pDialog.create("Tag Generator", _getstr(30067))
                    xbmc.log(msg= _getstr(30068),level=xbmc.LOGNOTICE)
                    wipedcount = wipealltags()
                    xbmc.log(msg= _getstr(30093),level=xbmc.LOGNOTICE)
                    sys.exit(_getstr(30093))
                else:
                    xbmc.log(msg= _getstr(30069),level=xbmc.LOGNOTICE)
                    sys.exit(_getstr(30069))
            else:
                xbmc.log(msg= _getstr(30069),level=xbmc.LOGNOTICE)
                sys.exit(_getstr(30069))
        elif "standup" in sys.argv[1]:
            pDialog = xbmcgui.DialogProgress()
            ret = pDialog.create("Tag Generator", _getstr(30064))
            xbmc.log(msg= _getstr(30073),level=xbmc.LOGNOTICE)
            Medialist = getxbmcdb()
            newwikitag = c_standuptag
            comedians = scrapewiki()
            comiccount = writestanduptags(comedians, Medialist, newwikitag)
            dialog = xbmcgui.Dialog()
            ok = dialog.ok("Tag Generator", _getstr(30081)+str(comiccount)+_getstr(30083))
            sys.exit(_getstr(30075))
        elif "imdb" in sys.argv[1]:
            pDialog = xbmcgui.DialogProgress()
            ret = pDialog.create("Tag Generator", _getstr(30064))
            xbmc.log(msg= _getstr(30074),level=xbmc.LOGNOTICE)
            Medialist = getxbmcdb()
            scrapecount = 0
            for imdburl in imdburllist:
                newimdbtag = imdbtaglist[scrapecount]
                imdblist = scrapeimdbrss(imdburl, scrapecount)
                moviecount += writeimdbtags(imdblist, Medialist, newimdbtag)
                scrapecount = scrapecount + 1
            dialog = xbmcgui.Dialog()
            ok = dialog.ok("Tag Generator", _getstr(30081)+str(moviecount)+_getstr(30930))
            sys.exit(_getstr(30076))
        elif sys.argv[1] == "trakt_init":
            dialog = xbmcgui.Dialog()
            ok = dialog.ok("Tag Generator", _getstr(30923))
            dialog = xbmcgui.Dialog()
            d = dialog.input(_getstr(30924))
            if d:
                try:
                    trakt_token=trakt.init(pin=d,client_id=trakt_client_id,client_secret=trakt_client_secret)
                    __settings__.setSetting("32031",trakt_token)
                    sys.exit(_getstr(30927))
                except Exception, e:
                    dialog = xbmcgui.Dialog()
                    ok = dialog.ok("Tag Generator", _getstr(30925)+str(e.message))
                    sys.exit(_getstr(30927))
            else:
                sys.exit(_getstr(30927))
        elif sys.argv[1] == "trakt":
            if len(c_trakt_token) != 64:
                dialog = xbmcgui.Dialog()
                ok = dialog.ok("Tag Generator", _getstr(30925))
                xbmc.log(msg= _getstr(30925),level=xbmc.LOGNOTICE)
                sys.exit(_getstr(30925))
            pDialog = xbmcgui.DialogProgress()
            ret = pDialog.create("Tag Generator", _getstr(30064))
            xbmc.log(msg= _getstr(30070),level=xbmc.LOGNOTICE)
            Medialist = getxbmcdb()
            i = 0
            for this_trakt_list in trakt_lists:
                this_trakt_tag = trakt_tags[i]
                this_trakt_user = trakt_users[i]
                try:
                    trakt_movies = get_trakt_movies(this_trakt_user, this_trakt_list, c_trakt_token)
                    moviecount += write_trakt_tags(trakt_movies, Medialist, this_trakt_tag)
                except:
                    xbmc.log(msg= _getstr(30928),level=xbmc.LOGERROR)
                i+=1
            dialog = xbmcgui.Dialog()
            ok = dialog.ok("Tag Generator", _getstr(30081)+str(moviecount)+_getstr(30930))
            xbmc.log(msg= _getstr(30084),level=xbmc.LOGNOTICE)
            sys.exit(_getstr(30927))        
        else:
            xbmc.log(msg= _getstr(30077),level=xbmc.LOGNOTICE)
            sys.exit(_getstr(30077))

            
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
    if ("true" in c_usetrakt) and ("false" in wipeout) and (len(c_trakt_token) == 64):
        scrapecount = 0
        for this_trakt_list in trakt_lists:
            this_trakt_tag = trakt_tags[scrapecount]
            try:
                trakt_movies = get_trakt_movies(this_trakt_list, c_trakt_token)
                moviecount += write_trakt_tags(trakt_movies, Medialist, this_trakt_tag)
            except:
                xbmc.log(msg= _getstr(30928),level=xbmc.LOGERROR)
            scrapecount = scrapecount + 1
    else:
        xbmc.log(msg= _getstr(30080),level=xbmc.LOGNOTICE)

    if "true" in manual:
        dialog = xbmcgui.Dialog()
        ok = dialog.ok("Tag Generator", _getstr(30081)+str(moviecount)+_getstr(30082) + str(comiccount)+_getstr(30083))
        xbmc.log(msg= _getstr(30084),level=xbmc.LOGNOTICE)
        sys.exit(_getstr(30084))
   
    elif "true" in wipeout:
        dialog = xbmcgui.Dialog()
        ok = dialog.ok("Tag Generator", _getstr(30085)+str(wipedcount)+_getstr(30086))
        xbmc.log(msg= _getstr(30087),level=xbmc.LOGNOTICE)
        sys.exit(_getstr(30087))
   
    else:
        xbmc.log(msg= _getstr(30088)+str(c_refresh)+_getstr(30089),level=xbmc.LOGNOTICE)
        while (sleeptime > 0 and not monitor.abortRequested()):
            xbmc.sleep(micronap)
            sleeptime = sleeptime - micronap 
