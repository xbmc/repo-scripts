import gzip
import struct
import random
import urllib2
import logging
from os import path
from StringIO import StringIO
from xml.etree import ElementTree
from httplib import HTTPConnection

import rarfile


# s1-9, s101-109
SUB_DOMAINS = ['s1', 's2', 's3', 's4', 's5', 's6', 's7', 's8', 's9',
               's101', 's102', 's103', 's104', 's105', 's106', 's107', 's108', 's109']
API_URL_TEMPLATE = "http://{sub_domain}.api.bsplayer-subtitles.com/v1.php"


def check_connectivity(url, timeout=5):
    try:
        urllib2.urlopen(url, timeout=timeout)
    except urllib2.URLError:
        return False
    return True


def get_sub_domain():
    sub_domains_end = len(SUB_DOMAINS) - 1
    url = API_URL_TEMPLATE.format(sub_domain=SUB_DOMAINS[random.randint(0, sub_domains_end)])

    while not check_connectivity(url):
        url = API_URL_TEMPLATE.format(sub_domain=SUB_DOMAINS[random.randint(0, sub_domains_end)])

    return url


def python_logger(module, msg):
    logger = logging.getLogger('BSPlayer')
    logger.log((u"### [%s] - %s" % (module, msg)), level=logging.DEBUG)


def generic_open(file_path):
    rf = None
    if path.splitext(file_path)[1] == '.rar':
        rf = rarfile.RarFile(file_path)
        rfi = rf.infolist()[0]
        return rf, rf.open(rfi, 'r'), rfi.file_size
    return rf, open(file_path, 'rb'), path.getsize(file_path)


def movie_size_and_hash(file_path):
    try:
        longlong_format = '<q'  # little-endian long long
        byte_size = struct.calcsize(longlong_format)

        rf, f, file_size = generic_open(file_path)
        movie_hash = file_size

        if file_size < 65536 * 2:
            return "SizeError"

        for x in range(65536 / byte_size):
            buff = f.read(byte_size)
            (l_value,) = struct.unpack(longlong_format, buff)
            movie_hash += l_value
            movie_hash &= 0xFFFFFFFFFFFFFFFF  # to remain as 64bit number

        f.seek(max(0, file_size - 65536), 0)
        for x in range(65536 / byte_size):
            buff = f.read(byte_size)
            (l_value,) = struct.unpack(longlong_format, buff)
            movie_hash += l_value
            movie_hash &= 0xFFFFFFFFFFFFFFFF
        returned_movie_hash = "%016x" % movie_hash

        # Close File And RarFile
        f.close()
        if rf:
            rf.close()

        return file_size, returned_movie_hash
    except IOError:
        return "IOError"


class HTTP10Connection(HTTPConnection):
    _http_vsn = 10
    _http_vsn_str = "HTTP/1.0"


class HTTP10Handler(urllib2.HTTPHandler):
    def http_open(self, req):
        return self.do_open(HTTP10Connection, req)


class BSPlayer(object):
    def __init__(self, search_url=get_sub_domain(), log=python_logger):
        self.search_url = search_url
        self.token = None
        self.log = log
        if self.log.__name__ == 'python_logger':
            logging.basicConfig(
                format='%(asctime)s T:%(thread)d  %(levelname)s: %(message)s',
                datefmt='%H:%M:%S',
                level=logging.DEBUG
            )

    def __enter__(self):
        self.login()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        return self.logout()

    def api_request(self, func_name='logIn', params=''):
        headers = {
            'User-Agent': 'BSPlayer/2.x (1022.12360)',
            'Content-Type': 'text/xml; charset=utf-8',
            'Connection': 'close',
            'SOAPAction': '"http://api.bsplayer-subtitles.com/v1.php#{func_name}"'.format(func_name=func_name)
        }
        data = (
            '<?xml version="1.0" encoding="UTF-8"?>\n'
            '<SOAP-ENV:Envelope xmlns:SOAP-ENV="http://schemas.xmlsoap.org/soap/envelope/" '
            'xmlns:SOAP-ENC="http://schemas.xmlsoap.org/soap/encoding/" '
            'xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" '
            'xmlns:xsd="http://www.w3.org/2001/XMLSchema" xmlns:ns1="{search_url}">'
            '<SOAP-ENV:Body SOAP-ENV:encodingStyle="http://schemas.xmlsoap.org/soap/encoding/">'
            '<ns1:{func_name}>{params}</ns1:{func_name}></SOAP-ENV:Body></SOAP-ENV:Envelope>'
        ).format(search_url=self.search_url, func_name=func_name, params=params)

        req = urllib2.Request(self.search_url, data, headers)
        return ElementTree.fromstring(urllib2.urlopen(req).read())

    def login(self):
        # If already logged in
        if self.token:
            return True

        root = self.api_request(
            func_name='logIn',
            params=('<username></username>'
                    '<password></password>'
                    '<AppID>BSPlayer v2.67</AppID>')
        )
        res = root.find('.//return')
        if res.find('status').text == 'OK':
            self.token = res.find('data').text
            self.log("BSPlayer.login", "Logged In Successfully.")
            return True
        return False

    def logout(self):
        # If already logged out / not logged in
        if not self.token:
            return True

        root = self.api_request(
            func_name='logOut',
            params='<handle>{token}</handle>'.format(token=self.token)
        )
        res = root.find('.//return')
        self.token = None
        if res.find('status').text == 'OK':
            self.log("BSPlayer.logout", "Logged Out Successfully.")
            return True
        return False

    def search_subtitles(self, movie_path, language_ids='heb,eng', logout=False):
        if not self.login():
            return None

        if isinstance(language_ids, (tuple, list, set)):
            language_ids = ",".join(language_ids)

        movie_size, movie_hash = movie_size_and_hash(movie_path)
        root = self.api_request(
            func_name='searchSubtitles',
            params=(
                '<handle>{token}</handle>'
                '<movieHash>{movie_hash}</movieHash>'
                '<movieSize>{movie_size}</movieSize>'
                '<languageId>{language_ids}</languageId>'
                '<imdbId>*</imdbId>'
            ).format(token=self.token, movie_hash=movie_hash,
                     movie_size=movie_size, language_ids=language_ids)
        )
        res = root.find('.//return/result')
        if res.find('status').text != 'OK':
            return []

        items = root.findall('.//return/data/item')
        subtitles = []
        if items:
            self.log("BSPlayer.search_subtitles", "Subtitles Found.")
            for item in items:
                subtitles.append(dict(
                    subID=item.find('subID').text,
                    subDownloadLink=item.find('subDownloadLink').text,
                    subLang=item.find('subLang').text,
                    subName=item.find('subName').text,
                    subFormat=item.find('subFormat').text
                ))

        if logout:
            self.logout()

        return subtitles

    @staticmethod
    def download_subtitles(download_url, dest_path=r"c:\tomerz.srt"):
        opener = urllib2.build_opener(HTTP10Handler)
        opener.addheaders = [('User-Agent', 'Mozilla/4.0 (compatible; Synapse)'),
                             ('Content-Length', 0)]
        res = opener.open(download_url)
        if res:
            gf = gzip.GzipFile(fileobj=StringIO(res.read()))
            with open(dest_path, 'wb') as f:
                f.write(gf.read())
                f.flush()
            gf.close()
            return True
        return False
#
#
# if __name__ == '__main__':
#     bsp = BSPlayer()
#     subs = bsp.search_subtitles(
#         r'..\..\..\Jurassic.World.2015.720p.BluRay.x264-SPARKS\jurassic.world.2015.720p.bluray.x264-sparks.rar',
#         logout=True
#     )
#     print subs[0]['subDownloadLink']
#     print bsp.download_subtitles(subs[0]['subDownloadLink'])
