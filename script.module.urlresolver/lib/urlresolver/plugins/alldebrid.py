"""
    urlresolver XBMC Addon
    Copyright (C) 2011 t0mm0, JUL1EN094

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
import simplejson as json
import xbmc,xbmcplugin,xbmcgui,xbmcaddon, datetime
import cookielib
from t0mm0.common.net import Net

#SET ERROR_LOGO# THANKS TO VOINAGE, BSTRDMKR, ELDORADO
error_logo = os.path.join(common.addon_path, 'resources', 'images', 'redx.png')

class AllDebridResolver(Plugin, UrlResolver, SiteAuth, PluginSettings):
    implements = [UrlResolver, SiteAuth, PluginSettings]
    name = "AllDebrid"
    domains = [ '*']
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
        common.addon.log('in get_media_url %s : %s' % (host, media_id))
        dialog = xbmcgui.Dialog()
        try:
            url = 'http://www.alldebrid.com/service.php?link=%s' % media_id
            source = self.net.http_GET(url).content
            source = source.decode('utf-8')
        except Exception, e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
            common.addon.log(str(exc_type) + " : " + fname + " : " + str(exc_tb.tb_lineno))
            dialog.ok(' all-Debrid ', ' all-Debrid server timed out ', '', '')
            return self.unresolvable(3,'alldebrid : error contacting the site')
        common.addon.log('************* %s' % source.encode('utf-8'))

        if re.search('login', source):
            dialog.ok(' All Debrid Message ', ' Your account may have Expired, please check by going to the website ', '', '')
            return self.unresolvable(0,'alldebrid : Your account may have expired')
        if re.search('Hoster unsupported or under maintenance', source):
            dialog.ok(' All Debrid Message ', ' Sorry this hoster is not supported, change the priority level in resolver settings for this host ', '', '')
            return self.unresolvable(2,'alldebrid : pb for supporting this hoster')
        #Go
        finallink = ''
        #try json return
        try:
            link      = json.loads(source)
            streaming = link['streaming']
            line      = [] 
            for item in streaming :
                line.append(item.encode('utf-8'))
            result = xbmcgui.Dialog().select('Choose the link', line)
            if result != -1 :
                finallink = streaming[str(line[result])].encode('utf-8')                  
        #classic method
        except :
            link =re.compile("href='(.+?)'").findall(source)
            if len(link) != 0:
                finallink = link[0].encode('utf-8')               
        #end
        common.addon.log('finallink is %s' % finallink)
        if finallink != '' :
            self.media_url = finallink
            return finallink
        #false/errors
        elif 'Invalid link' in source :
            common.addon.show_small_popup(title='[B][COLOR white]ALLDEBRID[/COLOR][/B]', msg='[COLOR red]INVALID LINK[/COLOR]', delay=15000, image=error_logo)
            return self.unresolvable(1,'Invalid link')
        else :
            return self.unresolvable(0,'No generated_link')

    def get_url(self, host, media_id):
        return media_id

    def get_host_and_id(self, url):
        return 'www.alldebrid.com', url

    def get_all_hosters(self):
        if self.allHosters is None:
            url = 'http://alldebrid.com/api.php?action=get_host'
            self.allHosters = self.net.http_GET(url).content
        return self.allHosters

    def valid_url(self, url, host):
        if self.get_setting('enabled') == 'false': return False
        if self.get_setting('login') == 'false':
            return False
        common.addon.log('in valid_url %s : %s' % (url, host))
        tmp = re.compile('//(.+?)/').findall(url)
        domain = ''
        if len(tmp) > 0 :
            domain = tmp[0].replace('www.', '')
            if 'megashares' in domain:
                domain = 'megashares.com'
            elif 'megashare' in domain:
                domain = 'megashare.com'
            elif 'mixture' in domain :
                domain = 'mixturevideo.com'
            common.addon.log('domain is %s ' % domain)
        if (domain in self.get_all_hosters()) or (len(host) > 0 and host in self.get_all_hosters()):
            return True
        else:
            return False

    def  checkLogin(self):
        url = 'http://alldebrid.com/service.php'
        if not os.path.exists(self.cookie_file):
               return True
        self.net.set_cookies(self.cookie_file)
        source =  self.net.http_GET(url).content
        common.addon.log(source)
        if re.search('login', source):
            common.addon.log('checkLogin returning False')
            return False
        else:
            common.addon.log('checkLogin returning True')
            return True

    #SiteAuth methods
    def login(self):
        if self.checkLogin():
            try:
                common.addon.log('Need to login since session is invalid')
                login_data = urllib.urlencode({'action' : 'login','login_login' : self.get_setting('username'), 'login_password' : self.get_setting('password')})
                url = 'http://alldebrid.com/register/?' + login_data
                source = self.net.http_GET(url).content
                if re.search('Control panel', source):
                    self.net.save_cookies(self.cookie_file)
                    self.net.set_cookies(self.cookie_file)
                    return True
            except:
                    common.addon.log('error with http_GET')
                    dialog = xbmcgui.Dialog()
                    dialog.ok(' Real-Debrid ', ' Unexpected error, Please try again.', '', '')
            else:
                return False
        else:
            return True

    #PluginSettings methods
    def get_settings_xml(self):
        xml = PluginSettings.get_settings_xml(self)
        xml += '<setting id="AllDebridResolver_login" '
        xml += 'type="bool" label="login" default="false"/>\n'
        xml += '<setting id="AllDebridResolver_username" enable="eq(-1,true)" '
        xml += 'type="text" label="username" default=""/>\n'
        xml += '<setting id="AllDebridResolver_password" enable="eq(-2,true)" '
        xml += 'type="text" label="password" option="hidden" default=""/>\n'
        return xml

    #to indicate if this is a universal resolver
    def isUniversal(self):
        return True
