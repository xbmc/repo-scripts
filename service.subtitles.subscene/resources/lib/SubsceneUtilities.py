# -*- coding: utf-8 -*-
import gzip
import time
from StringIO import StringIO
import xbmc
import urllib2
import re

subscene_languages = {
    'Albanian': {'id': 1, '3let': 'alb', '2let': 'sq', 'name': 'Albanian'},
    'Arabic': {'id': 2, '3let': 'ara', '2let': 'ar', 'name': 'Arabic'},
    'Big 5 code': {'id': 3, '3let': 'chi', '2let': 'zh', 'name': 'Chinese'},
    'Brazillian Portuguese': {'id': 4, '3let': 'por', '2let': 'pb', 'name': 'Brazilian Portuguese'},
    'Bulgarian': {'id': 5, '3let': 'bul', '2let': 'bg', 'name': 'Bulgarian'},
    'Chinese BG code': {'id': 7, '3let': 'chi', '2let': 'zh', 'name': 'Chinese'},
    'Croatian': {'id': 8, '3let': 'hrv', '2let': 'hr', 'name': 'Croatian'},
    'Czech': {'id': 9, '3let': 'cze', '2let': 'cs', 'name': 'Czech'},
    'Danish': {'id': 10, '3let': 'dan', '2let': 'da', 'name': 'Danish'},
    'Dutch': {'id': 11, '3let': 'dut', '2let': 'nl', 'name': 'Dutch'},
    'English': {'id': 13, '3let': 'eng', '2let': 'en', 'name': 'English'},
    'Estonian': {'id': 16, '3let': 'est', '2let': 'et', 'name': 'Estonian'},
    'Farsi/Persian': {'id': 46, '3let': 'per', '2let': 'fa', 'name': 'Persian'},
    'Finnish': {'id': 17, '3let': 'fin', '2let': 'fi', 'name': 'Finnish'},
    'French': {'id': 18, '3let': 'fre', '2let': 'fr', 'name': 'French'},
    'German': {'id': 19, '3let': 'ger', '2let': 'de', 'name': 'German'},
    'Greek': {'id': 21, '3let': 'gre', '2let': 'el', 'name': 'Greek'},
    'Hebrew': {'id': 22, '3let': 'heb', '2let': 'he', 'name': 'Hebrew'},
    'Hungarian': {'id': 23, '3let': 'hun', '2let': 'hu', 'name': 'Hungarian'},
    'Icelandic': {'id': 25, '3let': 'ice', '2let': 'is', 'name': 'Icelandic'},
    'Indonesian': {'id': 44, '3let': 'ind', '2let': 'id', 'name': 'Indonesian'},
    'Italian': {'id': 26, '3let': 'ita', '2let': 'it', 'name': 'Italian'},
    'Japanese': {'id': 27, '3let': 'jpn', '2let': 'ja', 'name': 'Japanese'},
    'Korean': {'id': 28, '3let': 'kor', '2let': 'ko', 'name': 'Korean'},
    'Lithuanian': {'id': 43, '3let': 'lit', '2let': 'lt', 'name': 'Lithuanian'},
    'Malay': {'id': 50, '3let': 'may', '2let': 'ms', 'name': 'Malay'},
    'Norwegian': {'id': 30, '3let': 'nor', '2let': 'no', 'name': 'Norwegian'},
    'Polish': {'id': 31, '3let': 'pol', '2let': 'pl', 'name': 'Polish'},
    'Portuguese': {'id': 32, '3let': 'por', '2let': 'pt', 'name': 'Portuguese'},
    'Romanian': {'id': 33, '3let': 'rum', '2let': 'ro', 'name': 'Romanian'},
    'Russian': {'id': 34, '3let': 'rus', '2let': 'ru', 'name': 'Russian'},
    'Serbian': {'id': 35, '3let': 'scc', '2let': 'sr', 'name': 'Serbian'},
    'Slovak': {'id': 36, '3let': 'slo', '2let': 'sk', 'name': 'Slovak'},
    'Slovenian': {'id': 37, '3let': 'slv', '2let': 'sl', 'name': 'Slovenian'},
    'Spanish': {'id': 38, '3let': 'spa', '2let': 'es', 'name': 'Spanish'},
    'Swedish': {'id': 39, '3let': 'swe', '2let': 'sv', 'name': 'Swedish'},
    'Thai': {'id': 40, '3let': 'tha', '2let': 'th', 'name': 'Thai'},
    'Turkish': {'id': 41, '3let': 'tur', '2let': 'tr', 'name': 'Turkish'},
    'Vietnamese': {'id': 45, '3let': 'vie', '2let': 'vi', 'name': 'Vietnamese'}
}


def get_language_codes(languages):
    codes = {}
    for lang in subscene_languages:
        if subscene_languages[lang]['3let'] in languages:
            codes[str(subscene_languages[lang]['id'])] = 1
    keys = codes.keys()
    return keys


def get_episode_pattern(episode):
    parts = episode.split(':')
    if len(parts) < 2:
        return "%%%%%"
    season = int(parts[0])
    epnr = int(parts[1])
    patterns = [
        "s%#02de%#02d" % (season, epnr),
        "%#02dx%#02d" % (season, epnr),
    ]
    if season < 10:
        patterns.append("(?:\A|\D)%dx%#02d" % (season, epnr))
    return '(?:%s)' % '|'.join(patterns)

subscene_start = time.time()


def log(module, msg):
    global subscene_start
    xbmc.log((u"### [%s] %f - %s" % (module, time.time() - subscene_start, msg,)).encode('utf-8'), level=xbmc.LOGDEBUG)


def geturl(url, cookies=None):
    log(__name__, "Getting url: %s" % url)
    try:
        request = urllib2.Request(url)
        request.add_header('Accept-encoding', 'gzip')
        if cookies:
            request.add_header('Cookie', cookies)
        request.add_header('User-Agent', 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10.11; rv:41.0) Gecko/20100101 Firefox/41.0')
        response = urllib2.urlopen(request)
        log(__name__, "request done")
        if response.info().get('Content-Encoding') == 'gzip':
            buf = StringIO(response.read())
            f = gzip.GzipFile(fileobj=buf)
            content = f.read()
        else:
            content = response.read()
        log(__name__, "read done")
        # Fix non-unicode characters in movie titles
        strip_unicode = re.compile("([^-_a-zA-Z0-9!@#%&=,/'\";:~`\$\^\*\(\)\+\[\]\.\{\}\|\?<>\\]+|[^\s]+)")
        content = strip_unicode.sub('', content)
        return_url = response.geturl()
        log(__name__, "fetching done")
    except:
        log(__name__, "Failed to get url: %s" % url)
        content = None
        return_url = None
    return content, return_url
