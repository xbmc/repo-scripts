'''Contains the Brightcove class which encapsulates all of the available
read-only API methods.

'''
try:
    import json
except ImportError:
    import simplejson as json
from brightcove.core import get_item, Connection
from brightcove.utils import requires_or, validate_params
from brightcove.objects import (Video, Playlist, VideoItemCollection,
                                PlaylistItemCollection)


BASE_URL = 'http://api.brightcove.com/services'
READ_API_URL = '%s/library' % BASE_URL


class Brightcove(object):
    '''Contains all of the read-only API methods. An instance handles appending
    the token query string parameter to all API calls.

    '''
    def __init__(self, token):
        self.token = token
        self.read_conn = Connection(token)

    def _read_api(self, command, params, cls=None):
        '''Pases the JSON response for a given API command to a constructor of
        the provided cls and returns the result.

        '''
        params.update({'command': command})
        resp = self.read_conn.get_request(READ_API_URL, params)
        _json = json.loads(resp)

        # try, ValueError if not json
        assert 'error' not in _json, 'API Error [%d]: %s' % (_json['code'],
                                                             _json['error'])
        if cls:
            return get_item(_json, cls)
        return _json

    def search_videos(self, all=None, any=None, none=None, sort_by=None,
                      exact=None, page_size=None, page_number=None,
                      get_item_count=None, video_fields=None,
                      custom_fields=None, media_delivery=None, output=None):
        ''' Returns an VideoItemCollection of Video results.'''
        params = validate_params(**locals())
        return self._read_api('search_videos', params, cls=VideoItemCollection)

    def find_all_videos(self, page_size=None, page_number=None, sort_by=None,
                        sort_order=None, get_item_count=None,
                        video_fields=None, custom_fields=None,
                        media_delivery=None, output=None):
        ''' Returns an VideoItemCollection of Video results.'''
        params = validate_params(**locals())
        return self._read_api('find_all_videos', params,
                              cls=VideoItemCollection)

    def find_video_by_id(self, video_id, fields=None, video_fields=None,
                         custom_fields=None, media_delivery=None, output=None):
        '''Returns a Video.'''
        params = validate_params(**locals())
        return self._read_api('find_video_by_id', params, cls=Video)

    @requires_or('video_id', 'reference_id')
    def find_related_videos(self, video_id=None, reference_id=None,
                            page_size=None, page_number=None,
                            get_item_count=None, fields=None,
                            video_fields=None, custom_fields=None,
                            media_deliver=None, output=None):
        '''Returns a VideoItemCollection of Videos. Requires either video_id or
        reference_id.

        '''
        params = validate_params(**locals())
        return self._read_api('find_related_videos', params,
                              cls=VideoItemCollection)

    def find_videos_by_ids(self, video_ids, fields=None, video_fields=None,
                           custom_fields=None, media_delivery=None,
                           output=None):
        '''Returns a VideoItemCollection of Videos.'''
        params = validate_params(**locals())
        return self._read_api('find_videos_by_ids', params,
                              cls=VideoItemCollection)

    def find_video_by_reference_id(self, reference_id, fields=None,
                                   video_fields=None, custom_fields=None,
                                   media_delivery=None, output=None):
        '''Returns a Video.'''
        params = validate_params(**locals())
        return self._read_api('find_video_by_reference_id', params, cls=Video)

    def find_videos_by_reference_ids(self, reference_ids, fields=None,
                                   video_fields=None, custom_fields=None,
                                   media_delivery=None, output=None):
        '''Returns a VideoItemCollection of Videos.'''
        params = validate_params(**locals())
        return self._read_api('find_videos_by_reference_ids', params,
                              cls=VideoItemCollection)

    def find_videos_by_user_id(self, user_id, page_size=None, page_number=None,
                               sort_by=None, sort_order=None,
                               get_item_count=None, fields=None,
                               video_fields=None, custom_fields=None,
                               media_delivery=None, output=None):
        '''Returns a VideoItemCollection of Videos.'''
        params = validate_params(**locals())
        return self._read_api('find_videos_by_user_id', params,
                              cls=VideoItemCollection)

    def find_videos_by_campaign_id(self, campaign_id, page_size=None,
                                   page_number=None, sort_by=None,
                                   sort_order=None, get_item_count=None,
                                   fields=None, video_fields=None,
                                   custom_fields=None, media_delivery=None,
                                   output=None):
        '''Returns a VideoItemCollection of Videos.'''
        params = validate_params(**locals())
        return self._read_api('find_videos_by_campaign_id', params,
                              cls=VideoItemCollection)

    def find_modified_videos(self, from_date, filter=None, page_size=None,
                             page_number=None, sort_by=None, sort_order=None,
                             get_item_count=None, fields=None,
                             video_fields=None, custom_fields=None,
                             media_delivery=None, output=None):
        '''Returns a VideoItemCollection of Videos. from_date should be an
        integer or string specified in minutes since January 1st, 1970 00:00:00
        GMT.

        '''
        params = validate_params(**locals())
        return self._read_api('find_modified_videos', params,
                              cls=VideoItemCollection)

    def find_video_by_id_unfiltered(self, video_id, fields=None,
                                    video_fields=None, custom_fields=None,
                                    media_delivery=None):
        '''Returns a VideoItemCollection of Videos.'''
        params = validate_params(**locals())
        return self._read_api('find_video_by_id_unfiltered', params, cls=Video)

    def find_video_by_ids_unfiltered(self, video_ids, fields=None,
                                    video_fields=None, custom_fields=None,
                                    media_delivery=None):
        '''Returns a VideoItemCollection of Videos.'''
        params = validate_params(**locals())
        return self._read_api('find_video_by_ids_unfiltered', params,
                              cls=VideoItemCollection)

    def find_video_by_reference_id_unfiltered(self, reference_id, fields=None,
                                              video_fields=None,
                                              custom_fields=None,
                                              media_delivery=None):
        '''Returns a Video.'''
        params = validate_params(**locals())
        return self._read_api('find_video_by_reference_id_unfiltered', params,
                              cls=Video)

    def find_videos_by_reference_ids_unfiltered(self, reference_ids,
                                               fields=None, video_fields=None,
                                               custom_fields=None,
                                               media_delivery=None):
        '''Returns a VideoItemCollection of Videos.'''
        params = validate_params(**locals())
        return self._read_api('find_videos_by_reference_ids_unfiltered',
                              params, cls=VideoItemCollection)

    ## Playlist stuff
    def find_all_playlists(self, page_size=None, page_number=None,
                           sort_by=None, sort_order=None, get_item_count=None,
                           fields=None, video_fields=None,
                           playlist_fields=None, custom_fields=None,
                           media_delivery=None, output=None):
        '''Returns a PlaylistItemCollection of Playlists.'''
        params = validate_params(**locals())
        return self._read_api('find_all_playlists', params,
                              cls=PlaylistItemCollection)

    def find_playlist_by_id(self, playlist_id, fields=None, video_fields=None,
                            playlist_fields=None, custom_fields=None,
                            media_delivery=None, output=None):
        '''Returns a Playlist.'''
        params = validate_params(**locals())
        return self._read_api('find_playlist_by_id', params, cls=Playlist)

    def find_playlists_by_ids(self, playlist_ids, fields=None,
                              video_fields=None, playlist_fields=None,
                              custom_fields=None, media_delivery=None,
                              output=None):
        '''Returns a PlaylistItemCollection of Playlists.'''
        params = validate_params(**locals())
        return self._read_api('find_playlists_by_ids', params,
                              cls=PlaylistItemCollection)

    def find_playlist_by_reference_id(self, reference_id, fields=None,
                                      video_fields=None, playlist_fields=None,
                                      custom_fields=None, media_delivery=None,
                                      output=None):
        '''Returns a Playlist.'''
        params = validate_params(**locals())
        return self._read_api('find_playlist_by_reference_id', params,
                              cls=Playlist)

    def find_playlists_by_reference_ids(self, reference_ids, fields=None,
                                        video_fields=None,
                                        playlist_fields=None,
                                        custom_fields=None,
                                        media_delivery=None,
                                        output=None):
        '''Returns a PlaylistItemCollection of Playlists.'''
        params = validate_params(**locals())
        return self._read_api('find_playlists_by_reference_ids', params,
                              cls=PlaylistItemCollection)

    def find_playlists_for_player_id(self, player_id, page_size=None,
                                     page_number=None, get_item_count=None,
                                     fields=None, video_fields=None,
                                     playlist_fields=None, custom_fields=None,
                                     media_delivery=None, output=None):
        '''Returns a PlaylistItemCollection of Playlists.'''
        params = validate_params(**locals())
        return self._read_api('find_playlists_for_player_id', params,
                              cls=PlaylistItemCollection)
