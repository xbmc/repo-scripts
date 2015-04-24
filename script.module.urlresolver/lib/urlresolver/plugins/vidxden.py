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

"""
RogerThis - 16/8/2011
Site: http://www.vidxden.com , http://www.divxden.com & http://www.vidbux.com
vidxden hosts both avi and flv videos
In testing there seems to be a timing issue with files coming up as not playable.
This happens on both the addon and in a browser.
"""
import socket
import re
from t0mm0.common.net import Net
from urlresolver import common
from urlresolver.plugnplay.interfaces import UrlResolver
from urlresolver.plugnplay.interfaces import PluginSettings
from urlresolver.plugnplay import Plugin
from lib import captcha_lib
from lib import jsunpack

# SET DEFAULT TIMEOUT FOR SLOW SERVERS:
socket.setdefaulttimeout(30)

class VidxdenResolver(Plugin, UrlResolver, PluginSettings):
    implements = [UrlResolver, PluginSettings]
    name = "vidxden"
    domains = ['vidxden.com', 'vidxden.to', 'divxden.com', 'vidbux.com', 'vidbux.to']

    def __init__(self):
        p = self.get_setting('priority') or 100
        self.priority = int(p)
        self.net = Net()

    def get_media_url(self, host, media_id):
        web_url = self.get_url(host, media_id)
        resp = self.net.http_GET(web_url)
        html = resp.content
        if "No such file or the file has been removed due to copyright infringement issues." in html:
            raise UrlResolver.ResolverError('File Not Found or removed')

        filename = re.compile('<input name="fname" type="hidden" value="(.+?)">').findall(html)[0]
        data = {'op': 'download1', 'method_free': '1', 'usr_login': '', 'id': media_id, 'fname': filename}
        data.update(captcha_lib.do_captcha(html))
        html = self.net.http_POST(resp.get_url(), data).content

        # find packed javascript embed code
        r = re.search('(eval.*?)\s*</script>', html, re.DOTALL)
        if r:
            packed_data = r.group(1)
        else:
            raise UrlResolver.ResolverError('packed javascript embed code not found')

        try: decrypted_data = jsunpack.unpack(packed_data)
        except: pass
        decrypted_data = decrypted_data.replace('\\', '')
        # First checks for a flv url, then the if statement is for the avi url
        r = re.search('[\'"]file[\'"]\s*,\s*[\'"]([^\'"]+)', decrypted_data)
        if not r:
            r = re.search('src="(.+?)"', decrypted_data)
        if r:
            stream_url = r.group(1)
        else:
            raise UrlResolver.ResolverError('stream url not found')

        return stream_url

    def get_url(self, host, media_id):
        if 'vidbux' in host:
            host = 'www.vidbux.com'
        else:
            host = 'www.vidxden.com'
        return 'http://%s/%s' % (host, media_id)

    def get_host_and_id(self, url):
        r = re.search('//(.+?)/(?:embed-)?([0-9a-z]+)', url)
        if r:
            return r.groups()
        else:
            return False

    def valid_url(self, url, host):
        if self.get_setting('enabled') == 'false': return False
        return (re.match('http://(?:www.)?(vidxden|divxden|vidbux).(com|to)/' +
                         '(embed-)?[0-9a-z]+', url) or
                'vidxden' in host or 'divxden' in host or
                'vidbux' in host)
