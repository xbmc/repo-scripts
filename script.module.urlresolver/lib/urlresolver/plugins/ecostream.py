"""
urlresolver XBMC Addon
Copyright (C) 2011 t0mm0

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
import urllib2, os
from urlresolver import common

# Custom imports
import re

#SET ERROR_LOGO# THANKS TO VOINAGE, BSTRDMKR, ELDORADO
error_logo = os.path.join(common.addon_path, 'resources', 'images', 'redx.png')

class EcostreamResolver(Plugin, UrlResolver, PluginSettings):
    implements = [UrlResolver, PluginSettings]
    name = "ecostream"
    profile_path = common.profile_path
    cookie_file = os.path.join(profile_path, 'ecostream.cookies')

    def __init__(self):
        p = self.get_setting('priority') or 100
        self.priority = int(p)
        self.net = Net()
        self.pattern = 'http://((?:www.)?ecostream.tv)/(?:stream|embed)?/([0-9a-zA-Z]+).html'


    def get_media_url(self, host, media_id):
        web_url = self.get_url(host, media_id)
        try:
            html = self.net.http_GET(web_url).content
            if re.search('>File not found!<',html):
                msg = 'File Not Found or removed'
                common.addon.show_small_popup(title='[B][COLOR white]ECOSTREAM[/COLOR][/B]', msg='[COLOR red]%s[/COLOR]'
                % msg, delay=5000, image=error_logo)
                return self.unresolvable(code = 1, msg = msg)
            self.net.save_cookies(self.cookie_file)
            r = re.search("anlytcs='([^']+)'", html)
            if not r:
                raise Exception ('Formvalue not found')
            part1 = r.group(1)
            r = re.search("superslots='([^']+)';", html)
            if not r:
                raise Exception ('Formvalue not found')
            part2 = r.group(1)
            tpm = part1+part2
            # emulate click on button "Start Stream"
            postHeader = ({'Referer':web_url, 'X-Requested-With':'XMLHttpRequest'})
            web_url = 'http://www.ecostream.tv/xhr/video/vidureis'
            self.net.set_cookies(self.cookie_file)
            html = self.net.http_POST(web_url,{'id':media_id, 'tpm':tpm}, headers = postHeader).content
            sPattern = '"url":"([^"]+)"'
            r = re.search(sPattern, html)
            if not r:
                raise Exception ('Unable to resolve Ecostream link. Filelink not found.')
            sLinkToFile = 'http://www.ecostream.tv'+r.group(1)
            return urllib2.unquote(sLinkToFile)

        except urllib2.URLError, e:
            common.addon.log_error(self.name + ': got http error %d fetching %s' %
                                    (e.code, web_url))
            common.addon.show_small_popup('Error','Http error: '+str(e), 8000, error_logo)
            return self.unresolvable(code=3, msg='Exception: %s' % e)
        except Exception, e:
            common.addon.log('**** Ecostream Error occured: %s' % e)
            common.addon.show_small_popup(title='[B][COLOR white]ECOSTREAM[/COLOR][/B]', msg='[COLOR red]%s[/COLOR]'
            % e, delay=5000, image=error_logo)
            return self.unresolvable(code=0, msg='Exception: %s' % e)


    def get_url(self, host, media_id):
            return 'http://www.ecostream.tv/stream/%s.html' % (media_id)

    def get_host_and_id(self, url):
        r = re.search(self.pattern, url.replace('embed','stream'))
        if r:
            return r.groups()
        else:
            return False


    def valid_url(self, url, host):
        if self.get_setting('enabled') == 'false': return False
        return re.match(self.pattern, url) or self.name in host
