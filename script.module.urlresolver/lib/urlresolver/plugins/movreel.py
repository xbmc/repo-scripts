"""
urlresolver XBMC Addon
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

Special thanks for help with this resolver go out to t0mm0, jas0npc,
mash2k3, Mikey1234,voinage and of course Eldorado. Cheers guys :)
"""

import re
import os
import xbmc
from t0mm0.common.net import Net
from urlresolver.plugnplay.interfaces import UrlResolver
from urlresolver.plugnplay.interfaces import PluginSettings
from urlresolver.plugnplay import Plugin
from urlresolver.plugnplay.interfaces import SiteAuth
from urlresolver import common

class MovreelResolver(Plugin, UrlResolver, SiteAuth, PluginSettings):
    implements = [UrlResolver, SiteAuth, PluginSettings]
    name = "movreel"
    domains = ["movreel.com"]
    profile_path = common.profile_path
    cookie_file = os.path.join(profile_path, '%s.cookies' % name)

    def __init__(self):
        p = self.get_setting('priority') or 1
        self.priority = int(p)
        self.net = Net()
        try:
            os.makedirs(os.path.dirname(self.cookie_file))
        except OSError:
            pass
                
    def get_media_url(self, host, media_id):
        self.net.set_cookies(self.cookie_file)
        web_url = self.get_url(host, media_id)
        html = self.net.http_GET(web_url).content
        if re.search('This server is in maintenance mode', html):
            raise UrlResolver.ResolverError('File is currently unavailable on the host')
        
        data = {}
        r = re.findall(r'type="hidden" name="(.+?)" value="(.+?)"', html)
        if r:
            for name, value in r:
                data[name] = value
            data['referer'] = web_url
        else:
            raise UrlResolver.ResolverError('Cannot find data values')
        data['btn_download'] = 'Continue to Video'
        
        r = re.search('<span id="countdown_str">Wait <span id=".+?">(.+?)</span> seconds</span>', html)
        if r:
            wait_time = r.group(1)
        else:
            wait_time = 2  # default to 2 seconds
        xbmc.sleep(int(wait_time) * 1000)

        html = self.net.http_POST(web_url, data).content
        
        r = re.search('href="([^"]+)">Download Link', html)
        if r:
            return r.group(1)
        else:
            raise UrlResolver.ResolverError('Unable to locate Download Link')

    def get_url(self, host, media_id):
        return 'http://www.movreel.com/%s' % media_id

    def get_host_and_id(self, url):
        r = re.search('//(.+?)/([0-9a-zA-Z]+)', url)
        if r:
            return r.groups()
        else:
            return False
        return('host', 'media_id')

    def valid_url(self, url, host):
        if self.get_setting('enabled') == 'false': return False
        return (re.match('http://(www.)?movreel.com/' +
                         '[0-9A-Za-z]+', url) or
                         'movreel' in host)

    def login(self):
        if self.get_setting('login') == 'true':
            loginurl = 'http://movreel.com'
            login = self.get_setting('username')
            password = self.get_setting('password')
            data = {'op': 'login', 'login': login, 'password': password}
            html = self.net.http_POST(loginurl, data).content
            if re.search('op=logout', html):
                self.net.save_cookies(self.cookie_file)
                common.addon.log('LOGIN SUCCESSFUL')
                return True
            else:
                common.addon.log('LOGIN FAILED')
                return False
        else:
            common.addon.log('No account info entered')
            return False

    def get_settings_xml(self):
        xml = PluginSettings.get_settings_xml(self)
        xml += '<setting id="%s_login" ' % (self.__class__.__name__)
        xml += 'type="bool" label="login" default="false"/>\n'
        xml += '<setting id="%s_username" enable="eq(-1,true)" ' % (self.__class__.__name__)
        xml += 'type="text" label="username" default=""/>\n'
        xml += '<setting id="%s_password" enable="eq(-2,true)" ' % (self.__class__.__name__)
        xml += 'type="text" label="password" option="hidden" default=""/>\n'
        return xml
