"""
TheFile.me urlresolver plugin
Copyright (C) 2013 voinage

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
import re
from lib import jsunpack

#SET ERROR_LOGO# THANKS TO VOINAGE, BSTRDMKR, ELDORADO
error_logo = os.path.join(common.addon_path, 'resources', 'images', 'redx.png')

class TheFileResolver(Plugin, UrlResolver, PluginSettings):
    implements = [UrlResolver, PluginSettings]
    name = "thefile"

    def __init__(self):
        p = self.get_setting('priority') or 100
        self.priority = int(p)
        self.net = Net()

    def get_media_url(self, host, media_id):
        web_url = self.get_url(host, media_id)
        try:
            headers = {
                'Referer': web_url
            }
            html = self.net.http_GET(web_url).content
            #print html.encode('ascii','ignore')
            
            # check if we have a p,ac,k,e,d source
            r = re.search('<script\stype=(?:"|\')text/javascript(?:"|\')>(eval\(function\(p,a,c,k,e,[dr]\)(?!.+player_ads.+).+?)</script>',html,re.DOTALL)
            if r:
                js = jsunpack.unpack(r.group(1))
                r = re.search("file:\'(.+?)\'",js.replace('\\',''))
                if r:
                    return r.group(1)
            
            data = {}
            r = re.findall(r'type="hidden"\s*name="(.+?)"\s*value="(.*?)"', html)
            for name, value in r: data[name] = value
            data.update({'referer': web_url})
            data.update({'method_free': 'Free Download'})
            data.update({'op': 'download1'})
            #print data
            
            html = self.net.http_POST(web_url, data, headers=headers).content
            #print html.encode('ascii','ignore')
            
            data = {}
            r = re.findall(r'type="hidden"\s*name="(.+?)"\s*value="(.*?)"', html)
            for name, value in r: data[name] = value
            data.update({'referer': web_url})
            data.update({'btn_download': 'Create Download Link'})
            data.update({'op': 'download2'})
            #print data
            
            html = self.net.http_POST(web_url, data, headers=headers).content
            #print html.encode('ascii','ignore')
            
            r = re.search(r'<span>\s*<a\s+href="(.+?)".*</a>\s*</span>',html)
            if r:
                return r.group(1)
            else:
                raise Exception("File Link Not Found")
                       
        except urllib2.URLError, e:
            common.addon.log_error(self.name + ': got http error %d fetching %s' %
                                   (e.code, web_url))
            common.addon.show_small_popup('Error','Http error: '+str(e), 8000, error_logo)
            return self.unresolvable(code=3, msg=e)
        except Exception, e:
            common.addon.log(self.name + ': general error occurred: %s' % e)
            common.addon.show_small_popup(title='[B][COLOR white]THEFILE[/COLOR][/B]', msg='[COLOR red]%s[/COLOR]' % e, delay=5000, image=error_logo)
            return self.unresolvable(code=0, msg=e)

    def get_url(self, host, media_id):
            return 'http://thefile.me/%s' % (media_id)

    def get_host_and_id(self, url):
        r = re.search(r'//(.+?)/(.+)', url)
        if r:
            return r.groups()
        else:
            return False


    def valid_url(self, url, host):
        if self.get_setting('enabled') == 'false': return False
        return re.match(r'http://(www.)?thefile.me/.+', url) or 'thefile' in host


