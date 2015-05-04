'''
shared.sx urlresolver plugin
Copyright (C) 2014 Lars-Daniel Weber

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

class SharedsxResolver(Plugin, UrlResolver, PluginSettings):
    implements = [UrlResolver, PluginSettings]
    name = "sharedsx"
    domains = ["shared.sx"]
    
    def __init__(self):
        p = self.get_setting('priority') or 100
        self.priority = int(p)
        self.net = Net()
    
    def get_media_url(self, host, media_id):
        web_url = self.get_url(host, media_id)
        # get landing page
        html = self.net.http_GET(web_url, headers={'Referer': web_url}).content
        
        # read POST variables into data
        data = {}
        r = re.findall(r'type="hidden" name="(.+?)"\s* value="?(.+?)"', html)
        if not r: raise UrlResolver.ResolverError('page structure changed')
        for name, value in r: data[name] = value
        
        # get delay from hoster; actually this is not needed, but we are polite
        delay = 5
        r = re.search(r'var RequestWaiting = (\d+);', html)
        if r: delay = r.groups(1)[0]
        
        # run countdown and check whether it was canceld or not
        cnt = common.addon.show_countdown(int(delay), title='shared.sx', text='Please wait for hoster...')
        if not cnt: raise UrlResolver.ResolverError('countdown was canceld by user')
        
        # get video page using POST variables
        html = self.net.http_POST(web_url, data, headers=({'Referer': web_url, 'X-Requested-With': 'XMLHttpRequest'})).content
        
        # search for content tag
        r = re.search(r'class="stream-content" data-url', html)
        if not r: raise UrlResolver.ResolverError('page structure changed')
        
        # read the data-url
        r = re.findall(r'data-url="?(.+?)"', html)
        if not r: raise UrlResolver.ResolverError('video not found')
        
        # return media URL
        return r[0]
    
    def get_url(self, host, media_id):
        return 'http://shared.sx/%s' % media_id
    
    def get_host_and_id(self, url):
        r = re.search('//(.+?)/([0-9a-zA-Z]+)', url)
        if r:
            return r.groups()
        else:
            return False
        return('host', 'media_id')
    
    def valid_url(self, url, host):
        if self.get_setting('enabled') == 'false': return False
        return (re.match('http://(www.)?shared.sx/' +
                         '[0-9A-Za-z]+', url) or
                         'shared.sx' in host)
