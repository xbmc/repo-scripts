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

from t0mm0.common.net import Net
from urlresolver.plugnplay.interfaces import UrlResolver
from urlresolver.plugnplay.interfaces import PluginSettings
from urlresolver.plugnplay import Plugin
import urllib2, urllib
from time import sleep
from urlresolver import common
import os

# Custom imports
import re

error_logo = os.path.join(common.addon_path, 'resources', 'images', 'redx.png')

class FlashxResolver(Plugin, UrlResolver, PluginSettings):
    implements = [UrlResolver, PluginSettings]
    name = "flashx"

    def __init__(self):
        p = self.get_setting('priority') or 100
        self.priority = int(p)
        self.net = Net()
        #e.g. http://flashx.tv/player/embed_player.php?vid=1503&width=600&height=370&autoplay=no
        self.pattern = 'http://((?:www.|play.)?flashx.tv)/(?:embed-)?([0-9a-zA-Z/-]+)(?:.html)?'


    def get_media_url(self, host, media_id):
        try:
            web_url = self.get_url(host, media_id)
            html = self.net.http_GET(web_url).content
            #print html.encode('ascii','ignore')
            headers = {
                'Referer': web_url
            }

            match = re.search("method=\"POST\" action='([^']+)", html)
            if match:
                form_url = match.group(1)
            else:
                raise Exception("Form Link Not Found")
                
            data = {}
            r = re.findall(r'type="hidden"\s*name="(.+?)"\s*value="(.*?)"', html)
            for name, value in r: data[name] = value
            data.update({'referer': web_url})
            data.update({'imhuman': 'Proceed to video'})

            # parse cookies from file as they are only useful for this interaction
            cookies={}
            for match in re.finditer("\$\.cookie\('([^']+)',\s*'([^']+)",html):
                key,value = match.groups()
                cookies[key]=value
            headers['Cookie']=urllib.urlencode(cookies)
            
            # POST seems to fail is submitted too soon after GET. Page Timeout?
            common.addon.show_countdown(10, title='FlashX.tv', text='Waiting for countdown...')
            
            html = self.net.http_POST(form_url, data, headers=headers).content
            #print html.encode('ascii','ignore')

            #{file: "http://u01.flashx.tv/luq4qurpehixexzw6v63f6mjtazgxcbn6qnvcvz5yvr7ff5acb2zmvmswa6q/v.mp4"}]
            r = re.search('file\s*:\s*"(http://[^"]+mp4)', html)
            if r:
                return r.group(1)
            else:
                raise Exception("File Link Not Found")

        except urllib2.URLError, e:
            common.addon.log_error('flashx.tv: got http error %d fetching %s' %
                                  (e.code, web_url))
            common.addon.show_small_popup('Error','flashx.tv: HTTP error: '+str(e), 5000, error_logo)
            return self.unresolvable(code=3, msg=e)
        
        except Exception, e:
            common.addon.log_error('flashx.tv: general error occured: %s' % e)
            common.addon.show_small_popup(title='[B][COLOR white]FLASHX.TV[/COLOR][/B]', msg='[COLOR red]%s[/COLOR]' % e, delay=5000, image=error_logo)
            return self.unresolvable(code=0, msg=e)

        return False

    def get_url(self, host, media_id):
            return 'http://flashx.tv/%s.html' % (media_id)

    def get_host_and_id(self, url):
        r = re.search(self.pattern, url)
        if r:
            return r.groups()
        else:
            return False

    def valid_url(self, url, host):
        if self.get_setting('enabled') == 'false': return False
        return re.match(self.pattern, url) or self.name in host
