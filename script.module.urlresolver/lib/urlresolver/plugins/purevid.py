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
import random
import re
import urllib, urllib2
import ast
import xbmc
import time
from urlresolver.plugnplay.interfaces import UrlResolver
from urlresolver.plugnplay.interfaces import SiteAuth
from urlresolver.plugnplay.interfaces import PluginSettings
from urlresolver.plugnplay import Plugin
from urlresolver import common
import xbmc,xbmcplugin,xbmcgui,xbmcaddon, datetime
import cookielib
from t0mm0.common.net import Net
import json

#SET ERROR_LOGO# THANKS TO VOINAGE, BSTRDMKR, ELDORADO
error_logo = os.path.join(common.addon_path, 'resources', 'images', 'redx.png')

class purevid(Plugin, UrlResolver, SiteAuth, PluginSettings):
    implements   = [UrlResolver, SiteAuth, PluginSettings]
    name         = "purevid"
    profile_path = common.profile_path    
    cookie_file  = os.path.join(profile_path, '%s.cookies' % name)
    
    def __init__(self):
        p             = self.get_setting('priority') or 1
        self.priority = int(p)
        self.net      = Net()
        try:
            os.makedirs(os.path.dirname(self.cookie_file))
        except OSError:
            pass

    #UrlResolver methods
    def get_media_url(self, host, media_id):
        try :
            web_url = self.get_url(host, media_id)
            try:
                html = self.net.http_GET(web_url).content
            except urllib2.URLError, e:
                raise Exception ('got http error %d fetching %s' % (e.code, web_url))
            data = json.loads(html)                
            if self.get_setting('quality') == '0' :
                url = data['clip']['bitrates'][0]['url']
            else :
                url = data['clip']['bitrates'][-1]['url']
            params = ''
            for val in data['plugins']['lighttpd']['params'] :
                params += val['name'] + '=' + val['value'] + '&'
            url =  url + '?' + params[:-1]
            cookies = {}
            for cookie in self.net._cj:
                cookies[cookie.name] = cookie.value
            url = url + '|' + urllib.urlencode({'Cookie' :urllib.urlencode(cookies)}) 
            common.addon.log(url)
            return url
        except Exception, e:
            common.addon.log('**** Purevid Error occured: %s' % e)
            common.addon.show_small_popup(title='[B][COLOR white]PUREVID[/COLOR][/B]', msg='[COLOR red]%s[/COLOR]' % e, delay=5000, image=error_logo)
            return self.unresolvable(code=0, msg=e)
                                                                                            
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
    def login(self):
        common.addon.log('login to purevid')
        url = 'http://www.purevid.com/?m=login'
        data = {'username' : self.get_setting('username'), 'password' : self.get_setting('password')}        
        source = self.net.http_POST(url,data).content        
        if re.search(self.get_setting('username'), source):            
            self.net.save_cookies(self.cookie_file)
            self.net.set_cookies(self.cookie_file)
            return True
        else:
            return False
                    
    #PluginSettings methods
    def get_settings_xml(self):
        xml = PluginSettings.get_settings_xml(self)
        xml += '<setting id="purevid_login" '        
        xml += 'type="bool" label="Login" default="false"/>\n'
        xml += '<setting id="purevid_username" enable="eq(-1,true)" '
        xml += 'type="text" label="     username" default=""/>\n'
        xml += '<setting id="purevid_password" enable="eq(-2,true)" '
        xml += 'type="text" label="     password" option="hidden" default=""/>\n'
        xml += '<setting label="Video quality" id="%s_quality" ' % self.__class__.__name__
        xml += 'type="enum" values="FLV|Maximum" default="0" />\n'
        xml += '<setting label="This plugin calls the Purevid urlresolver - '
        xml += 'change settings there." type="lsep" />\n'
        return xml
