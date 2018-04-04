# coding: utf-8
from __future__ import unicode_literals

from .common import InfoExtractor
from ..utils import (
    int_or_none,
    parse_iso8601,
)


class CWTVIE(InfoExtractor):
    _VALID_URL = r'https?://(?:www\.)?cw(?:tv(?:pr)?|seed)\.com/(?:shows/)?(?:[^/]+/)+[^?]*\?.*\b(?:play|watch)=(?P<id>[a-z0-9]{8}-[a-z0-9]{4}-[a-z0-9]{4}-[a-z0-9]{4}-[a-z0-9]{12})'
    _TESTS = [{
        'url': 'http://cwtv.com/shows/arrow/legends-of-yesterday/?play=6b15e985-9345-4f60-baf8-56e96be57c63',
        'info_dict': {
            'id': '6b15e985-9345-4f60-baf8-56e96be57c63',
            'ext': 'mp4',
            'title': 'Legends of Yesterday',
            'description': 'Oliver and Barry Allen take Kendra Saunders and Carter Hall to a remote location to keep them hidden from Vandal Savage while they figure out how to defeat him.',
            'duration': 2665,
            'series': 'Arrow',
            'season_number': 4,
            'season': '4',
            'episode_number': 8,
            'upload_date': '20151203',
            'timestamp': 1449122100,
        },
        'params': {
            # m3u8 download
            'skip_download': True,
        },
        'skip': 'redirect to http://cwtv.com/shows/arrow/',
    }, {
        'url': 'http://www.cwseed.com/shows/whose-line-is-it-anyway/jeff-davis-4/?play=24282b12-ead2-42f2-95ad-26770c2c6088',
        'info_dict': {
            'id': '24282b12-ead2-42f2-95ad-26770c2c6088',
            'ext': 'mp4',
            'title': 'Jeff Davis 4',
            'description': 'Jeff Davis is back to make you laugh.',
            'duration': 1263,
            'series': 'Whose Line Is It Anyway?',
            'season_number': 11,
            'season': '11',
            'episode_number': 20,
            'upload_date': '20151006',
            'timestamp': 1444107300,
        },
    }, {
        'url': 'http://cwtv.com/thecw/chroniclesofcisco/?play=8adebe35-f447-465f-ab52-e863506ff6d6',
        'only_matching': True,
    }, {
        'url': 'http://cwtvpr.com/the-cw/video?watch=9eee3f60-ef4e-440b-b3b2-49428ac9c54e',
        'only_matching': True,
    }, {
        'url': 'http://cwtv.com/shows/arrow/legends-of-yesterday/?watch=6b15e985-9345-4f60-baf8-56e96be57c63',
        'only_matching': True,
    }]

    def _real_extract(self, url):
        video_id = self._match_id(url)
        video_data = None
        formats = []
        for partner in (154, 213):
            vdata = self._download_json(
                'http://metaframe.digitalsmiths.tv/v2/CWtv/assets/%s/partner/%d?format=json' % (video_id, partner), video_id, fatal=False)
            if not vdata:
                continue
            video_data = vdata
            for quality, quality_data in vdata.get('videos', {}).items():
                quality_url = quality_data.get('uri')
                if not quality_url:
                    continue
                if quality == 'variantplaylist':
                    formats.extend(self._extract_m3u8_formats(
                        quality_url, video_id, 'mp4', m3u8_id='hls', fatal=False))
                else:
                    tbr = int_or_none(quality_data.get('bitrate'))
                    format_id = 'http' + ('-%d' % tbr if tbr else '')
                    if self._is_valid_url(quality_url, video_id, format_id):
                        formats.append({
                            'format_id': format_id,
                            'url': quality_url,
                            'tbr': tbr,
                        })
        video_metadata = video_data['assetFields']
        ism_url = video_metadata.get('smoothStreamingUrl')
        if ism_url:
            formats.extend(self._extract_ism_formats(
                ism_url, video_id, ism_id='mss', fatal=False))
        self._sort_formats(formats)

        thumbnails = [{
            'url': image['uri'],
            'width': image.get('width'),
            'height': image.get('height'),
        } for image_id, image in video_data['images'].items() if image.get('uri')] if video_data.get('images') else None

        subtitles = {
            'en': [{
                'url': video_metadata['UnicornCcUrl'],
            }],
        } if video_metadata.get('UnicornCcUrl') else None

        return {
            'id': video_id,
            'title': video_metadata['title'],
            'description': video_metadata.get('description'),
            'duration': int_or_none(video_metadata.get('duration')),
            'series': video_metadata.get('seriesName'),
            'season_number': int_or_none(video_metadata.get('seasonNumber')),
            'season': video_metadata.get('seasonName'),
            'episode_number': int_or_none(video_metadata.get('episodeNumber')),
            'timestamp': parse_iso8601(video_data.get('startTime')),
            'thumbnails': thumbnails,
            'formats': formats,
            'subtitles': subtitles,
        }
