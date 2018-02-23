# -*- coding: utf-8 -*-

import sys
import urllib.request
import gzip
import io

API = sys.modules[ "__main__" ].API
URL = 'http://api.wunderground.com/api/%s/%s/%s/q/%s.%s'

def wundergroundapi(features, settings, query, fmt):
    url = URL % (API, features, settings, query, fmt)
    try:
        req = urllib.request.Request(url)
        req.add_header('Accept-encoding', 'gzip')
        response = urllib.request.urlopen(req)
        if response.info().get('Content-Encoding') == 'gzip':
            buf = io.BytesIO(response.read())
            compr = gzip.GzipFile(fileobj=buf)
            data = compr.read()
        else:
            data = response.read()
        response.close()
    except:
        data = ''
    return data
