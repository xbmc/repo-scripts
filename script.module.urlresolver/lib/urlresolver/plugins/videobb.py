import re
from t0mm0.common.net import Net
import urllib2
from urlresolver import common
from urlresolver.plugnplay.interfaces import UrlResolver
from urlresolver.plugnplay.interfaces import PluginSettings
from urlresolver.plugnplay import Plugin

# Custom imports
from base64 import b64decode
from binascii import unhexlify
try:
    from json import loads
except ImportError:
    from simplejson import loads

class VideobbResolver(Plugin, UrlResolver, PluginSettings):
    implements = [UrlResolver, PluginSettings]
    name = "videobb"
    domains = [ "videobb.com" ]

    def __init__(self):
        p = self.get_setting('priority') or 100
        self.priority = int(p)
        self.net = Net()

    def get_media_url(self, host, media_id):
        #grab json info for this video
        json_url = 'http://videobb.com/player_control/settings.php?v=%s' % media_id
        json = self.net.http_GET(json_url).content

        #find highest quality URL
        max_res = [240, 480, 99999][int(self.get_setting('q'))]
        chosen_res = 0
        r = re.finditer('"l".*?:.*?"(.+?)".+?"u".*?:.*?"(.+?)"', json)
        if r:
            for match in r:
                res, url = match.groups()
                res = int(res.strip('p'))
                if res > chosen_res and res <= max_res:
                    stream_url_part1 = url.decode('base-64')
                    chosen_res = res
        else:
            raise UrlResolver.ResolverError('videobb: stream url part1 not found')

        # Try to load the datas from json.
        aData = loads(json)

        # Decode the link from the json data settings
        spn_ik = unhexlify(self.__decrypt(aData["settings"]["login_status"]["spen"], aData["settings"]["login_status"]["salt"], 950569)).split(';')
        spn = spn_ik[0].split('&')
        ik = spn_ik[1]

        for item in ik.split('&') :
            temp = item.split('=')
            if temp[0] == 'ik' :
                key = self.__get_key(temp[1])

        sLink = ""
        for item in spn :
            item = item.split('=')
            if(int(item[1])==1):
                sLink = sLink + item[0]+ '=' + self.__decrypt(aData["settings"]["info"]["sece2"], aData["settings"]["config"]["rkts"], key) + '&' #decrypt32byte
            elif(int(item[1]==2)):
                sLink = sLink + item[0]+ '=' + self.__decrypt(aData["settings"]["banner"]["g_ads"]["url"],aData["settings"]["config"]["rkts"], key) + '&'
            elif(int(item[1])==3):
                sLink = sLink + item[0]+ '=' + self.__decrypt(aData["settings"]["banner"]["g_ads"]["type"],aData["settings"]["config"]["rkts"], key,26,25431,56989,93,32589,784152) + '&'
            elif(int(item[1])==4):
                sLink = sLink + item[0]+ '=' + self.__decrypt(aData["settings"]["banner"]["g_ads"]["time"],aData["settings"]["config"]["rkts"], key,82,84669,48779,32,65598,115498) + '&'
            elif(int(item[1])==5):
                sLink = sLink + item[0]+ '=' + self.__decrypt(aData["settings"]["login_status"]["euno"],aData["settings"]["login_status"]["pepper"], key,10,12254,95369,39,21544,545555) + '&'
            elif(int(item[1])==6):
                sLink = sLink + item[0]+ '=' + self.__decrypt(aData["settings"]["login_status"]["sugar"],aData["settings"]["banner"]["lightbox2"]["time"], key,22,66595,17447,52,66852,400595) + '&'
    
        sLink = sLink + "start=0"
        stream_url = stream_url_part1 + '&' + sLink
        return stream_url

    def get_url(self, host, media_id):
        return 'http://www.videobb.com/video/%s' % media_id

    def get_host_and_id(self, url):
        r = re.search('//(.+?)/(?:e/|video/|watch_video.php\?v=)([0-9a-zA-Z]+)',
                        url)
        if r:
            return r.groups()
        else:
            return False

    def valid_url(self, url, host):
        if self.get_setting('enabled') == 'false': return False
        return re.match('http://(www.)?videobb.com/' +
                        '(e/|video/|watch_video.php\?v=)' +
                        '[0-9A-Za-z]+', url) or 'videobb' in host

    def get_settings_xml(self):
        xml = PluginSettings.get_settings_xml(self)
        xml += '<setting label="Highest Quality" id="%s_q" ' % (self.__class__.__name__)
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

    def __get_key(self, nbr):
        if nbr == '1': return 226593
        elif nbr == '2': return 441252
        elif nbr == '3': return 301517
        elif nbr == '4': return 596338
        elif nbr == '5': return 852084
        else: return False
