"""
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

"""
RogerThis - 16/8/2011
Site: http://www.vidxden.com , http://www.divxden.com & http://www.vidbux.com
vidxden hosts both avi and flv videos
In testing there seems to be a timing issue with files coming up as not playable.
This happens on both the addon and in a browser.
"""
import urllib2,xbmcaddon,socket,re,os
from t0mm0.common.net import Net
from urlresolver import common
from urlresolver.plugnplay.interfaces import UrlResolver
from urlresolver.plugnplay.interfaces import PluginSettings
from urlresolver.plugnplay import Plugin
from lib import captcha_lib
from lib import jsunpack

#SET ERROR_LOGO# THANKS TO VOINAGE, BSTRDMKR, ELDORADO
error_logo = os.path.join(common.addon_path, 'resources', 'images', 'redx.png')
datapath = common.profile_path

#SET DEFAULT TIMEOUT FOR SLOW SERVERS:
socket.setdefaulttimeout(30)

#SET DIRECTORIES 
addon=xbmcaddon.Addon(id='script.module.urlresolver')
logo='http://googlechromesupportnow.com/wp-content/uploads/2012/06/Installation-103-error-in-Chrome.png'

class VidxdenResolver(Plugin, UrlResolver, PluginSettings):
    implements = [UrlResolver, PluginSettings]
    name = "vidxden"

    def __init__(self):
        p = self.get_setting('priority') or 100
        self.priority = int(p)
        self.net = Net()

    def get_media_url(self, host, media_id):
        web_url = self.get_url(host, media_id)
        puzzle_img = os.path.join(datapath, "vidxden_puzzle.png")

        try:
            resp = self.net.http_GET(web_url)
            html = resp.content
            if "No such file or the file has been removed due to copyright infringement issues." in html:
                raise Exception ('File Not Found or removed')
            
            filename=re.compile('<input name="fname" type="hidden" value="(.+?)">').findall(html)[0]
            data={'op':'download1','method_free':'1','usr_login':'','id':media_id,'fname':filename}

            #Check for SolveMedia Captcha image
            solvemedia = re.search('<iframe src="(http://api.solvemedia.com.+?)"', html)
            if solvemedia:
                data.update(captcha_lib.do_solvemedia_captcha(solvemedia.group(1), puzzle_img))

            html = self.net.http_POST(resp.get_url(),data).content

            #find packed javascript embed code
            r = re.search('(eval.*?)\s*</script>',html, re.DOTALL)
            if r:
                packed_data = r.group(1)
            else:
                common.addon.log_error('vidxden: packed javascript embed code not found')
                raise Exception('packed javascript embed code not found')
                
            try: decrypted_data = jsunpack.unpack(packed_data)
            except: pass
        
            #First checks for a flv url, then the if statement is for the avi url
            r = re.search('file.\',.\'(.+?).\'', decrypted_data)
            if not r:
                r = re.search('src="(.+?)"', decrypted_data)
            if r:
                stream_url = r.group(1)
            else:
                raise Exception ('vidxden: stream url not found')

            return "%s" % (stream_url)
            
        except urllib2.HTTPError, e:
            common.addon.log_error('Vidxden: got http error %d fetching %s' %
                                  (e.code, web_url))
            common.addon.show_small_popup('Error','Http error: '+str(e), 5000, error_logo)
            return self.unresolvable(code=3, msg=e)

        except Exception, e:
            common.addon.log_error('**** Vidxden Error occured: %s' % e)
            common.addon.show_small_popup(title='[B][COLOR white]VIDXDEN[/COLOR][/B]', msg='[COLOR red]%s[/COLOR]' % e, delay=5000, image=error_logo)
            return self.unresolvable(code=0, msg=e)

        
    def get_url(self, host, media_id):
        if 'vidbux' in host:
            host = 'www.vidbux.com'
        else:
            host = 'www.vidxden.com'
        return 'http://%s/%s' % (host, media_id)
       
    def get_host_and_id(self, url):
        r = re.search('//(.+?)/(?:embed-)?([0-9a-z]+)', url)
        if r:
            return r.groups()
        else:
            return False


    def valid_url(self, url, host):
        if self.get_setting('enabled') == 'false': return False
        return (re.match('http://(?:www.)?(vidxden|divxden|vidbux).(com|to)/' +
                         '(embed-)?[0-9a-z]+', url) or
                'vidxden' in host or 'divxden' in host or
                'vidbux' in host)

    #PluginSettings methods
    def get_settings_xml(self):
        xml = PluginSettings.get_settings_xml(self)
        xml += '<setting id="vidxden_captchax" '
        xml += 'type="slider" label="Captcha Image X Position" range="0,500" default="335" option="int" />\n'
        xml += '<setting id="vidxden_captchay" '
        xml += 'type="slider" label="Captcha Image Y Position" range="0,500" default="0" option="int" />\n'
        xml += '<setting id="vidxden_captchah" '
        xml += 'type="slider" label="Captcha Image Height" range="0,500" default="180" option="int" />\n'
        xml += '<setting id="vidxden_captchaw" '
        xml += 'type="slider" label="Captcha Image Width" range="0,1000" default="624" option="int" />\n'
        return xml

def unpack_js(p, k):
    '''emulate js unpacking code'''
    k = k.split('|')
    for x in range(len(k) - 1, -1, -1):
        if k[x]:
            p = re.sub('\\b%s\\b' % base36encode(x), k[x], p)
    return p


def base36encode(number, alphabet='0123456789abcdefghijklmnopqrstuvwxyz'):
    """Convert positive integer to a base36 string. (from wikipedia)"""
    if not isinstance(number, (int, long)):
        raise TypeError('number must be an integer')
 
    # Special case for zero
    if number == 0:
        return alphabet[0]

    base36 = ''

    sign = ''
    if number < 0:
        sign = '-'
        number = - number

    while number != 0:
        number, i = divmod(number, len(alphabet))
        base36 = alphabet[i] + base36

    return sign + base36
        

