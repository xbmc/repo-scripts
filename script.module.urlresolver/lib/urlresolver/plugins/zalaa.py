"""
    urlresolver XBMC Addon
    Copyright (C) 2012 Bstrdsmkr

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

from t0mm0.common.net import Net
from urlresolver.plugnplay.interfaces import UrlResolver
from urlresolver.plugnplay.interfaces import PluginSettings
from urlresolver.plugnplay import Plugin
import urllib2, re, os
from urlresolver import common
from lib import jsunpack

#SET ERROR_LOGO# THANKS TO VOINAGE, BSTRDMKR, ELDORADO
error_logo = os.path.join(common.addon_path, 'resources', 'images', 'redx.png')


class ZalaaResolver(Plugin, UrlResolver, PluginSettings):
    implements = [UrlResolver, PluginSettings]
    name = "zalaa"

    def __init__(self):
        p = self.get_setting('priority') or 100
        self.priority = int(p)
        self.net = Net()
        #e.g.  http://www.zalaa.com/hj0eyq4jg0io
        #FIXME: http://www.zalaa.com/npwp1cr4uys7/Nikita.S02E14.HDTV.XviD-LOL.avi.htm
        self.pattern = 'http://www.(zalaa.com)/([a-zA-Z0-9]+)(?:/.+?\.htm)?'


    def get_media_url(self, host, media_id):
        web_url = self.get_url(host, media_id)

        try:
            html = self.net.http_GET(web_url).content

            #send all form values
            sPattern = '<input.*?name="([^"]+)".*?value=([^>]+)>'
            r = re.findall(sPattern, html)
            data = {}
            if r:
                for match in r:
                    name = match[0]
                    value = match[1].replace('"','')
                    data[name] = value

                html = self.net.http_POST(web_url, data).content
            else:
                raise Exception ('File Not Found or removed')

            # modified by mscreations. get the file url from the returned javascript
            match = re.search("addVariable[(]'file','(.+?)'[)]", html, re.DOTALL + re.IGNORECASE)
            if match:
                return match.group(1)+'|Referer=http%3A%2F%2Fwww.zalaa.com%2Fplayer%2Fplayer-embed.swf'

            raise Exception ('File Not Found or removed')
        except urllib2.URLError, e:
            common.addon.log_error(self.name + ': got http error %d fetching %s' %
                                   (e.code, web_url))
            common.addon.show_small_popup('Error','Http error: '+str(e), 8000, error_logo)
            return self.unresolvable(code=3, msg=e)
        except Exception, e:
            common.addon.log('**** Zalaa Error occured: %s' % e)
            common.addon.show_small_popup(title='[B][COLOR white]ZALAA[/COLOR][/B]', msg='[COLOR red]%s[/COLOR]' % e, delay=5000, image=error_logo)
            return self.unresolvable(code=0, msg=e)

    def get_url(self, host, media_id):
            return 'http://www.zalaa.com/%s' % (media_id)

    def get_host_and_id(self, url):
        r = re.search(self.pattern, url)
        if r:
            return r.groups()
        else:
            return False


    def valid_url(self, url, host):
        if self.get_setting('enabled') == 'false': return False
        return re.match(self.pattern, url) or self.name in host
