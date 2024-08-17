import xbmcgui
import xbmcvfs
import json
import pyqrcode
import resources.lib.tinyurl as tinyurl
import resources.lib.utils as utils
from datetime import datetime

# don't die on import error yet, these might not even get used
try:
    from dropbox import dropbox
    from dropbox import oauth
except ImportError:
    pass


class QRCode(xbmcgui.WindowXMLDialog):
    def __init__(self, *args, **kwargs):
        self.image = kwargs["image"]
        self.text = kwargs["text"]
        self.url = kwargs['url']

    def onInit(self):
        self.imagecontrol = 501
        self.textbox1 = 502
        self.textbox2 = 504
        self.okbutton = 503
        self.showdialog()

    def showdialog(self):
        self.getControl(self.imagecontrol).setImage(self.image)
        self.getControl(self.textbox1).setText(self.text)
        self.getControl(self.textbox2).setText(self.url)
        self.setFocus(self.getControl(self.okbutton))

    def onClick(self, controlId):
        if (controlId == self.okbutton):
            self.close()


class DropboxAuthorizer:
    TOKEN_FILE = "tokens.json"
    APP_KEY = ""
    APP_SECRET = ""

    def __init__(self):
        self.APP_KEY = utils.getSettingStringStripped('dropbox_key')
        self.APP_SECRET = utils.getSettingStringStripped('dropbox_secret')

    def setup(self):
        result = True

        if(self.APP_KEY == '' and self.APP_SECRET == ''):
            # we can't go any farther, need these for sure
            xbmcgui.Dialog().ok(utils.getString(30010), '%s %s\n%s' % (utils.getString(30027), utils.getString(30058), utils.getString(30059)))

            result = False

        return result

    def isAuthorized(self):
        user_token = self._getToken()

        return 'access_token' in user_token

    def authorize(self):
        result = True

        if(not self.setup()):
            return False

        if(self.isAuthorized()):
            # delete the token to start over
            self._deleteToken()

        # copied flow from http://dropbox-sdk-python.readthedocs.io/en/latest/moduledoc.html#dropbox.oauth.DropboxOAuth2FlowNoRedirect
        flow = oauth.DropboxOAuth2FlowNoRedirect(consumer_key=self.APP_KEY, consumer_secret=self.APP_SECRET, token_access_type="offline")

        url = flow.start()

        # print url in log
        utils.log("Authorize URL: " + url)

        # create a QR Code
        shortUrl = str(tinyurl.shorten(url), 'utf-8')
        imageFile = xbmcvfs.translatePath(utils.data_dir() + '/qrcode.png')
        qrIMG = pyqrcode.create(shortUrl)
        qrIMG.png(imageFile, scale=10)

        # show the dialog prompt to authorize
        qr = QRCode("script-backup-qrcode.xml", utils.addon_dir(), "default", image=imageFile, text=utils.getString(30056), url=shortUrl)
        qr.doModal()

        # cleanup
        del qr
        xbmcvfs.delete(imageFile)

        # get the auth code
        code = xbmcgui.Dialog().input(utils.getString(30027) + ' ' + utils.getString(30103))

        # if user authorized this will work

        try:
            user_token = flow.finish(code)
            self._setToken(user_token)
        except Exception as e:
            utils.log("Error: %s" % (e,))
            result = False

        return result

    # return the DropboxClient, or None if can't be created
    def getClient(self):
        result = None

        user_token = self._getToken()

        if(user_token != ''):
            # create the client
            result = dropbox.Dropbox(oauth2_access_token=user_token['access_token'], oauth2_refresh_token=user_token['refresh_token'],
                                     oauth2_access_token_expiration=user_token['expiration'], app_key=self.APP_KEY, app_secret=self.APP_SECRET)
            try:
                result.users_get_current_account()
            except:
                # this didn't work, delete the token file
                self._deleteToken()
                result = None

        return result

    def _setToken(self, token):
        # write the token files
        token_file = open(xbmcvfs.translatePath(utils.data_dir() + self.TOKEN_FILE), 'w')

        token_file.write(json.dumps({"access_token": token.access_token, "refresh_token": token.refresh_token, "expiration": str(token.expires_at)}))
        token_file.close()

    def _getToken(self):
        result = {}
        # get token, if it exists
        if(xbmcvfs.exists(xbmcvfs.translatePath(utils.data_dir() + self.TOKEN_FILE))):
            token_file = open(xbmcvfs.translatePath(utils.data_dir() + self.TOKEN_FILE))
            token = token_file.read()

            if(token.strip() != ""):
                result = json.loads(token)
                # convert expiration back to a datetime object
                result['expiration'] = datetime.strptime(result['expiration'], "%Y-%m-%d %H:%M:%S.%f")

            token_file.close()

        return result

    def _deleteToken(self):
        if(xbmcvfs.exists(xbmcvfs.translatePath(utils.data_dir() + self.TOKEN_FILE))):
            xbmcvfs.delete(xbmcvfs.translatePath(utils.data_dir() + self.TOKEN_FILE))
