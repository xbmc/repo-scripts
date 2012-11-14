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


__scriptname__ = "Linphonec"
__author__     = "Team PostMet"
__GUI__        = "Postmet Corp"
__scriptId__   = "script.linphone"
__settings__   = xbmcaddon.Addon(id=__scriptId__)
__language__   = __settings__.getLocalizedString
__version__    = __settings__.getAddonInfo("version")
__cwd__        = __settings__.getAddonInfo('path')

BASE_RESOURCE_PATH = xbmc.translatePath( os.path.join( __cwd__, "resources", "lib" ) )
sys.path.append (BASE_RESOURCE_PATH)

xbmc.log("##### [%s] - Version: %s" % (__scriptname__,__version__,),level=xbmc.LOGDEBUG )
is_full_ver = 0

if ( __name__ == "__main__" ):
    import gui
    #os.system("mv /home/"+os.getenv("USER")+"/.linphonerc2 /home/"+os.getenv("USER")+"/.linphonerc")
    os.system("touch /home/"+os.getenv("USER")+"/.linphonerc")

    f = open(__cwd__+'/resources'+'/settings.xml.base')
    settings = f.readlines()
    f.close()
    try:
        f1 = open(__cwd__+'/soundcards')
    except:
        os.system("touch %s" % (__cwd__+'/soundcards'))
        f1 = open(__cwd__+'/soundcards')
    soundcards = f1.readlines()
    f1.close()
    new_string = ''
    for i in soundcards:
        new_string = new_string + i[2:] + '|'

    new_settings = ['    <setting id="capture_list" type="enum" label="30311" values="%s" default="0" />\n' % (new_string[:-1]), '    <setting id="playback_list" type="enum" label="30312" values="%s" default="0" />\n' % (new_string[:-3]), '  </category>\n']
    settings = settings[:-3] + new_settings + settings[-3:]
    f = open(__cwd__+'/resources'+'/settings.xml', 'w')
    for i in settings:
        if is_full_ver != 1 and i.find("multimedia_size") > 0:
            i = '<setting id="multimedia_size" type="enum" label="30213" values="svga(800x600)|4cif(704x576)|vga(640x480)|ios-medium(360x480)|cif(352x288)|qvga(320x240)|qcif(176x144)" default="0" visible="eq(-1,false)"/>'
        f.write(i)
    f.close()

    ui = gui.GUI( "%s.xml" % __scriptId__.replace(".","-") , __cwd__, "Default")
    ui.doModal()
    del ui
    sys.modules.clear()
