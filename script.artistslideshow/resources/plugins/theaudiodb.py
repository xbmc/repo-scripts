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
    from . import theaudiodb_info as settings
except ImportError:
    clowncar = ''
try:
    clowncar = settings.clowncar
except AttributeError:
    clowncar = ''


class objectConfig(object):
    def __init__(self):
        url = 'https://www.theaudiodb.com/api/v1/json/%s/' % base64.b64decode(
            clowncar.encode('ascii')).decode('ascii')
        secsinweek = int(7 * 24 * 60 * 60)
        self.ARTISTMBIDURL = url + 'artist-mb.php'
        self.ARTISTSEARCHURL = url + 'search.php'
        self.ARTISTTADBIDURL = url + 'artist.php'
        self.ALBUMURL = url + 'album.php'
        self.ALBUMSEARCHURL = url + 'searchalbum.php'
        self.ARTISTFILENAME = 'theaudiodbartistbio.nfo'
        self.ALBUMFILENAME = 'theaudiodbartistsalbums.nfo'
        self.IDFILENAME = 'theaudiodbid.nfo'
        self.CACHETIMEFILENAME = 'theaudiodbcachetime.nfo'
        self.ALBUMCACHETIMEFILENAME = 'theaudiodbalbumcachetime.nfo'
        self.HASDONATION = False
        self.CACHEEXPIRE = {}
        self.CACHEEXPIRE['low'] = int(1 * secsinweek)
        self.CACHEEXPIRE['high'] = int(2 * secsinweek)
        self.CACHEEXPIREWITHDONATION = int(secsinweek / 7)
        self.LOGLINES = []
        self.JSONURL = URL('json')

    def provides(self):
        return ['bio', 'albums', 'images', 'mbid']

    def getAlbumList(self, album_params):
        self.LOGLINES = []
        self._set_filepaths(album_params)
        url_params = {}
        albums = []
        json_data = ''
        self._check_donation(album_params.get('donated', False))
        url, url_params = self._determine_url(
            album_params, '', self.ALBUMURL, self.ALBUMSEARCHURL)
        if url:
            json_data = self._get_data(
                self.ALBUMFILEPATH, self.ALBUMCACHEFILEPATH, url, url_params)
        if json_data:
            rawalbums = json_data.get('album')
            if rawalbums is not None:
                for album in rawalbums:
                    albums.append((album.get('strAlbum', ''),
                                  album.get('strAlbumThumb', '')))
        return albums, self.LOGLINES

    def getBio(self, bio_params):
        self.LOGLINES = []
        self._set_filepaths(bio_params)
        url_params = {}
        bio = ''
        json_data = ''
        self._check_donation(bio_params.get('donated', False))
        url, url_params = self._determine_url(
            bio_params, self.ARTISTMBIDURL, self.ARTISTTADBIDURL, self.ARTISTSEARCHURL)
        if url:
            json_data = self._get_data(
                self.ARTISTFILEPATH, self.CACHEFILEPATH, url, url_params)
            self.LOGLINES.extend(['the json data is:', json_data])
        if json_data:
            artist = json_data.get('artists')
            if artist is not None:
                bio = artist[0].get(
                    'strBiography' + bio_params.get('lang', '').upper(), '')
        return bio, self.LOGLINES

    def getImageList(self, img_params):
        self.LOGLINES = []
        self._set_filepaths(img_params)
        url_params = {}
        images = []
        json_data = ''
        self._check_donation(img_params.get('donated', False))
        url, url_params = self._determine_url(
            img_params, self.ARTISTMBIDURL, self.ARTISTTADBIDURL, self.ARTISTSEARCHURL)
        if url:
            json_data = self._get_data(
                self.ARTISTFILEPATH, self.CACHEFILEPATH, url, url_params)
        if json_data:
            artist = json_data.get('artists')
            if artist is not None:
                for count in range(4):
                    if count == 0:
                        num = ''
                    else:
                        num = str(count + 1)
                    image = artist[0].get('strArtistFanart' + num, '')
                    if image:
                        images.append(image)
                if img_params.get('getall', False):
                    image = artist[0].get('strArtistThumb')
                    if image:
                        images.append(image)
        return images, self.LOGLINES

    def getMBID(self, mbid_params):
        self.LOGLINES = []
        self._set_filepaths(mbid_params)
        exists, cloglines = checkPath(self.ARTISTFILEPATH, False)
        self.LOGLINES.extend(cloglines)
        if exists:
            cloglines, rawdata = readFile(self.ARTISTFILEPATH)
            self.LOGLINES.extend(cloglines)
            try:
                json_data = _json.loads(rawdata)
            except ValueError:
                self.LOGLINES.append(
                    'no valid JSON data returned from ' + self.ARTISTFILEPATH)
                return '', self.LOGLINES
            self.LOGLINES.append(
                'musicbrainz ID found in %s file' % self.ARTISTFILEPATH)
            try:
                return json_data.get('artists')[0].get('strMusicBrainzID', ''), self.LOGLINES
            except TypeError:
                self.LOGLINES.append(
                    'error reading musicbrainz ID from ' + self.ARTISTFILEPATH)
                return '', self.LOGLINES
        else:
            return '', self.LOGLINES

    def _check_donation(self, donation):
        if donation:
            self.HASDONATION = True
            self.CACHEEXPIRE['low'] = self.CACHEEXPIREWITHDONATION
            self.CACHEEXPIRE['high'] = self.CACHEEXPIREWITHDONATION

    def _determine_url(self, params, mbidurl, tadbidurl, nameurl):
        url_params = {}
        if mbidurl:
            mbid = params.get('mbid', '')
            if mbid:
                url_params['i'] = params.get('mbid', '')
                self.LOGLINES.append(
                    'found mbid, using mbidurl to get information from theaudiodb')
                return mbidurl, url_params
        if tadbidurl:
            tadbid = self._get_audiodbid()
            if tadbid:
                url_params['i'] = tadbid
                self.LOGLINES.append(
                    'found tadbid, using tadbidurl to get information from theaudiodb')
                return tadbidurl, url_params
        if nameurl:
            url_params['s'] = params.get('artist', '')
            self.LOGLINES.append(
                'no mbid or tadbid found, using artist name to get information from theaudiodb')
            return nameurl, url_params
        return '', ''

    def _get_audiodbid(self):
        audiodbid = ''
        exists, cloglines = checkPath(self.IDFILEPATH, False)
        self.LOGLINES.extend(cloglines)
        if not exists:
            exists, cloglines = checkPath(self.ARTISTFILEPATH, False)
            self.LOGLINES.extend(cloglines)
            if exists:
                rloglines, rawdata = readFile(self.ARTISTFILEPATH)
                self.LOGLINES.extend(rloglines)
                try:
                    gotData = True
                    json_data = _json.loads(rawdata)
                except ValueError:
                    self.LOGLINES.append(
                        'no valid JSON data returned from theaudiodb.com, setting artist to None')
                    gotData = False
                if gotData:
                    artist = json_data.get('artists')
                else:
                    artist = None
                if artist is not None:
                    audiodbid = artist[0].get('idArtist', '')
                if audiodbid:
                    success, wloglines = writeFile(audiodbid, self.IDFILEPATH)
                    self.LOGLINES.extend(wloglines)
        rloglines, audiodbid = readFile(self.IDFILEPATH)
        self.LOGLINES.extend(rloglines)
        return audiodbid

    def _get_cache_time(self, cachefilepath):
        rawdata = ''
        self.LOGLINES.append(
            'getting the cache timeout information for theaudiodb')
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
            self._get_audiodbid()  # this is to generate the id file if it doesn't exist
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
        cachetime = random.randint(
            self.CACHEEXPIRE['low'], self.CACHEEXPIRE['high'])
        success, wloglines = writeFile(str(cachetime), cachefilepath)
        self.LOGLINES.append(wloglines)
        return success

    def _set_filepaths(self, params):
        self.ARTISTFILEPATH = os.path.join(
            params.get('infodir', ''), self.ARTISTFILENAME)
        self.CACHEFILEPATH = os.path.join(
            params.get('infodir', ''), self.CACHETIMEFILENAME)
        self.ALBUMCACHEFILEPATH = os.path.join(
            params.get('infodir', ''), self.ALBUMCACHETIMEFILENAME)
        self.ALBUMFILEPATH = os.path.join(
            params.get('infodir', ''), self.ALBUMFILENAME)
        self.IDFILEPATH = os.path.join(
            params.get('infodir', ''), self.IDFILENAME)
        self.EXCLUSIONFILEPATH = params.get('exclusionsfile', '')

    def _update_cache(self, filepath, cachefilepath):
        exists, cloglines = checkPath(filepath, False)
        self.LOGLINES.extend(cloglines)
        if exists:
            st = xbmcvfs.Stat(filepath)
            if time.time() - st.st_mtime() < self._get_cache_time(cachefilepath):
                self.LOGLINES.append('cached info found for theaudiodb')
                return False
            else:
                self.LOGLINES.append(
                    'outdated cached info found for theaudiodb')
                return self._put_cache_time(cachefilepath)
        else:
            self.LOGLINES.append(
                'no theaudiodb cachetime file found, creating it')
            return self._put_cache_time(cachefilepath)
