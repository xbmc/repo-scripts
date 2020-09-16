#-*- coding: UTF-8 -*-
import time
from utilities import *
from culrcscrapers.azlyrics import lyricsScraper as lyricsScraper_azlyrics
from culrcscrapers.genius import lyricsScraper as lyricsScraper_genius
from culrcscrapers.gomaudio import lyricsScraper as lyricsScraper_gomaudio
from culrcscrapers.lyricscom import lyricsScraper as lyricsScraper_lyricscom
from culrcscrapers.lyricsmode import lyricsScraper as lyricsScraper_lyricsmode
from culrcscrapers.lyricwiki import lyricsScraper as lyricsScraper_lyricwiki
from culrcscrapers.minilyrics import lyricsScraper as lyricsScraper_minilyrics
from culrcscrapers.music163 import lyricsScraper as lyricsScraper_music163

FAILED = []

def test_scrapers():
    dialog = xbmcgui.DialogProgress()
    TIMINGS = []

    # test alsong
    dialog.create(ADDONNAME, LANGUAGE(32163) % 'azlyrics')
    log('==================== azlyrics ====================')
    song = Song('La Dispute', 'Such Small Hands')
    st = time.time()
    lyrics = lyricsScraper_azlyrics.LyricsFetcher().get_lyrics(song)
    ft = time.time()
    tt = ft - st
    TIMINGS.append(['azlyrics',tt])
    if lyrics:
        log(lyrics.lyrics)
    else:
        FAILED.append('azlyrics')
        log('FAILED: azlyrics')
    if dialog.iscanceled():
        return

    # test genius
    dialog.update(12, LANGUAGE(32163) % 'genius')
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
    dialog.update(25, LANGUAGE(32163) % 'gomaudio')
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
    dialog.update(37, LANGUAGE(32163) % 'lyricscom')
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
    dialog.update(50, LANGUAGE(32163) % 'lyricsmode')
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
    dialog.update(62, LANGUAGE(32163) % 'lyricwiki')
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

    # test minilyrics
    dialog.update(75, LANGUAGE(32163) % 'minilyrics')
    log('==================== minilyrics ====================')
    song = Song('Chicago', 'Stay The Night')
    st = time.time()
    lyrics = lyricsScraper_minilyrics.LyricsFetcher().get_lyrics(song)
    ft = time.time()
    tt = ft - st
    TIMINGS.append(['minilyrics',tt])
    if lyrics:
        log(lyrics.lyrics)
    else:
        FAILED.append('minilyrics')
        log('FAILED: minilyrics')
    if dialog.iscanceled():
        return

    # test music163
    dialog.update(87, LANGUAGE(32163) % 'music163')
    log('==================== music163 ====================')
    song = Song('Chicago', 'Stay The Night')
    st = time.time()
    lyrics = lyricsScraper_music163.LyricsFetcher().get_lyrics(song)
    ft = time.time()
    tt = ft - st
    TIMINGS.append(['music163',tt])
    if lyrics:
        log(lyrics.lyrics)
    else:
        FAILED.append('music163')
        log('FAILED: music163')
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
