# -*- coding: utf-8 -*-

"""
VKPass urlresolver XBMC Addon based on VKResolver
Copyright (C) 2015 Seberoth
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
import xbmcgui
from t0mm0.common.net import Net
from urlresolver.plugnplay.interfaces import UrlResolver
from urlresolver.plugnplay.interfaces import PluginSettings
from urlresolver.plugnplay import Plugin
from urlresolver import common

class VKPassResolver(Plugin, UrlResolver, PluginSettings):
    implements = [UrlResolver, PluginSettings]
    name = "VKPass.com"
    domains = ["vkpass.com"]

    def __init__(self):
        p = self.get_setting('priority') or 100
        self.priority = int(p)
        self.net = Net()
        self.pattern = '//((?:www.)?vkpass.com)/token/(.+)'

    def get_media_url(self, host, media_id):
        base_url = self.get_url(host, media_id)
        soup = self.net.http_GET(base_url).content
        html = soup.decode('cp1251')
        vBlocks = re.findall('{(file.*?label.*?)}', html)

        if vBlocks:
            purged_jsonvars = {}
            lines = []
            best = '0'

            for block in vBlocks:
                vItems = re.findall('([a-z]*):"(.*?)"', block)
                if vItems:
                    quality = ''
                    url = ''

                    for item in vItems:
                        if 'file' in item[0]:
                            url = item[1]
                        if 'label' in item[0]:
                            quality = re.sub("[^0-9]", "", item[1])
                            lines.append(quality)
                            if int(quality) > int(best): best = quality

                    purged_jsonvars[quality] = url
                else:
                    raise UrlResolver.ResolverError('No file found')

            lines = sorted(lines, key=int)

            if len(lines) == 1:
                return purged_jsonvars[lines[0]].encode('utf-8')
            else:
                if self.get_setting('auto_pick') == 'true':
                    return purged_jsonvars[str(best)].encode('utf-8') + '|User-Agent=%s' % (common.IE_USER_AGENT)
                else:
                    result = xbmcgui.Dialog().select('Choose the link', lines)
            if result != -1:
                return purged_jsonvars[lines[result]].encode('utf-8') + '|User-Agent=%s' % (common.IE_USER_AGENT)
            else:
                raise UrlResolver.ResolverError('No link selected')
        else:
            raise UrlResolver.ResolverError('No vsource found')

    def get_url(self, host, media_id):
        return 'http://%s/token/%s' % (host, media_id)

    def get_host_and_id(self, url):
        r = re.search(self.pattern, url)
        if r:
            return r.groups()
        else:
            return False

    def valid_url(self, url, host):
        if self.get_setting('enabled') == 'false':
            return False
        return re.search(self.pattern, url) or 'vkpass' in host

    def get_settings_xml(self):
        xml = PluginSettings.get_settings_xml(self)
        xml += '<setting id="%s_auto_pick" type="bool" label="Automatically pick best quality" default="false" visible="true"/>' % (self.__class__.__name__)
        return xml
