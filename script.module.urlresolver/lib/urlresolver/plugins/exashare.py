"""
Exashare.com urlresolver XBMC Addon
Copyright (C) 2014 JUL1EN094 

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

import urllib,urllib2,os,re,xbmc
from t0mm0.common.net import Net
from urlresolver.plugnplay.interfaces import UrlResolver
from urlresolver.plugnplay.interfaces import SiteAuth
from urlresolver.plugnplay.interfaces import PluginSettings
from urlresolver.plugnplay import Plugin
from urlresolver import common

class ExashareResolver(Plugin,UrlResolver,PluginSettings):
    implements   = [UrlResolver,SiteAuth,PluginSettings]
    name         = "exashare"
    domains      = [ "exashare.com" ]
    profile_path = common.profile_path    
    cookie_file  = os.path.join(profile_path,'%s.cookies'%name)
    
    def __init__(self):
        p=self.get_setting('priority') or 100
        self.priority=int(p)
        self.net=Net()
        
    #UrlResolver methods
    def get_media_url(self, host, media_id):
        base_url = 'http://www.' + host + '.com/' + media_id
        headers = {'User-Agent': common.IE_USER_AGENT, 'Referer': 'http://www.' + host + '.com/'}
        try: html = self.net.http_GET(base_url).content
        except: html = self.net.http_GET(base_url, headers=headers).content
        if re.search("""File Not Found""", html):
            raise UrlResolver.ResolverError('File not found or removed')
        POST_Url               = re.findall('form method="POST" action=\'(.*)\'',html)[0]
        POST_Selected          = re.findall('form method="POST" action=(.*)</Form>',html,re.DOTALL)[0]
        POST_Data              = {}
        POST_Data['op']        = re.findall('input type="hidden" name="op" value="(.*)"',POST_Selected)[0]
        POST_Data['usr_login'] = re.findall('input type="hidden" name="usr_login" value="(.*)"',POST_Selected)[0]
        POST_Data['id']        = re.findall('input type="hidden" name="id" value="(.*)"',POST_Selected)[0]
        POST_Data['fname']     = re.findall('input type="hidden" name="fname" value="(.*)"',POST_Selected)[0]
        POST_Data['referer']   = re.findall('input type="hidden" name="referer" value="(.*)"',POST_Selected)[0]
        POST_Data['hash']      = re.findall('input type="hidden" name="hash" value="(.*)"',POST_Selected)[0]
        POST_Data['imhuman']   = 'Proceed to video'
        try : html2 = self.net.http_POST(POST_Url,POST_Data).content
        except : html2 = self.net.http_POST(POST_Url,POST_Data,headers=headers).content
        stream_url = re.findall('file:\s*"([^"]+)"', html2)[0]
        if self.get_setting('login') == 'true':
            cookies = {}
            for cookie in self.net._cj:
                cookies[cookie.name] = cookie.value
            if len(cookies) > 0:
                stream_url = stream_url + '|' + urllib.urlencode({'Cookie': urllib.urlencode(cookies)})
        common.addon.log('stream_url : ' + stream_url)
        xbmc.sleep(7000)
        return stream_url

    def get_url(self,host,media_id):
        return 'http://www.exashare.com/%s' % media_id

    def get_host_and_id(self,url):
        r=re.search('http://(?:www.)?(.+?).com/(?:embed\-)?([0-9A-Za-z_]+)(?:\-[0-9]+x[0-9]+.html)?',url)
        if r:
            ls=r.groups()
            return ls
        else:
            return False

    def valid_url(self, url, host):
        if self.get_setting('enabled')=='false' or self.get_setting('login')=='false': 
            return False
        return re.match('http://(?:www.)?exashare.com/(?:embed\-)?[0-9A-Za-z]+(?:\-[0-9]+x[0-9]+.html)?',url) or 'exashare.com' in host

    #SiteAuth methods
    def needLogin(self):
        url='http://www.exashare.com/?op=my_account'
        if not os.path.exists(self.cookie_file):
            common.addon.log_debug('needLogin returning True')
            return True
        self.net.set_cookies(self.cookie_file)
        source=self.net.http_GET(url).content
        if re.search("""Your username is for logging in and cannot be changed""",source):
            common.addon.log_debug('needLogin returning False')
            return False
        else:
            common.addon.log_debug('needLogin returning True')
            return True
    
    def login(self):
        if (self.get_setting('login')=='true'):
            if self.needLogin():
                common.addon.log('logging in exashare')
                url='http://www.exashare.com/'
                data={'login':self.get_setting('username'),'password':self.get_setting('password'),'op':'login','redirect':'/login.html'}
                headers={'User-Agent':common.IE_USER_AGENT,'Referer':url}
                try: source=self.net.http_POST(url,data).content
                except: source=self.net.http_POST(url,data,headers=headers).content
                if re.search('Your username is for logging in and cannot be changed',source):
                    common.addon.log('logged in exashare')
                    self.net.save_cookies(self.cookie_file)
                    self.net.set_cookies(self.cookie_file)
                    return True
                else:
                    common.addon.log('error logging in exashare')
                    return False
        else:
            if os.path.exists(self.cookie_file): os.remove(self.cookie_file)
            return False
                    
    #PluginSettings methods
    def get_settings_xml(self):
        xml = PluginSettings.get_settings_xml(self)
        xml += '<setting id="ExashareResolver_login" '        
        xml += 'type="bool" label="Login" default="false"/>\n'
        xml += '<setting id="ExashareResolver_username" enable="eq(-1,true)" '
        xml += 'type="text" label="     username" default=""/>\n'
        xml += '<setting id="ExashareResolver_password" enable="eq(-2,true)" '
        xml += 'type="text" label="     password" option="hidden" default=""/>\n'
        return xml
