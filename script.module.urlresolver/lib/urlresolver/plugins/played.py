"""
Played.to urlresolver plugin
Copyright (C) 2013/2014 TheHighway

This program is free software: you can redistribute it and/or modify it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or (at your option) any later version.

This program is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU General Public License for more details.

You should have received a copy of the GNU General Public License along with this program. If not, see <http://www.gnu.org/licenses/>.
"""
import re
from t0mm0.common.net import Net
from urlresolver.plugnplay.interfaces import UrlResolver
from urlresolver.plugnplay.interfaces import PluginSettings
from urlresolver.plugnplay import Plugin
from urlresolver import common

class PlayedResolver(Plugin, UrlResolver, PluginSettings):
    implements = [UrlResolver, PluginSettings]
    name = "played"
    domains = ["played.to"]

    def __init__(self):
        p = self.get_setting('priority') or 100
        self.priority = int(p)
        self.net = Net()

    def get_media_url(self, host, media_id):
        web_url = self.get_url(host, media_id)
        html = self.net.http_GET(web_url, {'host': 'played.to'}).content
        r = re.findall(r'<input type="hidden" name="(.+?)"\s* value="(.*?)"', html)
        data = {}
        for name, value in r: data[name] = value
        data.update({'btn_download': 'Continue to Video'})
        html = self.net.http_POST(web_url, data).content
        match = re.search('file: "(.+?)"', html)
        if match: return match.group(1)
        else: raise UrlResolver.ResolverError('unable to locate video')

    def get_url(self, host, media_id):
            return 'http://played.to/%s' % (media_id)
    
    def get_host_and_id(self, url):
        r = re.match(r'http://(?:www.)?(played).to/(?:embed-)?([0-9a-zA-Z]+)', url)
        if r: return r.groups()
        else: return False
    
    def valid_url(self, url, host):
        if self.get_setting('enabled') == 'false': return False
        return re.match(r'http://(?:www.)?(played).to/(?:embed-)?([0-9a-zA-Z]+)', url) or 'played' in host
