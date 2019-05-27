# -*- coding: utf-8 -*-

import platform
import subprocess
import requests
import re
import threading
from timeit import default_timer as timer
import xbmc
import xbmcaddon
import pyxbmct

ADDON     = xbmcaddon.Addon()              #this addon
TVH_ADDON = xbmcaddon.Addon(id='pvr.hts')  #Tvheadend addon

#Returns string with given ID localized in the current language
def lang(string_id):
    return ADDON.getLocalizedString(string_id)

#Sends ping to the computer with the given address - every second and for sec seconds.
#Returns string: average round trip time in localized format: "dd[.ddd] ms[, dd% packets loss]"
#                or localized string "no connection" if there was no response.
def ping(hostname, sec):
    if re.match('^[a-zA-Z0-9.:-]{1,253}$', hostname) is None: return lang(32129)  #"incorrect address format"
    if platform.system() == "Windows":  #tested on Win10
        ping_command = 'ping -n '+str(sec)+' '+hostname
        ping_regex   = '[0-9.]+ ?ms.+ [0-9.]+ ?ms.+ ([0-9.]+) ?ms'
    else:  #tested on Linux Mint
        ping_command = 'ping -c '+str(sec)+' '+hostname
        ping_regex   = '[0-9.]+/([0-9.]+)/[0-9.]+' #LibreELEC doesn't output mdev; Debian (with derivatives) and macOS outputs it (won't be matched)
    if xbmc.getCondVisibility('system.platform.android'): #patch for Android (for example for Android TV 6)
        result = subprocess.Popen(ping_command, shell=True, executable="/system/bin/sh", stdout=subprocess.PIPE).stdout.read()
    else:
        result = subprocess.Popen(ping_command, shell=True, stdout=subprocess.PIPE).stdout.read()
    m1 = re.search('([0-9.]+)%', result)                 #% packet loss
    m2 = re.search(ping_regex, result)                   #avg ms
    if m2 is None: #no network connection or 100% packet loss
        return lang(32130)  #"no connection"
    else: #we received at least one ping packet
        packet_loss = m1.group(1) + "%"
        latency = m2.group(1) + " ms" + ("" if packet_loss == "0%" else ", " + packet_loss + " " + lang(32131))  #"packets loss"
        if latency == '0 ms': latency = '<1 ms' #patch for Windows
        return latency

#Tries to download the main page ("/") from the server with the given url (should be in "hostname[:port]" format)
# - every 10 seconds and no longer than sec seconds.
#Returns string: average round trip time in localized format: "dd.d ms[, dd% packets loss]"
#                or localized string "no connection" if there was no response.
#It works by analogy to ping(hostname, sec). I used it once when I couldn't use ping.
def http_rtt(url, sec):
    if re.match('^[a-zA-Z0-9.:-]{1,253}$', url) is None: return lang(32129)  #"incorrect address format"
    url = 'http://' + url
    wait_sec = 10                                  #number of seconds to wait between requests
    total_requests = 1 + sec/wait_sec              #number of requests that will be sent
    total_answers  = 0
    packet_loss    = 0
    total_time     = 0
    s = requests.Session()
    try:
        s.get(url, timeout=5).text                 #make a TCP connection to speed up proper requests
    except requests.RequestException:
        pass
    xbmc.sleep(1000)                               #be nice
    for i in range(0, total_requests):
        try:
            start = timer()
            s.get(url, timeout=5).text             #thanks to .text the session can be closed when not needed
            total_time += timer() - start
            total_answers += 1
            if i != total_requests - 1: xbmc.sleep(1000*wait_sec)  #wait <wait_sec> seconds
        except requests.RequestException:          #the web page could not be downloaded in <timeout> seconds
            packet_loss += 1
    if total_answers == 0:
        return lang(32130)  #"no connection"
    else:
        latency = format(total_time*1000/total_answers, '.1f') + " ms" #convert seconds to ms, calculate average, round to 1 decimal place
        if packet_loss != 0:
            latency += ", " + str(packet_loss*100/total_requests) + "% " + lang(32131)  #"packets loss"
        return latency

#Shows latency (RTT) and packets loss to consecutive steps on the way from Kodi to Tvheadend server.
#For more info see description in the README.md file.
class TVNetworkHealthWindow(pyxbmct.AddonDialogWindow):
    def setAnimation(self, control):
        control.setAnimations([('WindowOpen',  'effect=fade start=0   end=100 time=300',),
                               ('WindowClose', 'effect=fade start=100 end=0   time=300',)])

    def __init__(self):
        super(TVNetworkHealthWindow, self).__init__("Tvheadend route latencies")
        try:  #comment it temporary to see detailed log in case of errors
            self.testlength = int(ADDON.getSetting("testlength"))  #how long a single test will take

            #--------------- IP addresses of consecutive routers and servers ---------------
            local_router    = xbmc.getInfoLabel('Network.GatewayAddress')
            internet_server = ADDON.getSetting("nearby_internet_server")
            backend_router  = TVH_ADDON.getSetting("host")
            backend_service = backend_router + ":" + TVH_ADDON.getSetting("http_port")

            #----- window layout: grid of 5 rows and 3 columns plus "Check" and "Close" buttons at the bottom (no logic) -----
            self.setGeometry(950, 300, 6, 3)  #width, height, rows, columns

            #create controls and place them in the window
            self.grid = [[lang(32101),         lang(32102),     lang(32103)],  #Device"                    "Address" "Latency (Kodi <-> Device)"
                         ["1. " + lang(32104), local_router,    ""         ],  #"Local network router"
                         ["2. " + lang(32105), internet_server, ""         ],  #"Nearby Internet server"
                         ["3. " + lang(32106), backend_router,  ""         ],  #"Tvheadend server's router"
                         ["4. " + lang(32107), backend_service, ""         ]]  #"Tvheadend server (TCP)"
            for row in range(len(self.grid)):
                for col in range(len(self.grid[0])):
                    self.grid[row][col] = pyxbmct.Label(self.grid[row][col])  #now it is a grid of labels
                    self.placeControl(self.grid[row][col], row, col)

            self.button1 = pyxbmct.Button(lang(32120)); self.placeControl(self.button1, 5, 0, 1, 1)  #"Check"
            self.button2 = pyxbmct.Button(lang(32121)); self.placeControl(self.button2, 5, 1, 1, 1)  #"Close"

            #actions
            self.connect(self.button1,            self.check)
            self.connect(self.button2,            self.close)
            self.connect(pyxbmct.ACTION_NAV_BACK, self.close)

            #navigation between buttons
            self.button1.controlLeft(self.button2);  self.button2.controlLeft(self.button1)
            self.button1.controlRight(self.button2); self.button2.controlRight(self.button1)

            #--------------- check network health on startup ---------------
            self.show()
            self.check()

            #initial focus
            self.setFocus(self.button1)
        except Exception as msg:
            xbmc.log("AddOnLog: Tvheadend route latencies: " + str(msg), level=xbmc.LOGDEBUG)

    #Calculate latencies
    def task(self, i): #i = 1...4
        rtt_method = ping if i != 4 else http_rtt
        self.grid[i][2].setLabel(rtt_method(self.grid[i][1].getLabel(), self.testlength))

    def checkSingleThreaded(self):
        for i in [1, 2, 3, 4]:
            self.task(i)

    def checkMultiThreaded(self):
        threads = [threading.Thread(target=self.task, args=(i,)) for i in [1, 2, 3, 4]]  #create a list of threads
        for t in threads:
            t.start()
            xbmc.sleep(250)            #wait 250ms to not sent requests to all devices in the same moment at the beginning
        for t in threads: t.join()     #wait until all threads finish

    def check(self):
        self.grid[1][1].setLabel(xbmc.getInfoLabel('Network.GatewayAddress'))  #update address of local router in case of change
        self.button1.setEnabled(False)
        if (ADDON.getSetting("testconcurrently") == "true"):
            self.checkMultiThreaded()
        else:
            self.checkSingleThreaded()
        self.button1.setEnabled(True)

if __name__ == '__main__':
    window = TVNetworkHealthWindow()
    window.doModal()
    del window

