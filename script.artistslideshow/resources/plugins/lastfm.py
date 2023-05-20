# v.0.4.0

import base64
import os
import time
import random
import defusedxml.ElementTree as _xmltree
from resources.lib.url import URL
from resources.lib.fileops import readFile, writeFile, checkPath
import xbmcvfs
try:
    from . import lastfm_info as settings
except ImportError:
    clowncar = ''
try:
    clowncar = settings.clowncar
except AttributeError:
    clowncar = ''


class objectConfig(object):
    def __init__(self):
        secsinweek = int(7 * 24 * 60 * 60)
        self.ARTISTPARAMS = {'autocorrect': '1',
                             'api_key': base64.b64decode(clowncar.encode('ascii')).decode('ascii'), 'method': 'artist.getInfo'}
        self.ALBUMPARAMS = {'autocorrect': '1',
                            'api_key': base64.b64decode(clowncar.encode('ascii')).decode('ascii'), 'method': 'artist.getTopAlbums'}
        self.SIMILARPARAMS = {'autocorrect': '1',
                              'api_key': base64.b64decode(clowncar.encode('ascii')).decode('ascii'), 'limit': '50', 'method': 'artist.getSimilar'}
        self.URL = 'https://ws.audioscrobbler.com/2.0/'
        self.BIOFILENAME = 'lastfmartistbio.nfo'
        self.ALBUMFILENAME = 'lastfmartistalbums.nfo'
        self.SIMILARFILENAME = 'lastfmartistsimilar.nfo'
        self.CACHETIMEFILENAME = 'lastfmcachetime.nfo'
        self.CACHEEXPIRE = {}
        self.CACHEEXPIRE['low'] = int(1 * secsinweek)
        self.CACHEEXPIRE['high'] = int(2 * secsinweek)
        self.LOGLINES = []
        self.TEXTURL = URL('text')

    def provides(self):
        return ['bio', 'albums', 'similar', 'mbid']

    def getAlbumList(self, album_params):
        self.LOGLINES = []
        url_params = {}
        albums = []
        filepath = os.path.join(album_params.get(
            'infodir', ''), self.ALBUMFILENAME)
        cachefilepath = os.path.join(album_params.get(
            'infodir', ''), self.CACHETIMEFILENAME)
        additionalparams = {'artist': album_params.get('artist', '')}
        url_params = dict(list(self.ALBUMPARAMS.items()) +
                          list(additionalparams.items()))
        self.LOGLINES.append('trying to get artist albums from ' + self.URL)
        try:
            xmldata = _xmltree.fromstring(self._get_data(
                filepath, cachefilepath, url_params))
        except _xmltree.ParseError:
            self.LOGLINES.append('error reading XML file')
            return [], self.LOGLINES
        match = False
        for element in xmldata.iter():
            if element.tag == "name":
                if match:
                    match = False
                else:
                    name = element.text
                    match = True
            elif element.tag == "image":
                if element.attrib.get('size') == "extralarge":
                    image = element.text
                    if not image:
                        image = ''
                    albums.append((name, image))
                    match = False
        if albums == []:
            self.LOGLINES.append('no album info found in lastfm xml file')
            return [], self.LOGLINES
        else:
            return albums, self.LOGLINES

    def getBio(self, bio_params):
        self.LOGLINES = []
        url_params = {}
        bio = ''
        filepath = os.path.join(bio_params.get(
            'infodir', ''), self.BIOFILENAME)
        cachefilepath = os.path.join(bio_params.get(
            'infodir', ''), self.CACHETIMEFILENAME)
        additionalparams = {'artist': bio_params.get(
            'artist', ''), 'lang': bio_params.get('lang', '')}
        url_params = dict(list(self.ARTISTPARAMS.items()) +
                          list(additionalparams.items()))
        self.LOGLINES.append('trying to get artist bio from ' + self.URL)
        try:
            xmldata = _xmltree.fromstring(
                self._get_data(filepath, cachefilepath, url_params))
        except _xmltree.ParseError:
            self.LOGLINES.append('error reading XML file')
            return '', self.LOGLINES
        for element in xmldata.iter():
            if element.tag == "content":
                bio = element.text
        if not bio:
            self.LOGLINES.append('no bio found in lastfm xml file')
            return '', self.LOGLINES
        else:
            return bio, self.LOGLINES

    def getSimilarArtists(self, sim_params):
        self.LOGLINES = []
        url_params = {}
        similar_artists = []
        filepath = os.path.join(sim_params.get(
            'infodir', ''), self.SIMILARFILENAME)
        cachefilepath = os.path.join(sim_params.get(
            'infodir', ''), self.CACHETIMEFILENAME)
        additionalparams = {'artist': sim_params.get('artist', '')}
        url_params = dict(list(self.SIMILARPARAMS.items()) +
                          list(additionalparams.items()))
        self.LOGLINES.append('trying to get similar artists from ' + self.URL)
        try:
            xmldata = _xmltree.fromstring(
                self._get_data(filepath, cachefilepath, url_params))
        except _xmltree.ParseError:
            self.LOGLINES.append('error reading XML file')
            return [], self.LOGLINES
        match = False
        for element in xmldata.iter():
            if element.tag == "name":
                if match:
                    match = False
                else:
                    name = element.text
                    match = True
            elif element.tag == "image":
                if element.attrib.get('size') == "extralarge":
                    image = element.text
                    if not image:
                        image = ''
                    similar_artists.append((name, image))
                    match = False
        if similar_artists == []:
            self.LOGLINES.append(
                'no similar artists info found in lastfm xml file')
            return [], self.LOGLINES
        else:
            return similar_artists, self.LOGLINES

    def getMBID(self, mbid_params):
        self.LOGLINES = []
        filepath = os.path.join(mbid_params.get(
            'infodir', ''), self.BIOFILENAME)
        exists, cloglines = checkPath(filepath, False)
        self.LOGLINES.extend(cloglines)
        if exists:
            rloglines, rawxml = readFile(filepath)
            self.LOGLINES.extend(rloglines)
            try:
                xmldata = _xmltree.fromstring(rawxml)
            except _xmltree.ParseError:
                self.LOGLINES.append(
                    'error reading musicbrainz ID from ' + filepath)
                return '', self.LOGLINES
            for element in xmldata.iter():
                if element.tag == "mbid":
                    return element.text, self.LOGLINES
            self.LOGLINES.append('no mbid found in' + filepath)
            return '', self.LOGLINES
        else:
            return '', self.LOGLINES

    def _get_cache_time(self, cachefilepath):
        rawdata = ''
        self.LOGLINES.append(
            'getting the cache timeout information for last.fm')
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
        return cachetime

    def _get_data(self, filepath, cachefilepath, url_params):
        rawxml = ''
        if self._update_cache(filepath, cachefilepath):
            success, uloglines, data = self.TEXTURL.Get(
                self.URL, params=url_params)
            self.LOGLINES.extend(uloglines)
            if success:
                success, wloglines = writeFile(data, filepath)
                self.LOGLINES.extend(wloglines)
        exists, cloglines = checkPath(filepath, False)
        self.LOGLINES.extend(cloglines)
        if exists:
            rloglines, rawxml = readFile(filepath)
            self.LOGLINES.extend(rloglines)
        return rawxml

    def _put_cache_time(self, cachefilepath):
        self.LOGLINES.append(
            'writing out the cache timeout information for last.fm')
        cachetime = random.randint(
            self.CACHEEXPIRE['low'], self.CACHEEXPIRE['high'])
        success, wloglines = writeFile(str(cachetime), cachefilepath)
        self.LOGLINES.append(wloglines)
        return success

    def _update_cache(self, filepath, cachefilepath):
        exists, cloglines = checkPath(filepath, False)
        self.LOGLINES.extend(cloglines)
        if exists:
            st = xbmcvfs.Stat(filepath)
            if time.time() - st.st_mtime() < self._get_cache_time(cachefilepath):
                self.LOGLINES.append('cached info found for last.fm')
                return False
            else:
                self.LOGLINES.append('outdated cached info found for last.fm')
                return self._put_cache_time(cachefilepath)
        else:
            self.LOGLINES.append(
                'no last.fm cachetime file found, creating it')
            return self._put_cache_time(cachefilepath)
