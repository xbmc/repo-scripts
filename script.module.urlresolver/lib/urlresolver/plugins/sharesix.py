'''
sharesix urlresolver plugin
Copyright (C) 2014 tknorris

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
'''

import re
from t0mm0.common.net import Net
from urlresolver.plugnplay.interfaces import UrlResolver
from urlresolver.plugnplay.interfaces import PluginSettings
from urlresolver.plugnplay import Plugin
from urlresolver import common

USER_AGENT = 'Mozilla/5.0 (X11; Ubuntu; Linux i686; rv:30.0) Gecko/20100101 Firefox/30.0'

class SharesixResolver(Plugin, UrlResolver, PluginSettings):
    implements = [UrlResolver, PluginSettings]
    name = "sharesix"
    domains = ["sharesix.com"]

    def __init__(self):
        p = self.get_setting('priority') or 100
        self.priority = int(p)
        self.net = Net()

    def get_media_url(self, host, media_id):
        web_url = self.get_url(host, media_id)
        headers = {
            'User-Agent': USER_AGENT,
            'Referer': web_url
        }
        # Otherwise just use the original url to get the content. For sharesix
        html = self.net.http_GET(web_url).content
        
        data = {}
        r = re.findall(r'type="hidden"\s*name="(.+?)"\s*value="(.*?)"', html)
        for name, value in r:
            data[name] = value
        #data[u"method_premium"] = "Premium"
        data[u"method_free"] = "Free"
        data[u"op"] = "download1"; data[u"referer"] = web_url; data[u"usr_login"] = ""
        html = self.net.http_POST(web_url, data, headers=headers).content
        
        r = re.search("var\s+lnk1\s*=\s*'(.*?)'", html)
        if r:
            stream_url = r.group(1) + '|User-Agent=%s' % (USER_AGENT)
            return stream_url
        else:
            raise UrlResolver.ResolverError('Unable to locate link')
        
        if 'file you were looking for could not be found' in html:
            raise UrlResolver.ResolverError ('File Not Found or removed')

    def get_url(self, host, media_id):
        return 'http://%s/%s' % (host, media_id)
        
    def get_host_and_id(self, url):
        r = re.search('//(.+?)/([0-9a-zA-Z/]+)', url)
        if r:
            return r.groups()
        else:
            return False

    def valid_url(self, url, host):
        if self.get_setting('enabled') == 'false': return False
        return (re.match('http://(www.)?sharesix.com/' +
                         '[0-9A-Za-z]+', url) or
                         'sharesix' in host)
