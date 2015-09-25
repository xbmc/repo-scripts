'''
dailymotion urlresolver plugin
Copyright (C) 2011 cyrus007

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
import xbmc
from t0mm0.common.net import Net
from urlresolver.plugnplay.interfaces import UrlResolver
from urlresolver.plugnplay.interfaces import PluginSettings
from urlresolver.plugnplay import Plugin
import re
import urllib2, urllib
from urlresolver import common

class DailymotionResolver(Plugin, UrlResolver, PluginSettings):
    implements = [UrlResolver, PluginSettings]
    name = "dailymotion"
    domains = [ "dailymotion.com" ]

    def __init__(self):
        p = self.get_setting('priority') or 100
        self.priority = int(p)
        self.net = Net()

    def get_media_url(self, host, media_id):
        web_url = self.get_url(host, media_id)
        link = self.net.http_GET(web_url).content
        if link.find('"error":') >= 0:
            err_title = re.compile('"title":"(.+?)"').findall(link)[0]
            if not err_title:
                err_title = 'Content not available.'
            
            err_message = re.compile('"message":"(.+?)"').findall(link)[0]
            if not err_message:
                err_message = 'No such video or the video has been removed due to copyright infringement issues.'
            
            raise UrlResolver.ResolverError(err_message)
                
        dm_live = re.compile('live_rtsp_url":"(.+?)"', re.DOTALL).findall(link)
        dm_1080p = re.compile('"1080":.+?"url":"(.+?)"', re.DOTALL).findall(link)
        dm_720p = re.compile('"720":.+?"url":"(.+?)"', re.DOTALL).findall(link)
        dm_high = re.compile('"480":.+?"url":"(.+?)"', re.DOTALL).findall(link)
        dm_low = re.compile('"380":.+?"url":"(.+?)"', re.DOTALL).findall(link)
        dm_low2 = re.compile('"240":.+?"url":"(.+?)"', re.DOTALL).findall(link)
                
        videoUrl = []
        
        if dm_live:
            liveVideoUrl = urllib.unquote_plus(dm_live[0]).replace("\\/", "/")
            liveVideoUrl = liveVideoUrl.replace("protocol=rtsp", "protocol=rtmp")
            liveVideoUrl = self.net.http_GET(liveVideoUrl).content
            videoUrl.append(liveVideoUrl)
        else:
            if dm_1080p:
                videoUrl.append(urllib.unquote_plus(dm_1080p[0]).replace("\\/", "/"))
            if dm_720p:
                videoUrl.append(urllib.unquote_plus(dm_720p[0]).replace("\\/", "/"))
            if dm_high:
                videoUrl.append(urllib.unquote_plus(dm_high[0]).replace("\\/", "/"))
            if dm_low:
                videoUrl.append(urllib.unquote_plus(dm_low[0]).replace("\\/", "/"))
            if dm_low2:
                videoUrl.append(urllib.unquote_plus(dm_low2[0]).replace("\\/", "/"))
        
        vUrl = ''
        vUrlsCount = len(videoUrl)
        if vUrlsCount > 0:
            q = self.get_setting('quality')
            if q == '0':
                # Highest Quality
                vUrl = videoUrl[0]
            elif q == '1':
                # Medium Quality
                vUrl = videoUrl[(int)(vUrlsCount / 2)]
            elif q == '2':
                # Lowest Quality
                vUrl = videoUrl[vUrlsCount - 1]
        
        common.addon.log('url:' + vUrl)
        return vUrl

    def get_url(self, host, media_id):
        return 'http://www.dailymotion.com/embed/video/%s' % media_id
        
    def get_host_and_id(self, url):
        r = re.search('//(.+?)/embed/video/([0-9A-Za-z]+)', url)
        if r:
            return r.groups()
        else:
            r = re.search('//(.+?)/swf/video/([0-9A-Za-z]+)', url)
            if r:
                return r.groups()
            else:
                r = re.search('//(.+?)/video/([0-9A-Za-z]+)', url)
                if r:
                    return r.groups()
                else:
                    r = re.search('//(.+?)/swf/([0-9A-Za-z]+)', url)
                    if r:
                        return r.groups()
                    else:
                        r = re.search('//(.+?)/sequence/([0-9A-Za-z]+)', url)
                        if r:
                            return r.groups()
                        else:
                            return False


    def valid_url(self, url, host):
        if self.get_setting('enabled') == 'false': return False
        return re.match('http://(www.)?dailymotion.com/sequence/[0-9A-Za-z]+', url) or \
                re.match('http://(www.)?dailymotion.com/video/[0-9A-Za-z]+', url) or \
                re.match('http://(www.)?dailymotion.com/swf/[0-9A-Za-z]+', url) or \
                re.match('http://(www.)?dailymotion.com/embed/[0-9A-Za-z]+', url) or \
                self.name in host

    #PluginSettings methods
    def get_settings_xml(self):
        xml = PluginSettings.get_settings_xml(self)
        xml += '<setting label="Video Quality" id="%s_quality" ' % self.__class__.__name__
        xml += 'type="enum" values="High|Medium|Low" default="0" />\n'
        return xml
