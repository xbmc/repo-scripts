#-*- coding: UTF-8 -*-
import sys
import os
import re
import thread, threading
import xbmc, xbmcgui, xbmcvfs
from threading import Timer
from utilities import *
from embedlrc import *

CWD       = sys.modules[ "__main__" ].CWD
ADDON     = sys.modules[ "__main__" ].ADDON
ADDONNAME = sys.modules[ "__main__" ].ADDONNAME
PROFILE   = sys.modules[ "__main__" ].PROFILE
LANGUAGE  = sys.modules[ "__main__" ].LANGUAGE

class MAIN():
    def __init__(self, *args, **kwargs):
        self.mode = kwargs['mode']
        self.setup_main()
        WIN.setProperty('culrc.running', 'true')
        self.get_scraper_list()
        if ( ADDON.getSetting( "save_lyrics_path" ) == "" ):
            ADDON.setSetting(id="save_lyrics_path", value=os.path.join( PROFILE.encode("utf-8"), "lyrics" ))
        self.main_loop()
        self.cleanup_main()

    def setup_main(self):
        self.fetchedLyrics = []
        self.current_lyrics = Lyrics()
        self.MyPlayer = MyPlayer(function=self.myPlayerChanged, clear=self.clear)
        self.Monitor = MyMonitor(function=self.update_settings)

    def cleanup_main(self):
        # Clean up the monitor and Player classes on exit
        del self.MyPlayer
        del self.Monitor

    def get_scraper_list(self):
        self.scrapers = []
        for scraper in os.listdir(LYRIC_SCRAPER_DIR):
            if os.path.isdir(os.path.join(LYRIC_SCRAPER_DIR, scraper)) and ADDON.getSetting( scraper ) == "true":
                exec ( "from culrcscrapers.%s import lyricsScraper as lyricsScraper_%s" % (scraper, scraper))
                exec ( "self.scrapers.append([lyricsScraper_%s.__priority__,lyricsScraper_%s.LyricsFetcher(),lyricsScraper_%s.__title__,lyricsScraper_%s.__lrc__])" % (scraper, scraper, scraper, scraper))
        self.scrapers.sort()

    def main_loop(self):
        self.triggered = False
        # main loop
        while (not self.Monitor.abortRequested()) and (WIN.getProperty('culrc.quit') == ''):
            # Check if there is a manual override request
            if WIN.getProperty('culrc.manual') == 'true':
                log('searching for manually defined lyrics')
                self.get_manual_lyrics()
            # check if we are on the music visualization screen
            # do not try and get lyrics for any background media
            elif xbmc.getCondVisibility("Window.IsVisible(12006)") and xbmcgui.Window(10025).getProperty("PlayingBackgroundMedia") in [None, ""]:
                if not self.triggered:
                    self.triggered = True
                    # notify user the script is running
                    if ADDON.getSetting( "silent" ) == 'false':
                        xbmc.executebuiltin((u'Notification(%s,%s,%i)' % (ADDONNAME , LANGUAGE(32004), 2000)).encode('utf-8', 'ignore'))
                    # start fetching lyrics
                    self.myPlayerChanged()
                elif WIN.getProperty('culrc.force') == 'TRUE':
                    # we're already running, user clicked button on osd
                    WIN.setProperty('culrc.force','FALSE')
                    self.current_lyrics = Lyrics()
                    self.myPlayerChanged()
            else:
                # we may have exited the music visualization screen
                self.triggered = False
                # reset current lyrics so we show them again when re-entering the visualization screen
                self.current_lyrics = Lyrics()
            xbmc.sleep(1000)
        WIN.clearProperty('culrc.quit')
        WIN.clearProperty('culrc.lyrics')
        WIN.clearProperty('culrc.source')
        WIN.clearProperty('culrc.haslist')
        WIN.clearProperty('culrc.running')

    def get_lyrics(self, song):
        #xbmc.sleep( 60 )
        log('searching memory for lyrics')
        lyrics = self.get_lyrics_from_memory( song )
        if lyrics:
            log('found lyrics in memory')
            return lyrics
        if song.title:
            lyrics = self.find_lyrics( song )
            if ADDON.getSetting( 'strip' ) == "true":
                if isinstance (lyrics.lyrics,str):
                    fulltext = lyrics.lyrics.decode("utf-8")
                else:
                    fulltext = lyrics.lyrics
                strip_k = re.sub(ur"[\u1100-\u11ff]+", "", fulltext)
                strip_c = re.sub(ur"[\u3000-\u9fff]+", "", strip_k)
                lyrics.lyrics = strip_c.encode("utf-8")
        else:
            lyrics = Lyrics()
            lyrics.song = song
            lyrics.source = ''
            lyrics.lyrics = ''
        self.save_lyrics_to_memory(lyrics)
        return lyrics

    def find_lyrics(self, song):
        # search embedded lrc lyrics
        ext = os.path.splitext(song.filepath.decode("utf-8"))[1].lower()
        sup_ext = ['.mp3', '.flac']
        if ( ADDON.getSetting( "search_embedded" ) == "true") and song.analyze_safe and (ext in sup_ext):
            log('searching for embedded lrc lyrics')
            try:
                lyrics = getEmbedLyrics(song, True)
            except:
                lyrics = None
            if ( lyrics ):
                log('found embedded lrc lyrics')
                return lyrics
        # search lrc lyrics from file
        if ( ADDON.getSetting( "search_file" ) == "true" ):
            lyrics = self.get_lyrics_from_file(song, True)
            if ( lyrics ):
                log('found lrc lyrics from file')
                return lyrics
        # search lrc lyrics by scrapers
        for scraper in self.scrapers:
            if scraper[3]:
                lyrics = scraper[1].get_lyrics( song )
                if ( lyrics ):
                    log('found lrc lyrics online')
                    self.save_lyrics_to_file( lyrics )
                    return lyrics
        # search embedded txt lyrics
        if ( ADDON.getSetting( "search_embedded" ) == "true" and song.analyze_safe ):
            log('searching for embedded txt lyrics')
            try:
                lyrics = getEmbedLyrics(song, False)
            except:
                lyrics = None
            if lyrics:
                log('found embedded txt lyrics')
                return lyrics
        # search txt lyrics from file
        if ( ADDON.getSetting( "search_file" ) == "true" ):
            lyrics = self.get_lyrics_from_file(song, False)
            if ( lyrics ):
                log('found txt lyrics from file')
                return lyrics
        # search txt lyrics by scrapers
        for scraper in self.scrapers:
            if not scraper[3]:
                lyrics = scraper[1].get_lyrics( song )
                if ( lyrics ):
                    log('found txt lyrics online')
                    self.save_lyrics_to_file( lyrics )
                    return lyrics
        log('no lyrics found')
        lyrics = Lyrics()
        lyrics.song = song
        lyrics.source = ''
        lyrics.lyrics = ''
        return lyrics

    def get_lyrics_from_memory(self, song):
        for l in self.fetchedLyrics:
            if ( l.song == song ):
                return l
        return None

    def get_lyrics_from_file(self, song, getlrc):
        log('searching files for lyrics')
        lyrics = Lyrics()
        lyrics.song = song
        lyrics.source = LANGUAGE( 32000 )
        lyrics.lrc = getlrc
        if ADDON.getSetting( "save_lyrics1" ) == "true":
            # Search save path by Cu LRC Lyrics
            lyricsfile = song.path1(getlrc)
            if xbmcvfs.exists(lyricsfile):
                lyr = get_textfile( lyricsfile )
                if lyr:
                    lyrics.lyrics = lyr
                    return lyrics
        if ADDON.getSetting( "save_lyrics2" ) == "true":
            # Search same path with song file
            lyricsfile = song.path2(getlrc)
            if xbmcvfs.exists(lyricsfile):
                lyr = get_textfile( lyricsfile )
                if lyr:
                    lyrics.lyrics = lyr
                    return lyrics
        return None

    def save_lyrics_to_memory(self, lyrics):
        savedLyrics = self.get_lyrics_from_memory(lyrics.song)
        if ( savedLyrics is None ):
            self.fetchedLyrics.append(lyrics)
            self.fetchedLyrics = self.fetchedLyrics[:10]

    def save_lyrics_to_file(self, lyrics):
        if isinstance (lyrics.lyrics, str):
            lyr = lyrics.lyrics
        else:
            lyr = lyrics.lyrics.encode('utf-8')
        if ( ADDON.getSetting( "save_lyrics1" ) == "true" ):
            file_path = lyrics.song.path1(lyrics.lrc)
            success = self.write_lyrics_file( file_path, lyr)
        if ( ADDON.getSetting( "save_lyrics2" ) == "true" ):
            file_path = lyrics.song.path2(lyrics.lrc)
            success = self.write_lyrics_file( file_path, lyr)

    def write_lyrics_file(self, file, data):
        try:
            if ( not xbmcvfs.exists( os.path.dirname( file ) ) ):
                xbmcvfs.mkdirs( os.path.dirname( file ) )
            lyrics_file = xbmcvfs.File( file, "w" )
            lyrics_file.write( data )
            lyrics_file.close()
            return True
        except:
            log( "failed to save lyrics" )
            return False

    def myPlayerChanged(self):
        global lyrics
        for cnt in range( 5 ):
            song = Song.current()
            if ( song and ( self.current_lyrics.song != song ) ):
                log("Current Song: %s - %s" % (song.artist, song.title))
                lyrics = self.get_lyrics( song )
                self.current_lyrics = lyrics
                if lyrics.lyrics:
                    # signal the gui thread to display the next lyrics
                    WIN.setProperty('culrc.newlyrics', 'TRUE')
                    # check if gui is already running
                    if not WIN.getProperty('culrc.guirunning') == 'TRUE':
                        WIN.setProperty('culrc.guirunning', 'TRUE')
                        gui = guiThread(mode=self.mode)
                        gui.start()
                else:
                    # signal gui thread to exit
                    WIN.setProperty('culrc.nolyrics', 'TRUE')
                    # notify user no lyrics were found
                    if ADDON.getSetting( "silent" ) == 'false':
                        xbmc.executebuiltin((u'Notification(%s,%s,%i)' % (ADDONNAME + ": " + LANGUAGE(32001), song.artist.decode("utf-8") + " - " + song.title.decode("utf-8"), 2000)).encode('utf-8', 'ignore'))
                break
            xbmc.sleep( 50 )
        if xbmc.getCondVisibility('MusicPlayer.HasNext'):
            next_song = Song.next()
            if next_song:
                log("Next Song: %s - %s" % (next_song.artist, next_song.title))
                self.get_lyrics( next_song )
            else:
                log( "Missing Artist or Song name in ID3 tag for next track" )

    def get_manual_lyrics(self):
        # Read in the manually defined artist and track
        if WIN.getProperty('culrc.manual') == 'true':
            artist = WIN.getProperty('culrc.artist')
            track = WIN.getProperty('culrc.track')
            # Make sure we have both an artist and track name
            if artist and track:
                song = Song(artist, track)
                if ( song and ( self.current_lyrics.song != song ) ):
                    log("Current Song: %s - %s" % (song.artist, song.title))
                    lyrics = self.get_lyrics( song )
                    self.current_lyrics = lyrics
                    if lyrics.lyrics:
                        # Store the details of the lyrics
                        WIN.setProperty('culrc.newlyrics', 'TRUE')
                        WIN.setProperty('culrc.lyrics', lyrics.lyrics)
                        WIN.setProperty('culrc.source', lyrics.source)

    def update_settings(self):
        self.get_scraper_list()
        service = ADDON.getSetting('service')
        if service == "true":
            self.mode = 'service'
        else:
            self.mode = 'manual'
            # quit the script is mode was changed from service to manual
            WIN.setProperty('culrc.quit', 'TRUE')

    def clear(self):
        WIN.clearProperty('culrc.lyrics')
        WIN.clearProperty('culrc.source')
        WIN.clearProperty('culrc.haslist')


class guiThread(threading.Thread):
    def __init__(self, *args, **kwargs):
        threading.Thread.__init__(self)
        self.mode = kwargs[ "mode" ]

    def run(self):
        ui = GUI( "script-cu-lrclyrics-main.xml" , CWD, "Default", mode=self.mode )
        ui.doModal()
        del ui
        WIN.clearProperty('culrc.guirunning')

class GUI( xbmcgui.WindowXMLDialog ):
    def __init__(self, *args, **kwargs):
        xbmcgui.WindowXMLDialog.__init__(self)
        self.mode = kwargs[ "mode" ]
        self.Monitor = MyMonitor(function = None)
       
    def onInit(self):
        self.setup_gui()
        self.process_lyrics()
        self.gui_loop()

    def process_lyrics(self):
        global lyrics
        self.lyrics = lyrics
        self.stop_refresh()
        self.reset_controls()
        if self.lyrics.lyrics:
            self.show_lyrics(self.lyrics)
        else:
            WIN.setProperty('culrc.lyrics', LANGUAGE( 32001 ))
        self.getControl( 120 ).reset()
        if self.lyrics.list:
            WIN.setProperty('culrc.haslist', 'true')
            self.prepare_list(self.lyrics.list)
        else:
            WIN.clearProperty('culrc.haslist')

    def gui_loop(self):
        # gui loop
        while self.showgui and (not self.Monitor.abortRequested()) and xbmc.getCondVisibility('Player.HasAudio'):
            # check if we have new lyrics
            if WIN.getProperty("culrc.newlyrics") == "TRUE":
                WIN.clearProperty('culrc.newlyrics')
                # show new lyrics
                self.process_lyrics()
            # check if we have no lyrics
            elif WIN.getProperty("culrc.nolyrics") == "TRUE":
                # no lyrics, close the gui
                self.exit_gui('close')
            xbmc.sleep(500)
        # music ended, close the gui
        if (not xbmc.getCondVisibility('Player.HasAudio')):
            self.exit_gui('quit')
        # xbmc quits, close the gui 
        elif self.Monitor.abortRequested():
            self.exit_gui('quit')

    def setup_gui(self):
        WIN.clearProperty('culrc.newlyrics')
        WIN.clearProperty('culrc.nolyrics')
        WIN.clearProperty('culrc.haslist')
        self.lock = thread.allocate_lock()
        self.timer = None
        self.allowtimer = True
        self.refreshing = False
        self.selected = False
        self.controlId = -1
        self.pOverlay = []
        self.scroll_line = int(self.get_page_lines() / 2)
        self.showgui = True

    def get_page_lines(self):
        self.getControl( 110 ).setVisible( False )
        listitem = xbmcgui.ListItem()
        while xbmc.getInfoLabel('Container(110).NumPages') != '2':
            self.getControl(110).addItem(listitem)
            xbmc.sleep(10)
        lines = self.getControl( 110 ).size() - 1
        return lines

    def refresh(self):
        self.lock.acquire()
        try:
            #May be Kodi is not playing any media file
            cur_time = xbmc.Player().getTime()
            nums = self.getControl( 110 ).size()
            pos = self.getControl( 110 ).getSelectedPosition()
            if (cur_time < self.pOverlay[pos][0]):
                while (pos > 0 and self.pOverlay[pos - 1][0] > cur_time):
                    pos = pos -1
            else:
                while (pos < nums - 1 and self.pOverlay[pos + 1][0] < cur_time):
                    pos = pos +1
                if (pos + self.scroll_line > nums - 1):
                    self.getControl( 110 ).selectItem( nums - 1 )
                else:
                    self.getControl( 110 ).selectItem( pos + self.scroll_line )
            self.getControl( 110 ).selectItem( pos )
            self.setFocus( self.getControl( 110 ) )
            if (self.allowtimer and cur_time < self.pOverlay[nums - 1][0]):
                waittime = self.pOverlay[pos + 1][0] - cur_time
                self.timer = Timer(waittime, self.refresh)
                self.refreshing = True
                self.timer.start()
            else:
                self.refreshing = False
            self.lock.release()
        except:
            self.lock.release()

    def stop_refresh(self):
        self.lock.acquire()
        try:
            self.timer.cancel()
        except:
            pass
        self.refreshing = False
        self.lock.release()

    def show_control(self, controlId):
        self.getControl( 110 ).setVisible( controlId == 110 )
        self.getControl( 120 ).setVisible( controlId == 120 )
        xbmc.sleep( 5 )
        self.setFocus( self.getControl( controlId ) )

    def show_lyrics(self, lyrics):
        WIN.setProperty('culrc.lyrics', lyrics.lyrics)
        WIN.setProperty('culrc.source', lyrics.source)
        if lyrics.list:
            source = '%s (%d)' % (lyrics.source, len(lyrics.list))
        else:
            source = lyrics.source
        self.getControl( 200 ).setLabel( source )
        if lyrics.lrc:
            self.parser_lyrics( lyrics.lyrics )
            for time, line in self.pOverlay:
                listitem = xbmcgui.ListItem(line)
                listitem.setProperty('time', str(time))
                self.getControl( 110 ).addItem( listitem )
        else:
            splitLyrics = lyrics.lyrics.splitlines()
            for x in splitLyrics:
               self.getControl( 110 ).addItem( x )
        self.getControl( 110 ).selectItem( 0 )
        self.show_control( 110 )
        if lyrics.lrc:
            if (self.allowtimer and self.getControl( 110 ).size() > 1):
                self.refresh()

    def parser_lyrics(self, lyrics):
        self.pOverlay = []
        tag = re.compile('\[(\d+):(\d\d)([\.:]\d+|)\]')
        lyrics = lyrics.replace( "\r\n" , "\n" )
        sep = "\n"
        for x in lyrics.split( sep ):
            match1 = tag.match( x )
            times = []
            if ( match1 ):
                while ( match1 ):
                    times.append( float(match1.group(1)) * 60 + float(match1.group(2)) )
                    y = 5 + len(match1.group(1)) + len(match1.group(3))
                    x = x[y:]
                    match1 = tag.match( x )
                for time in times:
                    self.pOverlay.append( (time, x) )
        self.pOverlay.sort( cmp=lambda x,y: cmp(x[0], y[0]) )

    def prepare_list(self, list):
        listitems = []
        for song in list:
            listitem = xbmcgui.ListItem(song[0])
            listitem.setProperty('lyric', str(song))
            listitem.setProperty('source', lyrics.source)
            listitems.append(listitem)
        self.getControl( 120 ).addItems( listitems )

    def reshow_choices(self):
        if self.getControl( 120 ).size() > 1:
            self.getControl( 120 ).selectItem( 0 )
            self.stop_refresh()
            self.show_control( 120 )
            while not self.selected:
                xbmc.sleep(50)
            self.selected = False
            self.getControl( 110 ).reset()
            self.show_lyrics( self.lyrics )
#           self.save_lyrics_to_file( self.lyrics ) #FIXME

    def reset_controls(self):
        self.getControl( 110 ).reset()
        self.getControl( 200 ).setLabel('')
        WIN.clearProperty('culrc.lyrics')
        WIN.clearProperty('culrc.source')

    def exit_gui(self, action):
        # in manual mode, we also need to quit the script when the user cancels the gui or music has ended
        if (self.mode == 'manual') and (action == 'quit'):
            # signal the main loop to quit
            WIN.setProperty('culrc.quit', 'TRUE')
        self.allowtimer = False
        self.stop_refresh()
        self.showgui = False
        self.close()

    def onClick(self, controlId):
        if ( controlId == 110 ):
            # will only works for lrc based lyrics
            try:
                item = self.getControl( 110 ).getSelectedItem()
                stamp = float(item.getProperty('time'))
                xbmc.Player().seekTime(stamp)
            except:
                pass
        if ( controlId == 120 ):
            item = self.getControl( 120 ).getSelectedItem()
            source = item.getProperty('source').lower()
            lyric = eval(item.getProperty('lyric'))
            exec ( "from culrcscrapers.%s import lyricsScraper as lyricsScraper_%s" % (source, source))
            scraper = eval('lyricsScraper_%s.LyricsFetcher()' % source)
            self.lyrics.lyrics = scraper.get_lyrics_from_list( lyric )
            self.selected = True

    def onFocus(self, controlId):
        self.controlId = controlId

    def onAction(self, action):
        actionId = action.getId()
        if ( actionId in CANCEL_DIALOG ):
            # dialog cancelled, close the gui
            self.exit_gui('quit')
        elif ( actionId == 101 ) or ( actionId == 117 ): # ACTION_MOUSE_RIGHT_CLICK / ACTION_CONTEXT_MENU
            self.reshow_choices()
        elif ( actionId in ACTION_OSD ):
            xbmc.executebuiltin("ActivateWindow(10120)")
        elif ( actionId in ACTION_CODEC ):
            xbmc.executebuiltin("Action(codecinfo)")

class MyPlayer(xbmc.Player):
    def __init__(self, *args, **kwargs):
        xbmc.Player.__init__(self)
        self.function = kwargs["function"]
        self.clear = kwargs["clear"]

    def onPlayBackStarted(self):
        self.clear()
        if xbmc.getCondVisibility("Window.IsVisible(12006)"):
            self.function()

    def onPlayBackStopped(self):
        self.clear()

class MyMonitor(xbmc.Monitor):
    def __init__(self, *args, **kwargs):
        xbmc.Monitor.__init__(self)
        self.function = kwargs["function"]

    def onSettingsChanged(self):
        # sleep before retrieving the new settings
        xbmc.sleep(500)
        self.function()
