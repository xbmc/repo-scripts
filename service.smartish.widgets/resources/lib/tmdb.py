import xbmcaddon
import os
import xbmc
import urllib
import urllib2
import simplejson
from traceback import print_exc

moviedb_key = '9202e131cf0cf5f7586054ba4009efea'
__addon__ = xbmcaddon.Addon()
__addonid__ = __addon__.getAddonInfo('id')
__language__ = __addon__.getLocalizedString
Addon_Data_Path = os.path.join(xbmc.translatePath("special://profile/addon_data/%s" % __addonid__).decode("utf-8"))

def log(txt):
    message = '%s: %s' % ("Smart(ish)", txt.encode('ascii', 'ignore'))
    xbmc.log(msg=message, level=xbmc.LOGDEBUG)

def _Get_JSON_response( url= "" ):
    log( repr( url ) )
    response = _GetStringFromUrl(url)
    try:
        results = simplejson.loads(response)
        return results
    except:
        log("Exception: Could not get new JSON data")
        print_exc()
        return None
        
def _GetStringFromUrl(url):
    succeed = 0
    while (succeed < 5) and (not xbmc.abortRequested):
        try:
            request = urllib2.Request(url)
            request.add_header('User-agent', 'XBMC/13.2 ( ptemming@gmx.net )')
            response = urllib2.urlopen(request)
            data = response.read()
            return data
        except:
            print_exc()
            log("GetStringFromURL: could not get data from %s" % url)
            xbmc.sleep(1000)
            succeed += 1
    return None
                
def _GetMovieDBData( url = "" ):
    url = "http://api.themoviedb.org/3/" + url + "api_key=%s" % moviedb_key
    results = _Get_JSON_response(url )
    return results
    
def GetTMDBTVShow( name, year = None ):
    if year is None:
        response = _GetMovieDBData("search/tv?query=%s&" % ( urllib.quote_plus( name ) ) )
    else:
        response = _GetMovieDBData("search/tv?query=%s&first_air_date_year=%s&" % ( urllib.quote_plus( name ), year ) )
    if response and "results" in response:
        if len( response[ "results" ] ) == 0 and year is not None:
            # Try again, without the year
            return GetTMDBTVShow( name )
        return response["results"]
    else:
        return []
    
def GetTMDBTVShowDetails( id ):
    response = _GetMovieDBData("tv/%s?append_to_response=similar,keywords&" % ( id ) )
    return response
    
def GetTMDBMovie( name, year = None ):
    if year is None:
        response = _GetMovieDBData("search/movie?query=%s&include_adult=true&" % ( urllib.quote_plus( name.encode( "utf-8" ) ) ) )
    else:
        response = _GetMovieDBData("search/movie?query=%s&year=%s&include_adult=true&" % ( urllib.quote_plus( name.encode( "utf-8" ) ), year ) )
    if response and "results" in response:
        if len( response[ "results" ] ) == 0 and year is not None:
            # Try again, without the year
            return GetTMDBMovie( name )
        return response["results"]
    else:
        return []
    
def GetTMDBMovieDetails( id ):
    response = _GetMovieDBData("movie/%s?append_to_response=similar,keywords&" % ( id ) )
    return response
                