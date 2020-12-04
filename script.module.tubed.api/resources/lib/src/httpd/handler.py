# -*- coding: utf-8 -*-
"""
    Copyright (C) 2020 Tubed API (script.module.tubed.api)

    This file is part of script.module.tubed.api

    SPDX-License-Identifier: GPL-2.0-only
    See LICENSES/GPL-2.0-only.txt for more information.
"""

import os
import re
import traceback
from http.server import BaseHTTPRequestHandler
from ipaddress import ip_address

import requests
import xbmc  # pylint: disable=import-error
import xbmcgui  # pylint: disable=import-error
import xbmcvfs  # pylint: disable=import-error

from ..constants import TEMP_DIRECTORY
from ..tubed_api.utils.logger import Log

LOG = Log('httpd', __file__)


class RequestHandler(BaseHTTPRequestHandler):
    cache_path = xbmcvfs.translatePath(TEMP_DIRECTORY)
    chunk_size = 1024 * 64

    def log_message(self, format, *args):  # pylint: disable=redefined-builtin
        return  # disable BaseHTTPRequestHandler logging mechanism

    def connection_allowed(self):
        return ip_address(self.client_address[0]).is_private

    def _get_path(self):
        return os.path.join(self.cache_path, self.path.strip('/').strip('\\'))

    def _get_chunks(self, data):
        for i in range(0, len(data), self.chunk_size):
            yield data[i:i + self.chunk_size]

    def do_GET(self):  # pylint: disable=invalid-name
        if not self.connection_allowed():
            LOG.warning('Rejected GET connection from %s' %
                        ip_address(self.client_address[0]))
            self.send_error(403)
            return

        if self.path.endswith('.mpd'):
            dash_manifest = self._get_path()
            LOG.debug('A manifest was requested @ %s' % self.path)

            self.send_response(200)
            self.send_header('Content-Type', 'application/xml+dash')
            self.send_header('Content-Length', str(os.path.getsize(dash_manifest)))
            self.end_headers()

            try:
                with open(dash_manifest, 'rb') as file_handle:
                    chunk = True
                    while chunk:
                        chunk = file_handle.read(self.chunk_size)
                        if chunk:
                            self.wfile.write(chunk)

                LOG.debug('A manifest was delivered from %s' % self.path)

            except IOError:
                LOG.error('An IOError occurred when retrieving the manifest @ %s' % self.path)
                LOG.error(traceback.format_exc())
                self.send_error(404)

            except:  # pylint: disable=bare-except
                LOG.error('An unknown occurred when retrieving the manifest @ %s' % self.path)
                LOG.error(traceback.format_exc())
                self.send_error(500)

        elif self.path == '/ping':
            self.send_error(204)

        else:
            LOG.error('Rejected GET connection to an unknown resource @ %s' % self.path)
            self.send_error(501)

    def do_HEAD(self):  # pylint: disable=invalid-name
        if not self.connection_allowed():
            LOG.warning('Rejected HEAD connection from %s' %
                        ip_address(self.client_address[0]))
            self.send_error(403)
            return

        if self.path.endswith('.mpd'):
            dash_manifest = self._get_path()

            LOG.debug('A manifest existence check was requested @ %s' % self.path)

            if not os.path.isfile(dash_manifest):
                LOG.error('A manifest does not exist @ %s' % self.path)
                self.send_error(404)
                return

            self.send_response(200)
            self.send_header('Content-Type', 'application/xml+dash')
            self.send_header('Content-Length', str(os.path.getsize(dash_manifest)))
            self.end_headers()

            LOG.error('A manifest exists @ %s' % self.path)
            return

        LOG.error('Rejected HEAD connection to an unknown resource @ %s' % self.path)
        self.send_error(501)

    def do_POST(self):  # pylint: disable=invalid-name
        if not self.connection_allowed():
            LOG.warning('Rejected POST connection from %s' %
                        ip_address(self.client_address[0]))
            self.send_error(403)
            return

        if self.path.startswith('/widevine'):
            LOG.debug('A widevine license request was made')

            url = xbmcgui.Window(10000).getProperty('tubed-api-license_url')
            token = xbmcgui.Window(10000).getProperty('tubed-api-license_token')

            if not url:
                LOG.error('No license url was found')
                self.send_error(404)
                return

            if not token:
                LOG.error('No license token was found')
                self.send_error(403)
                return

            size_limit = None

            length = int(self.headers['Content-Length'])
            data = self.rfile.read(length)

            headers = {
                'Content-Type': 'application/x-www-form-urlencoded',
                'Authorization': 'Bearer %s' % token
            }

            response = requests.post(url=url, headers=headers, data=data, stream=True)

            content = response.raw.read(int(response.headers.get('content-length')))

            header, body = content.split('\r\n\r\n'.encode('utf-8'))
            header = header.decode('utf-8')

            authorized_formats = re.search(r'^Authorized-Format-Types:\s*(?P<types>.+?)\r*$',
                                           header, re.MULTILINE)
            if authorized_formats:
                authorized_types = authorized_formats.group('types').split(',')

                formats = {
                    'SD': (1280 * 528) - 1,
                    'HD720': 1280 * 720,
                    'HD': 7680 * 4320
                }

                if 'HD' in authorized_types:
                    size_limit = formats['HD']

                elif 'HD720' in authorized_types:
                    if xbmc.getCondVisibility('system.platform.android') == 1:
                        size_limit = formats['HD720']
                    else:
                        size_limit = formats['SD']

                elif 'SD' in authorized_types:
                    size_limit = formats['SD']

            self.send_response(200)

            if size_limit:
                self.send_header('X-Limit-Video', 'max={size_limit}px'
                                 .format(size_limit=str(size_limit)))

            for header, value in response.headers.items():
                if value.lower() == 'content-length':
                    self.send_header(value, str(len(body)))

                else:
                    self.send_header(header, value)

            self.end_headers()

            for chunk in self._get_chunks(body):
                self.wfile.write(chunk)

            LOG.debug('A widevine license response was sent')
            return

        LOG.error('Rejected POST connection to an unknown resource @ %s' % self.path)
        self.send_error(501)
