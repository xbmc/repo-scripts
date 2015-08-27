import sys, os, re, urllib, hashlib
import xbmc, xbmcvfs

__addon__    = sys.modules[ '__main__' ].__addon__
__addonid__  = sys.modules[ '__main__' ].__addonid__
__language__ = sys.modules[ '__main__' ].__language__

# supported image types by the screensaver
IMAGE_TYPES = ('.jpg', '.jpeg', '.png', '.tif', '.tiff', '.gif', '.pcx', '.bmp', '.tga', '.ico', '.nef')
CACHEFOLDER = xbmc.translatePath('special://profile/addon_data/%s' % __addonid__).decode('utf-8')
CACHEFILE   = os.path.join(CACHEFOLDER, '%s')

def log(txt):
    if isinstance (txt,str):
        txt = txt.decode('utf-8')
    message = u'%s: %s' % (__addonid__, txt)
    xbmc.log(msg=message.encode('utf-8'), level=xbmc.LOGDEBUG)

def checksum(path):
    return hashlib.md5(path).hexdigest()

def create_cache(startup):
    slideshow_type = __addon__.getSetting('type')
    if slideshow_type == '2':
        if startup: # don't notify during background scan
            xbmc.executebuiltin((u'Notification(%s,%s,%i)' % (__addonid__, __language__(30019), 5000)).encode('utf-8', 'ignore'))
        path = __addon__.getSetting('path')
        images = walk(path)
        if not xbmcvfs.exists(CACHEFOLDER):
            xbmcvfs.mkdir(CACHEFOLDER)
        hexfile = checksum(path)
        try:
            cache = xbmcvfs.File(CACHEFILE % hexfile, 'w')
            cache.write(str(images))
            cache.close()
        except:
            log('failed to save cachefile')
        if startup:
            xbmc.executebuiltin((u'Notification(%s,%s,%i)' % (__addonid__, __language__(30020), 5000)).encode('utf-8', 'ignore'))
    else:
        xbmc.executebuiltin((u'Notification(%s,%s,%i)' % (__addonid__, __language__(30028), 5000)).encode('utf-8', 'ignore'))

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
            # natural sort
            convert = lambda text: int(text) if text.isdigit() else text
            alphanum_key = lambda key: [convert(c) for c in re.split('([0-9]+)', key)]
            files.sort(key=alphanum_key)
            for item in files:
                # filter out all images
                if os.path.splitext(item)[1].lower() in IMAGE_TYPES:
                    images.append([os.path.join(folder,item), ''])
            for item in dirs:
                # recursively scan all subfolders
                images += walk(os.path.join(folder,item,'')) # make sure paths end with a slash
    return images
