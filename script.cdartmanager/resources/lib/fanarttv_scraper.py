# -*- coding: utf-8 -*-
# fanart.tv artist artwork scraper

import calendar
import sys
import os
from datetime import datetime
from traceback import print_exc

import xbmc
import xbmcvfs

if sys.version_info < (2, 7):
    import simplejson
else:
    import json as simplejson

__language__ = sys.modules["__main__"].__language__
__scriptname__ = sys.modules["__main__"].__scriptname__
__scriptID__ = sys.modules["__main__"].__scriptID__
__author__ = sys.modules["__main__"].__author__
__credits__ = sys.modules["__main__"].__credits__
__credits2__ = sys.modules["__main__"].__credits2__
__version__ = sys.modules["__main__"].__version__
__addon__ = sys.modules["__main__"].__addon__
addon_db = sys.modules["__main__"].addon_db
addon_work_folder = sys.modules["__main__"].addon_work_folder
BASE_RESOURCE_PATH = sys.modules["__main__"].BASE_RESOURCE_PATH
api_key = sys.modules["__main__"].api_key
enable_all_artists = sys.modules["__main__"].enable_all_artists
tempxml_folder = sys.modules["__main__"].tempxml_folder

from utils import get_html_source, log, dialog_msg
from database import store_lalist, store_local_artist_table, store_fanarttv_datecode, retrieve_fanarttv_datecode

music_url_json = "http://webservice.fanart.tv/v3/music/%s?api_key=%s"
new_music = "http://webservice.fanart.tv/v3/music/latest?api_key=%s&date=%s"

lookup_id = False


def remote_cdart_list(artist_menu):
    log("Finding remote cdARTs", xbmc.LOGDEBUG)
    cdart_url = []
    try:
        art = retrieve_fanarttv_json(artist_menu["musicbrainz_artistid"])
        if not len(art) < 2:
            album_artwork = art[5]["artwork"]
            if album_artwork:
                for artwork in album_artwork:
                    for cdart in artwork["cdart"]:
                        album = {}
                        album["artistl_id"] = artist_menu["local_id"]
                        album["artistd_id"] = artist_menu["musicbrainz_artistid"]
                        try:
                            album["local_name"] = album["artist"] = artist_menu["name"]
                        except KeyError:
                            album["local_name"] = album["artist"] = artist_menu["artist"]
                        album["musicbrainz_albumid"] = artwork["musicbrainz_albumid"]
                        album["disc"] = cdart["disc"]
                        album["size"] = cdart["size"]
                        album["picture"] = cdart["cdart"]
                        album["thumb_art"] = cdart["cdart"]
                        cdart_url.append(album)
                        # log( "cdart_url: %s " % cdart_url, xbmc.LOGDEBUG )
    except:
        print_exc()
    return cdart_url


def remote_coverart_list(artist_menu):
    log("Finding remote Cover ARTs", xbmc.LOGDEBUG)
    coverart_url = []
    try:
        art = retrieve_fanarttv_json(artist_menu["musicbrainz_artistid"])
        if not len(art) < 2:



            album_artwork = art[5]["artwork"]
            if album_artwork:
                for artwork in album_artwork:
                    if artwork["cover"]:
                        album = {}
                        album["artistl_id"] = artist_menu["local_id"]
                        album["artistd_id"] = artist_menu["musicbrainz_artistid"]
                        album["local_name"] = album["artist"] = artist_menu["name"]
                        album["musicbrainz_albumid"] = artwork["musicbrainz_albumid"]
                        album["size"] = 1000
                        album["picture"] = artwork["cover"]
                        album["thumb_art"] = artwork["cover"]
                        coverart_url.append(album)
                        # log( "cdart_url: %s " % cdart_url, xbmc.LOGDEBUG )
    except:
        print_exc()
    return coverart_url


def remote_fanart_list(artist_menu):
    log("Finding remote fanart", xbmc.LOGDEBUG)
    backgrounds = ""
    try:
        art = retrieve_fanarttv_json(artist_menu["musicbrainz_artistid"])
        if not len(art) < 3:
            backgrounds = art[0]["backgrounds"]
    except:
        print_exc()
    return backgrounds


def remote_clearlogo_list(artist_menu):
    log("Finding remote clearlogo", xbmc.LOGDEBUG)
    clearlogo = ""
    try:
        art = retrieve_fanarttv_json(artist_menu["musicbrainz_artistid"])
        if not len(art) < 3:
            clearlogo = art[1]["clearlogo"]
    except:
        print_exc()
    return clearlogo


def remote_hdlogo_list(artist_menu):
    log("Finding remote hdlogo", xbmc.LOGDEBUG)
    hdlogo = ""
    try:
        art = retrieve_fanarttv_json(artist_menu["musicbrainz_artistid"])
        if not len(art) < 3:
            hdlogo = art[3]["hdlogo"]
    except:
        print_exc()
    return hdlogo


def remote_banner_list(artist_menu):
    log("Finding remote music banners", xbmc.LOGDEBUG)
    banner = ""
    try:
        art = retrieve_fanarttv_json(artist_menu["musicbrainz_artistid"])
        if not len(art) < 3:
            banner = art[4]["banner"]
    except:
        print_exc()
    return banner


def remote_artistthumb_list(artist_menu):
    log("Finding remote artistthumb", xbmc.LOGDEBUG)
    artistthumb = ""
    # If there is something in artist_menu["distant_id"] build cdart_url
    try:
        art = retrieve_fanarttv_json(artist_menu["musicbrainz_artistid"])
        if not len(art) < 3:
            artistthumb = art[2]["artistthumb"]
    except:
        print_exc()
    return artistthumb


def retrieve_fanarttv_json(id):
    log("Retrieving artwork for artist id: %s" % id, xbmc.LOGDEBUG)
    # url = music_url_json % (api_key, id, "all")
    url = music_url_json % (id, api_key)
    # htmlsource = (get_html_source(url, id, save_file=False, overwrite=False)).encode('utf-8', 'ignore')
    htmlsource = get_html_source(url, "FTV_"+str(id), save_file=True, overwrite=False)
    artist_artwork = []
    backgrounds = []
    musiclogos = []
    artistthumbs = []
    hdlogos = []
    banners = []
    albums = []
    blank = {}
    fanart = {}
    clearlogo = {}
    artistthumb = {}
    album_art = {}
    hdlogo = {}
    banner = {}
    artist = ""
    artist_id = ""
    IMAGE_TYPES = ['musiclogo',
                   'artistthumb',
                   'artistbackground',
                   'hdmusiclogo',
                   'musicbanner',
                   'albums']
    try:
        data = simplejson.loads(htmlsource)
        # for key, value in data.iteritems():
        for art in IMAGE_TYPES:
            # if value.has_key(art):
            if data.has_key(art):
                # for item in value[art]:
                for item in data[art]:
                    if art == "musiclogo":
                        musiclogos.append(item.get('url'))
                    if art == "hdmusiclogo":
                        hdlogos.append(item.get('url'))
                    if art == "artistbackground":
                        backgrounds.append(item.get('url'))
                    if art == "musicbanner":
                        banners.append(item.get('url'))
                    if art == "artistthumb":
                        artistthumbs.append(item.get('url'))
                    if art == "albums" and not albums:
                        # for album_id in data[artist]["albums"]:
                        for album_id, album in data["albums"].iteritems():
                            album_artwork = {"musicbrainz_albumid": album_id, "cdart": [], "cover": ""}
                            # if value["albums"][album_id].has_key("cdart"):
                            if album.has_key("cdart"):
                                # for item in value["albums"][album_id]["cdart"]:
                                for item in album["cdart"]:
                                    cdart = {}
                                    if item.has_key("disc"):
                                        cdart["disc"] = int(item["disc"])
                                    else:
                                        cdart["disc"] = 1
                                    if item.has_key("url"):
                                        cdart["cdart"] = item["url"]
                                    else:
                                        cdart["cdart"] = ""
                                    if item.has_key("size"):
                                        cdart["size"] = int(item["size"])
                                    album_artwork["cdart"].append(cdart)
                            try:
                                if album.has_key("albumcover"):
                                    #if len(album["albumcover"]) < 2:
                                    # this is a quick fix, we should download the first hit here if there are multiple covers
                                    album_artwork["cover"] = album["albumcover"][0]["url"]
                            except:
                                album_artwork["cover"] = ""
                            albums.append(album_artwork)
    except:
        print_exc()
    fanart["backgrounds"] = backgrounds
    clearlogo["clearlogo"] = musiclogos
    hdlogo["hdlogo"] = hdlogos
    banner["banner"] = banners
    artistthumb["artistthumb"] = artistthumbs
    album_art["artwork"] = albums
    artist_artwork.append(fanart)
    artist_artwork.append(clearlogo)
    artist_artwork.append(artistthumb)
    artist_artwork.append(hdlogo)
    artist_artwork.append(banner)
    artist_artwork.append(album_art)
    # print artist_artwork
    return artist_artwork


def check_fanart_new_artwork(present_datecode):
    log("Checking for new Artwork on fanart.tv since last run...", xbmc.LOGNOTICE)
    previous_datecode = retrieve_fanarttv_datecode()
    # fix: use global tempxml_folder instead of explicit definition
    if xbmcvfs.exists(os.path.join(tempxml_folder, "%s.xml" % previous_datecode)):
        xbmcvfs.delete(os.path.join(tempxml_folder, "%s.xml" % previous_datecode))
    url = new_music % (api_key, str(previous_datecode))
    htmlsource = get_html_source(url, "FTV-NEW_"+str(present_datecode), save_file=True, overwrite=False)
    if htmlsource == "null":
        log("No new Artwork found on fanart.tv", xbmc.LOGNOTICE)
        return False, htmlsource
    else:
        try:
            log("New Artwork found on fanart.tv", xbmc.LOGNOTICE)
            data = simplejson.loads(htmlsource)
            return True, data
        except:
            htmlsource = "null"
            print_exc()
            return False, htmlsource


def check_art(mbid, artist_type="album"):
    has_art = "False"
    # url = music_url_json % (api_key, str(mbid), "all")
    url = music_url_json % (str(mbid), api_key)
    htmlsource = get_html_source(url, "FTV_"+str(mbid), save_file=True, overwrite=True)
    if htmlsource == "null":
        log("No artwork found for MBID: %s" % mbid, xbmc.LOGDEBUG)
        has_art = "False"
    else:
        log("Artwork found for MBID: %s" % mbid, xbmc.LOGDEBUG)
        has_art = "True"
    return has_art


def update_art(mbid, data, existing_has_art):
    has_art = existing_has_art
    for item in data:
        if item["id"] == mbid:
            # url = music_url_json % (api_key, str(mbid), "all")
            url = music_url_json % (str(mbid), api_key)
            has_art = "True"
            #            new_art = (get_html_source(url, str(mbid), save_file=True, overwrite=True)).encode('utf-8', 'ignore')
            new_art = get_html_source(url, "FTV_"+str(mbid), save_file=True, overwrite=True)
            break
    return has_art


def first_check(all_artists, album_artists, background=False, update_db=False):
    log("Checking for artist match with fanart.tv - First Check", xbmc.LOGNOTICE)
    heading = __language__(32187)
    album_artists_matched = []
    all_artists_matched = []
    d = datetime.utcnow()
    present_datecode = calendar.timegm(d.utctimetuple())
    count = 0
    name = ""
    artist_list = []
    all_artist_list = []
    recognized = []
    recognized_album = []
    fanart_test = ""
    dialog_msg("create", heading="", background=background)
    for artist in album_artists:
        percent = int((float(count) / len(album_artists)) * 100)
        log("Checking artist MBID: %s" % artist["musicbrainz_artistid"], xbmc.LOGDEBUG)
        match = {}
        match = artist
        if artist["musicbrainz_artistid"] and (artist["has_art"] == "False" or update_db):
            match["has_art"] = check_art(artist["musicbrainz_artistid"], artist_type="album")
        elif not artist["musicbrainz_artistid"]:
            match["has_art"] = "False"
        else:
            match["has_art"] = artist["has_art"]
        album_artists_matched.append(match)
        dialog_msg("update", percent=percent, line1=heading, line2="", line3=__language__(32049) % artist["name"],
                   background=background)
        count += 1
    log("Storing Album Artists List", xbmc.LOGDEBUG)
    store_lalist(album_artists_matched, len(album_artists_matched))
    if enable_all_artists and all_artists:
        count = 0
        for artist in all_artists:
            percent = int((float(count) / len(all_artists)) * 100)
            log("Checking artist MBID: %s" % artist["musicbrainz_artistid"], xbmc.LOGDEBUG)
            match = {}
            match = artist
            if artist["musicbrainz_artistid"] and (artist["has_art"] == "False" or update_db):
                match["has_art"] = check_art(artist["musicbrainz_artistid"], artist_type="all_artist")
            elif not artist["musicbrainz_artistid"]:
                match["has_art"] = "False"
            else:
                match["has_art"] = artist["has_art"]
            all_artists_matched.append(match)
            dialog_msg("update", percent=percent, line1=heading, line2="", line3=__language__(32049) % artist["name"],
                       background=background)
            count += 1
        store_local_artist_table(all_artists_matched, background=background)
    store_fanarttv_datecode(present_datecode)
    dialog_msg("close", background=background)
    log("Finished First Check", xbmc.LOGDEBUG)
    return


def get_recognized(all_artists, album_artists, background=False):
    log("Checking for artist match with fanart.tv - Get Recognized artists", xbmc.LOGNOTICE)
    album_artists_matched = []
    all_artists_matched = []
    count = 0
    dialog_msg("create", heading="", background=background)
    present_datecode = calendar.timegm(datetime.utcnow().utctimetuple())
    new_artwork, data = check_fanart_new_artwork(present_datecode)
    if new_artwork:
        for artist in album_artists:
            percent = int((float(count) / len(album_artists)) * 100)
            log("Checking artist MBID: %s" % artist["musicbrainz_artistid"], xbmc.LOGDEBUG)
            match = artist
            if match["musicbrainz_artistid"]:
                match["has_art"] = update_art(match["musicbrainz_artistid"], data, artist["has_art"])
            album_artists_matched.append(match)
            dialog_msg("update", percent=percent, line1=__language__(32185), line2="",
                       line3=__language__(32049) % artist["name"], background=background)
            count += 1
        if enable_all_artists and all_artists:
            count = 0
            for artist in all_artists:
                percent = int((float(count) / len(all_artists)) * 100)
                log("Checking artist MBID: %s" % artist["musicbrainz_artistid"], xbmc.LOGDEBUG)
                match = artist
                if match["musicbrainz_artistid"]:
                    match["has_art"] = update_art(match["musicbrainz_artistid"], data, artist["has_art"])
                all_artists_matched.append(match)
                dialog_msg("update", percent=percent, line1=__language__(32185), line2="",
                           line3=__language__(32049) % artist["name"], background=background)
                count += 1
    else:
        log("No new music artwork on fanart.tv", xbmc.LOGNOTICE)
        album_artists_matched = album_artists
        all_artists_matched = all_artists
    store_lalist(album_artists_matched, len(album_artists_matched))
    store_local_artist_table(all_artists_matched, background=background)
    store_fanarttv_datecode(present_datecode)
    dialog_msg("close", background=background)
    log("Finished Getting Recognized Artists", xbmc.LOGDEBUG)
    return all_artists_matched, album_artists_matched
