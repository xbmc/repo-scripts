'''
Billionuploads urlresolver plugin
Copyright (C) 2013 jas0npc

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
import os
import urllib
from urlresolver import common
from t0mm0.common.net import Net 
from urlresolver.plugnplay.interfaces import UrlResolver
from urlresolver.plugnplay.interfaces import PluginSettings
from urlresolver.plugnplay import Plugin

cookie_file = os.path.join(common.profile_path, 'bu.cookies')
net = Net(cookie_file)
MAX_TRIES = 3

class billionuploads(Plugin, UrlResolver, PluginSettings):
    implements = [UrlResolver, PluginSettings]
    name = "billionuploads"
    domains = [ "billionuploads.com" ]

    def __init__(self):
        p = self.get_setting('priority') or 100
        self.priority = int(p)

    def get_media_url(self, host, media_id):
        try:
            web_url = self.get_url(host, media_id)
            headers = {
                       'Host': 'billionuploads.com'
                    }
            
            tries = 0
            while tries < MAX_TRIES:
                html = net.http_GET(web_url, headers=headers).content
            
                match=re.search('var\s+b\s*=\s*"([^"]+)', html)
                if match:
                    html = self.__incapsala_decode(match.group(1))
                    match = re.search(',\s*"(/_Incapsula[^"]+)', html)
                    incap_url = 'http://www.billionuploads.com' + match.group(1)
                    net.http_GET(incap_url, headers=headers) # Don't need content, just the cookies
                else:
                    # Even though a captcha can be returned, it seems not to be required if you just re-request the page
                    match = re.search('iframe\s+src="(/_Incapsula[^"]+)', html)
                    if match:
                        captcha_url = 'http://www.billionuploads.com' + urllib.quote(match.group(1))
                        html = net.http_GET(captcha_url, headers=headers).content
                    else:
                        # not a Incapsula or a Captcha, so probably the landing page
                        break
                
                tries = tries + 1
            else:
                raise Exception('Tries Ran Out')
            
            if re.search('>\s*File Not Found\s*<', html, re.I):
                raise Exception('File Not Found/Removed')

            data = {}
            r = re.findall(r'type="hidden"\s+name="(.+?)"\s+value="(.*?)"', html)
            for name, value in r: data[name] = value
            data['method_free']='Download or watch'
    
            html = net.http_POST(web_url, form_data = data, headers = headers).content
            
            r = re.search(r'class="[^"]*download"\s+href="([^"]+)', html)
            if r:
                return r.group(1)
            else:
                raise Exception('Unable to locate file link')
        except Exception as e:
            common.addon.log_error('****billionuploads Error occured: %s' % e)
            return self.unresolvable(code=0, msg=e)
            
    def __incapsala_decode(self, s):
        return s.decode('hex')

    def __bu_decode(self, e):
        u = [ [65, 91], [97, 123], [48, 58], [43, 44], [47, 48] ]
        i = []
        t = {}
        s = ''
        for z in u:
            for n in xrange(z[0],z[1]):
                i.append(chr(n))
    
        for n in xrange(0,64):
            t[i[n]]=n
        for n in xrange(0,len(e),72):
            a=c=0
            h = e[n:n+72]
            for l in xrange(0,len(h)):
                f = t.get(h[l])
                if f is None: continue
                a = (a << 6) + f
                c = c + 6
                while (c >= 8):
                    c = c - 8
                    s = s + chr( (a >> c) % 256 )
        return s  
 
    def get_url(self, host, media_id):
        return 'http://www.billionuploads.com/%s' % media_id

    def get_host_and_id(self, url):
        r = re.search('//(.+?)/([0-9a-zA-Z]+)',url)
        if r:
            return r.groups()
        else:
            return False
        return ('host', 'media_id')

    def valid_url(self, url, host):
        if self.get_setting('enabled') == 'false': return False
        return (re.match('http://(www.)?[bB]illion[uU]ploads.com/' +
                         '[0-9A-Za-z]+', url) or
                         'billionuploads' in host.lower())
