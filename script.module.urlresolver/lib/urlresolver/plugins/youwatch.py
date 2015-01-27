#-*- coding: utf-8 -*-

"""
Youwatch urlresolver XBMC Addon
Copyright (C) 2013 JUL1EN094 

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
import urllib, urllib2, os, re
from t0mm0.common.net import Net
from urlresolver.plugnplay.interfaces import UrlResolver
from urlresolver.plugnplay.interfaces import SiteAuth
from urlresolver.plugnplay.interfaces import PluginSettings
from urlresolver.plugnplay import Plugin
from urlresolver import common

#SET ERROR_LOGO# THANKS TO VOINAGE, BSTRDMKR, ELDORADO
error_logo = os.path.join(common.addon_path, 'resources', 'images', 'redx.png')
#SET OK_LOGO#
ok_logo = os.path.join(common.addon_path, 'resources', 'images', 'greeninch.png')

class Base36:
    
    def __init__(self,ls=False):
        self.ls = False
        if ls :
            self.ls = ls
    
    def base36encode(self,number, alphabet='0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ'):
        """Converts an integer to a base36 string."""
        if not isinstance(number, (int, long)):
            raise TypeError('number must be an integer')
        base36 = ''
        sign = ''
        if number < 0:
            sign = '-'
            number = -number
        if 0 <= number < len(alphabet):
            return sign + alphabet[number]
        while number != 0:
            number, i = divmod(number, len(alphabet))
            base36 = alphabet[i] + base36
        return sign + base36
     
    def base36decode(self,number):
        return int(number, 36)
    
    def param36decode(self,match_object) :
        if self.ls :
            param = int(match_object.group(0), 36)
            return str(self.ls[param])
        else :
            return False
    
    
class YouwatchResolver(Plugin, UrlResolver, SiteAuth, PluginSettings):
    implements = [UrlResolver, SiteAuth, PluginSettings]
    name = "youwatch"
    profile_path = common.profile_path    
    cookie_file  = os.path.join(profile_path, '%s.cookies' % name)

    def __init__(self):
        p = self.get_setting('priority') or 100
        self.priority = int(p)
        self.net = Net()
        try:
            os.makedirs(os.path.dirname(self.cookie_file))
        except OSError:
            pass
            
    def get_media_url(self, host, media_id):
        base_url = 'http://'+host+'.org/embed-'+media_id+'.html'
        try:
            soup       = self.net.http_GET(base_url).content
            html       = soup.decode('utf-8')
            jscript    = re.findall("""function\(p,a,c,k,e,d\).*return p\}(.*)\)""",html)
            if jscript :
                lsParam   = eval(jscript[0].encode('utf-8'))
                flashvars = self.exec_javascript(lsParam)
                r         = re.findall('file:"(.*)",provider',flashvars)
                if r :
                    stream_url = r[0].encode('utf-8')
                    if self.get_setting('login') == 'true' :  
                        cookies = {}
                        for cookie in self.net._cj:
                            cookies[cookie.name] = cookie.value
                        stream_url = stream_url + '|' + urllib.urlencode({'Cookie' :urllib.urlencode(cookies)}) 
                        common.addon.log('stream_URL : '+stream_url)
                else :
                    raise Exception ('File Not Found or removed')
            else :
                raise Exception ('File Not Found or removed')
            return stream_url  
        except urllib2.URLError, e:
            common.addon.log_error(self.name + ': got http error %d fetching %s' %
                                   (e.code, web_url))
            common.addon.show_small_popup('Error','Http error: '+str(e), 8000, error_logo)
            return self.unresolvable(code=3, msg=e)
        except Exception, e:
            common.addon.log('**** Youwatch Error occured: %s' % e)
            common.addon.show_small_popup(title='[B][COLOR white]YOUWATCH[/COLOR][/B]', msg='[COLOR red]%s[/COLOR]' % e, delay=5000, image=error_logo)
            return self.unresolvable(code=0, msg=e)

    def get_url(self, host, media_id):
        return 'http://youwatch.org/%s' % media_id

    def get_host_and_id(self, url):
        r = re.search('http://(www.)?(.+?).org/embed-(.+?)-[0-9A-Za-z]+.html', url)
        if not r:
            r = re.search('http://(www.)?(.+?).org/([0-9A-Za-z]+)', url)
        if r :
            ls = r.groups()
            if ls[0] == 'www.' or ls[0] == None :
                ls = (ls[1],ls[2])
            return ls
        else :
            return False

    def exec_javascript(self,lsParam) :
        return re.sub('[a-zA-Z0-9]+',Base36(lsParam[3]).param36decode,str(lsParam[0]))
    
    def valid_url(self, url, host):
        if self.get_setting('enabled') == 'false': 
            return False
        return re.match('http://(www.)?youwatch.org/(embed-(.+?).html|[0-9A-Za-z]+)',url) or 'youwatch' in host    

    def login(self):
        if self.get_setting('login') == 'true':
            try :
                common.addon.log('login to youwatch')
                url = 'http://youwatch.org'
                data = {'op':'login', 'login' : self.get_setting('username'), 'password' : self.get_setting('password')}        
                source = self.net.http_POST(url,data).content      
                if re.search('<b>Registred</b>', source):            
                    common.addon.show_small_popup(title='[B][COLOR white]YOUWATCH LOGIN [/COLOR][/B]', msg='[COLOR green]Logged[/COLOR]', delay=5000, image=ok_logo)
                    self.net.save_cookies(self.cookie_file)
                    self.net.set_cookies(self.cookie_file)
                    return True
                elif re.search('Incorrect Login or Password', source) :
                    common.addon.log('**** Youwatch Error occured on login: Incorrect Login or Password')
                    common.addon.show_small_popup(title='[B][COLOR white]YOUWATCH LOGIN ERROR [/COLOR][/B]', msg='[COLOR red]Incorrect Login or Password[/COLOR]', delay=5000, image=error_logo)
                    return False
                else:
                    common.addon.log('**** Youwatch Error occured on login: not logged')
                    common.addon.show_small_popup(title='[B][COLOR white]YOUWATCH LOGIN ERROR [/COLOR][/B]', msg='[COLOR red]not logged[/COLOR]', delay=5000, image=error_logo)
                    return False
            except Exception, e :
                common.addon.log('**** Youwatch Error occured on login: %s' % e)
                common.addon.show_small_popup(title='[B][COLOR white]YOUWATCH LOGIN ERROR [/COLOR][/B]', msg='[COLOR red]%s[/COLOR]' % e, delay=5000, image=error_logo)
        else :
            return True

    def get_settings_xml(self):
        xml = PluginSettings.get_settings_xml(self)
        xml += '<setting id="YouwatchResolver_login" '        
        xml += 'type="bool" label="Login" default="false"/>\n'
        xml += '<setting id="YouwatchResolver_username" enable="eq(-1,true)" '
        xml += 'type="text" label="     username" default=""/>\n'
        xml += '<setting id="YouwatchResolver_password" enable="eq(-2,true)" '
        xml += 'type="text" label="     password" option="hidden" default=""/>\n'    
        return xml            