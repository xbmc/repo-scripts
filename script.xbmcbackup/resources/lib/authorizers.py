import xbmc
import xbmcgui
import xbmcvfs
import resources.lib.tinyurl as tinyurl
import resources.lib.utils as utils

# don't die on import error yet, these might not even get used
try:
    from dropbox import dropbox
except ImportError:
    pass


class DropboxAuthorizer:
    APP_KEY = ""
    APP_SECRET = ""

    def __init__(self):
        self.APP_KEY = utils.getSetting('dropbox_key')
        self.APP_SECRET = utils.getSetting('dropbox_secret')

    def setup(self):
        result = True

        if(self.APP_KEY == '' and self.APP_SECRET == ''):
            # we can't go any farther, need these for sure
            xbmcgui.Dialog().ok(utils.getString(30010), utils.getString(30027) + ' ' + utils.getString(30058), utils.getString(30059))

            result = False

        return result

    def isAuthorized(self):
        user_token = self._getToken()

        return user_token != ''

    def authorize(self):
        result = True

        if(not self.setup()):
            return False

        if(self.isAuthorized()):
            # delete the token to start over
            self._deleteToken()

        # copied flow from http://dropbox-sdk-python.readthedocs.io/en/latest/moduledoc.html#dropbox.oauth.DropboxOAuth2FlowNoRedirect
        flow = dropbox.oauth.DropboxOAuth2FlowNoRedirect(self.APP_KEY, self.APP_SECRET)

        url = flow.start()

        # print url in log
        utils.log("Authorize URL: " + url)
        xbmcgui.Dialog().ok(utils.getString(30010), utils.getString(30056), utils.getString(30057), tinyurl.shorten(url))

        # get the auth code
        code = xbmcgui.Dialog().input(utils.getString(30027) + ' ' + utils.getString(30103))

        # if user authorized this will work

        try:
            user_token = flow.finish(code)
            self._setToken(user_token.access_token)
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
            result = dropbox.Dropbox(user_token)

            try:
                result.users_get_current_account()
            except:
                # this didn't work, delete the token file
                self._deleteToken()
                result = None

        return result

    def _setToken(self, token):
        # write the token files
        token_file = open(xbmc.translatePath(utils.data_dir() + "tokens.txt"), 'w')
        token_file.write(token)
        token_file.close()

    def _getToken(self):
        # get token, if it exists
        if(xbmcvfs.exists(xbmc.translatePath(utils.data_dir() + "tokens.txt"))):
            token_file = open(xbmc.translatePath(utils.data_dir() + "tokens.txt"))
            token = token_file.read()
            token_file.close()

            return token
        else:
            return ""

    def _deleteToken(self):
        if(xbmcvfs.exists(xbmc.translatePath(utils.data_dir() + "tokens.txt"))):
            xbmcvfs.delete(xbmc.translatePath(utils.data_dir() + "tokens.txt"))
