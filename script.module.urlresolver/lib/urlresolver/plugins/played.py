"""
Played urlresolver plugin
Copyright (C) 2013 voinage

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

from t0mm0.common.net import Net
from urlresolver.plugnplay.interfaces import UrlResolver
from urlresolver.plugnplay.interfaces import PluginSettings
from urlresolver.plugnplay import Plugin
import urllib2
from urlresolver import common
import xbmcgui
import re


class playedResolver(Plugin, UrlResolver, PluginSettings):
    implements = [UrlResolver, PluginSettings]
    name = "played"

    def __init__(self):
        p = self.get_setting('priority') or 100
        self.priority = int(p)
        self.net = Net()

    def get_media_url(self, host, media_id):
        web_url = self.get_url(host, media_id)
        html=self.net.http_GET(web_url,{'host':'played.to'}).content
        id=re.compile('<input type="hidden" name="id" value="(.+?)">').findall(html)[0]
        fname=re.compile('<input type="hidden" name="fname" value="(.+?)">').findall(html)[0]
        hash=re.compile('<input type="hidden" name="hash" value="(.+?)">').findall(html)[0]
        data={'op':'download1','usr_login':'','id':id,'fname':fname,'referer':'','hash':hash,'imhuman':'Continue+to+Video'}
        html=self.net.http_POST(web_url,data).content
        played=re.compile('file: "(.+?)"').findall(html)[0]
        return played

    def get_url(self, host, media_id):
            return 'http://played.to/%s' % (media_id)

    def get_host_and_id(self, url):
        r = re.match(r'http://(played).to/([0-9a-zA-Z]+)', url)
        if r:
            return r.groups()
        else:
            return False


    def valid_url(self, url, host):
        if self.get_setting('enabled') == 'false': return False
        return re.match(r'http://(played).to/([0-9a-zA-Z]+)', url) or 'played' in host


