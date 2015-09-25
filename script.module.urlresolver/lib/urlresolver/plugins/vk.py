"""
VK urlresolver XBMC Addon
Copyright (C) 2015 tknorris

Version 0.0.1 

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
import re
import urlparse
import json
import xbmcgui
from t0mm0.common.net import Net
from urlresolver.plugnplay.interfaces import UrlResolver
from urlresolver.plugnplay.interfaces import PluginSettings
from urlresolver.plugnplay import Plugin
from urlresolver import common

class VKResolver(Plugin, UrlResolver, PluginSettings):
    implements = [UrlResolver, PluginSettings]
    name = "VK.com"
    domains = ["vk.com"]

    def __init__(self):
        p = self.get_setting('priority') or 100
        self.priority = int(p)
        self.net = Net()
        self.pattern = '//((?:www\.)?vk\.com)/video_ext\.php\?(.+)'

    def get_media_url(self, host, media_id):
        web_url = self.get_url(host, media_id)
        query = web_url.split('?', 1)[-1]
        query = urlparse.parse_qs(query)
        api_url = 'http://api.vk.com/method/video.getEmbed?oid=%s&video_id=%s&embed_hash=%s' % (query['oid'][0], query['id'][0], query['hash'][0])
        html = self.net.http_GET(api_url).content
        html = re.sub(r'[^\x00-\x7F]+', ' ', html)
        
        try: result = json.loads(html)['response']
        except: result = self.__get_private(query['oid'][0], query['id'][0])
        
        quality_list = []
        link_list = []
        best_link = ''
        for quality in ['url240', 'url360', 'url480', 'url540', 'url720']:
            if quality in result:
                quality_list.append(quality[3:])
                link_list.append(result[quality])
                best_link = result[quality]
        
        if self.get_setting('auto_pick') == 'true' and best_link:
            return best_link + '|User-Agent=%s' % (common.IE_USER_AGENT)
        else:
            if quality_list:
                if len(quality_list) > 1:
                    result = xbmcgui.Dialog().select('Choose the link', quality_list)
                    if result == -1:
                        raise UrlResolver.ResolverError('No link selected')
                    else:
                        return link_list[result] + '|User-Agent=%s' % (common.IE_USER_AGENT)
                else:
                    return link_list[0] + '|User-Agent=%s' % (common.IE_USER_AGENT)
        
        raise UrlResolver.ResolverError('No video found')

    def __get_private(self, oid, video_id):
        private_url = 'http://vk.com/al_video.php?act=show_inline&al=1&video=%s_%s' % (oid, video_id)
        html = self.net.http_GET(private_url).content
        html = re.sub(r'[^\x00-\x7F]+', ' ', html)
        match = re.search('var\s+vars\s*=\s*({.+?});', html)
        try: return json.loads(match.group(1))
        except: return {}
        return {}
    
    def get_url(self, host, media_id):
        return 'http://%s.com/video_ext.php?%s' % (host, media_id)

    def get_host_and_id(self, url):
        r = re.search(self.pattern, url)
        if r:
            return r.groups()
        else:
            return False

    def valid_url(self, url, host):
        if self.get_setting('enabled') == 'false':
            return False
        return re.search(self.pattern, url) or 'vk' in host

    def get_settings_xml(self):
        xml = PluginSettings.get_settings_xml(self)
        xml += '<setting id="%s_auto_pick" type="bool" label="Automatically pick best quality" default="false" visible="true"/>' % (self.__class__.__name__)
        return xml
