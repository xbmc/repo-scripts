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

from t0mm0.common.net import Net
from urlresolver.plugnplay.interfaces import UrlResolver
from urlresolver.plugnplay.interfaces import PluginSettings
from urlresolver.plugnplay import Plugin
import urllib2
from urlresolver import common

# Custom imports
import re



class EcostreamResolver(Plugin, UrlResolver, PluginSettings):
    implements = [UrlResolver, PluginSettings]
    name = "ecostream"

    def __init__(self):
        p = self.get_setting('priority') or 100
        self.priority = int(p)
        self.net = Net()
        self.pattern = 'http://((?:www.)?ecostream.tv)/(?:stream|embed)?/([0-9a-zA-Z]+).html'


    def get_media_url(self, host, media_id):
        # emulate click on button "Start Stream" (ss=1)
        web_url = self.get_url(host, media_id) + "?ss=1"

        try:
            html = self.net.http_GET(web_url).content
        except urllib2.URLError, e:
            common.addon.log_error(self.name + ': got http error %d fetching %s' %
                                    (e.code, web_url))
            return False

        # get vars
        sPattern = "var t=setTimeout\(\"lc\('([^']+)','([^']+)','([^']+)','([^']+)'\)"
        r = re.findall(sPattern, html)
        if r:
            for aEntry in r:
                sS = str(aEntry[0])
                sK = str(aEntry[1])
                sT = str(aEntry[2])
                sKey = str(aEntry[3])

                # send vars and retrieve stream url
                sNextUrl = 'http://www.ecostream.tv/object.php?s='+sS+'&k='+sK+'&t='+sT+'&key='+sKey

                try:
                    html = self.net.http_GET(sNextUrl).content
                except urllib2.URLError, e:
                    common.addon.log_error(self.name + ': got http error %d fetching %s' %
                                            (e.code, sNextUrl))
                    return False

                sPattern = '<param name="flashvars" value="file=(.*?)&'
                r = re.search(sPattern, html)
                if r:
                    sLinkToFile = r.group(1)
                    return sLinkToFile


        return False


    def get_url(self, host, media_id):
            return 'http://www.ecostream.tv/stream/%s.html' % (media_id)

    def get_host_and_id(self, url):
        r = re.search(self.pattern, url.replace('embed','stream'))
        if r:
            return r.groups()
        else:
            return False


    def valid_url(self, url, host):
        return re.match(self.pattern, url) or self.name in host