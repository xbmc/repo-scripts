"""
    urlresolver XBMC Addon
    Copyright (C) 2011 t0mm0

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

import re
import xbmc
from t0mm0.common.net import Net
from urlresolver.plugnplay.interfaces import UrlResolver
from urlresolver.plugnplay.interfaces import PluginSettings
from urlresolver.plugnplay import Plugin
from urlresolver import common

class StreamintoResolver(Plugin, UrlResolver, PluginSettings):
    implements = [UrlResolver, PluginSettings]
    name = "streaminto"
    domains = ["streamin.to"]

    def __init__(self):
        p = self.get_setting('priority') or 100
        self.priority = int(p)
        self.net = Net()
        #e.g. http://streamin.to/20xk6r5vpkch
        self.pattern = 'http://((?:www.)?streamin.to)/(.*)'

    def get_media_url(self, host, media_id):
        web_url = self.get_url(host, media_id)
        resp = self.net.http_GET(web_url)
        html = resp.content
        post_url = web_url

        # get post vars
        form_values = {}
        for i in re.finditer('<input.*?name="(.*?)".*?value="(.*?)">', html):
            form_values[i.group(1)] = i.group(2)
        xbmc.sleep(5000)
        html = self.net.http_POST(post_url, form_data=form_values).content

        # get stream url
        pattern = 'streamer:\s*"([^"]+)",'  # streamer: "
        file = 'file:\s*"([^"]+)",'  # streamer: "
        r = re.search(pattern, html)
        rr = re.search(file, html)
        if r:
            return r.group(1).replace(':1935', '') + ' swfUrl=http://streamin.to/player/player.swf live=false swfVfy=1 playpath=' + rr.group(1).replace('.flv', '')
        raise UrlResolver.ResolverError('File Not Found or removed')

    def get_url(self, host, media_id):
            return 'http://streamin.to/%s' % (media_id)

    def get_host_and_id(self, url):
        r = re.search(self.pattern, url)
        if r:
            return r.groups()
        else:
            return False

    def valid_url(self, url, host):
        if self.get_setting('enabled') == 'false': return False
        return re.match(self.pattern, url) or self.name in host
