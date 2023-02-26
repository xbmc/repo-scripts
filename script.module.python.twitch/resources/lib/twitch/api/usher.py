# -*- encoding: utf-8 -*-
#  By using this module you are violating the Twitch TOS
"""

    Copyright (C) 2012-2016 python-twitch (https://github.com/ingwinlu/python-twitch)
    Copyright (C) 2016-2018 script.module.python.twitch

    This file is part of script.module.python.twitch

    SPDX-License-Identifier: GPL-3.0-only
    See LICENSES/GPL-3.0-only for more information.
"""

import json
from urllib.parse import urlencode

from .. import keys
from ..api.parameters import Boolean
from ..parser import m3u8, clip_embed
from ..queries import ClipsQuery, HiddenApiQuery, UsherQuery, GQLQuery
from ..queries import query
from ..log import log

ACCESS_TOKEN_EXCEPTION = {
    'error': 'Error',
    'message': 'Failed to retrieve access token',
    'status': 404
}


def get_access_token(token):
    stream_access_token = None
    video_access_token = None
    if isinstance(token, list):
        if token:
            data = token[0].get(keys.DATA, {})
            stream_access_token = data.get(keys.STREAM_PLAYBACK_ACCESS_TOKEN)
            video_access_token = data.get(keys.VIDEO_PLAYBACK_ACCESS_TOKEN)
    return stream_access_token or video_access_token or token


def valid_video_id(video_id):
    if video_id.startswith('videos'):
        video_id = 'v' + video_id[6:]
    if video_id.startswith(('a', 'c', 'v')):
        return video_id[1:]
    return video_id


@query
def channel_token(channel, platform=keys.WEB, headers={}):
    data = [{
        "operationName": "PlaybackAccessToken_Template",
        "query": "query PlaybackAccessToken_Template($login: String!, $isLive: Boolean!, $vodID: ID!, $isVod: Boolean!, $playerType: String!) {  streamPlaybackAccessToken(channelName: $login, params: {platform: \"web\", playerBackend: \"mediaplayer\", playerType: $playerType}) @include(if: $isLive) {    value    signature    __typename  }  videoPlaybackAccessToken(id: $vodID, params: {platform: \"web\", playerBackend: \"mediaplayer\", playerType: $playerType}) @include(if: $isVod) {    value    signature    __typename  }}",
        "variables": {
            "isLive": True,
            "login": channel,
            "isVod": False,
            "vodID": "",
            "playerType": "site"
        }
    }]
    q = GQLQuery('', headers=headers, data=data, use_token=True)
    return q


@query
def vod_token(video_id, platform=keys.WEB, headers={}):
    data = [{
        "operationName": "PlaybackAccessToken_Template",
        "query": "query PlaybackAccessToken_Template($login: String!, $isLive: Boolean!, $vodID: ID!, $isVod: Boolean!, $playerType: String!) {  streamPlaybackAccessToken(channelName: $login, params: {platform: \"web\", playerBackend: \"mediaplayer\", playerType: $playerType}) @include(if: $isLive) {    value    signature    __typename  }  videoPlaybackAccessToken(id: $vodID, params: {platform: \"web\", playerBackend: \"mediaplayer\", playerType: $playerType}) @include(if: $isVod) {    value    signature    __typename  }}",
        "variables": {
            "isLive": False,
            "login": "",
            "isVod": True,
            "vodID": video_id,
            "playerType": "site"
        }
    }]
    q = GQLQuery('', headers=headers, data=data, use_token=True)
    return q


@query
def _legacy_video(video_id):
    q = HiddenApiQuery('videos/{id}')
    q.add_urlkw(keys.ID, video_id)
    return q


def live_request(channel, platform=keys.WEB, headers={}):
    token = channel_token(channel, platform=platform, headers=headers)
    token = get_access_token(token)

    if not token:
        return ACCESS_TOKEN_EXCEPTION
    elif isinstance(token, dict) and 'error' in token:
        return token
    else:
        signature = token[keys.SIGNATURE]
        access_token = token[keys.VALUE]
        q = UsherQuery('api/channel/hls/{channel}.m3u8', headers=headers)
        q.add_urlkw(keys.CHANNEL, channel)
        q.add_param(keys.SIG, signature.encode('utf-8'))
        q.add_param(keys.TOKEN, access_token.encode('utf-8'))
        q.add_param(keys.ALLOW_SOURCE, Boolean.TRUE)
        q.add_param(keys.ALLOW_SPECTRE, Boolean.TRUE)
        q.add_param(keys.ALLOW_AUDIO_ONLY, Boolean.TRUE)
        q.add_param(keys.FAST_BREAD, Boolean.TRUE)
        q.add_param(keys.CDM, keys.WV)
        q.add_param(keys.REASSIGNMENT_SUPPORTED, Boolean.TRUE)
        q.add_param(keys.PLAYLIST_INCLUDE_FRAMERATE, Boolean.TRUE)
        q.add_param(keys.RTQOS, keys.CONTROL)
        q.add_param(keys.PLAYER_BACKEND, keys.MEDIAPLAYER)
        url = '?'.join([q.url, urlencode(q.params)])
        request_dict = {
            'url': url,
            'headers': q.headers
        }
        log.debug('live_request: |{0}|'.format(str(request_dict)))
        return request_dict


@query
def _live(channel, token, headers={}):
    signature = token[keys.SIGNATURE]
    access_token = token[keys.VALUE]

    q = UsherQuery('api/channel/hls/{channel}.m3u8', headers=headers)
    q.add_urlkw(keys.CHANNEL, channel)
    q.add_param(keys.SIG, signature.encode('utf-8'))
    q.add_param(keys.TOKEN, access_token.encode('utf-8'))
    q.add_param(keys.ALLOW_SOURCE, Boolean.TRUE)
    q.add_param(keys.ALLOW_SPECTRE, Boolean.TRUE)
    q.add_param(keys.ALLOW_AUDIO_ONLY, Boolean.TRUE)
    q.add_param(keys.FAST_BREAD, Boolean.TRUE)
    q.add_param(keys.CDM, keys.WV)
    q.add_param(keys.REASSIGNMENT_SUPPORTED, Boolean.TRUE)
    q.add_param(keys.PLAYLIST_INCLUDE_FRAMERATE, Boolean.TRUE)
    q.add_param(keys.RTQOS, keys.CONTROL)
    q.add_param(keys.PLAYER_BACKEND, keys.MEDIAPLAYER)
    return q


@m3u8
def live(channel, platform=keys.WEB, headers={}):
    token = channel_token(channel, platform=platform, headers=headers)
    token = get_access_token(token)
    if not token:
        return ACCESS_TOKEN_EXCEPTION
    elif isinstance(token, dict) and 'error' in token:
        return token
    else:
        return _live(channel, token, headers=headers)


def video_request(video_id, platform=keys.WEB, headers={}):
    video_id = valid_video_id(video_id)
    if video_id:
        token = vod_token(video_id, platform=platform, headers=headers)
        token = get_access_token(token)

        if not token:
            return ACCESS_TOKEN_EXCEPTION
        elif isinstance(token, dict) and 'error' in token:
            return token
        else:
            signature = token[keys.SIGNATURE]
            access_token = token[keys.VALUE]
            q = UsherQuery('vod/{id}', headers=headers)
            q.add_urlkw(keys.ID, video_id)
            q.add_param(keys.NAUTHSIG, signature.encode('utf-8'))
            q.add_param(keys.NAUTH, access_token.encode('utf-8'))
            q.add_param(keys.ALLOW_SOURCE, Boolean.TRUE)
            q.add_param(keys.ALLOW_AUDIO_ONLY, Boolean.TRUE)
            q.add_param(keys.CDM, keys.WV)
            q.add_param(keys.REASSIGNMENT_SUPPORTED, Boolean.TRUE)
            q.add_param(keys.PLAYLIST_INCLUDE_FRAMERATE, Boolean.TRUE)
            q.add_param(keys.RTQOS, keys.CONTROL)
            q.add_param(keys.PLAYER_BACKEND, keys.MEDIAPLAYER)
            q.add_param(keys.BAKING_BREAD, Boolean.TRUE)
            q.add_param(keys.BAKING_BROWNIES, Boolean.TRUE)
            q.add_param(keys.BAKING_BROWNIES_TIMEOUT, 1050)
            url = '?'.join([q.url, urlencode(q.params)])
            request_dict = {
                'url': url,
                'headers': q.headers
            }
            log.debug('video_request: |{0}|'.format(str(request_dict)))
            return request_dict
    else:
        raise NotImplementedError('Unknown Video Type')


@query
def _vod(video_id, token, headers={}):
    signature = token[keys.SIGNATURE]
    access_token = token[keys.VALUE]

    q = UsherQuery('vod/{id}', headers=headers)
    q.add_urlkw(keys.ID, video_id)
    q.add_param(keys.NAUTHSIG, signature.encode('utf-8'))
    q.add_param(keys.NAUTH, access_token.encode('utf-8'))
    q.add_param(keys.ALLOW_SOURCE, Boolean.TRUE)
    q.add_param(keys.ALLOW_AUDIO_ONLY, Boolean.TRUE)
    q.add_param(keys.CDM, keys.WV)
    q.add_param(keys.REASSIGNMENT_SUPPORTED, Boolean.TRUE)
    q.add_param(keys.PLAYLIST_INCLUDE_FRAMERATE, Boolean.TRUE)
    q.add_param(keys.RTQOS, keys.CONTROL)
    q.add_param(keys.PLAYER_BACKEND, keys.MEDIAPLAYER)
    q.add_param(keys.BAKING_BREAD, Boolean.TRUE)
    q.add_param(keys.BAKING_BROWNIES, Boolean.TRUE)
    q.add_param(keys.BAKING_BROWNIES_TIMEOUT, 1050)
    return q


@m3u8
def video(video_id, platform=keys.WEB, headers={}):
    video_id = valid_video_id(video_id)
    if video_id:
        token = vod_token(video_id, platform=platform, headers=headers)
        token = get_access_token(token)

        if not token:
            return ACCESS_TOKEN_EXCEPTION
        elif isinstance(token, dict) and 'error' in token:
            return token
        else:
            return _vod(video_id, token, headers=headers)
    else:
        raise NotImplementedError('Unknown Video Type')


@clip_embed
@query
def clip(slug, headers={}):
    qry = {
        "operationName": "VideoAccessToken_Clip",
        "extensions": {
            "persistedQuery": {
                "version": 1,
                "sha256Hash": "36b89d2507fce29e5ca551df756d27c1cfe079e2609642b4390aa4c35796eb11"
            }
        },
        "variables": {
            "slug": slug
        }
    }

    q = ClipsQuery(headers=headers, data=json.dumps(qry))
    return q
