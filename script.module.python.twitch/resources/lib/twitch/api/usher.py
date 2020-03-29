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

from .. import keys
from ..api.parameters import Boolean
from ..parser import m3u8, clip_embed
from ..queries import ClipsQuery, HiddenApiQuery, UsherQuery
from ..queries import query
from ..log import log

from six.moves.urllib.parse import urlencode


def valid_video_id(video_id):
    if video_id.startswith('videos'):
        video_id = 'v' + video_id[6:]
    if video_id.startswith(('a', 'c', 'v')):
        return video_id[1:]
    return ''


@query
def channel_token(channel, platform=keys.WEB, headers={}):
    q = HiddenApiQuery('channels/{channel}/access_token', headers=headers)
    q.add_urlkw(keys.CHANNEL, channel)
    q.add_param(keys.NEED_HTTPS, Boolean.TRUE)
    q.add_param(keys.PLATFORM, platform)
    q.add_param(keys.PLAYER_BACKEND, keys.MEDIAPLAYER)
    return q


@query
def vod_token(video_id, platform=keys.WEB, headers={}):
    q = HiddenApiQuery('vods/{vod}/access_token', headers=headers)
    q.add_urlkw(keys.VOD, video_id)
    q.add_param(keys.NEED_HTTPS, Boolean.TRUE)
    q.add_param(keys.PLATFORM, platform)
    q.add_param(keys.PLAYER_BACKEND, keys.MEDIAPLAYER)
    return q


@query
def _legacy_video(video_id):
    q = HiddenApiQuery('videos/{id}')
    q.add_urlkw(keys.ID, video_id)
    return q


def live_request(channel, platform=keys.WEB, headers={}):
    token = channel_token(channel, platform=platform, headers=headers)
    if keys.ERROR in token:
        return token
    else:
        q = UsherQuery('api/channel/hls/{channel}.m3u8', headers=headers)
        q.add_urlkw(keys.CHANNEL, channel)
        q.add_param(keys.SIG, token[keys.SIG].encode('utf-8'))
        q.add_param(keys.TOKEN, token[keys.TOKEN].encode('utf-8'))
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
        request_dict = {'url': url, 'headers': q.headers}
        log.debug('live_request: |{0}|'.format(str(request_dict)))
        return request_dict


@query
def _live(channel, token, headers={}):
    q = UsherQuery('api/channel/hls/{channel}.m3u8', headers=headers)
    q.add_urlkw(keys.CHANNEL, channel)
    q.add_param(keys.SIG, token[keys.SIG].encode('utf-8'))
    q.add_param(keys.TOKEN, token[keys.TOKEN].encode('utf-8'))
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
    if keys.ERROR in token:
        return token
    else:
        return _live(channel, token, headers=headers)


def video_request(video_id, platform=keys.WEB, headers={}):
    video_id = valid_video_id(video_id)
    if video_id:
        token = vod_token(video_id, platform=platform, headers=headers)
        if keys.ERROR in token:
            return token
        else:
            q = UsherQuery('vod/{id}', headers=headers)
            q.add_urlkw(keys.ID, video_id)
            q.add_param(keys.NAUTHSIG, token[keys.SIG].encode('utf-8'))
            q.add_param(keys.NAUTH, token[keys.TOKEN].encode('utf-8'))
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
            request_dict = {'url': url, 'headers': q.headers}
            log.debug('video_request: |{0}|'.format(str(request_dict)))
            return request_dict
    else:
        raise NotImplementedError('Unknown Video Type')


@query
def _vod(video_id, token, headers={}):
    q = UsherQuery('vod/{id}', headers=headers)
    q.add_urlkw(keys.ID, video_id)
    q.add_param(keys.NAUTHSIG, token[keys.SIG].encode('utf-8'))
    q.add_param(keys.NAUTH, token[keys.TOKEN].encode('utf-8'))
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
        if keys.ERROR in token:
            return token
        else:
            return _vod(video_id, token, headers=headers)
    else:
        raise NotImplementedError('Unknown Video Type')


@clip_embed
@query
def clip(slug, headers={}):
    data = json.dumps({
        'query': '''{
      clip(slug: "%s") {
        broadcaster {
          displayName
        }
        createdAt
        curator {
          displayName
          id
        }
        durationSeconds
        id
        tiny: thumbnailURL(width: 86, height: 45)
        small: thumbnailURL(width: 260, height: 147)
        medium: thumbnailURL(width: 480, height: 272)
        title
        videoQualities {
          frameRate
          quality
          sourceURL
        }
        viewCount
      }
    }''' % slug,
    })
    q = ClipsQuery(headers=headers, data=data)
    return q
