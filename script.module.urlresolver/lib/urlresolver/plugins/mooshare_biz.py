'''
Allmyvideos urlresolver plugin
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
import xbmc
from t0mm0.common.net import Net
from urlresolver.plugnplay.interfaces import UrlResolver
from urlresolver.plugnplay.interfaces import PluginSettings
from urlresolver.plugnplay import Plugin
from urlresolver import common

class MooShareResolver(Plugin, UrlResolver, PluginSettings):
    implements = [UrlResolver, PluginSettings]
    name = "mooshare"
    domains = [ "mooshare.biz" ]

    def __init__(self):
        p = self.get_setting('priority') or 100
        self.priority = int(p)
        self.net = Net()

    def get_media_url(self, host, media_id):
            url = self.get_url(host, media_id)
            html = self.net.http_GET(url).content
    
            data = {}
            if '<form role="search"' in html and '<Form method="POST" action=\'\'>' in html: html=html.split('<Form method="POST" action=\'\'>')[1]
            r = re.findall(r'type="hidden" name="(.+?)"\s* value="?(.+?)">', html)
            for name, value in r:
                data[name] = value
            data[u'referer']=''; data[u'usr_login']=''; data[u'imhuman']='Proceed to video'; data[u'btn_download']='Proceed to video'; 
            xbmc.sleep(5000)
            html = self.net.http_POST(url, data).content
            
            r = re.search('file\s*:\s*"(.+?)"', html)
            if r:
                return r.group(1)
            else:
                raise UrlResolver.ResolverError('could not find video')
        
    def get_url(self, host, media_id):
        return 'http://mooshare.biz/%s' % media_id 

    def get_host_and_id(self, url):
        r = re.search('//(.+?)/(?:embed-)?([0-9a-zA-Z]+)',url)
        if r:
            return r.groups()
        else:
            return False
        return('host', 'media_id')

    def valid_url(self, url, host):
        if self.get_setting('enabled') == 'false': return False
        return (re.match('http://(www.)?mooshare.biz/[0-9A-Za-z]+', url) or re.match('http://(www.)?mooshare.biz/embed-[0-9A-Za-z]+[\-]*\d*[x]*\d*.*[html]*', url) or 'mooshare' in host)
