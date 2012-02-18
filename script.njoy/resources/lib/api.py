from default import *

import socket
import workerpool
import urllib
import re
import traceback
try: import json
except: import simplejson as json
from xml.dom import minidom
import xbmcgui

socket.setdefaulttimeout(3)

## A lot of the code borrowed from http://tv.i-njoy.eu/repo/ , all credit to them

#N7 API GLOBALS
PORT     = 80
DISCOVER = "n7mac.html"

def _(addr, command):
    """Call WebApi N7 and returns python dict"""
    return request(addr, "utelisys/%s" % (command, ))

def request(addr, command=DISCOVER, ping=False):
    """Raw request to N7 webserver"""
    try:
        r = urllib.urlopen("http://%s/%s" % (addr, command, ))
        data = r.read()
        r.close()
    except:
        return False

    if ping:
        if data.find("N7") < 0:
            return False
        return True
    
    return translate(data)

def translate(data):
    """Translate html data from webapi to python dict"""
    try:
        #Get text between body
        body = re.compile('body>(.*?)<\/body', re.DOTALL + re.MULTILINE).search(str(data)).group(1)
        #Prapare for splitting based on br tag
        body = body.replace('<br>', '||').replace('&nbsp;', '').replace('\x05', '')
        #remove all html tags
        body = re.sub('<.*?>', ' ', body)
        #split data into lines
        lines = body.split("||")
    except:
        return False

    result = []
    for i, line in enumerate(lines):
        r ={}
        #if data has attribute make it available
        if line.find(':') != -1:
            v = line.split(':', 1)
            r[v[0].strip()] = v[1].strip()
            r[i] = v[1].strip()
        #else use line number
        else:
            r[i] = line.strip()
        result.append(r)
    return result

def channel_list(addr):
#    <item>
#        <guid>http://192.168.1.23:8080/chlist/0001</guid>
#        <boxee:media-type type="movie" expression="full" name="feature"/>
#        <title>1. CSB TV</title>
#        <media:content type="video/mpg2" url="http://192.168.1.23:8080/chlist/0001"/>
#        <media:thumbnail url="http://www.anyseedirect.eu/images/csb_tv.png"/>
#        <description></description>
#    </item>
    channel_list = []
    r = urllib.urlopen('http://%s/n7channel.rss' % (addr, ))
    result = r.read()
    r.close()
    xmldoc = minidom.parseString(result)
    items = xmldoc.getElementsByTagName("item")
    for item in items:
        channel_list.append(
        {'guid'       :item.getElementsByTagName("guid")[0].firstChild.nodeValue,
         'title'      :item.getElementsByTagName("title")[0].firstChild.nodeValue,
         'description':item.getElementsByTagName("description")[0].firstChild.nodeValue,
         'url'        :item.getElementsByTagName("media:content")[0].getAttribute('url'),
         'thumb'      :item.getElementsByTagName("media:thumbnail")[0].getAttribute('url')})  
    return channel_list

def get_tuner_epg(addr, id):
    count = 4 - len(str(id))
    active = request(addr, 'utelisys/set_chview/' + '0'*count + str(id))

    if active:
        epg = request(addr, 'utelisys/get_currentch_epg')
        if epg and epg > 14:
            pass

def get_internet_epg(id):
    try:
        url = "http://web2py.formatics.nl/epg_grabber/xml/getNowNext.json/%s" % (id, )
        r = urllib.urlopen(url)
        data = r.read()
        r.close()
        return json.loads(data)
    except:
#        if DEBUG:
#            traceback.print_exc()
        return {"current": "", "next": ""}

class scan:
    """Detects (multiple) N7 in network"""
    def __init__(self):
        self.n7         = False
        self.ip         = self.get_local_ip()

    def get_local_ip(self):
        """Find local ip addresses at the host"""
        #adresses = [ip for ip in socket.gethostbyname_ex(socket.gethostname())[2] if not ip.startswith("127.")]
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("google.com",80))
        adresses = [(s.getsockname()[0])]
        s.close()
        
        if adresses:
            print "Found IP: %s" % (", ".join(adresses), )
            return adresses
        else:
            return False

    def get_lan(self, addr):
        """Get the LAN from an IP"""
        network = addr.split(".")
        del network[3]
        return ".".join(network)


    def is_n7(self, addr):
        """Find N7 tuner BASED ON OPEN PORT AND N7 MAKE FILE"""
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(0.10)    ## set a timeout of 0.10 sec
        try:
            s.connect((addr,PORT))
            s.close()
        except:
            return

        response = request(addr, DISCOVER, True)
        if response:
            return addr

    def run(self):
        """FIND N7 IN THREADED POOL"""
        lan       = [self.get_lan(ip) for ip in self.ip]
        scan_list = [".".join([l, str(i)]) for l in lan for i in xrange(1,256)]
        
        print "Ready for scanning LAN: %s" % (", ".join(lan), )

        pool   = workerpool.WorkerPool(size=25)
        result = pool.map(self.is_n7, scan_list)
        pool.shutdown()
        pool.wait()

        print "Scan Finished"

        result = filter(None, result)
        if result:
            self.n7 = result
            print " - Found N7 at: " + ", ".join(result)
            return True
        else:
            print " - No N7 found"
            return False

