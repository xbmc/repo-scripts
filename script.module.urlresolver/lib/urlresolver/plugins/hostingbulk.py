"""
    urlresolver XBMC Addon
    Copyright (C) 2011 anilkuj

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
import urllib2
from urlresolver import common
from urlresolver.plugnplay.interfaces import UrlResolver
from urlresolver.plugnplay.interfaces import PluginSettings
from urlresolver.plugnplay import Plugin

class hostingbulkResolver(Plugin, UrlResolver, PluginSettings):
    implements = [UrlResolver, PluginSettings]

    def __init__(self):
        p = self.get_setting('priority') or 100
        self.priority = int(p)

    def get_media_url(self, host, media_id):
        
        print 'host %s media_id %s' %(host, media_id)
        html = net.http_GET("http://www.hostingbulk.com/" + media_id + ".html").content
        m = re.match('addParam|(?P<port>)|(?P<ip4>)|(?P<ip3>)|(?P<ip2>)|(?P<ip1>).+?video|(?P<file>)|',html)
	if (len(m) > 0 ):
            videoLink = 'http://'+m.group("ip1")+'.'+m.group("ip2")+'.'+m.group("ip3")+'.'+m.group("ip4")+':'+m.group("port")+'/d/'+m.group("file")+'/video.flv?start=0'
            print 'video id is %' % videoLink
            return videoLink

        print 'could not obtain video url'
        return False


    def get_url(self, host, media_id):
        return 'http://hostingbulk.com/%s' % media_id


    def get_host_and_id(self, url):
        r = None
        video_id = None
        
        if re.search('embed-', url):
            r = re.compile('embed-(.+?).html').findall(url)
        elif re.search('watch/', url):
            r = re.compile('.com/(.+?).html').findall(url)
            
        if r is not None and len(r) > 0:
            video_id = r[0]
            
        if video_id:
            return ('hostingbulk.com', video_id)
        else:
            common.addon.log_error('hostingbulk: video id not found')
            return False

    def valid_url(self, url, host):
        #return re.match('http://(.+)?hostingbulk.com/[0-9]+', url) or 'hostingbulk' in host
        return False

    def get_settings_xml(self):
        xml = PluginSettings.get_settings_xml(self)
        xml += '<setting label="This plugin calls the hostingbulk addon - '
        xml += 'change settings there." type="lsep" />\n'
        return xml
