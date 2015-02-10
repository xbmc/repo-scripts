# -*- coding: utf-8 -*-
# *
# *      Copyright © 2012 Postmet Corp.
# *      http://www.postmet.com
# *      Created by: Perepelyatnik Peter, Jermakovich Alexander <team@postmet.com>
# *
# *
# * To add to zip file: zip script.linphone.zip script.linphone/* -r

import sys
import os
import xbmcaddon
import subprocess as sub
import time
import xbmc
import xbmcgui

__scriptname__ = "Linphonec"
__author__     = "Team PostMet"
__GUI__        = "Postmet Corp"
__scriptId__   = "script.linphone"
__license__    = 0
__settings__   = xbmcaddon.Addon(id=__scriptId__)
__language__   = __settings__.getLocalizedString
__version__    = __settings__.getAddonInfo("version")
__cwd__        = __settings__.getAddonInfo('path')

uparts = ["saturn.postmet.com/pub/", "saturn.postmet.com/priv/", "linphone_3.5.0-1_i386.deb", "linphone_3.5.0-2_i386.deb"]
linphone_path  = '/usr/local/bin/linphonecsh'
#__video_codecs__ = ['H264']
__audio_codecs__ = ['speex (16'] #'speex (32',
FIRST_RUN = 1
BASE_RESOURCE_PATH = xbmc.translatePath( os.path.join( __cwd__, "resources", "lib" ) )
sys.path.append (BASE_RESOURCE_PATH)

xbmc.log("##### [%s] - Version: %s" % (__scriptname__,__version__,),level=xbmc.LOGDEBUG )


if ( __name__ == "__main__" ):
    import gui
    #os.system("mv /home/"+os.getenv("USER")+"/.linphonerc2 /home/"+os.getenv("USER")+"/.linphonerc")
    os.system("touch /home/"+os.getenv("USER")+"/.linphonerc")

    import os.path
    if os.path.exists(linphone_path):
        os.system('killall -9 linphonec')
        installed = 1
    else:
        installed = 0
        file_name = uparts[2]
        if __license__:
            keyboard = xbmc.Keyboard("Please enter web login:password")
            keyboard.doModal()
            if keyboard.isConfirmed():
                auth_data = keyboard.getText()
                os.system("wget http://" + auth_data + "@" + uparts[1] + uparts[3])
            if os.path.exists('/home/'+os.getenv("USER")+'/'+uparts[3]):
                file_name = uparts[3]
            else:
                os.system("wget http://" + uparts[0] + uparts[2])
        else:
            os.system("wget http://" + uparts[0] + uparts[2])

        if os.path.exists('/home/'+os.getenv("USER")+'/'+file_name):
            keyboard = xbmc.Keyboard("Please enter sudo password to install Linphone")
            keyboard.doModal()
            if keyboard.isConfirmed():
                xbmc_pwd = keyboard.getText()
                if xbmc_pwd:
                    linfo = sub.Popen('echo "' + xbmc_pwd + '" | sudo -S dpkg -i '+file_name, shell=True, stdout=sub.PIPE).stdout.readlines()
                    for l in linfo:
                        installed = 1
                        xbmc.log('Linphone SETUP: %s' % (l))
    if not installed:
        dialog = xbmcgui.Dialog()
        dialog.ok("Error executing linphone", "Error installing linphone to " + linphone_path + "\n ",
                                   "(Wrong password specified?). \nYou can also install it maually from ",
                                   " \n" + uparts[0] + uparts[2])
        sys.exit()

    try:
        f = open(__cwd__+'/resources/settings.xml', 'r')
        FIRST_RUN = 0
    except:
        FIRST_RUN = 1
        cmd = 'bash -c "' + linphone_path + ' init"'
        os.system(cmd)
        time.sleep(1)
        soundcards = sub.Popen(linphone_path + " generic 'soundcard list'", shell=True, stdout=sub.PIPE).stdout.readlines()
        new_string = ''
        for i in soundcards:
            new_string = new_string + i.strip()[2:] + '|'
        capture_list = '    <setting id="capture_list" type="enum" label="30311" values="%s" default="0" />\n' % (new_string)
        playback_list = '    <setting id="playback_list" type="enum" label="30312" values="%s" default="0" />\n' % (new_string)

        soundcards = sub.Popen(linphone_path + " generic 'soundcard list'", shell=True, stdout=sub.PIPE).stdout.readlines()
        new_string = ''
        for i in soundcards:
            new_string = new_string + i.strip()[2:] + '|'

        lines = sub.Popen(linphone_path + " generic 'vcodec list'", shell=True, stdout=sub.PIPE).stdout.readlines()
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
