# -*- coding: utf-8 -*-
# Module: default
# Author: jurialmunkey
# License: GPL v.3 https://www.gnu.org/copyleft/gpl.html
from xbmc import Actor, VideoStreamDetail, AudioStreamDetail, SubtitleStreamDetail, LOGINFO
from xbmc import log as kodi_log


class ListItemInfoTag():
    INFO_TAG_ATTR = {
        'video': {
            'tag_getter': 'getVideoInfoTag',
            'tag_attr': {
                'genre': {'attr': 'setGenres', 'convert': lambda x: [x]},
                'country': {'attr': 'setCountries', 'convert': lambda x: [x]},
                'year': {'attr': 'setYear', 'convert': int},
                'episode': {'attr': 'setEpisode', 'convert': int},
                'season': {'attr': 'setSeason', 'convert': int},
                'sortepisode': {'attr': 'setSortEpisode', 'convert': int},
                'sortseason': {'attr': 'setSortSeason', 'convert': int},
                'episodeguide': {'attr': 'setEpisodeGuide', 'convert': str},
                'showlink': {'attr': 'setShowLinks', 'convert': lambda x: [x]},
                'top250': {'attr': 'setTop250', 'convert': int},
                'setid': {'attr': 'setSetId', 'convert': int},
                'tracknumber': {'attr': 'setTrackNumber', 'convert': int},
                'rating': {'attr': 'setRating', 'convert': float},
                'userrating': {'attr': 'setUserRating', 'convert': int},
                'watched': {'skip': True},  # Evaluated internally in Nexus based on playcount so skip
                'playcount': {'attr': 'setPlaycount', 'convert': int},
                'overlay': {'skip': True},  # Evaluated internally in Nexus based on playcount so skip
                'cast': {'route': 'set_info_cast'},
                'castandrole': {'route': 'set_info_cast'},
                'director': {'attr': 'setDirectors', 'convert': lambda x: [x]},
                'mpaa': {'attr': 'setMpaa', 'convert': str},
                'plot': {'attr': 'setPlot', 'convert': str},
                'plotoutline': {'attr': 'setPlotOutline', 'convert': str},
                'title': {'attr': 'setTitle', 'convert': str},
                'originaltitle': {'attr': 'setOriginalTitle', 'convert': str},
                'sorttitle': {'attr': 'setSortTitle', 'convert': str},
                'duration': {'attr': 'setDuration', 'convert': int},
                'studio': {'attr': 'setStudios', 'convert': lambda x: [x]},
                'tagline': {'attr': 'setTagLine', 'convert': str},
                'writer': {'attr': 'setWriters', 'convert': lambda x: [x]},
                'tvshowtitle': {'attr': 'setTvShowTitle', 'convert': str},
                'premiered': {'attr': 'setPremiered', 'convert': str},
                'status': {'attr': 'setTvShowStatus', 'convert': str},
                'set': {'attr': 'setSet', 'convert': str},
                'setoverview': {'attr': 'setSetOverview', 'convert': str},
                'tag': {'attr': 'setTags', 'convert': lambda x: [x]},
                'imdbnumber': {'attr': 'setIMDBNumber', 'convert': str},
                'code': {'attr': 'setProductionCode', 'convert': str},
                'aired': {'attr': 'setFirstAired', 'convert': str},
                'credits': {'attr': 'setWriters', 'convert': lambda x: [x]},
                'lastplayed': {'attr': 'setLastPlayed', 'convert': str},
                'album': {'attr': 'setAlbum', 'convert': str},
                'artist': {'attr': 'setArtists', 'convert': lambda x: [x]},
                'votes': {'attr': 'setVotes', 'convert': int},
                'path': {'attr': 'setPath', 'convert': str},
                'trailer': {'attr': 'setTrailer', 'convert': str},
                'dateadded': {'attr': 'setDateAdded', 'convert': str},
                'mediatype': {'attr': 'setMediaType', 'convert': str},
                'dbid': {'attr': 'setDbId', 'convert': int},
            }
        },
        'music': {
            'tag_getter': 'getMusicInfoTag',
            'tag_attr': {
                'tracknumber': {'attr': 'setTrack', 'convert': int},
                'discnumber': {'attr': 'setDisc', 'convert': int},
                'duration': {'attr': 'setDuration', 'convert': int},
                'year': {'attr': 'setYear', 'convert': int},
                'genre': {'attr': 'setGenres', 'convert': lambda x: [x]},
                'album': {'attr': 'setAlbum', 'convert': str},
                'artist': {'attr': 'setArtist', 'convert': str},
                'title': {'attr': 'setTitle', 'convert': str},
                'rating': {'attr': 'setRating', 'convert': float},
                'userrating': {'attr': 'setUserRating', 'convert': int},
                'lyrics': {'attr': 'setLyrics', 'convert': str},
                'playcount': {'attr': 'setPlayCount', 'convert': int},
                'lastplayed': {'attr': 'setLastPlayed', 'convert': str},
                'mediatype': {'attr': 'setMediaType', 'convert': str},
                'dbid': {'route': 'set_info_music_dbid'},
                'listeners': {'attr': 'setListeners', 'convert': int},
                'musicbrainztrackid': {'attr': 'setMusicBrainzTrackID', 'convert': str},
                'musicbrainzartistid': {'attr': 'setMusicBrainzArtistID', 'convert': lambda x: [x]},
                'musicbrainzalbumid': {'attr': 'setMusicBrainzAlbumID', 'convert': str},
                'musicbrainzalbumartistid': {'attr': 'setMusicBrainzAlbumArtistID', 'convert': lambda x: [x]},
                'comment': {'attr': 'setComment', 'convert': str},
                'albumartist': {'attr': 'setAlbumArtist', 'convert': str},  # Not listed in setInfo docs but included for forward compatibility
            }
        },
        'game': {
            'tag_getter': 'getGameInfoTag',
            'tag_attr': {
                'title': {'attr': 'setTitle', 'convert': str},
                'platform': {'attr': 'setPlatform', 'convert': str},
                'genres': {'attr': 'setGenres', 'convert': lambda x: [x]},
                'publisher': {'attr': 'setPublisher', 'convert': str},
                'developer': {'attr': 'setDeveloper', 'convert': str},
                'overview': {'attr': 'setOverview', 'convert': str},
                'year': {'attr': 'setYear', 'convert': int},
                'gameclient': {'attr': 'setGameClient', 'convert': str},
            }
        }
    }

    def __init__(self, listitem, tag_type: str = 'video'):
        self._listitem = listitem
        self._tag_type = tag_type
        self._tag_attr = self.INFO_TAG_ATTR[tag_type]['tag_attr']
        self._info_tag = getattr(self._listitem, self.INFO_TAG_ATTR[tag_type]['tag_getter'])()

    def set_info(self, infolabels: dict):
        """ Wrapper for compatibility with Matrix ListItem.setInfo() method """
        for k, v in infolabels.items():
            if v is None:
                continue
            try:
                func = getattr(self._info_tag, self._tag_attr[k]['attr'])
                func(v)
            except KeyError:
                if k not in self._tag_attr:
                    log_msg = f'[script.module.infotagger] set_info:\nKeyError: {k}'
                    kodi_log(log_msg, level=LOGINFO)
                    continue

                if self._tag_attr[k].get('skip'):
                    continue

                if 'route' in self._tag_attr[k]:
                    getattr(self, self._tag_attr[k]['route'])(v, infolabels)
                    continue

                log_msg = self._tag_attr[k].get('log_msg') or ''
                log_msg = f'[script.module.infotagger] set_info:\nKeyError: {log_msg}'
                kodi_log(log_msg, level=LOGINFO)
                continue

            except TypeError:
                func(self._tag_attr[k]['convert'](v))  # Attempt to force conversion to correct type

    def set_info_music_dbid(self, dbid: int, infolabels: dict, *args, **kwargs):
        """ Wrapper for InfoTagMusic.setDbId to retrieve mediatype """
        try:
            mediatype = infolabels['mediatype']
            self._info_tag.setDbId(int(dbid), mediatype)
        except (KeyError, TypeError):
            return

    def set_info_cast(self, cast: list, *args, **kwargs):
        """ Wrapper to convert cast and castandrole from ListItem.setInfo() to InfoTagVideo.setCast() """
        def _set_cast_member(x, i):
            if not isinstance(i, tuple):
                i = (i, '',)
            return {'name': f'{i[0]}', 'role': f'{i[1]}', 'order': x, 'thumbnail': ''}

        self._info_tag.setCast([Actor(**_set_cast_member(x, i)) for x, i in enumerate(cast, start=1)])

    def set_cast(self, cast: list):
        """ Wrapper for compatibility with Matrix ListItem.setCast() method """
        self._info_tag.setCast([Actor(**i) for i in cast])

    def set_unique_ids(self, unique_ids: dict, default_id: str = None):
        """ Wrapper for compatibility with Matrix ListItem.setUniqueIDs() method """
        self._info_tag.setUniqueIDs({k: f'{v}' for k, v in unique_ids.items()}, default_id)

    def set_stream_details(self, stream_details: dict):
        """ Wrapper for compatibility with multiple ListItem.addStreamInfo() methods in one call """
        if not stream_details:
            return

        try:
            for i in stream_details['video']:
                try:
                    self._info_tag.addVideoStream(VideoStreamDetail(**i))
                except TypeError:
                    # TEMP BANDAID workaround for inconsistent key names prior to Nexus Beta changes
                    i['hdrType'] = i.pop('hdrtype', '')
                    i['stereoMode'] = i.pop('stereomode', '')
                    self._info_tag.addVideoStream(VideoStreamDetail(**i))
        except (KeyError, TypeError):
            pass

        try:
            for i in stream_details['audio']:
                self._info_tag.addAudioStream(AudioStreamDetail(**i))
        except (KeyError, TypeError):
            pass

        try:
            for i in stream_details['subtitle']:
                self._info_tag.addSubtitleStream(SubtitleStreamDetail(**i))
        except (KeyError, TypeError):
            pass

    def add_stream_info(self, stream_type, stream_values):
        """ Wrapper for compatibility with Matrix ListItem.addStreamInfo() method """
        stream_details = {'video': [], 'audio': [], 'subtitle': []}
        stream_details[stream_type] = [stream_values]
        self.set_stream_details(stream_details)
