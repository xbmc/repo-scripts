
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
    stones = stones//10 if len(str(stones)) > 5 else stones
    REAL_SETTINGS.setSetting("cpuBench",str(stones))
    plat = '[COLOR=%s]%s[/COLOR]'% ('blue', detectPlatform())
    
    # http://www.cpubenchmark.net/cpu_list.php
    maxm = 9732 if plat.startswith(('Raspberry','ARM','Unknown')) else 25236
    minn = 58 if plat.startswith(('Raspberry','ARM','Unknown')) else 79
    med  = (maxm - minn) // 2
    msg = 'Top ' if stones > med else 'Bottom '
    
    if stones >= maxm:
        color = 'green'
    elif stones < maxm and stones > med:
        color = 'yellow'
    elif stones < maxm and stones < med:
        color = 'orange'
    else:
        color = 'red'
        
    stat = '[COLOR=%s]%g[/COLOR]'% (color, stones)
    avg  = ((stones - minn) * 100) // maxm
    space1 = repeat_to_length(' ',100 - avg)
    space2 = repeat_to_length(' ',avg-1)
    space3 = repeat_to_length(' ',(100 - avg) - len(msg))
    arrow = '%s^%s[CR]%s%s[COLOR=%s]%d%s[/COLOR]%s'%(space1,space2,space3,msg,color,avg,'%',space2)
    back = '[I] Back [/I] or [I]Okay [/I] to exit'
    showText("Pystone (v%s) time for %d passes = %g [CR]This machine [ %s ] [CR]benchmarks at %s pystones/second [CR][CR][COLOR=green]-------------------------[/COLOR][COLOR=yellow]-------------------------[/COLOR][COLOR=orange]-------------------------[/COLOR][COLOR=red]-------------------------[/COLOR][CR]%s[CR][CR]%s"%(ADDON_VERSION,loops, benchtime, plat, stat, arrow, back))

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