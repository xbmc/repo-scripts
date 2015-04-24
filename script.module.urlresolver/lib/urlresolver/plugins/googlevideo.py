"""
    Kodi urlresolver plugin
    Copyright (C) 2014  smokdpi

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
from urlresolver import common
from urlresolver.plugnplay import Plugin
from urlresolver.plugnplay.interfaces import UrlResolver
from urlresolver.plugnplay.interfaces import PluginSettings
import re
import urllib2
import xbmcgui


class GoogleResolver(Plugin, UrlResolver, PluginSettings):
    implements = [UrlResolver, PluginSettings]
    name = "googlevideo"
    domains = ["googlevideo.com", "picasaweb.google.com"]

    def __init__(self):
        p = self.get_setting('priority') or 100
        self.priority = int(p)
        self.net = Net()
        self.pattern = 'http[s]*://(.*?(?:\.googlevideo|picasaweb\.google)\.com)/(.*?(?:videoplayback\?|\?authkey).+)'

    def get_url(self, host, media_id):
        return 'https://%s/%s' % (host, media_id)

    def get_host_and_id(self, url):
        r = re.search(self.pattern, url)
        if r: return r.groups()
        else: return False

    def valid_url(self, url, host):
        if self.get_setting('enabled') == 'false': return False
        return re.match(self.pattern, url)

    def get_media_url(self, host, media_id):
        web_url = self.get_url(host, media_id)
        headers = {'Referer': web_url}
        stream_url = ''
        vid_sel = web_url
        if 'picasaweb.' in host:
            vid_sel = ''
            vid_id = re.search('.*?#(.+?)$', web_url)
            if vid_id:
                vid_id = vid_id.group(1)
                resp = self.net.http_GET(web_url, headers=headers)
                html = re.search('\["shared_group_' + re.escape(vid_id) + '"\](.+?),"ccOverride":"false"}', resp.content, re.DOTALL)
                if html:
                    videos = re.compile(',{"url":"(https://redirector\.googlevideo\.com/.+?)","height":([0-9]+?),"width":([0-9]+?),"type":"video/.+?"}').findall(html.group(1))
                    vid_list = []
                    url_list = []
                    best = 0
                    quality = 0
                    if videos:
                        if len(videos) > 1:
                            for index, video in enumerate(videos):
                                if int(video[1]) > quality: best = index
                                quality = int(video[1])
                                vid_list.extend(['GoogleVideo - %sp' % quality])
                                url_list.extend([video[0]])
                        if len(videos) == 1: vid_sel = videos[0][0]
                        else:
                            if self.get_setting('auto_pick') == 'true': vid_sel = url_list[best]
                            else:
                                result = xbmcgui.Dialog().select('Choose a link', vid_list)
                                if result != -1: vid_sel = url_list[result]
                                else:
                                    raise UrlResolver.ResolverError('No link selected')
        if vid_sel:
            if 'redirector.' in vid_sel: stream_url = urllib2.urlopen(vid_sel).geturl()
            elif 'google' in vid_sel: stream_url = vid_sel
            if stream_url: return stream_url

        raise UrlResolver.ResolverError('File not found')

    def get_settings_xml(self):
        xml = PluginSettings.get_settings_xml(self)
        xml += '<setting id="%s_auto_pick" type="bool" label="Automatically pick best quality" default="false" visible="true"/>' % (self.__class__.__name__)
        return xml
