'''
Vidbull urlresolver plugin
Copyright (C) 2013 Vinnydude

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
import urllib2
import urllib
from t0mm0.common.net import Net
from urlresolver.plugnplay.interfaces import UrlResolver
from urlresolver.plugnplay.interfaces import PluginSettings
from urlresolver.plugnplay import Plugin
from urlresolver import common

USER_AGENT = 'Mozilla/5.0 (Linux; Android 4.4; Nexus 5 Build/BuildID) AppleWebKit/537.36 (KHTML, like Gecko) Version/4.0 Chrome/30.0.0.0 Mobile Safari/537.36'

class VidbullResolver(Plugin, UrlResolver, PluginSettings):
    implements = [UrlResolver, PluginSettings]
    name = "vidbull"
    domains = [ "vidbull.com" ]

    def __init__(self):
        p = self.get_setting('priority') or 100
        self.priority = int(p)
        self.net = Net()

    def get_media_url(self, host, media_id):
        try:
            headers = {
                       'User-Agent': USER_AGENT
                    }
            
            web_url = self.get_url(host, media_id)
            html = self.net.http_GET(web_url, headers=headers).content
            match = re.search('<source\s+src="([^"]+)', html)
            if match:
                return match.group(1)
            else:
                raise Exception('File Link Not Found')

        except urllib2.HTTPError as e:
            common.addon.log_error(self.name + ': got http error %d fetching %s' % (e.code, web_url))
            return self.unresolvable(code=3, msg=e)
        except Exception as e:
            common.addon.log('**** Vidbull Error occured: %s' % e)
            return self.unresolvable(code=0, msg=e)

    def get_url(self, host, media_id):
        return 'http://www.vidbull.com/%s' % media_id 

    def get_host_and_id(self, url):
        r = re.search('//(.+?)/(?:embed-)?([0-9a-zA-Z]+)',url)
        if r:
            return r.groups()
        else:
            return False
        return('host', 'media_id')

    def valid_url(self, url, host):
        if self.get_setting('enabled') == 'false': return False
        return (re.match('http://(www.)?vidbull.com/(?:embed-)?' +
                         '[0-9A-Za-z]+', url) or
                         'vidbull' in host)
