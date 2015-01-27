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

import os
import xbmc
from t0mm0.common.net import Net
from urlresolver.plugnplay.interfaces import UrlResolver
from urlresolver.plugnplay.interfaces import PluginSettings
from urlresolver.plugnplay import Plugin
import re
import urllib2
from urlresolver import common

logo = os.path.join(common.addon_path, 'resources', 'images', 'redx.png')

class VshareResolver(Plugin, UrlResolver, PluginSettings):
    implements=[UrlResolver,PluginSettings]
    name="vshare"

    def __init__(self):
        p=self.get_setting('priority') or 100
        self.priority=int(p)
        self.net=Net()
        self.pattern='http://((?:www.)?vshare.io)/\w?/(\w+)(?:\/width-\d+/height-\d+/)?'
    
    def get_url(self,host,media_id): 
        return 'http://vshare.io/v/%s/width-620/height-280/' % (media_id)

    def get_host_and_id(self,url):
        r=re.search(self.pattern,url)
        if r: return r.groups()
        else: return False

    def valid_url(self,url,host):
        if self.get_setting('enabled')=='false': return False
        return re.match(self.pattern,url) or self.name in host

    def get_media_url(self,host,media_id):
        try:
            web_url = self.get_url(host, media_id)
            link = self.net.http_GET(web_url).content

            if link.find('404 - Error') >= 0:
                err_title = 'Content not available.'
                err_message = 'The requested video was not found.'
                common.addon.log_error(self.name + ' - fetching %s - %s - %s ' % (web_url,err_title,err_message))
                xbmc.executebuiltin('XBMC.Notification([B][COLOR white]'+__name__+'[/COLOR][/B] - '+err_title+',[COLOR red]'+err_message+'[/COLOR],8000,'+logo+')')
                return self.unresolvable(1, err_message)

            video_link = str(re.compile("url[: ]*'(.+?)'").findall(link)[0])

            if len(video_link) > 0:
                return video_link
            else:
                return self.unresolvable(0, 'No playable video found.')
        except urllib2.URLError, e:
            return self.unresolvable(3, str(e))
        except Exception, e:
            return self.unresolvable(0, str(e))
