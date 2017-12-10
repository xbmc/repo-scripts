import sys
import urlparse
import xbmcgui
import resources.lib.utils as utils
from resources.lib.authorizers import DropboxAuthorizer,GoogleDriveAuthorizer

def get_params():
    param = {}
    try:
        for i in sys.argv:
            args = i
            if(args.startswith('?')):
                args = args[1:]
            param.update(dict(urlparse.parse_qsl(args)))
    except:
        pass
    return param

params = get_params()

#drobpox
if(params['type'] == 'dropbox'):
    authorizer = DropboxAuthorizer()

    if(authorizer.authorize()):
        xbmcgui.Dialog().ok(utils.getString(30010),utils.getString(30027) + ' ' + utils.getString(30106))
    else:
        xbmcgui.Dialog().ok(utils.getString(30010),utils.getString(30107) + ' ' + utils.getString(30027))

#google drive
elif(params['type'] == 'google_drive'):
    authorizer = GoogleDriveAuthorizer()

    if(authorizer.authorize()):
        xbmcgui.Dialog().ok("Backup",utils.getString(30098) + ' ' + utils.getString(30106))
    else:
        xbmcgui.Dialog().ok("Backup",utils.getString(30107) + ' ' + utils.getString(30098))
