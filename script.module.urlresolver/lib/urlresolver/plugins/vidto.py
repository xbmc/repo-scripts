"""    This program is free software: you can redistribute it and/or modify
    it under the terms of the GNU General Public License as published by
    the Free Software Foundation, either version 3 of the License, or
    (at your option) any later version.
    
    This program is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
    GNU General Public License for more details.
    
    You should have received a copy of the GNU General Public License
    along with this program. If not, see <http://www.gnu.org/licenses/>.
    
    Special thanks for help with this resolver go out to t0mm0, jas0npc,
    mash2k3, Mikey1234,voinage and of course Eldorado. Cheers guys :)
"""

import re
from t0mm0.common.net import Net
from urlresolver.plugnplay.interfaces import UrlResolver
from urlresolver.plugnplay.interfaces import PluginSettings
from urlresolver.plugnplay import Plugin
from urlresolver import common
net = Net()


class vidto(Plugin, UrlResolver, PluginSettings):
    implements = [UrlResolver, PluginSettings]
    name = "vidto"

    def __init__(self):
        p = self.get_setting('priority') or 100
        self.priority = int(p)
        self.net = Net()

    def get_media_url(self, host, media_id):
        try:
            url = self.get_url(host, media_id)
            html = self.net.http_GET(url).content
            common.addon.show_countdown(6, title='Vidto', text='Loading Video...')

            data = {}
            r = re.findall(r'type="(?:hidden|submit)?" name="(.+?)"\s* value="?(.+?)">', html)
            for name, value in r:
                data[name] = value
            html = net.http_POST(url, data).content

            r = re.search('<a id="lnk_download" href="(.+?)"', html)
            if r:
                r=re.sub(' ','%20',r.group(1))
                return r
            else:
                raise Exception('could not find video')
        except Exception, e:
            common.addon.log('**** Vidto Error occured: %s' % e)
            common.addon.show_small_popup('Error', str(e), 5000, '')
            return self.unresolvable(code=0, msg='Exception: %s' % e)
        

        
    def get_url(self, host, media_id):
        return 'http://vidto.me/%s' % media_id

    def get_host_and_id(self, url):
        r = re.search('//(.+?)/([0-9A-Za-z]+)',url)
        if r:
            return r.groups()
        else:
            return False
        

    def valid_url(self, url, host):
        if self.get_setting('enabled') == 'false': return False
        return (re.match('http://(www.)?vidto.me/' +
                        '[0-9A-Za-z]+', url) or 'vidto.me' in host)
