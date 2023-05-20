# v.0.3.0

import base64
import os
import time
import random
import xbmcvfs
from resources.lib.url import URL
from resources.lib.fileops import readFile, writeFile, deleteFile, checkPath
import json as _json
try:
    from . import fanarttv_info as settings
except ImportError:
    clowncar = ''
try:
    clowncar = settings.clowncar
except AttributeError:
    clowncar = ''


class objectConfig(object):
    def __init__(self):
        secsinweek = int(7 * 24 * 60 * 60)
        self.URL = 'https://webservice.fanart.tv/v3/music/'
        self.FILENAME = 'fanarttvartistimages.nfo'
        self.CACHETIMEFILENAME = 'fanarttvcachetime.nfo'
        self.HASCLIENTKEY = False
        self.HASDONATION = False
        self.CACHEEXPIRE = {}
        self.CACHEEXPIRE['low'] = int(1 * secsinweek)
        self.CACHEEXPIRE['high'] = int(2 * secsinweek)
        self.CACHEEXPIREWITHCLIENTKEY = int(secsinweek / 3)
        self.CACHEEXPIREWITHDONATION = int(secsinweek / 14)
        self.LOGLINES = []
        self.JSONURL = URL('json')

    def provides(self):
        return ['images']

    def getImageList(self, img_params):
        self.LOGLINES = []
        url_params = {}
        images = []
        filepath = os.path.join(img_params.get('infodir', ''), self.FILENAME)
        cachefilepath = os.path.join(img_params.get(
            'infodir', ''), self.CACHETIMEFILENAME)
        url = self.URL + img_params.get('mbid', '')
        url_params['api_key'] = base64.b64decode(
            clowncar.encode('ascii')).decode('ascii')
        if img_params.get('clientapikey', False):
            self.HASCLIENTKEY = True
            url_params['client_key'] = img_params.get('clientapikey', '')
            if img_params.get('donated', False):
                self.HASDONATION = True
                self.CACHEEXPIRE['low'] = self.CACHEEXPIREWITHDONATION
                self.CACHEEXPIRE['high'] = self.CACHEEXPIREWITHDONATION
            else:
                self.CACHEEXPIRE['low'] = self.CACHEEXPIREWITHCLIENTKEY
                self.CACHEEXPIRE['high'] = self.CACHEEXPIREWITHCLIENTKEY
        json_data = self._get_data(filepath, cachefilepath, url, url_params)
        if json_data:
            image_list = json_data.get('artistbackground', [])
            if img_params.get('getall', False):
                image_list.extend(json_data.get('artistthumb', []))
            for image in image_list:
                url = image.get('url', '')
                if url:
                    images.append(url)
        return images, self.LOGLINES

    def _get_cache_time(self, cachefilepath):
        rawdata = ''
        self.LOGLINES.append(
            'getting the cache timeout information for fanarttv')
        exists, cloglines = checkPath(cachefilepath, False)
        self.LOGLINES.extend(cloglines)
        if exists:
            success = True
        else:
            success = self._put_cache_time(cachefilepath)
        if success:
            rloglines, rawdata = readFile(cachefilepath)
            self.LOGLINES.extend(rloglines)
        try:
            cachetime = int(rawdata)
        except ValueError:
            cachetime = 0
        # this is to honor donation or client key cache time immediately instead of after old cache expires
        if self.HASDONATION and cachetime > self.CACHEEXPIREWITHDONATION:
            return self.CACHEEXPIREWITHDONATION
        elif self.HASCLIENTKEY and cachetime > self.CACHEEXPIREWITHCLIENTKEY:
            return self.CACHEEXPIREWITHCLIENTKEY
        else:
            return cachetime

    def _get_data(self, filepath, cachefilepath, url, url_params):
        json_data = ''
        if self._update_cache(filepath, cachefilepath):
            success, uloglines, json_data = self.JSONURL.Get(
                url, params=url_params)
            self.LOGLINES.extend(uloglines)
            if success:
                success, wloglines = writeFile(
                    _json.dumps(json_data), filepath)
                self.LOGLINES.extend(wloglines)
        exists, cloglines = checkPath(filepath, False)
        self.LOGLINES.extend(cloglines)
        if exists:
            rloglines, rawdata = readFile(filepath)
            self.LOGLINES.extend(rloglines)
            try:
                json_data = _json.loads(rawdata)
            except ValueError:
                success, dloglines = deleteFile(filepath)
                self.LOGLINES.extend(dloglines)
                self.LOGLINES.append(
                    'Deleted old cache file. New file will be download on next run.')
                json_data = ''
        return json_data

    def _put_cache_time(self, cachefilepath):
        cachetime = random.randint(self.CACHEEXPIRE.get(
            'low'), self.CACHEEXPIRE.get('high'))
        success, wloglines = writeFile(str(cachetime), cachefilepath)
        self.LOGLINES.append(wloglines)
        return success

    def _update_cache(self, filepath, cachefilepath):
        exists, cloglines = checkPath(filepath, False)
        self.LOGLINES.extend(cloglines)
        if exists:
            st = xbmcvfs.Stat(filepath)
            if time.time() - st.st_mtime() < self._get_cache_time(cachefilepath):
                self.LOGLINES.append('cached artist info found for fanarttv')
                return False
            else:
                self.LOGLINES.append(
                    'outdated cached artist info found for fanarttv')
                return self._put_cache_time(cachefilepath)
        else:
            self.LOGLINES.append(
                'no fanarttv cachetime file found, creating it')
            return self._put_cache_time(cachefilepath)
