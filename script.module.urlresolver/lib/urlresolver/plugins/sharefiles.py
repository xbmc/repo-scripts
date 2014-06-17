"""
urlresolver XBMC Addon
Copyright (C) 2011 t0mm0

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
import urllib2
from urlresolver import common
from lib import jsunpack

# Custom imports
import re



class SharefilesResolver(Plugin, UrlResolver, PluginSettings):
    implements = [UrlResolver, PluginSettings]
    name = "sharefiles"

    def __init__(self):
        p = self.get_setting('priority') or 100
        self.priority = int(p)
        self.net = Net()
        self.pattern = 'http://((?:www.)?sharefiles4u.com)/([0-9a-zA-Z]+)'

    def get_media_url(self, host, media_id):
        web_url = self.get_url(host, media_id)

        try:
            html = self.net.http_GET(web_url).content

            #send all form values except premium
            sPattern = '<input.*?name="([^"]+)".*?value=([^>]+)>'
            r = re.findall(sPattern, html)
            data = {}
            for match in r:
                name = match[0]
                if 'premium' in name : continue
                value = match[1].replace('"','')
                data[name] = value
            html = self.net.http_POST(web_url, data).content

            # get url from packed javascript
            sPattern = "<div id=\"player_code\">\s*<script type='text/javascript'>eval.*?return p}\((.*?)\)\s*</script>"
            r = re.search(sPattern, html, re.DOTALL + re.IGNORECASE)
            sJavascript = r.group(1)
            sUnpacked = jsunpack.unpack(sJavascript)
            sPattern = '<param name="src"0="(.*?)"'
            r = re.search(sPattern, sUnpacked)
            return r.group(1)

        except urllib2.URLError, e:
            common.addon.log_error('Sharefiles: got http error %d fetching %s' %
                                  (e.code, web_url))
            common.addon.show_small_popup('Error','Http error: '+str(e), 5000, error_logo)
            return self.unresolvable(code=3, msg=e)
        
        except Exception, e:
            common.addon.log_error('**** Sharefiles Error occured: %s' % e)
            common.addon.show_small_popup(title='[B][COLOR white]SHAREFILES[/COLOR][/B]', msg='[COLOR red]%s[/COLOR]' % e, delay=5000, image=error_logo)
            return self.unresolvable(code=0, msg=e)


    def get_url(self, host, media_id):
            return 'http://www.sharefiles4u.com/%s' % (media_id)

    def get_host_and_id(self, url):
        r = re.search(self.pattern, url)
        if r:
            return r.groups()
        else:
            return False


    def valid_url(self, url, host):
        if self.get_setting('enabled') == 'false': return False
        return re.match(self.pattern, url) or self.name in host
