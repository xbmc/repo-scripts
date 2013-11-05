"""
vidx urlresolver plugin
Copyright (C) 2013 kriskra

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

from t0mm0.common.net import Net
from urlresolver.plugnplay.interfaces import UrlResolver
from urlresolver.plugnplay.interfaces import PluginSettings
from urlresolver.plugnplay import Plugin
import urllib2, os
from urlresolver import common
from lib import jsunpack
import xbmcgui
import re
import time

#SET ERROR_LOGO# THANKS TO VOINAGE, BSTRDMKR, ELDORADO
error_logo = os.path.join(common.addon_path, 'resources', 'images', 'redx.png')


class vidxResolver(Plugin, UrlResolver, PluginSettings):
    implements = [UrlResolver, PluginSettings]
    name = "vidx"

    def __init__(self):
        p = self.get_setting('priority') or 100
        self.priority = int(p)
        self.net = Net()

    def get_media_url(self, host, media_id):
        web_url = self.get_url(host, media_id)

        try:
            resp = self.net.http_GET(web_url)
            html = resp.content
            post_url = resp.get_url()
            dialog = xbmcgui.Dialog()
                
            if re.search('>(File Not Found)<',html):
                raise Exception ('File Not Found or removed')
                
            form_values = {}
            for i in re.finditer('<input.*?name="(.*?)".*?value="(.*?)">', html):
                form_values[i.group(1)] = i.group(2)
            #wait required
            common.addon.show_countdown(11)
            common.addon.log(post_url)
            html = self.net.http_POST(post_url, form_data=form_values).content
            
            r = re.search('file: "(.+?)",', html)
            if r:
                return r.group(1)
            else:
                raise Exception ('File Not Found or removed')
        except urllib2.URLError, e:
            common.addon.log_error(self.name + ': got http error %d fetching %s' %
                                   (e.code, web_url))
            common.addon.show_small_popup('Error','Http error: '+str(e), 8000, error_logo)
            return self.unresolvable(code=3, msg=e)
        except Exception, e:
            common.addon.log('**** vidx Error occured: %s' % e)
            common.addon.show_small_popup(title='[B][COLOR white]vidx[/COLOR][/B]', msg='[COLOR red]%s[/COLOR]' % e, delay=5000, image=error_logo)
            return self.unresolvable(code=0, msg=e)

    def get_url(self, host, media_id):
            return 'http://vidx.to/%s.html' % (media_id)

    def get_host_and_id(self, url):
        r = re.search('http://(?:www.)?(.+?)/([0-9A-Za-z]+)', url)
        if r:
            return r.groups()
        else:
            return False


    def valid_url(self, url, host):
        if self.get_setting('enabled') == 'false': return False
        return re.match('http://(www.)?vidx.to/[0-9A-Za-z]+\.html', url) or 'vidx' in host

