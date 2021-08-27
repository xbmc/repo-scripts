# -*- coding: utf-8 -*-
"""
    Copyright (C) 2020 Tubed API (script.module.tubed.api)

    This file is part of script.module.tubed.api

    SPDX-License-Identifier: GPL-2.0-only
    See LICENSES/GPL-2.0-only.txt for more information.
"""

import json
import operator
import re
from copy import deepcopy
from html import escape
from urllib.parse import parse_qsl
from urllib.parse import unquote

import xbmcaddon  # pylint: disable=import-error
import xbmcgui  # pylint: disable=import-error
import xbmcvfs  # pylint: disable=import-error

from ...utils.logger import Log
from .quality import Quality

LOG = Log('usher', __file__)


class ManifestGenerator:
    path = xbmcvfs.translatePath('special://temp/script.module.tubed.api/')

    def __init__(self, itags, cipher, calculate_n, license_data=None):
        self.addon = xbmcaddon.Addon('script.module.tubed.api')

        self._cipher = cipher
        self.calculate_n = calculate_n
        self._itags = itags
        self._discarded = []
        if license_data is None:
            license_data = {}
        self.license_data = license_data

        self.component_logging = self.addon.getSettingBool('log.manifest.generator')

    @property
    def cipher(self):
        return self._cipher

    @property
    def itags(self):
        return self._itags

    @property
    def discarded(self):
        return self._discarded

    @discarded.setter
    def discarded(self, value):
        self._discarded.append(value)

    def _make_dirs(self):
        if not xbmcvfs.exists(self.path):
            _ = xbmcvfs.mkdirs(self.path)

        return xbmcvfs.exists(self.path)

    def discard_audio(self, fmt, mime_type, itag, stream, reason='unsupported'):
        discarded = {
            'audio': {
                'itag': str(itag),
                'mime': str(mime_type),
                'codec': str(stream['codec']),
                'bandwidth': int(stream['bandwidth'])
            },
            'reason': reason
        }

        if fmt:
            bitrate = int(fmt.get('audio', {}).get('bitrate', 0))
            if bitrate > 0:
                discarded['audio']['bitrate'] = bitrate

        self.discarded = discarded

    def discard_video(self, mime_type, itag, stream, reason='unsupported'):
        discarded = {
            'video': {
                'itag': str(itag),
                'width': str(stream['width']),
                'height': str(stream['height']),
                'fps': str(stream['frameRate']),
                'codec': str(stream['codec']),
                'mime': str(mime_type),
                'bandwidth': int(stream['bandwidth'])
            },
            'reason': reason
        }

        if stream.get('quality_label'):
            discarded['video']['quality_label'] = str(stream['quality_label'])

        self.discarded = discarded

    def _filter_qualities(self, stream_data, container, quality_object):
        data = deepcopy(stream_data)

        height_to_width_map = {
            4320: 7680,
            2160: 3840,
            1440: 2560,
            1080: 1920,
            720: 1280,
            480: 854,
            426: 240,
        }

        rng = 1 if container == 'mp4' else 2

        for idx in range(rng):
            mime_mp4 = 'video/mp4'
            mime_webm = 'video/webm'
            if container == 'mp4' or (container == 'webm' and idx == 1):
                discard_mime = mime_webm
                discarded_mime_streams = data[mime_webm]

                selected_mime = mime_mp4
                streams = deepcopy(data[mime_mp4])
            elif container == 'webm':
                discard_mime = mime_mp4
                discarded_mime_streams = data[mime_mp4]

                selected_mime = mime_webm
                streams = deepcopy(data[mime_webm])

                if not streams:
                    discard_mime = mime_webm
                    discarded_mime_streams = data[mime_webm]

                    selected_mime = mime_mp4
                    streams = deepcopy(data[mime_mp4])
            else:
                return data

            thirty_fps_streams = [streams[itag] for itag in list(streams.keys())
                                  if streams[itag].get('fps') <= 30]

            sixty_fps_streams = [streams[itag] for itag in list(streams.keys())
                                 if streams[itag].get('fps') > 30]

            fps_streams = sixty_fps_streams
            if (not quality_object.limit_30fps and not sixty_fps_streams) or \
                    quality_object.limit_30fps:
                fps_streams = thirty_fps_streams

            quality_streams = []

            for quality in quality_object.qualities:
                # find all streams with matching width
                matches = [stream for stream in fps_streams
                           if int(stream.get('width', 0)) == height_to_width_map.get(quality, -1)]

                if matches:
                    quality_streams.extend(matches)
                    continue

            if not quality_streams:
                continue

            quality_streams.sort(key=operator.itemgetter('bandwidth'), reverse=True)
            quality_streams.sort(key=operator.itemgetter('width'), reverse=True)

            selected_stream = quality_streams[0]
            selected_itag = selected_stream.get('id', -1)

            for itag in list(streams.keys()):
                # discard all streams except the best match
                if itag != selected_itag:
                    self.discard_video(selected_mime, itag, streams[itag], 'quality')
                    del data[selected_mime][itag]

            if discarded_mime_streams:
                # discard streams with unwanted mime type
                for itag in list(discarded_mime_streams.keys()):
                    self.discard_video(discard_mime, itag,
                                       discarded_mime_streams[itag], 'mime type')
                    del data[discard_mime][itag]

            break

        return data

    def _stream_data(self, formats):
        data = {}
        for item in formats:
            stream_map = item

            stream_map.update(dict(parse_qsl(item.get('signatureCipher', item.get('cipher', '')))))
            stream_map['itag'] = str(stream_map.get('itag'))

            mime_type = stream_map.get('mimeType')
            mime_type = unquote(mime_type).split(';')

            key = mime_type[0]
            itag = stream_map.get('itag')

            if key not in data:
                data[key] = {}
            data[key][itag] = {}

            codec = str(mime_type[1][1:])
            data[key][itag]['codec'] = codec

            match = re.search('codecs="(?P<codec>[^"]+)"', codec)
            if match:
                data[key][itag]['codec'] = match.group('codec')

            data[key][itag]['id'] = itag

            data[key][itag]['width'] = stream_map.get('width')
            data[key][itag]['height'] = stream_map.get('height')

            data[key][itag]['quality_label'] = str(stream_map.get('qualityLabel'))

            data[key][itag]['bandwidth'] = stream_map.get('bitrate', 0)

            # map frame rates to a more common representation to
            # lessen the chance of double refresh changes sometimes
            # 30 fps is 30 fps, more commonly it is 29.97 fps (same for all mapped frame rates)
            frame_rate = None
            fps_scale_map = {
                24: 1001,
                30: 1001,
                60: 1001
            }

            if 'fps' in stream_map:
                fps = int(stream_map.get('fps'))
                data[key][itag]['fps'] = fps
                scale = fps_scale_map.get(fps, 1000)
                frame_rate = '%d/%d' % (fps * 1000, scale)

            data[key][itag]['frameRate'] = frame_rate

            url = unquote(stream_map.get('url'))

            signature_parameter = '&signature='
            if 'sp' in stream_map:
                signature_parameter = '&%s=' % stream_map['sp']

            if 'sig' in stream_map:
                url = ''.join([url, signature_parameter, stream_map['sig']])

            elif 's' in stream_map:
                url = ''.join([url, signature_parameter, self.cipher.signature(stream_map['s'])])

            url = self.calculate_n(url)
            url = url.replace("&", "&amp;").replace('"', "&quot;")
            url = url.replace("<", "&lt;").replace(">", "&gt;")

            data[key][itag]['baseUrl'] = url

            data[key][itag]['indexRange'] = '0-0'
            data[key][itag]['initRange'] = '0-0'

            if 'indexRange' in stream_map and 'initRange' in stream_map:
                data[key][itag]['indexRange'] = \
                    '-'.join([stream_map.get('indexRange').get('start'),
                              stream_map.get('indexRange').get('end')])

                data[key][itag]['init'] = \
                    '-'.join([stream_map.get('initRange').get('start'),
                              stream_map.get('initRange').get('end')])

            if ('indexRange' not in stream_map or
                    'initRange' not in stream_map or
                    data[key][itag].get('indexRange') == '0-0' and
                    data[key][itag].get('initRange') == '0-0'):

                if key.startswith('video'):
                    self.discard_video(key, itag, data[key][itag], 'no init or index')

                else:
                    stream_format = self.itags.get(itag, {})
                    self.discard_audio(stream_format, key, itag,
                                       data[key][itag], 'no init or index')

                del data[key][itag]

        return data

    def _filter_av1(self, data):
        data = deepcopy(data)
        payload = {}

        for itag in data.keys():
            if data[itag]['codec'].lower().startswith(('av01', 'av1')):
                continue

            payload[itag] = data[itag]

        discarded = [data[itag] for itag in (set(data) - set(payload)) if itag in data]

        for discard in discarded:
            self.discard_video('video/mp4', discard['id'],
                               data[discard['id']], 'av1 unsupported')

        return payload

    def _filter_hdr(self, data, hdr=False):
        data = deepcopy(data)
        webm = {}

        if hdr and any(itag for itag in data.keys()
                       if 'vp9.2' in data[itag]['codec']):
            # when hdr enabled and available replace vp9 streams with vp9.2 (hdr)
            for itag in data.keys():
                if 'vp9.2' in data[itag]['codec']:
                    webm[itag] = data[itag]

            discarded = [data[itag] for itag in (set(data) - set(webm)) if itag in data]

            for discard in discarded:
                self.discard_video('video/webm', discard['id'],
                                   data[discard['id']], 'replaced by hdr')

        elif not hdr:
            # when hdr disabled and remove vp9.2 (hdr) streams
            for itag in data.keys():
                if 'vp9.2' in data[itag]['codec']:
                    continue

                webm[itag] = data[itag]

            discarded = [data[itag] for itag in (set(data) - set(webm)) if itag in data]

            for discard in discarded:
                self.discard_video('video/webm', discard['id'],
                                   data[discard['id']], 'hdr disabled')

        return webm

    @staticmethod
    def _stream_info_template():
        return {
            'video': {
                'height': '0',
                'fps': '0',
                'codec': '',
                'mime': '',
                'quality_label': '',
                'bandwidth': 0
            },
            'audio': {
                'bitrate': '0',
                'codec': '',
                'mime': '',
                'bandwidth': 0
            }
        }

    def generate(self, video_id, formats, duration, quality_object=None):  # pylint: disable=too-many-branches,too-many-statements,too-many-locals
        LOG.debug('Generating MPEG-DASH manifest for %s' % video_id)

        if self.component_logging:
            LOG.debug('Stream information available for %s MPEG-DASH manifest:\n%s' %
                      (video_id, json.dumps(formats, indent=4)))

        if not self._make_dirs():
            return None

        if not quality_object:
            quality_object = Quality('mp4')

        has_video_stream = False

        stream_info = self._stream_info_template()
        data = self._stream_data(formats)

        if not data.get('video/mp4') and not data.get('video/webm'):
            return None, None

        default_mime_type = 'mp4'
        supported_mime_types = []

        if data.get('video/mp4'):
            supported_mime_types.append('video/mp4')

        if data.get('audio/mp4'):
            supported_mime_types.append('audio/mp4')

        if any(mime for mime in data if mime == 'video/webm') and data.get('video/webm'):
            supported_mime_types.append('video/webm')

        if ('video/webm' in supported_mime_types and
                ((isinstance(quality_object.quality, str) and quality_object.quality == 'webm') or
                 (isinstance(quality_object.quality, int) and quality_object.quality > 1080) or
                 quality_object.hdr)):
            default_mime_type = 'webm'

        av1_filtered = self._filter_av1(data.get('video/mp4', {}))
        if av1_filtered:
            data['video/mp4'] = av1_filtered

        hdr_filtered = self._filter_hdr(data.get('video/webm', {}), hdr=quality_object.hdr)
        if hdr_filtered:
            data['video/webm'] = hdr_filtered

        if isinstance(quality_object.quality, int) and isinstance(quality_object.qualities, list):
            data = self._filter_qualities(data, default_mime_type, quality_object)

        mpd_list = ['<?xml version="1.0" encoding="UTF-8"?>\n'
                    '<MPD xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" '
                    'xmlns="urn:mpeg:dash:schema:mpd:2011" '
                    'xmlns:xlink="http://www.w3.org/1999/xlink" '
                    'xsi:schemaLocation="urn:mpeg:dash:schema:mpd:2011 '
                    'http://standards.iso.org/ittf/PubliclyAvailableStandards/'
                    'MPEG-DASH_schema_files/DASH-MPD.xsd" '
                    'minBufferTime="PT1.5S" mediaPresentationDuration="PT', duration,
                    'S" type="static" profiles="urn:mpeg:dash:profile:isoff-main:2011">\n',
                    '\t<Period>\n']

        adaptation_set_idx = 0
        for key in data:  # pylint: disable=too-many-nested-blocks
            if "_" in key:
                mime, lang = key.split("_")
            else:
                mime = key
                lang = None

            if mime in supported_mime_types:
                default = False
                if mime.endswith(default_mime_type):
                    default = True

                mpd_list.append(''.join(['\t\t<AdaptationSet id="', str(adaptation_set_idx),
                                         '" mimeType="', mime, '" ']))
                if lang is not None:
                    # Avoid default language selection as it confuses the language selection in Kodi
                    default = False
                    mpd_list.append(''.join(['lang="', lang, '" ']))

                mpd_list.append(''.join(['subsegmentAlignment="true" subsegmentStartsWithSAP="1" '
                                         'bitstreamSwitching="true" default="',
                                         str(default).lower(), '">\n']))

                license_url = self.license_data.get('license_url')
                if license_url:
                    mpd_list.append(''.join(['\t\t\t<ContentProtection schemeIdUri='
                                             '"http://youtube.com/drm/2012/10/10">\n',
                                             '\t\t\t\t<yt:SystemURL type="widevine">',
                                             escape(license_url), '</yt:SystemURL>\n',
                                             '\t\t\t</ContentProtection>\n']))

                mpd_list.append('\t\t\t<Role schemeIdUri="urn:mpeg:DASH:role:2011" '
                                'value="main"/>\n')

                for itag in data[key]:
                    stream_format = self.itags.get(itag, {})
                    if 'audio' in mime:

                        audio_codec = data[key][itag]['codec']
                        if audio_codec.lower() == 'opus':
                            self.discard_audio(stream_format, mime, itag, data[key][itag])
                            continue

                        if audio_codec.lower() == 'vorbis':
                            self.discard_audio(stream_format, mime, itag, data[key][itag])
                            continue

                        if (int(data[key][itag]['bandwidth']) >
                                int(stream_info['audio']['bandwidth'])):

                            stream_info['audio']['mime'] = str(mime)
                            if stream_format:

                                bitrate = int(stream_format.get('audio', {}).get('bitrate', 0))
                                if bitrate > 0:
                                    stream_info['audio']['bitrate'] = bitrate

                                stream_info['audio']['codec'] = \
                                    stream_format.get('audio', {}).get('encoding')

                            if not stream_info['audio'].get('codec'):
                                stream_info['audio']['codec'] = audio_codec

                            stream_info['audio']['bandwidth'] = int(data[key][itag]['bandwidth'])

                        mpd_list.append(''.join(['\t\t\t<Representation id="',
                                                 itag, '" codecs="',
                                                 data[key][itag]['codec'], '" bandwidth="',
                                                 str(data[key][itag]['bandwidth']), '">\n']))

                        mpd_list.append('\t\t\t\t<AudioChannelConfiguration '
                                        'schemeIdUri="urn:mpeg:dash:23003:3:'
                                        'audio_channel_configuration:2011" value="2"/>\n')

                    else:
                        video_codec = data[key][itag]['codec']

                        if video_codec.lower() == 'vp9.2' and not quality_object.hdr:
                            self.discard_video(mime, itag, data[key][itag], 'hdr not selected')
                            continue

                        if video_codec.lower().startswith(('av01', 'av1') and
                                                          not quality_object.av1):
                            self.discard_video(mime, itag, data[key][itag], 'av1 not selected')
                            continue

                        has_video_stream = True
                        if default:
                            if (int(data[key][itag]['bandwidth']) >
                                    int(stream_info['video']['bandwidth'])):
                                stream_info['video']['height'] = str(data[key][itag]['height'])
                                stream_info['video']['fps'] = str(data[key][itag]['frameRate'])
                                stream_info['video']['mime'] = str(mime)
                                stream_info['video']['codec'] = video_codec
                                stream_info['video']['bandwidth'] = \
                                    int(data[key][itag]['bandwidth'])

                                if data[key][itag].get('quality_label'):
                                    stream_info['video']['quality_label'] = \
                                        str(data[key][itag]['quality_label'])

                                if stream_format:
                                    stream_info['video']['codec'] = \
                                        stream_format.get('video', {}).get('encoding')

                                if not stream_info['video'].get('codec'):
                                    stream_info['video']['codec'] = video_codec

                        video_codec = data[key][itag]['codec']
                        mpd_list.append(''.join(['\t\t\t<Representation id="', itag, '" codecs="',
                                                 video_codec, '" startWithSAP="1" bandwidth="',
                                                 str(data[key][itag]['bandwidth']), '" width="',
                                                 str(data[key][itag]['width']), '" height="',
                                                 str(data[key][itag]['height']), '" frameRate="',
                                                 str(data[key][itag]['frameRate']), '">\n']))

                    mpd_list.append(''.join(['\t\t\t\t<BaseURL>',
                                             data[key][itag]['baseUrl'],
                                             '</BaseURL>\n']))

                    mpd_list.append(''.join(['\t\t\t\t<SegmentBase indexRange="',
                                             data[key][itag]['indexRange'],
                                             '">\n', '\t\t\t\t\t\t<Initialization range="',
                                             data[key][itag]['init'], '" />\n',
                                             '\t\t\t\t</SegmentBase>\n']))

                    mpd_list.append('\t\t\t</Representation>\n')
                mpd_list.append('\t\t</AdaptationSet>\n')

                adaptation_set_idx = adaptation_set_idx + 1

            else:
                for i in data[key]:
                    stream_format = self.itags.get(i, {})
                    if 'audio' in mime:
                        self.discard_audio(stream_format, mime, i, data[key][i])

                    else:
                        self.discard_video(mime, i, data[key][i])

        mpd_list.append('\t</Period>\n</MPD>\n')
        manifest_contents = ''.join(mpd_list)

        if self.discarded:
            self._discarded = sorted(
                self.discarded,
                key=lambda k: (k.get('reason'), k.get('audio', k.get('video', {}))['bandwidth']),
                reverse=True
            )

        if not has_video_stream:
            pass

        filename = '{path}{video_id}.mpd'.format(path=self.path, video_id=video_id)
        with open(filename, 'wb') as file_handle:
            _ = file_handle.write(bytes(manifest_contents, encoding='utf-8'))

        license_url = self.license_data.get('license_url', '')
        license_token = self.license_data.get('license_token', '')
        if license_url and license_token:
            xbmcgui.Window(10000).setProperty('tubed-api-license_url', license_url)
            xbmcgui.Window(10000).setProperty('tubed-api-license_token', license_token)

        port = self.addon.getSettingInt('httpd.port') or 52520
        proxy_url = 'http://127.0.0.1:{port}/{video_id}.mpd'.format(port=port, video_id=video_id)

        if self.component_logging:
            LOG.debug('Stream information discard for %s MPEG-DASH manifest:\n%s' %
                      (video_id, json.dumps(self.discarded, indent=4)))
            LOG.debug('Stream information used for %s MPEG-DASH manifest:\n%s' %
                      (video_id, json.dumps(stream_info, indent=4)))

        LOG.debug('Finished generating MPEG-DASH manifest for %s @ %s' % (video_id, proxy_url))

        return proxy_url, stream_info
