"""Plugin wrapper for XSP-filtered library paths."""
from __future__ import annotations

import json
import xbmc
import xbmcgui
import xbmcplugin

from lib.kodi.client import log, extract_result


def handle_wrap(handle: int, params: dict) -> None:
    """Wrap XSP-filtered library paths in `plugin://` so Kodi refreshes them on updates.

    For inline XSP filters, `.xsp` files, and smart playlists with InfoLabel filters;
    not needed for regular library browsing.
    """
    from lib.kodi.settings import KodiSettings

    path = params.get('path', [''])[0]

    if not path:
        log("Plugin", "Path Wrapper: No path provided", xbmc.LOGERROR)
        xbmcplugin.endOfDirectory(handle, succeeded=False)
        return

    enable_debug = KodiSettings.debug_enabled()
    if enable_debug:
        log("Plugin", f"Path Wrapper: Wrapping path: {path}", xbmc.LOGDEBUG)

    json_request = json.dumps({
        'jsonrpc': '2.0',
        'method': 'Files.GetDirectory',
        'params': {
            'directory': path,
            'media': 'video',
            'properties': [
                'title', 'artist', 'genre', 'year', 'rating', 'album', 'track',
                'playcount', 'director', 'trailer', 'tagline', 'plot', 'plotoutline',
                'originaltitle', 'lastplayed', 'writer', 'studio', 'mpaa', 'country',
                'imdbnumber', 'premiered', 'productioncode', 'runtime', 'set', 'setid',
                'top250', 'votes', 'firstaired', 'season', 'episode', 'showtitle',
                'tvshowid', 'watchedepisodes', 'tag', 'art', 'userrating', 'resume',
                'dateadded'
            ]
        },
        'id': 1
    })

    response = xbmc.executeJSONRPC(json_request)
    result = json.loads(response)

    if 'error' in result:
        log("Plugin", f'Path Wrapper: Error - {result["error"]}', xbmc.LOGERROR)
        xbmcplugin.endOfDirectory(handle, succeeded=False)
        return

    files = extract_result(result, 'files', [])

    if enable_debug:
        log("Plugin", f"Path Wrapper: Found {len(files)} items", xbmc.LOGDEBUG)

    items = []

    for file_item in files:
        file_path = file_item.get('file', '')
        filetype = file_item.get('filetype', '')

        if filetype == 'directory' and file_path.endswith(
            ('.mkv', '.mp4', '.avi', '.m4v', '.mov', '.wmv', '.flv', '.webm')
        ):
            filetype = 'file'

        li = xbmcgui.ListItem(file_item.get('label', ''), offscreen=True)
        li.setPath(file_path)

        video_tag = li.getVideoInfoTag()

        if 'title' in file_item:
            video_tag.setTitle(file_item['title'])
        if 'year' in file_item:
            year = file_item['year']
            video_tag.setYear(
                int(year) if isinstance(year, (int, str)) and str(year).isdigit() else 0
            )
        if 'plot' in file_item:
            video_tag.setPlot(file_item['plot'])
        if 'plotoutline' in file_item:
            video_tag.setPlotOutline(file_item['plotoutline'])
        if 'rating' in file_item:
            video_tag.setRating(
                float(file_item['rating']) if file_item['rating'] else 0.0
            )
        if 'votes' in file_item:
            votes = file_item['votes']
            video_tag.setVotes(
                int(votes) if isinstance(votes, (int, str)) and str(votes).isdigit() else 0
            )
        if 'playcount' in file_item:
            playcount = file_item['playcount']
            video_tag.setPlaycount(
                int(playcount)
                if isinstance(playcount, (int, str)) and str(playcount).isdigit()
                else 0
            )
        if 'lastplayed' in file_item:
            video_tag.setLastPlayed(file_item['lastplayed'])
        if 'dateadded' in file_item:
            video_tag.setDateAdded(file_item['dateadded'])
        if 'userrating' in file_item:
            userrating = file_item['userrating']
            video_tag.setUserRating(
                int(userrating)
                if isinstance(userrating, (int, str)) and str(userrating).isdigit()
                else 0
            )
        if 'runtime' in file_item:
            runtime = file_item['runtime']
            video_tag.setDuration(
                int(runtime) if isinstance(runtime, (int, str)) and str(runtime).isdigit() else 0
            )
        if 'director' in file_item:
            video_tag.setDirectors(
                file_item['director']
                if isinstance(file_item['director'], list)
                else [file_item['director']]
            )
        if 'writer' in file_item:
            video_tag.setWriters(
                file_item['writer']
                if isinstance(file_item['writer'], list)
                else [file_item['writer']]
            )
        if 'genre' in file_item:
            video_tag.setGenres(
                file_item['genre']
                if isinstance(file_item['genre'], list)
                else [file_item['genre']]
            )
        if 'studio' in file_item:
            video_tag.setStudios(
                file_item['studio']
                if isinstance(file_item['studio'], list)
                else [file_item['studio']]
            )
        if 'country' in file_item:
            video_tag.setCountries(
                file_item['country']
                if isinstance(file_item['country'], list)
                else [file_item['country']]
            )
        if 'mpaa' in file_item:
            video_tag.setMpaa(file_item['mpaa'])
        if 'tagline' in file_item:
            video_tag.setTagLine(file_item['tagline'])
        if 'originaltitle' in file_item:
            video_tag.setOriginalTitle(file_item['originaltitle'])
        if 'premiered' in file_item:
            video_tag.setPremiered(file_item['premiered'])
        if 'trailer' in file_item:
            video_tag.setTrailer(file_item['trailer'])
        if 'imdbnumber' in file_item:
            video_tag.setIMDBNumber(file_item['imdbnumber'])
        if 'top250' in file_item:
            top250 = file_item['top250']
            video_tag.setTop250(
                int(top250) if isinstance(top250, (int, str)) and str(top250).isdigit() else 0
            )
        if 'set' in file_item:
            video_tag.setSet(file_item['set'])
        if 'setid' in file_item:
            setid = file_item['setid']
            video_tag.setSetId(
                int(setid) if isinstance(setid, (int, str)) and str(setid).isdigit() else 0
            )
        if 'tag' in file_item:
            video_tag.setTags(
                file_item['tag'] if isinstance(file_item['tag'], list) else [file_item['tag']]
            )
        if 'season' in file_item:
            season = file_item['season']
            video_tag.setSeason(
                int(season) if isinstance(season, (int, str)) and str(season).isdigit() else 0
            )
        if 'episode' in file_item:
            episode = file_item['episode']
            video_tag.setEpisode(
                int(episode) if isinstance(episode, (int, str)) and str(episode).isdigit() else 0
            )
        if 'showtitle' in file_item:
            video_tag.setTvShowTitle(file_item['showtitle'])
        if 'firstaired' in file_item:
            video_tag.setFirstAired(file_item['firstaired'])
        if 'productioncode' in file_item:
            video_tag.setProductionCode(file_item['productioncode'])
        if 'artist' in file_item:
            video_tag.setArtists(
                file_item['artist']
                if isinstance(file_item['artist'], list)
                else [file_item['artist']]
            )
        if 'album' in file_item:
            video_tag.setAlbum(file_item['album'])
        if 'track' in file_item:
            track = file_item['track']
            video_tag.setTrackNumber(
                int(track) if isinstance(track, (int, str)) and str(track).isdigit() else 0
            )

        if 'type' in file_item:
            video_tag.setMediaType(file_item['type'])

        if 'resume' in file_item:
            resume = file_item['resume']
            if isinstance(resume, dict):
                position = resume.get('position', 0)
                total = resume.get('total', 0)
                if position > 0 and total > 0:
                    video_tag.setResumePoint(position, total)

        if 'art' in file_item:
            li.setArt(file_item['art'])

        is_folder = filetype == 'directory'
        items.append((file_path, li, is_folder))

    xbmcplugin.addDirectoryItems(handle, items, len(items))
    xbmcplugin.endOfDirectory(handle, succeeded=True)

    if enable_debug:
        log("Plugin", f"Path Wrapper: Successfully wrapped {len(items)} items", xbmc.LOGDEBUG)
