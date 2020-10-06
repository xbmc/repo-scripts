#   Copyright (C) 2020 Lunatixz
#
#
# This file is part of CPU Benchmark.
#
# CPU Benchmark is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# CPU Benchmark is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with CPU Benchmark.  If not, see <http://www.gnu.org/licenses/>.

import os, re, sys, platform, time

from resources.lib import pystone
from resources.lib import platform_detect
from kodi_six      import xbmc, xbmcaddon, xbmcplugin, xbmcgui, xbmcvfs, py2_encode, py2_decode

try:
    from multiprocessing      import cpu_count 
    from multiprocessing.pool import ThreadPool 
    ENABLE_POOL = True
except: ENABLE_POOL = False
    
# Plugin Info
ADDON_ID       = 'script.pystone.benchmark'
REAL_SETTINGS  = xbmcaddon.Addon(id=ADDON_ID)
ADDON_NAME     = REAL_SETTINGS.getAddonInfo('name')
ADDON_PATH     = REAL_SETTINGS.getAddonInfo('path')
ADDON_VERSION  = REAL_SETTINGS.getAddonInfo('version')
SETTINGS_LOC   = REAL_SETTINGS.getAddonInfo('profile')
ICON           = REAL_SETTINGS.getAddonInfo('icon')
FANART         = REAL_SETTINGS.getAddonInfo('fanart')
LANGUAGE       = REAL_SETTINGS.getLocalizedString

def log(msg, level=xbmc.LOGDEBUG):
    xbmc.log('%s-%s-%s'%(ADDON_ID,ADDON_VERSION,msg),level)
    
def textviewer(text, header=ADDON_NAME):
    xbmcgui.Dialog().textviewer(header, text,usemono=True)
    
def ok(text, header=ADDON_NAME):
    xbmcgui.Dialog().ok(header, text)
    
def repeat_to_length(string_to_expand, length):
   length = int(round(length))
   return (string_to_expand * int((length/len(string_to_expand))+1))[:length]

class CPU(object):
    def __init__(self):
        if ENABLE_POOL:#todo multiprocessing
            self.pool = ThreadPool(cpu_count())
        
    
    def getpystone(self):
        maxpystone = 0
        for pyseed in [1000, 2000, 5000, 10000, 20000, 50000, 100000, 200000]:
            duration, pystonefloat = pystone.pystones(pyseed)
            maxpystone = max(maxpystone, int(pystonefloat))
            if duration > 0.1:
                break
        return duration, maxpystone
    
    
    def rank(self, stones):
         #https://pybenchmarks.org/u64q/performance.php?test=pystone
        avg = ((stones - 1400) * 100) // 140000
        msg = LANGUAGE(30002) if avg > 50 else LANGUAGE(30003)
        
        if   avg >= 75: color = 'green'
        elif avg >= 50: color = 'yellow'
        elif avg <= 25: color = 'red'
        else:           color = 'orange'
        
        score   = LANGUAGE(30006)%(platform.python_version(),pystone.__version__,LANGUAGE(30004)%(color,stones))
        space1  = repeat_to_length(' ', 100 - avg)
        space2  = repeat_to_length(' ', avg-1)
        space3  = repeat_to_length(' ', (100 - avg) - len(msg))
        line    = '%s%s%s%s'%(LANGUAGE(30004)%('green',repeat_to_length('-',25)),LANGUAGE(30004)%('yellow',repeat_to_length('-',25)),LANGUAGE(30004)%('orange',repeat_to_length('-',25)),LANGUAGE(30004)%('red',repeat_to_length('-',25)))
        arrow   = '%s^%s[CR]%s%s%s%s%s'%(space1,space2,space3,msg,LANGUAGE(30004)%(color,avg),LANGUAGE(30004)%(color,'%'),space2)
        back    = LANGUAGE(30004)%('dimgrey',LANGUAGE(30005))
        return '%s[CR]%s[CR]%s[CR]%s'%(score, line, arrow, back)


    def run(self):
        duration, stones = self.getpystone()
        info = LANGUAGE(30007)%(platform_detect.platform_detect(),platform_detect.processor_detect(),platform_detect.getcpu(),cpu_count())
        envo = LANGUAGE(30008)%(xbmc.getInfoLabel('System.BuildVersion'),platform.system())
        textviewer('%s[CR]%s[CR]%s'%(envo,info,self.rank(stones)))