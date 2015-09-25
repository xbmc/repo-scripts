"""
urlresolver XBMC Addon
Copyright (C) 2011 t0mm0

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

import re, os, urllib
from urlresolver.plugnplay.interfaces import UrlResolver
from urlresolver.plugnplay.interfaces import SiteAuth
from urlresolver.plugnplay.interfaces import PluginSettings
from urlresolver.plugnplay import Plugin
from urlresolver import common
from t0mm0.common.net import Net

class VeeHDResolver(Plugin, UrlResolver, SiteAuth, PluginSettings):
    implements = [UrlResolver, SiteAuth, PluginSettings]
    name = "VeeHD"
    domains = ["veehd.com"]
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

    #UrlResolver methods
    def get_media_url(self, host, media_id):
        if not self.get_setting('login') == 'true' or not (self.get_setting('username') and self.get_setting('password')):
            raise UrlResolver.ResolverError('VeeHD requires a username & password')

        web_url = self.get_url(host, media_id)
        html = self.net.http_GET(web_url).content

        # two possible playeriframe's: stream and download
        for match in re.finditer('playeriframe.+?src\s*:\s*"([^"]+)', html):
            player_url = 'http://%s%s' % (host, match.group(1))
            html = self.net.http_GET(player_url).content
            
            # if the player html contains an iframe the iframe url has to be gotten and then the player_url tried again
            r = re.search('<iframe.*?src="([^"]+)', html)
            if r:
                frame_url = 'http://%s%s' % (host, r.group(1))
                self.net.http_GET(frame_url)
                html = self.net.http_GET(player_url).content

            patterns = ['"video/divx"\s+src="([^"]+)', '"url"\s*:\s*"([^"]+)', 'href="([^"]+(?:mp4|avi))']
            for pattern in patterns:
                r = re.search(pattern, html)
                if r:
                    stream_url = urllib.unquote(r.group(1))
                    return stream_url

        raise UrlResolver.ResolverError('File Not Found or Removed')
        
    def get_url(self, host, media_id):
        return 'http://veehd.com/video/%s' % media_id
        
    def get_host_and_id(self, url):
        r = re.search('//(.+?)/video/([0-9A-Za-z]+)', url)
        if r:
            return r.groups()
        else:
            return False

    def valid_url(self, url, host):
        if self.get_setting('enabled') == 'false': return False
        return (re.match('http://(www.)?veehd.com/' +
                         '[0-9A-Za-z]+', url) or
                         'veehd' in host)
       
    #SiteAuth methods
    def login(self):
        loginurl = 'http://veehd.com/login'
        ref = 'http://veehd.com/'
        submit = 'Login'
        login = self.get_setting('username')
        pword = self.get_setting('password')
        terms = 'on'
        remember = 'on'
        data = {'ref': ref, 'uname': login, 'pword': pword, 'submit': submit, 'terms': terms, 'remember_me': remember}
        html = self.net.http_POST(loginurl, data).content
        self.net.save_cookies(self.cookie_file)
        if re.search('my dashboard', html):
            return True
        else:
            return False
        
    #PluginSettings methods
    def get_settings_xml(self):
        xml = PluginSettings.get_settings_xml(self)
        xml += '<setting id="%s_login" ' % (self.__class__.__name__)
        xml += 'type="bool" label="login" default="false"/>\n'
        xml += '<setting id="%s_username" enable="eq(-1,true)" ' % (self.__class__.__name__)
        xml += 'type="text" label="username" default=""/>\n'
        xml += '<setting id="%s_password" enable="eq(-2,true)" ' % (self.__class__.__name__)
        xml += 'type="text" label="password" option="hidden" default=""/>\n'
        return xml
        
    #to indicate if this is a universal resolver
    def isUniversal(self):
        return False
