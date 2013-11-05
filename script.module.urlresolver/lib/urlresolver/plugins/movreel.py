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

import re, os, xbmcgui, xbmcaddon, cookielib
from t0mm0.common.net import Net
from urlresolver.plugnplay.interfaces import UrlResolver
from urlresolver.plugnplay.interfaces import PluginSettings
from urlresolver.plugnplay.interfaces import SiteAuth
from urlresolver.plugnplay import Plugin
from urlresolver import common

net = Net()

class movreelResolver(Plugin, UrlResolver, SiteAuth, PluginSettings):
    implements = [UrlResolver, SiteAuth, PluginSettings]
    name = "movreel"
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
        

    def login(self):
        if self.get_setting('login') == 'true':
            loginurl = 'http://movreel.com/login.html'
            login = self.get_setting('username')
            password = self.get_setting('password')
            data = {'op': 'login', 'login': login, 'password': password}
            html = net.http_POST(loginurl, data).content
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
        

    def get_media_url(self, host, media_id):
               
        try:
            url = self.get_url(host, media_id)
            html = self.net.http_GET(url).content
            dialog = xbmcgui.DialogProgress()
            dialog.create('Resolving', 'Resolving Movreel Link...')
            dialog.update(0)
        
            html = net.http_GET(url).content
        
            dialog.update(33)
        
            if re.search('This server is in maintenance mode', html):
                raise Exception('File is currently unavailable on the host')
            
            data = {}
            r = re.findall(r'type="hidden" name="(.+?)"\s* value="?(.+?)">', html)
            method_free = re.search('<input type="(submit|hidden)" name="method_free" (style=".*?" )*value="(.*?)">', html).group(3)
            method_premium = re.search('<input type="(hidden|submit)" name="method_premium" (style=".*?" )*value="(.*?)">', html).group(3)
            
            if method_free:
                for name, value in r:
                    data[name] = value
                    data.update({'method_free':method_free})
            else:
                for name, value in r:
                    data[name] = value
                    data.update({'method_premium':method_premium})
        
            html = net.http_POST(url, data).content

            if method_free:
                if re.search('<p class="err">.+?</p>', html):
                    errortxt = re.search('<p class="err">(.+?)</p>', html).group(1)
                    raise Exception(errortxt)

                data = {}
                r = re.findall(r'type="hidden" name="(.+?)"\s* value="?(.+?)">', html)
                for name, value in r:
                    data[name] = value
                    data.update({'down_direct':1})
    
                html = net.http_POST(url, data).content

            dialog.update(100)
            link = re.search('<a href="(.+)">Download Link</a>', html).group(1)
            
            dialog.close()
            mediurl = link
        
            return mediurl

        except Exception, e:
            common.addon.log('**** Movreel Error occured: %s' % e)
            common.addon.show_small_popup('Error', str(e), 5000, '')
            return self.unresolvable(code=0, msg='Exception: %s' % e)
        

    def get_url(self, host, media_id):
        return 'http://www.movreel.com/%s' % media_id
    

    def get_host_and_id(self, url):
        r = re.search('//(.+?)/([0-9a-zA-Z]+)',url)
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
    
    def get_settings_xml(self):
        xml = PluginSettings.get_settings_xml(self)
        xml += '<setting id="movreelResolver_login" '
        xml += 'type="bool" label="login" default="false"/>\n'
        xml += '<setting id="movreelResolver_username" enable="eq(-1,true)" '
        xml += 'type="text" label="username" default=""/>\n'
        xml += '<setting id="movreelResolver_password" enable="eq(-2,true)" '
        xml += 'type="text" label="password" option="hidden" default=""/>\n'
        return xml
