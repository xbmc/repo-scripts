'''
Crunchyroll urlresolver plugin
Copyright (C) 2013 voinage

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

from t0mm0.common.net import Net
from urlresolver.plugnplay.interfaces import UrlResolver
from urlresolver.plugnplay.interfaces import PluginSettings
from urlresolver.plugnplay import Plugin
import re
import urllib2
from urlresolver import common
import os

class CrunchyRollResolver(Plugin, UrlResolver, PluginSettings):
    implements = [UrlResolver, PluginSettings]
    name = "crunchyroll"
    domains = [ "crunchyroll.com" ]


    def __init__(self):
        p = self.get_setting('priority') or 100
        self.priority = int(p)
        self.net = Net()
        #http://www.crunchyroll.co.uk/07-ghost/episode-2-nostalgic-memories-accompany-pain-573286
        #http://www.crunchyroll.com/07-ghost/episode-2-nostalgic-memories-accompany-pain-573286

    def get_media_url(self, host, media_id):
        web_url = self.get_url(host, media_id)
        html=self.net.http_GET('http://www.crunchyroll.com/android_rpc/?req=RpcApiAndroid_GetVideoWithAcl&media_id=%s'%media_id,{'Host':'www.crunchyroll.com',
             'X-Device-Uniqueidentifier':'ffffffff-931d-1f73-ffff-ffffaf02fc5f',
             'X-Device-Manufacturer':'HTC',
             'X-Device-Model':'HTC Desire',
             'X-Application-Name':'com.crunchyroll.crunchyroid',
             'X-Device-Product':'htc_bravo',
             'X-Device-Is-GoogleTV':'0'}).content
        mp4=re.compile(r'"video_url":"(.+?)","h"').findall(html.replace('\\',''))[0]
        return mp4

    def get_url(self, host, media_id):
        return 'http://www.crunchyroll.com/android_rpc/?req=RpcApiAndroid_GetVideoWithAcl&media_id=%s' % media_id
        
    def get_host_and_id(self, url):
        r = re.match(r'http://www.(crunchyroll).+?/.+?/.+?([^a-zA-Z-+]{6})', url)
        if r:
            return r.groups()
        else:
            return False

    def valid_url(self, url, host):
        if self.get_setting('enabled') == 'false': return False
        return (re.match(r'http://www.(crunchyroll).+?/.+?/.+?([^a-zA-Z-+]{6})', url) or 'crunchyroll' in host)
