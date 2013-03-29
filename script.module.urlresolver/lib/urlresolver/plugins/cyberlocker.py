'''
Cyberlocker urlresolver plugin
Copyright (C) 2013 Vinnydude

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
import urllib2, xbmcgui
from urlresolver import common
import os
from lib import jsunpack

net = Net()

class CyberlockerResolver(Plugin, UrlResolver, PluginSettings):
    implements = [UrlResolver, PluginSettings]
    name = "cyberlocker"


    def __init__(self):
        p = self.get_setting('priority') or 100
        self.priority = int(p)
        self.net = Net()


    def get_media_url(self, host, media_id):
        print 'Cyberlocker: in get_media_url %s %s' % (host, media_id)
        url = self.get_url(host, media_id)
        html = self.net.http_GET(url).content
        #Show dialog box so user knows something is happening
        dialog = xbmcgui.DialogProgress()
        dialog.create('Resolving', 'Resolving Cyberlocker Link...')       
        dialog.update(0)

        op = 'download1'
        usr_login = ''
        postid = re.search('<input type="hidden" name="id" value="(.+?)">', html).group(1)
        fname = re.search('<input type="hidden" name="fname" value="(.+?)">', html).group(1)
        method_free = re.search('<input disabled style=".+?" type="submit" id="btn_download" name="method_free" value="(.+?)">', html).group(1)
        referer = 'method_free'
        data = {'op': op, 'usr_login': usr_login, 'id': postid, 'fname': fname, 'referer': referer, 'method_free': method_free}
        html = net.http_POST(url, data).content

        dialog.update(50)

        sPattern =  '<script type=(?:"|\')text/javascript(?:"|\')>(eval\('
        sPattern += 'function\(p,a,c,k,e,d\)(?!.+player_ads.+).+np_vid.+?)'
        sPattern += '\s+?</script>'
        r = re.search(sPattern, html, re.DOTALL + re.IGNORECASE)
        if r:
            sJavascript = r.group(1)
            sUnpacked = jsunpack.unpack(sJavascript)
            print(sUnpacked)
            sPattern  = '<embed id="np_vid"type="video/divx"src="(.+?)'
            sPattern += '"custommode='
            r = re.search(sPattern, sUnpacked)
            if r:
                dialog.update(100)
                dialog.close()
                return r.group(1)
        
    def get_url(self, host, media_id):
        return 'http://cyberlocker.ch/%s' % media_id 
        

    def get_host_and_id(self, url):
        r = re.search('//(.+?)/([0-9a-zA-Z]+)',url)
        if r:
            return r.groups()
        else:
            return False
        return('host', 'media_id')


    def valid_url(self, url, host):
        if self.get_setting('enabled') == 'false': return False
        return (re.match('http://(www.)?cyberlocker.ch/' +
                         '[0-9A-Za-z]+', url) or
                         'cyberlocker' in host)
