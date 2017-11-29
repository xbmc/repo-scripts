# This script should be called in the settings dialog of other addons that use the dropbox API.
# example (from settings.xml):
# <setting id="dropbox_apikey" type="action" label="30023" action="RunScript(script.module.dropbox, ADDON_TARGET_ID, dropbox_apikey, DROPBOX_APP_KEY, DROPBOX_APP_SECRET)" />
# 
# This script authorizes with dropbox by using the given App key (has to be requested at dropbox) and the app secret.
# The registration token will be written back to the settings of the calling addon (with given id and settings name)

import xbmc, xbmcgui, xbmcaddon, xbmcvfs
import os, sys
from lib.dropbox import DropboxOAuth2FlowNoRedirect

# PIL needed for QR code generation (source code from qr-code.py from service.linuxwhatelse.notify)
'''
The QR-Code module used need the PIL (Python Image Library) to draw
the image. On some platforms (like android) PIL isn't available so
we check for the availability of this module and in case it is not
available we show a notification informing the user about it
'''
try:
    import PIL
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False
import qrcode    

import resources.utils as utils


# parse input arguments
if len(sys.argv) == 5:#
    ADDON_TARGET_ID = sys.argv[1] # id of the calling addon
    SETTINGNAME_TARGET = sys.argv[2] # name of the settings field where the output is written to
    DROPBOX_APP_KEY = sys.argv[3]
    DROPBOX_APP_SECRET = sys.argv[4]
else:
    utils.log('expecting 5 input arguments for Target Addon Id, Setting Name, Dropbox App key and secret. Received %d:' % len(sys.argv), xbmc.LOGERROR)
    utils.log(str(sys.argv), xbmc.LOGNOTICE)
    utils.showNotification(utils.getString(32102), utils.getString(32202))
    sys.exit(1)
        

# Define a class for the Dialog to show the URL
class MyClass(xbmcgui.WindowDialog):
  # Opening a xbmcgui.Window does not work, since the open settings dialog prevents this (http://forum.kodi.tv/showthread.php?tid=262100&pid=2263074#pid2263074)
  # Use xbmcgui.WindowDiaolog to be able to show the QR-code image
  def __init__(self, authorize_url):
      
    # save window resolution to arrange the text fields an QR code
    screenx = self.getWidth()
    screeny = self.getHeight()
    utils.log('Screen resolution: %dx%d' % (screenx, screeny), xbmc.LOGDEBUG)
    # Show Dialog with Dropbox Authorization URL

    res_qr_code = [0,0] # resolution of the QR-code image.
    # Show QR-Code Dropbox Authorization URL (source code from qr-code.py from service.linuxwhatelse.notify)
    if PIL_AVAILABLE:
        tmp_dir = os.path.join(utils.data_dir()) # tmp_dir has to exist
        tmp_file = os.path.join(tmp_dir, 'dropbox-auth-qr-code.png')
        # Create the QR-code image and save it to temp direcotry
        qr = qrcode.main.QRCode(box_size=40, border=2)
        qr.add_data(authorize_url)
        qr.make(fit=True)
        img = qr.make_image()
        img.save(tmp_file)
        # Show the QR-Code in Kodi
        # http://www.programcreek.com/python/example/84322/xbmcgui.getCurrentWindowId
        utils.log('Add control image with %dx%d at (%d,%d)' % (screeny/2, screeny/2, 100, 100), xbmc.LOGDEBUG)
        res_qr_code = [screeny/4, screeny/4] # TODO: the image is displayed bigger than the desired size. Find out why.
        image = xbmcgui.ControlImage(100, 100, res_qr_code[0], res_qr_code[1], tmp_file)
        self.addControl(image)
    else:
        # The PIL module isn't available so we inform the user about it
        utils.showNotification(utils.getString(32102), utils.getString(32201))

    # Print the Information text below the QR code
    self.addControl(xbmcgui.ControlLabel(x=100, y=(100+res_qr_code[1]+ 50), width=screenx, height=25, label=utils.getString(32704), textColor='0xFFFFFFFF'))
    self.addControl(xbmcgui.ControlLabel(x=100, y=(100+res_qr_code[1]+100), width=screenx, height=25, label=authorize_url, textColor='0xFFFFFFFF'))
    self.addControl(xbmcgui.ControlLabel(x=100, y=(100+res_qr_code[1]+150), width=screenx, height=25, label=utils.getString(32705), textColor='0xFFFFFFFF'))

    # this shows the window on the screen
    self.show()

  def onAction(self, action):
    # the window will be closed with any key
    self.close()


utils.log('Starting Dropbox authentification with key %s and secret %s' % (DROPBOX_APP_KEY, DROPBOX_APP_SECRET), xbmc.LOGDEBUG)
# start dropbox authentification
flow = DropboxOAuth2FlowNoRedirect(DROPBOX_APP_KEY, DROPBOX_APP_SECRET)
authorize_url = flow.start()
# display URL
mydisplay = MyClass(authorize_url)
mydisplay.doModal()
del mydisplay

# Open dialog to input the confirmation code.
dialog = xbmcgui.Dialog()
code = dialog.input(utils.getString(32703), type=xbmcgui.INPUT_ALPHANUM).strip()

if code == '':
    # empty code, aborted
    utils.log('Entered an empty authorization code. Abort.', xbmc.LOGDEBUG)
    sys.exit(0);
    
# finish authentification by sending the code to dropbox
try:
    token = flow.finish(code).access_token
except Exception as e:
    dialog.ok(utils.getString(32103), utils.getString(32706), str(e))
    sys.exit(1);

# positive notification
utils.showNotification(utils.getString(32103), utils.getString(32707))

# return the token to the calling script. That means writing the token in the pre-defined settings field
__Addon_Target = xbmcaddon.Addon(ADDON_TARGET_ID)
__Addon_Target.setSetting(SETTINGNAME_TARGET,token)
