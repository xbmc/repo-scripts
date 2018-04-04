# coding: utf-8
from __future__ import unicode_literals

import random
import re
import math

from .common import InfoExtractor
from ..compat import (
    compat_str,
    compat_chr,
    compat_ord,
)
from ..utils import (
    ExtractorError,
    float_or_none,
    int_or_none,
    orderedSet,
    str_or_none,
)


class GloboIE(InfoExtractor):
    _VALID_URL = r'(?:globo:|https?://.+?\.globo\.com/(?:[^/]+/)*(?:v/(?:[^/]+/)?|videos/))(?P<id>\d{7,})'

    _API_URL_TEMPLATE = 'http://api.globovideos.com/videos/%s/playlist'
    _SECURITY_URL_TEMPLATE = 'http://security.video.globo.com/videos/%s/hash?player=flash&version=17.0.0.132&resource_id=%s'

    _RESIGN_EXPIRATION = 86400

    _TESTS = [{
        'url': 'http://g1.globo.com/carros/autoesporte/videos/t/exclusivos-do-g1/v/mercedes-benz-gla-passa-por-teste-de-colisao-na-europa/3607726/',
        'md5': 'b3ccc801f75cd04a914d51dadb83a78d',
        'info_dict': {
            'id': '3607726',
            'ext': 'mp4',
            'title': 'Mercedes-Benz GLA passa por teste de colisão na Europa',
            'duration': 103.204,
            'uploader': 'Globo.com',
            'uploader_id': '265',
        },
    }, {
        'url': 'http://globoplay.globo.com/v/4581987/',
        'md5': 'f36a1ecd6a50da1577eee6dd17f67eff',
        'info_dict': {
            'id': '4581987',
            'ext': 'mp4',
            'title': 'Acidentes de trânsito estão entre as maiores causas de queda de energia em SP',
            'duration': 137.973,
            'uploader': 'Rede Globo',
            'uploader_id': '196',
        },
    }, {
        'url': 'http://canalbrasil.globo.com/programas/sangue-latino/videos/3928201.html',
        'only_matching': True,
    }, {
        'url': 'http://globosatplay.globo.com/globonews/v/4472924/',
        'only_matching': True,
    }, {
        'url': 'http://globotv.globo.com/t/programa/v/clipe-sexo-e-as-negas-adeus/3836166/',
        'only_matching': True,
    }, {
        'url': 'http://globotv.globo.com/canal-brasil/sangue-latino/t/todos-os-videos/v/ator-e-diretor-argentino-ricado-darin-fala-sobre-utopias-e-suas-perdas/3928201/',
        'only_matching': True,
    }, {
        'url': 'http://canaloff.globo.com/programas/desejar-profundo/videos/4518560.html',
        'only_matching': True,
    }, {
        'url': 'globo:3607726',
        'only_matching': True,
    }]

    class MD5(object):
        HEX_FORMAT_LOWERCASE = 0
        HEX_FORMAT_UPPERCASE = 1
        BASE64_PAD_CHARACTER_DEFAULT_COMPLIANCE = ''
        BASE64_PAD_CHARACTER_RFC_COMPLIANCE = '='
        PADDING = '=0xFF01DD'
        hexcase = 0
        b64pad = ''

        def __init__(self):
            pass

        class JSArray(list):
            def __getitem__(self, y):
                try:
                    return list.__getitem__(self, y)
                except IndexError:
                    return 0

            def __setitem__(self, i, y):
                try:
                    return list.__setitem__(self, i, y)
                except IndexError:
                    self.extend([0] * (i - len(self) + 1))
                    self[-1] = y

        @classmethod
        def hex_md5(cls, param1):
            return cls.rstr2hex(cls.rstr_md5(cls.str2rstr_utf8(param1)))

        @classmethod
        def b64_md5(cls, param1, param2=None):
            return cls.rstr2b64(cls.rstr_md5(cls.str2rstr_utf8(param1, param2)))

        @classmethod
        def any_md5(cls, param1, param2):
            return cls.rstr2any(cls.rstr_md5(cls.str2rstr_utf8(param1)), param2)

        @classmethod
        def rstr_md5(cls, param1):
            return cls.binl2rstr(cls.binl_md5(cls.rstr2binl(param1), len(param1) * 8))

        @classmethod
        def rstr2hex(cls, param1):
            _loc_2 = '0123456789ABCDEF' if cls.hexcase else '0123456789abcdef'
            _loc_3 = ''
            for _loc_5 in range(0, len(param1)):
                _loc_4 = compat_ord(param1[_loc_5])
                _loc_3 += _loc_2[_loc_4 >> 4 & 15] + _loc_2[_loc_4 & 15]
            return _loc_3

        @classmethod
        def rstr2b64(cls, param1):
            _loc_2 = 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-_'
            _loc_3 = ''
            _loc_4 = len(param1)
            for _loc_5 in range(0, _loc_4, 3):
                _loc_6_1 = compat_ord(param1[_loc_5]) << 16
                _loc_6_2 = compat_ord(param1[_loc_5 + 1]) << 8 if _loc_5 + 1 < _loc_4 else 0
                _loc_6_3 = compat_ord(param1[_loc_5 + 2]) if _loc_5 + 2 < _loc_4 else 0
                _loc_6 = _loc_6_1 | _loc_6_2 | _loc_6_3
                for _loc_7 in range(0, 4):
                    if _loc_5 * 8 + _loc_7 * 6 > len(param1) * 8:
                        _loc_3 += cls.b64pad
                    else:
                        _loc_3 += _loc_2[_loc_6 >> 6 * (3 - _loc_7) & 63]
            return _loc_3

        @staticmethod
        def rstr2any(param1, param2):
            _loc_3 = len(param2)
            _loc_4 = []
            _loc_9 = [0] * ((len(param1) >> 2) + 1)
            for _loc_5 in range(0, len(_loc_9)):
                _loc_9[_loc_5] = compat_ord(param1[_loc_5 * 2]) << 8 | compat_ord(param1[_loc_5 * 2 + 1])

            while len(_loc_9) > 0:
                _loc_8 = []
                _loc_7 = 0
                for _loc_5 in range(0, len(_loc_9)):
                    _loc_7 = (_loc_7 << 16) + _loc_9[_loc_5]
                    _loc_6 = math.floor(_loc_7 / _loc_3)
                    _loc_7 -= _loc_6 * _loc_3
                    if len(_loc_8) > 0 or _loc_6 > 0:
                        _loc_8[len(_loc_8)] = _loc_6

                _loc_4[len(_loc_4)] = _loc_7
                _loc_9 = _loc_8

            _loc_10 = ''
            _loc_5 = len(_loc_4) - 1
            while _loc_5 >= 0:
                _loc_10 += param2[_loc_4[_loc_5]]
                _loc_5 -= 1

            return _loc_10

        @classmethod
        def str2rstr_utf8(cls, param1, param2=None):
            _loc_3 = ''
            _loc_4 = -1
            if not param2:
                param2 = cls.PADDING
            param1 = param1 + param2[1:9]
            while True:
                _loc_4 += 1
                if _loc_4 >= len(param1):
                    break
                _loc_5 = compat_ord(param1[_loc_4])
                _loc_6 = compat_ord(param1[_loc_4 + 1]) if _loc_4 + 1 < len(param1) else 0
                if 55296 <= _loc_5 <= 56319 and 56320 <= _loc_6 <= 57343:
                    _loc_5 = 65536 + ((_loc_5 & 1023) << 10) + (_loc_6 & 1023)
                    _loc_4 += 1
                if _loc_5 <= 127:
                    _loc_3 += compat_chr(_loc_5)
                    continue
                if _loc_5 <= 2047:
                    _loc_3 += compat_chr(192 | _loc_5 >> 6 & 31) + compat_chr(128 | _loc_5 & 63)
                    continue
                if _loc_5 <= 65535:
                    _loc_3 += compat_chr(224 | _loc_5 >> 12 & 15) + compat_chr(128 | _loc_5 >> 6 & 63) + compat_chr(
                        128 | _loc_5 & 63)
                    continue
                if _loc_5 <= 2097151:
                    _loc_3 += compat_chr(240 | _loc_5 >> 18 & 7) + compat_chr(128 | _loc_5 >> 12 & 63) + compat_chr(
                        128 | _loc_5 >> 6 & 63) + compat_chr(128 | _loc_5 & 63)
            return _loc_3

        @staticmethod
        def rstr2binl(param1):
            _loc_2 = [0] * ((len(param1) >> 2) + 1)
            for _loc_3 in range(0, len(_loc_2)):
                _loc_2[_loc_3] = 0
            for _loc_3 in range(0, len(param1) * 8, 8):
                _loc_2[_loc_3 >> 5] |= (compat_ord(param1[_loc_3 // 8]) & 255) << _loc_3 % 32
            return _loc_2

        @staticmethod
        def binl2rstr(param1):
            _loc_2 = ''
            for _loc_3 in range(0, len(param1) * 32, 8):
                _loc_2 += compat_chr(param1[_loc_3 >> 5] >> _loc_3 % 32 & 255)
            return _loc_2

        @classmethod
        def binl_md5(cls, param1, param2):
            param1 = cls.JSArray(param1)
            param1[param2 >> 5] |= 128 << param2 % 32
            param1[(param2 + 64 >> 9 << 4) + 14] = param2
            _loc_3 = 1732584193
            _loc_4 = -271733879
            _loc_5 = -1732584194
            _loc_6 = 271733878
            for _loc_7 in range(0, len(param1), 16):
                _loc_8 = _loc_3
                _loc_9 = _loc_4
                _loc_10 = _loc_5
                _loc_11 = _loc_6
                _loc_3 = cls.md5_ff(_loc_3, _loc_4, _loc_5, _loc_6, param1[_loc_7 + 0], 7, -680876936)
                _loc_6 = cls.md5_ff(_loc_6, _loc_3, _loc_4, _loc_5, param1[_loc_7 + 1], 12, -389564586)
                _loc_5 = cls.md5_ff(_loc_5, _loc_6, _loc_3, _loc_4, param1[_loc_7 + 2], 17, 606105819)
                _loc_4 = cls.md5_ff(_loc_4, _loc_5, _loc_6, _loc_3, param1[_loc_7 + 3], 22, -1044525330)
                _loc_3 = cls.md5_ff(_loc_3, _loc_4, _loc_5, _loc_6, param1[_loc_7 + 4], 7, -176418897)
                _loc_6 = cls.md5_ff(_loc_6, _loc_3, _loc_4, _loc_5, param1[_loc_7 + 5], 12, 1200080426)
                _loc_5 = cls.md5_ff(_loc_5, _loc_6, _loc_3, _loc_4, param1[_loc_7 + 6], 17, -1473231341)
                _loc_4 = cls.md5_ff(_loc_4, _loc_5, _loc_6, _loc_3, param1[_loc_7 + 7], 22, -45705983)
                _loc_3 = cls.md5_ff(_loc_3, _loc_4, _loc_5, _loc_6, param1[_loc_7 + 8], 7, 1770035416)
                _loc_6 = cls.md5_ff(_loc_6, _loc_3, _loc_4, _loc_5, param1[_loc_7 + 9], 12, -1958414417)
                _loc_5 = cls.md5_ff(_loc_5, _loc_6, _loc_3, _loc_4, param1[_loc_7 + 10], 17, -42063)
                _loc_4 = cls.md5_ff(_loc_4, _loc_5, _loc_6, _loc_3, param1[_loc_7 + 11], 22, -1990404162)
                _loc_3 = cls.md5_ff(_loc_3, _loc_4, _loc_5, _loc_6, param1[_loc_7 + 12], 7, 1804603682)
                _loc_6 = cls.md5_ff(_loc_6, _loc_3, _loc_4, _loc_5, param1[_loc_7 + 13], 12, -40341101)
                _loc_5 = cls.md5_ff(_loc_5, _loc_6, _loc_3, _loc_4, param1[_loc_7 + 14], 17, -1502002290)
                _loc_4 = cls.md5_ff(_loc_4, _loc_5, _loc_6, _loc_3, param1[_loc_7 + 15], 22, 1236535329)
                _loc_3 = cls.md5_gg(_loc_3, _loc_4, _loc_5, _loc_6, param1[_loc_7 + 1], 5, -165796510)
                _loc_6 = cls.md5_gg(_loc_6, _loc_3, _loc_4, _loc_5, param1[_loc_7 + 6], 9, -1069501632)
                _loc_5 = cls.md5_gg(_loc_5, _loc_6, _loc_3, _loc_4, param1[_loc_7 + 11], 14, 643717713)
                _loc_4 = cls.md5_gg(_loc_4, _loc_5, _loc_6, _loc_3, param1[_loc_7 + 0], 20, -373897302)
                _loc_3 = cls.md5_gg(_loc_3, _loc_4, _loc_5, _loc_6, param1[_loc_7 + 5], 5, -701558691)
                _loc_6 = cls.md5_gg(_loc_6, _loc_3, _loc_4, _loc_5, param1[_loc_7 + 10], 9, 38016083)
                _loc_5 = cls.md5_gg(_loc_5, _loc_6, _loc_3, _loc_4, param1[_loc_7 + 15], 14, -660478335)
                _loc_4 = cls.md5_gg(_loc_4, _loc_5, _loc_6, _loc_3, param1[_loc_7 + 4], 20, -405537848)
                _loc_3 = cls.md5_gg(_loc_3, _loc_4, _loc_5, _loc_6, param1[_loc_7 + 9], 5, 568446438)
                _loc_6 = cls.md5_gg(_loc_6, _loc_3, _loc_4, _loc_5, param1[_loc_7 + 14], 9, -1019803690)
                _loc_5 = cls.md5_gg(_loc_5, _loc_6, _loc_3, _loc_4, param1[_loc_7 + 3], 14, -187363961)
                _loc_4 = cls.md5_gg(_loc_4, _loc_5, _loc_6, _loc_3, param1[_loc_7 + 8], 20, 1163531501)
                _loc_3 = cls.md5_gg(_loc_3, _loc_4, _loc_5, _loc_6, param1[_loc_7 + 13], 5, -1444681467)
                _loc_6 = cls.md5_gg(_loc_6, _loc_3, _loc_4, _loc_5, param1[_loc_7 + 2], 9, -51403784)
                _loc_5 = cls.md5_gg(_loc_5, _loc_6, _loc_3, _loc_4, param1[_loc_7 + 7], 14, 1735328473)
                _loc_4 = cls.md5_gg(_loc_4, _loc_5, _loc_6, _loc_3, param1[_loc_7 + 12], 20, -1926607734)
                _loc_3 = cls.md5_hh(_loc_3, _loc_4, _loc_5, _loc_6, param1[_loc_7 + 5], 4, -378558)
                _loc_6 = cls.md5_hh(_loc_6, _loc_3, _loc_4, _loc_5, param1[_loc_7 + 8], 11, -2022574463)
                _loc_5 = cls.md5_hh(_loc_5, _loc_6, _loc_3, _loc_4, param1[_loc_7 + 11], 16, 1839030562)
                _loc_4 = cls.md5_hh(_loc_4, _loc_5, _loc_6, _loc_3, param1[_loc_7 + 14], 23, -35309556)
                _loc_3 = cls.md5_hh(_loc_3, _loc_4, _loc_5, _loc_6, param1[_loc_7 + 1], 4, -1530992060)
                _loc_6 = cls.md5_hh(_loc_6, _loc_3, _loc_4, _loc_5, param1[_loc_7 + 4], 11, 1272893353)
                _loc_5 = cls.md5_hh(_loc_5, _loc_6, _loc_3, _loc_4, param1[_loc_7 + 7], 16, -155497632)
                _loc_4 = cls.md5_hh(_loc_4, _loc_5, _loc_6, _loc_3, param1[_loc_7 + 10], 23, -1094730640)
                _loc_3 = cls.md5_hh(_loc_3, _loc_4, _loc_5, _loc_6, param1[_loc_7 + 13], 4, 681279174)
                _loc_6 = cls.md5_hh(_loc_6, _loc_3, _loc_4, _loc_5, param1[_loc_7 + 0], 11, -358537222)
                _loc_5 = cls.md5_hh(_loc_5, _loc_6, _loc_3, _loc_4, param1[_loc_7 + 3], 16, -722521979)
                _loc_4 = cls.md5_hh(_loc_4, _loc_5, _loc_6, _loc_3, param1[_loc_7 + 6], 23, 76029189)
                _loc_3 = cls.md5_hh(_loc_3, _loc_4, _loc_5, _loc_6, param1[_loc_7 + 9], 4, -640364487)
                _loc_6 = cls.md5_hh(_loc_6, _loc_3, _loc_4, _loc_5, param1[_loc_7 + 12], 11, -421815835)
                _loc_5 = cls.md5_hh(_loc_5, _loc_6, _loc_3, _loc_4, param1[_loc_7 + 15], 16, 530742520)
                _loc_4 = cls.md5_hh(_loc_4, _loc_5, _loc_6, _loc_3, param1[_loc_7 + 2], 23, -995338651)
                _loc_3 = cls.md5_ii(_loc_3, _loc_4, _loc_5, _loc_6, param1[_loc_7 + 0], 6, -198630844)
                _loc_6 = cls.md5_ii(_loc_6, _loc_3, _loc_4, _loc_5, param1[_loc_7 + 7], 10, 1126891415)
                _loc_5 = cls.md5_ii(_loc_5, _loc_6, _loc_3, _loc_4, param1[_loc_7 + 14], 15, -1416354905)
                _loc_4 = cls.md5_ii(_loc_4, _loc_5, _loc_6, _loc_3, param1[_loc_7 + 5], 21, -57434055)
                _loc_3 = cls.md5_ii(_loc_3, _loc_4, _loc_5, _loc_6, param1[_loc_7 + 12], 6, 1700485571)
                _loc_6 = cls.md5_ii(_loc_6, _loc_3, _loc_4, _loc_5, param1[_loc_7 + 3], 10, -1894986606)
                _loc_5 = cls.md5_ii(_loc_5, _loc_6, _loc_3, _loc_4, param1[_loc_7 + 10], 15, -1051523)
                _loc_4 = cls.md5_ii(_loc_4, _loc_5, _loc_6, _loc_3, param1[_loc_7 + 1], 21, -2054922799)
                _loc_3 = cls.md5_ii(_loc_3, _loc_4, _loc_5, _loc_6, param1[_loc_7 + 8], 6, 1873313359)
                _loc_6 = cls.md5_ii(_loc_6, _loc_3, _loc_4, _loc_5, param1[_loc_7 + 15], 10, -30611744)
                _loc_5 = cls.md5_ii(_loc_5, _loc_6, _loc_3, _loc_4, param1[_loc_7 + 6], 15, -1560198380)
                _loc_4 = cls.md5_ii(_loc_4, _loc_5, _loc_6, _loc_3, param1[_loc_7 + 13], 21, 1309151649)
                _loc_3 = cls.md5_ii(_loc_3, _loc_4, _loc_5, _loc_6, param1[_loc_7 + 4], 6, -145523070)
                _loc_6 = cls.md5_ii(_loc_6, _loc_3, _loc_4, _loc_5, param1[_loc_7 + 11], 10, -1120210379)
                _loc_5 = cls.md5_ii(_loc_5, _loc_6, _loc_3, _loc_4, param1[_loc_7 + 2], 15, 718787259)
                _loc_4 = cls.md5_ii(_loc_4, _loc_5, _loc_6, _loc_3, param1[_loc_7 + 9], 21, -343485551)
                _loc_3 = cls.safe_add(_loc_3, _loc_8)
                _loc_4 = cls.safe_add(_loc_4, _loc_9)
                _loc_5 = cls.safe_add(_loc_5, _loc_10)
                _loc_6 = cls.safe_add(_loc_6, _loc_11)
            return [_loc_3, _loc_4, _loc_5, _loc_6]

        @classmethod
        def md5_cmn(cls, param1, param2, param3, param4, param5, param6):
            return cls.safe_add(
                cls.bit_rol(cls.safe_add(cls.safe_add(param2, param1), cls.safe_add(param4, param6)), param5), param3)

        @classmethod
        def md5_ff(cls, param1, param2, param3, param4, param5, param6, param7):
            return cls.md5_cmn(param2 & param3 | ~param2 & param4, param1, param2, param5, param6, param7)

        @classmethod
        def md5_gg(cls, param1, param2, param3, param4, param5, param6, param7):
            return cls.md5_cmn(param2 & param4 | param3 & ~param4, param1, param2, param5, param6, param7)

        @classmethod
        def md5_hh(cls, param1, param2, param3, param4, param5, param6, param7):
            return cls.md5_cmn(param2 ^ param3 ^ param4, param1, param2, param5, param6, param7)

        @classmethod
        def md5_ii(cls, param1, param2, param3, param4, param5, param6, param7):
            return cls.md5_cmn(param3 ^ (param2 | ~param4), param1, param2, param5, param6, param7)

        @classmethod
        def safe_add(cls, param1, param2):
            _loc_3 = (param1 & 65535) + (param2 & 65535)
            _loc_4 = (param1 >> 16) + (param2 >> 16) + (_loc_3 >> 16)
            return cls.lshift(_loc_4, 16) | _loc_3 & 65535

        @classmethod
        def bit_rol(cls, param1, param2):
            return cls.lshift(param1, param2) | (param1 & 0xFFFFFFFF) >> (32 - param2)

        @staticmethod
        def lshift(value, count):
            r = (0xFFFFFFFF & value) << count
            return -(~(r - 1) & 0xFFFFFFFF) if r > 0x7FFFFFFF else r

    def _real_extract(self, url):
        video_id = self._match_id(url)

        video = self._download_json(
            self._API_URL_TEMPLATE % video_id, video_id)['videos'][0]

        title = video['title']

        formats = []
        for resource in video['resources']:
            resource_id = resource.get('_id')
            if not resource_id or resource_id.endswith('manifest'):
                continue

            security = self._download_json(
                self._SECURITY_URL_TEMPLATE % (video_id, resource_id),
                video_id, 'Downloading security hash for %s' % resource_id)

            security_hash = security.get('hash')
            if not security_hash:
                message = security.get('message')
                if message:
                    raise ExtractorError(
                        '%s returned error: %s' % (self.IE_NAME, message), expected=True)
                continue

            hash_code = security_hash[:2]
            received_time = int(security_hash[2:12])
            received_random = security_hash[12:22]
            received_md5 = security_hash[22:]

            sign_time = received_time + self._RESIGN_EXPIRATION
            padding = '%010d' % random.randint(1, 10000000000)

            signed_md5 = self.MD5.b64_md5(received_md5 + compat_str(sign_time) + padding)
            signed_hash = hash_code + compat_str(received_time) + received_random + compat_str(sign_time) + padding + signed_md5

            resource_url = resource['url']
            signed_url = '%s?h=%s&k=%s' % (resource_url, signed_hash, 'flash')
            if resource_id.endswith('m3u8') or resource_url.endswith('.m3u8'):
                formats.extend(self._extract_m3u8_formats(
                    signed_url, resource_id, 'mp4', entry_protocol='m3u8_native',
                    m3u8_id='hls', fatal=False))
            else:
                formats.append({
                    'url': signed_url,
                    'format_id': 'http-%s' % resource_id,
                    'height': int_or_none(resource.get('height')),
                })

        self._sort_formats(formats)

        duration = float_or_none(video.get('duration'), 1000)
        uploader = video.get('channel')
        uploader_id = str_or_none(video.get('channel_id'))

        return {
            'id': video_id,
            'title': title,
            'duration': duration,
            'uploader': uploader,
            'uploader_id': uploader_id,
            'formats': formats
        }


class GloboArticleIE(InfoExtractor):
    _VALID_URL = r'https?://.+?\.globo\.com/(?:[^/]+/)*(?P<id>[^/.]+)(?:\.html)?'

    _VIDEOID_REGEXES = [
        r'\bdata-video-id=["\'](\d{7,})',
        r'\bdata-player-videosids=["\'](\d{7,})',
        r'\bvideosIDs\s*:\s*["\']?(\d{7,})',
        r'\bdata-id=["\'](\d{7,})',
        r'<div[^>]+\bid=["\'](\d{7,})',
    ]

    _TESTS = [{
        'url': 'http://g1.globo.com/jornal-nacional/noticia/2014/09/novidade-na-fiscalizacao-de-bagagem-pela-receita-provoca-discussoes.html',
        'info_dict': {
            'id': 'novidade-na-fiscalizacao-de-bagagem-pela-receita-provoca-discussoes',
            'title': 'Novidade na fiscalização de bagagem pela Receita provoca discussões',
            'description': 'md5:c3c4b4d4c30c32fce460040b1ac46b12',
        },
        'playlist_count': 1,
    }, {
        'url': 'http://g1.globo.com/pr/parana/noticia/2016/09/mpf-denuncia-lula-marisa-e-mais-seis-na-operacao-lava-jato.html',
        'info_dict': {
            'id': 'mpf-denuncia-lula-marisa-e-mais-seis-na-operacao-lava-jato',
            'title': "Lula era o 'comandante máximo' do esquema da Lava Jato, diz MPF",
            'description': 'md5:8aa7cc8beda4dc71cc8553e00b77c54c',
        },
        'playlist_count': 6,
    }, {
        'url': 'http://gq.globo.com/Prazeres/Poder/noticia/2015/10/all-o-desafio-assista-ao-segundo-capitulo-da-serie.html',
        'only_matching': True,
    }, {
        'url': 'http://gshow.globo.com/programas/tv-xuxa/O-Programa/noticia/2014/01/xuxa-e-junno-namoram-muuuito-em-luau-de-zeze-di-camargo-e-luciano.html',
        'only_matching': True,
    }, {
        'url': 'http://oglobo.globo.com/rio/a-amizade-entre-um-entregador-de-farmacia-um-piano-19946271',
        'only_matching': True,
    }]

    @classmethod
    def suitable(cls, url):
        return False if GloboIE.suitable(url) else super(GloboArticleIE, cls).suitable(url)

    def _real_extract(self, url):
        display_id = self._match_id(url)
        webpage = self._download_webpage(url, display_id)
        video_ids = []
        for video_regex in self._VIDEOID_REGEXES:
            video_ids.extend(re.findall(video_regex, webpage))
        entries = [
            self.url_result('globo:%s' % video_id, GloboIE.ie_key())
            for video_id in orderedSet(video_ids)]
        title = self._og_search_title(webpage, fatal=False)
        description = self._html_search_meta('description', webpage)
        return self.playlist_result(entries, display_id, title, description)
