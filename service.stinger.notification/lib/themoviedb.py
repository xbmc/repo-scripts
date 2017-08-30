import xbmc

import requests
from requests import Timeout, ConnectionError, HTTPError

def log(message, level=xbmc.LOGDEBUG):
    xbmc.log('[service.stinger.notification:themoviedb] %s' % (message), level)

class TheMovieDatabase(object):
    # username for this key: rmrector.kodistinger
    apikey = '847ea2f858b0275a3d941528605f5a11'
    apiurl = 'https://api.themoviedb.org/3/movie/%s/keywords'

    def __init__(self):
        self.session = requests.Session()
        self.session.headers['Accept'] = 'application/json'
        self.monitor = None

    def _get_request(self, mediaid):
        try:
            result = self.session.get(self.apiurl % mediaid, params={'api_key': self.apikey}, timeout=15)
        except (Timeout, ConnectionError):
            return None
        errcount = 0
        while result.status_code == requests.codes.too_many_requests:
            if errcount > 2:
                return None
            errcount += 1
            try:
                wait = int(result.headers.get('Retry-After')) + 1
            except ValueError:
                wait = 10
            if self.monitor.waitForAbort(wait):
                return None
            try:
                result = self.session.get(self.apiurl % mediaid, params={'api_key': self.apikey}, timeout=15)
            except (Timeout, ConnectionError):
                return None

        if result.status_code == requests.codes.not_found:
            return None
        try:
            result.raise_for_status()
        except HTTPError as ex:
            log('HTTP Error: {0}'.format(ex.message), xbmc.LOGWARNING)
            return None
        return result

    def get_stingertags(self, mediaid):
        response = self._get_request(mediaid)
        if not response:
            return None

        data = response.json()
        stingers = []
        for keyword in data['keywords']:
            if keyword['name'] in ('duringcreditsstinger', 'aftercreditsstinger'):
                stingers.append(str(keyword['name']))
        return stingers
