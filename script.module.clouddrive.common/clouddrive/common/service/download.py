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

import shutil
import threading
import time
import urllib.parse
import urllib.request

from clouddrive.common.account import AccountManager, DriveNotFoundException
from clouddrive.common.exception import ExceptionUtils
from clouddrive.common.remote.errorreport import ErrorReport
from clouddrive.common.service.base import BaseServerService, BaseHandler
from clouddrive.common.ui.logger import Logger
from clouddrive.common.ui.utils import KodiUtils
from clouddrive.common.utils import Utils
from urllib.error import HTTPError


class _SameHostAuthRedirectHandler(urllib.request.HTTPRedirectHandler):
    # urllib copies every request header to a redirect target, including Authorization. Only keep it for the same host.
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        new_req = super(_SameHostAuthRedirectHandler, self).redirect_request(req, fp, code, msg, headers, newurl)
        if new_req is not None and urllib.parse.urlsplit(newurl).netloc != urllib.parse.urlsplit(req.full_url).netloc:
            new_req.remove_header('Authorization')
        return new_req

_opener = urllib.request.build_opener(_SameHostAuthRedirectHandler)


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
    
    def _stream(self, provider, url):
        # Files are streamed through this local service instead of redirecting Kodi to the provider, because
        # Kodi logs the URLs it opens: Google needed "url|Authorization=Bearer <token>" and OneDrive's
        # download links carry a pre-authenticated "tempauth" code, so both ended up in the log.
        if provider.download_requires_auth:
            # prepare_request adds the Authorization header and refreshes the token when needed,
            # so long videos keep playing after the token expires.
            request = provider.prepare_request('get', url)
            url = request.url
            headers = dict(request.headers)
        else:
            # Pre-authenticated links (OneDrive) must not get an Authorization header.
            headers = {}
        for name in ('Range', 'If-Range'):
            value = self.headers.get(name)
            if value:
                headers[name] = value
        try:
            response = _opener.open(urllib.request.Request(url, None, headers))
        except HTTPError as e:
            response = e
        try:
            self.send_response(response.getcode())
            for name in self._STREAM_HEADERS:
                value = response.headers.get(name)
                if value:
                    self.send_header(name, value)
            self.send_header('Connection', 'close')
            self.end_headers()
            if self.command != 'HEAD':
                try:
                    shutil.copyfileobj(response, self.wfile, self._STREAM_CHUNK_SIZE)
                except Exception as e:
                    # Usually Kodi closing the connection to seek or stop. The response has started, so just stop.
                    Logger.debug('Stream ended early: %s' % Utils.str(e))
        finally:
            response.close()
        
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
