"""
    urlresolver XBMC Addon
    Copyright (C) 2011 t0mm0

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
import random
import re
import urllib, urllib2

from urlresolver.plugnplay.interfaces import UrlResolver
from urlresolver.plugnplay.interfaces import SiteAuth
from urlresolver.plugnplay.interfaces import PluginSettings
from urlresolver.plugnplay import Plugin
from urlresolver import common
import xbmc,xbmcplugin,xbmcgui,xbmcaddon, datetime
import cookielib
from t0mm0.common.net import Net


class RealDebridResolver(Plugin, UrlResolver, SiteAuth, PluginSettings):
    implements = [UrlResolver, SiteAuth, PluginSettings]
    name = "realdebrid"
    profile_path = common.profile_path    
    cookie_file = os.path.join(profile_path, '%s.cookies' % name)
    media_url = None
    allHosters = None


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
        print 'in get_media_url %s : %s' % (host, media_id)
        dialog = xbmcgui.Dialog()

        try:
            url = 'http://real-debrid.com/ajax/deb.php?lang=en&sl=1&link=%s' % media_id
            source = self.net.http_GET(url).content
        except Exception, e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
            print(exc_type, fname, exc_tb.tb_lineno)
            dialog.ok(' Real-Debrid ', ' Real-Debrid server timed out ', '', '')
            return False
        print '************* %s' % source
        
        if re.search('Upgrade your account now to generate a link', source):
            dialog.ok(' Real-Debrid ', ' Upgrade your account now to generate a link ', '', '')
            return False
        if source == '<span id="generation-error">Your file is unavailable on the hoster.</span>':
            dialog.ok(' Real-Debrid ', ' Your file is unavailable on the hoster ', '', '')
            return False
        if re.search('This hoster is not included in our free offer', source):
            dialog.ok(' Real-Debrid ', ' This hoster is not included in our free offer ', '', '')            
            return False
        if re.search('No server is available for this hoster.', source):
            dialog.ok(' Real-Debrid ', ' No server is available for this hoster ', '', '')            
            return False
        link =re.compile('ok"><a href="(.+?)"').findall(source)

        if len(link) == 0:
            return False
        
        print 'link is %s' % link[0]
        self.media_url = link[0]

        # avoid servers as configured in the settings to get better playback of your video on XBMC
##        if self.get_setting('avoidserver') == 'true':
##            print 'in chooseserver'
##            server = re.compile('//(.+?)\.').findall(link[0])
##            if len(server) > 0:
##                avoid = (self.get_setting('server')).split(',')
##                if server[0] in avoid:
##                    check = True
##                    while check:
##                        check = False
##                        new = ''
##                        gen = random.randint(1, 18)
##                        if len(str(gen)) == 1:
##                            new = 's0' + str(gen)
##                        else:
##                            new = 's' + str(gen)
##
##                        if new in avoid:
##                            check = True
##
##                    link[0] = re.sub('//.+?\.', '//' +new + '.', link[0], count = 1)
##                    print 'link is %s' % link[0]
        return link[0]
        
    def get_url(self, host, media_id):
        return media_id
        
        
    def get_host_and_id(self, url):
        return 'www.real-debrid.com', url

    def get_all_hosters(self):
        if self.allHosters is None:
            url = 'http://real-debrid.com/lib/api/hosters.php'
            self.allHosters = self.net.http_GET(url).content
        return self.allHosters 

    def valid_url(self, url, host):

        if self.get_setting('login') == 'false':
            return False
        print 'in valid_url %s : %s' % (url, host)
        tmp = re.compile('//(.+?)/').findall(url)
        domain = ''
        if len(tmp) > 0 :
            domain = tmp[0].replace('www.', '')
            if 'megashares' in domain:
                domain = 'megashares.com'
            elif 'megashare' in domain:
                domain = 'megashare.com'
            print 'domain is %s ' % domain
        if (domain in self.get_all_hosters()) or (len(host) > 0 and host in self.get_all_hosters()):
            return True
        else:
            return False

    def  checkLogin(self):
        url = 'http://real-debrid.com/lib/api/account.php'
        if not os.path.exists(self.cookie_file):
               return True
        self.net.set_cookies(self.cookie_file)
        source =  self.net.http_GET(url).content
        print source
        if re.search('expiration', source):
            print 'checkLogin returning False'
            return False
        else:
            print 'checkLogin returning True'
            return True
    
    #SiteAuth methods
    def login(self):
        if self.checkLogin():
            try:
                print 'Need to login since session is invalid'
                login_data = urllib.urlencode({'user' : self.get_setting('username'), 'pass' : self.get_setting('password')})
                url = 'https://real-debrid.com/ajax/login.php?' + login_data
                source = self.net.http_GET(url).content
                if re.search('OK', source):
                    self.net.save_cookies(self.cookie_file)
                    self.net.set_cookies(self.cookie_file)
                    return True
            except:
                    print 'error with http_GET'
                    dialog = xbmcgui.Dialog()
                    dialog.ok(' Real-Debrid ', ' Unexpected error, Please try again.', '', '')            
            else:
                return False
        else:
            return True

    #PluginSettings methods
    def get_settings_xml(self):
        xml = PluginSettings.get_settings_xml(self)
        xml += '<setting id="RealDebridResolver_login" '
        xml += 'type="bool" label="login" default="false"/>\n'
        xml += '<setting id="RealDebridResolver_username" enable="eq(-1,true)" '
        xml += 'type="text" label="username" default=""/>\n'
        xml += '<setting id="RealDebridResolver_password" enable="eq(-2,true)" '
        xml += 'type="text" label="password" option="hidden" default=""/>\n'
##        xml += '<setting id="RealDebridResolver_avoidserver" '
##        xml += 'type="bool" label="Avoid Servers" default="false"/>\n'        
##        xml += '<setting id="RealDebridResolver_server" '
##        xml += 'type="text" label="Avoid Servers # (Eg. s01,s02)" default="s09,s18"/>\n'
        return xml
        
    #to indicate if this is a universal resolver
    def isUniversal(self):
        
        return True
