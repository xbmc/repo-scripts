#-------------------------------------------------------------------------------
# Copyright (C) 2017 Carlos Guzman (cguZZman) carlosguzmang@protonmail.com
# 
# This file is part of Cloud Drive Common Module for Kodi
# 
# Cloud Drive Common Module for Kodi is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
# 
# Cloud Drive Common Module for Kodi is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
# 
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
#-------------------------------------------------------------------------------

import threading
import time

from clouddrive.common.account import AccountManager, DriveNotFoundException
from clouddrive.common.exception import ExceptionUtils
from clouddrive.common.remote.errorreport import ErrorReport
from clouddrive.common.service import upstream
from clouddrive.common.service.base import BaseServerService, BaseHandler
from clouddrive.common.ui.logger import Logger
from clouddrive.common.ui.utils import KodiUtils
from clouddrive.common.utils import Utils
from urllib.error import HTTPError


class DownloadService(BaseServerService):
    name = 'download'
    profile_path = Utils.unicode(KodiUtils.translate_path(KodiUtils.get_addon_info('profile')))
    
    def __init__(self, provider_class):
        super(DownloadService, self).__init__(provider_class)
        self._handler = Download
        
    
class Download(BaseHandler):
    # Response headers passed from the provider to Kodi when streaming.
    _STREAM_HEADERS = ('Content-Type', 'Content-Length', 'Content-Range', 'Accept-Ranges', 'Last-Modified', 'ETag')
    _STREAM_CHUNK_SIZE = 1024 * 1024
    # Players open the same file many times (probing, seeking). Remembering its download URL for a few minutes
    # saves a metadata request each time; OneDrive's pre-authenticated links stay valid for about an hour.
    _URL_CACHE_SECONDS = 300
    _url_cache = {}
    _url_cache_lock = threading.Lock()
    
    def do_GET(self):
        Logger.debug(self.path)
        data = self.path.split('/')
        code = 500
        headers = {}
        content = Utils.get_file_byte_buffer()
        if len(data) > 4 and data[1] == self.server.service.name:
            try:
                driveid = data[2]
                provider = self.server.data()
                account_manager = AccountManager(self.server.service.profile_path)
                provider.configure(account_manager, driveid)
                # Raises if the account was removed, so cached download links stop working with it.
                account_manager.get_by_driveid('drive', driveid)
                self._stream(provider, self._get_download_url(provider, driveid, data[3], data[4]))
                return
            except Exception as e:
                httpex = ExceptionUtils.extract_exception(e, HTTPError)
                if httpex:
                    code = httpex.code
                elif ExceptionUtils.extract_exception(e, DriveNotFoundException):
                    code = 404
                else:
                    code = 500
                
                ErrorReport.handle_exception(e)
                content.write(Utils.encode(ExceptionUtils.full_stacktrace(e)))
        else:
            code = 404
        self.write_response(code, content=content, headers=headers)
    
    def _get_download_url(self, provider, driveid, item_driveid, item_id):
        key = (driveid, item_driveid, item_id)
        now = time.time()
        with Download._url_cache_lock:
            cached = Download._url_cache.get(key)
            if cached and cached[1] > now:
                return cached[0]
        item = provider.get_item(item_driveid=item_driveid, item_id=item_id, include_download_info = True)
        url = item['download_info']['url']
        with Download._url_cache_lock:
            Download._url_cache = dict((k, v) for k, v in Download._url_cache.items() if v[1] > now)
            Download._url_cache[key] = (url, now + Download._URL_CACHE_SECONDS)
        return url
    
    # The provider is read in bounded chunks over a kept-open connection (service/upstream.py): a player probes a
    # file with open-ended ranges and hangs up after a few bytes, and only a chunk can be finished quickly enough to
    # reuse the connection for the player's next request. Chunks start small, for the probes, and grow for playback.
    _FIRST_CHUNK = 1024 * 1024
    _MAX_CHUNK = 8 * 1024 * 1024
    # When the player hangs up, the rest of the current chunk is read (if no larger) so the connection can be reused.
    _DRAIN_LIMIT = 2 * 1024 * 1024
    _READ_SIZE = 256 * 1024

    def _upstream_request(self, provider, url, byte_range):
        # Files are streamed through this local service instead of redirecting Kodi to the provider, because
        # Kodi logs the URLs it opens: Google needed "url|Authorization=Bearer <token>" and OneDrive's
        # download links carry a pre-authenticated "tempauth" code, so both ended up in the log.
        if provider.download_requires_auth:
            # prepare_request adds the Authorization header and refreshes the token when needed, for every chunk,
            # so long videos keep playing after the token expires.
            request = provider.prepare_request('get', url)
            url = request.url
            headers = dict(request.headers)
        else:
            # Pre-authenticated links (OneDrive) must not get an Authorization header.
            headers = {}
        if byte_range:
            headers['Range'] = byte_range
        if self.headers.get('If-Range'):
            headers['If-Range'] = self.headers.get('If-Range')
        return upstream.fetch(url, headers)

    def _stream(self, provider, url):
        wanted = upstream.parse_range(self.headers.get('Range')) if self.headers.get('Range') else (0, None)
        if self.command == 'HEAD' or wanted is None:
            # Not worth chunking: passed on as one request.
            self._send_as_is(*self._upstream_request(provider, url, self.headers.get('Range')))
            return
        start, end = wanted
        first_last = start + self._FIRST_CHUNK - 1 if end is None else min(end, start + self._FIRST_CHUNK - 1)
        key, connection, response = self._upstream_request(provider, url, 'bytes=%d-%d' % (start, first_last))
        content_range = upstream.parse_content_range(response.getheader('Content-Range'))
        if response.status != 206 or not content_range:
            # An error, or a provider that ignores ranges: its answer is passed on as it is.
            self._send_as_is(key, connection, response)
            return
        total = content_range[2]
        last = total - 1 if end is None else min(end, total - 1)
        ranged = 'Range' in self.headers
        self.send_response(206 if ranged else 200)
        for name in ('Content-Type', 'Accept-Ranges', 'Last-Modified', 'ETag'):
            value = response.getheader(name)
            if value:
                self.send_header(name, value)
        self.send_header('Content-Length', str(last - start + 1))
        if ranged:
            self.send_header('Content-Range', 'bytes %d-%d/%d' % (start, last, total))
        self.send_header('Connection', 'close')
        self.end_headers()
        position = start
        chunk = self._FIRST_CHUNK
        while True:
            sent, player_gone, failed = self._copy(response)
            position += sent
            if failed:
                connection.close()
                return
            if player_gone:
                self._drain(key, connection, response)
                return
            upstream.pool.release(key, connection, response)
            if position > last:
                return
            chunk = min(chunk * 2, self._MAX_CHUNK)
            key, connection, response = self._upstream_request(provider, url, 'bytes=%d-%d' % (position, min(last, position + chunk - 1)))
            if response.status != 206:
                Logger.debug('Stream stopped: the provider answered %d' % response.status)
                response.close()
                connection.close()
                return

    def _copy(self, response):
        """Copies the response to the player. Returns (bytes sent, the player hung up, reading the provider failed)."""
        sent = 0
        while True:
            try:
                data = response.read(self._READ_SIZE)
            except Exception as e:
                Logger.debug('Stream ended: reading from the provider failed: %s' % Utils.str(e))
                return sent, False, True
            if not data:
                return sent, False, False
            try:
                self.wfile.write(data)
            except Exception as e:
                # Usually Kodi closing the connection to seek or stop.
                Logger.debug('Stream ended early: %s' % Utils.str(e))
                return sent, True, False
            sent += len(data)

    def _drain(self, key, connection, response):
        remaining = response.length
        if remaining is not None and remaining <= self._DRAIN_LIMIT:
            try:
                response.read()
                upstream.pool.release(key, connection, response)
                return
            except Exception:
                pass
        connection.close()

    def _send_as_is(self, key, connection, response):
        try:
            self.send_response(response.status)
            for name in self._STREAM_HEADERS:
                value = response.getheader(name)
                if value:
                    self.send_header(name, value)
            self.send_header('Connection', 'close')
            self.end_headers()
            if self.command != 'HEAD':
                sent, player_gone, failed = self._copy(response)
                if not player_gone and not failed:
                    upstream.pool.release(key, connection, response)
                    return
        finally:
            if not response.isclosed():
                connection.close()


class DownloadServiceUtil(object):
    @staticmethod
    def build_download_url(driveid, item_driveid, item_id, name, addonid=None):
        return "http://{host}:{port}/{service}/{driveid}/{item_driveid}/{item_id}/{name}".format(
            host = DownloadService._interface,
            port = KodiUtils.get_service_port(DownloadService.name, addonid),
            service = DownloadService.name,
            driveid = driveid,
            item_driveid = item_driveid, 
            item_id = item_id, 
            name = name
        )
