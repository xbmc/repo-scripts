"""
primeshare urlresolver plugin
Copyright (C) 2013 Lynx187

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
import os
from t0mm0.common.net import Net
from urlresolver.plugnplay.interfaces import UrlResolver
from urlresolver.plugnplay.interfaces import PluginSettings
from urlresolver.plugnplay import Plugin
from urlresolver import common
from lib import jsunpack

class PrimeshareResolver(Plugin, UrlResolver, PluginSettings):
    implements = [UrlResolver, PluginSettings]
    name = "primeshare"
    domains = ["primeshare.tv"]
    profile_path = common.profile_path
    cookie_file = os.path.join(profile_path, 'primeshare.cookies')

    def __init__(self):
        p = self.get_setting('priority') or 100
        self.priority = int(p)
        self.net = Net()

    def get_media_url(self, host, media_id):
        web_url = self.get_url(host, media_id)
        html = self.net.http_GET(web_url).content
        if re.search('>File not exist<', html):
            raise UrlResolver.ResolverError('File Not Found or removed')
        self.net.save_cookies(self.cookie_file)
        headers = {'Referer': web_url}
        # wait required
        common.addon.show_countdown(8)
        self.net.set_cookies(self.cookie_file)
        html = self.net.http_POST(web_url, form_data={'hash': media_id}, headers=headers).content
        r = re.compile("clip:.*?url: '([^']+)'", re.DOTALL).findall(html)
        if not r:
            r = re.compile("download\('([^']+)'", re.DOTALL).findall(html)
        if not r:
            raise UrlResolver.ResolverError('Unable to resolve Primeshare link. Filelink not found.')
        return r[0]

    def get_url(self, host, media_id):
            return 'http://primeshare.tv/download/%s' % (media_id)

    def get_host_and_id(self, url):
        r = re.search('http://(?:www.)(.+?)/download/([0-9A-Za-z]+)', url)
        if r:
            return r.groups()       
        else:
            r = re.search('//(.+?)/download/([0-9A-Za-z]+)', url)
            if r:
                return r.groups()
            else:
                return False

    def valid_url(self, url, host):
        return re.match('http://(www.)?primeshare.tv/download/[0-9A-Za-z]+', url) or 'primeshare' in host


