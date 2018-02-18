# -*- coding: utf-8 -*-
# fanart.tv artist artwork scraper

import calendar
import json
import os
from datetime import datetime
from traceback import print_exc

import xbmc
import xbmcvfs

import cdam
from cdam import Def, ArtType
from cdam_db import store_lalist, store_local_artist_table, store_fanarttv_datecode, retrieve_fanarttv_datecode
from cdam_utils import get_html_source, log, dialog_msg, percent_of

__cdam__ = cdam.CDAM()
__cfg__ = cdam.Settings()
__lng__ = __cdam__.getLocalizedString

music_url_json = "http://webservice.fanart.tv/v3/music/%s?api_key=%s&client_key=%s"
new_music = "http://webservice.fanart.tv/v3/music/latest?api_key=%s&client_key=%s&date=%s"


def remote_cdart_list(artist_menu):
    log("Finding remote cdARTs")
    cdart_url = []
    try:
        art = retrieve_fanarttv_json(artist_menu["musicbrainz_artistid"])
        if not len(art) < 2:
            album_artwork = art[5]["artwork"]
            if album_artwork:
                for artwork in album_artwork:
                    for cdart in artwork[ArtType.CDART]:
                        album = {"artistl_id": artist_menu["local_id"],
                                 "artistd_id": artist_menu["musicbrainz_artistid"],
                                 "musicbrainz_albumid": artwork["musicbrainz_albumid"], "disc": cdart["disc"],
                                 "size": cdart["size"], "picture": cdart[ArtType.CDART],
                                 "thumb_art": cdart[ArtType.CDART]}
                        try:
                            album["local_name"] = album["artist"] = artist_menu["name"]
                        except KeyError:
                            album["local_name"] = album["artist"] = artist_menu["artist"]
                        cdart_url.append(album)
                        # log( "cdart_url: %s " % cdart_url)
    except Exception as e:
        log(e.message, xbmc.LOGERROR)
        print_exc()
    return cdart_url


def remote_coverart_list(artist_menu):
    log("Finding remote Cover ARTs")
    coverart_url = []
    try:
        art = retrieve_fanarttv_json(artist_menu["musicbrainz_artistid"])
        if not len(art) < 2:

            album_artwork = art[5]["artwork"]
            if album_artwork:
                for artwork in album_artwork:
                    if artwork[ArtType.COVER]:
                        album = {"artistl_id": artist_menu["local_id"],
                                 "artistd_id": artist_menu["musicbrainz_artistid"], "local_name": artist_menu["name"],
                                 "artist": artist_menu["name"], "musicbrainz_albumid": artwork["musicbrainz_albumid"],
                                 "size": 1000, "picture": artwork[ArtType.COVER], "thumb_art": artwork[ArtType.COVER]}
                        coverart_url.append(album)
                        # log( "cdart_url: %s " % cdart_url )
    except Exception as e:
        log(e.message, xbmc.LOGERROR)
        print_exc()
    return coverart_url


def remote_fanart_list(artist_menu):
    log("Finding remote fanart")
    backgrounds = ""
    try:
        art = retrieve_fanarttv_json(artist_menu["musicbrainz_artistid"])
        if not len(art) < 3:
            backgrounds = art[0]["backgrounds"]
    except Exception as e:
        log(e.message, xbmc.LOGERROR)
        print_exc()
    return backgrounds


def remote_clearlogo_list(artist_menu):
    log("Finding remote clearlogo")
    clearlogo = ""
    try:
        art = retrieve_fanarttv_json(artist_menu["musicbrainz_artistid"])
        if not len(art) < 3:
            clearlogo = art[1]["clearlogo"]
    except Exception as e:
        log(e.message, xbmc.LOGERROR)
        print_exc()
    return clearlogo


def remote_hdlogo_list(artist_menu):
    log("Finding remote hdlogo")
    hdlogo = ""
    try:
        art = retrieve_fanarttv_json(artist_menu["musicbrainz_artistid"])
        if not len(art) < 3:
            hdlogo = art[3]["hdlogo"]
    except Exception as e:
        log(e.message, xbmc.LOGERROR)
        print_exc()
    return hdlogo


def remote_banner_list(artist_menu):
    log("Finding remote music banners")
    banner = ""
    try:
        art = retrieve_fanarttv_json(artist_menu["musicbrainz_artistid"])
        if not len(art) < 3:
            banner = art[4]["banner"]
    except Exception as e:
        log(e.message, xbmc.LOGERROR)
        print_exc()
    return banner


def remote_artistthumb_list(artist_menu):
    log("Finding remote artistthumb")
    artistthumb = ""
    # If there is something in artist_menu["distant_id"] build cdart_url
    try:
        art = retrieve_fanarttv_json(artist_menu["musicbrainz_artistid"])
        if not len(art) < 3:
            artistthumb = art[2]["artistthumb"]
    except Exception as e:
        log(e.message, xbmc.LOGERROR)
        print_exc()
    return artistthumb


def retrieve_fanarttv_json(id_):
    log("Retrieving artwork for artist id: %s" % id_)
    # url = music_url_json % (api_key, id, "all")
    url = music_url_json % (id_, Def.FANARTTV_API_KEY, __cfg__.client_key())
    # htmlsource = (get_html_source(url, id, save_file=False, overwrite=False)).encode('utf-8', 'ignore')
    htmlsource = get_html_source(url, "FTV_" + str(id_), save_file=True, overwrite=False)
    artist_artwork = []
    backgrounds = []
    musiclogos = []
    artistthumbs = []
    hdlogos = []
    banners = []
    albums = []
    fanart = {}
    clearlogo = {}
    artistthumb = {}
    album_art = {}
    hdlogo = {}
    banner = {}
    image_types = ['musiclogo',
                   'artistthumb',
                   'artistbackground',
                   'hdmusiclogo',
                   'musicbanner',
                   'albums']
    try:
        data = json.loads(htmlsource)
        # for key, value in data.iteritems():
        for art in image_types:
            # if value.has_key(art):
            if art in data:
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
                            album_artwork = {"musicbrainz_albumid": album_id, ArtType.CDART: [], ArtType.COVER: ""}
                            if ArtType.CDART in album:
                                for subitem in album[ArtType.CDART]:
                                    cdart = {}
                                    if "disc" in subitem:
                                        cdart["disc"] = int(subitem["disc"])
                                    else:
                                        cdart["disc"] = 1
                                    if "url" in subitem:
                                        cdart[ArtType.CDART] = subitem["url"]
                                    else:
                                        cdart[ArtType.CDART] = ""
                                    if "size" in subitem:
                                        cdart["size"] = int(subitem["size"])
                                    album_artwork[ArtType.CDART].append(cdart)
                            try:
                                if "albumcover" in album:
                                    # if len(album["albumcover"]) < 2:
                                    # we should download the first hit here if there are multiple covers
                                    album_artwork[ArtType.COVER] = album["albumcover"][0]["url"]
                            except Exception as e:
                                log(e.message)
                                album_artwork[ArtType.COVER] = ""
                            albums.append(album_artwork)
    except Exception as e:
        log(e.message, xbmc.LOGERROR)
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
    tempxml_folder = __cdam__.path_temp_xml()
    if xbmcvfs.exists(os.path.join(tempxml_folder, "%s.xml" % previous_datecode)):
        xbmcvfs.delete(os.path.join(tempxml_folder, "%s.xml" % previous_datecode))
    url = new_music % (Def.FANARTTV_API_KEY, __cfg__.client_key(), str(previous_datecode))
    htmlsource = get_html_source(url, "FTV-NEW_" + str(present_datecode), save_file=True, overwrite=False)
    if htmlsource == "null":
        log("No new Artwork found on fanart.tv", xbmc.LOGNOTICE)
        return False, htmlsource
    else:
        try:
            log("New Artwork found on fanart.tv", xbmc.LOGNOTICE)
            data = json.loads(htmlsource)
            return True, data
        except Exception as e:
            htmlsource = "null"
            xbmc.log(e.message, xbmc.LOGERROR)
            print_exc()
            return False, htmlsource


def check_art(mbid):
    url = music_url_json % (str(mbid), Def.FANARTTV_API_KEY, __cfg__.client_key())
    htmlsource = get_html_source(url, "FTV_" + str(mbid), save_file=True, overwrite=True)
    if htmlsource == "null":
        log("No artwork found for MBID: %s" % mbid)
        has_art = "False"
    else:
        log("Artwork found for MBID: %s" % mbid)
        has_art = "True"
    return has_art


def update_art(mbid, data, existing_has_art):
    has_art = existing_has_art
    for item in data:
        if item["id"] == mbid:
            url = music_url_json % (str(mbid), Def.FANARTTV_API_KEY, __cfg__.client_key())
            has_art = "True"
            get_html_source(url, "FTV_" + str(mbid), save_file=True, overwrite=True)
            break
    return has_art


def first_check(all_artists, album_artists, background=False, update_db=False):
    log("Checking for artist match with fanart.tv - First Check", xbmc.LOGNOTICE)
    heading = __lng__(32187)
    album_artists_matched = []
    all_artists_matched = []
    d = datetime.utcnow()
    present_datecode = calendar.timegm(d.utctimetuple())
    count = 0
    dialog_msg("create", heading="", background=background)
    for artist in album_artists:
        log("Checking artist MBID: %s" % artist["musicbrainz_artistid"])
        match = artist
        if artist["musicbrainz_artistid"] and (artist["has_art"] == "False" or update_db):
            match["has_art"] = check_art(artist["musicbrainz_artistid"])
        elif not artist["musicbrainz_artistid"]:
            match["has_art"] = "False"
        else:
            match["has_art"] = artist["has_art"]
        album_artists_matched.append(match)
        dialog_msg("update", percent=percent_of(float(count), len(album_artists)), line1=heading,
                   line2="", line3=__lng__(32049) % artist["name"], background=background)
        count += 1
    log("Storing Album Artists List")
    store_lalist(album_artists_matched)
    if __cfg__.enable_all_artists() and all_artists:
        count = 0
        for artist in all_artists:
            log("Checking artist MBID: %s" % artist["musicbrainz_artistid"])
            match = artist
            if artist["musicbrainz_artistid"] and (artist["has_art"] == "False" or update_db):
                match["has_art"] = check_art(artist["musicbrainz_artistid"])
            elif not artist["musicbrainz_artistid"]:
                match["has_art"] = "False"
            else:
                match["has_art"] = artist["has_art"]
            all_artists_matched.append(match)
            dialog_msg("update", percent=percent_of(float(count), len(all_artists)), line1=heading,
                       line2="", line3=__lng__(32049) % artist["name"], background=background)
            count += 1
        store_local_artist_table(all_artists_matched, background=background)
    store_fanarttv_datecode(present_datecode)
    dialog_msg("close", background=background)
    log("Finished First Check")
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
            log("Checking artist MBID: %s" % artist["musicbrainz_artistid"])
            match = artist
            if match["musicbrainz_artistid"]:
                match["has_art"] = update_art(match["musicbrainz_artistid"], data, artist["has_art"])
            album_artists_matched.append(match)
            dialog_msg("update", percent=percent_of(float(count), len(album_artists)), line1=__lng__(32185), line2="",
                       line3=__lng__(32049) % artist["name"], background=background)
            count += 1
        if __cfg__.enable_all_artists() and all_artists:
            count = 0
            for artist in all_artists:
                log("Checking artist MBID: %s" % artist["musicbrainz_artistid"])
                match = artist
                if match["musicbrainz_artistid"]:
                    match["has_art"] = update_art(match["musicbrainz_artistid"], data, artist["has_art"])
                all_artists_matched.append(match)
                dialog_msg("update", percent=percent_of(float(count), len(all_artists)), line1=__lng__(32185), line2="",
                           line3=__lng__(32049) % artist["name"], background=background)
                count += 1
    else:
        log("No new music artwork on fanart.tv", xbmc.LOGNOTICE)
        album_artists_matched = album_artists
        all_artists_matched = all_artists
    store_lalist(album_artists_matched)
    store_local_artist_table(all_artists_matched, background=background)
    store_fanarttv_datecode(present_datecode)
    dialog_msg("close", background=background)
    log("Finished Getting Recognized Artists")
    return all_artists_matched, album_artists_matched
