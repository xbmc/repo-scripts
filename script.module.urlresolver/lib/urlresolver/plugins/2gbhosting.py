'''
2gbhosting urlresolver plugin
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
import os

class TwogbhostingResolver(Plugin, UrlResolver, PluginSettings):
    implements = [UrlResolver, PluginSettings]
    name = "2gbhosting"


    def __init__(self):
        p = self.get_setting('priority') or 100
        self.priority = int(p)
        self.net = Net()


    def get_media_url(self, host, media_id):
        web_url = self.get_url(host, media_id)
        data = {}
        try:
            html = self.net.http_GET(web_url).content
        except urllib2.URLError, e:
            common.addon.log_error('2gb-hosting: http error %d fetching %s' %
                                    (e.code, web_url))
            return False

        r = re.search('<input type="hidden" name="k" value="(.+?)" />', html)
        if r:
            sid = r.group(1)
            common.addon.log_debug('eg-hosting: found k' + sid)
        else:
            common.addon.log_error('2gb-hosting: Could not find k')
            return False
        try:
            data = { 'k' : sid,'submit' : 'Click Here To Continue', }
            html = self.net.http_POST(web_url, data).content
        except urllib2.URLError, e:
            common.addon.log_error('2gbhosting: got http error %d fetching %s' %
                                    (e.code, web_url))
            return False

        r = re.search('false\|(.+?)\|player\|bekle\|(.+?)\|(.+?)\|skin\|www\|(.+?)\|.+?stretching\|(.+?)\|start\|', html)
        if r:
            url_part4, stream_host, ext, url_part2, url_part1 = r.groups()
            stream_url = 'http://%s.2gb-hosting.com/files/%s/%s/2gb/%s.%s' % (
                             stream_host, url_part1, url_part2, url_part4, ext)
            common.addon.log_debug('2gbhosting: streaming url ' + stream_url)
        else:
            common.addon.log_error('2gbhosting: stream_url not found')
            return False

        return stream_url


    def get_url(self, host, media_id):
        return 'http://www.2gb-hosting.com/videos/%s' % media_id + '.html'
        
        
    def get_host_and_id(self, url):
        r = re.search('//(.+?)/videos/([0-9a-zA-Z/]+)', url)
        if r:
            return r.groups()
        else:
            return False


    def valid_url(self, url, host):
        return (re.match('http://(www.)?2gb-hosting.com/videos/' +
                         '[0-9A-Za-z]+/[0-9a-zA-Z]+.*', url) or
                         '2gb-hosting' in host)
