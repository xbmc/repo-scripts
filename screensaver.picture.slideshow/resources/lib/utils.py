import sys, os, re, urllib, hashlib
import xbmc, xbmcvfs, xbmcaddon

ADDON    = sys.modules[ '__main__' ].ADDON
ADDONID  = sys.modules[ '__main__' ].ADDONID
LANGUAGE = sys.modules[ '__main__' ].LANGUAGE

# supported image types by the screensaver
IMAGE_TYPES = ('.jpg', '.jpeg', '.png', '.tif', '.tiff', '.gif', '.pcx', '.bmp', '.tga', '.ico', '.nef')
CACHEFOLDER = xbmc.translatePath(xbmcaddon.Addon().getAddonInfo('profile')).decode('utf-8')
CACHEFILE   = os.path.join(CACHEFOLDER, '%s')

def log(txt):
    if isinstance (txt,str):
        txt = txt.decode('utf-8')
    message = u'%s: %s' % (ADDONID, txt)
    xbmc.log(msg=message.encode('utf-8'), level=xbmc.LOGDEBUG)

def checksum(path):
    return hashlib.md5(path).hexdigest()

def create_cache(path, hexfile):
    images = walk(path)
    if not xbmcvfs.exists(CACHEFOLDER):
        xbmcvfs.mkdir(CACHEFOLDER)
    # remove old cache files
    dirs, files = xbmcvfs.listdir(CACHEFOLDER)
    for item in files:
        print item
        if item != 'settings.xml':
            xbmcvfs.delete(os.path.join(CACHEFOLDER,item))
    # create index file
    try:
        cache = xbmcvfs.File(CACHEFILE % hexfile, 'w')
        cache.write(str(images))
        cache.close()
    except:
        log('failed to save cachefile')

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
