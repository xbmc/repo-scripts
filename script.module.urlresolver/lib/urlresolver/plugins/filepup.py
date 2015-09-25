"""
    urlresolver XBMC Addon
    Copyright (C) 2015 tknorris

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
import re
import urllib2
import urllib
from urlresolver import common

class NoRedirection(urllib2.HTTPErrorProcessor):
    def http_response(self, request, response):
        return response

    https_response = http_response


class FilePupResolver(Plugin, UrlResolver, PluginSettings):
    implements = [UrlResolver, PluginSettings]
    name = "filepup"
    domains = ["filepup.net"]

    def __init__(self):
        p = self.get_setting('priority') or 100
        self.priority = int(p)
        self.net = Net()
        self.pattern = 'http://((?:www.)?filepup.(?:net))/(?:play|files)/([0-9a-zA-Z]+)'

    def get_media_url(self, host, media_id):
        web_url = self.get_url(host, media_id)
        headers = {
                   'User-Agent': common.IE_USER_AGENT
        }
        html = self.net.http_GET(web_url, headers=headers).content
        match = re.search("document.location='([^']+).*?DOWNLOAD AS A FREE USER", html, re.I)
        if match:
            data = urllib.urlencode({'task': 'download'})
            req = urllib2.Request(match.group(1))
            req.add_header('User-Agent', common.IE_USER_AGENT)
            opener = urllib2.build_opener(NoRedirection)
            urllib2.install_opener(opener)
            res = urllib2.urlopen(req, data=data)
            return res.info().getheader('location') + '|Referer=%s' % (web_url)
        else:
            raise UrlResolver.ResolverError('Unable to location download link')

    def get_url(self, host, media_id):
        return 'http://www.filepup.net/files/%s' % (media_id)

    def get_host_and_id(self, url):
        r = re.search(self.pattern, url)
        if r:
            return r.groups()
        else:
            return False

    def valid_url(self, url, host):
        if self.get_setting('enabled') == 'false': return False
        return re.match(self.pattern, url) or self.name in host
