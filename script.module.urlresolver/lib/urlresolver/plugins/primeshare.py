"""
primeshare urlresolver plugin
Copyright (C) 2013 Lynx187

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
"""

from t0mm0.common.net import Net
from urlresolver.plugnplay.interfaces import UrlResolver
from urlresolver.plugnplay.interfaces import PluginSettings
from urlresolver.plugnplay import Plugin
import urllib2
from urlresolver import common
from lib import jsunpack
import re
import os

error_logo = os.path.join(common.addon_path, 'resources', 'images', 'redx.png')

class PrimeshareResolver(Plugin, UrlResolver, PluginSettings):
    implements = [UrlResolver, PluginSettings]
    name = "primeshare"
    profile_path = common.profile_path
    cookie_file = os.path.join(profile_path, 'primeshare.cookies')

    def __init__(self):
        p = self.get_setting('priority') or 100
        self.priority = int(p)
        self.net = Net()
       

    def get_media_url(self, host, media_id):
        web_url = self.get_url(host, media_id)
        try:          
            html = self.net.http_GET(web_url).content
            if re.search('>File not exist<',html):
                msg = 'File Not Found or removed'
                common.addon.show_small_popup(title='[B][COLOR white]PRIMESHARE[/COLOR][/B]', msg='[COLOR red]%s[/COLOR]' 
                % msg, delay=5000, image=error_logo)
                return self.unresolvable(code = 1, msg = msg)          
            self.net.save_cookies(self.cookie_file)
            headers = {'Referer':web_url}
            # wait required
            common.addon.show_countdown(8)
            self.net.set_cookies(self.cookie_file)
            html = self.net.http_POST(web_url, form_data={'hash':media_id}, headers = headers).content
            r = re.compile("clip:.*?url: '([^']+)'",re.DOTALL).findall(html)
            if not r:
                raise Exception ('Unable to resolve Primeshare link. Filelink not found.')
            return r[0]
        
        except urllib2.URLError, e:
            common.addon.log_error(self.name + ': got http error %d fetching %s' %
                                    (e.code, web_url))
            common.addon.show_small_popup('Error','Http error: '+str(e), 8000, error_logo)
            return self.unresolvable(code=3, msg='Exception: %s' % e) 
        except Exception, e:
            common.addon.log('**** Primeshare Error occured: %s' % e)
            common.addon.show_small_popup(title='[B][COLOR white]PRIMESHARE[/COLOR][/B]', msg='[COLOR red]%s[/COLOR]' % e, delay=5000, image=error_logo)
            return self.unresolvable(code=0, msg='Exception: %s' % e)

    def get_url(self, host, media_id):
            return 'http://primeshare.tv/download/%s' % (media_id)

    def get_host_and_id(self, url):
        r = re.search('http://(?:www.)(.+?)/download/([0-9A-Za-z]+)', url)
        if r:
            return r.groups()       
        else:
            r = re.search('//(.+?)/download/([0-9A-Za-z]+)', url)
            if r:
                return r.groups()
            else:
                return False
            


    def valid_url(self, url, host):
        return re.match('http://(www.)?primeshare.tv/download/[0-9A-Za-z]+', url) or 'primeshare' in host


