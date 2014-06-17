'''
Nosvideo urlresolver plugin
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
import re, os
from urlresolver import common

#SET ERROR_LOGO# THANKS TO VOINAGE, BSTRDMKR, ELDORADO
error_logo = os.path.join(common.addon_path, 'resources', 'images', 'redx.png')

net = Net()

class NosvideoResolver(Plugin, UrlResolver, PluginSettings):
    implements = [UrlResolver, PluginSettings]
    name = "nosvideo"

    def __init__(self):
        p = self.get_setting('priority') or 100
        self.priority = int(p)
        self.net = Net()

    def get_media_url(self, host, media_id):
        try:
            url = self.get_url(host, media_id)
            html = self.net.http_GET(url).content
            if 'This server is in maintenance mode. Refresh this page in some minutes.' in html: raise Exception('This server is in maintenance mode. Refresh this page in some minutes.')
            if '<b>File Not Found</b>' in html: raise Exception('File Not Found')
            url = re.findall('<a target="_blank" href="(.+?)" class="dotted">',html)
            html = self.net.http_GET(url[0]).content
    
            data = {}
            r = re.findall(r'type="hidden" name="(.+?)"\s* value="?(.+?)"', html)
            for name, value in r:
                data[name] = value
                data.update({'method_free':'Free Download'})
            
            html = net.http_POST(url[0], data).content

            data = {}
            r = re.findall(r'type="hidden" name="((?!(?:method_premium)).+?)"\s* value="?(.+?)"', html)
            for name, value in r:
                data[name] = value
                data.update({'method_free':'Free Download'})

            common.addon.show_countdown(30, title='Nosvideo', text='Loading Video...')
            html = net.http_POST(url[0], data).content
            
            r = re.search('<a class="select" href="(.+?)">Download</a>', html)
            if r:
                return r.group(1)
            else:
                raise Exception('could not find video')          
                                
        except Exception, e:
            common.addon.log('**** Nosvideo Error occured: %s' % e)
            common.addon.show_small_popup('Error', str(e), 5000, '')
            return self.unresolvable(code=0, msg='Exception: %s' % e)
        
    def get_url(self, host, media_id):
        return 'http://nosvideo.com/%s' % media_id 
        

    def get_host_and_id(self, url):
        r = re.search('//(.+?)/(\?v\=[0-9a-zA-Z]+)',url)
        if r:
            return r.groups()
        else:
            return False
        return('host', 'media_id')


    def valid_url(self, url, host):
        if self.get_setting('enabled') == 'false': return False
        return (re.match('http://(www.)?nosvideo.com/' +
                         '\?v\=[0-9A-Za-z]+', url) or
                         'nosvideo' in host)
