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

import json
import time
import urllib2

from clouddrive.common.exception import RequestException
from clouddrive.common.ui.logger import Logger
from clouddrive.common.utils import Utils
from cookielib import CookieJar
from clouddrive.common.ui.utils import KodiUtils


class Request(object):
    _DEFAULT_RESPONSE = '{}'
    DOWNLOAD_CHUNK_SIZE = 16 * 1024
    download_progress = 0
    url = None
    data = None
    headers = None
    tries = 1
    current_tries = 0
    delay = 0
    current_delay = 0
    backoff = 0
    before_request = None
    on_exception = None
    on_failure = None
    on_success = None
    on_complete = None
    exceptions = None
    cancel_operation = None
    waiting_retry = None
    wait = None
    read_content = True
    success = False
    response_url = None
    response_code = None
    response_info = None
    response_text = None
    response_cookies = None
    
    def __init__(self, url, data, headers=None, tries=4, delay=5, backoff=2, exceptions=None, \
                 before_request=None, on_exception=None, on_failure=None, on_success=None, on_complete=None, on_update_download=None, \
                 cancel_operation=None, waiting_retry=None, wait=None, read_content=True, download_path=None):
        self.url = url
        self.data = data
        self.headers = headers
        self.tries = tries
        self.current_tries = tries
        self.delay = delay
        self.current_delay = delay
        self.backoff = backoff
        self.before_request = before_request
        self.on_exception = on_exception
        self.on_failure = on_failure
        self.on_success = on_success
        self.on_complete = on_complete
        self.exceptions = exceptions
        self.cancel_operation = cancel_operation
        self.waiting_retry = waiting_retry
        self.wait = wait
        self.read_content = read_content
        self.download_path = download_path
        self.on_update_download = on_update_download
    
    def get_url_for_report(self, url):
        index = url.find('access_token=')
        if index > -1:
            url_report = url[:index + 13] + '*removed*'
            index = url.find('&', index + 1)
            if index > -1:
                url_report += url[index:]
            return url_report
        return url
    
    def get_headers_for_report(self, headers):
        headers_report = {}
        for header in headers:
            if header == 'authorization':
                headers_report[header] = '*removed*'
            else:
                headers_report[header] = headers[header]
        return headers_report
    
    def request(self):
        self.response_text = self._DEFAULT_RESPONSE
        if not self.exceptions:
            self.exceptions = Exception
        if not self.wait:
            self.wait = time.sleep
        if not self.headers:
            self.headers = {}
        
        for i in xrange(self.tries):
            self.current_tries = i + 1
            if self.before_request:
                self.before_request(self)
            if self.cancel_operation and self.cancel_operation():
                break
            request_report = 'Request URL: ' + self.get_url_for_report(self.url)
            request_report += '\nRequest data: ' + Utils.str(self.data)
            request_report += '\nRequest headers: ' + Utils.str(self.get_headers_for_report(self.headers))
            response_report = '<response_not_set>'
            response = None
            rex = None
            download_file = None
            try:
                Logger.debug(request_report)
                req = urllib2.Request(self.url, self.data, self.headers)
                response = urllib2.urlopen(req)
                self.response_code = response.getcode()
                self.response_info = response.info()
                self.response_url = response.geturl()
                cookiejar = CookieJar()
                cookiejar._policy._now = cookiejar._now = int(time.time())
                self.response_cookies = cookiejar.make_cookies(response, req)
                if self.read_content:
                    if self.download_path:
                        self.response_text = 'Downloading to: ' + self.download_path + '... '
                        download_file = KodiUtils.file(self.download_path, 'wb')
                        self.download_progress = 0
                        while True:
                            chunk = response.read(self.DOWNLOAD_CHUNK_SIZE)
                            if not chunk:
                                break
                            download_file.write(chunk)
                            self.download_progress += self.DOWNLOAD_CHUNK_SIZE
                            if self.on_update_download:
                                self.on_update_download(self)
                        self.response_text += ' OK.'
                    else:
                        self.response_text = response.read()
                content_length = self.response_info.getheader('content-length', -1)
                response_report = '\nResponse Headers:\n%s' % Utils.str(self.response_info)
                response_report += '\nResponse (%d) content-length=%s, len=<%s>:\n' % (self.response_code, content_length, len(self.response_text),)
                try:
                    response_report += Utils.str(self.response_text)
                except:
                    response_report += '<possible binary content>'
                self.success = True
                break
            except self.exceptions as e:
                Logger.debug('Exception...')
                root_exception = e
                response_report = '\nResponse <Exception>: ' 
                if isinstance(e, urllib2.HTTPError):
                    self.response_code = e.code
                    self.response_text = Utils.str(e.read())
                    response_report += self.response_text
                else:
                    response_report += Utils.str(e)
                rex = RequestException(Utils.str(e), root_exception, request_report, response_report)
            finally:
                try:
                    if download_file:
                        download_file.close()
                    Logger.debug(response_report)
                except:
                    Logger.debug('unable to print response_report')
                if response:
                    response.close()
            if rex:
                if self.on_exception:
                    Logger.debug('calling self.on_exception...')
                    self.on_exception(self, rex)
                if self.cancel_operation and self.cancel_operation():
                    break
                Logger.debug('current_tries: ' + str(self.current_tries) + ' maximum tries: ' + str(self.tries) + ' i: ' + str(i))
                if self.current_tries == self.tries:
                    Logger.debug('max retries reached')
                    if self.on_failure:
                        self.on_failure(self)
                    if self.on_complete:
                        self.on_complete(self)
                    Logger.debug('Raising exception...')
                    raise rex
                current_time = time.time()
                max_waiting_time = current_time + self.current_delay
                Logger.debug('current_delay: ' + str(self.current_delay) + ' seconds. Waiting...')
                while (not self.cancel_operation or not self.cancel_operation()) and max_waiting_time > current_time:
                    remaining = round(max_waiting_time-current_time)
                    if self.waiting_retry:
                        Logger.debug('calling self.waiting_retry...')
                        self.waiting_retry(self, remaining)
                    self.wait(1)
                    current_time = time.time()
                Logger.debug('Done waiting.')
                self.current_delay *= self.backoff
            
        if self.success and self.on_success:
            self.on_success(self)
        if self.on_complete:
            self.on_complete(self)
        return self.response_text
        
    def request_json(self):
        return json.loads(Utils.default(self.request(), self._DEFAULT_RESPONSE))

    def get_response_text_as_json(self):
        return json.loads(Utils.default(self.response_text, self._DEFAULT_RESPONSE))
