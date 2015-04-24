"""
    urlresolver XBMC Addon
    Copyright (C) 2014 TheHighway

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
import xbmcgui
from t0mm0.common.net import Net
from urlresolver.plugnplay.interfaces import UrlResolver
from urlresolver.plugnplay.interfaces import PluginSettings
from urlresolver.plugnplay import Plugin
from urlresolver import common

class Justmp4Resolver(Plugin, UrlResolver, PluginSettings):
    implements = [UrlResolver, PluginSettings]
    name = "justmp4.com"
    hostname2 = "justmp4"
    domains = ["justmp4.com"]

    def __init__(self):
        p = self.get_setting('priority') or 100
        self.priority = int(p)
        self.net = Net()
        self.pattern = 'http://((?:www.)?' + self.name + ')/\D+-embed/([0-9a-zA-Z\-_]+)*'

    def get_url(self, host, media_id):
        return 'http://%s/%s%s' % (self.name, 'kvp-embed/', media_id)

    def get_host_and_id(self, url):
        r = re.search(self.pattern, url)
        if r: return r.groups()
        else: return False

    def valid_url(self, url, host):
        if self.get_setting('enabled') == 'false': return False
        return re.match(self.pattern, url) or self.name in host or self.hostname2 in host

    def get_media_url(self, host, media_id):
        web_url = self.get_url(host, media_id)
        post_url = web_url
        common.addon.log_debug(web_url)
        headers = {'Referer': web_url}
        html = self.net.http_GET(web_url).content
        data = {}
        r = re.findall(r'<input type="hidden"\s*value="(.*?)"\s*name="(.+?)"', html)
        if r:
            for value, name in r: data[name] = value;
            xbmc.sleep(4000)
            html = self.net.http_POST(post_url, data, headers=headers).content
        try: r = re.compile('<source src="(.+?)" data-res="(\d+)" type="video/([0-9A-Za-z]+)">').findall(html)
        except: r = []
        ResList = []
        UrlList = []
        if len(r) > 0:
            for (aUrl, aRes, aFrmt) in r:
                ResList.append(aRes + ' ' + aFrmt)
                UrlList.append([aRes + ' ' + aFrmt, aUrl])
        dialogSelect = xbmcgui.Dialog()
        index = dialogSelect.select('Select Resolution', ResList)
        try:
            return UrlList[index][1]
        except:
            raise UrlResolver.ResolverError('no file located')
