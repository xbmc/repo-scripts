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

from t0mm0.common.net import Net
from urlresolver.plugnplay.interfaces import UrlResolver
from urlresolver.plugnplay.interfaces import PluginSettings
from urlresolver.plugnplay import Plugin
import re
import urllib2, xbmcgui, time, xbmc
from urlresolver import common
import os



net = Net()

class VidbullResolver(Plugin, UrlResolver, PluginSettings):
    implements = [UrlResolver, PluginSettings]
    name = "vidbull"


    def __init__(self):
        p = self.get_setting('priority') or 100
        self.priority = int(p)
        self.net = Net()


    def get_media_url(self, host, media_id):
        print 'Vidbull: in get_media_url %s %s' % (host, media_id)
        url = self.get_url(host, media_id)
        html = self.net.http_GET(url).content
        #Show dialog box so user knows something is happening
        dialog = xbmcgui.DialogProgress()
        dialog.create('Resolving', 'Resolving Vidbull Link...')       
        dialog.update(0)

        time.sleep(4)

        dialog.create('Resolving', 'Resolving Vidbull Link...') 
        dialog.update(50)

        op = re.search('<input type="hidden" name="op" value="(.+?)">', html).group(1)
        postid = re.search('<input type="hidden" name="id" value="(.+?)">', html).group(1)
        rand = re.search('<input type="hidden" name="rand" value="(.+?)">', html).group(1)
        referer = ''
        method_free = ''
        down_direct = 1
        
        data = {'op': op, 'id': postid, 'rand': rand, 'referer': referer, 'method_free': method_free, 'down_direct': down_direct}

        print 'Vidbull - Requesting POST URL: %s DATA: %s' % (url, data)
        html = net.http_POST(url, data).content

        num = re.compile('event\|(.+?)\|aboutlink').findall(html)
        pre = 'http://'+num[0]+'.vidbull.com:182/d/'
        preb = re.compile('image\|(.+?)\|video\|(.+?)\|').findall(html)
        for ext, link in preb:
                    r = pre+link+'/video.'+ext
                    dialog.update(100)
                    dialog.close()
                    return r
    
    def get_url(self, host, media_id):
        print 'vidbull: in get_url %s %s' % (host, media_id)
        return 'http://www.vidbull.com/%s' % media_id 
        

    def get_host_and_id(self, url):
        r = re.search('//(.+?)/([0-9a-zA-Z]+)',url)
        if r:
            return r.groups()
        else:
            return False
        return('host', 'media_id')


    def valid_url(self, url, host):
        if self.get_setting('enabled') == 'false': return False
        return (re.match('http://(www.)?vidbull.com/' +
                         '[0-9A-Za-z]+', url) or
                         'vidbull' in host)
