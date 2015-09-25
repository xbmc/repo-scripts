"""
openload.io urlresolver plugin
Copyright (C) 2015 tknorris

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

from t0mm0.common.net import Net
from urlresolver.plugnplay.interfaces import UrlResolver
from urlresolver.plugnplay.interfaces import PluginSettings
from urlresolver.plugnplay import Plugin
from urlresolver import common
import re
import urllib
from lib import jsunpack

class OpenLoadResolver(Plugin, UrlResolver, PluginSettings):
    implements = [UrlResolver, PluginSettings]
    name = "openload"
    domains = ["openload.io", "openload.co"]

    def __init__(self):
        p = self.get_setting('priority') or 100
        self.priority = int(p)
        self.net = Net()
        self.pattern = '//((?:www.)?openload\.(?:io|co))/(?:embed|f)/([0-9a-zA-Z-_]+)'

    def get_media_url(self, host, media_id):
        web_url = self.get_url(host, media_id)
        html = self.net.http_GET(web_url).content
        if 'We are sorry!' in html:
            raise UrlResolver.ResolverError('File Not Found or Removed.')
        
        stream_url = self.__decode_O(html)
        if stream_url:
            return stream_url + '|User-Agent=%s' % (common.IE_USER_AGENT)
        
        raise UrlResolver.ResolverError('Unable to resolve openload.io link. Filelink not found.')

    def __decode_O(self, html):
        try:
            packed_data = re.search('>\s*(eval\s*\(function.*?)\s*</script>', html, re.DOTALL).group(1)
            new_str = re.search("decodeURIComponent\('(.*?)'\)", packed_data).group(1)
            new_str = urllib.unquote(new_str)
            packed_data = re.sub('decodeURIComponent\(.*?\)', "'%s'" % (new_str), packed_data)
            match = re.search(',\s*\((.*?)\)\.split\([\'"](.*?)[\'"]\)', packed_data)
            if match:
                split_str, delim = match.groups()
                new_split_str = eval(split_str)
                new_split_str = new_split_str.replace(delim, '|')
                packed_data = re.sub(',\s*\(.*?\)\.split\(.*?\)', ", '%s'.split('%s')" % (new_split_str, '|'), packed_data)
            html = jsunpack.unpack(packed_data)
            html = html.replace('\\\\', '\\')
            
            O = {
                '___': 0,
                '$$$$': "f",
                '__$': 1,
                '$_$_': "a",
                '_$_': 2,
                '$_$$': "b",
                '$$_$': "d",
                '_$$': 3,
                '$$$_': "e",
                '$__': 4,
                '$_$': 5,
                '$$__': "c",
                '$$_': 6,
                '$$$': 7,
                '$___': 8,
                '$__$': 9,
                '$_': "constructor",
                '$$': "return",
                '_$': "o",
                '_': "u",
                '__': "t",
            }
            s1 = re.search('o\.\$\(o\.\$\((.*?)\)\(\)\)\(\);', html).group(1)
            s1 = s1.replace(' ', '')
            s1 = s1.replace('(![]+"")', 'false')
            s3 = ''
            for s2 in s1.split('+'):
                if s2.startswith('o.'):
                    s3 += str(O[s2[2:]])
                elif '[' in s2 and ']' in s2:
                    key = s2[s2.find('[') + 3:-1]
                    s3 += s2[O[key]]
                else:
                    s3 += s2[1:-1]
            
            s3 = s3.replace('\\\\', '\\')
            s3 = s3.decode('unicode_escape')
            s3 = s3.replace('\\/', '/')
            s3 = s3.replace('\\\\"', '"')
            s3 = s3.replace('\\"', '"')
            match = re.search('<source.+?src="([^"]+)', s3)
            return match.group(1)
        except Exception as e:
            raise UrlResolver.ResolverError('Decode-O Parsing Failure: %s' % (e))

    def get_url(self, host, media_id):
            return 'http://openload.io/embed/%s' % (media_id)

    def get_host_and_id(self, url):
        r = re.search(self.pattern, url)
        if r:
            return r.groups()
        else:
            return False

    def valid_url(self, url, host):
        return re.search(self.pattern, url) or self.name  in host
