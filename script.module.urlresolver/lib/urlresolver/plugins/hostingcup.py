'''
dailymotion urlresolver plugin
Copyright (C) 2011 cyrus007

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
from vidxden import unpack_js

class HostingcupResolver(Plugin, UrlResolver, PluginSettings):
    implements = [UrlResolver, PluginSettings]
    name = "hostingcup"

    def __init__(self):
        p = self.get_setting('priority') or 100
        self.priority = int(p)
        self.net = Net()
        self.pattern = 'http://(www.)?hostingcup.com/[0-9A-Za-z]+'


    def get_media_url(self, host, media_id):
        web_url = self.get_url(host, media_id)
        try:
            html = self.net.http_GET(web_url).content
            page = ''.join(html.splitlines()).replace('\t','')
            r = re.search("return p\}\(\'(.+?)\',\d+,\d+,\'(.+?)\'", page)
            if r:
                p, k = r.groups()
            else:
                raise Exception ('packed javascript embed code not found')
    
            decrypted_data = unpack_js(p, k)
            r = re.search('file.\',.\'(.+?).\'', decrypted_data)
            if not r:
                r = re.search('src="(.+?)"', decrypted_data)
            if r:
                stream_url = r.group(1)
            else:
                raise Exception ('stream url not found')
    
            return stream_url
        
        except urllib2.URLError, e:
            common.addon.log_error('Hostingcup: got http error %d fetching %s' %
                                  (e.code, web_url))
            common.addon.show_small_popup('Error','Http error: '+str(e), 5000, error_logo)
            return self.unresolvable(code=3, msg=e)
        
        except Exception, e:
            common.addon.log_error('**** Hostingcup Error occured: %s' % e)
            common.addon.show_small_popup(title='[B][COLOR white]HOSTINGCUP[/COLOR][/B]', msg='[COLOR red]%s[/COLOR]' % e, delay=5000, image=error_logo)
            return self.unresolvable(code=0, msg=e)


    def get_url(self, host, media_id):
        return 'http://vidpe.com/%s' % media_id
        
        
    def get_host_and_id(self, url):
        r = re.search('//(.+?)/([0-9A-Za-z]+)', url)
        if r:
            return r.groups()
        else:
            return False

    def valid_url(self, url, host):
        if self.get_setting('enabled') == 'false': return False
        return re.match(self.pattern, url) or 'hostingcup' in host
