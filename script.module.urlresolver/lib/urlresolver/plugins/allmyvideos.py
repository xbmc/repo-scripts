'''
Allmyvideos urlresolver plugin
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
import re,os,xbmcgui,xbmc
from urlresolver import common
#SET ERROR_LOGO# THANKS TO VOINAGE, BSTRDMKR, ELDORADO
error_logo=os.path.join(common.addon_path,'resources','images','redx.png')
net=Net()
USER_AGENT='Mozilla/5.0 (X11; Ubuntu; Linux i686; rv:30.0) Gecko/20100101 Firefox/30.0'
class AllmyvideosResolver(Plugin,UrlResolver,PluginSettings):
    implements=[UrlResolver,PluginSettings]
    name="allmyvideos"
    def __init__(self):
        p=self.get_setting('priority') or 100
        self.priority=int(p)
        self.net=Net()
    def get_media_url(self,host,media_id):
        try:
            dialog=xbmcgui.DialogProgress()
            dialog.create('Resolving','Resolving Allmyvideos Link...')       
            dialog.update(0)
            
            url=self.get_url1st(host,media_id)
            headers={'User-Agent':USER_AGENT,'Referer':url}
            html=self.net.http_GET(url,headers=headers).content
            dialog.update(20)
            r=re.search('"mediaid"\s*:\s*".*?",\s*"sources"\s*:\s*.\n*\s*.\n*\s*"file"\s*:\s*"(.+?)"',html)
            if r:
                dialog.update(100)
                dialog.close()
                xbmc.sleep(2000)
                return r.group(1)+'|User-Agent=%s'%(USER_AGENT)
            
            url=self.get_url(host,media_id)
            headers={'User-Agent':USER_AGENT,'Referer':url}
            html=self.net.http_GET(url,headers=headers).content
            
            data={}; r=re.findall(r'type="hidden" name="(.+?)"\s* value="?(.+?)">',html)
            for name,value in r: data[name]=value
            html=net.http_POST(url,data,headers=headers).content
            dialog.update(50)
            
            r=re.search('"sources"\s*:\s*.\n*\s*.\n*\s*"file"\s*:\s*"(.+?)"',html)
            if r:
                dialog.update(100)
                dialog.close()
                xbmc.sleep(2000) 
                return r.group(1)+'|User-Agent=%s'%(USER_AGENT)
            else:
                dialog.close()
                raise Exception('could not find video')          
        except Exception, e:
            common.addon.log('**** Allmyvideos Error occured: %s' % e)
            common.addon.show_small_popup('Error', str(e), 5000, '')
            return self.unresolvable(code=0, msg='Exception: %s' % e)
    def get_url(self,host,media_id): return 'http://allmyvideos.net/%s'%media_id 
    def get_url1st(self,host,media_id): return 'http://allmyvideos.net/embed-%s.html'%media_id 
    def get_host_and_id(self, url):
        r=re.search('//(?:www.)?(allmyvideos.net)/(?:embed-)?([0-9a-zA-Z]+)',url)
        if r: return r.groups()
        else: return False
        return('host','media_id')
    def valid_url(self,url,host):
        if self.get_setting('enabled')=='false': return False
        return (re.match('http://(?:www.)?(allmyvideos.net)/(?:embed-)?([0-9A-Za-z]+)',url) or re.match('http://(www.)?(allmyvideos.net)/embed-([0-9A-Za-z]+)[\-]*\d*[x]*\d*.*[html]*',url) or 'allmyvideos' in host)
