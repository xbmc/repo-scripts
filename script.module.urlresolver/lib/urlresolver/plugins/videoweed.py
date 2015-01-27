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

import re
from t0mm0.common.net import Net
import urllib2, os
from urlresolver import common
from urlresolver.plugnplay.interfaces import UrlResolver
from urlresolver.plugnplay.interfaces import PluginSettings
from urlresolver.plugnplay import Plugin
import xbmcgui
from lib import unwise

#SET ERROR_LOGO# THANKS TO VOINAGE, BSTRDMKR, ELDORADO
error_logo = os.path.join(common.addon_path, 'resources', 'images', 'redx.png')

class VideoweedResolver(Plugin, UrlResolver, PluginSettings):
    implements = [UrlResolver, PluginSettings]
    name = "videoweed.es"

    def __init__(self):
        p = self.get_setting('priority') or 100
        self.priority = int(p)
        self.net = Net()

    def get_media_url(self, host, media_id):
        web_url = self.get_url(host, media_id)
        dialog = xbmcgui.Dialog()
        #grab stream details
        try:
            html = self.net.http_GET(web_url).content
            html = unwise.unwise_process(html)
            filekey = unwise.resolve_var(html, "flashvars.filekey")

            #use api to find stream address
            api_call = ('http://www.videoweed.es/api/player.api.php?user=undefined&codes=1&file=%s' +
                        '&pass=undefined&key=%s') % (media_id, filekey)

            api_html = self.net.http_GET(api_call).content
            rapi = re.search('url=(.+?)&title=', api_html)
            if rapi:
                stream_url = rapi.group(1)
            else:
                raise Exception ('File Not Found or removed')
            
            return stream_url

        except urllib2.URLError, e:
            common.addon.log_error(self.name + ': got http error %d fetching %s' %
                                   (e.code, web_url))
            common.addon.show_small_popup('Error','Http error: '+str(e), 8000, error_logo)
            return self.unresolvable(code=3, msg=e)
        except Exception, e:
            common.addon.log('**** Videoweed Error occured: %s' % e)
            common.addon.show_small_popup(title='[B][COLOR white]VIDEOWEED[/COLOR][/B]', msg='[COLOR red]%s[/COLOR]' % e, delay=5000, image=error_logo)
            return self.unresolvable(code=0, msg=e)

    def get_url(self, host, media_id):
        return 'http://www.videoweed.es/file/%s' % media_id

    def get_host_and_id(self, url):
        r = re.search('//(?:embed.)?(.+?)/(?:video/|embed.php\?v=|file/)' + 
                      '([0-9a-z]+)', url)
        if r:
            return r.groups()
        else:
            return False

    def valid_url(self, url, host):
        if self.get_setting('enabled') == 'false': return False
        return re.match('http://(www.|embed.)?videoweed.(?:es|com)/(video/|file|embed.php\?|file/)' +
                        '(?:[0-9a-z]+|width)', url) or 'videoweed' in host
