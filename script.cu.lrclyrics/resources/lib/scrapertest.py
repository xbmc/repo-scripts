#-*- coding: UTF-8 -*-
import time
from utilities import *
from culrcscrapers.alsong import lyricsScraper as lyricsScraper_alsong
from culrcscrapers.baidu import lyricsScraper as lyricsScraper_baidu
from culrcscrapers.darklyrics import lyricsScraper as lyricsScraper_darklyrics
from culrcscrapers.genius import lyricsScraper as lyricsScraper_genius
from culrcscrapers.gomaudio import lyricsScraper as lyricsScraper_gomaudio
from culrcscrapers.lyricscom import lyricsScraper as lyricsScraper_lyricscom
from culrcscrapers.lyricsmode import lyricsScraper as lyricsScraper_lyricsmode
from culrcscrapers.lyricwiki import lyricsScraper as lyricsScraper_lyricwiki
from culrcscrapers.ttplayer import lyricsScraper as lyricsScraper_ttplayer

FAILED = []

def test_scrapers():
    dialog = xbmcgui.DialogProgress()
    TIMINGS = []

    # test alsong
    dialog.create(ADDONNAME, LANGUAGE(32163) % 'alsong')
    log('==================== alsong ====================')
    song = Song('Blur', 'There\'s No Other Way')
    st = time.time()
    lyrics = lyricsScraper_alsong.LyricsFetcher().get_lyrics(song)
    ft = time.time()
    tt = ft - st
    TIMINGS.append(['alsong',tt])
    if lyrics:
        log(lyrics.lyrics)
    else:
        FAILED.append('alsong')
        log('FAILED: alsong')
    if dialog.iscanceled():
        return

    # test baidu
    dialog.update(11, LANGUAGE(32163) % 'baidu')
    log('==================== baidu ====================')
    song = Song('Blur', 'There\'s No Other Way')
    st = time.time()
    lyrics = lyricsScraper_baidu.LyricsFetcher().get_lyrics(song)
    ft = time.time()
    tt = ft - st
    TIMINGS.append(['baidu',tt])
    if lyrics:
        log(lyrics.lyrics)
    else:
        FAILED.append('baidu')
        log('FAILED: baidu')
    if dialog.iscanceled():
        return

    # test darklyrics
    dialog.update(22, LANGUAGE(32163) % 'darklyrics')
    log('==================== darklyrics ====================')
    song = Song('Neurosis', 'Lost')
    st = time.time()
    lyrics = lyricsScraper_darklyrics.LyricsFetcher().get_lyrics(song)
    ft = time.time()
    tt = ft - st
    TIMINGS.append(['darklyrics',tt])
    if lyrics:
        log(lyrics.lyrics)
    else:
        FAILED.append('darklyrics')
        log('FAILED: darklyrics')
    if dialog.iscanceled():
        return

    # test genius
    dialog.update(33, LANGUAGE(32163) % 'genius')
    log('==================== genius ====================')
    song = Song('Maren Morris', 'My Church')
    st = time.time()
    lyrics = lyricsScraper_genius.LyricsFetcher().get_lyrics(song)
    ft = time.time()
    tt = ft - st
    TIMINGS.append(['genius',tt])
    if lyrics:
        log(lyrics.lyrics)
    else:
        FAILED.append('genius')
        log('FAILED: genius')
    if dialog.iscanceled():
        return

    # test gomaudio
    dialog.update(44, LANGUAGE(32163) % 'gomaudio')
    log('==================== gomaudio ====================')
    song = Song('Lady Gaga', 'Just Dance')
    st = time.time()
    lyrics = lyricsScraper_gomaudio.LyricsFetcher().get_lyrics(song, 'd106534632cb43306423acb351f8e6e9', '.mp3')
    ft = time.time()
    tt = ft - st
    TIMINGS.append(['gomaudio',tt])
    if lyrics:
        log(lyrics.lyrics)
    else:
        FAILED.append('gomaudio')
        log('FAILED: gomaudio')
    if dialog.iscanceled():
        return

    # test lyricscom
    dialog.update(55, LANGUAGE(32163) % 'lyricscom')
    log('==================== lyricscom ====================')
    song = Song('Blur', 'You\'re So Great')
    st = time.time()
    lyrics = lyricsScraper_lyricscom.LyricsFetcher().get_lyrics(song)
    ft = time.time()
    tt = ft - st
    TIMINGS.append(['lyricscom',tt])
    if lyrics:
        log(lyrics.lyrics)
    else:
        FAILED.append('lyricscom')
        log('FAILED: lyricscom')
    if dialog.iscanceled():
        return

    # test lyricsmode
    dialog.update(66, LANGUAGE(32163) % 'lyricsmode')
    log('==================== lyricsmode ====================')
    song = Song('Maren Morris', 'My Church')
    st = time.time()
    lyrics = lyricsScraper_lyricsmode.LyricsFetcher().get_lyrics(song)
    ft = time.time()
    tt = ft - st
    TIMINGS.append(['lyricsmode',tt])
    if lyrics:
        log(lyrics.lyrics)
    else:
        FAILED.append('lyricsmode')
        log('FAILED: lyricsmode')
    if dialog.iscanceled():
        return

    # test lyricwiki
    dialog.update(77, LANGUAGE(32163) % 'lyricwiki')
    log('==================== lyricwiki ====================')
    song = Song('Maren Morris', 'My Church')
    st = time.time()
    lyrics = lyricsScraper_lyricwiki.LyricsFetcher().get_lyrics(song)
    ft = time.time()
    tt = ft - st
    TIMINGS.append(['lyricwiki',tt])
    if lyrics:
        log(lyrics.lyrics)
    else:
        FAILED.append('lyricwiki')
        log('FAILED: lyricwiki')
    if dialog.iscanceled():
        return

    # test ttplayer
    dialog.update(88, LANGUAGE(32163) % 'ttplayer')
    log('==================== ttplayer ====================')
    song = Song('Abba', 'Elaine')
    st = time.time()
    lyrics = lyricsScraper_ttplayer.LyricsFetcher().get_lyrics(song)
    ft = time.time()
    tt = ft - st
    TIMINGS.append(['ttplayer',tt])
    if lyrics:
        log(lyrics.lyrics)
    else:
        FAILED.append('ttplayer')
        log('FAILED: ttplayer')
    if dialog.iscanceled():
        return

    dialog.close()
    log('=======================================')
    log('FAILED: %s' % str(FAILED))
    log('=======================================')
    for item in TIMINGS:
        log('%s - %i' % (item[0], item[1]))
    log('=======================================')
    if FAILED:
        dialog = xbmcgui.Dialog().ok(ADDONNAME, LANGUAGE(32165) % ' / '.join(FAILED))
    else:
        dialog = xbmcgui.Dialog().ok(ADDONNAME, LANGUAGE(32164))
