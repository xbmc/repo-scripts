#-*- coding: utf-8 -*-
"""
    Purevid urlresolver XBMC Addon
    Copyright (C) 2011 t0mm0, belese, JUL1EN094

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

import os
import re
import urllib
import json
from t0mm0.common.net import Net
from urlresolver.plugnplay.interfaces import UrlResolver
from urlresolver.plugnplay.interfaces import SiteAuth
from urlresolver.plugnplay.interfaces import PluginSettings
from urlresolver.plugnplay import Plugin
from urlresolver import common

class PurevidResolver(Plugin, UrlResolver, SiteAuth, PluginSettings):
    implements = [UrlResolver, SiteAuth, PluginSettings]
    name = "purevid"
    domains = ["purevid.com"]
    profile_path = common.profile_path
    pv_cookie_file = os.path.join(profile_path, '%s.cookies' % name)
    
    def __init__(self):
        p = self.get_setting('priority') or 1
        self.priority = int(p)
        self.net = Net()
        try:
            os.makedirs(os.path.dirname(self.pv_cookie_file))
        except OSError:
            pass

    #UrlResolver methods
    def get_media_url(self, host, media_id):
        web_url = self.get_url(host, media_id)
        html = self.net.http_GET(web_url).content
        data = json.loads(html)
        if self.get_setting('quality') == 'FLV':
            url = data['clip']['bitrates'][0]['url']
        else:
            url = data['clip']['bitrates'][-1]['url']
        params = ''
        for val in data['plugins']['lighttpd']['params']:
            params += val['name'] + '=' + val['value'] + '&'
        url = url + '?' + params[:-1]
        cookies = {}
        for cookie in self.net._cj:
            cookies[cookie.name] = cookie.value
        url = url + '|' + urllib.urlencode({'Cookie': urllib.urlencode(cookies)})
        common.addon.log_debug(url)
        return url
                                                                                            
    def get_url(self, host, media_id):
        return 'http://www.purevid.com/?m=video_info_embed_flv&id=%s' % media_id
                        
    def get_host_and_id(self, url):     
        r = re.search('//(.+?)/v/([0-9A-Za-z]+)', url)
        if r:
            return r.groups()
        else:
            return False

    def valid_url(self, url, host):                 
        if self.get_setting('login') == 'false':        
            return False
        common.addon.log(url)
        return 'purevid' in url

    #SiteAuth methods
    def needLogin(self):
        url = 'http://www.purevid.com/?m=main'
        if not os.path.exists(self.pv_cookie_file):
            return True
        self.net.set_cookies(self.pv_cookie_file)
        source = self.net.http_GET(url).content
        common.addon.log_debug(source.encode('utf-8'))
        if re.search("""<span>Welcome <strong>.*</strong></span>""", source) :
            common.addon.log_debug('needLogin returning False')
            return False
        else :
            common.addon.log_debug('needLogin returning True')
            return True
    
    def login(self):
        if self.needLogin() :
            common.addon.log('login to purevid')
            url = 'http://www.purevid.com/?m=login'
            data = {'username' : self.get_setting('username'), 'password' : self.get_setting('password')}        
            source = self.net.http_POST(url,data).content        
            if re.search(self.get_setting('username'), source):            
                self.net.save_cookies(self.pv_cookie_file)
                self.net.set_cookies(self.pv_cookie_file)
                return True
            else:
                return False
        else :
            return True
                    
    #PluginSettings methods
    def get_settings_xml(self):
        xml = PluginSettings.get_settings_xml(self)
        xml += '<setting id="PurevidResolver_login" '        
        xml += 'type="bool" label="Login" default="false"/>\n'
        xml += '<setting id="PurevidResolver_username" enable="eq(-1,true)" '
        xml += 'type="text" label="     username" default=""/>\n'
        xml += '<setting id="PurevidResolver_password" enable="eq(-2,true)" '
        xml += 'type="text" label="     password" option="hidden" default=""/>\n'
        xml += '<setting label="Video quality" id="PurevidResolver_quality" '
        xml += 'type="labelenum" values="FLV|Maximum" default="Maximum" />\n'
        xml += '<setting label="This plugin calls the Purevid urlresolver - '
        xml += 'change settings there." type="lsep" />\n'
        return xml
