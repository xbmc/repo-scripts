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
import re, os
import random
import urllib2
from urlresolver import common

#SET ERROR_LOGO# THANKS TO VOINAGE, BSTRDMKR, ELDORADO
error_logo = os.path.join(common.addon_path, 'resources', 'images', 'redx.png')

class Stream2kResolver(Plugin, UrlResolver, PluginSettings):
    implements = [UrlResolver, PluginSettings]
    name = "stream2k"

    def __init__(self):
        p = self.get_setting('priority') or 100
        self.priority = int(p)
        self.net = Net()
        # e.g. http://server4.stream2k.com/playerjw/vConfig56.php?vkey=1d8dc00940da661ffba9
        # updated to resolver the embedded url also : http://embed.stream2k.com/mdBtg097yuQc-7bXQBt-9GwtNEDawZJceCuSqsu86DXshHXngHMYOkq7YDwT-5c6s=nqAOQRzQ177QnR2P3vKOTQ&e=1358597943
        self.pattern ='http://([^/]*stream2k.com)/[^"]+vkey=([0-9A-Za-z]+)'
       
    def get_media_url(self, host, media_id):
        web_url = self.get_url(host, media_id)
        try:
            html = self.net.http_GET(web_url,{'referer': web_url}).content
            if host.find('embed')>0: sPattern = "file=(.+?)&"
            else: sPattern = "<file>(.*?)</file>"

            # get stream url
            r = re.search(sPattern, html, re.DOTALL + re.IGNORECASE)
            if r:
                return r.group(1)

            raise Exception ('File Not Found or removed')
        except urllib2.URLError, e:
            common.addon.log_error(self.name + ': got http error %d fetching %s' %
                                   (e.code, web_url))
            common.addon.show_small_popup('Error','Http error: '+str(e), 8000, error_logo)
            return self.unresolvable(code=3, msg=e)
        except Exception, e:
            common.addon.log('**** stream2k Error occured: %s' % e)
            common.addon.show_small_popup(title='[B][COLOR white]STREAM2K[/COLOR][/B]', msg='[COLOR red]%s[/COLOR]' % e, delay=5000, image=error_logo)
            return self.unresolvable(code=0, msg=e)

    def get_url(self, host, media_id):
        if not host.find('embed')>0:
            serverNum = random.randint(2,15)
            url = 'http://server' + str(serverNum) + \
                '.stream2k.com/playerjw/vConfig56.php?vkey=%s' % (media_id)
        else:
            url = "%s%s"%(host,media_id)
            return url

    def get_host_and_id(self, url):
        r = re.search(self.pattern, url)
        if r : return r.groups()
        if not r:
            r = url.split('?')
            return r[0],r[1].replace('s=','?s=')
            
        else:
            
            return False

    def valid_url(self, url, host):
        if self.get_setting('enabled') == 'false': return False
        return re.match(self.pattern, url) or re.match('http://([^/]*stream2k.com)/.+?s=([0-9A-Za-z]+).+?', url) or self.name in host
