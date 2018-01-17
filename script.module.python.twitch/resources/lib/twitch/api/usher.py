# -*- encoding: utf-8 -*-
#  By using this module you are violating the Twitch TOS

from twitch import keys
from twitch.api.parameters import Boolean
from twitch.parser import m3u8, clip_embed
from twitch.queries import ClipsQuery, HiddenApiQuery, UsherQuery
from twitch.queries import query
from twitch.logging import log

from six.moves.urllib.parse import urlencode


def valid_video_id(video_id):
    if video_id.startswith('videos'):
        video_id = 'v' + video_id[6:]
    if video_id.startswith(('a', 'c', 'v')):
        return video_id[1:]
    return ''


@query
def channel_token(channel):
    q = HiddenApiQuery('channels/{channel}/access_token')
    q.add_urlkw(keys.CHANNEL, channel)
    q.add_param(keys.NEED_HTTPS, Boolean.TRUE)
    return q


@query
def vod_token(video_id):
    q = HiddenApiQuery('vods/{vod}/access_token')
    q.add_urlkw(keys.VOD, video_id)
    q.add_param(keys.NEED_HTTPS, Boolean.TRUE)
    return q


@query
def _legacy_video(video_id):
    q = HiddenApiQuery('videos/{id}')
    q.add_urlkw(keys.ID, video_id)
    return q


def live_request(channel):
    token = channel_token(channel)
    if keys.ERROR in token:
        return token
    else:
        q = UsherQuery('api/channel/hls/{channel}.m3u8')
        q.add_urlkw(keys.CHANNEL, channel)
        q.add_param(keys.SIG, token[keys.SIG])
        q.add_param(keys.TOKEN, token[keys.TOKEN])
        q.add_param(keys.ALLOW_SOURCE, Boolean.TRUE)
        q.add_param(keys.ALLOW_SPECTRE, Boolean.TRUE)
        q.add_param(keys.ALLOW_AUDIO_ONLY, Boolean.TRUE)
        url = '?'.join([q.url, urlencode(q.params)])
        request_dict = {'url': url, 'headers': q.headers}
        log.debug('live_request: |{0}|'.format(str(request_dict)))
        return request_dict


@query
def _live(channel, token):
    q = UsherQuery('api/channel/hls/{channel}.m3u8')
    q.add_urlkw(keys.CHANNEL, channel)
    q.add_param(keys.SIG, token[keys.SIG])
    q.add_param(keys.TOKEN, token[keys.TOKEN])
    q.add_param(keys.ALLOW_SOURCE, Boolean.TRUE)
    q.add_param(keys.ALLOW_SPECTRE, Boolean.TRUE)
    q.add_param(keys.ALLOW_AUDIO_ONLY, Boolean.TRUE)
    return q


@m3u8
def live(channel):
    token = channel_token(channel)
    if keys.ERROR in token:
        return token
    else:
        return _live(channel, token)


def video_request(video_id):
    video_id = valid_video_id(video_id)
    if video_id:
        token = vod_token(video_id)
        if keys.ERROR in token:
            return token
        else:
            q = UsherQuery('vod/{id}')
            q.add_urlkw(keys.ID, video_id)
            q.add_param(keys.NAUTHSIG, token[keys.SIG])
            q.add_param(keys.NAUTH, token[keys.TOKEN])
            q.add_param(keys.ALLOW_SOURCE, Boolean.TRUE)
            q.add_param(keys.ALLOW_AUDIO_ONLY, Boolean.TRUE)
            url = '?'.join([q.url, urlencode(q.params)])
            request_dict = {'url': url, 'headers': q.headers}
            log.debug('video_request: |{0}|'.format(str(request_dict)))
            return request_dict
    else:
        raise NotImplementedError('Unknown Video Type')


@query
def _vod(video_id, token):
    q = UsherQuery('vod/{id}')
    q.add_urlkw(keys.ID, video_id)
    q.add_param(keys.NAUTHSIG, token[keys.SIG])
    q.add_param(keys.NAUTH, token[keys.TOKEN])
    q.add_param(keys.ALLOW_SOURCE, Boolean.TRUE)
    q.add_param(keys.ALLOW_AUDIO_ONLY, Boolean.TRUE)
    return q


@m3u8
def video(video_id):
    video_id = valid_video_id(video_id)
    if video_id:
        token = vod_token(video_id)
        if keys.ERROR in token:
            return token
        else:
            return _vod(video_id, token)
    else:
        raise NotImplementedError('Unknown Video Type')


@clip_embed
@query
def clip(slug):
    q = ClipsQuery('embed')
    q.add_param(keys.CLIP, slug)
    return q
