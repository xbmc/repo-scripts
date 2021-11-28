import os
import socket
import time
from urllib.parse import urljoin

import requests
import xbmc
import xbmcaddon
import xbmcvfs

from helpers import is_local, get_url_data
from mapping import kodi_mapping

__addon__ = xbmcaddon.Addon()
__addonid__ = __addon__.getAddonInfo('id')
__version__ = __addon__.getAddonInfo('version')

HEADERS = {'User-Agent': 'Kodi Media center', 'Accept-Charset': 'utf-8'}
LANGUAGE = __addon__.getLocalizedString
DATAPATH = xbmc.translatePath(
    xbmcaddon.Addon().getAddonInfo('profile'))

socket.setdefaulttimeout(10)


def log(txt, session):
    message = '%s - %s: %s' % (__addonid__, session, txt)
    xbmc.log(msg=message, level=xbmc.LOGDEBUG)


def read_settings(session, puser=False, ptoken=False, pserver=False):
    # read settings
    settings = {}
    user = __addon__.getSetting('listenbrainzuser')
    token = __addon__.getSetting('listenbrainztoken')
    server = __addon__.getSetting('listenbrainzserver')
    songs = __addon__.getSetting('listenbrainzsubmitsongs') == 'true'
    videos = __addon__.getSetting('listenbrainzsubmitvideos') == 'true'
    radio = __addon__.getSetting('listenbrainzsubmitradio') == 'true'
    # if puser or ptoken is true, we were called by onSettingsChanged
    if puser or ptoken:
        if puser != user:
            # username changed
            pass  # TODO: Validate username
        if ptoken != token:
            # token changed
            listenbrainz.validate_token()
    elif not (user and token):
        # no username or token
        xbmc.executebuiltin(
            'Notification(%s,%s,%i)' %
            (LANGUAGE(32011), LANGUAGE(32027), 7000))
    if pserver:
        if pserver != server:
            pass  # TODO: Implement check here
    elif not server:
        pass  # TODO: Raise error
    settings['user'] = user
    settings['token'] = token
    settings['server'] = server
    settings['songs'] = songs
    settings['videos'] = videos
    settings['radio'] = radio
    return settings


def read_file(item):
    # read the queue file if we have one
    path = os.path.join(DATAPATH, item)
    if xbmcvfs.exists(path):
        with open(path, 'r') as f:
            data = f.read()
            if data:
                try:
                    data = eval(data)
                except Exception:
                    log('ERROR: Unreadable queue file: ' + path, 'utils')
                    return None
            return data
    else:
        return None


def write_file(item, data):
    # create the data dir if needed
    if not xbmcvfs.exists(DATAPATH):
        xbmcvfs.mkdir(DATAPATH)
    # save data to file
    queue_file = os.path.join(DATAPATH, item)
    with open(queue_file, 'w') as f:
        f.write(repr(data))


class ListenBrainz(object):
    """Implementation of the ListenBrainz API.

    Upstream documentation available at:
    https://listenbrainz.readthedocs.io/en/production/dev/api.html
    """

    def __init__(self):
        """Initialise ListenBrainz object."""
        self.api_version = 1

    @property
    def server(self):
        """Get server from settings."""
        return __addon__.getSetting('listenbrainzserver')

    @property
    def token(self):
        """Get token from settings."""
        return __addon__.getSetting('listenbrainztoken')

    @property
    def api_url(self):
        """Generate API URL based on server set in settings."""
        return urljoin(self.server, '/{}/'.format(self.api_version))

    def _post(self, endpoint, payload=None, auth=False):
        """Submit HTTP POST request to ListenBrainz."""
        submit_url = urljoin(self.api_url, endpoint)
        headers = HEADERS.copy()
        if auth:
            headers['Authorization'] = 'Token {}'.format(self.token)
        response = requests.post(
            url=submit_url,
            json=payload,
            headers=headers,
        )
        response.raise_for_status()
        return response

    def _get(self, endpoint, payload=None, auth=False):
        """Submit HTTP GET request to ListenBrainz."""
        submit_url = urljoin(self.api_url, endpoint)
        headers = HEADERS.copy()
        if auth:
            headers['Authorization'] = 'Token {}'.format(self.token)
        response = requests.get(
            url=submit_url,
            params=payload,
            headers=headers,
        )
        response.raise_for_status()
        return response

    def validate_server(self):
        """Validate ListenBrainz server"""
        try:
            endpoint = 'validate-token'
            payload = {'token': self.token}
            response = self._get(endpoint, payload=payload).json()
            if 'code' in response:
                return True
        except (requests.exceptions.MissingSchema,
                requests.exceptions.HTTPError,
                requests.exceptions.ConnectionError,
                ValueError):
            pass
        return False

    def validate_token(self):
        """Validate a ListenBrainz token."""
        endpoint = 'validate-token'
        if not self.token:
            xbmc.executebuiltin(
                'Notification(%s,%s,%i)' %
                (LANGUAGE(32011), LANGUAGE(32027), 7000))
            return False
        payload = {'token': self.token}
        response = self._get(endpoint, payload=payload).json()
        if 'message' in response:
            token_valid = response['message'] == 'Token valid.'
            if token_valid is False:
                xbmc.executebuiltin(
                    'Notification(%s,%s,%i)' %
                    (LANGUAGE(32011), LANGUAGE(32028), 7000))
            return token_valid

    def submit_listens(self, listen_type, payload):
        """Submit listens to ListenBrainz."""
        endpoint = 'submit-listens'
        data = {"listen_type": listen_type, "payload": payload}
        response = self._post(endpoint, data, auth=True)
        return response.json()

    def submit_single_listen(self, listen):
        """Submit a single listen to ListenBrainz."""
        listen_type = 'single'
        payload = [listen.payload]
        return self.submit_listens(listen_type, payload)

    def submit_playingnow(self, listen):
        """Submit "playing now" data to ListenBrainz."""
        listen_type = 'playing_now'
        payload = [{'track_metadata': listen.payload['track_metadata']}]
        return self.submit_listens(listen_type, payload)

    def import_listens(self, listens):
        """Imports multiple listens to ListenBrainz."""
        listen_type = 'import'
        payload = []
        for listen in listens:
            payload.append(listen.payload)
        return self.submit_listens(listen_type, payload)


class Listen(object):
    """A single ListenBrainz listen."""
    def __init__(self, tags, timestamp=None, **kwargs):
        if not timestamp:
            timestamp = int(round(time.time()))
        self.timestamp = timestamp
        self._kodi_tags = tags
        self.metadata = self.get_metadata_from_kodi_tags(tags)
        for k, v in kwargs.items():
            self.metadata[k] = v
        if not self.metadata['artist_name']:
            # TODO: Raise error; artist is required to submit a listen
            pass
        if not self.metadata['track_name']:
            # TODO: Raise error; title is required to submit a listen
            pass

    def __expr__(self):
        """Express object as a ready to submit to ListenBrainz payload"""
        data = self.metadata.copy()
        payload = {
            'listened_at': self.timestamp,
            'track_metadata': {
                'artist_name': data['artist_name'],
                'track_name': data['track_name'],
            }
        }
        if data['release_name']:
            payload['track_metadata']['release_name'] = data['release_name']
        del(data['artist_name'])
        del(data['track_name'])
        del(data['release_name'])

        # Populate the additional info
        payload['track_metadata']['additional_info'] = dict()
        additional_info = payload['track_metadata']['additional_info']

        additional_info['media_player'] = 'Kodi'
        additional_info['media_player_version'] = \
            xbmc.getInfoLabel('System.BuildVersionCode')
        additional_info['submission_client'] = __addonid__
        additional_info['submission_client_version'] = __version__

        if not is_local(data.get('origin_url')):
            url_info = get_url_data(data.get('origin_url'))
            try:
                additional_info |= url_info
            except TypeError:
                # TODO: Remove once minimum Python version is 3.9
                additional_info.update(url_info)

        for k, v in data.items():
            if v or isinstance(v, bool):
                additional_info[k] = v
        return payload

    @property
    def payload(self):
        """Get ListenBrainz ready payload dictionary."""
        return self.__expr__()

    @staticmethod
    def get_metadata_from_kodi_tags(tags):
        """Convert a Kodi *InfoTag class to a *Brainz compatible dict."""
        metadata = {}
        # if type(tags) is xbmc.InfoTagVideo:
        #     pass
        for k, v in kodi_mapping.items():
            try:
                tag = eval('tags.get{}()'.format(v))
            except AttributeError:
                tag = None
            log('Listen metadata "{}": {}'.format(k, tag), 'utils')
            metadata[k] = tag

        # If the played track is local one, don’t include it in payload
        if is_local(metadata['origin_url']):
            log('"URL" is local, so deleting.', 'utils')
            del(metadata['origin_url'])

        return metadata


listenbrainz = ListenBrainz()
