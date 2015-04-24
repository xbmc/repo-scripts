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
import urllib, urllib2
from urlresolver import common
import re

class YourUploadResolver(Plugin, UrlResolver, PluginSettings):
    implements = [UrlResolver, PluginSettings]
    name = "yourupload.com"
    domains = [ "yourupload.com" ]

    def __init__(self):
        p = self.get_setting('priority') or 100
        self.priority = int(p)
        self.net = Net()
        # http://yourupload.com/embed/a67563063236469c65a94a1dfbbb129b&width=718&height=438
        # http://yourupload.com/embed_ext/videoweed/4f4d574ed3266&width=718&height=438
        # http://embed.yourupload.com/2o6B1y?client_file_id=380101&width=600&height=438
        self.pattern = 'http://((?:www.)?yourupload.com)/embed/([0-9a-zA-Z]+)[\?&]*'
        self.pattern2 = 'http://((?:www.)?yourupload.com)/embed_ext/[0-9A-Za-z]+/([0-9a-zA-Z]+)[\?&]*'
        # self.pattern3 = 'http://embed.(yourupload.com)/([0-9a-zA-Z]+\?.*?client_file_id=[0-9a-zA-Z]+)[&]*'
        # self.pattern3 = 'http://((?:embed.)?yourupload.com)/(.+?client_file_id.+?)'
        self.pattern3 = 'http://embed.(yourupload.com)/(.+?)'
        # self.pattern = 'http://((?:www.)?yourupload.com)/embed/(.+?)'

    def get_url(self, host, media_id):
            common.addon.log(host + ' - media_id: %s' % media_id)
            if len(media_id) > 5: common.addon.log_notice('1st 4 digits:  ' + media_id[:4])
            if media_id[:4] == 'ext_':
                common.addon.log_notice(media_id[4:] + ':  media_id is for an external video source')
                return 'http://yourupload.com/embed_ext/videoweed/%s' % (media_id[4:])
            elif ('___' in media_id):
                r = media_id.split('___')[0]
                s = media_id.split('___')[1]
                common.addon.log_notice(media_id + ':  media_id is for 2 ID types')
                return 'http://embed.yourupload.com/%s?client_file_id=%s' % (r, s)
            elif ('client_file_id' in media_id):
                common.addon.log_notice(media_id + ':  media_id is for 2 ID types')
                return 'http://embed.yourupload.com/%s' % (media_id)
            elif ('=' in media_id) or ('&' in media_id) or ('?' in media_id) or ('client' in media_id):
                common.addon.log_notice(media_id + ':  media_id is for 2 ID types')
                return 'http://embed.yourupload.com/%s' % (media_id)
            else: return 'http://yourupload.com/embed/%s' % (media_id)

    def get_host_and_id(self, url):
        common.addon.log_notice('get host and id from: %s' % url)
        if 'yourupload.com/embed_ext' in url: r = re.search(self.pattern2, url); s = 'ext_'
        elif ('embed.yourupload.com' in url):
            r = re.search('/([0-9a-zA-Z]+)\?', url).group(1)
            s = re.search('client_file_id=([0-9a-zA-Z]+)', url).group(1)
            return [r + '___' + s, 'embed.yourupload.com']
        elif ('embed.yourupload.com/' in url):
            r = url.split('yourupload.com/')[1]; s = ''
            return [r, 'embed.yourupload.com']
        elif ('embed.yourupload.com' in url): r = re.search(self.pattern3, url); s = ''
        else: r = re.search(self.pattern, url); s = ''
        # if r: return s+r.groups()
        if r: return [r.group(1), s + r.group(2)]
        else:
            common.addon.log_notice('failed to get host and id: %s' % url)
            # return 'failed to get host and id: %s'
            return False

    def valid_url(self, url, host):
        if self.get_setting('enabled') == 'false': return False
        elif ('yourupload.com' in url) or ('yourupload.com' in host): return True
        elif ('yourupload.com' in url) and ('embed' in url): return True
        elif 'yourupload.com/embed' in url: return True
        elif 'embed.yourupload.com' in url: return True
        elif 'yourupload.com/embed_ext/' in url: return re.match(self.pattern2, url) or self.name in host
        elif ('http://embed.yourupload.com/' in url) and ('client_file_id' in url): return re.match(self.pattern3, url) or self.name in host
        else: return re.match(self.pattern, url) or self.name in host

    def get_media_url(self, host, media_id):
        web_url = self.get_url(host, media_id)
        resp = self.net.http_GET(web_url)
        html = resp.content
        r = re.search('<meta property="og:video" content="(.+?)"', html)
        if not r:
            r = re.search('<source src="(.+?)"', html)
            if not r:
                r = re.search("'file'\s*:\s*'(.+?)'", html)
        if r:
            return r.group(1)
        else:
            raise UrlResolver.ResolverError('no file located')
