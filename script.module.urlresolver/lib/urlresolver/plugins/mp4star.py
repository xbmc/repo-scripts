"""
    urlresolver Host Plugin for mp4star.com
    Copyright (C) 2014-2015 TheHighway

    This program is free software: you can redistribute it and/or modify
    it under the terms of the GNU General Public License as published by
    the Free Software Foundation, either version 3 of the License, or
    (at your option) any later version.

    This program is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU General Public License for more details.

    You should have received a copy of the GNU General Public License
    along with this program.  If not, see <http://www.gnu.org/licenses/>.
"""

from t0mm0.common.net import Net
from urlresolver.plugnplay.interfaces import UrlResolver
from urlresolver.plugnplay.interfaces import PluginSettings
from urlresolver.plugnplay import Plugin
from urlresolver import common
import urllib
import re
import xbmc

class MP4StarResolver(Plugin, UrlResolver, PluginSettings):
    implements = [UrlResolver, PluginSettings]
    name = "mp4star"
    domains = ["mp4star.com"]
    domain = "http://mp4star.com"

    def __init__(self):
        p = self.get_setting('priority') or 100
        self.priority = int(p)
        self.net = Net()
        self.pattern = 'http://((?:www.)?mp4star.com)/\D+/(\d+)'

    def get_url(self, host, media_id):
        return self.domain + '/vid/' + media_id

    def get_host_and_id(self, url):
        r = re.search(self.pattern, url)
        if r: return r.groups()
        else: return False

    def valid_url(self, url, host):
        if self.get_setting('enabled') == 'false': return False
        return re.match(self.pattern, url) or self.name in host

    def get_media_url(self, host, media_id):
        web_url = self.get_url(host, media_id)
        post_url = web_url
        common.addon.log(web_url)
        headers = {'Referer': web_url}
        resp = self.net.http_GET(web_url)
        html = resp.content
        data = {}
        r = re.findall(r'<input type="hidden"\s*value="(.*?)"\s*name="(.+?)"', html)
        if r:
            for value, name in r: data[name] = value
            # data.update({'referer': web_url})
            # headers={'Referer':web_url}
            xbmc.sleep(4000)
            html = self.net.http_POST(post_url, data, headers=headers).content
        r = re.search('<source src="(\D+://.+?)" type="video', html)
        if r:
            xbmc.sleep(4000)
            stream_url = urllib.unquote_plus(r.group(1))
        else:
            raise UrlResolver.ResolverError('no file located')
        return stream_url
