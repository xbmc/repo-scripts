# -*- coding: utf-8 -*-
# fanart.tv artist artwork scraper

import xbmc, xbmcgui, xbmcaddon, xbmcplugin
import os, sys, traceback, re
import urllib
from traceback import print_exc
from urllib import quote_plus, unquote_plus

__language__      = sys.modules[ "__main__" ].__language__
__scriptname__    = sys.modules[ "__main__" ].__scriptname__
__scriptID__      = sys.modules[ "__main__" ].__scriptID__
__author__        = sys.modules[ "__main__" ].__author__
__credits__       = sys.modules[ "__main__" ].__credits__
__credits2__      = sys.modules[ "__main__" ].__credits2__
__version__       = sys.modules[ "__main__" ].__version__
__addon__         = sys.modules[ "__main__" ].__addon__
addon_db          = sys.modules[ "__main__" ].addon_db
addon_work_folder = sys.modules[ "__main__" ].addon_work_folder
BASE_RESOURCE_PATH= sys.modules[ "__main__" ].BASE_RESOURCE_PATH
api_key           = sys.modules[ "__main__" ].api_key

sys.path.append( os.path.join( BASE_RESOURCE_PATH, "lib" ) )
from utils import get_html_source, unescape
from musicbrainz_utils import get_musicbrainz_album, get_musicbrainz_artist_id, update_musicbrainzid

music_url = "http://fanart.tv/webservice/artist/%s/%s/xml/%s/2/2"
single_release_group = "http://fanart.tv/webservice/album/%s/%s/xml/%s/2/2"
artist_url = "http://fanart.tv/webservice/has-art/%s/"
lookup_id = False

pDialog = xbmcgui.DialogProgress()

def remote_cdart_list( artist_menu ):
    xbmc.log( "[script.cdartmanager] - Finding remote cdARTs", xbmc.LOGDEBUG )
    cdart_url = []
    try:
        art = retrieve_fanarttv_xml( artist_menu["musicbrainz_artistid"] )
        if not len(art) < 2:
            album_artwork = art[3]["artwork"]
            if album_artwork:
                for artwork in album_artwork:
                    for cdart in artwork["cdart"]:
                        album = {}
                        album["artistl_id"] = artist_menu["local_id"]
                        album["artistd_id"] = artist_menu["distant_id"]
                        album["local_name"] = album["artist"] = artist_menu["name"]
                        album["musicbrainz_albumid"] = artwork["musicbrainz_albumid"]
                        album["disc"] = cdart["disc"]
                        album["size"] = cdart["size"]
                        album["picture"] = cdart["cdart"]
                        album["thumb_art"] = cdart["cdart"]
                        cdart_url.append(album)
                    #xbmc.log( "[script.cdartmanager] - cdart_url: %s " % cdart_url, xbmc.LOGDEBUG )
    except:
        print_exc()
    return cdart_url

def remote_coverart_list( artist_menu ):
    xbmc.log( "[script.cdartmanager] - Finding remote Cover ARTs", xbmc.LOGDEBUG )
    coverart_url = []
    try:
        art = retrieve_fanarttv_xml( artist_menu["musicbrainz_artistid"] )
        if not len(art) < 2:
            album_artwork = art[3]["artwork"]
            if album_artwork:
                for artwork in album_artwork:
                    if artwork["cover"]:
                        album = {}
                        album["artistl_id"] = artist_menu["local_id"]
                        album["artistd_id"] = artist_menu["distant_id"]
                        album["local_name"] = album["artist"] = artist_menu["name"]
                        album["musicbrainz_albumid"] = artwork["musicbrainz_albumid"]
                        album["size"] = 1000
                        album["picture"] = artwork["cover"]
                        album["thumb_art"] = artwork["cover"]
                        coverart_url.append(album)
                    #xbmc.log( "[script.cdartmanager] - cdart_url: %s " % cdart_url, xbmc.LOGDEBUG )
    except:
        print_exc()
    return coverart_url

def remote_fanart_list( artist_menu ):
    xbmc.log( "[script.cdartmanager] - Finding remote fanart", xbmc.LOGDEBUG )
    backgrounds = ""
    try:
        art = retrieve_fanarttv_xml( artist_menu["musicbrainz_artistid"] )
        if not len(art) < 3:
            backgrounds = art[0]["backgrounds"]
    except:
        print_exc()
    return backgrounds

def remote_clearlogo_list( artist_menu ):
    xbmc.log( "[script.cdartmanager] - Finding remote clearlogo", xbmc.LOGDEBUG )
    clearlogo = ""
    try:
        art = retrieve_fanarttv_xml( artist_menu["musicbrainz_artistid"] )
        if not len(art) < 3:
            clearlogo = art[ 1 ]["clearlogo"]
    except:
        print_exc()
    return clearlogo

def remote_artistthumb_list( artist_menu ):
    xbmc.log( "[script.cdartmanager] - Finding remote artistthumb", xbmc.LOGDEBUG )
    artistthumb = ""
    #If there is something in artist_menu["distant_id"] build cdart_url
    try:
        art = retrieve_fanarttv_xml( artist_menu["musicbrainz_artistid"] )
        if not len(art) < 3:
            artistthumb = art[ 2 ]["artistthumb"]
    except:
        print_exc()
    return artistthumb
    
def retrieve_fanarttv_xml( id ):
    xbmc.log( "[script.cdartmanager] - Retrieving artwork for artist id: %s" % id, xbmc.LOGDEBUG )
    url = music_url % ( api_key, id, "all" )
    htmlsource = get_html_source( url, id )
    music_id = '<music id="' + id + '" name="(.*?)">'
    match = re.search( music_id, htmlsource )
    artist_artwork = []
    blank = {}
    back = {}
    clearlogo = {}
    artistthumb = {}
    album_art = {}
    try:
        if match:
            backgrounds = re.search( '<artistbackgrounds>(.*?)</artistbackgrounds>', htmlsource )
            if backgrounds:
                xbmc.log( "[script.cdartmanager] - Found FanART", xbmc.LOGDEBUG )
                _background = re.findall('<artistbackground id="(?:.*?)" url="(.*?)" likes="(?:.*?)/>' , htmlsource )
                back["backgrounds"] = _background
                artist_artwork.append( back )
            else:
                xbmc.log( "[script.cdartmanager] - No FanART found", xbmc.LOGDEBUG )
                back["backgrounds"] = blank
                artist_artwork.append( back )
            clearlogos = re.search( '<musiclogos>(.*?)</musiclogos>', htmlsource )
            if clearlogos:
                xbmc.log( "[script.cdartmanager] - Found ClearLOGOs", xbmc.LOGDEBUG )
                _clearlogos = re.findall('<musiclogo id="(?:.*?)" url="(.*?)" likes="(?:.*?)/>' , htmlsource )
                clearlogo["clearlogo"] = _clearlogos
                artist_artwork.append( clearlogo )
            else:
                clearlogo["clearlogo"] = ""
                artist_artwork.append( clearlogo )
                xbmc.log( "[script.cdartmanager] - No Artist ClearLOGO found", xbmc.LOGDEBUG )
            artistthumbs = re.search( '<artistthumbs>(.*?)</artistthumbs>', htmlsource )
            if artistthumbs:
                xbmc.log( "[script.cdartmanager] - Found artistthumbs", xbmc.LOGDEBUG )
                _artistthumbs = re.findall('<artistthumb id="(?:.*?)" url="(.*?)" likes="(?:.*?)/>' , htmlsource )
                artistthumb["artistthumb"] = _artistthumbs
                artist_artwork.append( artistthumb )
            else:
                artistthumb["artistthumb"] = ""
                artist_artwork.append( artistthumb )
                xbmc.log( "[script.cdartmanager] - No Artist artistthumbs found", xbmc.LOGDEBUG )
            albums = re.search( "<albums>(.*?)</albums>", htmlsource )
            if albums:
                album = re.findall( '<album id="(.*?)">(.*?)</album>', albums.group( 1 ) )
                a_art = []
                for album_sort in album:
                    album_artwork = {}
                    album_artwork["musicbrainz_albumid"] = album_sort[ 0 ]
                    album_artwork["cdart"] = []
                    album_artwork["cover"] = ""
                    try:
                        cdart_match = re.findall( '<cdart id="(?:.*?)" url="(.*?)" likes="(?:.*?) disc="(.*?)" size="(.*?)"/>' , album_sort[ 1 ] )
                        cover_match = re.search( '<albumcover id="(?:.*?)" url="(.*?)" likes="(?:.*?)/>' , album_sort[ 1 ] )
                        if cdart_match:
                            for disc in cdart_match:
                                cdart = {}
                                cdart["disc"] = int(disc[1])
                                cdart["cdart"] = disc[0]
                                cdart["size"] = int( disc[2] )
                                album_artwork["cdart"].append(cdart)
                        if cover_match:
                            album_artwork["cover"] = cover_match.group( 1 )
                            #xbmc.log( "[script.cdartmanager] - cover: %s" % cover_match.group( 1 ), xbmc.LOGDEBUG )                        
                    except:
                        xbmc.log( "[script.cdartmanager] - No Album Artwork found", xbmc.LOGDEBUG )
                        print_exc()
                    a_art.append(album_artwork)
                album_art["artwork"] = a_art
                artist_artwork.append(album_art)
            else:
                xbmc.log( "[script.cdartmanager] - No artwork found for artist_id: %s" % id, xbmc.LOGDEBUG )
                album_art["artwork"] = blank
                artist_artwork.append( album_art )
    except:
        print_exc()
    return artist_artwork

def get_distant_artists():
    """ This retrieve the distant artist list from fanart.tv """
    xbmc.log( "[script.cdartmanager] - Retrieving Distant Artists", xbmc.LOGDEBUG )
    distant_artists = []
    htmlsource = get_html_source( artist_url % api_key, "distant" )
    match = re.compile( '<artist id="(.*?)" name="(.*?)"/>', re.DOTALL )
    for item in match.finditer( htmlsource ):
        distant = {}
        distant["name"] = unescape( ( item.group(2).replace("&amp;", "&") ) )
        distant["id"] = ( item.group(1) )
        distant_artists.append(distant)
    return distant_artists

def get_recognized( distant, local ):
    xbmc.log( "[script.cdartmanager] - Retrieving Recognized Artists from fanart.tv", xbmc.LOGDEBUG )
    true = 0
    count = 0
    name = ""
    artist_list = []
    recognized = []
    fanart_test = ""
    #percent = 0
    pDialog.create( __language__(32048) )
    #Onscreen dialog - Retrieving Recognized Artist List....
    for artist in local:
        percent = int((float(count)/len(local))*100)
        if ( pDialog.iscanceled() ):
            break
        if not artist["musicbrainz_artistid"] and lookup_id:
            artist["musicbrainz_artistid"] = update_musicbrainzid( "artist", artist )
        for d_artist in distant:
            if ( pDialog.iscanceled() ):
                break
            if artist["musicbrainz_artistid"] == d_artist["id"] and d_artist["name"]:
                true += 1
                artist["distant_id"] = d_artist["id"]
                fanart_test = fanart_test + d_artist["id"] + "|"
                break                
            else:
                artist["distant_id"] = ""
        recognized.append(artist)
        artist_list.append(artist)
        pDialog.update(percent, ( __language__(32049) % true))
        #Onscreen Dialog - Artists Matched: %
        count += 1
    print fanart_test
    xbmc.log( "[script.cdartmanager] - Total Artists Matched: %s" % true, xbmc.LOGDEBUG )
    if true == 0:
        xbmc.log( "[script.cdartmanager] - No Matches found.  Compare Artist and Album names with xbmcstuff.com", xbmc.LOGDEBUG )
    pDialog.close()   
    return recognized, artist_list    

def match_library( local_artist_list ):
    available_artwork = []
    try:
        for artist in local_artist_list:
            artist_artwork = {}
            if not artist["musicbrainz_artistid"]:
                name, artist["musicbrainz_artistid"], sortname = get_musicbrainz_artist_id( artist["name"] )
            if artist["musicbrainz_artistid"]:
                artwork = retrieve_fanarttv_xml( artist["musicbrainz_artistid"] )
                if artwork:
                    artist_artwork["name"] = artist["name"]
                    artist_artwork["musicbrainz_id"] = artist["musicbrainz_artistid"]
                    artist_artwork["artwork"] = artwork
                    available_artwork.append(artist_artwork)
                else:
                    xbmc.log( "[script.cdartmanager] - Unable to match artist on fanart.tv: %s" % repr( artist["name"] ), xbmc.LOGDEBUG )
            else:
                xbmc.log( "[script.cdartmanager] - Unable to match artist on Musicbrainz: %s" % repr( artist["name"] ), xbmc.LOGDEBUG )
    except:
        print_exc()
    return available_artwork