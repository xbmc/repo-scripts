'''
Sharerepo urlresolver plugin
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
from urlresolver import common
import re
import urllib2
import os
import urllib

#SET ERROR_LOGO# THANKS TO VOINAGE, BSTRDMKR, ELDORADO
error_logo = os.path.join(common.addon_path, 'resources', 'images', 'redx.png')

net = Net()

class SharerepoResolver(Plugin, UrlResolver, PluginSettings):
    implements = [UrlResolver, PluginSettings]
    name = "sharerepo"


    def __init__(self):
        p = self.get_setting('priority') or 100
        self.priority = int(p)
        self.net = Net()


    def get_media_url(self, host, media_id):
        try:
            web_url = self.get_url(host, media_id)
            headers = {
                'Referer':web_url
            }
            
            # Get the landing page
            html = self.net.http_GET(web_url).content
            #print html.encode('ascii','ignore')
            
            data = {}
            r = re.findall(r'type="hidden" name="(.+?)"\s* value="?(.+?)">', html)
            for name, value in r: data[name] = value
            data.update({'referer':web_url})
            data.update({'method_free':'Free Download'})
            #print data
            
            # get the video page
            html = self.net.http_POST(web_url, data, headers=headers).content
            
            r = re.search(r'type="submit"\s*id="btn_download"',html)
            if not r:
                raise Exception("Video Not Found")
            
            data = {}
            r = re.findall(r'type="hidden" name="(.+?)"\s* value="?(.+?)">', html)
            for name, value in r: data[name] = value
            data.update({'referer':web_url})
            data.update({'method_free':'Free Download'})
            data.update({'btn_download':'download'})
            #print data

            # click download button
            # using standard urlopen because t0mm0's wrappers don't seem to return until content download is complete
            request = urllib2.Request(web_url,urllib.urlencode(data),headers=headers)            
            response = urllib2.urlopen(request)
            return response.geturl()
        except urllib2.URLError, e:
            common.addon.log_error(self.name + ': got http error %d fetching %s' %
                                   (e.code, web_url))
            common.addon.show_small_popup('Error','Http error: '+str(e), 8000, error_logo)
            return self.unresolvable(code=3, msg=e)
        except Exception, e:
            common.addon.log('sharerepo: general error occured: %s' % e)
            common.addon.show_small_popup(title='[B][COLOR white]SHAREREPO[/COLOR][/B]', msg='[COLOR red]%s[/COLOR]' % e, delay=5000, image=error_logo)
            return self.unresolvable(code=0, msg=e)
            
    def get_url(self, host, media_id):
        return 'http://sharerepo.com/%s' % media_id 
        

    def get_host_and_id(self, url):
        r = re.search('//(.+?)/([0-9a-zA-Z]+)',url)
        if r:
            return r.groups()
        else:
            return False
        return('host', 'media_id')


    def valid_url(self, url, host):
        if self.get_setting('enabled') == 'false': return False
        return (re.match('http://(www.)?sharerepo.com/' +
                         '[0-9A-Za-z]+', url) or
                         'sharerepo' in host)
