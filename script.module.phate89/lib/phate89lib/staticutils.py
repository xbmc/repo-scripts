#!/usr/bin/env python
# -*- coding: utf-8 -*-
import urllib
import urlparse
import sys
import re
import unicodedata

def getParams():
    if not sys.argv[2]:
        return {}
    return dict(urlparse.parse_qsl(sys.argv[2][1:]))
 
def parameters (p):
    return sys.argv[0] + '?' + urllib.urlencode(p)

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
