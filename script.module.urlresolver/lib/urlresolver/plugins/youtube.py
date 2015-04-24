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
from urlresolver import common
from urlresolver.plugnplay.interfaces import UrlResolver
from urlresolver.plugnplay.interfaces import PluginSettings
from urlresolver.plugnplay import Plugin

class YoutubeResolver(Plugin, UrlResolver, PluginSettings):
    implements = [UrlResolver, PluginSettings]
    name = "youtube"
    domains = [ 'youtube.com', 'youtu.be' ]

    def __init__(self):
        p = self.get_setting('priority') or 100
        self.priority = int(p)

    def get_media_url(self, host, media_id):
        #just call youtube addon
        plugin = 'plugin://plugin.video.youtube/?action=play_video&videoid=' + media_id
        return plugin

    def get_url(self, host, media_id):
        return 'http://youtube.com/watch?v=%s' % media_id

    def get_host_and_id(self, url):
        if url.find('?') > -1:
            queries = common.addon.parse_query(url.split('?')[1])
            video_id = queries.get('v', None)
        else:
            r = re.findall('/([0-9A-Za-z_\-]+)', url)
            if r:
                video_id = r[-1]
        if video_id:
            return ('youtube.com', video_id)
        else:
            return False

    def valid_url(self, url, host):
        if self.get_setting('enabled') == 'false': return False
        return re.match('http[s]*://(((www.|m.)?youtube.+?(v|embed)(=|/))|' +
                        'youtu.be/)[0-9A-Za-z_\-]+', 
                        url) or 'youtube' in host or 'youtu.be' in host

    def get_settings_xml(self):
        xml = PluginSettings.get_settings_xml(self)
        xml += '<setting label="This plugin calls the youtube addon - '
        xml += 'change settings there." type="lsep" />\n'
        return xml
