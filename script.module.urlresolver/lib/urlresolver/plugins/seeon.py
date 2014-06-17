import random
import re
from t0mm0.common.net import Net
import urllib2
from urlresolver import common
from urlresolver.plugnplay.interfaces import UrlResolver
from urlresolver.plugnplay.interfaces import PluginSettings
from urlresolver.plugnplay import Plugin

class SeeonResolver(Plugin, UrlResolver, PluginSettings):
    implements = [UrlResolver, PluginSettings]
    name = "seeon.tv"

    def __init__(self):
        p = self.get_setting('priority') or 100
        self.priority = int(p)
        self.net = Net()

    def get_media_url(self, host, media_id):
        web_url = self.get_url(host, media_id)
        try:
            html = self.net.http_GET(web_url).content

            swf_url, play = re.search('data="(.+?)".+?file=(.+?)\.flv', html, re.DOTALL).groups()

            rtmp = 'rtmp://live%d.seeon.tv/edge' % (random.randint(1, 10)) 
            rtmp += '/%s swfUrl=%s pageUrl=%s tcUrl=%s' % (play, swf_url, 
                                                           web_url, rtmp)
            return rtmp

        except urllib2.URLError, e:
            common.addon.log_error('Seeon: got http error %d fetching %s' %
                                  (e.code, web_url))
            common.addon.show_small_popup('Error','Http error: '+str(e), 5000, error_logo)
            return self.unresolvable(code=3, msg=e)
        
        except Exception, e:
            common.addon.log_error('**** Seeon Error occured: %s' % e)
            common.addon.show_small_popup(title='[B][COLOR white]SEEON[/COLOR][/B]', msg='[COLOR red]%s[/COLOR]' % e, delay=5000, image=error_logo)
            return self.unresolvable(code=0, msg=e)


    def get_url(self, host, media_id):
        return 'http://seeon.tv/view/%s' % media_id
        
        
    def get_host_and_id(self, url):
        r = re.search('//(.+?)/view/(\d+)', url)
        if r:
            return r.groups()
        else:
            return False


    def valid_url(self, url, host):
        if self.get_setting('enabled') == 'false': return False
        return re.match('http://(www.)?seeon.tv/view/(?:\d+)', 
                        url) or 'seeon' in host 
    
