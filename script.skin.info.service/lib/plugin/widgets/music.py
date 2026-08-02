"""Music library widget handlers for plugin content."""
from __future__ import annotations

from typing import Optional

import xbmc
import xbmcgui
import xbmcplugin

from lib.kodi.client import log, request, extract_result, get_item_details


def _resolve_artist_name(params: dict) -> Optional[str]:
    """Extract artist name from params or resolve via dbid+dbtype."""
    artist = params.get('artist', [''])[0]
    if artist:
        return artist

    dbid_str = params.get('dbid', [''])[0]
    dbtype = params.get('dbtype', [''])[0]
    if not dbid_str or not dbtype:
        return None

    try:
        dbid = int(dbid_str)
    except (ValueError, TypeError):
        return None

    if dbtype == 'musicvideo':
        details = get_item_details('musicvideo', dbid, ['artist'])
        artists = details.get('artist', []) if details else []
        return artists[0] if artists else None

    if dbtype == 'artist':
        details = get_item_details('artist', dbid, [])
        return details.get('artist') if details else None

    if dbtype == 'album':
        details = get_item_details('album', dbid, ['artist'])
        artists = details.get('artist', []) if details else []
        return artists[0] if artists else None

    if dbtype == 'song':
        details = get_item_details('song', dbid, ['artist'])
        artists = details.get('artist', []) if details else []
        return artists[0] if artists else None

    return None


def _resolve_artist_id(artist_name: str) -> Optional[int]:
    """Resolve artist name to AudioLibrary artistid."""
    result = request('AudioLibrary.GetArtists', {
        'filter': {'field': 'artist', 'operator': 'is', 'value': artist_name},
        'properties': ['genre'],
        'limits': {'start': 0, 'end': 1},
    })
    artists = extract_result(result, 'artists', [])
    if artists:
        return artists[0].get('artistid')
    return None


_ARTIST_PROPERTIES = ['thumbnail', 'genre', 'description', 'art', 'dateadded',
                       'fanart']

_ALBUM_PROPERTIES = ['title', 'artist', 'year', 'genre', 'thumbnail', 'art',
                      'rating', 'userrating', 'playcount', 'dateadded',
                      'displayartist', 'albumlabel', 'description']

_MUSICVIDEO_PROPERTIES = ['title', 'artist', 'album', 'genre', 'year', 'art',
                           'file', 'runtime', 'plot', 'director', 'studio',
                           'track', 'playcount', 'lastplayed', 'dateadded',
                           'rating', 'userrating', 'tag', 'resume', 'thumbnail']


def _create_artist_listitem(artist: dict) -> xbmcgui.ListItem:
    """Create artist ListItem with MusicInfoTag + art."""
    name = artist.get('artist') or artist.get('label', '')
    item = xbmcgui.ListItem(name, offscreen=True)

    music_tag = item.getMusicInfoTag()
    music_tag.setMediaType('artist')
    music_tag.setArtist(name)

    artistid = artist.get('artistid')
    if artistid:
        music_tag.setDbId(artistid, 'artist')

    genres = artist.get('genre', [])
    if genres:
        music_tag.setGenres(genres if isinstance(genres, list) else [genres])

    description = artist.get('description', '')
    if description:
        music_tag.setComment(description)

    art = artist.get('art', {})
    if not art:
        thumb = artist.get('thumbnail', '')
        if thumb:
            art = {'thumb': thumb}
    if art:
        item.setArt(art)

    return item


def _create_album_listitem(album: dict) -> xbmcgui.ListItem:
    """Create album ListItem with MusicInfoTag + art."""
    title = album.get('title') or album.get('label', '')
    item = xbmcgui.ListItem(title, offscreen=True)

    music_tag = item.getMusicInfoTag()
    music_tag.setMediaType('album')
    music_tag.setAlbum(title)

    albumid = album.get('albumid')
    if albumid:
        music_tag.setDbId(albumid, 'album')

    artists = album.get('artist', [])
    if artists:
        if isinstance(artists, list):
            music_tag.setArtist(artists[0] if artists else '')
        else:
            music_tag.setArtist(str(artists))

    year = album.get('year', 0)
    if year:
        music_tag.setYear(int(year))

    genres = album.get('genre', [])
    if genres:
        music_tag.setGenres(genres if isinstance(genres, list) else [genres])

    rating = album.get('rating')
    if rating:
        music_tag.setRating(float(rating))

    userrating = album.get('userrating')
    if userrating:
        music_tag.setUserRating(int(userrating))

    art = album.get('art', {})
    if not art:
        thumb = album.get('thumbnail', '')
        if thumb:
            art = {'thumb': thumb}
    if art:
        item.setArt(art)

    return item


def _create_musicvideo_listitem(mv: dict) -> xbmcgui.ListItem:
    """Create musicvideo ListItem with VideoInfoTag + art."""
    title = mv.get('title') or mv.get('label', '')
    item = xbmcgui.ListItem(title, offscreen=True)

    video_tag = item.getVideoInfoTag()
    video_tag.setMediaType('musicvideo')
    video_tag.setTitle(title)

    mvid = mv.get('musicvideoid')
    if mvid:
        video_tag.setDbId(mvid)

    year = mv.get('year', 0)
    if year:
        video_tag.setYear(int(year))

    runtime = mv.get('runtime', 0)
    if runtime:
        video_tag.setDuration(int(runtime))

    plot = mv.get('plot', '')
    if plot:
        video_tag.setPlot(plot)

    directors = mv.get('director', [])
    if directors:
        video_tag.setDirectors(directors if isinstance(directors, list) else [directors])

    studios = mv.get('studio', [])
    if studios:
        video_tag.setStudios(studios if isinstance(studios, list) else [studios])

    genres = mv.get('genre', [])
    if genres:
        video_tag.setGenres(genres if isinstance(genres, list) else [genres])

    artists = mv.get('artist', [])
    if artists:
        video_tag.setArtists(artists if isinstance(artists, list) else [artists])

    album = mv.get('album', '')
    if album:
        video_tag.setAlbum(album)

    track = mv.get('track', 0)
    if track:
        video_tag.setTrackNumber(int(track))

    playcount = mv.get('playcount', 0)
    if playcount:
        video_tag.setPlaycount(int(playcount))

    lastplayed = mv.get('lastplayed', '')
    if lastplayed:
        video_tag.setLastPlayed(lastplayed)

    rating = mv.get('rating', 0.0)
    if rating:
        video_tag.setRating(float(rating))

    userrating = mv.get('userrating', 0)
    if userrating:
        video_tag.setUserRating(int(userrating))

    tags = mv.get('tag', [])
    if tags:
        video_tag.setTags(tags if isinstance(tags, list) else [tags])

    resume = mv.get('resume', {})
    if isinstance(resume, dict):
        position = resume.get('position', 0)
        total = resume.get('total', 0)
        if position > 0 and total > 0:
            video_tag.setResumePoint(position, total)

    art = mv.get('art', {})
    if art:
        item.setArt(art)

    return item


def handle_similar_artists(handle: int, params: dict) -> None:
    """Get library artists similar to the given artist via Last.fm data."""
    artist_name = _resolve_artist_name(params)
    if not artist_name:
        log("Plugin", "similar_artists: Could not resolve artist name", xbmc.LOGWARNING)
        xbmcplugin.endOfDirectory(handle, succeeded=False)
        return

    limit = int(params.get('limit', ['25'])[0])

    from lib.service.music import get_similar_artist_names
    similar_names = get_similar_artist_names(artist_name)

    if not similar_names:
        log("Plugin", f"similar_artists: No similar artists for '{artist_name}'", xbmc.LOGDEBUG)
        xbmcplugin.endOfDirectory(handle, succeeded=True)
        return

    result = request('AudioLibrary.GetArtists', {
        'filter': {'or': [{'field': 'artist', 'operator': 'is', 'value': n}
                          for n in similar_names]},
        'properties': _ARTIST_PROPERTIES,
    })
    matched = extract_result(result, 'artists', [])[:limit]

    for artist in matched:
        item = _create_artist_listitem(artist)
        xbmcplugin.addDirectoryItem(handle, '', item, isFolder=False)

    xbmcplugin.setContent(handle, 'artists')
    xbmcplugin.endOfDirectory(handle, succeeded=True)
    log("Plugin", f"similar_artists: Returned {len(matched)} artists for '{artist_name}'",
        xbmc.LOGDEBUG)


def handle_artist_albums(handle: int, params: dict) -> None:
    """Get albums by the given artist from AudioLibrary."""
    artist_name = _resolve_artist_name(params)
    if not artist_name:
        log("Plugin", "artist_albums: Could not resolve artist name", xbmc.LOGWARNING)
        xbmcplugin.endOfDirectory(handle, succeeded=False)
        return

    from lib.plugin.widgets import validate_sort_method
    limit = int(params.get('limit', ['25'])[0])
    sort_method = validate_sort_method(params.get('sort', ['year'])[0], 'year')

    artistid = _resolve_artist_id(artist_name)
    if artistid is None:
        log("Plugin", f"artist_albums: Artist '{artist_name}' not in AudioLibrary", xbmc.LOGDEBUG)
        xbmcplugin.endOfDirectory(handle, succeeded=True)
        return

    result = request('AudioLibrary.GetAlbums', {
        'filter': {'artistid': artistid},
        'properties': _ALBUM_PROPERTIES,
        'sort': {'method': sort_method, 'order': 'ascending'},
        'limits': {'start': 0, 'end': limit},
    })
    albums = extract_result(result, 'albums', [])

    for album in albums:
        item = _create_album_listitem(album)
        xbmcplugin.addDirectoryItem(handle, '', item, isFolder=False)

    xbmcplugin.setContent(handle, 'albums')
    xbmcplugin.endOfDirectory(handle, succeeded=True)
    log("Plugin", f"artist_albums: Returned {len(albums)} albums for '{artist_name}'",
        xbmc.LOGDEBUG)


def handle_artist_musicvideos(handle: int, params: dict) -> None:
    """Get musicvideos by the given artist from VideoLibrary."""
    artist_name = _resolve_artist_name(params)
    if not artist_name:
        log("Plugin", "artist_musicvideos: Could not resolve artist name", xbmc.LOGWARNING)
        xbmcplugin.endOfDirectory(handle, succeeded=False)
        return

    limit = int(params.get('limit', ['25'])[0])

    exclude_id: Optional[int] = None
    dbid_str = params.get('dbid', [''])[0]
    dbtype = params.get('dbtype', [''])[0]
    if dbid_str and dbtype == 'musicvideo':
        try:
            exclude_id = int(dbid_str)
        except (ValueError, TypeError):
            pass

    result = request('VideoLibrary.GetMusicVideos', {
        'filter': {'artist': artist_name},
        'properties': _MUSICVIDEO_PROPERTIES,
        'sort': {'method': 'year', 'order': 'descending'},
        'limits': {'start': 0, 'end': limit + (1 if exclude_id else 0)},
    })
    musicvideos = extract_result(result, 'musicvideos', [])

    count = 0
    for mv in musicvideos:
        if exclude_id and mv.get('musicvideoid') == exclude_id:
            continue
        if count >= limit:
            break
        item = _create_musicvideo_listitem(mv)
        file_path = mv.get('file', '')
        xbmcplugin.addDirectoryItem(handle, file_path, item, isFolder=False)
        count += 1

    xbmcplugin.setContent(handle, 'musicvideos')
    xbmcplugin.endOfDirectory(handle, succeeded=True)
    log("Plugin", f"artist_musicvideos: Returned {count} musicvideos for '{artist_name}'",
        xbmc.LOGDEBUG)


def handle_genre_artists(handle: int, params: dict) -> None:
    """Get artists in the same genre as the given artist from AudioLibrary."""
    genre = params.get('genre', [''])[0]
    source_artist: Optional[str] = None

    if not genre:
        source_artist = _resolve_artist_name(params)
        if not source_artist:
            log("Plugin", "genre_artists: Could not resolve artist or genre", xbmc.LOGWARNING)
            xbmcplugin.endOfDirectory(handle, succeeded=False)
            return

        artistid = _resolve_artist_id(source_artist)
        if artistid is None:
            log("Plugin", f"genre_artists: Artist '{source_artist}' not in AudioLibrary",
                xbmc.LOGDEBUG)
            xbmcplugin.endOfDirectory(handle, succeeded=True)
            return

        details = get_item_details('artist', artistid, ['genre'])
        genres = details.get('genre', []) if details else []
        if not genres:
            log("Plugin", f"genre_artists: No genre for '{source_artist}'", xbmc.LOGDEBUG)
            xbmcplugin.endOfDirectory(handle, succeeded=True)
            return
        genre = genres[0]

    limit = int(params.get('limit', ['25'])[0])

    result = request('AudioLibrary.GetArtists', {
        'filter': {'field': 'genre', 'operator': 'is', 'value': genre},
        'properties': _ARTIST_PROPERTIES,
        'sort': {'method': 'random'},
        'limits': {'start': 0, 'end': limit + (1 if source_artist else 0)},
    })
    artists = extract_result(result, 'artists', [])

    count = 0
    for artist in artists:
        name = artist.get('artist') or artist.get('label', '')
        if source_artist and name.lower() == source_artist.lower():
            continue
        if count >= limit:
            break
        item = _create_artist_listitem(artist)
        xbmcplugin.addDirectoryItem(handle, '', item, isFolder=False)
        count += 1

    xbmcplugin.setContent(handle, 'artists')
    xbmcplugin.endOfDirectory(handle, succeeded=True)
    log("Plugin", f"genre_artists: Returned {count} artists for genre '{genre}'", xbmc.LOGDEBUG)
