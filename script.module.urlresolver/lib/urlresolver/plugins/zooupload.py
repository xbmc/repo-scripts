"""
zooupload urlresolver plugin
Copyright (C) 2012 Lynx187

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
from lib import jsunpack
import xbmcgui
import re
import time


class ZoouploadResolver(Plugin, UrlResolver, PluginSettings):
    implements = [UrlResolver, PluginSettings]
    name = "zooupload"

    def __init__(self):
        p = self.get_setting('priority') or 100
        self.priority = int(p)
        self.net = Net()

    def get_media_url(self, host, media_id):
        web_url = self.get_url(host, media_id)
        try:
            lang = ({'Cookie':'lang=english;'})
            html = self.net.http_GET(web_url, headers = lang).content
        except urllib2.URLError, e:
            common.addon.log_error('zooupload: got http error %d fetching %s' %
                                  (e.code, web_url))
            return False
        dialog = xbmcgui.Dialog()            
        if re.search('>File Not Found<',html):
            dialog.ok( 'UrlResolver', 'File was deleted', '', '')
            return False #1
        r = re.search("<div id=\"player_code\"><script type='text/javascript'>(.*?)</script>",html,re.DOTALL)
        if r:
            js = jsunpack.unpack(r.group(1))
            r = re.search('src="([^"]+)"', js)
            if r:
                return r.group(1)
        return False

    def get_url(self, host, media_id):
            return 'http://zooupload.com/%s' % (media_id)

    def get_host_and_id(self, url):
        r = re.search('http://(?:www.)?(.+?)/([0-9A-Za-z]+)', url)
        if r:
            return r.groups()
        else:
            return False


    def valid_url(self, url, host):
        return re.match('http://(www.)?zooupload.com/[0-9A-Za-z]+', url) or 'zooupload' in host


