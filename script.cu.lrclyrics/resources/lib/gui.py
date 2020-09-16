#-*- coding: UTF-8 -*-
import sys
import os
import re
import time
import threading
import xbmc
import xbmcgui
import xbmcvfs
from threading import Timer
from utilities import *
from embedlrc import *

CWD = sys.modules['__main__'].CWD
ADDON = sys.modules['__main__'].ADDON
ADDONNAME = sys.modules['__main__'].ADDONNAME
PROFILE = sys.modules['__main__'].PROFILE
LANGUAGE = sys.modules['__main__'].LANGUAGE

class MAIN():
    def __init__(self, *args, **kwargs):
        self.mode = kwargs['mode']
        self.setup_main()
        WIN.setProperty('culrc.running', 'true')
        self.get_scraper_list()
        if (ADDON.getSetting('save_lyrics_path') == ''):
            ADDON.setSetting(id='save_lyrics_path', value=os.path.join(PROFILE.encode('utf-8'), 'lyrics'))
        self.main_loop()
        self.cleanup_main()

    def setup_main(self):
        self.fetchedLyrics = []
        self.current_lyrics = Lyrics()
        self.MyPlayer = MyPlayer(function=self.myPlayerChanged, clear=self.clear)
        self.Monitor = MyMonitor(function=self.update_settings)
        self.customtimer = False
        self.starttime = 0

    def cleanup_main(self):
        # Clean up the monitor and Player classes on exit
        del self.MyPlayer
        del self.Monitor

    def get_scraper_list(self):
        self.scrapers = []
        for scraper in os.listdir(LYRIC_SCRAPER_DIR):
            if os.path.isdir(os.path.join(LYRIC_SCRAPER_DIR, scraper)) and ADDON.getSetting(scraper) == 'true':
                exec ('from culrcscrapers.%s import lyricsScraper as lyricsScraper_%s' % (scraper, scraper))
                exec ('self.scrapers.append([lyricsScraper_%s.__priority__,lyricsScraper_%s.LyricsFetcher(),lyricsScraper_%s.__title__,lyricsScraper_%s.__lrc__])' % (scraper, scraper, scraper, scraper))
        self.scrapers.sort()

    def main_loop(self):
        self.triggered = False
        # main loop
        while (not self.Monitor.abortRequested()) and (WIN.getProperty('culrc.quit') == ''):
            # Check if there is a manual override request
            if WIN.getProperty('culrc.manual') == 'true':
                WIN.clearProperty('culrc.manual')
                log('searching for manually defined lyrics')
                self.get_manual_lyrics()
            # check if we are on the music visualization screen
            # do not try and get lyrics for any background media
            elif xbmc.getCondVisibility('Window.IsVisible(12006)') and xbmcgui.Window(10025).getProperty('PlayingBackgroundMedia') in [None, '']:
                if not self.triggered:
                    self.triggered = True
                    # notify user the script is searching for lyrics
                    if ADDON.getSetting('silent') == 'false':
                        dialog = xbmcgui.Dialog()
                        dialog.notification(ADDONNAME, LANGUAGE(32004), time=2000, sound=False)
                    # start fetching lyrics
                    self.myPlayerChanged()
                elif WIN.getProperty('culrc.force') == 'TRUE':
                    # we're already running, user clicked button on osd
                    WIN.setProperty('culrc.force','FALSE')
                    self.current_lyrics = Lyrics()
                    self.myPlayerChanged()
                elif xbmc.getCondVisibility('Player.IsInternetStream'):
                    self.myPlayerChanged()
            else:
                # we may have exited the music visualization screen
                self.triggered = False
                # reset current lyrics so we show them again when re-entering the visualization screen
                self.current_lyrics = Lyrics()
            xbmc.sleep(100)
        WIN.clearProperty('culrc.quit')
        WIN.clearProperty('culrc.lyrics')
        WIN.clearProperty('culrc.islrc')
        WIN.clearProperty('culrc.source')
        WIN.clearProperty('culrc.haslist')
        WIN.clearProperty('culrc.running')

    def get_lyrics(self, song):
        log('searching memory for lyrics')
        lyrics = self.get_lyrics_from_memory(song)
        if lyrics:
            if lyrics.lyrics:
                log('found lyrics in memory')
                return lyrics
        if song.title and xbmc.getCondVisibility('Window.IsVisible(12006)'):
            lyrics = self.find_lyrics(song)
            if lyrics.lyrics and ADDON.getSetting('strip') == 'true':
                if isinstance (lyrics.lyrics,str):
                    fulltext = lyrics.lyrics.decode('utf-8')
                else:
                    fulltext = lyrics.lyrics
                strip_k1 = re.sub(ur'[\u1100-\u11ff]+', '', fulltext)
                strip_k2 = re.sub(ur'[\uAC00-\uD7A3]+', '', strip_k1)
                strip_c = re.sub(ur'[\u3000-\u9fff]+', '', strip_k2)
                lyrics.lyrics = strip_c.encode('utf-8').replace('：',':') #replace fullwith colon (not present in many font files)
        # no song title, we can't search online. try matching local filename
        elif (ADDON.getSetting('save_lyrics2') == 'true') and xbmc.getCondVisibility('Window.IsVisible(12006)'):
            lyrics = self.get_lyrics_from_file(song, True)
            if not lyrics:
                lyrics = self.get_lyrics_from_file(song, False)
        if not lyrics:
            lyrics = Lyrics()
            lyrics.song = song
            lyrics.source = ''
            lyrics.lyrics = ''
        if xbmc.getCondVisibility('Window.IsVisible(12006)'):
            self.save_lyrics_to_memory(lyrics)
        return lyrics

    def find_lyrics(self, song):
        # search embedded lrc lyrics
        ext = os.path.splitext(song.filepath.decode('utf-8'))[1].lower()
        sup_ext = ['.mp3', '.flac']
        if (ADDON.getSetting('search_embedded') == 'true') and song.analyze_safe and (ext in sup_ext) and xbmc.getCondVisibility('Window.IsVisible(12006)'):
            log('searching for embedded lrc lyrics')
            try:
                lyrics = getEmbedLyrics(song, True)
            except:
                lyrics = None
            if (lyrics):
                log('found embedded lrc lyrics')
                return lyrics
        # search lrc lyrics from file
        if (ADDON.getSetting('search_file') == 'true') and xbmc.getCondVisibility('Window.IsVisible(12006)'):
            lyrics = self.get_lyrics_from_file(song, True)
            if (lyrics):
                log('found lrc lyrics from file')
                return lyrics
        # search lrc lyrics by scrapers
        for scraper in self.scrapers:
            if scraper[3] and xbmc.getCondVisibility('Window.IsVisible(12006)'):
                lyrics = scraper[1].get_lyrics(song)
                if (lyrics):
                    log('found lrc lyrics online')
                    self.save_lyrics_to_file(lyrics)
                    return lyrics
        # search embedded txt lyrics
        if (ADDON.getSetting('search_embedded') == 'true' and song.analyze_safe) and xbmc.getCondVisibility('Window.IsVisible(12006)'):
            log('searching for embedded txt lyrics')
            try:
                lyrics = getEmbedLyrics(song, False)
            except:
                lyrics = None
            if lyrics:
                log('found embedded txt lyrics')
                return lyrics
        # search txt lyrics from file
        if (ADDON.getSetting('search_file') == 'true') and xbmc.getCondVisibility('Window.IsVisible(12006)'):
            lyrics = self.get_lyrics_from_file(song, False)
            if (lyrics):
                log('found txt lyrics from file')
                return lyrics
        # search txt lyrics by scrapers
        for scraper in self.scrapers:
            if not scraper[3] and xbmc.getCondVisibility('Window.IsVisible(12006)'):
                lyrics = scraper[1].get_lyrics(song)
                if (lyrics):
                    log('found txt lyrics online')
                    self.save_lyrics_to_file(lyrics)
                    return lyrics
        log('no lyrics found')
        lyrics = Lyrics()
        lyrics.song = song
        lyrics.source = ''
        lyrics.lyrics = ''
        return lyrics

    def get_lyrics_from_memory(self, song):
        for l in self.fetchedLyrics:
            if (l.song == song):
                return l
        return None

    def get_lyrics_from_file(self, song, getlrc):
        log('searching files for lyrics')
        lyrics = Lyrics()
        lyrics.song = song
        lyrics.source = LANGUAGE(32000)
        lyrics.lrc = getlrc
        if ADDON.getSetting('save_lyrics1') == 'true':
            # Search save path by Cu LRC Lyrics
            lyricsfile = song.path1(getlrc)
            if xbmcvfs.exists(lyricsfile):
                lyr = get_textfile(lyricsfile)
                if lyr != None:
                    lyrics.lyrics = lyr
                    return lyrics
        if ADDON.getSetting('save_lyrics2') == 'true':
            # Search same path with song file
            lyricsfile = song.path2(getlrc)
            if xbmcvfs.exists(lyricsfile):
                lyr = get_textfile(lyricsfile)
                if lyr != None:
                    lyrics.lyrics = lyr
                    return lyrics
        return None

    def save_lyrics_to_memory(self, lyrics):
        savedLyrics = self.get_lyrics_from_memory(lyrics.song)
        if (savedLyrics is None):
            self.fetchedLyrics.append(lyrics)
            self.fetchedLyrics = self.fetchedLyrics[-10:]

    def save_lyrics_to_file(self, lyrics, adjust=None):
        if isinstance (lyrics.lyrics, str):
            lyr = lyrics.lyrics
        else:
            lyr = lyrics.lyrics.encode('utf-8')
        if adjust:
            # save our manual sync offset to file
            adjust = int(adjust * 1000)
            # check if there's an existing offset tag
            found = re.search('\[offset:(.*?)\]', lyr, flags=re.DOTALL)
            if found:
                # get the sum of both values
                try:
                    adjust = int(found.group(1)) + adjust
                except:
                    # offset tag without value
                    pass
                # remove the existing offset tag
                lyr = lyr.replace(found.group(0) + '\n','')
            # write our new offset tag
            lyr = '[offset:%i]\n' % adjust + lyr
        if (ADDON.getSetting('save_lyrics1') == 'true'):
            file_path = lyrics.song.path1(lyrics.lrc)
            success = self.write_lyrics_file(file_path, lyr)
        if (ADDON.getSetting('save_lyrics2') == 'true'):
            file_path = lyrics.song.path2(lyrics.lrc)
            success = self.write_lyrics_file(file_path, lyr)

    def write_lyrics_file(self, path, data):
        try:
            if (not xbmcvfs.exists(os.path.dirname(path))):
                xbmcvfs.mkdirs(os.path.dirname(path))
            lyrics_file = xbmcvfs.File(path, 'w')
            lyrics_file.write(data)
            lyrics_file.close()
            return True
        except:
            log('failed to save lyrics')
            return False

    def remove_lyrics_from_memory(self, lyrics):
        # delete lyrics from memory
        if lyrics in self.fetchedLyrics:
            self.fetchedLyrics.remove(lyrics)

    def delete_lyrics(self, lyrics):
        # delete lyrics from memory
        self.remove_lyrics_from_memory(lyrics)
        # delete saved lyrics
        if (ADDON.getSetting('save_lyrics1') == 'true'):
            file_path = lyrics.song.path1(lyrics.lrc)
            success = self.delete_file(file_path)
        if (ADDON.getSetting('save_lyrics2') == 'true'):
            file_path = lyrics.song.path2(lyrics.lrc)
            success = self.delete_file(file_path)

    def delete_file(self, path):
        try:
            xbmcvfs.delete(path)
            return True
        except:
            log('failed to delete file')
            return False

    def myPlayerChanged(self):
        global lyrics
        songchanged = False
        for cnt in range(5):
            song = Song.current()
            if (song and (self.current_lyrics.song != song)):
                songchanged = True
                if xbmc.getCondVisibility('Player.IsInternetStream') and not xbmc.getInfoLabel('MusicPlayer.TimeRemaining'):
                    # internet stream that does not provide time, we need our own timer to sync lrc lyrics
                    self.starttime = time.time()
                    self.customtimer = True
                else:
                    self.customtimer = False
                log('Current Song: %s - %s' % (song.artist, song.title))
                lyrics = self.get_lyrics(song)
                self.current_lyrics = lyrics
                if lyrics.lyrics:
                    # signal the gui thread to display the next lyrics
                    WIN.setProperty('culrc.newlyrics', 'TRUE')
                    # double-check if we're still on the visualisation screen and check if gui is already running
                    if xbmc.getCondVisibility('Window.IsVisible(12006)') and not WIN.getProperty('culrc.guirunning') == 'TRUE':
                        WIN.setProperty('culrc.guirunning', 'TRUE')
                        gui = guiThread(mode=self.mode, save=self.save_lyrics_to_file, remove=self.remove_lyrics_from_memory, delete=self.delete_lyrics, function=self.return_time, monitor=self.Monitor)
                        gui.start()
                else:
                    # signal gui thread to exit
                    WIN.setProperty('culrc.nolyrics', 'TRUE')
                    # notify user no lyrics were found
                    if ADDON.getSetting('silent') == 'false':
                        dialog = xbmcgui.Dialog()
                        dialog.notification(ADDONNAME + ': ' + LANGUAGE(32001), song.artist + ' - ' + song.title, time=2000, sound=False)
                break
            xbmc.sleep(50)
        # only search for next lyrics if current song has changed
        if xbmc.getCondVisibility('MusicPlayer.HasNext') and songchanged:
            next_song = Song.next()
            if next_song:
                log('Next Song: %s - %s' % (next_song.artist, next_song.title))
                self.get_lyrics(next_song)
            else:
                log('Missing Artist or Song name in ID3 tag for next track')

    def get_manual_lyrics(self):
        # Read the manually defined artist and track
        artist = WIN.getProperty('culrc.artist')
        track = WIN.getProperty('culrc.track')
        # Make sure we have both an artist and track name
        if artist and track:
            song = Song(artist, track)
            if (song and (self.current_lyrics.song != song)):
                log('Current Song: %s - %s' % (song.artist, song.title))
                lyrics = self.get_lyrics(song)
                self.current_lyrics = lyrics
                if lyrics.lyrics:
                    # Store the details of the lyrics
                    WIN.setProperty('culrc.newlyrics', 'TRUE')
                    WIN.setProperty('culrc.lyrics', lyrics.lyrics)
                    WIN.setProperty('culrc.source', lyrics.source)

    def update_settings(self):
        self.get_scraper_list()
        service = ADDON.getSetting('service')
        if service == 'true':
            self.mode = 'service'
        else:
            self.mode = 'manual'
            # quit the script is mode was changed from service to manual
            WIN.setProperty('culrc.quit', 'TRUE')

    def clear(self):
        WIN.clearProperty('culrc.lyrics')
        WIN.clearProperty('culrc.islrc')
        WIN.clearProperty('culrc.source')
        WIN.clearProperty('culrc.haslist')

    def return_time(self):
        return self.customtimer, self.starttime


class guiThread(threading.Thread):
    def __init__(self, *args, **kwargs):
        threading.Thread.__init__(self)
        self.mode = kwargs['mode']
        self.save = kwargs['save']
        self.remove = kwargs['remove']
        self.delete = kwargs['delete']
        self.function = kwargs['function']
        self.Monitor = kwargs['monitor']

    def run(self):
        ui = GUI('script-cu-lrclyrics-main.xml', CWD, 'Default', mode=self.mode, save=self.save, remove=self.remove, delete=self.delete, function=self.function, monitor=self.Monitor)
        ui.doModal()
        del ui
        WIN.clearProperty('culrc.guirunning')

class syncThread(threading.Thread):
    def __init__(self, *args, **kwargs):
        threading.Thread.__init__(self)
        self.function = kwargs['function']
        self.adjust = kwargs['adjust']
        self.save = kwargs['save']
        self.remove = kwargs['remove']
        self.lyrics = kwargs['lyrics']

    def run(self):
        import sync
        dialog = sync.GUI('DialogSlider.xml' , CWD, 'Default', offset=self.adjust, function=self.function)
        dialog.doModal()
        adjust = dialog.val
        del dialog
        self.save(self.lyrics, adjust)
        # file has changed, remove it from memory
        self.remove(self.lyrics)

class GUI(xbmcgui.WindowXMLDialog):
    def __init__(self, *args, **kwargs):
        xbmcgui.WindowXMLDialog.__init__(self)
        self.mode = kwargs['mode']
        self.save = kwargs['save']
        self.remove = kwargs['remove']
        self.delete = kwargs['delete']
        self.function = kwargs['function']
        self.Monitor = kwargs['monitor']
       
    def onInit(self):
        self.matchlist = ['@', 'www\.(.*?)\.(.*?)', 'QQ(.*?)[1-9]', 'artist ?: ?.', 'album ?: ?.', 'title ?: ?.', 'song ?: ?.', 'by ?: ?.']
        self.text = self.getControl(110)
        self.list = self.getControl(120)
        self.label = self.getControl(200)
        self.list.setVisible(False)
        self.offset = float(ADDON.getSetting('offset'))
        self.setup_gui()
        self.process_lyrics()
        self.gui_loop()

    def process_lyrics(self):
        global lyrics
        self.syncadjust = 0.0
        self.lyrics = lyrics
        self.stop_refresh()
        self.reset_controls()
        if self.lyrics.lyrics:
            self.show_lyrics(self.lyrics)
        else:
            WIN.setProperty('culrc.lyrics', LANGUAGE(32001))
            WIN.clearProperty('culrc.islrc')
        self.list.reset()
        if self.lyrics.list:
            WIN.setProperty('culrc.haslist', 'true')
            self.prepare_list(self.lyrics.list)
        else:
            WIN.clearProperty('culrc.haslist')

    def gui_loop(self):
        # gui loop
        while self.showgui and (not self.Monitor.abortRequested()) and xbmc.Player().isPlayingAudio():
            # check if we have new lyrics
            if WIN.getProperty('culrc.newlyrics') == 'TRUE':
                WIN.clearProperty('culrc.newlyrics')
                # show new lyrics
                self.process_lyrics()
            # check if we have no lyrics
            elif WIN.getProperty('culrc.nolyrics') == 'TRUE':
                # no lyrics, close the gui
                self.exit_gui('close')
            elif not xbmc.getCondVisibility('Window.IsVisible(12006)'):
                # we're not on the visualisation screen anymore
                self.exit_gui('quit')
            xbmc.sleep(100)
        # music ended, close the gui
        if (not xbmc.Player().isPlayingAudio()):
            self.exit_gui('quit')
        # xbmc quits, close the gui 
        elif self.Monitor.abortRequested():
            self.exit_gui('quit')

    def setup_gui(self):
        WIN.clearProperty('culrc.newlyrics')
        WIN.clearProperty('culrc.nolyrics')
        WIN.clearProperty('culrc.haslist')
#        self.lock = threading.Lock()
        self.timer = None
        self.allowtimer = True
        self.refreshing = False
        self.blockOSD = False
        self.controlId = -1
        self.pOverlay = []
        self.scroll_line = int(self.get_page_lines() / 2)
        self.showgui = True
        self.selecteditem = 0

    def get_page_lines(self):
        # we need to close the OSD else we can't get control 110
        self.blockOSD = True
        if xbmc.getCondVisibility('Window.IsVisible(musicosd)'):
            xbmc.executebuiltin('Dialog.Close(musicosd,true)')
        self.text.setVisible(False)
        # numpages returns a string, make sure it's not empty
        while xbmc.getInfoLabel('Container(110).NumPages') and (int(xbmc.getInfoLabel('Container(110).NumPages')) < 2) and (not self.Monitor.abortRequested()):
            listitem = xbmcgui.ListItem(offscreen=True)
            self.text.addItem(listitem)
            xbmc.sleep(50)
        lines = self.text.size() - 1
        self.blockOSD = False
        return lines

    def refresh(self):
#        self.lock.acquire()
        #Maybe Kodi is not playing any media file
        try:
            customtimer, starttime = self.function()
            if customtimer:
                cur_time = time.time() - starttime
            else:
                cur_time = xbmc.Player().getTime()
            nums = self.text.size()
            pos = self.text.getSelectedPosition()
            if (cur_time < (self.pOverlay[pos][0] - self.syncadjust)):
                while (pos > 0 and (self.pOverlay[pos - 1][0] - self.syncadjust) > cur_time):
                    pos = pos -1
            else:
                while (pos < nums - 1 and (self.pOverlay[pos + 1][0] - self.syncadjust) < cur_time):
                    pos = pos +1
                if (pos + self.scroll_line > nums - 1):
                    self.text.selectItem(nums - 1)
                else:
                    self.text.selectItem(pos + self.scroll_line)
            self.text.selectItem(pos)
            self.setFocus(self.text)
            if (self.allowtimer and cur_time < (self.pOverlay[nums - 1][0] - self.syncadjust)):
                waittime = (self.pOverlay[pos + 1][0] - self.syncadjust) - cur_time
                self.timer = Timer(waittime, self.refresh)
                self.refreshing = True
                self.timer.start()
            else:
                self.refreshing = False
#            self.lock.release()
        except:
            pass
#            self.lock.release()

    def stop_refresh(self):
#        self.lock.acquire()
        try:
            self.timer.cancel()
        except:
            pass
        self.refreshing = False
#        self.lock.release()

    def show_control(self, controlId):
        self.text.setVisible(controlId == 110)
        self.list.setVisible(controlId == 120)
        xbmc.sleep(5)
        self.setFocus(self.getControl(controlId))

    def show_lyrics(self, lyrics):
        WIN.setProperty('culrc.lyrics', lyrics.lyrics)
        WIN.setProperty('culrc.source', lyrics.source)
        if lyrics.list:
            source = '%s (%d)' % (lyrics.source, len(lyrics.list))
        else:
            source = lyrics.source
        self.label.setLabel(source)
        if lyrics.lrc:
            WIN.setProperty('culrc.islrc', 'true')
            self.parser_lyrics(lyrics.lyrics)
            for num, (time, line) in enumerate(self.pOverlay):
                parts = self.get_parts(line)
                listitem = xbmcgui.ListItem(line, offscreen=True)
                for count, item in enumerate(parts):
                    listitem.setProperty('part%i' % (count + 1), item)
                delta = 100000 # in case duration of the last line is undefined
                if num < len(self.pOverlay) - 1:
                    delta = (self.pOverlay[num+1][0] - time) * 1000
                listitem.setProperty('duration', str(int(delta)))
                listitem.setProperty('time', str(time))
                self.text.addItem(listitem)
        else:
            WIN.clearProperty('culrc.islrc')
            splitLyrics = lyrics.lyrics.splitlines()
            for line in splitLyrics:
                parts = self.get_parts(line)
                listitem = xbmcgui.ListItem(line, offscreen=True)
                for count, item in enumerate(parts):
                    listitem.setProperty('part%i' % (count + 1), item)
                self.text.addItem(listitem)
        self.text.selectItem(0)
        self.show_control(110)
        if lyrics.lrc:
            if (self.allowtimer and self.text.size() > 1):
                self.refresh()

    def match_pattern(self, line):
        for item in self.matchlist:
            match = re.search(item, line, flags=re.IGNORECASE)
            if match:
                return True

    def get_parts(self, line):
        result = ['', '', '', '']
        parts = line.split(' ', 3)
        for count, item in enumerate(parts):
            result[count] = item
        return result

    def parser_lyrics(self, lyrics):
        offset = 0.00
        found = re.search('\[offset:\s?(-?\d+)\]', lyrics)
        if found:
            offset = float(found.group(1)) / 1000
        self.pOverlay = []
        tag1 = re.compile('\[(\d+):(\d\d)[\.:](\d\d)\]')
        tag2 = re.compile('\[(\d+):(\d\d)([\.:]\d+|)\]')
        lyrics = lyrics.replace('\r\n' , '\n')
        sep = '\n'
        for x in lyrics.split(sep):
            if self.match_pattern(x):
                continue
            match1 = tag1.match(x)
            match2 = tag2.match(x)
            times = []
            if (match1):
                while (match1): # [xx:yy.zz]
                    times.append(float(match1.group(1)) * 60 + float(match1.group(2)) + (float(match1.group(3))/100) + self.offset - offset)
                    y = 6 + len(match1.group(1)) + len(match1.group(3))
                    x = x[y:]
                    match1 = tag1.match(x)
                for time in times:
                    self.pOverlay.append((time, x))
            elif (match2): # [xx:yy]
                while (match2):
                    times.append(float(match2.group(1)) * 60 + float(match2.group(2)) + self.offset - offset)
                    y = 5 + len(match2.group(1)) + len(match2.group(3))
                    x = x[y:]
                    match2 = tag2.match(x)
                for time in times:
                    self.pOverlay.append((time, x))
        self.pOverlay.sort(cmp=lambda x,y: cmp(x[0], y[0]))
        # don't display/focus the first line from the start of the song
        self.pOverlay.insert(0, (00.00, ''))
        if ADDON.getSetting('strip') == 'true':
            poplist = []
            prev_time = []
            prev_line = ''
            for num, (time, line) in enumerate(self.pOverlay):
                if time == prev_time:
                    if len(line) > len(prev_line):
                        poplist.append(num - 1)
                    else:
                        poplist.append(num)
                prev_time = time
                prev_line = line
            for i in reversed(poplist):
                self.pOverlay.pop(i)

    def prepare_list(self, list):
        listitems = []
        for song in list:
            listitem = xbmcgui.ListItem(song[0], offscreen=True)
            listitem.setProperty('lyric', str(song))
            listitem.setProperty('source', lyrics.source)
            listitems.append(listitem)
        self.list.addItems(listitems)

    def reshow_choices(self):
        if self.list.size() > 1:
            self.list.selectItem(0)
            self.list.getListItem(self.selecteditem).select(True)
            self.stop_refresh()
            self.show_control(120)

    def set_synctime(self, adjust):
        self.syncadjust = adjust

    def context_menu(self):
        labels = ()
        functions = ()
        if self.list.size() > 1:
            labels += (LANGUAGE(32006),)
            functions += ('select',)
        if WIN.getProperty('culrc.islrc') == 'true':
            labels += (LANGUAGE(32007),)
            functions += ('sync',)
        if lyrics.source != LANGUAGE(32002):
            labels += (LANGUAGE(32167),)
            functions += ('delete',)
        if labels:
            selection = xbmcgui.Dialog().contextmenu(labels)
            if selection >= 0:
                if functions[selection] == 'select':
                    self.reshow_choices()
                elif functions[selection] == 'sync':
                    sync = syncThread(adjust=self.syncadjust, function=self.set_synctime, save=self.save, lyrics=self.lyrics, remove=self.remove)
                    sync.start()
                elif functions[selection] == 'delete':
                    self.lyrics.lyrics = ''
                    self.reset_controls()
                    WIN.setProperty('culrc.nolyrics', 'TRUE')
                    self.delete(self.lyrics)

    def reset_controls(self):
        self.text.reset()
        self.label.setLabel('')
        WIN.clearProperty('culrc.lyrics')
        WIN.clearProperty('culrc.islrc')
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
        if (controlId == 110):
            # will only works for lrc based lyrics
            try:
                item = self.text.getSelectedItem()
                stamp = float(item.getProperty('time'))
                xbmc.Player().seekTime(stamp)
            except:
                pass
        if (controlId == 120):
            self.list.getListItem(self.selecteditem).select(False)
            self.selecteditem = self.list.getSelectedPosition()
            self.list.getListItem(self.selecteditem).select(True)
            item = self.list.getSelectedItem()
            source = item.getProperty('source').lower()
            lyric = eval(item.getProperty('lyric'))
            exec ('from culrcscrapers.%s import lyricsScraper as lyricsScraper_%s' % (source, source))
            scraper = eval('lyricsScraper_%s.LyricsFetcher()' % source)
            self.lyrics.lyrics = scraper.get_lyrics_from_list(lyric)
            self.text.reset()
            self.show_lyrics(self.lyrics)
            self.save(self.lyrics)

    def onFocus(self, controlId):
        self.controlId = controlId

    def onAction(self, action):
        actionId = action.getId()
        if (actionId in CANCEL_DIALOG):
            if xbmc.getCondVisibility('Control.IsVisible(120)'):
                self.show_control(110)
            else:
                # dialog cancelled, close the gui
                self.exit_gui('quit')
        elif (actionId == 101) or (actionId == 117): # ACTION_MOUSE_RIGHT_CLICK / ACTION_CONTEXT_MENU
            self.context_menu()
        elif (actionId in ACTION_OSD):
            if not self.blockOSD:
                xbmc.executebuiltin('ActivateWindow(10120)')
        elif (actionId in ACTION_CODEC):
            xbmc.executebuiltin('Action(PlayerProcessInfo)')

class MyPlayer(xbmc.Player):
    def __init__(self, *args, **kwargs):
        xbmc.Player.__init__(self)
        self.function = kwargs['function']
        self.clear = kwargs['clear']

    def onAVStarted(self):
        self.clear()
        if xbmc.getCondVisibility('Window.IsVisible(12006)'):
            self.function()

    def onPlayBackStopped(self):
        self.clear()

    def onPlayBackEnded(self):
        self.clear()

class MyMonitor(xbmc.Monitor):
    def __init__(self, *args, **kwargs):
        xbmc.Monitor.__init__(self)
        self.function = kwargs['function']

    def onSettingsChanged(self):
        # sleep before retrieving the new settings
        xbmc.sleep(500)
        self.function()
