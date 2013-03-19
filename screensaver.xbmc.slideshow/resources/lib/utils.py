import sys, os, urllib
import xbmc, xbmcvfs

__addonid__ = sys.modules[ "__main__" ].__addonid__

# supported image types by the screensaver
IMAGE_TYPES = ('.jpg', '.jpeg', '.png', '.tif', '.tiff', '.gif', '.pcx', '.bmp', '.tga', '.ico')
CACHEFOLDER = xbmc.translatePath('special://profile/addon_data/%s' % __addonid__).decode("utf-8")
CACHEFILE   = os.path.join(CACHEFOLDER, 'cache.txt')

def log(txt):
    if isinstance (txt,str):
        txt = txt.decode('utf-8')
    message = u'%s: %s' % (__addonid__, txt)
    xbmc.log(msg=message.encode('utf-8'), level=xbmc.LOGDEBUG)

def walk(path):
    images = []
    folders = []
    # multipath support
    if path.startswith('multipath://'):
        # get all paths from the multipath
        paths = path[12:-1].split('/')
        for item in paths:
            folders.append(urllib.unquote_plus(item))
    else:
        folders.append(path)
    for folder in folders:
        if xbmcvfs.exists(xbmc.translatePath(folder)):
            # get all files and subfolders
            dirs,files = xbmcvfs.listdir(folder)
            for item in files:
                # filter out all images
                if os.path.splitext(item)[1].lower() in IMAGE_TYPES:
                    images.append([os.path.join(folder,item), ''])
            for item in dirs:
                # recursively scan all subfolders
                images += walk(os.path.join(folder,item))
    return images
