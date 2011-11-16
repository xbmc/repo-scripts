#!/usr/bin/env python
from decorators import requires_or, validate_params
from objects import Video, Playlist, item_collection_factory
from core import get_item, Connection
try:
    import json
except ImportError:
    import simplejson as json

BASE_URL = 'http://api.brightcove.com/services'
READ_API_URL = '%s/library' % BASE_URL


class Brightcove(object):
    def __init__(self, token):
        self.token = token
        self.read_conn = Connection(token)

    def _read_api(self, command, params, cls=None):
        params.update({'command': command})
        resp = self.read_conn.get_request(READ_API_URL, params)
        _json = json.loads(resp)

        # try, ValueError if not json
        assert 'error' not in _json, 'API Error [%d]: %s' % (_json['code'],
                                                             _json['error'])
        if cls:
            return get_item(_json, cls)
        return _json

    # Video Read APIs
    def search_videos(self, all=None, any=None, none=None, sort_by=None,
                      exact=None, page_size=None, page_number=None,
                      get_item_count=None, video_fields=None,
                      custom_fields=None, media_delivery=None, output=None):
        ''' Returns an ItemCollection of Video results.

        See http://docs.brightcove.com/en/media/#search_videos for more
        information.
        '''
        params = validate_params(**locals())
        return self._read_api('search_videos', params,
                             cls=item_collection_factory(Video))

    def find_all_videos(self, page_size=None, page_number=None, sort_by=None,
                        sort_order=None, get_item_count=None,
                        video_fields=None, custom_fields=None,
                        media_delivery=None, output=None):
        ''' Returns an ItemCollection of Video results.
        '''
        params = validate_params(**locals())
        return self._read_api('find_all_videos', params,
                             cls=item_collection_factory(Video))

    def find_video_by_id(self, video_id, fields=None, video_fields=None,
                         custom_fields=None, media_delivery=None, output=None):
        params = validate_params(**locals())
        #return Video(**self._read_api('find_video_by_id', params))
        return self._read_api('find_video_by_id', params, cls=Video)

    @requires_or('video_id', 'reference_id')
    def find_related_videos(self, video_id=None, reference_id=None,
                            page_size=None, page_number=None,
                            get_item_count=None, fields=None,
                            video_fields=None, custom_fields=None,
                            media_deliver=None, output=None):

        params = validate_params(**locals())
        return self._read_api('find_related_videos', params,
                             cls=item_collection_factory(Video))

    def find_videos_by_ids(self, video_ids, fields=None, video_fields=None,
                           custom_fields=None, media_delivery=None,
                           output=None):
        params = validate_params(**locals())
        return self._read_api('find_videos_by_ids', params,
                             cls=item_collection_factory(Video))

    def find_video_by_reference_id(self, reference_id, fields=None,
                                   video_fields=None, custom_fields=None,
                                   media_delivery=None, output=None):
        params = validate_params(**locals())
        return self._read_api('find_video_by_reference_id', params, cls=Video)

    def find_videos_by_reference_ids(self, reference_ids, fields=None,
                                   video_fields=None, custom_fields=None,
                                   media_delivery=None, output=None):
        params = validate_params(**locals())
        return self._read_api('find_videos_by_reference_ids', params,
                             cls=item_collection_factory(Video))

    def find_videos_by_user_id(self, user_id, page_size=None, page_number=None,
                               sort_by=None, sort_order=None,
                               get_item_count=None, fields=None,
                               video_fields=None, custom_fields=None,
                               media_delivery=None, output=None):
        params = validate_params(**locals())
        return self._read_api('find_videos_by_user_id', params,
                             cls=item_collection_factory(Video))

    def find_videos_by_campaign_id(self, campaign_id, page_size=None,
                                   page_number=None, sort_by=None,
                                   sort_order=None, get_item_count=None,
                                   fields=None, video_fields=None,
                                   custom_fields=None, media_delivery=None,
                                   output=None):
        params = validate_params(**locals())
        return self._read_api('find_videos_by_campaign_id', params,
                             cls=item_collection_factory(Video))

    def find_modified_videos(self, from_date, filter=None, page_size=None,
                             page_number=None, sort_by=None, sort_order=None,
                             get_item_count=None, fields=None,
                             video_fields=None, custom_fields=None,
                             media_delivery=None, output=None):
        params = validate_params(**locals())
        return self._read_api('find_modified_videos', params,
                             cls=item_collection_factory(Video))

    def find_video_by_id_unfiltered(self, video_id, fields=None,
                                    video_fields=None, custom_fields=None,
                                    media_delivery=None):
        params = validate_params(**locals())
        return self._read_api('find_video_by_id_unfiltered', params, cls=Video)

    def find_video_by_ids_unfiltered(self, video_ids, fields=None,
                                    video_fields=None, custom_fields=None,
                                    media_delivery=None):
        params = validate_params(**locals())
        return self._read_api('find_video_by_ids_unfiltered', params,
                             cls=item_collection_factory(Video))

    def find_video_by_reference_id_unfiltered(self, reference_id, fields=None,
                                              video_fields=None,
                                              custom_fields=None,
                                              media_delivery=None):
        params = validate_params(**locals())
        return self._read_api('find_video_by_reference_id_unfiltered', params,
                             cls=Video)

    def find_videos_by_reference_ids_unfiltered(self, reference_ids,
                                               fields=None, video_fields=None,
                                               custom_fields=None,
                                               media_delivery=None):
        params = validate_params(**locals())
        return self._read_api('find_videos_by_reference_ids_unfiltered',
                              params, cls=item_collection_factory(Video))

    ## Playlist stuff
    def find_all_playlists(self, page_size=None, page_number=None,
                           sort_by=None, sort_order=None, get_item_count=None,
                           fields=None, video_fields=None,
                           playlist_fields=None, custom_fields=None,
                           media_delivery=None, output=None):
        params = validate_params(**locals())
        return self._read_api('find_all_playlists', params,
                             cls=item_collection_factory(Playlist))

    def find_playlist_by_id(self, playlist_id, fields=None, video_fields=None,
                            playlist_fields=None, custom_fields=None,
                            media_delivery=None, output=None):
        params = validate_params(**locals())
        return self._read_api('find_playlist_by__id', params, cls=Playlist)

    def find_playlist_by_ids(self, playlist_ids, fields=None,
                             video_fields=None, playlist_fields=None,
                             custom_fields=None, media_delivery=None,
                             output=None):
        params = validate_params(**locals())
        return self._read_api('find_playlist_by__id', params,
                             cls=item_collection_factory(Playlist))

    def find_playlist_by_reference_id(self, reference_id, fields=None,
                                      video_fields=None, playlist_fields=None,
                                      custom_fields=None, media_delivery=None,
                                      output=None):
        params = validate_params(**locals())
        return self._read_api('find_playlist_by_reference_id', params,
                             cls=Playlist)

    def find_playlist_by_reference_ids(self, reference_ids, fields=None,
                                      video_fields=None, playlist_fields=None,
                                      custom_fields=None, media_delivery=None,
                                      output=None):
        params = validate_params(**locals())
        return self._read_api('find_playlist_by_reference_ids', params,
                             cls=item_collection_factory(Playlist))

    def find_playlists_for_player_id(self, player_id, page_size=None,
                                     page_number=None, get_item_count=None,
                                     fields=None, video_fields=None,
                                     playlist_fields=None, custom_fields=None,
                                     media_delivery=None, output=None):
        params = validate_params(**locals())
        return self._read_api('find_playlists_for_player_id', params,
                             cls=item_collection_factory(Playlist))
