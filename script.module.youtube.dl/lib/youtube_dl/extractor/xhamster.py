from __future__ import unicode_literals

import re

from .common import InfoExtractor
from ..compat import compat_str
from ..utils import (
    clean_html,
    determine_ext,
    dict_get,
    ExtractorError,
    int_or_none,
    parse_duration,
    try_get,
    unified_strdate,
)


class XHamsterIE(InfoExtractor):
    _VALID_URL = r'''(?x)
                    https?://
                        (?:.+?\.)?xhamster\.com/
                        (?:
                            movies/(?P<id>\d+)/(?P<display_id>[^/]*)\.html|
                            videos/(?P<display_id_2>[^/]*)-(?P<id_2>\d+)
                        )
                    '''

    _TESTS = [{
        'url': 'http://xhamster.com/movies/1509445/femaleagent_shy_beauty_takes_the_bait.html',
        'md5': '8281348b8d3c53d39fffb377d24eac4e',
        'info_dict': {
            'id': '1509445',
            'display_id': 'femaleagent_shy_beauty_takes_the_bait',
            'ext': 'mp4',
            'title': 'FemaleAgent Shy beauty takes the bait',
            'timestamp': 1350194821,
            'upload_date': '20121014',
            'uploader': 'Ruseful2011',
            'duration': 893,
            'age_limit': 18,
            'categories': ['Fake Hub', 'Amateur', 'MILFs', 'POV', 'Beauti', 'Beauties', 'Beautiful', 'Boss', 'Office', 'Oral', 'Reality', 'Sexy', 'Taking'],
        },
    }, {
        'url': 'http://xhamster.com/movies/2221348/britney_spears_sexy_booty.html?hd',
        'info_dict': {
            'id': '2221348',
            'display_id': 'britney_spears_sexy_booty',
            'ext': 'mp4',
            'title': 'Britney Spears  Sexy Booty',
            'timestamp': 1379123460,
            'upload_date': '20130914',
            'uploader': 'jojo747400',
            'duration': 200,
            'age_limit': 18,
            'categories': ['Britney Spears', 'Celebrities', 'HD Videos', 'Sexy', 'Sexy Booty'],
        },
        'params': {
            'skip_download': True,
        },
    }, {
        # empty seo
        'url': 'http://xhamster.com/movies/5667973/.html',
        'info_dict': {
            'id': '5667973',
            'ext': 'mp4',
            'title': '....',
            'timestamp': 1454948101,
            'upload_date': '20160208',
            'uploader': 'parejafree',
            'duration': 72,
            'age_limit': 18,
            'categories': ['Amateur', 'Blowjobs'],
        },
        'params': {
            'skip_download': True,
        },
    }, {
        # mobile site
        'url': 'https://m.xhamster.com/videos/cute-teen-jacqueline-solo-masturbation-8559111',
        'only_matching': True,
    }, {
        'url': 'https://xhamster.com/movies/2272726/amber_slayed_by_the_knight.html',
        'only_matching': True,
    }, {
        # This video is visible for marcoalfa123456's friends only
        'url': 'https://it.xhamster.com/movies/7263980/la_mia_vicina.html',
        'only_matching': True,
    }, {
        # new URL schema
        'url': 'https://pt.xhamster.com/videos/euro-pedal-pumping-7937821',
        'only_matching': True,
    }]

    def _real_extract(self, url):
        mobj = re.match(self._VALID_URL, url)
        video_id = mobj.group('id') or mobj.group('id_2')
        display_id = mobj.group('display_id') or mobj.group('display_id_2')

        desktop_url = re.sub(r'^(https?://(?:.+?\.)?)m\.', r'\1', url)
        webpage = self._download_webpage(desktop_url, video_id)

        error = self._html_search_regex(
            r'<div[^>]+id=["\']videoClosed["\'][^>]*>(.+?)</div>',
            webpage, 'error', default=None)
        if error:
            raise ExtractorError(error, expected=True)

        age_limit = self._rta_search(webpage)

        def get_height(s):
            return int_or_none(self._search_regex(
                r'^(\d+)[pP]', s, 'height', default=None))

        initials = self._parse_json(
            self._search_regex(
                r'window\.initials\s*=\s*({.+?})\s*;\s*\n', webpage, 'initials',
                default='{}'),
            video_id, fatal=False)
        if initials:
            video = initials['videoModel']
            title = video['title']
            formats = []
            for format_id, formats_dict in video['sources'].items():
                if not isinstance(formats_dict, dict):
                    continue
                for quality, format_item in formats_dict.items():
                    if format_id == 'download':
                        # Download link takes some time to be generated,
                        # skipping for now
                        continue
                        if not isinstance(format_item, dict):
                            continue
                        format_url = format_item.get('link')
                        filesize = int_or_none(
                            format_item.get('size'), invscale=1000000)
                    else:
                        format_url = format_item
                        filesize = None
                    if not isinstance(format_url, compat_str):
                        continue
                    formats.append({
                        'format_id': '%s-%s' % (format_id, quality),
                        'url': format_url,
                        'ext': determine_ext(format_url, 'mp4'),
                        'height': get_height(quality),
                        'filesize': filesize,
                    })
            self._sort_formats(formats)

            categories_list = video.get('categories')
            if isinstance(categories_list, list):
                categories = []
                for c in categories_list:
                    if not isinstance(c, dict):
                        continue
                    c_name = c.get('name')
                    if isinstance(c_name, compat_str):
                        categories.append(c_name)
            else:
                categories = None

            return {
                'id': video_id,
                'display_id': display_id,
                'title': title,
                'description': video.get('description'),
                'timestamp': int_or_none(video.get('created')),
                'uploader': try_get(
                    video, lambda x: x['author']['name'], compat_str),
                'thumbnail': video.get('thumbURL'),
                'duration': int_or_none(video.get('duration')),
                'view_count': int_or_none(video.get('views')),
                'like_count': int_or_none(try_get(
                    video, lambda x: x['rating']['likes'], int)),
                'dislike_count': int_or_none(try_get(
                    video, lambda x: x['rating']['dislikes'], int)),
                'comment_count': int_or_none(video.get('views')),
                'age_limit': age_limit,
                'categories': categories,
                'formats': formats,
            }

        # Old layout fallback

        title = self._html_search_regex(
            [r'<h1[^>]*>([^<]+)</h1>',
             r'<meta[^>]+itemprop=".*?caption.*?"[^>]+content="(.+?)"',
             r'<title[^>]*>(.+?)(?:,\s*[^,]*?\s*Porn\s*[^,]*?:\s*xHamster[^<]*| - xHamster\.com)</title>'],
            webpage, 'title')

        formats = []
        format_urls = set()

        sources = self._parse_json(
            self._search_regex(
                r'sources\s*:\s*({.+?})\s*,?\s*\n', webpage, 'sources',
                default='{}'),
            video_id, fatal=False)
        for format_id, format_url in sources.items():
            if not isinstance(format_url, compat_str):
                continue
            if format_url in format_urls:
                continue
            format_urls.add(format_url)
            formats.append({
                'format_id': format_id,
                'url': format_url,
                'height': get_height(format_id),
            })

        video_url = self._search_regex(
            [r'''file\s*:\s*(?P<q>["'])(?P<mp4>.+?)(?P=q)''',
             r'''<a\s+href=(?P<q>["'])(?P<mp4>.+?)(?P=q)\s+class=["']mp4Thumb''',
             r'''<video[^>]+file=(?P<q>["'])(?P<mp4>.+?)(?P=q)[^>]*>'''],
            webpage, 'video url', group='mp4', default=None)
        if video_url and video_url not in format_urls:
            formats.append({
                'url': video_url,
            })

        self._sort_formats(formats)

        # Only a few videos have an description
        mobj = re.search(r'<span>Description: </span>([^<]+)', webpage)
        description = mobj.group(1) if mobj else None

        upload_date = unified_strdate(self._search_regex(
            r'hint=["\'](\d{4}-\d{2}-\d{2}) \d{2}:\d{2}:\d{2} [A-Z]{3,4}',
            webpage, 'upload date', fatal=False))

        uploader = self._html_search_regex(
            r'<span[^>]+itemprop=["\']author[^>]+><a[^>]+><span[^>]+>([^<]+)',
            webpage, 'uploader', default='anonymous')

        thumbnail = self._search_regex(
            [r'''["']thumbUrl["']\s*:\s*(?P<q>["'])(?P<thumbnail>.+?)(?P=q)''',
             r'''<video[^>]+"poster"=(?P<q>["'])(?P<thumbnail>.+?)(?P=q)[^>]*>'''],
            webpage, 'thumbnail', fatal=False, group='thumbnail')

        duration = parse_duration(self._search_regex(
            [r'<[^<]+\bitemprop=["\']duration["\'][^<]+\bcontent=["\'](.+?)["\']',
             r'Runtime:\s*</span>\s*([\d:]+)'], webpage,
            'duration', fatal=False))

        view_count = int_or_none(self._search_regex(
            r'content=["\']User(?:View|Play)s:(\d+)',
            webpage, 'view count', fatal=False))

        mobj = re.search(r'hint=[\'"](?P<likecount>\d+) Likes / (?P<dislikecount>\d+) Dislikes', webpage)
        (like_count, dislike_count) = (mobj.group('likecount'), mobj.group('dislikecount')) if mobj else (None, None)

        mobj = re.search(r'</label>Comments \((?P<commentcount>\d+)\)</div>', webpage)
        comment_count = mobj.group('commentcount') if mobj else 0

        categories_html = self._search_regex(
            r'(?s)<table.+?(<span>Categories:.+?)</table>', webpage,
            'categories', default=None)
        categories = [clean_html(category) for category in re.findall(
            r'<a[^>]+>(.+?)</a>', categories_html)] if categories_html else None

        return {
            'id': video_id,
            'display_id': display_id,
            'title': title,
            'description': description,
            'upload_date': upload_date,
            'uploader': uploader,
            'thumbnail': thumbnail,
            'duration': duration,
            'view_count': view_count,
            'like_count': int_or_none(like_count),
            'dislike_count': int_or_none(dislike_count),
            'comment_count': int_or_none(comment_count),
            'age_limit': age_limit,
            'categories': categories,
            'formats': formats,
        }


class XHamsterEmbedIE(InfoExtractor):
    _VALID_URL = r'https?://(?:.+?\.)?xhamster\.com/xembed\.php\?video=(?P<id>\d+)'
    _TEST = {
        'url': 'http://xhamster.com/xembed.php?video=3328539',
        'info_dict': {
            'id': '3328539',
            'ext': 'mp4',
            'title': 'Pen Masturbation',
            'timestamp': 1406581861,
            'upload_date': '20140728',
            'uploader': 'ManyakisArt',
            'duration': 5,
            'age_limit': 18,
        }
    }

    @staticmethod
    def _extract_urls(webpage):
        return [url for _, url in re.findall(
            r'<iframe[^>]+?src=(["\'])(?P<url>(?:https?:)?//(?:www\.)?xhamster\.com/xembed\.php\?video=\d+)\1',
            webpage)]

    def _real_extract(self, url):
        video_id = self._match_id(url)

        webpage = self._download_webpage(url, video_id)

        video_url = self._search_regex(
            r'href="(https?://xhamster\.com/(?:movies/{0}/[^"]*\.html|videos/[^/]*-{0})[^"]*)"'.format(video_id),
            webpage, 'xhamster url', default=None)

        if not video_url:
            vars = self._parse_json(
                self._search_regex(r'vars\s*:\s*({.+?})\s*,\s*\n', webpage, 'vars'),
                video_id)
            video_url = dict_get(vars, ('downloadLink', 'homepageLink', 'commentsLink', 'shareUrl'))

        return self.url_result(video_url, 'XHamster')
