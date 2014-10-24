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
from lib import jsunpack

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
        code=0
        try:
            url = self.get_url(host, media_id)
            html = self.net.http_GET(url).content
            if 'File Not Found' in html:
                code=1
                raise Exception('File Not Found')
            
            headers = {
                'Referer': url
            }
    
            data = {}
            r = re.findall(r'type="hidden" name="(.+?)"\s* value="(.+?)"', html)
            for name, value in r:
                data[name] = value
            data.update({'method_free':'Free Download'})
            
            html = net.http_POST(url, data, headers=headers).content

            r = re.search('(eval\(function\(p,a,c,k,e,[dr].*)',html)
            if r:
                js = jsunpack.unpack(r.group(1))
                r = re.search('playlist=(.*)&config=',js)
                if r:
                    html = self.net.http_GET(r.group(1)).content
                    r = re.search('<file>\s*(.*)\s*</file>',html)
                    if r:
                        return r.group(1)
                    else:
                        raise Exception('Unable to locate video file')
                else:
                    raise Exception('Unable to locate playlist')
            else:
                raise Exception('Unable to locate packed data')
                                                    
        except Exception, e:
            common.addon.log('**** Nosvideo Error occured: %s' % e)
            common.addon.show_small_popup('*** Nosvideo Error occured ***', str(e), 5000, '')
            return self.unresolvable(code=code, msg='Exception: %s' % e)
        
    def get_url(self, host, media_id):
        return 'http://nosvideo.com/?v=%s' % media_id

    def get_host_and_id(self, url):
        r = re.search('//(.+?)/(?:\?v\=)?([0-9a-zA-Z]+)',url)
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
