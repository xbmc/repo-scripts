#!/usr/bin/python
# -*- coding: utf-8 -*-

#  This program is free software; you can redistribute it and/or modify
#  it under the terms of the GNU General Public License as published by
#  the Free Software Foundation; either version 3 of the License, or
#  (at your option) any later version.
#
#  This program is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with this program; if not, write to the Free Software
#  Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston,
#  MA 02110-1301, USA.
#
#  (c) 2023 black_eagle

import xbmc
import xbmcaddon
import xbmcgui

import json
import sys
import urllib.parse
import urllib.request
from urllib.error import HTTPError
from urllib.error import URLError

ADDON = xbmcaddon.Addon()
ADDONID = ADDON.getAddonInfo('id')
ADDONNAME = ADDON.getAddonInfo('name')
ADDONVERSION = ADDON.getAddonInfo('version')
ICON = ADDON.getAddonInfo('icon')
LANGUAGE = ADDON.getLocalizedString

AUDIODBKEY = '95424d43204d6564696538'
AUDIODBURL = 'https://www.theaudiodb.com/api/v1/json/%s/%s'
AUDIODBMVIDS = 'mvid-mb.php?i=%s'


def log(txt, level=xbmc.LOGDEBUG):
    message = '%s: %s' % (LANGUAGE(30000), txt)
    xbmc.log(msg=message, level=level)


def get_mvid_data(artist_mbid):
    mvidurl = AUDIODBURL % (AUDIODBKEY, AUDIODBMVIDS % artist_mbid)
    headers = {}
    headers['User-Agent'] = ('%s/%s ( http://kodi.tv )'
                             % (ADDONNAME, ADDONVERSION))
    try:
        req = urllib.request.Request(mvidurl, headers=headers)
        resp = urllib.request.urlopen(req, timeout=5)
    except HTTPError as e:
        message = LANGUAGE(30001) + " {} {} ".format(e.code, e.reason)
        message = message + LANGUAGE(30017) + " {}".format(mvidurl)
        exit_on_error(message)
    except URLError as e:
        message = LANGUAGE(30002) + " {} ".format(e.reason)
        message = message + LANGUAGE(30017) + " {}".format(mvidurl)
        exit_on_error(message)
    else:
        respdata = resp.read()
        mvid_data = json.loads(respdata)
    return mvid_data


def update_songs(songstoupdate):
    for songs in songstoupdate:
        have_art = True
        songid = songs['songid']
        vidurl = songs['strVideoURL']
        vidthumb = songs['strVideoThumb']
        log(LANGUAGE(30003) + " " + str(songid) + " " + LANGUAGE(30004))
        # Only add in the art stuff if we have any,
        # else the jsonrpc will complain about the art field being too small
        if vidthumb is None:
            vidthumb = ""
            have_art = False
        rpc_string = (
            '{"jsonrpc":"2.0","id":1,"method":"audioLibrary.SetSongDetails", \
             "params":{"songid":' + str(songid) + ',\
             "songvideourl": "' + vidurl + '"}')
        if have_art:
            rpc_string = (
                rpc_string + ', "art": {"videothumb": "' + vidthumb + '"}}')
        else:
            rpc_string = rpc_string + '}'

        res = xbmc.executeJSONRPC(rpc_string)
        result = json.loads(res)
        if result['result'] != "OK":
            message = LANGUAGE(30006) + " - {}".format(res)
            exit_on_error(message)
        xbmc.sleep(5)


def get_songs_for_artist(artist_id):
    getsongs = xbmc.executeJSONRPC('{"jsonrpc":"2.0", \
    "id":1,"method":"audioLibrary.GetSongs", \
    "params":{"filter": {"artistid": ' + artist_id + '}, \
    "properties":["musicbrainztrackid"]}}')
    thesongs = json.loads(getsongs)
    songlist = thesongs['result']['songs']
    return songlist


def match_mvids_to_songs(mvidlist, songlist):
    for item in mvidlist:
        songstoupdate = []
        mviddata = {}
        mviddata['title'] = item['strTrack']
        mviddata['mbtrackid'] = item.get('strMusicBrainzID')
        tempurl = item.get('strMusicVid', '')
        log(tempurl)
        # Find and remove extraneous data in the URL leaving just the video ID
        index = tempurl.find('=')
        vid_id = tempurl[index+1:]
        http_index = vid_id.find('//youtu.be/')
        if http_index != -1:
            vid_id = vid_id[http_index+11:]
            log(vid_id)
        check1 = vid_id.find('/www.youtube.com/embed/')
        if check1 != -1:
            vid_id = vid_id[check1 + 23:check1 + 34]
            log(vid_id)

        mviddata['url'] = \
            'plugin://plugin.video.youtube/play/?video_id=%s' % vid_id
        mviddata['thumb'] = item.get('strTrackThumb', '')
        for songinfo in songlist:
            songdata = {}
            if songinfo['musicbrainztrackid'] == mviddata['mbtrackid'] \
                    or songinfo['label'].lower() == mviddata['title'].lower():
                songdata['songid'] = songinfo['songid']
                songdata['strVideoURL'] = mviddata['url']
                songdata['strVideoThumb'] = mviddata['thumb']
                xbmc.sleep(5)
                if songdata:
                    songstoupdate.append(songdata)
        if songstoupdate:
            update_songs(songstoupdate)


def process_all_artists():
    monitor = xbmc.Monitor()
    while not monitor.abortRequested():
        artist_list = xbmc.executeJSONRPC('{"jsonrpc": "2.0", "id": 1, \
        "method": "AudioLibrary.GetArtists", \
        "params": {"sort": { "order": "ascending", \
        "ignorearticle": true, "method": "label", \
        "albumartistsonly": true}, "properties":["musicbrainzartistid"]}}')
        artistlist = json.loads(artist_list)
        total_artists = artistlist['result']['limits']['total']
        log(LANGUAGE(30008))
        dialog = xbmcgui.DialogProgress()
        dialog.create(LANGUAGE(30015), LANGUAGE(30016))
        start_value = 0
        xbmc.sleep(100)

        for artist in artistlist['result']['artists']:
            xbmc.sleep(1)
            start_value += 1
            artist_id = artist['artistid']
            artist_name = artist['artist']
            artist_mbid = artist['musicbrainzartistid'][0]
            message = LANGUAGE(30009) + " {} " .format(artist_id)
            message = message + LANGUAGE(30010) + " {}".format(artist_name)
            log(message)
            if artist_id == 1 and 'missing' in artist_name.lower():
                log(LANGUAGE(30011))
                continue
            message = artist_name
            dialog.update(int((start_value / total_artists) * 100), message)
            log(LANGUAGE(30012) + "'" + artist_name + "'")

            if dialog.iscanceled():
                log(LANGUAGE(30013))
                dialog.close()
                return

            if monitor.abortRequested():
                return

            songlist = []
            songlist = get_songs_for_artist(str(artist_id))
            if artist_mbid is None or artist_mbid == "":
                continue
            mvid_data = get_mvid_data(artist_mbid)
            mvidlist = mvid_data.get('mvids', [])

            if monitor.abortRequested():
                return

            if mvidlist:
                match_mvids_to_songs(mvidlist, songlist)
        dialog.close()
        del monitor
        return


def single_artist(artist_id):
    response = xbmc.executeJSONRPC('{"jsonrpc": "2.0", "id": 1,\
    "method": "AudioLibrary.GetArtistDetails","params":{"artistid":'
                                   + artist_id +
                                   ',"properties":["musicbrainzartistid"]}}')
    artists = json.loads(response)
    artist_mbid = artists['result']['artistdetails']['musicbrainzartistid'][0]

    if artist_mbid is None or artist_mbid == "":
        return

    songlist = []
    songlist = get_songs_for_artist(artist_id)
    mvid_data = get_mvid_data(artist_mbid)
    mvidlist = mvid_data.get('mvids', [])
    if mvidlist:
        match_mvids_to_songs(mvidlist, songlist)


def exit_on_error(the_error):
    log(the_error, xbmc.LOGERROR)
    xbmcgui.Dialog().notification(LANGUAGE(30000), LANGUAGE(30014), ICON)
    sys.exit(1)
