#!/usr/bin/python
import os

"""
The MIT License (MIT)

Copyright (c) 2015 Maker Musings && m0ngr31, ylazarev && pineur

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in
all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
THE SOFTWARE.
"""

# For a complete discussion, see http://forum.kodi_helpers.tv/showthread.php?tid=254502

import datetime
import json
import os.path
import random
import re
import string
import sys
import time
from multiprocessing import Process
import xbmc
import xbmcgui
import xbmcaddon
from texts import localize

sys.path += [os.path.dirname(__file__)]

try:
    import aniso8601
    import verifier
except:
    # cert/appid verification dependencies are optional installs
    pass

import kodi_helpers

ENV_FILE = os.path.join(os.path.dirname(__file__), ".env")
KODI_ID = None


# These utility functions construct the required JSON for a full Alexa Skills Kit response

def build_response(session_attributes, speechlet_response):
    response = {
        'version': '1.0',
        'sessionAttributes': session_attributes,
        'response': speechlet_response
    }

    return response


def build_speechlet_response(title, output, reprompt_text, should_end_session):
    response = {}

    if output:
        response['outputSpeech'] = {
            'type': 'PlainText',
            'text': output
        }
        if title:
            response['card'] = {
                'type': 'Simple',
                'title': title,
                'content': output
            }

    if reprompt_text:
        response['reprompt'] = {
            'outputSpeech': {
                'type': 'PlainText',
                'text': reprompt_text
            }
        }
    response['shouldEndSession'] = should_end_session

    return response


# def build_alexa_response(speech = " ", card_title = None, session_attrs = {}, reprompt_text = " ", end_session = True):
def build_alexa_response(speech=" ", card_title=None, **kwargs):
    session_attrs = {}
    reprompt_text = " "
    end_session = True

    if 'session_attrs' in kwargs:
        session_attrs = kwargs['session_attrs']
    if 'reprompt_text' in kwargs:
        reprompt_text = kwargs['reprompt_text']
    if 'end_session' in kwargs:
        end_session = kwargs['end_session']

    return build_response(session_attrs, build_speechlet_response(card_title, speech, reprompt_text, end_session))


# Utility function to sanitize name of media (e.g., strip out symbols)

RE_NAME_WITH_PARAM = re.compile(r"(.*) \([^)]+\)$")


def sanitize_name(media_name):
    m = RE_NAME_WITH_PARAM.match(media_name)
    if m:
        return m.group(1)
    return media_name


# Handle the NewShowInquiry intent.
def alexa_new_show_inquiry(slots):
    heard_show = str(slots['Show']['value']).lower().translate(None, string.punctuation)

    card_title = localize(32040) % (heard_show,)  # @@


    shows = kodi_helpers.GetTvShows()
    if 'result' in shows and 'tvshows' in shows['result']:
        shows_array = shows['result']['tvshows']

        located = kodi_helpers.matchHeard(heard_show, shows_array)

        if located:
            episodes_result = kodi_helpers.GetUnwatchedEpisodesFromShow(located['tvshowid'])

            if not 'episodes' in episodes_result['result']:
                num_of_unwatched = 0

            else:
                num_of_unwatched = len(episodes_result['result']['episodes'])

            if num_of_unwatched > 0:
                if num_of_unwatched == 1:
                    return build_alexa_response(
                        localize(32041) % {  # @@
                            'real_show': heard_show}, card_title)
                else:
                    return build_alexa_response(
                        localize(32042) % {  # @@
                            'real_show': heard_show,
                            'num': num_of_unwatched}, card_title)

            else:
                return build_alexa_response(
                    localize(32043) % {  # @@
                        localize(32044): heard_show}, card_title)  # @@
        else:
            return build_alexa_response(localize(32045) % (heard_show), card_title)  # @@
    else:
        return build_alexa_response(localize(32046) % (heard_show), card_title)  # @@


# Handle the CurrentPlayItemInquiry intent.
def alexa_current_playitem_inquiry(slots):
    card_title = localize(32047)  # @@

    answer = localize(32048)  # @@
    answer_append = localize(32049)  # @@

    try:
        curitem = kodi_helpers.GetActivePlayItem()
    except:
        answer = localize(32050)  # @@
        answer_append = localize(32051)  # @@
    else:
        if curitem is not None:
            if curitem['type'] == 'episode':
                # is a tv show
                answer += localize(32052)  # @@
                answer_append = localize(32053)  # @@
                if curitem['showtitle']:
                    answer += ' %s,' % (curitem['showtitle'])
                    answer_append = ''
                if curitem['season']:
                    answer += localize(32054) % (  # @@
                        curitem['season'])
                    answer_append = ''
                if curitem['episode']:
                    answer += localize(32055) % (  # @@
                        curitem['episode'])
                    answer_append = ''
                if curitem['title']:
                    answer += ' %s' % (curitem['title'])
                    answer_append = ''
            elif curitem['type'] == 'song' or curitem['type'] == 'musicvideo':
                # is a song (music video or audio)
                answer += localize(32056)  # @@
                answer_append = localize(32053)  # @@
                if curitem['title']:
                    answer += ' %s,' % (curitem['title'])
                    answer_append = ''
                if curitem['artist']:
                    answer += ' by %s,' % (curitem['artist'][0])
                    answer_append = ''
                if curitem['album']:
                    answer += localize(32058) % (  # @@
                        curitem['album'])
                    answer_append = ''
            elif curitem['type'] == 'movie':
                # is a video
                answer += localize(32059)  # @@
                answer_append = localize(32053)  # @@
                if curitem['title']:
                    answer += ' %s' % (curitem['title'])
                    answer_append = ''

        return build_alexa_response('%s%s.' % (answer, answer_append), card_title)


# Handle the CurrentPlayItemTimeRemaining intent.
def alexa_current_playitem_time_remaining(slots):
    card_title = localize(32061)  # @@

    answer = 'Playback is stopped.'

    status = kodi_helpers.GetPlayerStatus()
    if status['state'] is not 'stop':
        minsleft = status['total_mins'] - status['time_mins']
        if minsleft == 0:
            answer = localize(32062)  # @@
        elif minsleft == 1:
            answer = localize(32063)  # @@
        elif minsleft > 1:
            answer = localize(32064) % (minsleft)  # @@
            if minsleft > 9:
                loctime = datetime.datetime.now()
                endtime = loctime + datetime.timedelta(minutes=minsleft)
                answer += localize(32065) % (  # @@
                    endtime.strftime('%I:%M'))
            else:
                answer += '.'

    return build_alexa_response(answer, card_title)


# Handle the PlayPause intent.
def alexa_play_pause(slots):
    xbmc.log('In play_pause', level=xbmc.LOGNOTICE)
    card_title = localize(32066)  # @@

    kodi_helpers.PlayPause()
    answer = localize(32067)  # @@
    return build_alexa_response(answer, card_title)


# Handle the Stop intent.
def alexa_stop(slots):
    card_title = localize(32068)  # @@

    kodi_helpers.Stop()
    answer = localize(32069)  # @@
    return build_alexa_response(answer, card_title)


# Handle the PlayerSeekSmallForward intent.
def alexa_player_seek_smallforward(slots):
    card_title = localize(32070)  # @@

    kodi_helpers.PlayerSeekSmallForward()
    answer = ""
    return build_alexa_response(answer, card_title)


# Handle the PlayerSeekSmallBackward intent.
def alexa_player_seek_smallbackward(slots):
    card_title = localize(32071)  # @@

    kodi_helpers.PlayerSeekSmallBackward()
    answer = ""
    return build_alexa_response(answer, card_title)


# Handle the PlayerSeekBigForward intent.
def alexa_player_seek_bigforward(slots):
    card_title = localize(32072)  # @@

    kodi_helpers.PlayerSeekBigForward()
    answer = ""
    return build_alexa_response(answer, card_title)


# Handle the PlayerSeekBigBackward intent.
def alexa_player_seek_bigbackward(slots):
    card_title = localize(32073)  # @@

    kodi_helpers.PlayerSeekBigBackward()
    answer = ""
    return build_alexa_response(answer, card_title)


# Handle the ListenToArtist intent.
# Shuffle all music by an artist.
def alexa_listen_artist(slots):
    heard_artist = str(slots['Artist']['value']).lower().translate(None, string.punctuation)

    card_title = localize(32074) % (heard_artist,)  # @@

    artists = kodi_helpers.GetMusicArtists()
    if 'result' in artists and 'artists' in artists['result']:
        artists_list = artists['result']['artists']
        located = kodi_helpers.matchHeard(heard_artist, artists_list, 'artist')

        if located:
            songs_result = kodi_helpers.GetArtistSongs(located['artistid'])
            songs = songs_result['result']['songs']

            songs_array = []

            for song in songs:
                songs_array.append(song['songid'])

            kodi_helpers.Stop()
            kodi_helpers.ClearAudioPlaylist()
            kodi_helpers.AddSongsToPlaylist(songs_array, True)
            kodi_helpers.StartAudioPlaylist()
            return build_alexa_response(localize(32075) % (heard_artist,), card_title)  # @@
        else:
            return build_alexa_response(localize(32076) % (heard_artist,), card_title)  # @@
    else:
        return build_alexa_response(localize(32077) % (heard_artist,), card_title)  # @@


# Handle the ListenToAlbum intent.
# Play whole album, or whole album by a specific artist.
def alexa_listen_album(slots):
    heard_album = str(slots['Album']['value']).lower().translate(None, string.punctuation)
    if 'value' in slots['Artist']:
        heard_artist = str(slots['Artist']['value']).lower().translate(None, string.punctuation)
        card_title = localize(32078) % (heard_album, heard_artist)  # @@
    else:
        card_title = localize(32079) % (heard_album,)  # @@

    if 'value' in slots['Artist']:
        artists = kodi_helpers.GetMusicArtists()
        if 'result' in artists and 'artists' in artists['result']:
            artists_list = artists['result']['artists']
            located = kodi_helpers.matchHeard(heard_artist, artists_list, 'artist')

            if located:
                albums = kodi_helpers.GetArtistAlbums(located['artistid'])
                if 'result' in albums and 'albums' in albums['result']:
                    albums_list = albums['result']['albums']
                    album_located = kodi_helpers.matchHeard(heard_album, albums_list, 'label')

                    if album_located:
                        album_result = album_located['albumid']
                        kodi_helpers.Stop()
                        kodi_helpers.ClearAudioPlaylist()
                        kodi_helpers.AddAlbumToPlaylist(album_result)
                        kodi_helpers.StartAudioPlaylist()
                    else:
                        return build_alexa_response(localize(32080) % (heard_album, heard_artist),  # @@
                                                    card_title)
                    return build_alexa_response(localize(32081) % (  # @@
                        heard_album, heard_artist), card_title)
                else:
                    return build_alexa_response(localize(32082) % (heard_album, heard_artist),  # @@
                                                card_title)

            else:
                return build_alexa_response(localize(32083) % (heard_album, heard_artist), card_title)  # @@
        else:
            return build_alexa_response(localize(32084) % (heard_artist,), card_title)  # @@
    else:
        albums = kodi_helpers.GetAlbums()
        if 'result' in albums and 'albums' in albums['result']:
            albums_list = albums['result']['albums']
            album_located = kodi_helpers.matchHeard(heard_album, albums_list, 'label')

            if album_located:
                album_result = album_located['albumid']
                kodi_helpers.Stop()
                kodi_helpers.ClearAudioPlaylist()
                kodi_helpers.AddAlbumToPlaylist(album_result)
                kodi_helpers.StartAudioPlaylist()
            else:
                return build_alexa_response(localize(32085) % (heard_album,), card_title)  # @@
            return build_alexa_response(localize(32086) % (heard_album,), card_title)  # @@
        else:
            return build_alexa_response(localize(32087) % (heard_album,), card_title)  # @@


# Handle the ListenToSong intent.
# Play a song, or song by a specific artist.
def alexa_listen_song(slots):
    heard_song = str(slots['Song']['value']).lower().translate(None, string.punctuation)
    heard_artist = 'UNKNOWN'
    if 'value' in slots['Artist']:
        heard_artist = str(slots['Artist']['value']).lower().translate(None, string.punctuation)
        card_title = localize(32088) % (heard_song, heard_artist)  # @@
    else:
        card_title = localize(32089) % (heard_song,)  # @@

    if 'value' in slots['Artist']:
        artists = kodi_helpers.GetMusicArtists()
        if 'result' in artists and 'artists' in artists['result']:
            artists_list = artists['result']['artists']
            located = kodi_helpers.matchHeard(heard_artist, artists_list, 'artist')

            if located:
                songs = kodi_helpers.GetArtistSongs(located['artistid'])
                if 'result' in songs and 'songs' in songs['result']:
                    songs_list = songs['result']['songs']
                    song_located = kodi_helpers.matchHeard(heard_song, songs_list, 'label')

                    if song_located:
                        song_result = song_located['songid']
                        kodi_helpers.Stop()
                        kodi_helpers.ClearAudioPlaylist()
                        kodi_helpers.AddSongToPlaylist(song_result)
                        kodi_helpers.StartAudioPlaylist()
                    else:
                        return build_alexa_response(localize(32090) % (heard_song, heard_artist),  # @@
                                                    card_title)
                    return build_alexa_response(localize(32091) % (heard_song, heard_artist), card_title)  # @@
                else:
                    return build_alexa_response(localize(32092) % (heard_song, heard_artist),  # @@
                                                card_title)

            else:
                return build_alexa_response(localize(32093) % (heard_song, heard_artist), card_title)  # @@
        else:
            return build_alexa_response(localize(32094) % (heard_artist,), card_title)  # @@
    else:
        songs = kodi_helpers.GetSongs()
        if 'result' in songs and 'songs' in songs['result']:
            songs_list = songs['result']['songs']
            song_located = kodi_helpers.matchHeard(heard_song, songs_list, 'label')

            if song_located:
                song_result = song_located['songid']
                kodi_helpers.Stop()
                kodi_helpers.ClearAudioPlaylist()
                kodi_helpers.AddSongToPlaylist(song_result)
                kodi_helpers.StartAudioPlaylist()
            else:
                return build_alexa_response(localize(32095) % (heard_song,), card_title)  # @@
            return build_alexa_response(localize(32096) % (heard_song,), card_title)  # @@
        else:
            return build_alexa_response(localize(32097) % (heard_song,), card_title)  # @@


# Handle the ListenToAlbumOrSong intent.
# Play whole album or song by a specific artist.
def alexa_listen_album_or_song(slots):
    heard_search = 'UNKNOWN'
    heard_artist = 'UNKNOWN'
    if 'value' in slots['Song']:
        heard_search = str(slots['Song']['value']).lower().translate(None, string.punctuation)
    elif 'value' in slots['Album']:
        heard_search = str(slots['Album']['value']).lower().translate(None, string.punctuation)
    if 'value' in slots['Artist']:
        heard_artist = str(slots['Artist']['value']).lower().translate(None, string.punctuation)
    card_title = 'Playing %s by %s' % (heard_search, heard_artist)

    artists = kodi_helpers.GetMusicArtists()
    if 'result' in artists and 'artists' in artists['result']:
        artists_list = artists['result']['artists']
        located = kodi_helpers.matchHeard(heard_artist, artists_list, 'artist')

        if located:
            albums = kodi_helpers.GetArtistAlbums(located['artistid'])
            if 'result' in albums and 'albums' in albums['result']:
                albums_list = albums['result']['albums']
                album_located = kodi_helpers.matchHeard(heard_search, albums_list, 'label')

                if album_located:
                    album_result = album_located['albumid']
                    kodi_helpers.Stop()
                    kodi_helpers.ClearAudioPlaylist()
                    kodi_helpers.AddAlbumToPlaylist(album_result)
                    kodi_helpers.StartAudioPlaylist()
                    return build_alexa_response(localize(32081) % (  # @@
                        heard_search, heard_artist), card_title)
                else:
                    songs = kodi_helpers.GetArtistSongs(located['artistid'])
                    if 'result' in songs and 'songs' in songs['result']:
                        songs_list = songs['result']['songs']
                        song_located = kodi_helpers.matchHeard(heard_search, songs_list, 'label')

                        if song_located:
                            song_result = song_located['songid']
                            kodi_helpers.Stop()
                            kodi_helpers.ClearAudioPlaylist()
                            kodi_helpers.AddSongToPlaylist(song_result)
                            kodi_helpers.StartAudioPlaylist()
                            return build_alexa_response(localize(32099) %  # @@
                                                        (heard_search, heard_artist),
                                                        card_title)
                        else:
                            return build_alexa_response(localize(32100) %  # @@
                                                        (heard_search, heard_artist),
                                                        card_title)
                    else:
                        return build_alexa_response(localize(32101) %  # @@
                                                    (heard_search, heard_artist),
                                                    card_title)
            else:
                return build_alexa_response(localize(32102) %  # @@
                                            (heard_search, heard_artist), card_title)

        else:
            return build_alexa_response(localize(32103) % (heard_search, heard_artist), card_title)  # @@
    else:
        return build_alexa_response(localize(32077) % (heard_artist,), card_title)  # @@


# Handle the ListenToAudioPlaylistRecent intent.
# Shuffle all recently added songs.
def alexa_listen_recently_added_songs(slots):
    card_title = localize(32105)  # @@

    songs_result = kodi_helpers.GetRecentlyAddedSongs()
    if songs_result:
        songs = songs_result['result']['songs']

        songs_array = []

        for song in songs:
            songs_array.append(song['songid'])

        kodi_helpers.Stop()
        kodi_helpers.ClearAudioPlaylist()
        kodi_helpers.AddSongsToPlaylist(songs_array, True)
        kodi_helpers.StartAudioPlaylist()
        return build_alexa_response(localize(32106), card_title)  # @@
    return build_alexa_response(localize(32107), card_title)  # @@


# Handle the ListenToAudioPlaylist intent.
def alexa_listen_audio_playlist(slots, shuffle=False):
    heard_search = str(slots['AudioPlaylist']['value']).lower().translate(None, string.punctuation)

    if shuffle:
        op = localize(32108)  # @@
    else:
        op = localize(32109)  # @@

    card_title = localize(32110) % op  # @@
    card_title += '"%s"' % heard_search

    playlist = kodi_helpers.FindAudioPlaylist(heard_search)
    if playlist:
        if shuffle:
            songs = kodi_helpers.GetPlaylistItems(playlist)['result']['files']

            songs_array = []

            for song in songs:
                songs_array.append(song['id'])

            kodi_helpers.Stop()
            kodi_helpers.ClearAudioPlaylist()
            kodi_helpers.AddSongsToPlaylist(songs_array, True)
            kodi_helpers.StartAudioPlaylist()
        else:
            kodi_helpers.Stop()
            kodi_helpers.StartAudioPlaylist(playlist)
        return build_alexa_response(localize(32111) % (op, heard_search), card_title)  # @@
    else:
        return build_alexa_response(localize(32112) % (heard_search,), card_title)  # @@


# Handle the ShuffleAudioPlaylist intent.
def alexa_shuffle_audio_playlist(slots):
    return alexa_listen_audio_playlist(slots, True)


# Handle the PartyMode intent.
def alexa_party_play(slots):
    card_title = localize(32113)  # @@
    songs = kodi_helpers.GetSongs()

    if 'result' in songs and 'songs' in songs['result']:
        songs_array = []

        for song in songs['result']['songs']:
            songs_array.append(song['songid'])

        kodi_helpers.Stop()
        kodi_helpers.ClearAudioPlaylist()
        kodi_helpers.AddSongsToPlaylist(songs_array, True)
        kodi_helpers.StartAudioPlaylist()
        return build_alexa_response(localize(32114), card_title)  # @@
    else:
        return build_alexa_response(localize(32115), card_title)  # @@


# Handle the StartOver intent.
def alexa_start_over(slots):
    card_title = localize(32116)  # @@

    kodi_helpers.PlayStartOver()
    answer = localize(32117)  # @@
    return build_alexa_response(answer, card_title)


# Handle the Skip intent.
def alexa_skip(slots):
    card_title = localize(32118)  # @@

    kodi_helpers.PlaySkip()
    answer = localize(32119)  # @@
    return build_alexa_response(answer, card_title)


# Handle the Prev intent.
def alexa_prev(slots):
    card_title = localize(32120)  # @@

    kodi_helpers.PlayPrev()
    answer = localize(32121)  # @@
    return build_alexa_response(answer, card_title)


# Handle the Fullscreen intent.
def alexa_fullscreen(slots):
    card_title = localize(32122)  # @@

    kodi_helpers.ToggleFullscreen()
    answer = localize(32123)  # @@
    return build_alexa_response(answer, card_title)


# Handle the Mute intent.
def alexa_mute(slots):
    card_title = localize(32124)  # @@

    kodi_helpers.ToggleMute()
    answer = localize(32125)  # @@
    return build_alexa_response(answer, card_title)


# Handle the VolumeUp intent.
def alexa_volume_up(slots):
    card_title = localize(32126)  # @@

    vol = kodi_helpers.VolumeUp()['result']
    answer = localize(32127) % (vol,)  # @@
    return build_alexa_response(answer, card_title)


# Handle the VolumeDown intent.
def alexa_volume_down(slots):
    card_title = localize(32128)  # @@

    vol = kodi_helpers.VolumeDown()['result']
    answer = localize(32127) % (vol,)  # @@
    return build_alexa_response(answer, card_title)


# Handle the VolumeSet intent.
def alexa_volume_set(slots):
    card_title = localize(32130)  # @@

    try:
        vol = kodi_helpers.VolumeSet(int(slots['Volume']['value']), False)['result']
        answer = localize(32127) % (vol,)  # @@
    except ValueError:
        answer = localize(32132)  # @@
    return build_alexa_response(answer, card_title)


# Handle the VolumeSetPct intent.
def alexa_volume_set_pct(slots):
    card_title = localize(32130)  # @@

    try:
        vol = kodi_helpers.VolumeSet(int(slots['Volume']['value']))['result']
        answer = localize(32127) % (vol,)  # @@
    except ValueError:
        answer = localize(32135)  # @@
    return build_alexa_response(answer, card_title)


# Handle the SubtitlesOn intent.
def alexa_subtitles_on(slots):
    card_title = localize(32136)  # @@

    kodi_helpers.SubtitlesOn()
    answer = kodi_helpers.GetCurrentSubtitles()
    return build_alexa_response(answer, card_title)


# Handle the SubtitlesOff intent.
def alexa_subtitles_off(slots):
    card_title = localize(32137)  # @@

    kodi_helpers.SubtitlesOff()
    answer = kodi_helpers.GetCurrentSubtitles()
    return build_alexa_response(answer, card_title)


# Handle the SubtitlesNext intent.
def alexa_subtitles_next(slots):
    card_title = localize(32138)  # @@

    kodi_helpers.SubtitlesNext()
    answer = kodi_helpers.GetCurrentSubtitles()
    return build_alexa_response(answer, card_title)


# Handle the AudioStreamNext intent.
def alexa_audiostream_next(slots):
    card_title = localize(32139)  # @@

    kodi_helpers.AudioStreamNext()
    answer = kodi_helpers.GetCurrentAudioStream()
    return build_alexa_response(answer, card_title)


# Handle the Menu intent.
def alexa_context_menu(slots):
    card_title = localize(32140)  # @@

    kodi_helpers.Menu()
    answer = localize(32141)  # @@
    return build_alexa_response(answer, None, end_session=False)


# Handle the Home intent.
def alexa_go_home(slots):
    card_title = localize(32142)  # @@

    kodi_helpers.Home()
    answer = localize(32143)  # @@
    return build_alexa_response(answer, None, end_session=False)


# Handle the Select intent.
def alexa_select(slots):
    card_title = localize(32144)  # @@

    kodi_helpers.Select()
    answer = localize(32145)  # @@
    return build_alexa_response(answer, None, end_session=False)


# Handle the PageUp intent.
def alexa_pageup(slots):
    card_title = localize(32146)  # @@

    kodi_helpers.PageUp()
    answer = localize(32147)  # @@
    return build_alexa_response(answer, None, end_session=False)


# Handle the PageDown intent.
def alexa_pagedown(slots):
    card_title = localize(32148)  # @@

    kodi_helpers.PageDown()
    answer = localize(32149)  # @@
    return build_alexa_response(answer, None, end_session=False)


# Handle the Left intent.
def alexa_left(slots):
    card_title = localize(32150)  # @@

    kodi_helpers.Left()
    answer = localize(32151)  # @@
    return build_alexa_response(answer, None, end_session=False)


# Handle the Right intent.
def alexa_right(slots):
    card_title = localize(32152)  # @@

    kodi_helpers.Right()
    answer = localize(32153)  # @@
    return build_alexa_response(answer, None, end_session=False)


# Handle the Up intent.
def alexa_up(slots):
    card_title = localize(32154)  # @@

    kodi_helpers.Up()
    answer = localize(32155)  # @@
    return build_alexa_response(answer, None, end_session=False)


# Handle the Down intent.
def alexa_down(slots):
    card_title = localize(32156)  # @@

    kodi_helpers.Down()
    answer = localize(32157)  # @@
    return build_alexa_response(answer, None, end_session=False)


# Handle the Back intent.
def alexa_back(slots):
    card_title = localize(32158)  # @@

    kodi_helpers.Back()
    answer = localize(32159)  # @@
    return build_alexa_response(answer, None, end_session=False)


# Handle the Hibernate intent.
def alexa_hibernate(slots):
    card_title = localize(32160)  # @@

    kodi_helpers.SystemHibernate()
    answer = localize(32161)  # @@
    return build_alexa_response(answer, card_title)


# Handle the Reboot intent.
def alexa_reboot(slots):
    card_title = localize(32162)  # @@

    kodi_helpers.SystemReboot()
    answer = localize(32163)  # @@
    return build_alexa_response(answer, card_title)


# Handle the Shutdown intent.
def alexa_shutdown(slots):
    card_title = localize(32164)  # @@

    kodi_helpers.SystemShutdown()
    answer = localize(32165)  # @@
    return build_alexa_response(answer, card_title)


# Handle the Suspend intent.
def alexa_suspend(slots):
    card_title = localize(32166)  # @@

    kodi_helpers.SystemSuspend()
    answer = localize(32167)  # @@
    return build_alexa_response(answer, card_title)


# Handle the EjectMedia intent.
def alexa_ejectmedia(slots):
    card_title = localize(32168)  # @@

    kodi_helpers.SystemEjectMedia()
    answer = localize(32169)  # @@
    return build_alexa_response(answer, card_title)


# Handle the CleanVideo intent.
def alexa_clean_video(slots):
    card_title = localize(32170)  # @@

    # Use threading to solve the call from returing too late
    c = Process(target=kodi_helpers.CleanVideo)
    c.daemon = True
    c.start()

    time.sleep(2)

    answer = localize(32171)  # @@
    return build_alexa_response(answer, card_title)


# Handle the UpdateVideo intent.
def alexa_update_video(slots):
    card_title = localize(32172)  # @@

    kodi_helpers.UpdateVideo()

    answer = localize(32173)  # @@
    return build_alexa_response(answer, card_title)


# Handle the CleanAudio intent.
def alexa_clean_audio(slots):
    card_title = localize(32174)  # @@

    # Use threading to solve the call from returing too late
    c = Process(target=kodi_helpers.CleanMusic)
    c.daemon = True
    c.start()

    time.sleep(2)

    answer = localize(32175)  # @@
    return build_alexa_response(answer, card_title)


# Handle the UpdateAudio intent.
def alexa_update_audio(slots):
    card_title = localize(32176)  # @@

    kodi_helpers.UpdateMusic()

    answer = localize(32177)  # @@
    return build_alexa_response(answer, card_title)


# Handle the AddonExecute intent.
def alexa_addon_execute(slots):
    heard_addon = str(slots['Addon']['value']).lower().translate(None, string.punctuation)

    card_title = localize(32178) % (heard_addon,)  # @@

    for content in ['video', 'audio', 'image', 'executable']:
        addons = kodi_helpers.GetAddons(content)
        if 'result' in addons and 'addons' in addons['result']:
            addons_array = addons['result']['addons']

            located = kodi_helpers.matchHeard(heard_addon, addons_array, lookingFor='name')

            if located:
                kodi_helpers.Home()
                kodi_helpers.AddonExecute(located['addonid'])

                return build_alexa_response(localize(32179) %   # @@
                                            (located['name']), card_title)
        else:
            return build_alexa_response(localize(32180) % (heard_addon,), card_title)  # @@

    return build_alexa_response(localize(32181) % (heard_addon,), card_title)  # @@


# Handle the AddonGlobalSearch intent.
def alexa_addon_globalsearch(slots):
    card_title = localize(32182)  # @@
    heard_search = ''

    if 'value' in slots['Movie']:
        heard_search = str(slots['Movie']['value']).lower().translate(None, string.punctuation)
    elif 'value' in slots['Show']:
        heard_search = str(slots['Show']['value']).lower().translate(None, string.punctuation)
    elif 'value' in slots['Artist']:
        heard_search = str(slots['Artist']['value']).lower().translate(None, string.punctuation)
    elif 'value' in slots['Album']:
        heard_search = str(slots['Album']['value']).lower().translate(None, string.punctuation)
    elif 'value' in slots['Song']:
        heard_search = str(slots['Song']['value']).lower().translate(None, string.punctuation)

    if (len(heard_search) > 0):
        answer = localize(32183) % (heard_search,)  # @@

        kodi_helpers.Home()
        kodi_helpers.AddonGlobalSearch(heard_search)

        return build_alexa_response(answer, card_title)
    else:
        return build_alexa_response(localize(32184), card_title)  # @@


# Handle the WatchRandomMovie intent.
def alexa_watch_random_movie(slots):
    genre_located = None
    # If a genre has been specified, match the genre for use in selecting a random film
    if 'value' in slots['Genre']:
        heard_genre = str(slots['Genre']['value']).lower().translate(None, string.punctuation)
        card_title = localize(32185) % (heard_genre,)  # @@
        genres = kodi_helpers.GetMovieGenres()
        if 'result' in genres and 'genres' in genres['result']:
            genres_list = genres['result']['genres']
            genre_located = kodi_helpers.matchHeard(heard_genre, genres_list, 'label')
    else:
        card_title = localize(32186)  # @@

    # Select from specified genre if one was matched
    if genre_located:
        movies_array = kodi_helpers.GetUnwatchedMoviesByGenre(genre_located['label'])
    else:
        movies_array = kodi_helpers.GetUnwatchedMovies()
    if not len(movies_array):
        # Fall back to all movies if no unwatched available
        if genre_located:
            movies = kodi_helpers.GetMoviesByGenre(genre_located['label'])
        else:
            movies = kodi_helpers.GetMovies()
        if 'result' in movies and 'movies' in movies['result']:
            movies_array = movies['result']['movies']

    if len(movies_array):
        random_movie = random.choice(movies_array)

        kodi_helpers.PlayMovie(random_movie['movieid'], False)
        if genre_located:
            return build_alexa_response(localize(32187) %   # @@
                                        (genre_located['label'], random_movie['label']),
                                        card_title)
        else:
            return build_alexa_response(localize(32188) % (  # @@
                random_movie['label']), card_title)
    else:
        return build_alexa_response(localize(32189), card_title)  # @@


# Handle the WatchMovie intent.
def alexa_watch_movie(slots):
    heard_movie = str(slots['Movie']['value']).lower().translate(None, string.punctuation)

    card_title = localize(32190) % (heard_movie,)  # @@

    movies = kodi_helpers.GetMovies()
    if 'result' in movies and 'movies' in movies['result']:
        movies_array = movies['result']['movies']

        located = kodi_helpers.matchHeard(heard_movie, movies_array)

        if located:
            if kodi_helpers.GetMovieDetails(located['movieid'])['resume']['position'] > 0:
                action = localize(32191)  # @@
            else:
                action = localize(32192)  # @@

            kodi_helpers.PlayMovie(located['movieid'])

            return build_alexa_response('%s %s' % (action, heard_movie), card_title)
        else:
            return build_alexa_response(localize(32193) % (heard_movie,), card_title)  # @@
    else:
        return build_alexa_response(localize(32194) % (heard_movie,), card_title)  # @@


# Handle the WatchRandomEpisode intent.
def alexa_watch_random_episode(slots):
    heard_show = str(slots['Show']['value']).lower().translate(None, string.punctuation)

    card_title = localize(32195) % (heard_show,)  # @@

    shows = kodi_helpers.GetTvShows()
    if 'result' in shows and 'tvshows' in shows['result']:
        shows_array = shows['result']['tvshows']

        located = kodi_helpers.matchHeard(heard_show, shows_array)

        if located:
            episodes_result = kodi_helpers.GetUnwatchedEpisodesFromShow(located['tvshowid'])

            if not 'episodes' in episodes_result['result']:
                # Fall back to all episodes if no unwatched available
                episodes_result = kodi_helpers.GetEpisodesFromShow(located['tvshowid'])

            episodes_array = []

            for episode in episodes_result['result']['episodes']:
                episodes_array.append(episode['episodeid'])

            episode_id = random.choice(episodes_array)
            episode_details = kodi_helpers.GetEpisodeDetails(episode_id)

            kodi_helpers.PlayEpisode(episode_id, False)

            return build_alexa_response(localize(32196) % (  # @@
                episode_details['season'], episode_details['episode'], heard_show), card_title)
        else:
            return build_alexa_response(localize(32197) % (heard_show,), card_title)  # @@
    else:
        return build_alexa_response(localize(32198), card_title)  # @@


# Handle the WatchEpisode intent.
def alexa_watch_episode(slots):
    heard_show = str(slots['Show']['value']).lower().translate(None, string.punctuation)

    card_title = localize(32199) % (heard_show,)  # @@

    shows = kodi_helpers.GetTvShows()
    if 'result' in shows and 'tvshows' in shows['result']:
        shows_array = shows['result']['tvshows']

        heard_season = slots['Season']['value']
        heard_episode = slots['Episode']['value']

        located = kodi_helpers.matchHeard(heard_show, shows_array)

        if located:
            episode_id = kodi_helpers.GetSpecificEpisode(located['tvshowid'], heard_season, heard_episode)

            if episode_id:
                if kodi_helpers.GetEpisodeDetails(episode_id)['resume']['position'] > 0:
                    action = localize(32191)  # @@
                else:
                    action = localize(32192)  # @@

                kodi_helpers.PlayEpisode(episode_id)

                return build_alexa_response(
                    localize(32202) %  # @@
                    (action, heard_season, heard_episode, heard_show), card_title)

            else:
                return build_alexa_response(
                    localize(32203) %  # @@
                    (heard_season, heard_episode, heard_show), card_title)
        else:
            return build_alexa_response(localize(32204) %  # @@
                                        (heard_show,), card_title)
    else:
        return build_alexa_response(localize(32198), card_title)  # @@


# Handle the WatchNextEpisode intent.
def alexa_watch_next_episode(slots):
    heard_show = str(slots['Show']['value']).lower().translate(None, string.punctuation)

    card_title = localize(32206) % (heard_show,)  # @@

    shows = kodi_helpers.GetTvShows()
    if 'result' in shows and 'tvshows' in shows['result']:
        shows_array = shows['result']['tvshows']

        located = kodi_helpers.matchHeard(heard_show, shows_array)

        if located:
            next_episode_id = kodi_helpers.GetNextUnwatchedEpisode(located['tvshowid'])

            if next_episode_id:
                episode_details = kodi_helpers.GetEpisodeDetails(next_episode_id)

                if episode_details['resume']['position'] > 0:
                    action = localize(32191)  # @@
                else:
                    action = localize(32192)  # @@

                kodi_helpers.PlayEpisode(next_episode_id)

                return build_alexa_response(localize(32209) % (  # @@
                    action, episode_details['season'], episode_details['episode'], heard_show), card_title)
            else:
                return build_alexa_response(localize(32210) % (heard_show,), card_title)  # @@
        else:
            return build_alexa_response(localize(32197) % (heard_show,), card_title)  # @@
    else:
        return build_alexa_response(localize(32212) % (heard_show,), card_title)  # @@


# Handle the WatchNewestEpisode intent.
def alexa_watch_newest_episode(slots):
    heard_show = str(slots['Show']['value']).lower().translate(None, string.punctuation)

    card_title = localize(32213) % (heard_show)  # @@

    shows = kodi_helpers.GetTvShows()
    if 'result' in shows and 'tvshows' in shows['result']:
        shows_array = shows['result']['tvshows']

        located = kodi_helpers.matchHeard(heard_show, shows_array)

        if located:
            episode_id = kodi_helpers.GetNewestEpisodeFromShow(located['tvshowid'])

            if episode_id:
                episode_details = kodi_helpers.GetEpisodeDetails(episode_id)

                if episode_details['resume']['position'] > 0:
                    action = localize(32191)  # @@
                else:
                    action = localize(32192)  # @@

                kodi_helpers.PlayEpisode(episode_id)

                return build_alexa_response(localize(32209) % (  # @@
                    action, episode_details['season'], episode_details['episode'], heard_show), card_title)
            else:
                return build_alexa_response(localize(32210) % (heard_show,), card_title)  # @@
        else:
            return build_alexa_response(localize(32218) % (heard_show,), card_title)  # @@
    else:
        return build_alexa_response(localize(32115), card_title)  # @@


# Handle the WatchLastShow intent.
def alexa_watch_last_show(slots):
    card_title = localize(32220)  # @@

    last_show_obj = kodi_helpers.GetLastWatchedShow()

    try:
        last_show_id = last_show_obj['result']['episodes'][0]['tvshowid']
        next_episode_id = kodi_helpers.GetNextUnwatchedEpisode(last_show_id)

        if next_episode_id:
            episode_details = kodi_helpers.GetEpisodeDetails(next_episode_id)

            if episode_details['resume']['position'] > 0:
                action = localize(32191)  # @@
            else:
                action = localize(32192)  # @@

            kodi_helpers.PlayEpisode(next_episode_id)

            return build_alexa_response(localize(32223) % (  # @@
                action, episode_details['season'], episode_details['episode'],
                last_show_obj['result']['episodes'][0]['showtitle']), card_title)
        else:
            return build_alexa_response(localize(32224) %  # @@
                                        last_show_obj['result']['episodes'][0]['showtitle'],
                                        card_title)
    except:
        return build_alexa_response(localize(32115), card_title)  # @@


# Handle the WatchVideoPlaylist intent.
def alexa_watch_video_playlist(slots, shuffle=False):
    heard_search = str(slots['VideoPlaylist']['value']).lower().translate(None, string.punctuation)

    if shuffle:
        op = localize(32108)  # @@
    else:
        op = localize(32109)  # @@

    card_title = localize(32228) % op  # @@
    card_title += '"%s"' % heard_search

    playlist = kodi_helpers.FindVideoPlaylist(heard_search)
    if playlist:
        if shuffle:
            videos = kodi_helpers.GetPlaylistItems(playlist)['result']['files']

            videos_array = []

            for video in videos:
                videos_array.append(video['file'])

            kodi_helpers.Stop()
            kodi_helpers.ClearVideoPlaylist()
            kodi_helpers.AddVideosToPlaylist(videos_array, True)
            kodi_helpers.StartVideoPlaylist()
        else:
            kodi_helpers.Stop()
            kodi_helpers.StartVideoPlaylist(playlist)
        return build_alexa_response(localize(32111) % (op, heard_search), card_title)  # @@
    else:
        return build_alexa_response(localize(32112) % (heard_search,), card_title)  # @@


# Handle the ShuffleVideoPlaylist intent.
def alexa_shuffle_video_playlist(slots):
    return alexa_watch_video_playlist(slots, True)


# Handle the ShufflePlaylist intent.
def alexa_shuffle_playlist(slots):
    heard_search = ''
    if 'value' in slots['VideoPlaylist']:
        heard_search = str(slots['VideoPlaylist']['value']).lower().translate(None, string.punctuation)
    elif 'value' in slots['AudioPlaylist']:
        heard_search = str(slots['AudioPlaylist']['value']).lower().translate(None, string.punctuation)

    card_title = localize(32231)  # @@
    card_title += '"%s"' % heard_search

    if len(heard_search) > 0:
        playlist = kodi_helpers.FindVideoPlaylist(heard_search)
        if playlist:
            videos = kodi_helpers.GetPlaylistItems(playlist)['result']['files']

            videos_array = []

            for video in videos:
                videos_array.append(video['file'])

            kodi_helpers.Stop()
            kodi_helpers.ClearVideoPlaylist()
            kodi_helpers.AddVideosToPlaylist(videos_array, True)
            kodi_helpers.StartVideoPlaylist()
            return build_alexa_response(localize(32232) % (heard_search,), card_title)  # @@
        else:
            playlist = kodi_helpers.FindAudioPlaylist(heard_search)
            if playlist:
                songs = kodi_helpers.GetPlaylistItems(playlist)['result']['files']

                songs_array = []

                for song in songs:
                    songs_array.append(song['id'])

                kodi_helpers.Stop()
                kodi_helpers.ClearAudioPlaylist()
                kodi_helpers.AddSongsToPlaylist(songs_array, True)
                kodi_helpers.StartAudioPlaylist()
                return build_alexa_response(localize(32233) % (heard_search,), card_title)  # @@

        return build_alexa_response(localize(32112) % (heard_search,), card_title)  # @@
    else:
        return build_alexa_response(localize(32112) % (heard_search,), card_title)  # @@


def suggest_alternate_activity(chance=0.25):
    if random.random() < chance:
        comments = [
            localize(32236),  # @@
            localize(32237),  # @@
            localize(32238),  # @@
            localize(32239),  # @@
        ]
        return random.choice(comments)
    else:
        return ''


# Handle the WhatNewAlbums intent.
def alexa_what_new_albums(slots):
    card_title = localize(32240)  # @@

    # Get the list of recently added albums from Kodi
    new_albums = kodi_helpers.GetRecentlyAddedAlbums()['result']['albums']

    new_album_names = list(set([sanitize_name(localize(32241) %  # @@
                                              (x['label'], x['artist'][0])) for x in new_albums]))
    num_albums = len(new_album_names)

    xbmc.executebuiltin('ActivateWindow(Music,RecentlyAddedAlbums)')

    if num_albums == 0:
        # There's been nothing added to Kodi recently
        answers = [
            localize(32242),  # @@
            localize(32243),  # @@
        ]
        answer = random.choice(answers)
        answer += suggest_alternate_activity()
    else:
        random.shuffle(new_album_names)
        limited_new_album_names = new_album_names[0:5]
        album_list = limited_new_album_names[0]
        for one_album in limited_new_album_names[1:-1]:
            album_list += ", " + one_album
        if num_albums > 5:
            album_list += ", " + limited_new_album_names[-1] +\
                          localize(32244)  # @@
        else:
            album_list += localize(32245) + limited_new_album_names[-1]  # @@
        answer = localize(32246) % {  # @@
            "album_list": album_list}
    return build_alexa_response(answer, card_title)


# Handle the WhatNewMovies intent.
def alexa_what_new_movies(slots):
    genre_located = None
    # If a genre has been specified, match the genre for use in selecting random films
    if 'value' in slots['Genre']:
        heard_genre = str(slots['Genre']['value']).lower().translate(None, string.punctuation)
        card_title = localize(32247) % (heard_genre)  # @@
        genres = kodi_helpers.GetMovieGenres()
        if 'result' in genres and 'genres' in genres['result']:
            genres_list = genres['result']['genres']
            genre_located = kodi_helpers.matchHeard(heard_genre, genres_list, 'label')
    else:
        card_title = localize(32248)  # @@

    # Select from specified genre if one was matched
    if genre_located:
        new_movies = kodi_helpers.GetUnwatchedMoviesByGenre(genre_located['label'])
    else:
        new_movies = kodi_helpers.GetUnwatchedMovies()

    new_movie_names = list(set([sanitize_name(x['title']) for x in new_movies]))
    num_movies = len(new_movie_names)

    xbmc.executebuiltin('ActivateWindow(Videos,RecentlyAddedMovies)')

    if num_movies == 0:
        # There's been nothing added to Kodi recently
        answers = [
            localize(32249),  # @@
            localize(32250),  # @@
        ]
        answer = random.choice(answers)
        answer += suggest_alternate_activity()
    else:
        random.shuffle(new_movie_names)
        limited_new_movie_names = new_movie_names[0:5]
        movie_list = limited_new_movie_names[0]
        for one_movie in limited_new_movie_names[1:-1]:
            movie_list += ", " + one_movie
        if num_movies > 5:
            movie_list += ", " + limited_new_movie_names[-1] +\
                          localize(32244)  # @@
        else:
            movie_list += localize(32252) + limited_new_movie_names[-1]  # @@
        answer = localize(32253) % {  # @@
            "movie_list": movie_list}
    return build_alexa_response(answer, card_title)


# Handle the WhatNewShows intent.
def alexa_what_new_episodes(slots):
    card_title = localize(32254)  # @@

    # Lists the shows that have had new episodes added to Kodi in the last 5 days

    # Get the list of unwatched EPISODES from Kodi
    new_episodes = kodi_helpers.GetUnwatchedEpisodes()

    # Find out how many EPISODES were recently added and get the names of the SHOWS
    new_show_names = list(set([sanitize_name(x['show']) for x in new_episodes]))
    num_shows = len(new_show_names)

    xbmc.executebuiltin('ActivateWindow(Videos,RecentlyAddedEpisodes)')

    if num_shows == 0:
        # There's been nothing added to Kodi recently
        answers = [
            localize(32255),  # @@
            localize(32256),  # @@
        ]
        answer = random.choice(answers)
        answer += suggest_alternate_activity()
    elif len(new_show_names) == 1:
        # There's only one new show, so provide information about the number of episodes, too.
        count = len(new_episodes)
        if count == 1:
            answers = [
                localize(32257) %  # @@
                {'show': new_show_names[0]},
                localize(32258) %  # @@
                {'show': new_show_names[0]},
            ]
        elif count == 2:
            answers = [
                localize(32259) %  # @@
                {'show': new_show_names[0]},
                localize(32260) %  # @@
                {'show': new_show_names[0]},
            ]
        elif count >= 5:
            answers = [
                localize(32261) %  # @@
                {'show': new_show_names[0]},
                localize(32262) %  # @@
                {"count": count, "show": new_show_names[0]},
            ]
        else:
            answers = [
                localize(32263) %  # @@
                {'show': new_show_names[0]},
                localize(32262) %  # @@
                {"count": count, "show": new_show_names[0]},
            ]
        answer = random.choice(answers)
    else:
        # More than one new show has new episodes ready
        random.shuffle(new_show_names)
        limited_new_show_names = new_show_names[0:5]
        show_list = limited_new_show_names[0]
        for one_show in limited_new_show_names[1:-1]:
            show_list += "; " + one_show
        if num_shows > 5:
            show_list += "; " + limited_new_show_names[-1] + \
                         localize(32265)  # @@
        else:
            show_list += localize(32266) + limited_new_show_names[-1]  # @@
        answer = localize(32267) % {  # @@
            "show_list": show_list}
    return build_alexa_response(answer, card_title)


# Handle the WhatAlbums intent.
def alexa_what_albums(slots):
    heard_artist = str(slots['Artist']['value']).lower().translate(None, string.punctuation)

    card_title = localize(32268) % (heard_artist,)  # @@

    artists = kodi_helpers.GetMusicArtists()
    if 'result' in artists and 'artists' in artists['result']:
        artists_list = artists['result']['artists']
        located = kodi_helpers.matchHeard(heard_artist, artists_list, 'artist')

        if located:
            albums_result = kodi_helpers.GetArtistAlbums(located['artistid'])
            albums = albums_result['result']['albums']
            num_albums = len(albums)

            if num_albums > 0:
                really_albums = list(set([sanitize_name(x['label']) for x in albums]))
                album_list = really_albums[0]
                if num_albums > 1:
                    for one_album in really_albums[1:-1]:
                        album_list += ", " + one_album
                    album_list += localize(32269) + really_albums[-1]  # @@
                return build_alexa_response(localize(32270) % (album_list,), card_title)  # @@
            else:
                return build_alexa_response(localize(32271) % (heard_artist,), card_title)  # @@
        else:
            return build_alexa_response(localize(32076) % (heard_artist,), card_title)  # @@
    else:
        return build_alexa_response(localize(32077) % (heard_artist,), card_title)  # @@


def general_notification(slots):
    if 'NotificationText' in slots:
        text = slots['NotificationText']['value']
    else:
        text = ""
    return build_alexa_response(text)


# This maps the Intent names to the functions that provide the corresponding Alexa response.
INTENTS = dict([
    ['NewShowInquiry', alexa_new_show_inquiry],
    ['CurrentPlayItemInquiry', alexa_current_playitem_inquiry],
    ['CurrentPlayItemTimeRemaining', alexa_current_playitem_time_remaining],
    ['WhatNewAlbums', alexa_what_new_albums],
    ['WhatNewMovies', alexa_what_new_movies],
    ['WhatNewShows', alexa_what_new_episodes],
    ['WhatAlbums', alexa_what_albums],
    ['ListenToArtist', alexa_listen_artist],
    ['ListenToAlbum', alexa_listen_album],
    ['ListenToSong', alexa_listen_song],
    ['ListenToAlbumOrSong', alexa_listen_album_or_song],
    ['ListenToAudioPlaylist', alexa_listen_audio_playlist],
    ['ListenToAudioPlaylistRecent', alexa_listen_recently_added_songs],
    ['WatchRandomMovie', alexa_watch_random_movie],
    ['WatchRandomEpisode', alexa_watch_random_episode],
    ['WatchMovie', alexa_watch_movie],
    ['WatchEpisode', alexa_watch_episode],
    ['WatchNextEpisode', alexa_watch_next_episode],
    ['WatchLatestEpisode', alexa_watch_newest_episode],
    ['WatchLastShow', alexa_watch_last_show],
    ['WatchVideoPlaylist', alexa_watch_video_playlist],
    ['ShuffleAudioPlaylist', alexa_shuffle_audio_playlist],
    ['ShuffleVideoPlaylist', alexa_shuffle_video_playlist],
    ['ShufflePlaylist', alexa_shuffle_playlist],
    ['PlayPause', alexa_play_pause],
    ['Stop', alexa_stop],
    ['Skip', alexa_skip],
    ['Prev', alexa_prev],
    ['StartOver', alexa_start_over],
    ['PlayerSeekSmallForward', alexa_player_seek_smallforward],
    ['PlayerSeekBigForward', alexa_player_seek_bigforward],
    ['PlayerSeekSmallBackward', alexa_player_seek_smallbackward],
    ['PlayerSeekBigBackward', alexa_player_seek_bigbackward],
    ['Home', alexa_go_home],
    ['Back', alexa_back],
    ['Up', alexa_up],
    ['Down', alexa_down],
    ['Right', alexa_right],
    ['Left', alexa_left],
    ['Select', alexa_select],
    ['Menu', alexa_context_menu],
    ['PageUp', alexa_pageup],
    ['PageDown', alexa_pagedown],
    ['Fullscreen', alexa_fullscreen],
    ['Mute', alexa_mute],
    ['VolumeUp', alexa_volume_up],
    ['VolumeDown', alexa_volume_down],
    ['VolumeSet', alexa_volume_set],
    ['VolumeSetPct', alexa_volume_set_pct],
    ['SubtitlesOn', alexa_subtitles_on],
    ['SubtitlesOff', alexa_subtitles_off],
    ['SubtitlesNext', alexa_subtitles_next],
    ['AudioStreamNext', alexa_audiostream_next],
    ['CleanVideo', alexa_clean_video],
    ['UpdateVideo', alexa_update_video],
    ['CleanAudio', alexa_clean_audio],
    ['UpdateAudio', alexa_update_audio],
    ['PartyMode', alexa_party_play],
    ['AddonExecute', alexa_addon_execute],
    ['AddonGlobalSearch', alexa_addon_globalsearch],
    ['Hibernate', alexa_hibernate],
    ['Reboot', alexa_reboot],
    ['Shutdown', alexa_shutdown],
    ['Suspend', alexa_suspend],
    ['EjectMedia', alexa_ejectmedia],
    ['GeneralNotification', general_notification]
])


def dispatch_handler(intent_req):
    try:
        xbmc.log('In dispatch_handler', level=xbmc.LOGNOTICE)
        handler = INTENTS[intent_req['intent']['name']]
        resp = handler(intent_req['intent'].get('slots', {}))
        output = resp['response'].get('outputSpeech', {'text': ''})['text']
        xbmc.log('Response: %s' % output, level=xbmc.LOGNOTICE)
        icon = xbmc.translatePath(
            xbmcaddon.Addon().getAddonInfo('path') + '/resources/icon.png').decode('utf-8')
        xbmc.executebuiltin("Notification(Miracle, %s, 3000, %s)" % (output.replace(',', ';'), icon))
    except Exception as e:
        xbmc.log('Can\'t handle intent %s: %s' % (intent_req['intent']['name'], e), level=xbmc.LOGERROR)
