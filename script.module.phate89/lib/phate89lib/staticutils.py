#!/usr/bin/env python
# -*- coding: utf-8 -*-
import urllib
try:
    from urllib.parse import urlparse, urlencode, parse_qsl
except ImportError:
    from urlparse import parse_qsl, urlparse
    from urllib import urlencode
import sys
import re
import unicodedata
from datetime import datetime
import time

def getParams():
    if not sys.argv[2]:
        return {}
    return dict(parse_qsl(sys.argv[2][1:]))
 
def parameters (p):
    return sys.argv[0] + '?' + urlencode(p)

def normalizeString(str):
    return unicodedata.normalize(
        'NFKD', unicode(unicode(str, 'utf-8'))
    ).encode('ascii', 'ignore')

def guessQuality(sFileName):
    fl=sFileName.lower()
    if ('web-dl' in fl) or ('web.dl' in fl) or ('webdl' in fl) or ('web dl' in fl):
        return "web-dl"
    elif ('720p' in fl) and ('hdtv' in fl):
        return "720p"
    elif ('bdrip' in fl):
        return "bdrip"
    elif ('bdrip' in fl):
        return "bdrip"
    elif ('bluray' in fl):
        return "bluray"
    elif ('1080i' in fl):
        return "1080i"
    elif ('1080p' in fl):
        return "1080p"
    elif ('hdtv' in fl):
        return "normale"
    elif ('hr' in fl):
        return "hr"
    return ""

def createMenu(items, dflt):
    params = getParams()
    if 'mode' in params and params['mode'] in items:
        items[params['mode']](params)
    elif dflt:
        dflt()

def parseFileName(filename):
    tvshow=episode=season=''
    reStrings=[
    '(?P<NOME>.*[^ _.-])[ _.-]+s(?P<STAGIONE>[0-9]+)[ ._-]*e(?P<EPISODIO>[0-9]+(?:(?:[a-i]|\.[1-9])(?![0-9]))?)',
    '(?P<NOME>.*[^ _.-])[ _.-]+(?P<STAGIONE>[0-9]+)x(?P<EPISODIO>[0-9]+(?:(?:[a-i]|\.[1-9])(?![0-9]))?)',
    '(?P<NOME>.*[^ _.-])[ _.-]+e(?:p[ ._-]?)?(?P<EPISODIO>[0-9]+(?:(?:[a-i]|\.[1-9])(?![0-9]))?)'
    ]
    for rg in reStrings:
        p=re.search(rg,filename,re.IGNORECASE)
        if p:
            break
    if p:
        tvshow=p.group('NOME').replace("."," ").replace("_"," ").replace("-"," ").replace("  "," ").strip()
        episode=int(p.group('EPISODIO'))
        if len(p.groups())>2:
            season=int(p.group('STAGIONE'))
        else:
            season=1
    return tvshow,season,episode

def get_timestamp(dt = None):
    if dt == None:
        dt = datetime.now()
    return int(time.mktime(dt.timetuple())) * 1000

def get_timestamp_midnight(dt = None):
    if dt == None:
        dt = datetime.now()
    return get_timestamp(dt.replace(hour=0, minute=0, second=0, microsecond=0))

def get_date_from_timestamp(dt):
    return datetime.fromtimestamp(dt / 1e3)
