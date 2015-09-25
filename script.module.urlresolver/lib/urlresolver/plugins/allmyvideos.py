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

from t0mm0.common.net import Net
from urlresolver.plugnplay.interfaces import UrlResolver
from urlresolver.plugnplay.interfaces import PluginSettings
from urlresolver.plugnplay import Plugin
import re, os, xbmc, json
from urlresolver import common

class AllmyvideosResolver(Plugin,UrlResolver,PluginSettings):
    implements=[UrlResolver,PluginSettings]
    name="allmyvideos"
    domains=[ "allmyvideos.net" ]


    def __init__(self):
        p=self.get_setting('priority') or 100
        self.priority=int(p)
        self.net=Net()

    def get_media_url(self,host,media_id):
        url=self.get_url1st(host,media_id)
        headers={'User-Agent':common.IE_USER_AGENT,'Referer':url}
        html=self.net.http_GET(url,headers=headers).content
        stream_url = self.__get_best_source(html) 
        if stream_url:
            xbmc.sleep(2000)
            return stream_url
        
        url=self.get_url(host,media_id)
        headers={'User-Agent':common.IE_USER_AGENT,'Referer':url}
        html=self.net.http_GET(url,headers=headers).content
        
        data={}; r=re.findall(r'type="hidden" name="(.+?)"\s* value="?(.+?)">',html)
        for name,value in r: data[name]=value
        html=self.net.http_POST(url,data,headers=headers).content
        
        stream_url = self.__get_best_source(html) 
        if stream_url:
            xbmc.sleep(2000)
            return stream_url
        
        raise UrlResolver.ResolverError('could not find video')

    def __get_best_source(self, html):
        r=re.search('"sources"\s*:\s*(\[.*?\])',html, re.DOTALL)
        if r:
            sources = json.loads(r.group(1))
            max_label = 0
            stream_url = ''
            for source in sources:
                if 'label' in source and int(source['label'])>max_label:
                    stream_url = source['file']
                    max_label = int(source['label'])
            if stream_url: return stream_url+'|User-Agent=%s'%(common.IE_USER_AGENT)
        
    def get_url(self,host,media_id):
        return 'http://allmyvideos.net/%s'%media_id 

    def get_url1st(self,host,media_id):
        return 'http://allmyvideos.net/embed-%s.html'%media_id
     
    def get_host_and_id(self, url):
        r=re.search('//(?:www.)?(allmyvideos.net)/(?:embed-)?([0-9a-zA-Z]+)',url)
        if r: return r.groups()
        else: return False
        return('host','media_id')
    
    def valid_url(self,url,host):
        if self.get_setting('enabled')=='false': return False
        return (re.match('http://(?:www.)?(allmyvideos.net)/(?:embed-)?([0-9A-Za-z]+)',url) or re.match('http://(www.)?(allmyvideos.net)/embed-([0-9A-Za-z]+)[\-]*\d*[x]*\d*.*[html]*',url) or 'allmyvideos' in host)
