#!/usr/bin/python

JSON_MAP = {
    'movie_properties': [
        'title',
        'originaltitle',
        'sorttitle',
        'votes',
        'playcount',
        'year',
        'genre',
        'studio',
        'country',
        'tagline',
        'tag',
        'plot',
        'runtime',
        'premiered',
        'file',
        'plotoutline',
        'lastplayed',
        'trailer',
        'rating',
        'ratings',
        'userrating',
        'resume',
        'art',
        'mpaa',
        'director',
        'writer',
        'cast',
        'set',
        'setid',
        'top250',
        'dateadded',
        'imdbnumber',
        'uniqueid'
    ],

    'movies_properties': [
        'title',
        'year'
    ],

    'set_properties': [
        'title',
        'plot'
    ],

    'sets_properties': [
        'title'
    ],

    'episode_properties': [
        'title',
        'playcount',
        'season',
        'episode',
        'showtitle',
        'originaltitle',
        'plot',
        'votes',
        'file',
        'rating',
        'ratings',
        'userrating',
        'resume',
        'tvshowid',
        'firstaired',
        'art',
        'runtime',
        'director',
        'writer',
        'cast',
        'dateadded',
        'lastplayed',
        'uniqueid'
    ],

    'episodes_properties': [
        'title',
        'showtitle'
    ],

    'season_properties': [
        'season',
        'episode',
        'art',
        'userrating',
        'watchedepisodes',
        'showtitle',
        'playcount',
        'tvshowid'
    ],

    'seasons_properties': [
        'season',
        'showtitle',
        'tvshowid'
    ],

    'tvshow_properties': [
        'title',
        'studio',
        'year',
        'plot',
        'cast',
        'rating',
        'ratings',
        'userrating',
        'votes',
        'file',
        'genre',
        'episode',
        'season',
        'runtime',
        'mpaa',
        'premiered',
        'playcount',
        'lastplayed',
        'sorttitle',
        'originaltitle',
        'episodeguide',
        'art',
        'tag',
        'dateadded',
        'watchedepisodes',
        'imdbnumber',
        'uniqueid'
    ],

    'tvshows_properties': [
        'title',
        'year'
    ],

    'musicvideo_properties': [
        'title',
        'playcount',
        'runtime',
        'director',
        'studio',
        'year',
        'plot',
        'album',
        'artist',
        'genre',
        'track',
        'lastplayed',
        'fanart',
        'thumbnail',
        'file',
        'resume',
        'dateadded',
        'tag',
        'art',
        'rating',
        'userrating',
        'premiered'
    ],

    'musicvideos_properties': [
        'title',
        'year'
    ],

    'artist_properties': [
        'instrument',
        'style',
        'mood',
        'born',
        'formed',
        'description',
        'genre',
        'died',
        'disbanded',
        'yearsactive',
        'musicbrainzartistid',
        'fanart',
        'thumbnail',
        'compilationartist',
        'dateadded',
        'roles',
        'songgenres',
        'isalbumartist',
        'disambiguation'
    ],

    'artists_properties': [
        'dateadded'
    ],

    'album_properties': [
        'title',
        'description',
        'artist',
        'genre',
        'theme',
        'mood',
        'style',
        'type',
        'albumlabel',
        'rating',
        'votes',
        'userrating',
        'year',
        'musicbrainzalbumid',
        'musicbrainzalbumartistid',
        'fanart',
        'thumbnail',
        'playcount',
        'artistid',
        'displayartist',
        'compilation',
        'releasetype',
        'dateadded'
    ],

    'albums_properties': [
        'title',
        'year'
    ],

    'song_properties': [
        'title',
        'artist',
        'albumartist',
        'genre',
        'year',
        'rating',
        'album',
        'track',
        'duration',
        'comment',
        'lyrics',
        'musicbrainztrackid',
        'musicbrainzartistid',
        'musicbrainzalbumid',
        'musicbrainzalbumartistid',
        'playcount',
        'fanart',
        'thumbnail',
        'file',
        'albumid',
        'lastplayed',
        'disc',
        'genreid',
        'artistid',
        'displayartist',
        'albumartistid',
        'albumreleasetype',
        'dateadded',
        'votes',
        'userrating',
        'mood',
        'contributors',
        'displaycomposer',
        'displayconductor',
        'displayorchestra',
        'displaylyricist'
    ],

    'songs_properties': [
        'title',
        'artist'
    ]
}