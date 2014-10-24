#-*- coding: utf-8 -*-

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

import urllib, urllib2, os, re
from t0mm0.common.net import Net
from urlresolver.plugnplay.interfaces import UrlResolver
from urlresolver.plugnplay.interfaces import PluginSettings
from urlresolver.plugnplay import Plugin
from urlresolver import common

#SET ERROR_LOGO# THANKS TO VOINAGE, BSTRDMKR, ELDORADO
error_logo = os.path.join(common.addon_path, 'resources', 'images', 'redx.png')
#SET OK_LOGO# THANKS TO JUL1EN094
ok_logo = os.path.join(common.addon_path, 'resources', 'images', 'greeninch.png')

class ExashareResolver(Plugin, UrlResolver, PluginSettings):
    implements = [UrlResolver, PluginSettings]
    name = "exashare"    

    def __init__(self):
        p = self.get_setting('priority') or 100
        self.priority = int(p)
        self.net = Net()

    def get_media_url(self, host, media_id):
        base_url = 'http://www.'+host+'.com/'+media_id
        try:
            html  = self.net.http_GET(base_url).content
            stream_url = re.findall('file: "([^"]+)"', html)[0]
            return stream_url
        except urllib2.HTTPError, e:
            e = e.code
            common.addon.log_error(self.name + ': got Http error %s fetching %s' % (e, base_url))
            common.addon.show_small_popup('Error','Http error: %s' % e, 8000, image=error_logo)
            return self.unresolvable(code=3, msg=e)
        except urllib2.URLError, e:
            e = str(e.args)
            common.addon.log_error(self.name + ': got Url error %s fetching %s' % (e, base_url))
            common.addon.show_small_popup('Error','URL error: %s' % e, 8000, image=error_logo)
            return self.unresolvable(code=3, msg=e)
        except IndexError, e :
            if re.search("""File Not Found""", html) :
                e = 'File not found or removed'
                common.addon.log('**** Exashare Error occured: %s' % e)
                common.addon.show_small_popup(title='[B][COLOR white]EXASHARE[/COLOR][/B]', msg='[COLOR red]%s[/COLOR]' % e, delay=5000, image=error_logo)
                return self.unresolvable(code=1, msg=e)
            else :
                common.addon.log('**** Exashare Error occured: %s' % e)
                common.addon.show_small_popup(title='[B][COLOR white]EXASHARE[/COLOR][/B]', msg='[COLOR red]%s[/COLOR]' % e, delay=5000, image=error_logo)
                return self.unresolvable(code=0, msg=e) 
        except Exception, e:
            common.addon.log('**** Exashare Error occured: %s' % e)
            common.addon.show_small_popup(title='[B][COLOR white]EXASHARE[/COLOR][/B]', msg='[COLOR red]%s[/COLOR]' % e, delay=5000, image=error_logo)
            return self.unresolvable(code=0, msg=e)

    def get_url(self, host, media_id):
        return 'http://www.exashare.com/%s' % media_id

    def get_host_and_id(self, url):
        r = re.search('http://(www.)?(.+?).com/(embed\-)?(.+)(\-[0-9]+x[0-9]+.html)?', url)
        if r :
            ls = r.groups()
            ls = (ls[1],ls[3])
            return ls
        else :
            return False

    def valid_url(self, url, host):
        if self.get_setting('enabled') == 'false': 
            return False
        return re.match('http://(www.)?exashare.com/(embed\-)?[0-9A-Za-z]+(\-[0-9]+x[0-9]+.html)?',url) or 'exashare.com' in host    

    def get_settings_xml(self):
        xml = PluginSettings.get_settings_xml(self)
        return xml            