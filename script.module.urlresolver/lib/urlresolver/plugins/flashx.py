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
import urllib2
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
        self.pattern = 'http://((?:www.|play.)?flashx.tv)/(?:player/embed_player.php\?vid=|player/embed.php\?vid=|video/)([0-9a-zA-Z/-]+)'


    def get_media_url(self, host, media_id):
        web_url = self.get_url(host, media_id)
        try:
            html = self.net.http_GET(web_url).content
            if re.search('>Video not found',html):
                msg = 'File Not Found or removed'
                common.addon.show_small_popup(title='[B][COLOR white]FLASHX[/COLOR][/B]', msg='[COLOR red]%s[/COLOR]' 
                % msg, delay=5000, image=error_logo)
                return self.unresolvable(code = 1, msg = msg)
            if re.search('conversion queue <',html):
                msg = 'File is still being converted'
                common.addon.show_small_popup(title='[B][COLOR white]FLASHX[/COLOR][/B]', msg='[COLOR red]%s[/COLOR]' 
                % msg, delay=5000, image=error_logo)
                return self.unresolvable(code = 2, msg = msg)
             
            #get embedded player
            pattern = '(http://play\.flashx\.tv/player/embed\.php\?vid=[^&]+)'
            r = re.search(pattern, html)
            if not r:
                raise Exception ('Unable to resolve Flashx link. Embedded link not found.')
            web_url = r.group(1)
            html = self.net.http_GET(web_url).content
            #get form action
            pattern = 'action="([^"]+)"'
            r = re.search(pattern, html)
            if not r:
                raise Exception ('Unable to resolve Flashx link. Post action not found.')
            form_action = r.group(1)
            form_values = {}
            #get post var
            for i in re.finditer('<input.*?name="(.*?)".*?value="(.*?)">', html):
                form_values[i.group(1)] = i.group(2)
            if not r:
                raise Exception ('Unable to resolve Flashx link. Post var not found.')           
            web_url = web_url[0:web_url.rfind('/')+1] + form_action
            html = self.net.http_POST(web_url, form_data=form_values).content
            #get config url
            pattern = 'data="([^"]+)"'
            r = re.search(pattern, html)
            if not r:
                raise Exception ('Unable to resolve Flashx link. Config url not found.')
            web_url = r.group(1)                   
            html = self.net.http_GET(web_url).content
            #get player url
            web_url = web_url.split('config=')[-1]
            html = self.net.http_GET(web_url).content
            #get file link
            pattern = '<file>([^<]+)</file>'
            r = re.search(pattern, html)
            if not r:
                raise Exception ('Unable to resolve Flashx link. Filelink not found.')
            return r.group(1)
            
        except urllib2.URLError, e:
            common.addon.log_error(self.name + ': got http error %d fetching %s' %
                                    (e.code, web_url))
            common.addon.show_small_popup('Error','Http error: '+str(e), 8000, error_logo)
            return self.unresolvable(code=3, msg='Exception: %s' % e) 
        except Exception, e:
            common.addon.log('**** Flashx Error occured: %s' % e)
            common.addon.show_small_popup(title='[B][COLOR white]FLASHX[/COLOR][/B]', msg='[COLOR red]%s[/COLOR]' 
            % e, delay=5000, image=error_logo)
            return self.unresolvable(code=0, msg='Exception: %s' % e) 

    def get_url(self, host, media_id):
            return 'http://flashx.tv/video/%s' % (media_id)

    def get_host_and_id(self, url):
        r = re.search(self.pattern, url)
        if r:
            return r.groups()
        else:
            return False

    def valid_url(self, url, host):
        if self.get_setting('enabled') == 'false': return False
        return re.match(self.pattern, url) or self.name in host
