"""
mrfile urlresolver plugin
Copyright (C) 2014 Lynx187

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
import urllib2
from urlresolver import common
import re
import os

error_logo = os.path.join(common.addon_path, 'resources', 'images', 'redx.png')

class mrfileResolver(Plugin, UrlResolver, PluginSettings):
    implements = [UrlResolver, PluginSettings]
    name = "mrfile"

    def __init__(self):
        p = self.get_setting('priority') or 100
        self.priority = int(p)
        self.net = Net()

    def get_media_url(self, host, media_id):
        web_url = self.get_url(host, media_id)
        try:
            html = self.net.http_GET(web_url).content
            if re.search('File was deleted',html):
                raise Exception ('File Not Found or removed')
            r = re.search("file: '([^']+)'",html)
            if not r:
                raise Exception ('Unable to resolve mrfile link. Filelink not found.')
            return r.group(1)
        
        except urllib2.URLError, e:
            common.addon.log_error(self.name + ': got http error %d fetching %s' %
                                    (e.code, web_url))
            common.addon.show_small_popup('Error','Http error: '+str(e), 8000, error_logo)
            return self.unresolvable(code=3, msg='Exception: %s' % e) 
        except Exception, e:
            common.addon.log('**** mrfile Error occured: %s' % e)
            common.addon.show_small_popup(title='[B][COLOR white]mrfile[/COLOR][/B]', msg='[COLOR red]%s[/COLOR]' 
            % e, delay=5000, image=error_logo)
            return self.unresolvable(code=0, msg='Exception: %s' % e)

    def get_url(self, host, media_id):
            return 'http://www.mrfile.me/embed-%s.html' % (media_id)

    def get_host_and_id(self, url):
        r = re.search('http://(?:www.)?(.+?)/embed-([\w]+)-', url)
        if r:
            return r.groups()
        else:
            r = re.search('//(.+?)/([\w]+)', url)
            if r:
                return r.groups()
            else:
                return False


    def valid_url(self, url, host):
        return re.match('http://(www.)?mrfile.me/[0-9A-Za-z]+', url) or 'mrfile' in host


