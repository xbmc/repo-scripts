"""
    OVERALL CREDIT TO:
        t0mm0, Eldorado, VOINAGE, BSTRDMKR, tknorris, smokdpi, TheHighway

    urlresolver XBMC Addon
    Copyright (C) 2011 t0mm0

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

import re,urllib,urllib2,os,xbmc
from t0mm0.common.net import Net
from urlresolver import common
from urlresolver.plugnplay.interfaces import UrlResolver
from urlresolver.plugnplay.interfaces import PluginSettings
from urlresolver.plugnplay import Plugin
from time import sleep

#SET ERROR_LOGO# THANKS TO VOINAGE, BSTRDMKR, ELDORADO
error_logo=os.path.join(common.addon_path,'resources','images','redx.png')

class VideomegaResolver(Plugin,UrlResolver,PluginSettings):
    implements=[UrlResolver,PluginSettings]
    name="videomega"
    domains=["videomega.tv","movieshd.co"]

    def __init__(self):
        p = self.get_setting('priority') or 100
        self.priority=int(p)
        self.net=Net()
        self.headers={'Referer':'http://videomega.tv/'}

    def get_media_url(self,host,media_id):
        web_url=self.get_url(host,media_id)
        stream_url=None
        self.headers['Referer']=web_url
        try:
            html=self.net.http_GET(web_url,headers=self.headers).content
            if 'Error connecting to db' in html: return self.unresolvable(0, 'Error connecting to DB')
            # find the unescape string 
            r=re.compile('document\.write\(unescape\("([^"]+)').findall(html)
            if r:
                unescaped_str=urllib.unquote(r[-1])
                r=re.search('file\s*:\s*"([^"]+)',unescaped_str)
                if r:
                    stream_url=r.group(1)
                    stream_url=stream_url.replace(" ","%20")
            if stream_url:
                #sleep(6)
                xbmc.sleep(6000)
                return stream_url
            else: return self.unresolvable(0,'No playable video found.')
        except urllib2.URLError, e:
            common.addon.log_error('%s: got http error %d fetching %s'%(host,e.code,web_url))
            return self.unresolvable(code=3,msg=e)
        except Exception, e:
            common.addon.log_error('**** %s Error occured: %s'%(host,e))
            common.addon.show_small_popup(title='[B][COLOR white]%s[/COLOR][/B]'%host,msg='[COLOR red]%s[/COLOR]'%e,delay=5000,image=error_logo)
            return self.unresolvable(code=0,msg=e)

    def get_url(self,host,media_id):
        if "movieshd.co" in host:
            return 'http://%s/iframe.php?ref=%s'%(host,media_id)
        else: #For VideoMega.tv
            if len(media_id) == 60:
                try:
                    html=self.net.http_GET('http://%s/validatehash.php?hashkey=%s'%(host,media_id),headers=self.headers).content
                    #print html
                    if 'Error connecting to db' in html: return self.unresolvable(0, 'Error connecting to DB')
                    if 'ref=' in html:
                        return 'http://%s/cdn.php?ref=%s'%(host,re.compile('.*?ref="(.+?)".*').findall(html)[0])
                    else:
                        raise Exception('No playable video found.')
                except urllib2.URLError,e:
                    common.addon.log_error('Videomega: got http error %d fetching %s' % (e.code, 'http://%s/validatehash.php?hashkey=%s'%(host,media_id)))
                    common.addon.show_small_popup(title='[B][COLOR white]Videomega[/COLOR][/B]',msg='[COLOR red]HTTP Error: %s[/COLOR]'%e,delay=5000,image=error_logo)
                except Exception,e:
                    common.addon.log_error('**** Videomega Error occured: %s'%e)
                    common.addon.show_small_popup(title='[B][COLOR white]Videomega[/COLOR][/B]',msg='[COLOR red]%s[/COLOR]'%e,delay=5000,image=error_logo)
            else:
                return 'http://%s/iframe.php?ref=%s'%(host,media_id)

    def get_host_and_id(self,url):
        q=re.search('//(?:www.)?movieshd.co/watch-online/.*html',url)
        if q: # movieshd link
            try:
                # Request MoviesHD page
                req=urllib2.Request(url)
                req.add_header('User-Agent','Mozilla/5.0 (Windows; U; Windows NT 5.1; en-GB; rv:1.9.0.3) Gecko/2008092417 Firefox/3.0.3')
                response=urllib2.urlopen(req)
                link=response.read()
                response.close()
                # Find videomega reference
                match=re.compile("'text/javascript'>ref='(.+?)?';width.*iframe").findall(link)
                if (len(match) == 1):
                    return ['videomega.tv',match[0]]
            except urllib2.URLError,e:
                common.addon.log_error('movieshd.co: got http error %d fetching %s'%(e.code,web_url))
                return self.unresolvable(code=3,msg=e)
            except Exception,e:
                common.addon.log_error('**** movieshd.co Error occured: %s'%e)
                common.addon.show_small_popup(title='[B][COLOR white]Videomega[/COLOR][/B]',msg='[COLOR red]%s[/COLOR]'%e,delay=5000,image=error_logo)
        r=re.search('//((?:www.)?(?:.+?))/.*(?:\?(?:ref|hashkey)=)([0-9a-zA-Z]+)',url)
        if r: # videomega link
            return r.groups()
        v=re.search('//((?:www.)?(?:videomega.+?))/(?:iframe.(?:php|js)\?ref=)([0-9a-zA-Z]+)',url)
        if v: # videomega link
            return v.groups()
        return False

    def valid_url(self,url,host):
        if self.get_setting('enabled')=='false': return False
        return re.match('http://(?:www.)?videomega.tv/(?:iframe|cdn|validatehash|\?ref=)(?:\.php|\.js|.*)\?*', url) or 'videomega' in host
