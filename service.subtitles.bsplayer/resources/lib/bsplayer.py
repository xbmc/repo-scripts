import gzip
import random
from time import sleep
from StringIO import StringIO
from xml.etree import ElementTree

from utils import movie_size_and_hash, get_session, log

# s1-9, s101-109
SUB_DOMAINS = ['s1', 's2', 's3', 's4', 's5', 's6', 's7', 's8', 's9',
               's101', 's102', 's103', 's104', 's105', 's106', 's107', 's108', 's109']
API_URL_TEMPLATE = "http://{sub_domain}.api.bsplayer-subtitles.com/v1.php"


def get_sub_domain():
    sub_domains_end = len(SUB_DOMAINS) - 1
    return API_URL_TEMPLATE.format(sub_domain=SUB_DOMAINS[random.randint(0, sub_domains_end)])


class BSPlayer(object):
    def __init__(self, search_url=None, proxies=None):
        self.session = get_session(proxies=proxies)
        self.search_url = search_url or get_sub_domain()
        self.token = None

    def __enter__(self):
        self.login()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        return self.logout()

    def api_request(self, func_name='logIn', params='', tries=5):
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

        log('BSPlayer.api_request', 'Sending request: %s.' % func_name)
        for i in xrange(tries):
            try:
                self.session.addheaders.extend(headers.items())
                res = self.session.open(self.search_url, data)
                return ElementTree.fromstring(res.read())
            except Exception, ex:
                log("BSPlayer.api_request", "ERROR: %s." % ex)
                if func_name == 'logIn':
                    self.search_url = get_sub_domain()
                sleep(1)
        log('BSPlayer.api_request', 'ERROR: Too many tries (%d)...' % tries)
        raise Exception('Too many tries...')

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
            log("BSPlayer.login", "Logged In Successfully.")
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
            log("BSPlayer.logout", "Logged Out Successfully.")
            return True
        return False

    def search_subtitles(self, movie_path, language_ids='heb,eng', logout=False):
        if not self.login():
            return None

        if isinstance(language_ids, (tuple, list, set)):
            language_ids = ",".join(language_ids)

        movie_size, movie_hash = movie_size_and_hash(movie_path)
        log('BSPlayer.search_subtitles', 'Movie Size: %s, Movie Hash: %s.' % (movie_size, movie_hash))
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
            log("BSPlayer.search_subtitles", "Subtitles Found.")
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
    def download_subtitles(download_url, dest_path, proxies=None):
        session = get_session(proxies=proxies, http_10=True)
        session.addheaders = [('User-Agent', 'Mozilla/4.0 (compatible; Synapse)'),
                             ('Content-Length', 0)]
        res = session.open(download_url)
        if res:
            gf = gzip.GzipFile(fileobj=StringIO(res.read()))
            with open(dest_path, 'wb') as f:
                f.write(gf.read())
                f.flush()
            gf.close()
            return True
        return False
