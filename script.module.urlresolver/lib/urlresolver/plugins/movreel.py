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

import re, os, xbmcgui
from t0mm0.common.net import Net
from urlresolver.plugnplay.interfaces import UrlResolver
from urlresolver.plugnplay.interfaces import PluginSettings
from urlresolver.plugnplay.interfaces import SiteAuth
from urlresolver.plugnplay import Plugin
from urlresolver import common

net = Net()

class MovreelResolver(Plugin, UrlResolver, SiteAuth, PluginSettings):
    implements = [UrlResolver, SiteAuth, PluginSettings]
    name = "movreel"
    profile_path = common.profile_path
    cookie_file = os.path.join(profile_path, '%s.cookies' % name)
    

    def __init__(self):
        p = self.get_setting('priority') or 100
        self.priority = int(p)
        self.net = Net()
        try:
            os.makedirs(os.path.dirname(self.cookie_file))
        except OSError:
            pass
        

    def login(self):

        if self.get_setting('login') == 'true':
            loginurl = 'http://movreel.com/login.html'
            data = {'op': 'login', 'login': self.get_setting('username'), 'password': self.get_setting('password')}
            html = net.http_POST(loginurl, data).content
            if re.search('op=logout', html):
                common.addon.log('LOGIN SUCCESSFUL')
                self.net.save_cookies(self.cookie_file)
                return True
            else:
                common.addon.log('LOGIN FAILED')
                return False
        else:
            common.addon.log('No account info entered')
            return False
        

    def get_media_url(self, host, media_id):
               
        try:

            self.net.set_cookies(self.cookie_file)
            
            url = self.get_url(host, media_id)
            html = self.net.http_GET(url).content
            dialog = xbmcgui.DialogProgress()
            dialog.create('Resolving', 'Resolving Movreel Link...')
            dialog.update(0)
        
            common.addon.log('Movreel - Requesting GET URL: %s' % url)
            html = net.http_GET(url).content
        
            dialog.update(33)
        
            if re.search('This server is in maintenance mode', html):
                common.addon.log('***** Movreel - Site reported maintenance mode')
                raise Exception('File is currently unavailable on the host')

            op = re.search('<input type="hidden" name="op" value="(.+?)">', html).group(1)
            postid = re.search('<input type="hidden" name="id" value="(.+?)">', html).group(1)
            method_free = re.search('<input type="(submit|hidden)" name="method_free" (style=".*?" )*value="(.*?)">', html).group(3)
            method_premium = re.search('<input type="(hidden|submit)" name="method_premium" (style=".*?" )*value="(.*?)">', html).group(3)
            
            if method_free:
                usr_login = ''
                fname = re.search('<input type="hidden" name="fname" value="(.+?)">', html).group(1)
                data = {'op': op, 'usr_login': usr_login, 'id': postid, 'referer': url, 'fname': fname, 'method_free': method_free}
            else:
                rand = re.search('<input type="hidden" name="rand" value="(.+?)">', html).group(1)
                data = {'op': op, 'id': postid, 'referer': url, 'rand': rand, 'method_premium': method_premium}
        
            print 'Movreel - Requesting POST URL: %s DATA: %s' % (url, data)
            html = net.http_POST(url, data).content

            if method_free:
                if re.search('<p class="err">.+?</p>', html):
                    common.addon.log('***** Download limit reached')
                    errortxt = re.search('<p class="err">(.+?)</p>', html).group(1)
                    raise Exception(errortxt)
    
                dialog.update(66)
            
                op = re.search('<input type="hidden" name="op" value="(.+?)">', html).group(1)
                postid = re.search('<input type="hidden" name="id" value="(.+?)">', html).group(1)
                rand = re.search('<input type="hidden" name="rand" value="(.+?)">', html).group(1)
                method_free = re.search('<input type="hidden" name="method_free" value="(.+?)">', html).group(1)
            
                data = {'op': op, 'id': postid, 'rand': rand, 'referer': url, 'method_free': method_free, 'down_direct': 1}
    
                common.addon.log('Movreel - Requesting POST URL: %s DATA: %s' % (url, data))
                html = net.http_POST(url, data).content

            dialog.update(100)
            dialog.close()
            link = re.search('<a id="lnk_download" href="(.+?)">Download Original Video</a>', html, re.DOTALL).group(1)
            return link

        except Exception, e:
            common.addon.log_error('**** Movreel Error occured: %s' % e)
            return False


    def get_url(self, host, media_id):
        return 'http://www.movreel.com/%s' % media_id
    

    def get_host_and_id(self, url):
        r = re.search('//(.+?)/([0-9a-zA-Z]+)',url)
        if r:
            return r.groups()
        else:
            return False
    

    def valid_url(self, url, host):
        if self.get_setting('enabled') == 'false': return False
        return (re.match('http://(www.)?movreel.com/' +
                         '[0-9A-Za-z]+', url) or
                         'movreel' in host)


#Obtaining the Movreel login info from your app
    def get_settings_xml(self):
        xml = PluginSettings.get_settings_xml(self)
        xml += '<setting id="MovreelResolver_login" '
        xml += 'type="bool" label="login" default="false"/>\n'
        xml += '<setting id="MovreelResolver_username" enable="eq(-1,true)" '
        xml += 'type="text" label="username" default=""/>\n'
        xml += '<setting id="MovreelResolver_password" enable="eq(-2,true)" '
        xml += 'type="text" label="password" option="hidden" default=""/>\n'
        return xml