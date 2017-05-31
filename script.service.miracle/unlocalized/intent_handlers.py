#!/usr/bin/python
import os

"""
The MIT License (MIT)

Copyright (c) 2015 ylazarev && pineur

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

    card_title = "Looking for new episodes of %s" % (heard_show,)  # @@


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
                        "There is one unseen episode of %(real_show)s." % {  # @@
                            'real_show': heard_show}, card_title)
                else:
                    return build_alexa_response(
                        "There are %(num)d unseen episodes of %(real_show)s." % {  # @@
                            'real_show': heard_show,
                            'num': num_of_unwatched}, card_title)

            else:
                return build_alexa_response(
                    "There are no unseen episodes of %(real_show)s." % {  # @@
                        'real_show': heard_show}, card_title)  # @@
        else:
            return build_alexa_response('Can\'t find %s' % (heard_show), card_title)  # @@
    else:
        return build_alexa_response('Can\'t find %s' % (heard_show), card_title)  # @@


# Handle the CurrentPlayItemInquiry intent.
def alexa_current_playitem_inquiry(slots):
    card_title = "Currently playing item"  # @@

    answer = 'The current'  # @@
    answer_append = 'ly playing item is unknown'  # @@

    try:
        curitem = kodi_helpers.GetActivePlayItem()
    except:
        answer = 'There is nothing current'  # @@
        answer_append = 'ly playing'  # @@
    else:
        if curitem is not None:
            if curitem['type'] == 'episode':
                # is a tv show
                answer += ' TV show is'  # @@
                answer_append = ' unknown'  # @@
                if curitem['showtitle']:
                    answer += ' %s,' % (curitem['showtitle'])
                    answer_append = ''
                if curitem['season']:
                    answer += ' season %s,' % (  # @@
                        curitem['season'])
                    answer_append = ''
                if curitem['episode']:
                    answer += ' episode %s,' % (  # @@
                        curitem['episode'])
                    answer_append = ''
                if curitem['title']:
                    answer += ' %s' % (curitem['title'])
                    answer_append = ''
            elif curitem['type'] == 'song' or curitem['type'] == 'musicvideo':
                # is a song (music video or audio)
                answer += ' song is'  # @@
                answer_append = ' unknown'  # @@
                if curitem['title']:
                    answer += ' %s,' % (curitem['title'])
                    answer_append = ''
                if curitem['artist']:
                    answer += ' by %s,' % (curitem['artist'][0])
                    answer_append = ''
                if curitem['album']:
                    answer += ' on the album %s' % (  # @@
                        curitem['album'])
                    answer_append = ''
            elif curitem['type'] == 'movie':
                # is a video
                answer += ' movie is'  # @@
                answer_append = ' unknown'  # @@
                if curitem['title']:
                    answer += ' %s' % (curitem['title'])
                    answer_append = ''

        return build_alexa_response('%s%s.' % (answer, answer_append), card_title)


# Handle the CurrentPlayItemTimeRemaining intent.
def alexa_current_playitem_time_remaining(slots):
    card_title = "Time left on currently playing item"  # @@

    answer = 'Playback is stopped.'

    status = kodi_helpers.GetPlayerStatus()
    if status['state'] is not 'stop':
        minsleft = status['total_mins'] - status['time_mins']
        if minsleft == 0:
            answer = 'It is nearly over.'  # @@
        elif minsleft == 1:
            answer = 'There is one minute remaining.'  # @@
        elif minsleft > 1:
            answer = 'There are %d minutes remaining' % (minsleft)  # @@
            if minsleft > 9:
                loctime = datetime.datetime.now()
                endtime = loctime + datetime.timedelta(minutes=minsleft)
                answer += '; and it will end at %s.' % (  # @@
                    endtime.strftime('%I:%M'))
            else:
                answer += '.'

    return build_alexa_response(answer, card_title)


# Handle the PlayPause intent.
def alexa_play_pause(slots):
    xbmc.log('In play_pause', level=xbmc.LOGNOTICE)
    card_title = 'Playing or pausing'  # @@

    kodi_helpers.PlayPause()
    answer = "Play/Pause"  # @@
    return build_alexa_response(answer, card_title)


# Handle the Stop intent.
def alexa_stop(slots):
    card_title = 'Stopping playback'  # @@

    kodi_helpers.Stop()
    answer = "Playback stopped"  # @@
    return build_alexa_response(answer, card_title)


# Handle the PlayerSeekSmallForward intent.
def alexa_player_seek_smallforward(slots):
    card_title = 'Stepping forward'  # @@

    kodi_helpers.PlayerSeekSmallForward()
    answer = ""
    return build_alexa_response(answer, card_title)


# Handle the PlayerSeekSmallBackward intent.
def alexa_player_seek_smallbackward(slots):
    card_title = 'Stepping backward'  # @@

    kodi_helpers.PlayerSeekSmallBackward()
    answer = ""
    return build_alexa_response(answer, card_title)


# Handle the PlayerSeekBigForward intent.
def alexa_player_seek_bigforward(slots):
    card_title = 'Big Step forward'  # @@

    kodi_helpers.PlayerSeekBigForward()
    answer = ""
    return build_alexa_response(answer, card_title)


# Handle the PlayerSeekBigBackward intent.
def alexa_player_seek_bigbackward(slots):
    card_title = 'Big Step backward'  # @@

    kodi_helpers.PlayerSeekBigBackward()
    answer = ""
    return build_alexa_response(answer, card_title)


# Handle the ListenToArtist intent.
# Shuffle all music by an artist.
def alexa_listen_artist(slots):
    heard_artist = str(slots['Artist']['value']).lower().translate(None, string.punctuation)

    card_title = 'Playing music by %s' % (heard_artist,)  # @@

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
            return build_alexa_response('Playing %s' % (heard_artist,), card_title)  # @@
        else:
            return build_alexa_response('Can\'t find %s' % (heard_artist,), card_title)  # @@
    else:
        return build_alexa_response('Can\'t find %s' % (heard_artist,), card_title)  # @@


# Handle the ListenToAlbum intent.
# Play whole album, or whole album by a specific artist.
def alexa_listen_album(slots):
    heard_album = str(slots['Album']['value']).lower().translate(None, string.punctuation)
    if 'value' in slots['Artist']:
        heard_artist = str(slots['Artist']['value']).lower().translate(None, string.punctuation)
        card_title = 'Playing album %s by %s' % (heard_album, heard_artist)  # @@
    else:
        card_title = 'Playing album %s' % (heard_album,)  # @@

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
                        return build_alexa_response('Can\'t find album %s by %s' % (heard_album, heard_artist),  # @@
                                                    card_title)
                    return build_alexa_response('Playing album %s by %s' % (  # @@
                        heard_album, heard_artist), card_title)
                else:
                    return build_alexa_response('Can\'t find album %s by %s' % (heard_album, heard_artist),  # @@
                                                card_title)

            else:
                return build_alexa_response('Can\'t find album %s by %s' % (heard_album, heard_artist), card_title)  # @@
        else:
            return build_alexa_response('Can\'t find artist %s' % (heard_artist,), card_title)  # @@
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
                return build_alexa_response('Can\'t find album %s' % (heard_album,), card_title)  # @@
            return build_alexa_response('Playing album %s' % (heard_album,), card_title)  # @@
        else:
            return build_alexa_response('Can\'t find album %s' % (heard_album,), card_title)  # @@


# Handle the ListenToSong intent.
# Play a song, or song by a specific artist.
def alexa_listen_song(slots):
    heard_song = str(slots['Song']['value']).lower().translate(None, string.punctuation)
    heard_artist = 'UNKNOWN'
    if 'value' in slots['Artist']:
        heard_artist = str(slots['Artist']['value']).lower().translate(None, string.punctuation)
        card_title = 'Playing song %s by %s' % (heard_song, heard_artist)  # @@
    else:
        card_title = 'Playing song %s' % (heard_song,)  # @@

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
                        return build_alexa_response('Can\'t find song %s by %s' % (heard_song, heard_artist),  # @@
                                                    card_title)
                    return build_alexa_response('Playing song %s by %s' % (heard_song, heard_artist), card_title)  # @@
                else:
                    return build_alexa_response('Can\'t find song %s by %s' % (heard_song, heard_artist),  # @@
                                                card_title)

            else:
                return build_alexa_response('Can\'t find song %s by %s' % (heard_song, heard_artist), card_title)  # @@
        else:
            return build_alexa_response('Can\'t find song %s by %s' % (heard_artist,), card_title)  # @@
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
                return build_alexa_response('Can\'t find song %s' % (heard_song,), card_title)  # @@
            return build_alexa_response('Playing song %s' % (heard_song,), card_title)  # @@
        else:
            return build_alexa_response('Can\'t find song %s' % (heard_song,), card_title)  # @@


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
                    return build_alexa_response('Playing album %s by %s' % (  # @@
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
                            return build_alexa_response('Playing song %s by %s' %  # @@
                                                        (heard_search, heard_artist),
                                                        card_title)
                        else:
                            return build_alexa_response('Can\'t find %s by %s' %  # @@
                                                        (heard_search, heard_artist),
                                                        card_title)
                    else:
                        return build_alexa_response('Can\'t find %s by %s' %  # @@
                                                    (heard_search, heard_artist),
                                                    card_title)
            else:
                return build_alexa_response('Can\'t find %s by %s' %  # @@
                                            (heard_search, heard_artist), card_title)

        else:
            return build_alexa_response('Can\'t find %s by %s' % (heard_search, heard_artist), card_title)  # @@
    else:
        return build_alexa_response('Can\'t find %s' % (heard_artist,), card_title)  # @@


# Handle the ListenToAudioPlaylistRecent intent.
# Shuffle all recently added songs.
def alexa_listen_recently_added_songs(slots):
    card_title = 'Playing recently added songs'  # @@

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
        return build_alexa_response('Playing recently added songs', card_title)  # @@
    return build_alexa_response('No recently added songs found', card_title)  # @@


# Handle the ListenToAudioPlaylist intent.
def alexa_listen_audio_playlist(slots, shuffle=False):
    heard_search = str(slots['AudioPlaylist']['value']).lower().translate(None, string.punctuation)

    if shuffle:
        op = 'Shuffling'  # @@
    else:
        op = 'Playing'  # @@

    card_title = '%s audio playlist ' % op  # @@
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
        return build_alexa_response('%s playlist %s' % (op, heard_search), card_title)  # @@
    else:
        return build_alexa_response('Can\'t find a playlist named %s' % (heard_search,), card_title)  # @@


# Handle the ShuffleAudioPlaylist intent.
def alexa_shuffle_audio_playlist(slots):
    return alexa_listen_audio_playlist(slots, True)


# Handle the PartyMode intent.
def alexa_party_play(slots):
    card_title = 'Party Mode'  # @@
    songs = kodi_helpers.GetSongs()

    if 'result' in songs and 'songs' in songs['result']:
        songs_array = []

        for song in songs['result']['songs']:
            songs_array.append(song['songid'])

        kodi_helpers.Stop()
        kodi_helpers.ClearAudioPlaylist()
        kodi_helpers.AddSongsToPlaylist(songs_array, True)
        kodi_helpers.StartAudioPlaylist()
        return build_alexa_response('Starting party play', card_title)  # @@
    else:
        return build_alexa_response('Error parsing results', card_title)  # @@


# Handle the StartOver intent.
def alexa_start_over(slots):
    card_title = 'Starting current item over'  # @@

    kodi_helpers.PlayStartOver()
    answer = "Starting over"  # @@
    return build_alexa_response(answer, card_title)


# Handle the Skip intent.
def alexa_skip(slots):
    card_title = 'Playing next item'  # @@

    kodi_helpers.PlaySkip()
    answer = "Skip"  # @@
    return build_alexa_response(answer, card_title)


# Handle the Prev intent.
def alexa_prev(slots):
    card_title = 'Playing previous item'  # @@

    kodi_helpers.PlayPrev()
    answer = "Previous"  # @@
    return build_alexa_response(answer, card_title)


# Handle the Fullscreen intent.
def alexa_fullscreen(slots):
    card_title = 'Toggling fullscreen'  # @@

    kodi_helpers.ToggleFullscreen()
    answer = "Fullscreen toggled"  # @@
    return build_alexa_response(answer, card_title)


# Handle the Mute intent.
def alexa_mute(slots):
    card_title = 'Muting or unmuting'  # @@

    kodi_helpers.ToggleMute()
    answer = "Mute toggled"  # @@
    return build_alexa_response(answer, card_title)


# Handle the VolumeUp intent.
def alexa_volume_up(slots):
    card_title = 'Turning volume up'  # @@

    vol = kodi_helpers.VolumeUp()['result']
    answer = "Volume set to %d%%." % (vol,)  # @@
    return build_alexa_response(answer, card_title)


# Handle the VolumeDown intent.
def alexa_volume_down(slots):
    card_title = 'Turning volume down'  # @@

    vol = kodi_helpers.VolumeDown()['result']
    answer = "Volume set to %d%%." % (vol,)  # @@
    return build_alexa_response(answer, card_title)


# Handle the VolumeSet intent.
def alexa_volume_set(slots):
    card_title = 'Adjusting volume'  # @@

    try:
        vol = kodi_helpers.VolumeSet(int(slots['Volume']['value']), False)['result']
        answer = "Volume set to %d%%." % (vol,)  # @@
    except ValueError:
        answer = "Couldn't catch the volume requested"  # @@
    return build_alexa_response(answer, card_title)


# Handle the VolumeSetPct intent.
def alexa_volume_set_pct(slots):
    card_title = 'Adjusting volume'  # @@

    try:
        vol = kodi_helpers.VolumeSet(int(slots['Volume']['value']))['result']
        answer = "Volume set to %d%%." % (vol,)  # @@
    except ValueError:
        answer = "Couldn't catch the volume percent"  # @@
    return build_alexa_response(answer, card_title)


# Handle the SubtitlesOn intent.
def alexa_subtitles_on(slots):
    card_title = 'Enabling subtitles'  # @@

    kodi_helpers.SubtitlesOn()
    answer = kodi_helpers.GetCurrentSubtitles()
    return build_alexa_response(answer, card_title)


# Handle the SubtitlesOff intent.
def alexa_subtitles_off(slots):
    card_title = 'Disabling subtitles'  # @@

    kodi_helpers.SubtitlesOff()
    answer = kodi_helpers.GetCurrentSubtitles()
    return build_alexa_response(answer, card_title)


# Handle the SubtitlesNext intent.
def alexa_subtitles_next(slots):
    card_title = 'Switching to next subtitles'  # @@

    kodi_helpers.SubtitlesNext()
    answer = kodi_helpers.GetCurrentSubtitles()
    return build_alexa_response(answer, card_title)


# Handle the AudioStreamNext intent.
def alexa_audiostream_next(slots):
    card_title = 'Switching to next audio stream'  # @@

    kodi_helpers.AudioStreamNext()
    answer = kodi_helpers.GetCurrentAudioStream()
    return build_alexa_response(answer, card_title)


# Handle the Menu intent.
def alexa_context_menu(slots):
    card_title = 'Navigate: Context Menu'  # @@

    kodi_helpers.Menu()
    answer = "Opening menu"  # @@
    return build_alexa_response(answer, None, end_session=False)


# Handle the Home intent.
def alexa_go_home(slots):
    card_title = 'Navigate: Home'  # @@

    kodi_helpers.Home()
    answer = "Home screen"  # @@
    return build_alexa_response(answer, None, end_session=False)


# Handle the Select intent.
def alexa_select(slots):
    card_title = 'Navigate: Select'  # @@

    kodi_helpers.Select()
    answer = "Selecting"  # @@
    return build_alexa_response(answer, None, end_session=False)


# Handle the PageUp intent.
def alexa_pageup(slots):
    card_title = 'Navigate: Page up'  # @@

    kodi_helpers.PageUp()
    answer = "Page up"  # @@
    return build_alexa_response(answer, None, end_session=False)


# Handle the PageDown intent.
def alexa_pagedown(slots):
    card_title = 'Navigate: Page down'  # @@

    kodi_helpers.PageDown()
    answer = "Page down"  # @@
    return build_alexa_response(answer, None, end_session=False)


# Handle the Left intent.
def alexa_left(slots):
    card_title = 'Navigate: Left'  # @@

    kodi_helpers.Left()
    answer = "Left"  # @@
    return build_alexa_response(answer, None, end_session=False)


# Handle the Right intent.
def alexa_right(slots):
    card_title = 'Navigate: Right'  # @@

    kodi_helpers.Right()
    answer = "Right"  # @@
    return build_alexa_response(answer, None, end_session=False)


# Handle the Up intent.
def alexa_up(slots):
    card_title = 'Navigate: Up'  # @@

    kodi_helpers.Up()
    answer = "Up"  # @@
    return build_alexa_response(answer, None, end_session=False)


# Handle the Down intent.
def alexa_down(slots):
    card_title = 'Navigate: Down'  # @@

    kodi_helpers.Down()
    answer = "Down"  # @@
    return build_alexa_response(answer, None, end_session=False)


# Handle the Back intent.
def alexa_back(slots):
    card_title = 'Navigate: Back'  # @@

    kodi_helpers.Back()
    answer = "Back"  # @@
    return build_alexa_response(answer, None, end_session=False)


# Handle the Hibernate intent.
def alexa_hibernate(slots):
    card_title = 'Hibernating'  # @@

    kodi_helpers.SystemHibernate()
    answer = "Hibernating system"  # @@
    return build_alexa_response(answer, card_title)


# Handle the Reboot intent.
def alexa_reboot(slots):
    card_title = 'Rebooting'  # @@

    kodi_helpers.SystemReboot()
    answer = "Rebooting system"  # @@
    return build_alexa_response(answer, card_title)


# Handle the Shutdown intent.
def alexa_shutdown(slots):
    card_title = 'Shutting down'  # @@

    kodi_helpers.SystemShutdown()
    answer = "Shutting down system"  # @@
    return build_alexa_response(answer, card_title)


# Handle the Suspend intent.
def alexa_suspend(slots):
    card_title = 'Suspending'  # @@

    kodi_helpers.SystemSuspend()
    answer = "Suspending system"  # @@
    return build_alexa_response(answer, card_title)


# Handle the EjectMedia intent.
def alexa_ejectmedia(slots):
    card_title = 'Ejecting media'  # @@

    kodi_helpers.SystemEjectMedia()
    answer = "Ejecting media"  # @@
    return build_alexa_response(answer, card_title)


# Handle the CleanVideo intent.
def alexa_clean_video(slots):
    card_title = 'Cleaning video library'  # @@

    # Use threading to solve the call from returing too late
    c = Process(target=kodi_helpers.CleanVideo)
    c.daemon = True
    c.start()

    time.sleep(2)

    answer = "Cleaning video library"  # @@
    return build_alexa_response(answer, card_title)


# Handle the UpdateVideo intent.
def alexa_update_video(slots):
    card_title = 'Updating video library'  # @@

    kodi_helpers.UpdateVideo()

    answer = "Updating video library"  # @@
    return build_alexa_response(answer, card_title)


# Handle the CleanAudio intent.
def alexa_clean_audio(slots):
    card_title = 'Cleaning audio library'  # @@

    # Use threading to solve the call from returing too late
    c = Process(target=kodi_helpers.CleanMusic)
    c.daemon = True
    c.start()

    time.sleep(2)

    answer = "Cleaning audio library"  # @@
    return build_alexa_response(answer, card_title)


# Handle the UpdateAudio intent.
def alexa_update_audio(slots):
    card_title = 'Updating audio library'  # @@

    kodi_helpers.UpdateMusic()

    answer = "Updating audio library"  # @@
    return build_alexa_response(answer, card_title)


# Handle the AddonExecute intent.
def alexa_addon_execute(slots):
    heard_addon = str(slots['Addon']['value']).lower().translate(None, string.punctuation)

    card_title = 'Opening the addon %s' % (heard_addon,)  # @@

    for content in ['video', 'audio', 'image', 'executable']:
        addons = kodi_helpers.GetAddons(content)
        if 'result' in addons and 'addons' in addons['result']:
            addons_array = addons['result']['addons']

            located = kodi_helpers.matchHeard(heard_addon, addons_array, lookingFor='name')

            if located:
                kodi_helpers.Home()
                kodi_helpers.AddonExecute(located['addonid'])

                return build_alexa_response('Opening %s' %   # @@
                                            (located['name']), card_title)
        else:
            return build_alexa_response('Can\'t find an addon called %s' % (heard_addon,), card_title)  # @@

    return build_alexa_response('Can\'t find an addon called %s' % (heard_addon,), card_title)  # @@


# Handle the AddonGlobalSearch intent.
def alexa_addon_globalsearch(slots):
    card_title = 'Search'  # @@
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
        answer = 'Searching for %s' % (heard_search,)  # @@

        kodi_helpers.Home()
        kodi_helpers.AddonGlobalSearch(heard_search)

        return build_alexa_response(answer, card_title)
    else:
        return build_alexa_response("Couldn't find anything matching that phrase", card_title)  # @@


# Handle the WatchRandomMovie intent.
def alexa_watch_random_movie(slots):
    genre_located = None
    # If a genre has been specified, match the genre for use in selecting a random film
    if 'value' in slots['Genre']:
        heard_genre = str(slots['Genre']['value']).lower().translate(None, string.punctuation)
        card_title = 'Playing a random %s movie' % (heard_genre,)  # @@
        genres = kodi_helpers.GetMovieGenres()
        if 'result' in genres and 'genres' in genres['result']:
            genres_list = genres['result']['genres']
            genre_located = kodi_helpers.matchHeard(heard_genre, genres_list, 'label')
    else:
        card_title = 'Playing a random movie'  # @@

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
            return build_alexa_response('Playing the %s movie %s' %   # @@
                                        (genre_located['label'], random_movie['label']),
                                        card_title)
        else:
            return build_alexa_response('Playing %s' % (  # @@
                random_movie['label']), card_title)
    else:
        return build_alexa_response('No movies', card_title)  # @@


# Handle the WatchMovie intent.
def alexa_watch_movie(slots):
    heard_movie = str(slots['Movie']['value']).lower().translate(None, string.punctuation)

    card_title = 'Playing the movie %s' % (heard_movie,)  # @@

    movies = kodi_helpers.GetMovies()
    if 'result' in movies and 'movies' in movies['result']:
        movies_array = movies['result']['movies']

        located = kodi_helpers.matchHeard(heard_movie, movies_array)

        if located:
            if kodi_helpers.GetMovieDetails(located['movieid'])['resume']['position'] > 0:
                action = 'Resuming'  # @@
            else:
                action = 'Playing'  # @@

            kodi_helpers.PlayMovie(located['movieid'])

            return build_alexa_response('%s %s' % (action, heard_movie), card_title)
        else:
            return build_alexa_response('Can\'t find a movie called %s' % (heard_movie,), card_title)  # @@
    else:
        return build_alexa_response('Can\'t find a movie called %s' % (heard_movie,), card_title)  # @@


# Handle the WatchRandomEpisode intent.
def alexa_watch_random_episode(slots):
    heard_show = str(slots['Show']['value']).lower().translate(None, string.punctuation)

    card_title = 'Playing a random episode of %s' % (heard_show,)  # @@

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

            return build_alexa_response('Playing season %d episode %d of %s' % (  # @@
                episode_details['season'], episode_details['episode'], heard_show), card_title)
        else:
            return build_alexa_response('Can\'t find a show named %s' % (heard_show,), card_title)  # @@
    else:
        return build_alexa_response('Show not found', card_title)  # @@


# Handle the WatchEpisode intent.
def alexa_watch_episode(slots):
    heard_show = str(slots['Show']['value']).lower().translate(None, string.punctuation)

    card_title = 'Playing an episode of %s' % (heard_show,)  # @@

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
                    action = 'Resuming'  # @@
                else:
                    action = 'Playing'  # @@

                kodi_helpers.PlayEpisode(episode_id)

                return build_alexa_response(
                    '%s season %s episode %s of %s' %  # @@
                    (action, heard_season, heard_episode, heard_show), card_title)

            else:
                return build_alexa_response(
                    'Can\'t find season %s episode %s of %s' %  # @@
                    (heard_season, heard_episode, heard_show), card_title)
        else:
            return build_alexa_response('Can\'t find a show named %s' %  # @@
                                        (heard_show,), card_title)
    else:
        return build_alexa_response('Show not found', card_title)  # @@


# Handle the WatchNextEpisode intent.
def alexa_watch_next_episode(slots):
    heard_show = str(slots['Show']['value']).lower().translate(None, string.punctuation)

    card_title = 'Playing the next unwatched episode of %s' % (heard_show,)  # @@

    shows = kodi_helpers.GetTvShows()
    if 'result' in shows and 'tvshows' in shows['result']:
        shows_array = shows['result']['tvshows']

        located = kodi_helpers.matchHeard(heard_show, shows_array)

        if located:
            next_episode_id = kodi_helpers.GetNextUnwatchedEpisode(located['tvshowid'])

            if next_episode_id:
                episode_details = kodi_helpers.GetEpisodeDetails(next_episode_id)

                if episode_details['resume']['position'] > 0:
                    action = 'Resuming'  # @@
                else:
                    action = 'Playing'  # @@

                kodi_helpers.PlayEpisode(next_episode_id)

                return build_alexa_response('%s season %d episode %d of %s' % (  # @@
                    action, episode_details['season'], episode_details['episode'], heard_show), card_title)
            else:
                return build_alexa_response('No new episodes for %s' % (heard_show,), card_title)  # @@
        else:
            return build_alexa_response('Can\'t find a show named %s' % (heard_show,), card_title)  # @@
    else:
        return build_alexa_response('Can\'t find a show named %s' % (heard_show,), card_title)  # @@


# Handle the WatchNewestEpisode intent.
def alexa_watch_newest_episode(slots):
    heard_show = str(slots['Show']['value']).lower().translate(None, string.punctuation)

    card_title = 'Playing the newest episode of %s' % (heard_show)  # @@

    shows = kodi_helpers.GetTvShows()
    if 'result' in shows and 'tvshows' in shows['result']:
        shows_array = shows['result']['tvshows']

        located = kodi_helpers.matchHeard(heard_show, shows_array)

        if located:
            episode_id = kodi_helpers.GetNewestEpisodeFromShow(located['tvshowid'])

            if episode_id:
                episode_details = kodi_helpers.GetEpisodeDetails(episode_id)

                if episode_details['resume']['position'] > 0:
                    action = 'Resuming'  # @@
                else:
                    action = 'Playing'  # @@

                kodi_helpers.PlayEpisode(episode_id)

                return build_alexa_response('%s season %d episode %d of %s' % (  # @@
                    action, episode_details['season'], episode_details['episode'], heard_show), card_title)
            else:
                return build_alexa_response('No new episodes for %s' % (heard_show,), card_title)  # @@
        else:
            return build_alexa_response('Can\'t find %s' % (heard_show,), card_title)  # @@
    else:
        return build_alexa_response('Error parsing results', card_title)  # @@


# Handle the WatchLastShow intent.
def alexa_watch_last_show(slots):
    card_title = 'Playing the next unwatched episode of the last show watched'  # @@

    last_show_obj = kodi_helpers.GetLastWatchedShow()

    try:
        last_show_id = last_show_obj['result']['episodes'][0]['tvshowid']
        next_episode_id = kodi_helpers.GetNextUnwatchedEpisode(last_show_id)

        if next_episode_id:
            episode_details = kodi_helpers.GetEpisodeDetails(next_episode_id)

            if episode_details['resume']['position'] > 0:
                action = 'Resuming'  # @@
            else:
                action = 'Playing'  # @@

            kodi_helpers.PlayEpisode(next_episode_id)

            return build_alexa_response('%s season %d episode %d of %s' % (  # @@
                action, episode_details['season'], episode_details['episode'],
                last_show_obj['result']['episodes'][0]['showtitle']), card_title)
        else:
            return build_alexa_response('No new episodes for %s' %  # @@
                                        last_show_obj['result']['episodes'][0]['showtitle'],
                                        card_title)
    except:
        return build_alexa_response('Error parsing results', card_title)  # @@


# Handle the WatchVideoPlaylist intent.
def alexa_watch_video_playlist(slots, shuffle=False):
    heard_search = str(slots['VideoPlaylist']['value']).lower().translate(None, string.punctuation)

    if shuffle:
        op = 'Shuffling'  # @@
    else:
        op = 'Playing'  # @@

    card_title = '%s video playlist ' % op  # @@
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
        return build_alexa_response('%s playlist %s' % (op, heard_search), card_title)  # @@
    else:
        return build_alexa_response('Can\'t find a playlist named %s' % (heard_search,), card_title)  # @@


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

    card_title = 'Shuffling playlist '  # @@
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
            return build_alexa_response('Shuffling video playlist %s' % (heard_search,), card_title)  # @@
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
                return build_alexa_response('Shuffling audio playlist %s' % (heard_search,), card_title)  # @@

        return build_alexa_response('Can\'t find a playlist named %s' % (heard_search,), card_title)  # @@
    else:
        return build_alexa_response('Can\'t find a playlist named %s' % (heard_search,), card_title)  # @@


def suggest_alternate_activity(chance=0.25):
    if random.random() < chance:
        comments = [
            " Maybe you should go to the movies.",  # @@
            " Maybe you'd like to read a book.",  # @@
            " Time to go for a bike ride?",  # @@
            " You probably have chores to do anyway.",  # @@
        ]
        return random.choice(comments)
    else:
        return ''


# Handle the WhatNewAlbums intent.
def alexa_what_new_albums(slots):
    card_title = 'Newly added albums'  # @@

    # Get the list of recently added albums from Kodi
    new_albums = kodi_helpers.GetRecentlyAddedAlbums()['result']['albums']

    new_album_names = list(set([sanitize_name('%s by %s' %  # @@
                                              (x['label'], x['artist'][0])) for x in new_albums]))
    num_albums = len(new_album_names)

    xbmc.executebuiltin('ActivateWindow(Music,RecentlyAddedAlbums)')

    if num_albums == 0:
        # There's been nothing added to Kodi recently
        answers = [
            "You don't have any new albums to listen to.",  # @@
            "There are no new albums to listen to.",  # @@
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
                          ", and more"  # @@
        else:
            album_list += ", and " + limited_new_album_names[-1]  # @@
        answer = "You have %(album_list)s." % {  # @@
            "album_list": album_list}
    return build_alexa_response(answer, card_title)


# Handle the WhatNewMovies intent.
def alexa_what_new_movies(slots):
    genre_located = None
    # If a genre has been specified, match the genre for use in selecting random films
    if 'value' in slots['Genre']:
        heard_genre = str(slots['Genre']['value']).lower().translate(None, string.punctuation)
        card_title = 'Newly added %s movies' % (heard_genre)  # @@
        genres = kodi_helpers.GetMovieGenres()
        if 'result' in genres and 'genres' in genres['result']:
            genres_list = genres['result']['genres']
            genre_located = kodi_helpers.matchHeard(heard_genre, genres_list, 'label')
    else:
        card_title = 'Newly added movies'  # @@

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
            "You don't have any new movies to watch.",  # @@
            "There are no new movies to watch.",  # @@
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
                          ", and more"  # @@
        else:
            movie_list += ", and " + limited_new_movie_names[-1]  # @@
        answer = "You have %(movie_list)s." % {  # @@
            "movie_list": movie_list}
    return build_alexa_response(answer, card_title)


# Handle the WhatNewShows intent.
def alexa_what_new_episodes(slots):
    card_title = 'Newly added shows'  # @@

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
            "You don't have any new shows to watch.",  # @@
            "There are no new shows to watch.",  # @@
        ]
        answer = random.choice(answers)
        answer += suggest_alternate_activity()
    elif len(new_show_names) == 1:
        # There's only one new show, so provide information about the number of episodes, too.
        count = len(new_episodes)
        if count == 1:
            answers = [
                "There is a single new episode of %(show)s." %  # @@
                {'show': new_show_names[0]},
                "There is one new episode of %(show)s." %  # @@
                {'show': new_show_names[0]},
            ]
        elif count == 2:
            answers = [
                "There are a couple new episodes of %(show)s" %  # @@
                {'show': new_show_names[0]},
                "There are two new episodes of %(show)s" %  # @@
                {'show': new_show_names[0]},
            ]
        elif count >= 5:
            answers = [
                "There are lots and lots of new episodes of %(show)s" %  # @@
                {'show': new_show_names[0]},
                "There are %(count)d new episodes of %(show)s" %  # @@
                {"count": count, "show": new_show_names[0]},
            ]
        else:
            answers = [
                "You have a few new episodes of %(show)s" %  # @@
                {'show': new_show_names[0]},
                "There are %(count)d new episodes of %(show)s" %  # @@
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
                         " and more"  # @@
        else:
            show_list += " and " + limited_new_show_names[-1]  # @@
        answer = "There are new episodes of %(show_list)s." % {  # @@
            "show_list": show_list}
    return build_alexa_response(answer, card_title)


# Handle the WhatAlbums intent.
def alexa_what_albums(slots):
    heard_artist = str(slots['Artist']['value']).lower().translate(None, string.punctuation)

    card_title = 'Albums by %s' % (heard_artist,)  # @@

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
                    album_list += ", and " + really_albums[-1]  # @@
                return build_alexa_response('You have %s' % (album_list,), card_title)  # @@
            else:
                return build_alexa_response('You have no albums by %s' % (heard_artist,), card_title)  # @@
        else:
            return build_alexa_response('Can\'t find %s' % (heard_artist,), card_title)  # @@
    else:
        return build_alexa_response('Can\'t find %s' % (heard_artist,), card_title)  # @@


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
