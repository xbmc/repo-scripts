'''
Sharerepo urlresolver plugin
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
from t0mm0.common.net import Net
from urlresolver.plugnplay.interfaces import UrlResolver
from urlresolver.plugnplay.interfaces import PluginSettings
from urlresolver.plugnplay import Plugin
from urlresolver import common

class SharerepoResolver(Plugin, UrlResolver, PluginSettings):
    implements = [UrlResolver, PluginSettings]
    name = "sharerepo"
    domains = ["sharerepo.com"]

    def __init__(self):
        p = self.get_setting('priority') or 100
        self.priority = int(p)
        self.net = Net()

    def get_media_url(self, host, media_id):
        web_url = self.get_url(host, media_id)
        headers = {
            'User-Agent': common.IE_USER_AGENT,
            'Referer': web_url
        }

        try:
            html = self.net.http_GET(web_url, headers=headers).content
        except urllib2.HTTPError as e:
            if e.code == 404:
                # sharerepo supports two different styles of links/media_ids
                # if the first fails, try the second kind
                web_url = 'http://sharerepo.com/%s' % media_id
                html = self.net.http_GET(web_url, headers=headers).content
            else:
                raise
            
        link = re.search("file\s*:\s*'([^']+)", html)
        if link:
            common.addon.log_debug('ShareRepo Link Found: %s' % link.group(1))
            return link.group(1) + '|User-Agent=%s' % (common.IE_USER_AGENT)
        else:
            raise UrlResolver.ResolverError('Unable to resolve ShareRepo Link')

    def get_url(self, host, media_id):
        return 'http://sharerepo.com/f/%s' % media_id

    def get_host_and_id(self, url):
        r = re.search('//(.+?)(?:/f)?/([0-9a-zA-Z]+)', url)
        if r:
            return r.groups()
        else:
            return False
        return('host', 'media_id')

    def valid_url(self, url, host):
        if self.get_setting('enabled') == 'false': return False
        return (re.match('http://(www.)?sharerepo.com/(f/)?' +
                         '[0-9A-Za-z]+', url) or
                         'sharerepo' in host)
