"""
urlresolver XBMC Addon
Copyright (C) 2011 t0mm0

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

# Custom imports
#SET ERROR_LOGO# THANKS TO VOINAGE, BSTRDMKR, ELDORADO
error_logo = os.path.join(common.addon_path, 'resources', 'images', 'redx.png')
import re
from base64 import b64decode
from binascii import unhexlify
try:
    from json import loads
except ImportError:
    from simplejson import loads



class VideozerResolver(Plugin, UrlResolver, PluginSettings):
    implements = [UrlResolver, PluginSettings]
    name = "videozer"

    def __init__(self):
        p = self.get_setting('priority') or 100
        self.priority = int(p)
        self.net = Net()
        self.pattern = 'http://((?:www.)?videozer.com)/(?:embed|video)?/([0-9a-zA-Z]+)'


    def get_media_url(self, host, media_id):

        #grab url for this video
        settings_url = "http://www.videozer.com/" + \
            "player_control/settings.php?v=%s" % media_id

        try:
            html = self.net.http_GET(settings_url).content

            #find highest quality URL
            max_res = [240, 480, 99999][int(self.get_setting('q'))]
            r = re.finditer('"l".*?:.*?"(.+?)".+?"u".*?:.*?"(.+?)"', html)
            chosen_res = 0
            stream_url = False

            if r:
                for match in r:
                    res, url = match.groups()
                    if (res == 'LQ' ): res = 240
                    elif (res == 'SD') : res = 480
                    else : res = 720
                    if res > chosen_res and res <= max_res:
                        stream_url_part1 = url.decode('base-64')
                        chosen_res = res
            else:
                raise Exception ('File Not Found or removed')

            # Try to load the datas from html. This data should be json styled.
            aData = loads(html)

            # Decode the link from the json data settings.
            spn_ik = unhexlify(self.__decrypt(aData["cfg"]["login"]["spen"], aData["cfg"]["login"]["salt"], 950569)).split(';')
            spn = spn_ik[0].split('&')
            ik = spn_ik[1]

            for item in ik.split('&') :
                temp = item.split('=')
                if temp[0] == 'ik' :
                    key = self.__getKey(temp[1])

            sLink = ""
            for item in spn :
                item = item.split('=')
                if(int(item[1])==1):
                    sLink = sLink + item[0]+ '=' + self.__decrypt(aData["cfg"]["info"]["sece2"], aData["cfg"]["environment"]["rkts"], key) + '&' #decrypt32byte
                elif(int(item[1]==2)):
                    sLink = sLink + item[0]+ '=' + self.__decrypt(aData["cfg"]["ads"]["g_ads"]["url"],aData["cfg"]["environment"]["rkts"], key) + '&'
                elif(int(item[1])==3):
                    sLink = sLink + item[0]+ '=' + self.__decrypt(aData["cfg"]["ads"]["g_ads"]["type"],aData["cfg"]["environment"]["rkts"], key,26,25431,56989,93,32589,784152) + '&'
                elif(int(item[1])==4):
                    sLink = sLink + item[0]+ '=' + self.__decrypt(aData["cfg"]["ads"]["g_ads"]["time"],aData["cfg"]["environment"]["rkts"], key,82,84669,48779,32,65598,115498) + '&'
                elif(int(item[1])==5):
                    sLink = sLink + item[0]+ '=' + self.__decrypt(aData["cfg"]["login"]["euno"],aData["cfg"]["login"]["pepper"], key,10,12254,95369,39,21544,545555) + '&'
                elif(int(item[1])==6):
                    sLink = sLink + item[0]+ '=' + self.__decrypt(aData["cfg"]["login"]["sugar"],aData["cfg"]["ads"]["lightbox2"]["time"], key,22,66595,17447,52,66852,400595) + '&'

            sLink = sLink + "start=0"

            sMediaLink = stream_url_part1 + '&' + sLink

            return sMediaLink

        except urllib2.URLError, e:
            common.addon.log_error(self.name + ': got http error %d fetching %s' %
                                     (e.code, web_url))
            common.addon.show_small_popup('Error','Http error: '+str(e), 8000, error_logo)
            return self.unresolvable(code=3, msg=e)
        except Exception, e:
            common.addon.log('**** Videozer Error occured: %s' % e)
            common.addon.show_small_popup(title='[B][COLOR white]VIDEOZER[/COLOR][/B]', msg='[COLOR red]%s[/COLOR]' % e, delay=5000, image=error_logo)
            return self.unresolvable(code=0, msg=e)


    def get_url(self, host, media_id):
            return 'http://www.videozer.com/video/%s' % (media_id)

    def get_host_and_id(self, url):
        r = re.search(self.pattern, url)
        if r:
            return r.groups()
        else:
            return False


    def valid_url(self, url, host):
        if self.get_setting('enabled') == 'false': return False
        return re.match(self.pattern, url) or self.name in host

    def get_settings_xml(self):
        xml = PluginSettings.get_settings_xml(self)
        xml += '<setting label="Highest Quality" id="VideozerResolver_q" '
        xml += 'type="enum" values="240p|480p|Maximum" default="2" />\n'
        return xml

    def __decrypt(self, str, k1, k2, p4 = 11, p5 = 77213, p6 = 81371, p7 = 17, p8 = 92717, p9 = 192811):
        tobin = self.hex2bin(str,len(str)*4)
        tobin_lenght = len(tobin)
        keys = []
        index = 0

        while (index < tobin_lenght*3):
            k1 = ((int(k1) * p4) + p5) % p6
            k2 = ((int(k2) * p7) + p8) % p9
            keys.append((int(k1) + int(k2)) % tobin_lenght)
            index += 1

        index = tobin_lenght*2

        while (index >= 0):
            val1 = keys[index]
            mod = index%tobin_lenght
            val2 = tobin[val1]
            tobin[val1] = tobin[mod]
            tobin[mod] = val2
            index -= 1

        index = 0
        while(index < tobin_lenght):
            tobin[index] = int(tobin[index]) ^ int(keys[index+(tobin_lenght*2)]) & 1
            index += 1
            decrypted = self.bin2hex(tobin)
        return decrypted

    def hex2bin(self,val,fill):
        bin_array = []
        string = self.bin(int(val, 16))[2:].zfill(fill)
        for value in string:
            bin_array.append(value)
        return bin_array

    def bin2hex(self,val):
        string = str("")
        for char in val:
            string+=str(char)
        return "%x" % int(string, 2)

    def bin(self, x):
        '''
        bin(number) -> string
        
        Stringifies an int or long in base 2.
        '''
        if x < 0: return '-' + bin(-x)
        out = []
        if x == 0: out.append('0')
        while x > 0:
            out.append('01'[x & 1])
            x >>= 1
            pass
        try: return '0b' + ''.join(reversed(out))
        except NameError, ne2: out.reverse()
        return '0b' + ''.join(out)

    def __getKey(self, nbr):
        if nbr == '1': return 215678
        elif nbr == '2': return 516929
        elif nbr == '3': return 962043
        elif nbr == '4': return 461752
        elif nbr == '5': return 141994
        else: return False
