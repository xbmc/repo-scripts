'''
Adapted from https://github.com/thodnev/MonkeyTest
I/O Benchmark -- test your hard drive read-write speed in Python
A simplistic script to show that such system programming
tasks are possible and convenient to be solved in Python

I haven't done any command-line arguments parsing, so
you should configure it using the constants below.

The file is being created, then Wrote with random data, randomly read
and deleted, so the script doesn't waste your drive

(!) Be sure, that the file you point to is not smthng
    you need, cause it'll be overWrote during test

Runs on both Python3 and 2, despite that I prefer 3
Has been tested on 3.5 and 2.7 under ArchLinux
'''
from __future__ import division, print_function	# for compatability with py2

import os, sys
import xbmc, xbmcgui, xbmcplugin, xbmcvfs, xbmcaddon
from random import shuffle

try:                    # if Python >= 3.3 use new high-res counter
    from time import perf_counter as time
except ImportError:     # else select highest available resolution counter
    if sys.platform[:3] == 'win':
        from time import clock as time
    else:
        from time import time

# Plugin Info
ADDON_ID       = 'script.io.benchmark'
REAL_SETTINGS  = xbmcaddon.Addon(id=ADDON_ID)
ADDON_ID       = REAL_SETTINGS.getAddonInfo('id')
ADDON_NAME     = REAL_SETTINGS.getAddonInfo('name')
ADDON_PATH     = (REAL_SETTINGS.getAddonInfo('path').decode('utf-8'))
ADDON_VERSION  = REAL_SETTINGS.getAddonInfo('version')
SETTINGS_LOC   = REAL_SETTINGS.getAddonInfo('profile')
ICON           = os.path.join(ADDON_PATH, 'icon.png')
FANART         = os.path.join(ADDON_PATH, 'fanart.jpg') 

# change the constants below according to your needs
WRITE_MB       = 128    # total MBs Wrote during test
WRITE_BLOCK_KB = 1024   # KBs in each write block
READ_BLOCK_B   = 512    # bytes in each read block (high values may lead to
                        # invalid results because of system I/O scheduler        
                        # file must be at drive under test
ADDON_FILE   = os.path.join((xbmc.translatePath(ADDON_PATH)),'test.tmp')
SETTINGS_FILE= os.path.join((xbmc.translatePath(SETTINGS_LOC)),'test.tmp')
if xbmcvfs.exists(SETTINGS_LOC) == False:
    xbmcvfs.mkdirs(SETTINGS_LOC)

def log(msg, level = xbmc.LOGDEBUG):
    xbmc.log(ADDON_ID + '-' + ADDON_VERSION + '-' + str(msg), level)
    
def showText(text, heading=ADDON_NAME):
    log("utils: showText")
    id = 10147
    xbmc.executebuiltin('ActivateWindow(%d)' % id)
    xbmc.sleep(100)
    win = xbmcgui.Window(id)
    retry = 50
    while (retry > 0):
        try:
            xbmc.sleep(10)
            retry -= 1
            win.getControl(1).setLabel(heading)
            win.getControl(5).setText(text)
            return
        except:
            pass
     
def okay(line1= '', line2= '', line3= '', header=ADDON_NAME):
    dlg = xbmcgui.Dialog()
    dlg.ok(header, line1, line2, line3)
    del dlg
         
def write_test(file, block_size, blocks_count, show_progress=None):
    log('write_test, file = ' + file)
    '''
    Tests write speed by writing random blocks, at total quantity
    of blocks_count, each at size of block_size bytes to disk.
    Function returns a list of write times in sec of each block.
    '''
    f = os.open(file, os.O_CREAT|os.O_WRONLY, 0o777) # low-level I/O

    took = []
    for i in range(blocks_count): 
        if show_progress:    
            if (show_progress.iscanceled()) == True:
                return
            show_progress.update(int((i+1)*100/blocks_count),"Writing...",file)
        buff = os.urandom(block_size)
        start = time()
        os.write(f, buff)
        os.fsync(f)	# force write to disk
        t = time() - start
        took.append(t)
    os.close(f)
    log('write_test, return')
    return took
   
def read_test(file, block_size, blocks_count, show_progress=None):
    log('read_test, file = ' + file)
    '''
    Performs read speed test by reading random offset blocks from
    file, at maximum of blocks_count, each at size of block_size
    bytes until the End Of File reached.
    Returns a list of read times in sec of each block.
    '''
    f = os.open(file, os.O_RDONLY, 0o777) # low-level I/O
    # generate random read positions
    offsets = list(range(0, blocks_count*block_size, block_size))
    shuffle(offsets)
    took = []
    for i, offset in enumerate(offsets, 1):
        if show_progress and i % int(WRITE_BLOCK_KB*1024/READ_BLOCK_B) == 0:    
            if (show_progress.iscanceled()) == True:
                return
            # read is faster than write, so try to equalize print period
            show_progress.update(int((i+1)*100/blocks_count),"Reading...",file)
        start = time()
        os.lseek(f, offset, os.SEEK_SET) # set position
        buff = os.read(f, block_size) # read from position
        t = time() - start
        if not buff: break # if EOF reached
        took.append(t)
    os.close(f)
    log('read_test, return')
    return took

TEST_PATHS = None
try:
    params = dict( arg.split( '=' ) for arg in sys.argv[ 1 ].split( '&' ) )
except:
    params = {}
if params and len(params.get('paths')) > 0:
    TEST_PATHS = (params.get('paths','')).split(',')
elif params and len(params.get('path')) > 0:
    TEST_PATHS = [params.get('path','')]
else:
    TEST_PATHS = [ADDON_FILE,SETTINGS_FILE]

okay('Kodi is about to perform a benchmark','Please do not interfere','Results will display when finished')
progress = xbmcgui.DialogProgress()
progress.create(ADDON_NAME,'','','') 
result = ''

for FILE in list(set(TEST_PATHS)): 
    try:
        result += ('[COLOR=gold]%s[/COLOR]\n'%(xbmc.translatePath(FILE)))
         
        wr_blocks      = int(WRITE_MB*1024/WRITE_BLOCK_KB)
        rd_blocks      = int(WRITE_MB*1024*1024/READ_BLOCK_B)  
        write_results = write_test(FILE, 1024*WRITE_BLOCK_KB, wr_blocks, progress)
        progress.update(0)
        read_results = read_test(FILE, READ_BLOCK_B, rd_blocks, progress)
        
        #Statistics from http://hdd.userbenchmark.com/
        if WRITE_MB/sum(write_results) < 148:
            WCOLOR = 'red'
        elif WRITE_MB/sum(write_results) > 181:
            WCOLOR = 'green'
        else:
            WCOLOR = 'orange'

        if WRITE_MB/sum(read_results) < 164:
            RCOLOR = 'red'
        elif WRITE_MB/sum(read_results) > 194:
            RCOLOR = 'green'
        else:
            RCOLOR = 'orange'

        result += ('\nWrote [COLOR=blue]{0} MB[/COLOR] in [COLOR=blue]{1:.4f}s[/COLOR]\nWrite speed is [COLOR={2}]{3:.2f} MB/s[/COLOR]'
                   '\nmax: [COLOR=blue]{4:.2f}[/COLOR], min: [COLOR=blue]{5:.2f}[/COLOR]\n'.format(
                   WRITE_MB, sum(write_results), WCOLOR, WRITE_MB/sum(write_results),
                   (WRITE_BLOCK_KB/(1024*min(write_results))), (WRITE_BLOCK_KB/(1024*max(write_results)))))
                     
        result += ('\nRead [COLOR=blue]{0} x {1} B[/COLOR] blocks in [COLOR=blue]{2:.4f}s[/COLOR]\nRead speed is [COLOR={3}]{4:.2f} MB/s[/COLOR]'
                   '\nmax: [COLOR=blue]{5:.2f}[/COLOR], min: [COLOR=blue]{6:.2f}[/COLOR]\n'.format(
                   len(read_results), READ_BLOCK_B, sum(read_results), RCOLOR, WRITE_MB/sum(read_results),
                   (READ_BLOCK_B/(1024*1024*min(read_results))), (READ_BLOCK_B/(1024*1024*max(read_results)))))

        progress.update(0)
    except Exception,e:
        result += ('\n[COLOR=red]Benchmark Failed![/COLOR]')
        result += ('\n[COLOR=red]%s[/COLOR]\n'%str(e))
        
    result += ('[COLOR=gold]---------------------------------------------------------------------------------------------------------------------------------------------------------------[/COLOR]\n')
        
result += ('[COLOR=red]RED=BAD[/COLOR][COLOR=gray]----[/COLOR][COLOR=orange]ORANGE=AVERAGE[/COLOR][COLOR=gray]----[/COLOR][COLOR=green]GREEN=GREAT[/COLOR]')

for FILE in TEST_PATHS:
    for i in range(3):
        if i == 3:
            okay('Error deleting',File,'Check Kodi permissions')
            break
        try:
            os.remove(FILE)
            continue
        except:
            xbmc.sleep(10)
del progress        
showText(result)