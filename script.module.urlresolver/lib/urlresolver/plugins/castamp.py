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
import random
import re
import math
from t0mm0.common.net import Net
from urlresolver.plugnplay.interfaces import UrlResolver
from urlresolver.plugnplay.interfaces import PluginSettings
from urlresolver.plugnplay import Plugin
from urlresolver import common


class CastampResolver(Plugin, UrlResolver, PluginSettings):
    implements = [UrlResolver, PluginSettings]
    name = "castamp"
    domains = [ "castamp.com" ]

    def __init__(self):
        p = self.get_setting('priority') or 100
        self.priority = int(p)
        self.net = Net()
        self.pattern =  r"""(http://(?:www\.|)castamp\.com)/embed\.php\?c=(.*?)&"""

    def get_media_url(self, host, media_id):
        web_url = self.get_url(host, media_id)
        html = self.net.http_GET(web_url).content

        streamer = ""
        flashplayer = ""
        file = ""

        common.addon.log("*******************************************")
        common.addon.log("web_url: " + web_url)

        pattern_flashplayer = r"""'flashplayer': \"(.*?)\""""
        r = re.search(pattern_flashplayer, html)
        if r:
            flashplayer = r.group(1)

        pattern_streamer  = r"""'streamer': '(.*?)'"""
        r = re.search(pattern_streamer, html)
        if r:
            streamer = r.group(1)

        pattern_file = r"""'file': '(.*?)'"""
        r = re.search(pattern_file, html)
        if r:
            file = r.group(1)

        rtmp = streamer
        rtmp += '/%s swfUrl=%s live=true swfVfy=true pageUrl=%s tcUrl=%s' % (file, flashplayer, web_url, rtmp)

        return rtmp

    def get_url(self, host, media_id):
        chars = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXTZabcdefghiklmnopqrstuvwxyz"
        string_length = 8
        randomstring = ''
        for x in range(0, string_length):
            rnum = int(math.floor(random.random() * len(chars)))
            randomstring += chars[rnum:rnum+1]
        domainsa = randomstring
        return 'http://www.castamp.com/embed.php?c=%s&tk=%s' % (media_id, domainsa)

    def get_host_and_id(self, url):
        r = re.search(self.pattern, url)
        if r:
            return r.groups()
        else:
            return False

    def valid_url(self, url, host):
        if self.get_setting('enabled') == 'false': return False
        return re.match(self.pattern, url)
