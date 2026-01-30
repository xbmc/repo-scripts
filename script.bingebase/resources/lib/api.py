import json
from urllib.request import Request, urlopen
from urllib.parse import urlencode
from urllib.error import URLError, HTTPError

from resources.lib.utils import get_setting, log_error, BASE_URL


class BingebaseAPI:
    def __init__(self):
        self.token = get_setting('access_token')
        self.webhook_url = get_setting('webhook_url')

    def _request(self, url, data=None, method=None, auth=True):
        headers = {
            'Content-Type': 'application/json',
            'User-Agent': 'Kodi/script.bingebase',
        }
        if auth and self.token:
            headers['Authorization'] = 'Bearer {}'.format(self.token)

        body = json.dumps(data).encode('utf-8') if data is not None else None
        req = Request(url, data=body, headers=headers, method=method)
        try:
            response = urlopen(req, timeout=30)
            response_body = response.read().decode('utf-8')
            if response_body:
                return json.loads(response_body)
            return None
        except HTTPError as e:
            log_error('HTTP error {}'.format(e.code))
            raise
        except URLError as e:
            log_error('URL error: {}'.format(e.reason))
            raise

    def is_connected(self):
        return bool(self.token)

    def scrobble(self, payload):
        if not self.webhook_url:
            return None
        return self._request(self.webhook_url, data=payload, auth=False)

    def import_history(self, movies, episodes):
        url = '{}/api/v1/kodi/import'.format(BASE_URL)
        payload = {'movies': movies, 'episodes': episodes}
        return self._request(url, data=payload)

    def export_history(self, since=None):
        url = '{}/api/v1/kodi/export'.format(BASE_URL)
        if since:
            url += '?{}'.format(urlencode({'since': since}))
        return self._request(url)
