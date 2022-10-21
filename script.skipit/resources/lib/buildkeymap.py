import os
import xbmcvfs
import xbmc


def setup_keymap_folder():
    if not os.path.exists(userdata):
        os.makedirs(userdata)

def write_keymap(file):
    
    setup_keymap_folder()
    # if the skipit keymapfile already exists do nothing
    if os.path.exists(file):
        exit

    keymapxml = open(file,"w")
    keymapxml.write("<keymap><fullscreenvideo><keyboard>")
    keymapxml.write("<key id=\"61571\">runaddon(script.skipit)</key>")
    keymapxml.write("</keyboard></fullscreenvideo></keymap>")
    
    keymapxml.close()
    
monitor = xbmc.Monitor()

if monitor.abortRequested():
    exit

userdata = xbmcvfs.translatePath("special://userdata/keymaps")
skipit_keymap_file = os.path.join(userdata, "skipit.xml")

xbmc.log('Write keymap: ' + skipit_keymap_file, xbmc.LOGDEBUG)
write_keymap(skipit_keymap_file)

xbmc.executebuiltin("action(reloadkeymaps)")
