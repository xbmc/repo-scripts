"""
Played.to urlresolver plugin
Copyright (C) 2013/2014 TheHighway

This program is free software: you can redistribute it and/or modify it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or (at your option) any later version.

This program is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU General Public License for more details.

You should have received a copy of the GNU General Public License along with this program. If not, see <http://www.gnu.org/licenses/>.
"""
import urllib2,xbmcgui,re,os,xbmc
from t0mm0.common.net import Net
from urlresolver.plugnplay.interfaces import UrlResolver
from urlresolver.plugnplay.interfaces import PluginSettings
from urlresolver.plugnplay import Plugin
from urlresolver import common

#SET ERROR_LOGO# THANKS TO VOINAGE, BSTRDMKR, ELDORADO
error_logo=os.path.join(common.addon_path,'resources','images','redx.png')

class playedResolver(Plugin,UrlResolver,PluginSettings):
    implements=[UrlResolver,PluginSettings]
    name="played"
    def __init__(self):
        p=self.get_setting('priority') or 100
        self.priority=int(p)
        self.net=Net()
    def get_media_url(self,host,media_id):
        web_url=self.get_url(host,media_id)
        try:
            data={}; html=self.net.http_GET(web_url,{'host':'played.to'}).content
            r=re.findall(r'<input type="hidden" name="(.+?)"\s* value="(.*?)"',html)
            for name,value in r: data[name]=value
            data.update({'btn_download':'Continue to Video'})
            html=self.net.http_POST(web_url,data).content
            match=re.search('file: "(.+?)"',html)
            if match: return match.group(1)
            else: return self.unresolvable(code=0,msg='unable to locate video') 
        except urllib2.URLError, e:
            common.addon.log_error('Played: got http error %d fetching %s'%(e.code,web_url))
            common.addon.show_small_popup('Error','Http error: '+str(e),5000,error_logo)
            return self.unresolvable(code=3,msg=e)
        except Exception, e:
            common.addon.log_error('**** Played Error occured: %s'%e)
            common.addon.show_small_popup(title='[B][COLOR white]PLAYED[/COLOR][/B]',msg='[COLOR red]%s[/COLOR]'%e,delay=5000,image=error_logo)
            return self.unresolvable(code=0,msg=e)
    def get_url(self,host,media_id):
            return 'http://played.to/%s'%(media_id)
    def get_host_and_id(self,url):
        r=re.match(r'http://(?:www.)?(played).to/(?:embed-)?([0-9a-zA-Z]+)',url)
        if r: return r.groups()
        else: return False
    def valid_url(self,url,host):
        if self.get_setting('enabled')=='false': return False
        return re.match(r'http://(?:www.)?(played).to/(?:embed-)?([0-9a-zA-Z]+)',url) or 'played' in host
