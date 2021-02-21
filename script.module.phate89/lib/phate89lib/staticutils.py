#!/usr/bin/env python
# -*- coding: utf-8 -*-
from urllib.parse import urlencode, parse_qsl
import sys
import re
import unicodedata
from datetime import datetime
import time


PY2 = sys.version_info[0] == 2


def getParams():
    if not sys.argv[2]:
        return {}
    return dict(parse_qsl(sys.argv[2][1:]))


def parameters(p):
    for k, v in list(p.items()):
        p[k] = v
    return sys.argv[0] + '?' + urlencode(p)


def normalizeString(s):
    return unicodedata.normalize('NFKD', s).encode('ascii', 'ignore')


def guessQuality(sFileName):
    fl = sFileName.lower()
    res = ""
    if ('web-dl' in fl) or ('web.dl' in fl) or ('webdl' in fl) or ('web dl' in fl):
        res = "web-dl"
    if ('720p' in fl) and ('hdtv' in fl):
        res = "720p"
    if ('bdrip' in fl):
        res = "bdrip"
    if ('bdrip' in fl):
        res = "bdrip"
    if ('bluray' in fl):
        res = "bluray"
    if ('1080i' in fl):
        res = "1080i"
    if ('1080p' in fl):
        res = "1080p"
    if ('hdtv' in fl):
        res = "normale"
    if ('hr' in fl):
        res = "hr"
    return res


def createMenu(items, dflt):
    params = getParams()
    if 'mode' in params and params['mode'] in items:
        items[params['mode']](params)
    elif dflt:
        dflt()


def parseFileName(filename):
    tvshow = episode = season = ''
    reStrings = [
        (r'(?P<NOME>.*[^ _.-])[ _.-]+s(?P<STAGIONE>[0-9]+)[ ._-]*'
         r'e(?P<EPISODIO>[0-9]+(?:(?:[a-i]|\.[1-9])(?![0-9]))?)'),
        (r'(?P<NOME>.*[^ _.-])[ _.-]+(?P<STAGIONE>[0-9]+)x'
         r'(?P<EPISODIO>[0-9]+(?:(?:[a-i]|\.[1-9])(?![0-9]))?)'),
        (r'(?P<NOME>.*[^ _.-])[ _.-]+e(?:p[ ._-]?)?'
         r'(?P<EPISODIO>[0-9]+(?:(?:[a-i]|\.[1-9])(?![0-9]))?)')
    ]
    for rg in reStrings:
        p = re.search(rg, filename, re.IGNORECASE)
        if p:
            break
    if p:
        tvshow = p.group('NOME').replace(".", " ").replace(
            "_", " ").replace("-", " ").replace("  ", " ").strip()
        episode = int(p.group('EPISODIO'))
        if len(p.groups()) > 2:
            season = int(p.group('STAGIONE'))
        else:
            season = 1
    return tvshow, season, episode


def get_timestamp(dt=None):
    if dt is None:
        dt = datetime.now()
    return int(time.mktime(dt.timetuple())) * 1000


def get_timestamp_midnight(dt=None):
    if dt is None:
        dt = datetime.now()
    return get_timestamp(dt.replace(hour=0, minute=0, second=0, microsecond=0))


def get_date_from_timestamp(dt):
    return datetime.fromtimestamp(dt / 1e3)
