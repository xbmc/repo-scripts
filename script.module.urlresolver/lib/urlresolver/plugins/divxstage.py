'''
divxstage urlresolver plugin
Copyright (C) 2011 t0mm0, DragonWin

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

from t0mm0.common.net import Net
from urlresolver.plugnplay.interfaces import UrlResolver
from urlresolver.plugnplay.interfaces import PluginSettings
from urlresolver.plugnplay import Plugin
import re
import urllib2
from urlresolver import common

class DivxstageResolver(Plugin, UrlResolver, PluginSettings):
    implements = [UrlResolver, PluginSettings]
    name = "divxstage"

    def __init__(self):
        p = self.get_setting('priority') or 100
        self.priority = int(p)
        self.net = Net()


    def get_media_url(self, host, media_id):
        web_url = self.get_url(host, media_id)
        try:
            html = self.net.http_GET(web_url).content
        except urllib2.URLError, e:
            common.addon.log_error('Divxstage: got http error %d fetching %s' %
                                   (e.code, web_url))
            return False

        r = re.search('<param name="src" value="(.+?)"', html)
        if r:
            stream_url = r.group(1)
        else:
            message ='Divxstage: 1st attempt at finding the stream_url failed'
            common.addon.log_debug(message)
            r = re.search('flashvars.filekey="(.+)"', html)
            if r:
                file_key = r.group(1)
                player_url = 'http://'+host+'/api/player.api.php?user=undefined&key='+file_key+'&pass=undefined&codes=1&file='+media_id
                try:
                    html = self.net.http_GET(player_url).content
                except urllib2.URLError, e:
                    common.addon.log_error('Divxstage: got http error %d fetching %s' %
                                        (e.code, web_url))
                    return False
                r = re.search('url=(.+?)&', html)
                if r:
                    stream_url = r.group(1)
                else:
                    message ='Divxstage: attempt at finding the stream_url failed'
                    common.addon.log_debug(message)
                    return False
            else:
                message ='Divxstage: attempt at finding the filekey failed'
                common.addon.log_debug(message)
                return False
        return stream_url


    def get_url(self, host, media_id):
        print 'http://www.divxstage.eu/video/%s' % media_id
        return 'http://www.divxstage.eu/video/%s' % media_id
        
        
        
        
    def get_host_and_id(self, url):
        r = re.search('//(.+?)/(?:video/([0-9a-z]+)|embed.php\?v=([0-9a-z]+)&width)', url)
        if r and 'embed' in r.group(1):
            return r.group(1),r.group(3)
        else:
            return r.group(1),r.group(2)
        if not r:
            return False


    def valid_url(self, url, host):
        #http://embed.divxstage.eu/embed.php?v=8da26363e05fd&width=746&height=388&c=000
        return re.match('http://(?:www.|embed.)?divxstage.(?:eu|net)/' or 'divxstage' in host,url)
