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
import re
import urllib2
from urlresolver import common

class ZshareResolver(Plugin, UrlResolver, PluginSettings):
    implements = [UrlResolver, PluginSettings]
    name = "zshare"

    def __init__(self):
        p = self.get_setting('priority') or 100
        self.priority = int(p)
        self.net = Net()
        self.pattern ='http://((?:www.)?zshare.net)/video/([0-9A-Za-z]+)'


    def get_media_url(self, host, media_id):
        web_url = self.get_url(host, media_id)

        try:
            html = self.net.http_GET(web_url).content

            # get iframe redirect
            sPattern = '<iframe src="(http://www.zshare.net[^"]+)"'
            r = re.search(sPattern, html, re.DOTALL + re.IGNORECASE)
            if r:
                iframe = r.group(1).replace(" ", "+")
                html = self.net.http_GET(iframe).content

            # get stream url
            stream_url = ''
            sPattern = 'file: "([^"]+)"'
            r = re.search(sPattern, html, re.DOTALL + re.IGNORECASE)
            if r:
                stream_url = r.group(1).replace(" ", "+") + "?start=0" + '|user-agent=Mozilla/5.0 (X11; Linux i686) AppleWebKit/535.1 (KHTML, like Gecko) Chrome/14.0.835.109 Safari/535.1'

            # get download url
            download_url = ''
            # emulate download button click
            sPattern = '<a href="([^"]+)"[^>]*>Download Video</a>'
            r = re.search(sPattern, html, re.DOTALL + re.IGNORECASE)
            if r:
                buttonlink = r.group(1)
                data = {'referer2': '',
                        'download': 1,
                        'imageField.x': 76,
                        'imageField.y': 28
                        }
                html = self.net.http_POST(buttonlink, data).content

                sPattern = 'new Array\(([^\)]*)\);'
                r = re.search(sPattern, html, re.DOTALL + re.IGNORECASE)
                if r:
                    download_url = r.group(1).replace("'","").replace(",","")

            return stream_url

        except urllib2.URLError, e:
            common.addon.log_error('Zshare: got http error %d fetching %s' %
                                  (e.code, web_url))
            common.addon.show_small_popup('Error','Http error: '+str(e), 5000, error_logo)
            return self.unresolvable(code=3, msg=e)

        except Exception, e:
            common.addon.log_error('**** Zshare Error occured: %s' % e)
            common.addon.show_small_popup(title='[B][COLOR white]ZSHARE[/COLOR][/B]', msg='[COLOR red]%s[/COLOR]' % e, delay=5000, image=error_logo)
            return self.unresolvable(code=0, msg=e)


    def get_url(self, host, media_id):
            return 'http://www.zshare.net/video/%s' % (media_id)

    def get_host_and_id(self, url):
        r = re.search(self.pattern, url)
        if r:
            return r.groups()
        else:
            return False

    def valid_url(self, url, host):
        if self.get_setting('enabled') == 'false': return False
        return re.match(self.pattern, url) or self.name in host
