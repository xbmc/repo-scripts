import sys, os, re, urllib, hashlib
import xbmc, xbmcvfs, xbmcaddon
import xml.etree.ElementTree as etree

ADDON    = sys.modules[ '__main__' ].ADDON
ADDONID  = sys.modules[ '__main__' ].ADDONID
LANGUAGE = sys.modules[ '__main__' ].LANGUAGE

# supported image types by the screensaver
IMAGE_TYPES = ('.jpg', '.jpeg', '.png', '.tif', '.tiff', '.gif', '.pcx', '.bmp', '.tga', '.ico', '.nef')
CACHEFOLDER = xbmc.translatePath(xbmcaddon.Addon().getAddonInfo('profile')).decode('utf-8')
CACHEFILE   = os.path.join(CACHEFOLDER, '%s')
RESUMEFILE  = os.path.join(CACHEFOLDER, 'offset')
ASFILE      = xbmc.translatePath('special://profile/advancedsettings.xml').decode('utf-8')

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
        if item != 'settings.xml':
            xbmcvfs.delete(os.path.join(CACHEFOLDER,item))
    if images:
        # create index file
        try:
            cache = xbmcvfs.File(CACHEFILE % hexfile, 'w')
            cache.write(str(images))
            cache.close()
        except:
            log('failed to save cachefile')

def get_excludes():
    regexes = []
    if xbmcvfs.exists(ASFILE):
        try:
            tree = etree.parse(ASFILE)
            root = tree.getroot()
            excludes = root.find('pictureexcludes')
            if excludes is not None:
                for expr in excludes:
                    regexes.append(expr.text)
        except:
            pass
    return regexes

def walk(path):
    images = []
    folders = []
    excludes = get_excludes()
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
            log('dirs: %s' % len(dirs))
            log('files: %s' % len(files))
            # natural sort
            convert = lambda text: int(text) if text.isdigit() else text
            alphanum_key = lambda key: [convert(c) for c in re.split('([0-9]+)', key)]
            files.sort(key=alphanum_key)
            for item in files:
                #check pictureexcludes from as.xml
                fileskip = False
                if excludes:
                    for string in excludes:
                        regex = re.compile(string)
                        match = regex.search(item)
                        if match:
                            fileskip = True
                            break
                # filter out all images
                if os.path.splitext(item)[1].lower() in IMAGE_TYPES and not fileskip:
                    images.append([os.path.join(folder,item), ''])
            for item in dirs:
                #check pictureexcludes from as.xml
                dirskip = False
                if excludes:
                    for string in excludes:
                        regex = re.compile(string)
                        match = regex.search(item)
                        if match:
                            dirskip = True
                            break
                # recursively scan all subfolders
                if not dirskip:
                    images += walk(os.path.join(folder,item,'')) # make sure paths end with a slash
        else:
            log('folder does not exist')
    return images
