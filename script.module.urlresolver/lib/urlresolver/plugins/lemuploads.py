'''
Lemuploads urlresolver plugin

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
import re, os, time, xbmc
import xbmcgui
from urlresolver import common
from lib import jsunpack

#SET ERROR_LOGO# THANKS TO VOINAGE, BSTRDMKR, ELDORADO
error_logo = os.path.join(common.addon_path, 'resources', 'images', 'redx.png')

net = Net()

class LemuploadsResolver(Plugin, UrlResolver, PluginSettings):
    implements = [UrlResolver, PluginSettings]
    name = "lemuploads"


    def __init__(self):
        p = self.get_setting('priority') or 100
        self.priority = int(p)
        self.net = Net()


    def get_media_url(self, host, media_id):
        try:
            dialog = xbmcgui.DialogProgress()
            dialog.create('Resolving', 'Resolving Lemuploads Link...')       
            dialog.update(0)
            
            url = self.get_url(host, media_id)
            html = self.net.http_GET(url).content
    
            dialog.update(50)
            
            #Check page for any error msgs
            if re.search('This server is in maintenance mode', html):
                common.addon.log_error(self.name + ' - Site reported maintenance mode')
                xbmc.executebuiltin('XBMC.Notification([B][COLOR white]LEMUPLOADS[/COLOR][/B],[COLOR red]Site reported maintenance mode[/COLOR],8000,'+logo+')')
                return self.unresolvable(code=2, msg='Site reported maintenance mode')                
                
            if re.search('<b>File Not Found</b>', html):
                common.addon.log_error(self.name + ' - File Not Found')
                xbmc.executebuiltin('XBMC.Notification([B][COLOR white]LEMUPLOADS[/COLOR][/B],[COLOR red]File Not Found[/COLOR],8000,'+logo+')')
                return self.unresolvable(code=1, msg='File Not Found')    
                
            filename = re.search('<h2>(.+?)</h2>', html).group(1)
            extension = re.search('(\.[^\.]*$)', filename).group(1)
            guid = re.search('http://lemuploads.com/(.+)$', url).group(1)
            
            vid_embed_url = 'http://lemuploads.com/vidembed-%s%s' % (guid, extension)
            
            import urllib2
            request = urllib2.Request(vid_embed_url)
            request.add_header('User-Agent', 'Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/28.0.1500.72 Safari/537.36')
            request.add_header('Referer', url)
            response = urllib2.urlopen(request)
            redirect_url = re.search('(http://.+?)video', response.geturl()).group(1)
            download_link = redirect_url + filename
            
            dialog.update(100)
            
            return download_link
                                
        except Exception, e:
            common.addon.log('**** Lemuploads Error occured: %s' % e)
            common.addon.show_small_popup('Error', str(e), 5000, '')
            return self.unresolvable(code=0, msg='Exception: %s' % e)
        
        finally:
            dialog.close()
            

        
    def get_url(self, host, media_id):
        return 'http://lemuploads.com/%s' % media_id 
        

    def get_host_and_id(self, url):
        r = re.search('//(.+?)/([0-9a-zA-Z]+)',url)
        if r:
            return r.groups()
        else:
            return False
        return('host', 'media_id')


    def valid_url(self, url, host):
        if self.get_setting('enabled') == 'false': return False
        return (re.match('http://(www.)?lemuploads.com/' +
                         '[0-9A-Za-z]+', url) or
                         'lemuploads' in host)
