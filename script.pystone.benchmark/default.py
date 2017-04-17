#   Copyright (C) 2017 Lunatixz
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

import os, re, sys, platform, pystone
import xbmc, xbmcgui, xbmcplugin, xbmcvfs, xbmcaddon

# Plugin Info
ADDON_ID       = 'script.pystone.benchmark'
REAL_SETTINGS  = xbmcaddon.Addon(id=ADDON_ID)
ADDON_NAME     = REAL_SETTINGS.getAddonInfo('name')
ADDON_PATH     = (REAL_SETTINGS.getAddonInfo('path').decode('utf-8'))
ADDON_VERSION  = REAL_SETTINGS.getAddonInfo('version')
SETTINGS_LOC   = REAL_SETTINGS.getAddonInfo('profile')
ICON           = os.path.join(ADDON_PATH, 'icon.png')
FANART         = os.path.join(ADDON_PATH, 'fanart.jpg') 
LOOPS          = 50000

def main(loops=LOOPS):
    benchtime, stones = pystone.pystones(loops)
    stones = int(round(stones))
    REAL_SETTINGS.setSetting("pystone",str(stones))
    plat = '[COLOR=%s]%s[/COLOR]'% ('blue', detectPlatform())
    pyver = '[COLOR=%s]v%s[/COLOR]'% ('blue', str(platform.python_version()))
    pystver = '[COLOR=%s]v%s[/COLOR]'% ('blue', str(1.1))
    
    # http://tiborsimko.org/python-speed-amd-vs-intel.html , https://pybenchmarks.org/u64q/performance.php?test=pystone
    maxm = 200000
    minn = 2000
    avg  = ((stones - minn) * 100) // maxm
    msg = 'Top ' if avg > 50 else 'Bottom '
    
    if avg >= 75:
        color = 'green'
    elif avg >= 50:
        color = 'yellow'
    elif avg <= 25:
        color = 'red'
    else:
        color = 'orange'
        
    stat = '[COLOR=%s]%g[/COLOR]'% (color, stones)
    space1 = repeat_to_length(' ',100 - avg)
    space2 = repeat_to_length(' ',avg-1)
    space3 = repeat_to_length(' ',(100 - avg) - len(msg))
    arrow = '%s^%s[CR]%s%s[COLOR=%s]%d%s[/COLOR]%s'%(space1,space2,space3,msg,color,avg,'%',space2)
    back = '[COLOR=dimgrey][I] Back [/I] or [I]Okay [/I] to exit[/COLOR]'
    results = 'Python 2.7 Comparison[CR]Intel - i7 [[COLOR=blue]%d[/COLOR]] | i3 [[COLOR=blue]%d[/COLOR]] | Core2 DUO [[COLOR=blue]%d[/COLOR]][CR]AMD - Athlon XP 2500+ [[COLOR=blue]%d[/COLOR]][CR]ARM - v7 [[COLOR=blue]%d[/COLOR]] | v6 [[COLOR=blue]%d[/COLOR]]'%(140000,70000,50000,30000,10000,5000)
    showText("Pystone (%s) time for %d passes = %g [CR]This machine [ %s ][CR]Python [%s] benchmarks at %s pystones/second [CR][CR][COLOR=green]-------------------------[/COLOR][COLOR=yellow]-------------------------[/COLOR][COLOR=orange]-------------------------[/COLOR][COLOR=red]-------------------------[/COLOR][CR]%s[CR][CR]%s[CR]%s"%(pystver ,loops, benchtime, plat, pyver, stat, arrow, results, back))

def log(msg, level = xbmc.LOGDEBUG):
    xbmc.log(ADDON_ID + '-' + ADDON_VERSION + '-' + str(msg), level)

def showText(text, header=ADDON_NAME):
    xbmcgui.Dialog().textviewer(header, text)

def okay(line1= '', line2= '', line3= '', header=ADDON_NAME):
    dlg = xbmcgui.Dialog()
    dlg.ok(header, line1, line2, line3)
    del dlg

def detectPlatform():
    plat = pi_version()
    if plat == 'Unknown':
        try:
            plat = (platform.processor() or platform.platform())
        except:
            plat = 'Unknown'    
    if plat.startswith('arm'):
        plat = 'ARM Architecture'
    return plat
        
def pi_version():
    """Detect the version of the Raspberry Pi.  Returns either 1, 2 or
    None depending on if it's a Raspberry Pi 1 (model A, B, A+, B+),
    Raspberry Pi 2 (model B+), or not a Raspberry Pi.
    """
    # Check /proc/cpuinfo for the Hardware field value.
    # 2708 is pi 1
    # 2709 is pi 2
    # 2835 is pi 3 on 4.9.x kernel
    # Anything else is not a pi.
    try:
        with open('/proc/cpuinfo', 'r') as infile:
            cpuinfo = infile.read()
        # Match a line like 'Hardware   : BCM2709'
        match = re.search('^Hardware\s+:\s+(\w+)$', cpuinfo,
                          flags=re.MULTILINE | re.IGNORECASE)
        if match.group(1) == 'BCM2708':
            # Pi 1
            return 'Raspberry Pi 1, BCM2708'
        elif match.group(1) == 'BCM2709':
            # Pi 2
            return 'Raspberry Pi 2, BCM2709'
        elif match.group(1) == 'BCM2835':
            # Pi 3 / Pi on 4.9.x kernel
            return 'Raspberry Pi 3, BCM2835'
        return 'Unknown'
    except:
        return 'Unknown'

def repeat_to_length(string_to_expand, length):
   return (string_to_expand * ((length/len(string_to_expand))+1))[:length]

if __name__ == '__main__':
    main(LOOPS)