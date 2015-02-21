'''
videott urlresolver plugin
Copyright (C) 2015 icharania

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
'''

import os
import xbmc
from t0mm0.common.net import Net
from urlresolver.plugnplay.interfaces import UrlResolver
from urlresolver.plugnplay.interfaces import PluginSettings
from urlresolver.plugnplay import Plugin
import re
import urllib2, urllib
from urlresolver import common

# Custom imports
try:
    from json import loads
except ImportError:
    from simplejson import loads

class VideoTTResolver(Plugin, UrlResolver, PluginSettings):
    implements = [UrlResolver, PluginSettings]
    name = "videott"
    domains = ["video.tt"]

    def __init__(self):
        p = self.get_setting('priority') or 100
        self.priority = int(p)
        self.net = Net()
        self.pattern = 'http://(?:www\.)?(video\.tt)/(?:video\/|embed\/|watch_video\.php\?v=)(\w+)'

    def get_media_url(self, host, media_id):
        json_url = 'http://www.video.tt/player_control/settings.php?v=%s' % media_id

        try:
            json = self.net.http_GET(json_url).content
            data = loads(json)

            vids = data['settings']['res']

            if not vids:
                err_title = 'Content not available.'
                err_message = 'The requested video was not found.'
                common.addon.log_error(self.name + ' - fetching %s - %s - %s ' % (json_url, err_title, err_message))
                return self.unresolvable(1, err_message)

            else:
                vUrlsCount = len(vids)

                if (vUrlsCount > 0):
                    q = self.get_setting('quality')
                    # Lowest Quality
                    li = 0

                    if q == '1':
                        # Medium Quality
                        li = (int)(vUrlsCount / 2)
                    elif q == '2':
                        # Highest Quality
                        li = vUrlsCount - 1

                    vUrl = vids[li]['u'].decode('base-64')
                    return vUrl

        except urllib2.URLError, e:
            return self.unresolvable(3, str(e))
        except Exception, e:
            return self.unresolvable(0, str(e))


    def get_url(self, host, media_id):
        return 'http://www.video.tt/watch_video.php?v=%s' % media_id

    def get_host_and_id(self, url):
        r = re.search(self.pattern, url)
        return r.groups()

    def valid_url(self, url, host):
        if self.get_setting('enabled') == 'false': return False
        return re.match(self.pattern, url) or self.name in host

    #PluginSettings methods
    def get_settings_xml(self):
        xml = PluginSettings.get_settings_xml(self)
        xml += '<setting label="Video Quality" id="%s_quality" ' % self.__class__.__name__
        xml += 'type="enum" values="Low|Medium|High" default="2" />\n'
        return xml
