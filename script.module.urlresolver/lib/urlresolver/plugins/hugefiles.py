'''
Hugefiles urlresolver plugin
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
import re, os, urllib2, urllib
from urlresolver import common
from lib import jsunpack
from lib import captcha_lib
import xbmc, xbmcgui

error_logo = os.path.join(common.addon_path, 'resources', 'images', 'redx.png')
net = Net()

class HugefilesResolver(Plugin, UrlResolver, PluginSettings):
    implements = [UrlResolver, PluginSettings]
    name = "hugefiles"


    def __init__(self):
        p = self.get_setting('priority') or 100
        self.priority = int(p)
        self.net = Net()


    def get_media_url(self, host, media_id):
        try:
            url = self.get_url(host, media_id)
            puzzle_img = os.path.join(common.profile_path, "hugefiles_puzzle.png")
            common.addon.log('HugeFiles - Requesting GET URL: %s' % url)
            html = self.net.http_GET(url).content
            r = re.findall('File Not Found',html)
            if r:
                raise Exception ('File Not Found or removed')
                            
            #Check page for any error msgs
            if re.search('<b>File Not Found</b>', html):
                common.addon.log('***** HugeFiles - File Not Found')
                raise Exception('File Not Found')
    
            #Set POST data values
            data = {}
            r = re.findall(r'type="hidden" name="(.+?)" value="(.+?)">', html)
            
            if r:
                for name, value in r:
                    data[name] = value
            else:
                common.addon.log('***** HugeFiles - Cannot find data values')
                raise Exception('Unable to resolve HugeFiles Link')
            
            data['method_free'] = 'Free Download'
            file_name = data['fname']
    
            #Check for SolveMedia Captcha image
            solvemedia = re.search('<iframe src="(http://api.solvemedia.com.+?)"', html)
            recaptcha = re.search('<script type="text/javascript" src="(http://www.google.com.+?)">', html)
    
            if solvemedia:
                data.update(captcha_lib.do_solvemedia_captcha(solvemedia.group(1), puzzle_img))
            elif recaptcha:
                data.update(captcha_lib.do_recaptcha(recaptcha.group(1)))
            else:
                captcha = re.compile("left:(\d+)px;padding-top:\d+px;'>&#(.+?);<").findall(html)
                result = sorted(captcha, key=lambda ltr: int(ltr[0]))
                solution = ''.join(str(int(num[1])-48) for num in result)
                data.update({'code':solution})

            common.addon.log('HugeFiles - Requesting POST URL: %s DATA: %s' % (url, data))
            html = net.http_POST(url, data).content
            # issue one more time for download link
            #Set POST data values
            data = {}
            r = re.findall(r'type="hidden" name="(.+?)" value="(.+?)">', html)
            
            if r:
                for name, value in r:
                    data[name] = value
            else:
                common.addon.log('***** HugeFiles - Cannot find data values')
                raise Exception('Unable to resolve HugeFiles Link')
            data['method_free'] = 'Free Download'

            # can't use t0mm0 net because the post doesn't return until the file is downloaded
            request = urllib2.Request(url, urllib.urlencode(data))
            response = urllib2.urlopen(request)
            stream_url = response.geturl()
            
            # assume that if the final url matches the original url that the process failed
            if stream_url == url:
                raise Exception('Unable to find stream url')
            return stream_url
        except urllib2.HTTPError, e:
            common.addon.log_error(self.name + ': got http error %d fetching %s' %(e.code, url))
            common.addon.show_small_popup('Error','Http error: '+str(e), 5000, error_logo)
            return self.unresolvable(code=3, msg=e)
        except Exception, e:
            common.addon.log_error('**** Hugefiles Error occured: %s' % e)
            common.addon.show_small_popup(title='[B][COLOR white]HUGEFILES[/COLOR][/B]', msg='[COLOR red]%s[/COLOR]' % e, delay=5000, image=error_logo)
            return self.unresolvable(code=0, msg=e)
        
    def get_url(self, host, media_id):
        return 'http://hugefiles.net/%s' % media_id 
        

    def get_host_and_id(self, url):
        r = re.search('//(.+?)/([0-9a-zA-Z]+)',url)
        if r:
            return r.groups()
        else:
            return False
        return('host', 'media_id')


    def valid_url(self, url, host):
        if self.get_setting('enabled') == 'false': return False
        return (re.match('http://(www.)?hugefiles.net/' +
                         '[0-9A-Za-z]+', url) or
                         'hugefiles' in host)
