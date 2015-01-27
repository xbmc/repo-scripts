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

import re, urllib, urllib2, os
from t0mm0.common.net import Net
from urlresolver import common
from urlresolver.plugnplay.interfaces import UrlResolver
from urlresolver.plugnplay.interfaces import PluginSettings
from urlresolver.plugnplay import Plugin

#SET ERROR_LOGO# THANKS TO VOINAGE, BSTRDMKR, ELDORADO
error_logo = os.path.join(common.addon_path, 'resources', 'images', 'redx.png')

class VideomegaResolver(Plugin, UrlResolver, PluginSettings):
    implements = [UrlResolver, PluginSettings]
    name = "videomega"

    def __init__(self):
        p = self.get_setting('priority') or 100
        self.priority = int(p)
        self.net = Net()

    def get_media_url(self, host, media_id):
        web_url = self.get_url(host, media_id)
        try:
            html = self.net.http_GET(web_url).content
            stream_url = None

            # find the unescape string 
            r = re.search('document\.write\(unescape\("([^"]+)',html)

            if r:
                unescaped_str = urllib.unquote(r.group(1))
                r = re.search('file:\s+"([^"]+)',unescaped_str)
                if r:
                    stream_url = r.group(1)
                    stream_url = stream_url.replace(" ","%20")
                
            if stream_url:
                return stream_url
            else:
                return self.unresolvable(0, 'No playable video found.')
            
        except urllib2.URLError, e:
            common.addon.log_error('Videomega: got http error %d fetching %s' %
                                    (e.code, web_url))
            return self.unresolvable(code=3, msg=e)
        except Exception, e:
            common.addon.log_error('**** Videomega Error occured: %s' % e)
            common.addon.show_small_popup(title='[B][COLOR white]Videomega[/COLOR][/B]', msg='[COLOR red]%s[/COLOR]' % e, delay=5000, image=error_logo)
            return self.unresolvable(code=0, msg=e)

    def get_url(self, host, media_id):
        return 'http://%s/iframe.php?ref=%s' % (host,media_id)

    def get_host_and_id(self, url):
        r = re.search('//((?:www.)?(?:.+?))/(?:iframe.(?:php|js)\?ref=)([0-9a-zA-Z]+)', url)
        if r:
            return r.groups()
        else:
            return False

    def valid_url(self, url, host):
        if self.get_setting('enabled') == 'false': return False
        return re.match('http://(?:www.)?videomega.tv/iframe.(?:php|js)\?', url) or 'videomega' in host
