#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import re
import sys
import threading
import xbmc, xbmcaddon

__addon__         = xbmcaddon.Addon()
__addonid__       = __addon__.getAddonInfo('id')
__cwd__           = __addon__.getAddonInfo('path')
__icon__          = __addon__.getAddonInfo("icon")
__scriptname__    = __addon__.getAddonInfo('name')
__version__       = __addon__.getAddonInfo('version')
__language__      = __addon__.getLocalizedString
__resource_path__ = os.path.join(__cwd__, 'resources', 'lib')
__resource__      = xbmc.translatePath(__resource_path__).decode('utf-8')
__datapath__      = os.path.join(xbmc.translatePath('special://masterprofile/addon_data/').decode('utf-8'), __addonid__)

DB_CACHE_TVDB_IDS = 'cache.tvdb.ids.db'

__nextAired__     = False

if __addon__.getSetting('tvsna-enabled'):
    try:
        __nextAired__     = xbmcaddon.Addon(id='script.tv.show.next.aired')
        addon_path = __nextAired__.getAddonInfo('path')
        sys.path.append (xbmc.translatePath( os.path.join(addon_path) ))
        sys.path = [xbmc.translatePath( os.path.join(addon_path, 'resources', 'lib') )] + sys.path

        from default import NextAired
        import xbmcvfs, xbmcgui
    except:
        __nextAired__     = False

from resources.lib.myepisodecalendar import MyEpisodeCalendar

class Monitor(xbmc.Monitor):
    def __init__( self, *args, **kwargs ):
        xbmc.Monitor.__init__( self )
        self.action = kwargs['action']

    def onSettingsChanged( self ):
        log('#DEBUG# onSettingsChanged')
        # remove shows added by plugin when integration is disabled
        if __nextAired__ and __addon__.getSetting('tvsna-enabled') == 'false':
            __nextAired__.setSetting("ExtraShows", re.sub(r"\D?mec\d+", '', __nextAired__.getSetting("ExtraShows")))
        self.action()

class Player(xbmc.Player):

    def __init__ (self):
        xbmc.Player.__init__(self)
        log('Player - init')
        self.mye = self._loginMyEpisodeCalendar()
        if not self.mye.is_logged:
            return
        self.showid = self.episode = self.title = self.season = None
        self._totalTime = 999999
        self._lastPos = 0
        self._min_percent = int(__addon__.getSetting('watched-percent'))
        self._tracker = None
        self._playbackLock = threading.Event()
        self._monitor = Monitor(action = self._reset)

    def _reset(self):
        self._tearDown()
        if self.mye:
            del self.mye
        self.__init__()

    def _trackPosition(self):
        while self._playbackLock.isSet() and not xbmc.abortRequested:
            try:
                self._lastPos = self.getTime()
            except:
                self._playbackLock.clear()
            log('Inside Player. Tracker time = %s' % self._lastPos)
            xbmc.sleep(250)
        log('Position tracker ending with lastPos = %s' % self._lastPos)

    def _setUp(self):
        self._playbackLock.set()
        self._tracker = threading.Thread(target=self._trackPosition)

    def _tearDown(self):
        if hasattr(self, '_playbackLock'):
            self._playbackLock.clear()
        self._monitor = None
        if not hasattr(self, '_tracker'):
            return
        if self._tracker is None:
            return
        if self._tracker.isAlive():
            self._tracker.join()
        self._tracker = None

    @staticmethod
    def _loginMyEpisodeCalendar(silent=False):
        username = __addon__.getSetting('Username')
        password = __addon__.getSetting('Password')

        login_notif = __language__(32912)
        if username is "" or password is "":
            notif(login_notif, time=2500)
            return None

        showLoginNotif = True
        mye = MyEpisodeCalendar(username, password)
        if mye.is_logged:
            if __addon__.getSetting('showNotif-login') != "true" or silent:
                showLoginNotif = False

            login_notif = "%s %s" % (username, __language__(32911))

        if showLoginNotif is True:
            notif(login_notif, time=2500)

        if mye.is_logged and (not mye.get_show_list()):
            notif(__language__(32927), time=2500)

        if (not silent and __addon__.getSetting('tvsna-enabled') != "false"):
            if(__nextAired__):
                log('script.tv.show.next.aired is available')

                changedCount = 0
                if __addon__.getSetting('tvsna-onstartup') != "false":
                    changedCount = addShowsToTSNA(mye, silent=True)

                    if (changedCount > 0):
                        xbmc.executebuiltin("XBMC.RunScript(script.tv.show.next.aired,force=True)")
                    elif __addon__.getSetting('tvsna-showgui') != "false":
                        xbmc.executebuiltin("XBMC.RunScript(script.tv.show.next.aired)")
            else:
                log('script.tv.show.next.aired is NOT available')

        return mye

    def _mecReCheckAuth(self):
        if (not self.mye.is_logged):
            log("not logged in anymore")
            login_notif = __language__(32912)
            notif(login_notif, time=2500)
            return False
        return True

    def _addShow(self):
        # Add the show if it's not already in our account
        if self.showid in self.mye.shows.values():
            if __addon__.getSetting('showNotif-found') == "true":
                notif(self.title, time=2000)
            return
        was_added = self.mye.add_show(self.showid)
        added = 32926

        showAddNotif = True
        if was_added:
            if __addon__.getSetting('showNotif-autoadd') != "true":
                showAddNotif = False
            added = 32925
        
        if showAddNotif is True:
            notif("%s %s" % (self.title, __language__(32925)))

    def onPlayBackStarted(self):
        self._setUp()
        self._totalTime = self.getTotalTime()
        self._tracker.start()

        filename_full_path = self.getPlayingFile().decode('utf-8')
        # We don't want to take care of any URL because we can't really gain
        # information from it.
        if _is_excluded(filename_full_path):
            self._tearDown()
            return

        # Try to find the title with the help of XBMC (Theses came from
        # XBMC.Subtitles add-ons)
        self.season = str(xbmc.getInfoLabel("VideoPlayer.Season"))
        log('Player - Season: %s' % self.season)
        self.episode = str(xbmc.getInfoLabel("VideoPlayer.Episode"))
        log('Player - Episode: %s' % self.episode)
        self.title = xbmc.getInfoLabel("VideoPlayer.TVshowtitle")
        log('Player - TVShow: %s' % self.title)
        if self.title == "":
            filename = os.path.basename(filename_full_path)
            log('Player - Filename: %s' % filename)
            self.title, self.season, self.episode = self.mye.get_info(filename)
            log('Player - TVShow: %s' % self.title)

        log("Title: %s - Season: %s - Ep: %s" % (self.title, self.season, self.episode))
        if not self.season and not self.episode:
            # It's not a show. If it should be recognised as one. Send a bug.
            self._tearDown()
            return

        self.title, self.showid = self.mye.find_show_id(self.title)
        if self.showid is None:
            notif("%s %s" % (self.title, __language__(32923)), time=3000)
            self._tearDown()
            return
        log('Player - Found : %s - %d (S%s E%s)' % (self.title,
                self.showid, self.season, self.episode))

        if __addon__.getSetting('auto-add') == "true":
            self._addShow()

    def onPlayBackStopped(self):
        # User stopped the playback
        self.onPlayBackEnded()

    def onPlayBackEnded(self):
        self._tearDown()

        actual_percent = (self._lastPos/self._totalTime)*100
        log('lastPos / totalTime : %s / %s = %s %%' % (self._lastPos,
            self._totalTime, actual_percent))
        if (actual_percent < self._min_percent):
            return

        # Playback is finished, set the items to watched
        found = 32923
        showMarkedNotif = True
        if self.mye.set_episode_watched(self.showid, self.season, self.episode):
            if __addon__.getSetting('showNotif-marked') != "true":
                showMarkedNotif = False
            found = 32924
        else:
            if (not self._mecReCheckAuth()):
                return False

        if showMarkedNotif is True:
            notif("%s (S%sE%s) %s" % (self.title, self.season.zfill(2), self.episode.zfill(2),
                __language__(found)))

def notif(msg, time=5000):
    notif_msg = "\"%s\", \"%s\", %i, %s" % ('MyEpisodeCalendar', msg.decode('utf-8', "replace"), time, __icon__)
    xbmc.executebuiltin("XBMC.Notification(%s)" % notif_msg.encode('utf-8'))

def log(msg):
    try:
        msg = msg.encode('utf-8')
    except:
        pass

    xbmc.log("### [%s] - %s" % (__scriptname__, msg, ),
            level=xbmc.LOGDEBUG)

def _is_excluded(filename):
    log("_is_excluded(): Check if '%s' is a URL." % filename)
    excluded_protocols = ["pvr://", "http://", "https://"]
    return any(protocol in filename for protocol in excluded_protocols)

def addShowsProgressDiag():
    progressdiag = xbmcgui.DialogProgress()
    progressdiag.create(__language__(32906), __language__(32907))

    progressdiag.update(0)
    return progressdiag

def mceIDsToTVDBIDs(showlist, TVDBidCache):
    show_stack_v = showlist.values()

    tvdbIds = []
    for mecId in show_stack_v:
        try:
            tvdbIds.append(TVDBidCache[mecId])
        except:
            pass

    return tvdbIds


def addShowsToTSNA(mye, progressdiag=False, silent=False):
    if (not progressdiag and not silent):
        progressdiag = addShowsProgressDiag()

    tvdbLang = __nextAired__.getSetting("SearchLang").split(' ')[0]

    ESSetting = __nextAired__.getSetting("ExtraShows")
    ExtraShows = re.findall(r"(?:mec)?\d+", ESSetting)

    TVDBidCache = NextAired.get_list(DB_CACHE_TVDB_IDS)

    if (TVDBidCache == []):
        TVDBidCache = {}

    show_stack = mye.shows.keys()
    show_stack_v = mye.shows.values()
    showCount = len(mye.shows)
    stackIndex = 0;

    addedCount = 0
    includedCount = 0
    failedCount = 0
    removedCount = 0

    checkRemoved = __addon__.getSetting('tvsna-autoremove') != "false"

    percent = 0

    while True:
        if not silent and (not mye.is_logged or progressdiag.iscanceled()):
            progressdiag.close()
            break

        seriesID_mye  = show_stack_v[stackIndex]
        seriesID_tvdb = False
        seriesTitle   = show_stack.pop(0)
        if ';' in seriesTitle:
            seriesTitle = seriesTitle.split(';')[0]

        
        log('Looking up TVDB ID for series "%s" | MYE ID: %s' % (seriesTitle, seriesID_mye))
        if not silent:
            if checkRemoved:
                percent = int(round((showCount - len(show_stack)) / (float(showCount) + float(len(ExtraShows))) * 100))
            else:
                percent = int(round((showCount - len(show_stack)) / float(showCount) * 100))
            progressdiag.update(percent, __language__(32908), '"%s"' % seriesTitle)

        seriesID_tvdb = False
        try:
            seriesID_tvdb = TVDBidCache[seriesID_mye]
            log('TVDB ID is in cache: %s' % seriesID_tvdb)
        except:
            log('fetching id from TVDB API...')
            fetchedID = mye.getTVDBIDFromShowTitle(seriesTitle).decode('utf-8')
            if(fetchedID):
                seriesID_tvdb = fetchedID
                TVDBidCache[seriesID_mye] = fetchedID
                log('fetched TVDB ID %s' % seriesID_tvdb)

        if (not seriesID_tvdb):
            failedCount=failedCount+1
            log('ERROR: Failed getting TVDB ID!')
        elif (seriesID_tvdb not in ExtraShows and 'mec' + seriesID_tvdb not in ExtraShows):
            ExtraShows.append('mec' + seriesID_tvdb)
            addedCount=addedCount+1
            log('TVDB ID %s added to extra shows' % seriesID_tvdb)
        else:
            includedCount=includedCount+1
            log('TVDB ID %s is already in extra shows' % seriesID_tvdb)

        stackIndex=stackIndex+1

        if (len(show_stack) < 1):
            break
    
    NextAired.save_file(TVDBidCache, DB_CACHE_TVDB_IDS)

    percentStepTwo = 0
    
    # delete shows that are no longer followed on MyEpisodeCalendar
    if(checkRemoved):
        tvdbIds = mceIDsToTVDBIDs(mye.shows, TVDBidCache)
        CleanedExtraShows = []

        esCount = 0
        for showId in ExtraShows:
            cleanId = re.sub(r"\D+", '', showId)
            esCount = esCount + 1
            if not silent:
                percentStepTwo = percent + int(round(esCount / len(ExtraShows)))
                progressdiag.update(percentStepTwo, __language__(32913), '"%s"' % cleanId)
            if (re.sub(r"\d+", '', showId) != 'mec'):
                log("showId %s not added by MEC" % showId)
                CleanedExtraShows.append(showId)
                continue

            if (cleanId in tvdbIds):
                log("showId %s is in shows list" % cleanId)
                CleanedExtraShows.append('mec' + cleanId)
            else:
                log("remove %s from shows list" % cleanId)
                removedCount = removedCount+1

        ExtraShows = CleanedExtraShows

    # save new ExtraShows list to script.tv.show.next.aired settings
    __nextAired__.setSetting('ExtraShows', ','.join(ExtraShows))

    log("added %s IDs" % addedCount)
    log("removed %s IDs" % removedCount)

    if not silent:
        progressdiag.update(100)
        progressdiag.close()
        xbmcgui.Dialog().ok(__language__(32909),__language__(32910) % (addedCount, includedCount, removedCount, failedCount))

    changedCount = addedCount + removedCount
    return changedCount

if ( __name__ == "__main__" ):
    monitor = xbmc.Monitor()
    player = Player()
    if not player.mye.is_logged:
        sys.exit(0)

    log( "[%s] - Version: %s Started" % (__scriptname__, __version__))

    while not monitor.abortRequested():
        if monitor.waitForAbort(10):
            break

    player._tearDown()
    sys.exit(0)

elif ( __nextAired__ and sys.argv and sys.argv[1] and sys.argv[1] == 'addShowsNow'):
    log("started from settings")
    
    progressdiag = addShowsProgressDiag()

    mye = Player._loginMyEpisodeCalendar(silent=True)
        
    if mye.is_logged:
        addShowsToTSNA(mye, progressdiag)
    
    sys.exit(0)


    