import xbmc
import xbmcaddon
import xbmcgui

import pykodi

from random import shuffle
from pykodi import log

SELECTWATCHMODE_HEADING_LOCALIZE_ID = 32010
WATCHMODE_ALLVIDEOS_LOCALIZE_ID = 16100
WATCHMODE_ALLVIDEOS = 'all videos'
WATCHMODE_UNWATCHED_LOCALIZE_ID = 16101
WATCHMODE_UNWATCHED = 'unwatched'
WATCHMODE_WATCHED_LOCALIZE_ID = 16102
WATCHMODE_WATCHED = 'watched'
WATCHMODE_ASKME_LOCALIZE_ID = 36521
WATCHMODE_ASKME = 'ask me'
# Same order as settings
WATCHMODES = (WATCHMODE_ALLVIDEOS, WATCHMODE_UNWATCHED, WATCHMODE_WATCHED, WATCHMODE_ASKME)
WATCHMODE_NONE = 'none'

MAX_FILESYSTEM_LIMIT = 20
FILESYSTEM_DIRCOUNT_WARNING = 8
FILESYSTEM_DIRCOUNT_WARNING_NEW_LIMIT = 5

def _play_videos(items):
    playlist = xbmc.PlayList(xbmc.PLAYLIST_VIDEO)
    playlist.clear()
    for item in items:
        playlist.add(item.get('file'), xbmcgui.ListItem(item.get('label')))
    xbmc.Player().play(playlist)

def _get_watchmode(path):
    if path['type'] not in ('videodb', 'library'):
        return WATCHMODE_ALLVIDEOS

    option = None

    if 'forcewatchmode' in path:
        if path['forcewatchmode'].lower() in (WATCHMODE_ALLVIDEOS, WATCHMODE_UNWATCHED, WATCHMODE_WATCHED, WATCHMODE_ASKME):
            option = path['forcewatchmode'].lower()
        elif path['forcewatchmode'] == xbmc.getLocalizedString(WATCHMODE_ALLVIDEOS_LOCALIZE_ID):
            option = WATCHMODE_ALLVIDEOS
        elif path['forcewatchmode'] == xbmc.getLocalizedString(WATCHMODE_UNWATCHED_LOCALIZE_ID):
            option = WATCHMODE_UNWATCHED
        elif path['forcewatchmode'] == xbmc.getLocalizedString(WATCHMODE_WATCHED_LOCALIZE_ID):
            option = WATCHMODE_WATCHED

    if not option:
        addon = xbmcaddon.Addon()
        sectionindex = 0 if path['type'] == 'videodb' else 1
        settingenum = None
        if path['path'][sectionindex] in ('movies', 'recentlyaddedmovies.xml', 'recentlyaddedmovies'):
            settingenum = addon.getSetting('watchmodemovies')
        elif path['path'][sectionindex] in ('tvshows', 'inprogressshows.xml', 'recentlyaddedepisodes.xml', 'recentlyaddedepisodes'):
            settingenum = addon.getSetting('watchmodetvshows')
        elif path['path'][sectionindex] in ('musicvideos', 'recentlyaddedmusicvideos.xml', 'recentlyaddedmusicvideos'):
            settingenum = addon.getSetting('watchmodemusicvideos')

        if settingenum:
            try:
                option = WATCHMODES[int(settingenum)]
            except ValueError:
                pass

    if option == WATCHMODE_ASKME:
        return _ask_me()
    elif option:
        return option
    else:
        return WATCHMODE_ALLVIDEOS

def _ask_me():
    options = [xbmc.getLocalizedString(WATCHMODE_ALLVIDEOS_LOCALIZE_ID), xbmc.getLocalizedString(WATCHMODE_UNWATCHED_LOCALIZE_ID), xbmc.getLocalizedString(WATCHMODE_WATCHED_LOCALIZE_ID)]
    selectedindex = xbmcgui.Dialog().select(xbmcaddon.Addon().getLocalizedString(SELECTWATCHMODE_HEADING_LOCALIZE_ID), options)

    if selectedindex == 0:
        return WATCHMODE_ALLVIDEOS
    elif selectedindex == 1:
        return WATCHMODE_UNWATCHED
    elif selectedindex == 2:
        return WATCHMODE_WATCHED
    else:
        return WATCHMODE_NONE

unplayed_filter = {'field': 'playcount', 'operator': 'lessthan', 'value':'1'}
played_filter = {'field': 'playcount', 'operator': 'greaterthan', 'value':'0'}

class RandomPlayer(object):
    def __init__(self, limit=1):
        self.limit_length = limit
        self._reset()

    def _reset(self):
        self.file_mode = False
        self.dircount = 0

    @property
    def filewarning(self):
        return self.file_mode and self.dircount > FILESYSTEM_DIRCOUNT_WARNING

    def play_randomvideos_from_path(self, path):
        self._reset()
        path['watchmode'] = _get_watchmode(path)
        if path['watchmode'] == WATCHMODE_NONE:
            # Dear viewer backed out of the selection
            return

        xbmc.executebuiltin('ActivateWindow(busydialog)')
        videos = None
        if path['type'] == 'library':
            if path['path'][1] == 'inprogressshows.xml':
                videos = self._get_randomepisodes_by_category(showfilter={'field': 'inprogress', 'operator':'true', 'value':''}, watchmode=path['watchmode'])
            elif path['path'][1] == 'tvshows':
                videos = self._get_randomepisodes(watchmode=path['watchmode'])
            elif path['path'][1] in ('movies', 'musicvideos'):
                videos = self._get_randomvideos_from_path('library://video/%s/titles.xml/' % path['path'][1], path['watchmode'])
            elif path['path'][1] in ('files.xml', 'addons.xml'):
                # Trying to descend into these is probably not a good idea ever
                videos = []
        elif path['type'] == 'videodb':
            if path['path'][0] == 'tvshows':
                videos = self._get_randomepisodes_by_path(path)
            elif path['path'][0] in ('movies', 'musicvideos') and len(path['path']) < 3:
                # Hasn't selected a genre/studio/etc, select from all options
                videos = self._get_randomvideos_from_path('library://video/%s/titles.xml/' % path['path'][0], path['watchmode'])
        elif path['type'] == 'special':
            if path['path'][0] == 'videoplaylists':
                videos = []
        else:
            # probably file system, set flag to watch directory count
            self.file_mode = True

        if videos == None: # skips empty lists set above
            videos = self._get_randomvideos_from_path(path['full path'], path['watchmode'])

        if videos:
            shuffle(videos)
            _play_videos(videos)
        xbmc.executebuiltin('Dialog.Close(busydialog)')

    def _get_randomepisodes_by_path(self, path):
        path_len = len(path['path'])
        category = path['path'][1] if path_len > 1 else None
        if category in (None, 'titles'):
            tvshow_id = path['path'][2] if path_len > 2 else None
            season = path['path'][3] if path_len > 3 else None
            return self._get_randomepisodes(tvshow_id, season, path['watchmode'])
        elif path_len < 3:
            return self._get_randomepisodes(watchmode=path['watchmode'])
        elif path_len == 3:
            category_id = path['path'][2]
            return self._get_randomepisodes_by_category(category, category_id, path['label'], watchmode=path['watchmode'])
        else: # Nested TV show selected
            tvshow_id = path['path'][3] if path_len > 4 else None
            season = path['path'][4] if path_len > 5 else None
            return self._get_randomepisodes(tvshow_id, season, path['watchmode'])

    def _get_randomepisodes(self, tvshow_id=None, season=None, watchmode=WATCHMODE_ALLVIDEOS):
        json_request = pykodi.get_base_json_request('VideoLibrary.GetEpisodes')
        json_request['params']['sort'] = {'method': 'random'}
        json_request['params']['limits'] = {'end': self.limit_length}
        json_request['params']['properties'] = ['file']

        if tvshow_id:
            json_request['params']['tvshowid'] = int(tvshow_id)
            if season and not season.startswith('-'):
                json_request['params']['season'] = int(season)

        if watchmode == WATCHMODE_UNWATCHED:
            json_request['params']['filter'] = unplayed_filter
        elif watchmode == WATCHMODE_WATCHED:
            json_request['params']['filter'] = played_filter

        json_result = pykodi.execute_jsonrpc(json_request)
        if 'result' in json_result and 'episodes' in json_result['result']:
            return json_result['result']['episodes']
        elif 'error' in json_result:
            _jsonerror_notification()
            log(json_result, xbmc.LOGDEBUG)

        return []

    category_lookup = {
        'genres': 'genreid',
        'years': 'year',
        'actors': 'actor',
        'studios': 'studio',
        'tags': 'tag'}

    def _get_randomepisodes_by_category(self, category=None, category_id=None, category_label=None, showfilter=None, watchmode=WATCHMODE_ALLVIDEOS):
        json_request = pykodi.get_base_json_request('VideoLibrary.GetTVShows')
        json_request['params']['sort'] = {'method': 'random'}
        if watchmode == WATCHMODE_ALLVIDEOS:
            # Can't combine simple category filters based on library path with playcount filter, so we can only limit ALLVIDEOS here
            json_request['params']['limits'] = {'end': self.limit_length}
        json_request['params']['properties'] = ['file', 'playcount']

        if not showfilter:
            category = self.category_lookup.get(category, category)
            if category == 'genreid' or category == 'year':
                category_value = int(category_id)
            elif category_label:
                category_value = category_label
            showfilter = {category: category_value}
        json_request['params']['filter'] = showfilter

        json_result = pykodi.execute_jsonrpc(json_request)
        if 'result' in json_result and 'tvshows' in json_result['result']:
            random_episodes = []
            count = 0
            for show in json_result['result']['tvshows']:
                if watchmode == WATCHMODE_UNWATCHED and show['playcount'] != 0 or watchmode == WATCHMODE_WATCHED and show['playcount'] == 0:
                    continue
                newepisodes = self._get_randomepisodes(show['tvshowid'])
                if len(newepisodes):
                    random_episodes.extend(newepisodes)
                    count += 1
                if count >= self.limit_length:
                    break
            shuffle(random_episodes)
            return random_episodes[:self.limit_length]
        elif 'error' in json_result:
            _jsonerror_notification()
            log(json_result, xbmc.LOGDEBUG)

        return []

    def _get_randomvideos_from_path(self, fullpath, watchmode=WATCHMODE_ALLVIDEOS):
        """Hits the filesystem more often than it needs to for TV shows, but it pretty much works for everything."""
        return self._recurse_randomvideos_from_path(fullpath, watchmode)

    skip_foldernames = ('extrafanart', 'extrathumbs')
    def _recurse_randomvideos_from_path(self, fullpath, watchmode=WATCHMODE_ALLVIDEOS, depth=3):
        self.dircount += 1
        json_request = pykodi.get_base_json_request('Files.GetDirectory')
        json_request['params'] = {'directory': fullpath, 'media': 'video'}
        json_request['params']['sort'] = {'method': 'random'}

        if self.file_mode:
            if self.filewarning:
                limit = min(self.limit_length, MAX_FILESYSTEM_LIMIT)
            else:
                limit = self.limit_length
        else:
            if watchmode != WATCHMODE_ALLVIDEOS:
                # 'Files.GetDirectory' can't be filtered, grab playcount and a lot more extras and we'll filter in the loop later
                json_request['params']['properties'] = ['playcount']
                limit = self.limit_length * 20
            else:
                limit = self.limit_length

        json_request['params']['limits'] = {'end': limit}

        json_result = pykodi.execute_jsonrpc(json_request)
        if 'result' in json_result and 'files' in json_result['result']:
            result = []
            local_warning_dircount = 0
            for result_file in json_result['result']['files']:
                if result_file['file'].endswith(('.m3u', '.pls', '.cue')):
                    # m3u acts as a directory but "'media': 'video'" doesn't filter out flac/mp3/etc like real directories; the others probably do the same.
                    continue
                if result_file['label'] in self.skip_foldernames:
                    continue
                if result_file['filetype'] == 'directory':
                    if depth > 0 and local_warning_dircount < FILESYSTEM_DIRCOUNT_WARNING_NEW_LIMIT:
                        if self.filewarning:
                            local_warning_dircount += 1
                        result.extend(self._recurse_randomvideos_from_path(result_file['file'], watchmode, depth - 1))
                else:
                    if watchmode == WATCHMODE_ALLVIDEOS or 'playcount' not in result_file:
                        result.append(result_file)
                    elif watchmode == WATCHMODE_UNWATCHED and result_file['playcount'] == 0:
                        result.append(result_file)
                    elif watchmode == WATCHMODE_WATCHED and result_file['playcount'] > 0:
                        result.append(result_file)

            shuffle(result)
            return result[:MAX_FILESYSTEM_LIMIT if self.filewarning else self.limit_length]
        elif 'error' in json_result:
            _jsonerror_notification()
            log(json_result, xbmc.LOGDEBUG)

        return []

def _jsonerror_notification():
    xbmcgui.Dialog().notification('Add-on warning: Play Random Videos', 'Encountered a JSON-RPC error. More info in the debug log.', xbmcgui.NOTIFICATION_WARNING)
