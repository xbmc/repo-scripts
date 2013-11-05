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

import re, urllib2, os
from t0mm0.common.net import Net
from urlresolver import common
from urlresolver.plugnplay.interfaces import UrlResolver
from urlresolver.plugnplay.interfaces import PluginSettings
from urlresolver.plugnplay import Plugin
from vidxden import unpack_js

#SET ERROR_LOGO# THANKS TO VOINAGE, BSTRDMKR, ELDORADO
error_logo = os.path.join(common.addon_path, 'resources', 'images', 'redx.png')

class vidpeResolver(Plugin, UrlResolver, PluginSettings):
    implements = [UrlResolver, PluginSettings]

    def __init__(self):
        p = self.get_setting('priority') or 100
        self.net = Net()
        self.priority = int(p)

    def get_media_url(self, host, media_id):
        web_url = self.get_url(host, media_id)
        try:
            html = self.net.http_GET(web_url).content

            page = ''.join(html.splitlines()).replace('\t','')
            r = re.search("return p\}\(\'(.+?)\',\d+,\d+,\'(.+?)\'", page)
            if r:
                p, k = r.groups()
            else:
                raise Exception ('packed javascript embed code not found')

            decrypted_data = unpack_js(p, k)
            r = re.search('file.\',.\'(.+?).\'', decrypted_data)
            if not r:
                r = re.search('src="(.+?)"', decrypted_data)
            if r:
                stream_url = r.group(1)
            else:
                raise Exception ('File Not Found or removed')

            return stream_url

        except urllib2.URLError, e:
            common.addon.log_error(self.name + ': got http error %d fetching %s' %
                                   (e.code, web_url))
            common.addon.show_small_popup('Error','Http error: '+str(e), 8000, error_logo)
            return self.unresolvable(code=3, msg=e)
        except Exception, e:
            common.addon.log('**** Vidpe Error occured: %s' % e)
            common.addon.show_small_popup(title='[B][COLOR white]VIDPE[/COLOR][/B]', msg='[COLOR red]%s[/COLOR]' % e, delay=5000, image=error_logo)
            return self.unresolvable(code=0, msg=e)


    def get_url(self, host, media_id):
        if 'vidpe' in host or 'hostingcup' in host:
            return 'http://'+host+'/%s.html' % media_id
        else:
            return 'http://'+host+'/%s' % media_id


    def get_host_and_id(self, url):
        r = re.search('http://(.+?)/embed-([\w]+)-', url)
        if r:
            return r.groups()
        else:
            r = re.search('http://(.+?)/embed-([\w]+).html', url)
            if r:
                return r.groups()
            else:
                r = re.search('//(.+?)/([\w]+)', url)
                if r:
                    return r.groups()
                else:
                    return False


    def get_domain(self, url):
        tmp = re.compile('//(.+?)/').findall(url)
        if len(tmp) == 0:
            return False
        domain = tmp[0].replace('www.', '')
        return domain

    def valid_url(self, url, host):
        if self.get_setting('enabled') == 'false': return False
        return re.search('http://(.+)?(vidpe|hostingcup).com/.+?.html',url) or 'vidpe' in host or 'hostingcup' in host

    def get_settings_xml(self):
        xml = PluginSettings.get_settings_xml(self)
        xml += '<setting label="This plugin calls the vidpe addon - '
        xml += 'change settings there." type="lsep" />\n'
        return xml
