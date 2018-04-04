# coding: utf-8
from __future__ import unicode_literals

from .common import InfoExtractor
from .once import OnceIE
from ..compat import compat_urllib_parse_unquote
from ..utils import ExtractorError


class VoxMediaVolumeIE(OnceIE):
    _VALID_URL = r'https?://volume\.vox-cdn\.com/embed/(?P<id>[0-9a-f]{9})'

    def _real_extract(self, url):
        video_id = self._match_id(url)
        webpage = self._download_webpage(url, video_id)
        video_data = self._parse_json(self._search_regex(
            r'Volume\.createVideo\(({.+})\s*,\s*{.*}\s*,\s*\[.*\]\s*,\s*{.*}\);', webpage, 'video data'), video_id)
        for provider_video_type in ('ooyala', 'youtube', 'brightcove'):
            provider_video_id = video_data.get('%s_id' % provider_video_type)
            if not provider_video_id:
                continue
            info = {
                'id': video_id,
                'title': video_data.get('title_short'),
                'description': video_data.get('description_long') or video_data.get('description_short'),
                'thumbnail': video_data.get('brightcove_thumbnail')
            }
            if provider_video_type == 'brightcove':
                info['formats'] = self._extract_once_formats(provider_video_id)
                self._sort_formats(info['formats'])
            else:
                info.update({
                    '_type': 'url_transparent',
                    'url': provider_video_id if provider_video_type == 'youtube' else '%s:%s' % (provider_video_type, provider_video_id),
                    'ie_key': provider_video_type.capitalize(),
                })
            return info
        raise ExtractorError('Unable to find provider video id')


class VoxMediaIE(InfoExtractor):
    _VALID_URL = r'https?://(?:www\.)?(?:(?:theverge|vox|sbnation|eater|polygon|curbed|racked)\.com|recode\.net)/(?:[^/]+/)*(?P<id>[^/?]+)'
    _TESTS = [{
        'url': 'http://www.theverge.com/2014/6/27/5849272/material-world-how-google-discovered-what-software-is-made-of',
        'info_dict': {
            'id': '11eXZobjrG8DCSTgrNjVinU-YmmdYjhe',
            'ext': 'mp4',
            'title': 'Google\'s new material design direction',
            'description': 'md5:2f44f74c4d14a1f800ea73e1c6832ad2',
        },
        'params': {
            # m3u8 download
            'skip_download': True,
        },
        'add_ie': ['Ooyala'],
    }, {
        # data-ooyala-id
        'url': 'http://www.theverge.com/2014/10/21/7025853/google-nexus-6-hands-on-photos-video-android-phablet',
        'md5': 'd744484ff127884cd2ba09e3fa604e4b',
        'info_dict': {
            'id': 'RkZXU4cTphOCPDMZg5oEounJyoFI0g-B',
            'ext': 'mp4',
            'title': 'The Nexus 6: hands-on with Google\'s phablet',
            'description': 'md5:87a51fe95ff8cea8b5bdb9ac7ae6a6af',
        },
        'add_ie': ['Ooyala'],
        'skip': 'Video Not Found',
    }, {
        # volume embed
        'url': 'http://www.vox.com/2016/3/31/11336640/mississippi-lgbt-religious-freedom-bill',
        'info_dict': {
            'id': 'wydzk3dDpmRz7PQoXRsTIX6XTkPjYL0b',
            'ext': 'mp4',
            'title': 'The new frontier of LGBTQ civil rights, explained',
            'description': 'md5:0dc58e94a465cbe91d02950f770eb93f',
        },
        'params': {
            # m3u8 download
            'skip_download': True,
        },
        'add_ie': ['Ooyala'],
    }, {
        # youtube embed
        'url': 'http://www.vox.com/2016/3/24/11291692/robot-dance',
        'md5': '83b3080489fb103941e549352d3e0977',
        'info_dict': {
            'id': 'FcNHTJU1ufM',
            'ext': 'mp4',
            'title': 'How "the robot" became the greatest novelty dance of all time',
            'description': 'md5:b081c0d588b8b2085870cda55e6da176',
            'upload_date': '20160324',
            'uploader_id': 'voxdotcom',
            'uploader': 'Vox',
        },
        'add_ie': ['Youtube'],
    }, {
        # SBN.VideoLinkset.entryGroup multiple ooyala embeds
        'url': 'http://www.sbnation.com/college-football-recruiting/2015/2/3/7970291/national-signing-day-rationalizations-itll-be-ok-itll-be-ok',
        'info_dict': {
            'id': 'national-signing-day-rationalizations-itll-be-ok-itll-be-ok',
            'title': '25 lies you will tell yourself on National Signing Day',
            'description': 'It\'s the most self-delusional time of the year, and everyone\'s gonna tell the same lies together!',
        },
        'playlist': [{
            'md5': '721fededf2ab74ae4176c8c8cbfe092e',
            'info_dict': {
                'id': 'p3cThlMjE61VDi_SD9JlIteSNPWVDBB9',
                'ext': 'mp4',
                'title': 'Buddy Hield vs Steph Curry (and the world)',
                'description': 'Let’s dissect only the most important Final Four storylines.',
            },
        }, {
            'md5': 'bf0c5cc115636af028be1bab79217ea9',
            'info_dict': {
                'id': 'BmbmVjMjE6esPHxdALGubTrouQ0jYLHj',
                'ext': 'mp4',
                'title': 'Chasing Cinderella 2016: Syracuse basketball',
                'description': 'md5:e02d56b026d51aa32c010676765a690d',
            },
        }],
    }, {
        # volume embed, Brightcove Once
        'url': 'https://www.recode.net/2014/6/17/11628066/post-post-pc-ceo-the-full-code-conference-video-of-microsofts-satya',
        'md5': '01571a896281f77dc06e084138987ea2',
        'info_dict': {
            'id': '1231c973d',
            'ext': 'mp4',
            'title': 'Post-Post-PC CEO: The Full Code Conference Video of Microsoft\'s Satya Nadella',
            'description': 'The longtime veteran was chosen earlier this year as the software giant\'s third leader in its history.',
        },
        'add_ie': ['VoxMediaVolume'],
    }]

    def _real_extract(self, url):
        display_id = self._match_id(url)
        webpage = compat_urllib_parse_unquote(self._download_webpage(url, display_id))

        def create_entry(provider_video_id, provider_video_type, title=None, description=None):
            video_url = {
                'youtube': '%s',
                'ooyala': 'ooyala:%s',
                'volume': 'http://volume.vox-cdn.com/embed/%s',
            }[provider_video_type] % provider_video_id
            return {
                '_type': 'url_transparent',
                'url': video_url,
                'title': title or self._og_search_title(webpage),
                'description': description or self._og_search_description(webpage),
            }

        entries = []
        entries_data = self._search_regex([
            r'Chorus\.VideoContext\.addVideo\((\[{.+}\])\);',
            r'var\s+entry\s*=\s*({.+});',
            r'SBN\.VideoLinkset\.entryGroup\(\s*(\[.+\])',
        ], webpage, 'video data', default=None)
        if entries_data:
            entries_data = self._parse_json(entries_data, display_id)
            if isinstance(entries_data, dict):
                entries_data = [entries_data]
            for video_data in entries_data:
                provider_video_id = video_data.get('provider_video_id')
                provider_video_type = video_data.get('provider_video_type')
                if provider_video_id and provider_video_type:
                    entries.append(create_entry(
                        provider_video_id, provider_video_type,
                        video_data.get('title'), video_data.get('description')))

        provider_video_id = self._search_regex(
            r'data-ooyala-id="([^"]+)"', webpage, 'ooyala id', default=None)
        if provider_video_id:
            entries.append(create_entry(provider_video_id, 'ooyala'))

        volume_uuid = self._search_regex(
            r'data-volume-uuid="([^"]+)"', webpage, 'volume uuid', default=None)
        if volume_uuid:
            entries.append(create_entry(volume_uuid, 'volume'))

        if len(entries) == 1:
            return entries[0]
        else:
            return self.playlist_result(entries, display_id, self._og_search_title(webpage), self._og_search_description(webpage))
