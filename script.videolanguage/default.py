import sys
import xbmc, xbmcgui, xbmcaddon
if sys.version_info < (2, 7):
    import simplejson
else:
    import json as simplejson

__addon__        = xbmcaddon.Addon()
__addonid__      = __addon__.getAddonInfo('id')
__addonversion__ = __addon__.getAddonInfo('version')

def log(txt):
    if isinstance(txt, str):
        txt = txt.decode("utf-8")
    message = u'%s: %s' % (__addonid__, txt)
    xbmc.log(msg=message.encode("utf-8"), level=xbmc.LOGDEBUG)

class Main:
    def __init__( self ):
        log("version %s started" % __addonversion__ )
        self._init_vars()
        self._parse_argv()
        # run in backend if parameter was set
        if xbmc.getCondVisibility("IsEmpty(Window(home).Property(videolanguage_backend_running))"):
            if self.backend:
                xbmc.executebuiltin('SetProperty(videolanguage_backend_running,true,home)')
                self.run_backend()
            # only set new properties if movieid is not smaller than 0, e.g. -1
            elif self.movieid and self.movieid > -1:
                self._set_languages(self.movieid)
            # else clear old properties
            else:
                self._clear_properties()
            
    def _init_vars(self):
        self.window = xbmcgui.Window(12003) # Video info dialog
        self.cleared = False

    def _parse_argv(self):
        try:
            params = dict( arg.split("=") for arg in sys.argv[1].split("&"))
        except:
            params = {}
        log("params: %s" % params)
        self.movieid = -1
        try: self.movieid = int(params.get("movieid", "-1"))
        except: pass
        self.backend = params.get("backend", False)
        self.type = str(params.get("type", False))

    def run_backend(self):
        self._stop = False
        self.previousitem = ""
        while not self._stop:
            if not xbmc.getCondVisibility("Container.Scrolling"):
                self.selecteditem = xbmc.getInfoLabel("ListItem.DBID")
                if (self.selecteditem != self.previousitem):
                    self.previousitem = self.selecteditem
                    if xbmc.getInfoLabel("ListItem.DBID") > -1 and not xbmc.getCondVisibility("ListItem.IsFolder"):
                        self._set_languages(xbmc.getInfoLabel("ListItem.DBID"))
                    else:
                        self._clear_properties()
            else:
                self._clear_properties()
            xbmc.sleep(100)
            if not xbmc.getCondVisibility("Window.IsVisible(videolibrary)"):
                self._clear_properties()
                xbmc.executebuiltin('ClearProperty(videolanguage_backend_running,home)')
                self._stop = True

    def _set_languages( self, dbid ):
        try:
            if xbmc.getCondVisibility('Container.Content(movies)') or self.type == "movie":
                json_query = xbmc.executeJSONRPC('{"jsonrpc": "2.0", "method": "VideoLibrary.GetMovieDetails", "params": {"properties": ["streamdetails"], "movieid":%s }, "id": 1}' % dbid)
                json_query = unicode(json_query, 'utf-8', errors='ignore')
                log(json_query)
                json_response = simplejson.loads(json_query)
                if json_response['result'].has_key('moviedetails'):
                    self._set_properties(json_response['result']['moviedetails']['streamdetails']['audio'], json_response['result']['moviedetails']['streamdetails']['subtitle'])
            elif xbmc.getCondVisibility('Container.Content(episodes)') or self.type == "episode":
                json_query = xbmc.executeJSONRPC('{"jsonrpc": "2.0", "method": "VideoLibrary.GetEpisodeDetails", "params": {"properties": ["streamdetails"], "episodeid":%s }, "id": 1}' % dbid)
                json_query = unicode(json_query, 'utf-8', errors='ignore')
                log(json_query)
                json_response = simplejson.loads(json_query)
                if json_response['result'].has_key('episodedetails'):
                    self._set_properties(json_response['result']['episodedetails']['streamdetails']['audio'], json_response['result']['episodedetails']['streamdetails']['subtitle'])
            elif xbmc.getCondVisibility('Container.Content(musicvideos)') or self.type == "musicvideo":
                json_query = xbmc.executeJSONRPC('{"jsonrpc": "2.0", "method": "VideoLibrary.GetMusicVideoDetails", "params": {"properties": ["streamdetails"], "musicvideoid":%s }, "id": 1}' % dbid)
                json_query = unicode(json_query, 'utf-8', errors='ignore')
                log(json_query)
                json_response = simplejson.loads(json_query)
                if json_response['result'].has_key('musicvideodetails'):
                    self._set_properties(json_response['result']['musicvideodetails']['streamdetails']['audio'], json_response['result']['musicvideodetails']['streamdetails']['subtitle'])
        except:
            pass
            
    def _set_properties( self, audio, subtitles ):
        # Set language properties
        count = 1
        # Clear properties before setting new ones
        self._clear_properties()
        for item in audio:
            self.window.setProperty('AudioLanguage.%d' % count, item['language'])
            self.window.setProperty('AudioCodec.%d' % count, item['codec'])
            self.window.setProperty('AudioChannels.%d' % count, str(item['channels']))
            count += 1
        count = 1
        for item in subtitles:
            self.window.setProperty('SubtitleLanguage.%d' % count, item['language'])     
            count += 1
        self.cleared = False
                
    def _clear_properties( self ):
        if not self.cleared:
            # 1 to 99 should really be enough
            for i in range(1,100):
                self.window.clearProperty('AudioLanguage.%d' % i)
                self.window.clearProperty('AudioCodec.%d' % i)
                self.window.clearProperty('AudioChannels.%d' % i)
                self.window.clearProperty('SubtitleLanguage.%d' % i)
            self.cleared = True

if ( __name__ == "__main__" ):
    Main()
log('finished')
