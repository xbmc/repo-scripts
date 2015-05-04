"""
urlresolver XBMC Addon
Copyright (C) 2011 t0mm0

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
import urllib2
import os
from t0mm0.common.net import Net
from urlresolver.plugnplay.interfaces import UrlResolver
from urlresolver.plugnplay.interfaces import PluginSettings
from urlresolver.plugnplay import Plugin
from urlresolver import common


class EcostreamResolver(Plugin, UrlResolver, PluginSettings):
    implements = [UrlResolver, PluginSettings]
    name = "ecostream"
    domains = [ "ecostream.tv" ]
    profile_path = common.profile_path
    cookie_file = os.path.join(profile_path, 'ecostream.cookies')

    def __init__(self):
        p = self.get_setting('priority') or 100
        self.priority = int(p)
        self.net = Net()
        self.pattern = 'http://((?:www.)?ecostream.tv)/(?:stream|embed)?/([0-9a-zA-Z]+).html'

    def get_media_url(self, host, media_id):
        web_url = self.get_url(host, media_id)
        html = self.net.http_GET(web_url).content
        if re.search('>File not found!<', html):
            raise UrlResolver.ResolverError('File Not Found or removed')
        self.net.save_cookies(self.cookie_file)
        
        web_url = 'http://www.ecostream.tv/js/ecoss.js'
        js = self.net.http_GET(web_url).content
        r = re.search("\$\.post\('([^']+)'[^;]+'#auth'\).html\(''\)", js)
        if not r:
            raise UrlResolver.ResolverError('Posturl not found')

        post_url = r.group(1)
        r = re.search('data\("tpm",([^\)]+)\);', js)
        if not r:
            raise UrlResolver.ResolverError('Postparameterparts not found')
        post_param_parts = r.group(1).split('+')
        found_parts = []
        for part in post_param_parts:
            pattern = "%s='([^']+)'" % part.strip()
            r = re.search(pattern, html)
            if not r:
                raise UrlResolver.ResolverError('Formvaluepart not found')
            found_parts.append(r.group(1))
        tpm = ''.join(found_parts)
        # emulate click on button "Start Stream"
        postHeader = ({'Referer': web_url, 'X-Requested-With': 'XMLHttpRequest'})
        web_url = 'http://www.ecostream.tv' + post_url
        self.net.set_cookies(self.cookie_file)
        html = self.net.http_POST(web_url, {'id': media_id, 'tpm': tpm}, headers=postHeader).content
        sPattern = '"url":"([^"]+)"'
        r = re.search(sPattern, html)
        if not r:
            raise UrlResolver.ResolverError('Unable to resolve Ecostream link. Filelink not found.')
        sLinkToFile = 'http://www.ecostream.tv' + r.group(1)
        return urllib2.unquote(sLinkToFile)

    def get_url(self, host, media_id):
            return 'http://www.ecostream.tv/stream/%s.html' % (media_id)

    def get_host_and_id(self, url):
        r = re.search(self.pattern, url.replace('embed','stream'))
        if r:
            return r.groups()
        else:
            return False

    def valid_url(self, url, host):
        if self.get_setting('enabled') == 'false': return False
        return re.match(self.pattern, url) or self.name in host
