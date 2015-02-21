'''
SpeedVideo.net urlresolver plugin
Copyright (C) 2014 TheHighway and tknorris

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

import urllib,urllib2,os,re,xbmc,logging,array,string
from t0mm0.common.net import Net
from urlresolver import common
from urlresolver.plugnplay.interfaces import UrlResolver
from urlresolver.plugnplay.interfaces import PluginSettings
from urlresolver.plugnplay import Plugin

#from base64 import b64decode
import base64

error_logo=os.path.join(common.addon_path,'resources','images','redx.png')
ok_logo=os.path.join(common.addon_path,'resources','images','greeninch.png')

class SpeedVideoResolver(Plugin,UrlResolver,PluginSettings):
    implements=[UrlResolver,PluginSettings]
    name="speedvideo"
    domains = [ "speedvideo.net" ]
    domain="speedvideo.net"
    USER_AGENT='Mozilla/5.0 (X11; Ubuntu; Linux i686; rv:30.0) Gecko/20100101 Firefox/30.0'
    
    def __init__(self):
        p=self.get_setting('priority') or 100
        self.priority=int(p)
        self.net=Net()
    
    def valid_url(self,url,host):
        if self.get_setting('enabled')=='false': 
            return False
        return re.match('http://(?:www.)?%s/(?:embed\-)?[0-9A-Za-z_]+(?:\-[0-9]+x[0-9]+.html)?'%self.domain,url) or 'speedvideo' in host
    
    def get_url(self,host,media_id):
        return 'http://%s/embed-%s-640x400.html'%(self.domain,media_id)
        #return 'http://%s/%s'%(self.domain,media_id)
    
    def get_host_and_id(self,url):
        r=re.search('http://(?:www\.)?(%s)\.net/(?:embed-)?([0-9A-Za-z_]+)(?:-\d+x\d+.html)?'%self.name,url)
        if r:
            return r.groups()
        else:
            return False
    
    def get_media_url(self,host,media_id):
        base_url=self.get_url(host,media_id)
        headers={'User-Agent':self.USER_AGENT,'Referer':'http://%s/'%self.domain}
        try:
        #if len(base_url) > 0:
            html=self.net.http_GET(base_url,headers=headers).content
            linkfile=re.compile('var linkfile\s*=\s*"([A-Za-z0-9]+)"').findall(html)[0]
            common.addon.log(linkfile)
            linkfileb=re.compile('var linkfile\s*=\s*base64_decode\(linkfile,\s*([A-Za-z0-9]+)\);').findall(html)[0]
            common.addon.log(linkfileb)
            linkfilec=re.compile('var '+linkfileb+'\s*=\s*(\d+);').findall(html)[0]
            common.addon.log(linkfilec)
            linkfilec=int(linkfilec)
            linkfilez=linkfile[:linkfilec]+linkfile[(linkfilec+10):]
            common.addon.log(linkfilez)
            stream_url=base64.b64decode(linkfilez)
            common.addon.log(stream_url)
            xbmc.sleep(4000)
            #if stream_url: 
            return stream_url
            #else: return False
        #try:
        #    pass
        except urllib2.HTTPError,e:
            e=e.code
            common.addon.log_error(self.name+': got Http error %s fetching %s'%(e,base_url))
            common.addon.show_small_popup('Error','Http error: %s'%e,8000,image=error_logo)
            return self.unresolvable(code=3,msg=e)
        except urllib2.URLError,e:
            e=str(e.args)
            common.addon.log_error(self.name+': got Url error %s fetching %s'%(e,base_url))
            common.addon.show_small_popup('Error','URL error: %s'%e,8000,image=error_logo)
            return self.unresolvable(code=3,msg=e)
        except IndexError,e:
            if re.search('File Not Found',html) :
                e='File not found or removed'
                common.addon.log('**** %s Error occured: %s'%(self.name,e))
                common.addon.show_small_popup(title='[B][COLOR white]%s[/COLOR][/B]'%self.name,msg='[COLOR red]%s[/COLOR]'%e,delay=5000,image=error_logo)
                return self.unresolvable(code=1, msg=e)
            else:
                common.addon.log('**** %s Error occured: %s'%(self.name,e))
                common.addon.show_small_popup(title='[B][COLOR white]%s[/COLOR][/B]'%self.name,msg='[COLOR red]%s[/COLOR]'%e,delay=5000,image=error_logo)
                return self.unresolvable(code=0, msg=e) 
        except Exception,e:
            common.addon.log('**** %s Error occured: %s'%(self.name,e))
            common.addon.show_small_popup(title='[B][COLOR white]%s[/COLOR][/B]'%self.name,msg='[COLOR red]%s[/COLOR]'%e,delay=5000,image=error_logo)
            return self.unresolvable(code=0,msg=e)
    
