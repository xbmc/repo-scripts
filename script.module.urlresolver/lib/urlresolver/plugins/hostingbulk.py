"""
    urlresolver XBMC Addon
    Copyright (C) 2011 anilkuj

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

import xbmc
from t0mm0.common.net import Net
from urlresolver.plugnplay.interfaces import UrlResolver
from urlresolver.plugnplay.interfaces import PluginSettings
from urlresolver.plugnplay import Plugin
import re
import urllib2, urllib
from urlresolver import common
from lib import jsunpack

class HostingBulkResolver(Plugin, UrlResolver, PluginSettings):
    implements = [UrlResolver, PluginSettings]
    name = "hostingbulk"
    domains = [ "hostingbulk.com" ]

    def __init__(self):
        p = self.get_setting('priority') or 100
        self.priority = int(p)
        self.net = Net()

    def get_media_url(self, host, media_id):
        web_url = self.get_url(host, media_id)
        link = self.net.http_GET(web_url).content

        if link.find('File Not Found') >= 0:
            raise UrlResolver.ResolverError('The requested video was not found.')

        videoUrl = re.compile("\'file\'\s?:\s?\'([\w\/\.\:\-\=\?]+)\'").findall(link)

        if len(videoUrl) > 0:
            return videoUrl[0]
        else:
            # search for packed function
            sPattern = "<script type='text/javascript'>(eval\(function\(p,a,c,k,e,d\)\{while.+?(hostingbulk|np_vid|player_ads).+?)</script>"
            r = re.search(sPattern, link, re.DOTALL)
            if r:
                sUnpacked = jsunpack.unpack(r.group(1))
                r = re.search('file:"(.+?)",', sUnpacked)
            if r:
                return r.group(1)
            else:
                raise UrlResolver.ResolverError('No playable video found.')

    def get_url(self, host, media_id):
        #return 'http://hostingbulk.com/%s' % media_id
        return '%s/%s' % (host,media_id)

    def get_host_and_id(self, url):
        r = re.search('(http://(?:www.|)(?:.+?))/(.+)', url)
        if r:
            return r.groups()
        else:
            r = None

    def valid_url(self, url, host):
        if self.get_setting('enabled') == 'false': return False
        return re.match('http://(?:www.|)hostingbulk.com/(.+)', url) or 'hostingbulk' in host

    def get_settings_xml(self):
        xml = PluginSettings.get_settings_xml(self)
        return xml
