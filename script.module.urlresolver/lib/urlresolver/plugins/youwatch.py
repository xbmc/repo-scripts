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
import urllib2, os, re
from t0mm0.common.net import Net
from urlresolver.plugnplay.interfaces import UrlResolver
from urlresolver.plugnplay.interfaces import PluginSettings
from urlresolver.plugnplay import Plugin
from urlresolver import common

#SET ERROR_LOGO# THANKS TO VOINAGE, BSTRDMKR, ELDORADO
error_logo = os.path.join(common.addon_path, 'resources', 'images', 'redx.png')


class YouwatchResolver(Plugin, UrlResolver, PluginSettings):
    implements = [UrlResolver, PluginSettings]
    name = "youwatch"
    
    def __init__(self):
        p = self.get_setting('priority') or 100
        self.priority = int(p)
        self.net = Net()

    def get_media_url(self, host, media_id):
        base_url = 'http://'+host+'.org/embed-'+media_id+'.html'
        try:
            soup = self.net.http_GET(base_url).content
            r = re.findall('file: "(.+)?",',soup.decode('utf-8'))
            if r :
                stream_url = r[0].encode('utf-8')
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

    def valid_url(self, url, host):
        if self.get_setting('enabled') == 'false': 
            return False
        return re.match('http://(www.)?youwatch.org/(embed-(.+?).html|[0-9A-Za-z]+)',url) or 'youwatch' in host    
