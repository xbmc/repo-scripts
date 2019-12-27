from bs4 import BeautifulSoup
import datetime
import json
import os
import re
import requests
import sys
import xbmc
import xbmcgui
import xbmcaddon

sys.path.append(os.path.join(os.path.abspath(os.path.dirname(__file__)), "resources", "lib"))
import trakt
from trakt import users as traktusers

try:
    from hashlib import sha1
except ImportError:
    from sha import new as sha1

__settings__ = xbmcaddon.Addon()
__language__ = __settings__.getLocalizedString
c_refresh = __settings__.getSetting("32012")
c_runasservice = json.loads(__settings__.getSetting("32011"))
start_time = datetime.datetime.now()
service_interval = int(c_refresh) * 3600  # seconds
nap = 1  # seconds


def _getstr(id):
    return str(__language__(id))


if len(sys.argv) != 2:
    xbmc.sleep(1000)
    xbmc.log(msg="TAG-GEN: Starting as a service.", level=xbmc.LOGNOTICE)


###################################################################
############################ FUNCTIONS ############################
###################################################################
def internet_test(url):
    try:
        response = requests.get(url, timeout=5)
        return True
    except Exception as e:
        pass
    if len(sys.argv) == 2:
        dialog = xbmcgui.Dialog()
        ok = dialog.ok(_getstr(30000), url + _getstr(30001))
    xbmc.log(msg="TAG-GEN: " + str(url) + " unreachable. Check network and retry.", level=xbmc.LOGERROR)
    sys.exit(1)


def ifcancel():
    if len(sys.argv) == 2:
        if (pDialog.iscanceled()):
            debuglog("TAG-GEN: Cancel received from Kodi dialog, exiting.")
            sys.exit(0)


def debuglog(string):
    if c_debug:
        xbmc.log(msg=string, level=xbmc.LOGDEBUG)


def notify(input):
    icon = os.path.join(os.path.abspath(os.path.dirname(__file__)), 'icon.png')
    xbmcgui.Dialog().notification("Tag Generator", str(input), icon, 2500)


def wipealltags():
    """A function to overwrite EVERY tag found in the database with a blank [] tag."""
    counter = 0
    medialist = getkodidb()
    for movie in medialist:
        ifcancel()
        json_query = '{"jsonrpc": "2.0", "id": "libMovies", "method": "VideoLibrary.SetMovieDetails", ' \
                     '"params": {"movieid" : replaceid, "tag":[]}}'
        json_query = unicode(json_query, 'utf-8', errors='ignore')
        xbmcid = (json.dumps(movie.get('xbmcid', '')))
        json_query = re.sub('replaceid', xbmcid, json_query)
        jsonobject = json.loads(xbmc.executeJSONRPC(json_query))
        if len(sys.argv) == 2:
            counter = counter + 1
            percent = (100 * int(counter) / int(len(medialist)))
            pDialog.update(percent, " ", _getstr(30002) + str(counter) + "/" + str(len(medialist)) + _getstr(30003))
    return counter


def getkodidb():
    """Dump the entire Kodi library to a big list of dicts"""
    if wipeout:
        pDialog.update(0, _getstr(30004), " ", " ")
    elif len(sys.argv) == 2:
        pDialog.update(0, _getstr(30005), " ", " ")
    # json strings -> unicode -> json
    json_query = xbmc.executeJSONRPC('{"jsonrpc": "2.0", "method": "VideoLibrary.GetMovies", "params": {"properties" : '
                                     '["title","studio","tag","imdbnumber","year"], "sort": {"order": "ascending", '
                                     '"method": "label", "ignorearticle": true}}, "id": "libMovies"}')
    json_query = unicode(json_query, 'utf-8', errors='ignore')
    jsonobject = json.loads(json_query)
    medialist = []
    if 'movies' in jsonobject['result']:
        for item in jsonobject['result']['movies']:
            ifcancel()
            medialist.append({'xbmcid': item.get('movieid', ''), 'imdbid': item.get('imdbnumber', ''), 'name':
                item.get('label', ''), 'tag': item.get('tag', ''), 'year': item.get('year', '')})
    return medialist


def write_trakt_tags(traktlist, medialist, newtrakttag):
    """Write tags for locally found movies given a Trakt watchlist, local media list and the new tag to write."""
    if len(sys.argv) == 2:
        pDialog.update(0, _getstr(30006), " ", " ")
    moviecount = 0
    counter = 0
    for traktimdbid in traktlist:
        ifcancel()
        counter = counter + 1
        for movie in medialist:
            xbmcimdbid = (json.dumps(movie.get('imdbid', '')))
            xbmcid = (json.dumps(movie.get('xbmcid', '')))
            xbmctag = (json.dumps(movie.get('tag', '')))
            xbmcname = (json.dumps(movie.get('name', '')))
            if (traktimdbid in xbmcimdbid) and (newtrakttag not in xbmctag):
                moviecount = moviecount + 1
                percent = (100 * int(counter) / int(len(traktlist)))
                if len(sys.argv) == 2:
                    pDialog.update(percent, "", "", _getstr(30007) + str(newtrakttag) + _getstr(30008) + str(moviecount)
                                   + _getstr(30010))
                debuglog('TAG-GEN: Writing tag "' + newtrakttag + '" to Trakt movie: ' + xbmcname)
                writetags(xbmcid, newtrakttag, xbmctag[1:-1])
            else:
                percent = (100 * int(counter) / int(len(traktlist)))
                debuglog("TAG-GEN: Not writing tag: " + newtrakttag + " to movie: " + xbmcname + " with existing tag: "
                         + xbmctag)
            if len(sys.argv) == 2:
                pDialog.update(percent, "", _getstr(30009) + str(counter) + "/" + str(len(traktlist)) + _getstr(30010))
    return moviecount


def get_trakt_movies(user_name, list_name, token):
    """Return imdb ids for movies in a given trakt list. Requires oauth token for user lists."""
    trakt.core.AUTH_METHOD = trakt.core.OAUTH_AUTH
    trakt.core.OAUTH_TOKEN = token
    trakt.core.CLIENT_ID = trakt_client_id
    trakt.core.CLIENT_SECRET = trakt_client_secret
    if list_name.lower() == "watchlist":
        target_list = traktusers.User(user_name).watchlist_movies
    else:
        target_list = traktusers.User(user_name).get_list(list_name).get_items()
    found_ids = list()
    for item in target_list:
        imdb_id = item.ids["ids"]["imdb"]
        if not imdb_id in found_ids:
            found_ids.append(imdb_id)
            debuglog("TAG-GEN: Found Trakt movie " + (str(item)) + " in Trakt List: " + list_name)
    return found_ids


def writetags(xbmcid, newtag, xbmctag):
    """Write tags via json. Requires the xbmcid, the existing xbmctag and the new tag"""
    ifcancel()
    jsonurl = '{"jsonrpc": "2.0", "id": 1, "method": "VideoLibrary.SetMovieDetails", "params": {"movieid" : replaceid, "tag":replacetag}}'
    jsonurl = re.sub('replaceid', xbmcid, jsonurl)
    if type(newtag) == list:
        tags = []
        xbmctag = json.loads(xbmctag)
        if len(xbmctag) > 0:
            tags += xbmctag
        tags += newtag
        tags = json.dumps(tags)
        jsonurl = re.sub('replacetag', tags, jsonurl)
    elif len(xbmctag) > 2:
        jsonurl = re.sub('replacetag', '[' + xbmctag + "," + '"' + newtag + '"]', jsonurl)
    else:
        jsonurl = re.sub('replacetag', '["' + newtag + '"]', jsonurl)
    jsonresponse = json.loads(xbmc.executeJSONRPC(jsonurl))


def scrapeimdb(imdburl, scrapecount):
    """Scrapes IMDb given a URL and a scrape count (counter for how many times it has run)"""
    internet_test("http://www.imdb.com")
    if len(sys.argv) == 2:
        pDialog.update(0, _getstr(30011), " ", " ")
    ifcancel()
    try:
        imdbpage = requests.get(imdburl).text
        imdbuser = re.findall(r'<title>(.+?)</title>', imdbpage)
        if imdbuser[0] == "Your Watchlist - IMDb":
            imdbuser = str(imdbuser[1])
        else:
            imdbuser = str(imdbuser[0])
        imdblist = re.findall(r'"(tt[0-9]{7})"', imdbpage)
        imdblist = sorted(set(imdblist))
        debuglog("TAG-GEN: Found these IMDb tags on " + str(imdbuser) + ": " + str(imdburl) + ": " + str(imdblist))
        return imdblist, imdbuser
    except Exception as e:
        if len(sys.argv) == 2:
            dialog = xbmcgui.Dialog()
            ok = dialog.ok(_getstr(30000), imdburl + _getstr(30012))
        xbmc.log(msg="TAG-GEN: " + imdburl + " contains no IMDb IDs. Check URL and retry.", level=xbmc.LOGERROR)
        debuglog("TAG-GEN: " + str(e))
        sys.exit(1)


def writeimdbtags(imdblist, medialist, newimdbtag):
    """Write tags for locally found movies given an imdb watchlist, local media list and the new tag to write."""
    if len(sys.argv) == 2:
        pDialog.update(0, _getstr(30013) + str(imdbuser))
    moviecount = 0
    counter = 0
    for webimdbid in imdblist:
        ifcancel()
        counter = counter + 1
        for movie in medialist:
            xbmcimdbid = (json.dumps(movie.get('imdbid', '')))
            xbmcid = (json.dumps(movie.get('xbmcid', '')))
            xbmctag = (json.dumps(movie.get('tag', '')))
            xbmcname = (json.dumps(movie.get('name', '')))
            if (webimdbid in xbmcimdbid) and (newimdbtag not in xbmctag):
                moviecount = moviecount + 1
                debuglog(
                    "TAG-GEN: Writing tag: " + newimdbtag + " to IMDb movie: " + xbmcname + " from " + str(imdbuser))
                percent = (100 * int(counter) / int(len(imdblist)))
                if len(sys.argv) == 2:
                    pDialog.update(percent, "", "", _getstr(30014) + str(newimdbtag) + _getstr(30015) + str(moviecount)
                                   + _getstr(30016))
                writetags(xbmcid, newimdbtag, xbmctag[1:-1])
            else:
                percent = (100 * int(counter) / int(len(imdblist)))
                debuglog("TAG-GEN: Not writing tag: " + newimdbtag +
                         " to movie: " + xbmcname + " with existing tag: " +
                         xbmctag + " from " + str(imdbuser))
            if len(sys.argv) == 2:
                pDialog.update(percent, "", _getstr(30017) + str(counter) + "/" + str(len(imdblist)) + _getstr(30018))
    debuglog(str(imdblist))
    return moviecount


def scrapewiki():
    """Scrapes Wikipedia URLs for comedian names given a single url."""
    internet_test("https://en.wikipedia.org")
    if len(sys.argv) == 2:
        pDialog.update(0, _getstr(30019), " ", " ")
    comiclist = []
    for wikiurl in wikiurllist:
        ifcancel()
        try:
            page = requests.get(wikiurl).text
            results = (re.findall(
                r'<li><a href="/wiki/.+?" title=".+?">((?!.*List.*|.*rticle.*|.*omedian.*)\b.+?\b.+?)</a></li>', page))
            for comic in results:
                comic = comic.encode("utf-8")
                ifcancel()
                debuglog("TAG-GEN: Found comedian: " + comic + " in Wiki URL: " + wikiurl)
                comiclist.append(comic)
            comiclist = sorted(set(comiclist))
        except Exception as e:
            if len(sys.argv) == 2:
                dialog = xbmcgui.Dialog()
                ok = dialog.ok(_getstr(30000), wikiurl + _getstr(30020))
            xbmc.log(msg="TAG-GEN: " + wikiurl + " contains no comedians. Check URL and retry.", level=xbmc.LOGERROR)
            debuglog("TAG-GEN: " + str(e))
            sys.exit(1)
    return comiclist


def writestanduptags(comiclist, medialist, newwikitag):
    """Write tags for locally found Stand-up movies given list of comedians, local media list and the new tag to write."""
    if len(sys.argv) == 2:
        pDialog.update(0, _getstr(30021), " ", " ")
    comicmatches = 0
    counter = 0
    for comic in comiclist:
        ifcancel()
        counter = counter + 1
        for movie in medialist:
            xbmcname = (json.dumps(movie.get('name', '')))
            xbmcid = (json.dumps(movie.get('xbmcid', '')))
            xbmctag = (json.dumps(movie.get('tag', '')))
            if (comic in xbmcname) and (newwikitag not in xbmctag):
                comicmatches = comicmatches + 1
                debuglog("TAG-GEN: Match found for comedian: " + comic + " in feature: " + xbmcname
                         + " from Wikipedia comedians.")
                xbmctag = xbmctag[1:-1]
                percent = (100 * int(counter) / int(len(comiclist)))
                if len(sys.argv) == 2:
                    pDialog.update(percent, "", "", _getstr(30022) + str(newwikitag) + _getstr(30023)
                                   + str(comicmatches) + _getstr(30024))
                    pDialog.update(percent, "", _getstr(30025) + str(counter) + "/"
                                   + str(len(comiclist)) + _getstr(30026))
                    writetags(xbmcid, newwikitag, xbmctag)
            else:
                percent = (100 * int(counter) / int(len(comiclist)))
                debuglog("TAG-GEN: No match found for comedian: " + comic +
                         " in feature: " + xbmcname +
                         " with existing tag: " + xbmctag)
                if len(sys.argv) == 2:
                    pDialog.update(percent, "", _getstr(30025) + str(counter) + "/" + str(len(comiclist))
                                   + _getstr(30026))
    return comicmatches


def write_award_tags(medialist, tag_winners, tag_nominees):
    """Use the imdb awards pages for each title to create tags for each Oscar award and nomination."""
    imdburl = 'https://www.imdb.com'
    internet_test(imdburl)
    if len(sys.argv) == 2:
        pDialog.update(0, _getstr(30041), " ", " ")
    awardsmatches = 0
    counter = 0
    for movie in medialist:
        retry_attempts = 10  # amount of times to attempt the imdb scrape
        retry_interval = 5  # seconds to wait between each try
        counter += 1
        ifcancel()
        if len(sys.argv) == 2:
            percent = (100 * int(counter) / int(len(medialist)))
            pDialog.update(percent, _getstr(30041) + " " + str(counter) + "/" + str(len(medialist)))
        xbmcname = (json.dumps(movie.get('name', '')))
        xbmcid = (json.dumps(movie.get('xbmcid', '')))
        xbmctag = (json.dumps(movie.get('tag', '')))
        imdbid = (json.dumps(movie.get('imdbid', '')))[1:-1]
        while retry_attempts > 0:
            try:
                page = requests.get(imdburl + '/title/' + imdbid + '/awards')
                page_soup = BeautifulSoup(page.text, "html.parser")
                page_portion = page_soup.find("body")
                retry_attempts = 0
            except:
                if retry_attempts == 1:
                    xbmc.log(
                        msg="TAG-GEN: Failed to extract Oscar awards from IMDb after several attempts. Try increasing the retry interval.",
                        level=xbmc.LOGERROR)
                    return awardsmatches
                retry_attempts -= 1
                xbmc.sleep(retry_interval * 1000)
        awards = []
        if page_portion:
            for header in page_portion.find_all("h3"):
                if len(header.find_all("a", "event_year")) > 0:
                    award = header.contents[0].encode('utf-8').strip()
                    if award == 'Academy Awards, USA':  # only oscars (for the time being)
                        table = list(header.next_siblings)[1]
                        award_descriptions = [x.contents[0].strip().encode('utf-8')
                                              for x in table.find_all("td", "award_description")]
                        j = 0
                        for td in table.find_all("td", "title_award_outcome"):
                            for i in range(int(td['rowspan'])):
                                award_type = td.b.contents[0].encode('utf-8')
                                found_award = 'Oscar ' + award_type + ': ' + award_descriptions[j]
                                # new awards only, and skip 'special achievements', which will be 0 len
                                # write winners and nominees according to settings
                                if found_award not in json.loads(xbmctag) and len(award_descriptions[j]) > 0 \
                                        and ((award_type == "Winner" and tag_winners) or
                                             (award_type == "Nominee" and tag_nominees)):
                                    awards.append(found_award)
                                j += 1
        if len(awards) > 0:
            debuglog("TAG-GEN: Found the following awards for " + xbmcname + str(awards))
            awardsmatches += 1
            if len(sys.argv) == 2:
                pDialog.update(percent, "", _getstr(30042) + str(xbmcname))
            writetags(xbmcid, awards, xbmctag)
    return awardsmatches


###################################################################
########################## END FUNCTIONS ##########################
###################################################################


# These are the URLs that we will be searching for comedians
wikiurllist = ["https://en.wikipedia.org/wiki/List_of_British_stand-up_comedians",
               "https://en.wikipedia.org/wiki/List_of_stand-up_comedians",
               "https://en.wikipedia.org/wiki/List_of_Australian_stand-up_comedians",
               "https://en.wikipedia.org/wiki/List_of_Canadian_stand-up_comedians",
               "https://en.wikipedia.org/wiki/List_of_United_States_stand-up_comedians"]

monitor = xbmc.Monitor()
while not monitor.abortRequested():
    if not c_runasservice and len(sys.argv) != 2:
        xbmc.log(msg="TAG-GEN: Manual run not requested and runasservice not selected, exiting.", level=xbmc.LOGERROR)
        sys.exit(1)
    c_debug = json.loads(__settings__.getSetting("32030"))
    debuglog("TAG-GEN: Starting tag generation.")
    URLID = 32050
    TAGID = 32080
    awardcount = 0
    comiccount = 0
    moviecount = 0
    c_useimdb = json.loads(__settings__.getSetting("32020"))
    c_imdburl = __settings__.getSetting(str(URLID))
    c_imdbtag = __settings__.getSetting(str(TAGID))
    c_usestandup = json.loads(__settings__.getSetting("32015"))
    c_standuptag = __settings__.getSetting("32016")
    c_plusurl = __settings__.getSetting("32013")
    c_minusurl = __settings__.getSetting("32014")
    c_urlcount = __settings__.getSetting("32099")
    c_usetrakt = json.loads(__settings__.getSetting("32023"))
    c_useawards = json.loads(__settings__.getSetting("32021"))
    c_oscarwinners = json.loads(__settings__.getSetting("32024"))
    c_oscarnominees = json.loads(__settings__.getSetting("32025"))
    trakt_list_start = 32120
    trakt_tag_start = 32140
    trakt_user_start = 32160
    c_trakt_list = __settings__.getSetting(str(trakt_list_start))
    c_trakt_tag = __settings__.getSetting(str(trakt_tag_start))
    c_trakt_user = __settings__.getSetting(str(trakt_user_start))
    trakt.core.APPLICATION_ID = '12265'
    trakt_client_id = '8bc9b1371d9594b451c863bea2c95aa96ac5e5bf9ecee274daa23c0790386afe'
    trakt_client_secret = '6087cbfb47b8f0cdc1c0fc491ec52524c9d23bf37a8480a8c2827ea91312cbad'
    c_trakt_token = __settings__.getSetting("32031")
    c_trakt_list_count = __settings__.getSetting("32098")

    c_notify = json.loads(__settings__.getSetting("32019"))
    manual = False
    wipeout = False

    # Initialise IMDb URL list, add extra to list if specified by settings.xml.
    # Also make a list out of the user-defined tags
    listurlcount = int(c_urlcount)
    imdburllist = []
    imdbtaglist = []
    while listurlcount > -1:
        imdburllist.append(c_imdburl)
        imdbtaglist.append(c_imdbtag)
        URLID = URLID + 1
        TAGID = TAGID + 1
        c_imdburl = __settings__.getSetting(str(URLID))
        c_imdbtag = __settings__.getSetting(str(TAGID))
        listurlcount = listurlcount - 1

    # init Trakt lists and tags
    trakt_list_count = int(c_trakt_list_count)
    trakt_lists = list()
    trakt_tags = list()
    trakt_users = list()
    while trakt_list_count > -1:
        trakt_lists.append(c_trakt_list)
        trakt_tags.append(c_trakt_tag)
        trakt_users.append(c_trakt_user)
        trakt_list_start += 1
        trakt_tag_start += 1
        trakt_user_start += 1
        c_trakt_list = __settings__.getSetting(str(trakt_list_start))
        c_trakt_tag = __settings__.getSetting(str(trakt_tag_start))
        c_trakt_user = __settings__.getSetting(str(trakt_user_start))
        trakt_list_count -= 1

    # command line arguments for manual/tag delete executions
    if len(sys.argv) == 2:
        if sys.argv[1] == "manual":
            manual = True
            pDialog = xbmcgui.DialogProgress()
            ret = pDialog.create("Tag Generator", _getstr(30027))
        elif sys.argv[1] == "wipeout":
            wipeout = True
            if xbmcgui.Dialog().yesno("Tag Generator", _getstr(30028)):
                if xbmcgui.Dialog().yesno("Tag Generator", _getstr(30029)):
                    pDialog = xbmcgui.DialogProgress()
                    pDialog.create("Tag Generator", _getstr(30030))
                    wipedcount = wipealltags()
                    xbmc.log(msg="TAG-GEN: Finished wiping tags.", level=xbmc.LOGNOTICE)
                    sys.exit(0)
                else:
                    debuglog("TAG-GEN: Manual tag deletion arg received, but not confirmed so exiting.")
                    sys.exit(0)
            else:
                debuglog("TAG-GEN: Manual tag deletion arg received, but not confirmed so exiting.")
                sys.exit(0)
        elif sys.argv[1] == "standup":
            pDialog = xbmcgui.DialogProgress()
            ret = pDialog.create("Tag Generator", _getstr(30027))
            xbmc.log(msg="TAG-GEN: Starting stand-up tag writing.", level=xbmc.LOGNOTICE)
            medialist = getkodidb()
            newwikitag = c_standuptag
            comedians = scrapewiki()
            comiccount = writestanduptags(comedians, medialist, newwikitag)
            dialog = xbmcgui.Dialog()
            ok = dialog.ok("Tag Generator", _getstr(30031) + str(comiccount) + _getstr(30044))
            debuglog("TAG-GEN: Manual Stand-Up arg received, exiting after execution.")
            sys.exit(0)
        elif sys.argv[1] == "imdb":
            pDialog = xbmcgui.DialogProgress()
            ret = pDialog.create("Tag Generator", _getstr(30027))
            xbmc.log(msg="TAG-GEN: Starting IMDb tag writing.", level=xbmc.LOGNOTICE)
            medialist = getkodidb()
            scrapecount = 0
            for imdburl in imdburllist:
                newimdbtag = imdbtaglist[scrapecount]
                imdblist, imdbuser = scrapeimdb(imdburl, scrapecount)
                moviecount += writeimdbtags(imdblist, medialist, newimdbtag)
                scrapecount = scrapecount + 1
            dialog = xbmcgui.Dialog()
            ok = dialog.ok("Tag Generator", _getstr(30031) + str(moviecount) + _getstr(30003))
            debuglog("TAG-GEN: Manual IMDb arg received, exiting after execution.")
            sys.exit(0)
        elif sys.argv[1] == "trakt_init":
            dialog = xbmcgui.Dialog()
            ok = dialog.ok("Tag Generator", _getstr(30923))
            dialog = xbmcgui.Dialog()
            d = dialog.input(_getstr(30924))
            if d:
                try:
                    trakt_token = trakt.init(pin=d, client_id=trakt_client_id, client_secret=trakt_client_secret)
                    __settings__.setSetting("32031", trakt_token)
                    sys.exit(0)
                except Exception as e:
                    dialog = xbmcgui.Dialog()
                    ok = dialog.ok("Tag Generator", _getstr(30925))
                    xbmc.log(msg="Unable to retrieve Trakt oauth token." + str(e), level=xbmc.LOGERROR)
                    sys.exit(0)
            else:
                debuglog("TAG-GEN: Manual Trakt Init arg received, exiting after execution.")
                sys.exit(0)
        elif sys.argv[1] == "trakt":
            if len(c_trakt_token) != 64:
                dialog = xbmcgui.Dialog()
                ok = dialog.ok("Tag Generator", _getstr(30925))
                xbmc.log(msg="TAG-GEN: Unable to retrieve Trakt oauth token.", level=xbmc.LOGERROR)
                sys.exit(1)
            pDialog = xbmcgui.DialogProgress()
            ret = pDialog.create("Tag Generator", _getstr(30027))
            xbmc.log(msg="TAG-GEN: Starting Trakt writing.", level=xbmc.LOGNOTICE)
            medialist = getkodidb()
            i = 0
            for this_trakt_list in trakt_lists:
                this_trakt_tag = trakt_tags[i]
                this_trakt_user = trakt_users[i]
                try:
                    trakt_movies = get_trakt_movies(this_trakt_user, this_trakt_list, c_trakt_token)
                    moviecount += write_trakt_tags(trakt_movies, medialist, this_trakt_tag)
                except:
                    xbmc.log(msg="TAG-GEN: Could not retrieve movies from Trakt API.", level=xbmc.LOGERROR)
                i += 1
            dialog = xbmcgui.Dialog()
            ok = dialog.ok("Tag Generator", _getstr(30031) + str(moviecount) + _getstr(30003))
            debuglog("TAG-GEN: Manual arg received, exiting after single execution.")
            sys.exit(0)
        elif sys.argv[1] == "awards":
            if not (c_oscarwinners or c_oscarnominees):
                dialog = xbmcgui.Dialog()
                ok = dialog.ok("Tag Generator", _getstr(30043))
                xbmc.log(msg="TAG-GEN: No awards category chosen", level=xbmc.LOGERROR)
                sys.exit(1)
            pDialog = xbmcgui.DialogProgress()
            ret = pDialog.create("Tag Generator", _getstr(30027))
            xbmc.log(msg="TAG-GEN: Starting awards tag writing.", level=xbmc.LOGNOTICE)
            medialist = getkodidb()
            awardscount = write_award_tags(medialist, c_oscarwinners, c_oscarnominees)
            dialog = xbmcgui.Dialog()
            ok = dialog.ok("Tag Generator", _getstr(30031) + str(awardscount) + _getstr(30040))
            debuglog("TAG-GEN: Manual arg received, exiting after single execution.")
            sys.exit(0)
        else:
            xbmc.log(msg="TAG-GEN: No valid arguments supplied.", level=xbmc.LOGERROR)
            sys.exit(1)

    # Read the local XBMC DB
    medialist = getkodidb()

    # IMDb tag writing
    if c_useimdb and not wipeout:
        if c_notify:
            notify(_getstr(30036))
        xbmc.log(msg="TAG-GEN: Starting IMDb tag writing.", level=xbmc.LOGNOTICE)
        scrapecount = 0
        moviecount = 0
        for imdburl in imdburllist:
            newimdbtag = imdbtaglist[scrapecount]
            imdblist, imdbuser = scrapeimdb(imdburl, scrapecount)
            moviecount = moviecount + writeimdbtags(imdblist, medialist, newimdbtag)
            scrapecount = scrapecount + 1
    else:
        debuglog("TAG-GEN: Skipping IMDb tag writing.")
        moviecount = 0

    # Trakt movies tag writing
    if c_usetrakt and not wipeout and (len(c_trakt_token) == 64):
        if c_notify:
            notify(_getstr(30037))
        xbmc.log(msg="TAG-GEN: Starting Trakt tag writing.", level=xbmc.LOGNOTICE)
        i = 0
        for this_trakt_list in trakt_lists:
            this_trakt_tag = trakt_tags[i]
            this_trakt_user = trakt_users[i]
            try:
                trakt_movies = get_trakt_movies(this_trakt_user, this_trakt_list, c_trakt_token)
                moviecount += write_trakt_tags(trakt_movies, medialist, this_trakt_tag)
            except:
                xbmc.log(msg="TAG-GEN: Could not retrieve movies from Trakt API.", level=xbmc.LOGERROR)
            i += 1
    else:
        debuglog("TAG-GEN: Skipping Trakt tag writing.")

    # Stand-up Comedy tag writing
    if c_usestandup and not wipeout:
        if c_notify:
            notify(_getstr(30038))
        newwikitag = c_standuptag
        xbmc.log(msg="TAG-GEN: Starting stand-up tag writing.", level=xbmc.LOGNOTICE)
        comedians = scrapewiki()
        comiccount = writestanduptags(comedians, medialist, newwikitag)
    else:
        debuglog("TAG-GEN: Skipping stand-up tag writing.")

    # Awards tag writing
    if c_useawards and not wipeout and (c_oscarwinners or c_oscarnominees):
        if c_notify:
            notify(_getstr(30039))
        medialist = getkodidb()
        xbmc.log("TAG-GEN: Starting awards tag writing.", level=xbmc.LOGNOTICE)
        awardscount = write_award_tags(medialist, c_oscarwinners, c_oscarnominees)
    else:
        debuglog("TAG-GEN: Skipping awards tag writing.")

    if manual:
        dialog = xbmcgui.Dialog()
        try:
            _ = awardscount
        except:
            awardscount = 0
        ok = dialog.ok("Tag Generator", _getstr(30031) + str(moviecount) + _getstr(30032) + str(comiccount)
                       + _getstr(30033) + str(awardscount) + _getstr(30040))
        debuglog("TAG-GEN: Manual arg received, exiting after single execution.")
        sys.exit(0)
    elif wipeout:
        dialog = xbmcgui.Dialog()
        ok = dialog.ok("Tag Generator", _getstr(30034) + str(wipealltags()) + _getstr(30035))
        debuglog("TAG-GEN: Wipeout arg received, exiting after single execution.")
        sys.exit(0)
    else:
        xbmc.log(msg="TAG-GEN: Sleeping for " + str(c_refresh) + " hours", level=xbmc.LOGNOTICE)
        while not monitor.abortRequested():
            if (datetime.datetime.now() - start_time).total_seconds() < service_interval:
                if monitor.waitForAbort(nap):
                    xbmc.log("TAG-GEN: Abort request received, exiting.", level=xbmc.LOGNOTICE)
                    sys.exit(0)
            else:
                start_time = datetime.datetime.now()
                break
