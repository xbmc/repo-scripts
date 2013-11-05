'''
jumbofiles urlresolver plugin
Copyright (C) 2011 anilkuj

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
'''

from t0mm0.common.net import Net
from urlresolver.plugnplay.interfaces import UrlResolver
from urlresolver.plugnplay.interfaces import PluginSettings
from urlresolver.plugnplay import Plugin
import re
import urllib2
from urlresolver import common
import os, xbmcgui
from vidxden import unpack_js


class JumbofilesResolver(Plugin, UrlResolver, PluginSettings):
    implements = [UrlResolver, PluginSettings]
    name = "jumbofiles"


    def __init__(self):
        p = self.get_setting('priority') or 100
        self.priority = int(p)
        self.net = Net()


    def get_media_url(self, host, media_id):
        try:
            common.addon.log('jumbofiles: in get_media_url %s %s' % (host, media_id))
            web_url = self.get_url(host, media_id)
            html = self.net.http_GET(web_url).content
    
            dialog = xbmcgui.Dialog()
    
            if 'file has been removed' in html:
                raise Exception ('File has been removed.')
    
            form_values = {}
            for i in re.finditer('<input type="hidden" name="(.+?)" value="(.+?)">', html):
                form_values[i.group(1)] = i.group(2)
    
            html = self.net.http_POST(web_url, form_data=form_values).content
            match = re.search('ACTION="(.+?)"', html)
            if match:
                return match.group(1)
            else:
                raise Exception ('failed to parse link')

        except urllib2.URLError, e:
            common.addon.log_error('Jumbofiles: got http error %d fetching %s' %
                                  (e.code, web_url))
            common.addon.show_small_popup('Error','Http error: '+str(e), 5000, error_logo)
            return self.unresolvable(code=3, msg=e)
        
        except Exception, e:
            common.addon.log_error('**** Jumbofiles Error occured: %s' % e)
            common.addon.show_small_popup(title='[B][COLOR white]JUMBOFILES[/COLOR][/B]', msg='[COLOR red]%s[/COLOR]' % e, delay=5000, image=error_logo)
            return self.unresolvable(code=0, msg=e)
    

    def get_url(self, host, media_id):
        common.addon.log('jumbofiles: in get_url %s %s' % (host, media_id))
        return 'http://www.jumbofiles.com/%s' % media_id 
        
        
    def get_host_and_id(self, url):
        common.addon.log('jumbofiles: in get_host_and_id %s' % (url))
        r = re.search('//(.+?)/([0-9a-zA-Z/]+)', url)
        if r:
            return r.groups()
        else:
            return False


    def valid_url(self, url, host):
        if self.get_setting('enabled') == 'false': return False
        return (re.match('http://(www.)?jumbofiles.com/' +
                         '[0-9A-Za-z]+', url) or
                         'jumbofiles' in host)
