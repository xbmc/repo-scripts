# -*- coding: utf-8 -*-

"""
Teramixer.com urlresolver XBMC Addon
Copyright (C) 2014 JUL1EN094 

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program. If not, see <http://www.gnu.org/licenses/>.
"""

import re
import base64
from t0mm0.common.net import Net
from urlresolver.plugnplay.interfaces import UrlResolver
from urlresolver.plugnplay.interfaces import PluginSettings
from urlresolver.plugnplay import Plugin
from urlresolver import common

class TeramixerResolver(Plugin, UrlResolver, PluginSettings):
    implements = [UrlResolver, PluginSettings]
    name       = "teramixer"
    domains    = [ 'teramixer.com' ]
    useragent  = 'Mozilla/5.0 (X11; Ubuntu; Linux i686; rv:30.0) Gecko/20100101 Firefox/30.0'    


    def __init__(self):
        p = self.get_setting('priority') or 100
        self.priority = int(p)
        self.net = Net()

    def get_media_url(self, host, media_id):
        base_url = 'http://www.' + host + '.com/' + media_id
        try:
            html = self.net.http_GET(base_url).content
            encodedUrl = re.findall("""filepath = '(.*)';""", html)[0]
            encodedUrl = encodedUrl[9:]
            encodedUrl = base64.b64decode(encodedUrl)
            if not encodedUrl.startswith('aws'): encodedUrl = encodedUrl[1:]
            stream_url = 'http://%s|User-Agent=%s' %(encodedUrl,self.useragent)
            return stream_url
        except IndexError as e:
            if re.search("""<title>File not found or deleted - Teramixer</title>""", html) :
                raise UrlResolver.ResolverError('File not found or removed')
            else:
                raise UrlResolver.ResolverError(e)

    def get_url(self, host, media_id):
        return 'http://www.teramixer.com/%s' % media_id

    def get_host_and_id(self, url):
        r = re.search('http://(www.)?(.+?).com/(embed/)?(.+)', url)
        if r :
            ls = r.groups()
            ls = (ls[1], ls[3])
            return ls
        else :
            return False

    def valid_url(self, url, host):
        if self.get_setting('enabled') == 'false':
            return False
        return re.match('http://(www.)?teramixer.com/(embed/)?[0-9A-Za-z]+', url) or 'teramixer.com' in host

    def get_settings_xml(self):
        xml = PluginSettings.get_settings_xml(self)
        return xml
