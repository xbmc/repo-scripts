import xbmc
import json

from resources.lib.utils import log


class Monitor(xbmc.Monitor):
    def __init__(self, api, *args, **kwargs):
        xbmc.Monitor.__init__(self)

        self._api = api

    def onNotification(self, sender, method, data):
        log('onNotification')
        log('sender {0}'.format(bool(sender == 'script.simkl')))

        if (method == 'VideoLibrary.OnUpdate'):
            params = json.loads(data)
            _item = params.get('item')
            if _item and _item.get('type') and _item.get('id') and 'playcount' in params:
                ptype = _item['type']
                pid = _item['id']
                playcount = params.get('playcount')

                mitem = {}
                mitem['ids'] = {}
                mitem_valid = False
                if ptype == 'episode':
                    while True:
                        episodeid = pid
                        _response = json.loads(xbmc.executeJSONRPC(json.dumps({
                            'jsonrpc': '2.0',
                            'method': 'VideoLibrary.GetEpisodeDetails',
                            'params': {'episodeid': episodeid,
                                       'properties': ['tvshowid', 'showtitle', 'season', 'episode']},
                            'id': 1})))
                        episodedetails = _response.get('result', {}).get('episodedetails')
                        if not episodedetails:
                            log('failed response episodedetails: {0}'.format(_response))
                            break
                        _response = json.loads(xbmc.executeJSONRPC(json.dumps({
                            'jsonrpc': '2.0',
                            'method': 'VideoLibrary.GetTVShowDetails',
                            'params': {'tvshowid': episodedetails['tvshowid'],
                                       'properties': ['uniqueid']},
                            'id': 1})))
                        tvshowdetails = _response.get('result', {}).get('tvshowdetails')
                        if not tvshowdetails:
                            log('failed response tvshowdetails: {0}'.format(_response))
                            break
                        mitem['type'] = 'shows'
                        mitem['title'] = episodedetails['showtitle']
                        mitem['season'] = episodedetails['season']
                        mitem['episode'] = episodedetails['episode']
                        if tvshowdetails["uniqueid"].get("tvdb"): mitem["ids"]["tvdb"] = tvshowdetails["uniqueid"]["tvdb"]
                        if tvshowdetails["uniqueid"].get("tmdb"): mitem["ids"]["tmdb"] = tvshowdetails["uniqueid"]["tmdb"]
                        mitem_valid = True
                        break
                elif ptype == 'movie':
                    while True:
                        movieid = pid
                        _response = json.loads(xbmc.executeJSONRPC(json.dumps({
                            'jsonrpc': '2.0',
                            'method': 'VideoLibrary.GetMovieDetails',
                            'params': {'movieid': movieid,
                                       'properties': ['title', 'year', 'uniqueid']},
                            'id': 1})))
                        moviedetails = _response.get('result', {}).get('moviedetails')
                        if not moviedetails:
                            log('failed response moviedetails: {0}'.format(_response))
                            break
                        mitem['type'] = 'movies'
                        mitem['title'] = moviedetails['title']
                        mitem['year'] = moviedetails['year']
                        if moviedetails["uniqueid"].get("tvdb"): mitem["ids"]["tvdb"] = moviedetails["uniqueid"]["tvdb"]
                        if moviedetails["uniqueid"].get("tmdb"): mitem["ids"]["tmdb"] = moviedetails["uniqueid"]["tmdb"]
                        if moviedetails["uniqueid"].get("imdb"): mitem["ids"]["imdb"] = moviedetails["uniqueid"]["imdb"]
                        mitem_valid = True
                        break
                else:
                    log('Unknown type {0}'.format(ptype))

                if mitem_valid:
                    if (playcount > 0): # If it has been watched
                        self._api.mark_as_watched(mitem)
                    else:
                        self._api.mark_as_unwatched(mitem)

        if sender == "script.simkl":
            if method == 'Other.login':
                self._api.login()

    def onSettingsChanged(self):
        log("CHANGED")
