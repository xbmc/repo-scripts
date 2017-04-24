#   Copyright (C) 2017 Lunatixz
#
#
# This file is part of I/O Benchmark.
# The MIT License

# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:

# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.

# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
# THE SOFTWARE.

import os, sys, monkeytest
import xbmc, xbmcgui, xbmcplugin, xbmcvfs, xbmcaddon


# Plugin Info
ADDON_ID       = 'script.io.benchmark'
REAL_SETTINGS  = xbmcaddon.Addon(id=ADDON_ID)
ADDON_NAME     = REAL_SETTINGS.getAddonInfo('name')
ADDON_PATH     = (REAL_SETTINGS.getAddonInfo('path').decode('utf-8'))
ADDON_VERSION  = REAL_SETTINGS.getAddonInfo('version')
SETTINGS_LOC   = REAL_SETTINGS.getAddonInfo('profile')
ICON           = REAL_SETTINGS.getAddonInfo('icon')
FANART         = REAL_SETTINGS.getAddonInfo('fanart')
                        
ADDON_FILE   = os.path.join((xbmc.translatePath(ADDON_PATH)),'test.tmp')
SETTINGS_FILE= os.path.join((xbmc.translatePath(SETTINGS_LOC)),'test.tmp')

if xbmcvfs.exists(SETTINGS_LOC) == False:
    xbmcvfs.mkdirs(SETTINGS_LOC)
     
TEST_PATHS = None
# change the constants below according to your needs
WRITE_MB       = 128    # total MBs Wrote during test
WRITE_BLOCK_KB = 1024   # KBs in each write block
READ_BLOCK_B   = 512    # bytes in each read block (high values may lead to
                        # invalid results because of system I/O scheduler        
                        # file must be at drive under test

def repeat_to_length(string_to_expand, length):
   return (string_to_expand * ((length/len(string_to_expand))+1))[:length]
 
def log(msg, level = xbmc.LOGDEBUG):
    xbmc.log(ADDON_ID + '-' + ADDON_VERSION + '-' + str(msg), level)
    
def showText(text, header=ADDON_NAME):
    xbmcgui.Dialog().textviewer(header, text)
     
def okay(line1= '', line2= '', line3= '', header=ADDON_NAME):
    xbmcgui.Dialog().ok(header, line1, line2, line3)
       
if __name__ == '__main__':
    try:
        params = dict( arg.split( '=' ) for arg in sys.argv[ 1 ].split( '&' ) )
    except:
        params = {}
    if params and len(params.get('paths')) > 0:
        TEST_PATHS = (params.get('paths','')).split(',')
    elif params and len(params.get('path')) > 0:
        TEST_PATHS = [params.get('path','')]
    else:
        TEST_PATHS = [SETTINGS_FILE]

    okay('Kodi is about to perform a I/O benchmark','Please do not interfere.','File cache may impact read results.')
    progress = xbmcgui.DialogProgress()
    progress.create(ADDON_NAME,'','','') 
    result = ''

    for FILE in list(set(TEST_PATHS)): 
        try:   
            #Statistics from http://hdd.userbenchmark.com/  
            result += ('Test Path [COLOR=blue]%s[/COLOR]\n'%(FILE))
            progress.update(0)
            wr_blocks = int(WRITE_MB*1024/WRITE_BLOCK_KB)
            write_results = monkeytest.write_test(FILE, 1024*WRITE_BLOCK_KB, wr_blocks, progress)
            maxw = 158 # Median between types SSD,HDD,FLASH
            minw = 0
            write = (int(round(WRITE_BLOCK_KB/(1024*max(write_results)))) + int(round(WRITE_BLOCK_KB/(1024*min(write_results))))) // 2
            avgw  = ((write - minw) * 100) // maxw
            msgw = 'Top ' if avgw >= 50 else 'Bottom '
                
            if avgw >= 75:
                WCOLOR = 'green'
            elif avgw >= 50:
                WCOLOR = 'yellow'
            elif avgw > 25:
                WCOLOR = 'red'
            else:
                WCOLOR = 'orange'
                
            result += ('\nWrote [COLOR=blue]{0} MB[/COLOR] in [COLOR=blue]{1:.4f}s[/COLOR]\nWrite speed is [COLOR={2}]{3:.2f} MB/s[/COLOR]'
                       ' max: [COLOR=blue]{4:.2f}[/COLOR], min: [COLOR=blue]{5:.2f}[/COLOR]\n'.format(
                       WRITE_MB, sum(write_results), WCOLOR, WRITE_MB/sum(write_results),
                       (WRITE_BLOCK_KB/(1024*min(write_results))), (WRITE_BLOCK_KB/(1024*max(write_results)))))

            space1w = repeat_to_length(' ',100 - avgw)
            space2w = repeat_to_length(' ',avgw-1)
            space3w = repeat_to_length(' ',(100 - avgw) - len(msgw))
            arrow = '%s^%s[CR]%s%s[COLOR=%s]%d%s[/COLOR]%s'%(space1w,space2w,space3w,msgw,WCOLOR,avgw,'%',space2w)
            result += "[COLOR=green]-------------------------[/COLOR][COLOR=yellow]-------------------------[/COLOR][COLOR=orange]-------------------------[/COLOR][COLOR=red]-------------------------[/COLOR][CR]%s"%(arrow)
            REAL_SETTINGS.setSetting("wbBench", str(write_results))  
                           
            progress.update(0)
            rd_blocks = int(WRITE_MB*1024*1024/READ_BLOCK_B) 
            read_results = monkeytest.read_test(FILE, READ_BLOCK_B, rd_blocks, progress)
            maxr = 183 # Median between typesSSD,HDD,FLASH
            minr = 0
            read = (int(round(READ_BLOCK_B/(1024*1024*max(read_results)))) + int(round(READ_BLOCK_B/(1024*1024*min(read_results))))) // 2
            avgr  = ((read - minr) * 100) // maxr
            msgr = 'Top ' if avgr >= 50 else 'Bottom '

            if avgr >= 75:
                RCOLOR = 'green'
            elif avgr >= 50:
                RCOLOR = 'yellow'
            elif avgr > 25:
                RCOLOR = 'red'
            else:
                RCOLOR = 'orange'

            result += ('\nRead [COLOR=blue]{0} x {1} B[/COLOR] blocks in [COLOR=blue]{2:.4f}s[/COLOR]\nRead speed is [COLOR={3}]{4:.2f} MB/s[/COLOR]'
                       ' max: [COLOR=blue]{5:.2f}[/COLOR], min: [COLOR=blue]{6:.2f}[/COLOR]\n'.format(
                       len(read_results), READ_BLOCK_B, sum(read_results), RCOLOR, WRITE_MB/sum(read_results),
                       (READ_BLOCK_B/(1024*1024*min(read_results))), (READ_BLOCK_B/(1024*1024*max(read_results)))))

            space1r = repeat_to_length(' ',100 - avgr)
            space2r = repeat_to_length(' ',avgr-1)
            space3r = repeat_to_length(' ',(100 - avgr) - len(msgr))
            arrow = '%s^%s[CR]%s%s[COLOR=%s]%d%s[/COLOR]%s'%(space1r,space2r,space3r,msgr,RCOLOR,avgr,'%',space2r)
            result += "[COLOR=green]-------------------------[/COLOR][COLOR=yellow]-------------------------[/COLOR][COLOR=orange]-------------------------[/COLOR][COLOR=red]-------------------------[/COLOR][CR]%s[CR]"%(arrow)
            REAL_SETTINGS.setSetting("rbBench", str(read_results))
            
            result += ('*Median Results: R[[COLOR=blue]%s MB/s[/COLOR]] W[[COLOR=blue]%s MB/s[/COLOR]]  [COLOR=dimgrey][I] Back [/I] or [I]Okay [/I] to exit[/COLOR]\n'%(str(maxr), str(maxw)))
        except Exception,e:
            result += ('\n[COLOR=red]Benchmark Failed![/COLOR]')
            result += ('\n[COLOR=red]%s[/COLOR]\n'%str(e))

        result += ('[COLOR=dimgrey]*Median results from the best & worst SSD, HDD and Flash benchmarks[/COLOR]')
        
        
    for FILE in TEST_PATHS:
        for i in range(3):
            try:
                os.remove(FILE)
                continue
            except:
                xbmc.sleep(10)
                
    del progress        
    showText(result)