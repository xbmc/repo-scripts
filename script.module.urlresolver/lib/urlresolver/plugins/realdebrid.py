"""
urlresolver XBMC Addon
Copyright (C) 2013 t0mm0, JUL1EN094, bstrdsmkr

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

import os
import re
import urllib
import xbmcgui
from urlresolver.plugnplay.interfaces import UrlResolver
from urlresolver.plugnplay.interfaces import SiteAuth
from urlresolver.plugnplay.interfaces import PluginSettings
from urlresolver.plugnplay import Plugin
from urlresolver import common
from t0mm0.common.net import Net
import simplejson as json

# SET ERROR_LOGO# THANKS TO VOINAGE, BSTRDMKR, ELDORADO
error_logo = os.path.join(common.addon_path, 'resources', 'images', 'redx.png')

class RealDebridResolver(Plugin, UrlResolver, SiteAuth, PluginSettings):
    implements = [UrlResolver, SiteAuth, PluginSettings]
    name = "realdebrid"
    domains = ["*"]
    profile_path = common.profile_path
    cookie_file = os.path.join(profile_path, '%s.cookies' % name)
    media_url = None

    def __init__(self):
        p = self.get_setting('priority') or 1
        self.priority = int(p)
        self.net = Net()
        self.hosters = None
        self.hosts = None
        try:
            os.makedirs(os.path.dirname(self.cookie_file))
        except OSError:
            pass

    # UrlResolver methods
    def get_media_url(self, host, media_id):
        dialog = xbmcgui.Dialog()
        url = 'https://real-debrid.com/ajax/unrestrict.php?link=%s' % media_id.replace('|User-Agent=Mozilla%2F5.0%20(Windows%20NT%206.1%3B%20rv%3A11.0)%20Gecko%2F20100101%20Firefox%2F11.0', '')
        source = self.net.http_GET(url).content
        jsonresult = json.loads(source)
        if 'generated_links' in jsonresult:
            generated_links = jsonresult['generated_links']
            if len(generated_links) == 1:
                return generated_links[0][2].encode('utf-8')
            line = []
            for link in generated_links:
                extension = link[0].split('.')[-1]
                line.append(extension.encode('utf-8'))
            result = dialog.select('Choose the link', line)
            if result != -1:
                link = generated_links[result][2]
                return link.encode('utf-8')
            else:
                raise UrlResolver.ResolverError('No generated_link')
        elif 'main_link' in jsonresult:
            return jsonresult['main_link'].encode('utf-8')
        else:
            if 'message' in jsonresult:
                raise UrlResolver.ResolverError(jsonresult['message'].encode('utf-8'))
            else:
                raise UrlResolver.ResolverError('No generated_link and no main_link')

    def get_url(self, host, media_id):
        return media_id

    def get_host_and_id(self, url):
        return 'www.real-debrid.com', url

    def get_all_hosters(self):
        if self.hosters is None:
            try:
                url = 'http://www.real-debrid.com/api/regex.php?type=all'
                response = self.net.http_GET(url).content.lstrip('/').rstrip('/g')
                delim = '/g,/|/g\|-\|/'
                self.hosters = [re.compile(host) for host in re.split(delim, response)]
            except:
                self.hosters = []
        common.addon.log_debug('RealDebrid hosters : %s' % self.hosters)
        return self.hosters

    def get_hosts(self):
        if self.hosts is None:
            try:
                url = 'https://real-debrid.com/api/hosters.php'
                response = self.net.http_GET(url).content
                response = response[1:-1]
                self.hosts = response.split('","')
            except:
                self.hosts = []
        common.addon.log_debug('RealDebrid hosts : %s' % self.hosts)

    def valid_url(self, url, host):
        if self.get_setting('enabled') == 'false': return False
        if self.get_setting('login') == 'false': return False
        common.addon.log_debug('in valid_url %s : %s' % (url, host))
        if url:
            self.get_all_hosters()
            for host in self.hosters:
                # common.addon.log_debug('RealDebrid checking host : %s' %str(host))
                if re.search(host, url):
                    common.addon.log_debug('RealDebrid Match found')
                    return True
        elif host:
            self.get_hosts()
            if host in self.hosts or any(item in host for item in self.hosts):
                return True
        return False

    def checkLogin(self):
        url = 'https://real-debrid.com/api/account.php'
        if not os.path.exists(self.cookie_file):
            return True
        self.net.set_cookies(self.cookie_file)
        source = self.net.http_GET(url).content
        common.addon.log_debug(source)
        if re.search('expiration', source):
            common.addon.log_debug('checkLogin returning False')
            return False
        else:
            common.addon.log_debug('checkLogin returning True')
            return True

    # SiteAuth methods
    def login(self):
        if self.checkLogin():
            try:
                common.addon.log_debug('Need to login since session is invalid')
                import hashlib
                login_data = urllib.urlencode({'user': self.get_setting('username'), 'pass': hashlib.md5(self.get_setting('password')).hexdigest()})
                url = 'https://real-debrid.com/ajax/login.php?' + login_data
                source = self.net.http_GET(url).content
                if re.search('OK', source):
                    self.net.save_cookies(self.cookie_file)
                    self.net.set_cookies(self.cookie_file)
                    return True
            except:
                    common.addon.log_debug('error with http_GET')
                    dialog = xbmcgui.Dialog()
                    dialog.ok(' Real-Debrid ', ' Unexpected error, Please try again.', '', '')
            else:
                return False
        else:
            return True

    # PluginSettings methods
    def get_settings_xml(self):
        xml = PluginSettings.get_settings_xml(self)
        xml += '<setting id="%s_login" ' % (self.__class__.__name__)
        xml += 'type="bool" label="login" default="false"/>\n'
        xml += '<setting id="%s_username" enable="eq(-1,true)" ' % (self.__class__.__name__)
        xml += 'type="text" label="username" default=""/>\n'
        xml += '<setting id="%s_password" enable="eq(-2,true)" ' % (self.__class__.__name__)
        xml += 'type="text" label="password" option="hidden" default=""/>\n'
        return xml

    # to indicate if this is a universal resolver
    def isUniversal(self):
        return True
