import sys
import xbmc
import xbmcplugin
import xbmcaddon
from resources.lib import mainmenu
from resources.lib.utilities import tweet
from resources.lib.utilities import  sina_tweet
from resources.lib.utilities import keymapeditor


def get_params():
    pairsofparams = []
    if len(sys.argv) >= 2:
        params=sys.argv[1]
        pairsofparams=params.split('/')
        pairsofparams = [parm for parm in pairsofparams if parm]
    return pairsofparams

params=get_params()

if not params:
    if "script-sinaweibo-MainMenu.xml" not in xbmc.getInfoLabel('Window.Property(xmlfile)'):
        #xbmc.executebuiltin("Notification(%s, %s, %d, %s)" % ('weilcome', 'Thanks for using this addon', 4000, xbmcaddon.Addon().getAddonInfo('icon')))
        mainmenu.start()
else:
    # Integration patterns below
    if params[0] == "removetwitterhistory":
        tweet.remove_twitter_hashtag_history()
    elif params[0] == "removetweibohistory":
        sina_tweet.remove_twitter_hashtag_history()
    elif params[0] == "keymapeditor":
        keymapeditor.run()

try:
    xbmcplugin.endOfDirectory(int(sys.argv[1]))
except:
    sys.exit(0)