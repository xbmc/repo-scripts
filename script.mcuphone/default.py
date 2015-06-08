# -*- coding: utf-8 -*-
# *
# *      Copyright © 2012-2015 Postmet Corp.
# *      http://www.postmet.com
# *      Created by:Jermakovich Alexander, Anikin Alexander <team@postmet.com>
# *
# *
# zip -r script.mcuphone-1.0.10.zip script.mcuphone/

import sys
import os,stat
import xbmcaddon
import subprocess as sub
import time
import xbmc
import xbmcgui
import platform as pl

__scriptname__ = "mcuphone"
__author__     = "Team PostMet"
__GUI__        = "Postmet Corp"
__scriptId__   = "script.mcuphone"
__license__    = 1
__settings__   = xbmcaddon.Addon(id=__scriptId__)
__language__   = __settings__.getLocalizedString
__version__    = __settings__.getAddonInfo("version")
__cwd__        = __settings__.getAddonInfo('path')

PHONE_CONFIG   = xbmc.translatePath( os.path.join( __cwd__,'resources', '.mcuphonerc'))
PHONE_LOG      = '/home/' + os.getenv("USER") + '/mcuphone.log'
PHONE_TERMINATE = 'killall -9 mcuphonec'
PHONE_PATH     = xbmc.translatePath( os.path.join( __cwd__,'resources', 'bin', 'mcuphonecsh.' + pl.machine() + '.bin'))
ORIG_DAEMON_PATH    = xbmc.translatePath( os.path.join( __cwd__,'resources', 'bin', 'mcuphonec.' + pl.machine() + '.bin' ))
DAEMON_PATH    = xbmc.translatePath( os.path.join( __cwd__,'resources', 'bin', 'mcuphonec'))

FIRST_RUN = 1
BASE_RESOURCE_PATH = xbmc.translatePath( os.path.join( __cwd__, "resources", "lib" ) )
sys.path.append (BASE_RESOURCE_PATH)

xbmc.log("##### [%s] - Version: %s" % (__scriptname__,__version__,),level=xbmc.LOGDEBUG )
xbmc.log("##### PHOME_PATH: %s" % (PHONE_PATH),level=xbmc.LOGDEBUG )

def ensure_exec_perms(file_):
    st = os.stat(file_)
    os.chmod(file_, st.st_mode | stat.S_IEXEC)
    return file_


if ( __name__ == "__main__" ):
    ensure_exec_perms(PHONE_PATH)
    ensure_exec_perms(ORIG_DAEMON_PATH)
    import gui
    os.system("touch " + PHONE_CONFIG)

    import os.path
    if not __settings__.getSetting("pip_active"):
        os.system(PHONE_TERMINATE)

    try:
        f = open(__cwd__+'/resources/settings.xml', 'r')
        FIRST_RUN = 0
	xbmc.log("##### PHOME FIRST") # % level=xbmc.LOGDEBUG )
    except:
        FIRST_RUN = 1

	if not os.path.isfile(DAEMON_PATH):
	   os.symlink(ORIG_DAEMON_PATH, DAEMON_PATH)

        cmd = 'bash -c "' + PHONE_PATH + ' init"'
        os.system(cmd)
	xbmc.log("##### PHOME SYSTEM: %s" % cmd, level=xbmc.LOGDEBUG )
        time.sleep(1)
        soundcards = sub.Popen(PHONE_PATH + " generic 'soundcard list'", shell=True, stdout=sub.PIPE).stdout.readlines()
        new_string = ''
        is_playback = 0
        is_capture = 0
        capture_list = ''
        playback_list = ''
        for i in soundcards:
            if i.find('layback device') > 0:
                is_playback = 1
                is_capture = 0
            elif i.find('apture device') > 0:
                is_playback = 0
                is_capture = 1
            elif is_playback == 1:
                playback_list += i.strip()[2:] + '|'
            elif is_capture == 1:
                capture_list += i.strip()[2:] + '|'

        playback_list = '    <setting id="playback_list" type="enum" label="30312" values="%s" default="0" />\n' % (playback_list)
        capture_list = '    <setting id="capture_list" type="enum" label="30311" values="%s" default="0" />\n' % (capture_list)

        lines = sub.Popen(PHONE_PATH + " generic 'vcodec list'", shell=True, stdout=sub.PIPE).stdout.readlines()
        h264 = 0
        vp8 = 0
        for line in lines:
            if line.find('H264') > 0:
                h264 = 1
            if line.find('VP8') > 0:
                vp8 = 1
        if h264 and vp8:
            codecs = 'H264|VP8|H264+VP8'
        elif vp8:
            codecs = 'VP8'
        else:
            codecs = 'H264'

        f = open(__cwd__+'/resources'+'/settings.xml', 'w')
        fb = open(__cwd__+'/resources'+'/settings.xml.base', 'r')
        settings = fb.readlines()
        for i in settings:
            if i.find("capture_list") > 0:
                f.write(capture_list)
            elif i.find("playback_list") > 0:
                f.write(playback_list)
            elif __license__ != 1 and i.find("multimedia_size") > 0:
                i = '<setting id="multimedia_size" type="enum" label="30213" values="svga(800x600)|4cif(704x576)|vga(640x480)|ios-medium(360x480)|cif(352x288)|qvga(320x240)|qcif(176x144)" default="0" visible="eq(-1,false)"/>'
                f.write(i)
            elif i.find("vcodec_priority") > 0:
                i = '<setting id="vcodec_priority" type="enum" label="30216" values="'+codecs+'" default="0"/>'
                f.write(i)
            else:
                f.write(i)
        fb.close()

    f.close()
    ui = gui.GUI( "%s.xml" % __scriptId__.replace(".","-") , __cwd__, "Default")
    ui.doModal()
    del ui
    sys.modules.clear()
