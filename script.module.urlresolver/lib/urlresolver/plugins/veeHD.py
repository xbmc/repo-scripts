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

import os
import random
import re
import urllib, urllib2
import xbmc
from urlresolver.plugnplay.interfaces import UrlResolver
from urlresolver.plugnplay.interfaces import SiteAuth
from urlresolver.plugnplay.interfaces import PluginSettings
from urlresolver.plugnplay import Plugin
from urlresolver import common
import xbmc,xbmcplugin,xbmcgui,xbmcaddon, datetime
import cookielib
from t0mm0.common.net import Net

net = Net()
addon_id = 'plugin.video.dailyflix'
selfAddon = xbmcaddon.Addon(id=addon_id)

class veeHDResolver(Plugin, UrlResolver, SiteAuth, PluginSettings):
    implements = [UrlResolver, SiteAuth, PluginSettings]
    name = "veeHD"
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
        web_url = self.get_url(host, media_id)
        try:
            html = self.net.http_GET(web_url).content
        except urllib2.URLError, e:
            common.addon.log_error(self.name + '- got http error %d fetching %s' %
                                   (e.code, web_url))
            return False

        fragment = re.search('playeriframe".+?attr.+?src : "(.+?)"', html)
        frag = 'http://%s%s'%(host,fragment.group(1))
        xbmc.log(frag)
        try:
            html = self.net.http_GET(frag).content
        except urllib2.URLError, e:
            common.addon.log_error(self.name + '- got http error %d fetching %s' %
                                   (e.code, web_url))
            return False
        r = re.search('"video/divx" src="(.+?)"', html)
        if r:
            stream_url = r.group(1)
        else:
            message = self.name + '- 1st attempt at finding the stream_url failed probably an Mp4, finding Mp4'
            common.addon.log_debug(message)
            a = re.search('"url":"(.+?)"', html)
            r=urllib.unquote(a.group(1))
            if r:
                stream_url = r
            else:
                message = self.name + '- Giving up on finding the stream_url'
                common.addon.log_error(message)
                return False
        return stream_url
    
        
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
        submit = 'login'
        login = selfAddon.getSetting('veeHDResolver_username')
        pword = selfAddon.getSetting('veeHDResolver_password')
        terms = 'on'
        remember = 'on'
        data = {'ref': ref, 'uname': login, 'pword': pword, 'submit': submit, 'terms': terms, 'remember_me': remember}
        html = net.http_POST(loginurl, data).content
        self.net.save_cookies(self.cookie_file)
        if re.search('my dashboard', html):
            return True
        else:
            return False
        
        
    #PluginSettings methods
    def get_settings_xml(self):
        xml = PluginSettings.get_settings_xml(self)
        xml += '<setting id="veeHDResolver_login" '
        xml += 'type="bool" label="login" default="false"/>\n'
        xml += '<setting id="veeHDResolver_username" enable="eq(-1,true)" '
        xml += 'type="text" label="username" default=""/>\n'
        xml += '<setting id="veeHDResolver_password" enable="eq(-2,true)" '
        xml += 'type="text" label="password" option="hidden" default=""/>\n'
        return xml
        
    #to indicate if this is a universal resolver
    def isUniversal(self):
        
        return True
