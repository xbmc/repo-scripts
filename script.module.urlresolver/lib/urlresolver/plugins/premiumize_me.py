"""
    urlresolver XBMC Addon
    Copyright (C) 2013 Bstrdsmkr

    This program is free software: you can redistribute it and/or modify
    it under the terms of the GNU General Public License as published by
    the Free Software Foundation, either version 3 of the License, or
    (at your option) any later version.

    This program is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU General Public License for more details.

    You should have received a copy of the GNU General Public License
    along with this program.  If not, see <http://www.gnu.org/licenses/>.
"""

import os, sys
import re

from urlresolver.plugnplay.interfaces import UrlResolver
from urlresolver.plugnplay.interfaces import SiteAuth
from urlresolver.plugnplay.interfaces import PluginSettings
from urlresolver.plugnplay import Plugin
from urlresolver import common
from t0mm0.common.net import Net

try:
    import simplejson as json
except ImportError:
    import json

class PremiumizeMeResolver(Plugin, UrlResolver, SiteAuth, PluginSettings):
    implements = [UrlResolver, PluginSettings]
    name = "Premiumize.me"
    media_url = None

    def __init__(self):
        p = self.get_setting('priority') or 100
        self.priority = int(p)
        self.net = Net()
        self.patterns = None

    #UrlResolver methods
    def get_media_url(self, host, media_id):
        try:
            username = self.get_setting('username')
            password = self.get_setting('password')
            url   = 'https://api.premiumize.me/pm-api/v1.php?'
            url += 'method=directdownloadlink&params%%5Blogin%%5D=%s'
            url += '&params%%5Bpass%%5D=%s&params%%5Blink%%5D=%s'
            url   = url % (username, password, media_id)
            response = self.net.http_GET(url).content
            response = json.loads(response)
            link = response['result']['location']
        except Exception, e:
            common.addon.log_error('**** Premiumize Error occured: %s' % e)
            common.addon.show_small_popup(title='[B][COLOR white]PREMIUMIZE[/COLOR][/B]', msg='[COLOR red]%s[/COLOR]' % e, delay=5000, image=error_logo)
            return self.unresolvable(code=0, msg=e)
        
        common.addon.log('Premiumize.me: Resolved to %s' %link)
        return link

    def get_url(self, host, media_id):
        return media_id

    def get_host_and_id(self, url):
        return 'Premiumize.me', url

    def get_all_hosters(self):
        try :
            if self.patterns is None:
                username = self.get_setting('username')
                password = self.get_setting('password')
                url = 'https://api.premiumize.me/pm-api/v1.php?method=hosterlist'
                url += '&params%%5Blogin%%5D=%s&params%%5Bpass%%5D=%s'
                url = url % (username, password)
                response = self.net.http_GET(url).content
                response = json.loads(response)
                result = response['result']
                log_msg = 'Premiumize.me patterns: %s' % result['regexlist']
                common.addon.log_debug(log_msg)
                self.patterns = [re.compile(regex) for regex in result['regexlist']]
            return self.patterns
        except :
            return [] 

    def valid_url(self, url, host):
        if self.get_setting('enabled') == 'false':
            return False
        if self.get_setting('login') == 'false': return False 
        for pattern in self.get_all_hosters():
            if pattern.findall(url):
                return True
        return False

    #PluginSettings methods
    def get_settings_xml(self):
        xml = PluginSettings.get_settings_xml(self)
        xml += '<setting id="PremiumizeMeResolver_login" '
        xml += 'type="bool" label="login" default="false"/>\n'        
        xml += '<setting id="PremiumizeMeResolver_username" enable="eq(-1,true)" '
        xml += 'type="text" label="username" default=""/>\n'
        xml += '<setting id="PremiumizeMeResolver_password" enable="eq(-2,true)" '
        xml += 'type="text" label="password" option="hidden" default=""/>\n'
        return xml
        
    #to indicate if this is a universal resolver
    def isUniversal(self):
        return True
