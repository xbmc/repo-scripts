import hashlib
import os
import json
import random
import re
import sys
import urllib
import xbmc
import xbmcvfs
import xbmcaddon
import xml.etree.ElementTree as etree

ADDON    = xbmcaddon.Addon()
ADDONID = ADDON.getAddonInfo('id')
LANGUAGE = ADDON.getLocalizedString

# supported image types by the screensaver
IMAGE_TYPES = ['.jpg', '.jpeg', '.png', '.tif', '.tiff', '.gif', '.pcx', '.bmp', '.tga', '.ico', '.nef', '.webp', '.jp2', '.apng']
HEIF_TYPES = ['.heic', '.heif']
MPO_TYPES = ['.mpo']
RAW_TYPES = ['.3fr', '.arw', '.cr2', '.crw', '.dcr', '.dng', '.erf', '.kdc', '.mdc', '.mef', '.mos', '.mrw', '.nef', '.nrw', '.orf', '.pef', '.ppm', '.raf', '.raw', '.rw2', '.srw', '.x3f']
CACHEFOLDER = xbmcvfs.translatePath(ADDON.getAddonInfo('profile'))
CACHEFILE = os.path.join(CACHEFOLDER, 'cache_%s')
RESUMEFILE = os.path.join(CACHEFOLDER, 'offset')
ASFILE = xbmcvfs.translatePath('special://profile/advancedsettings.xml')

def log(txt):
    message = '%s: %s' % (ADDONID, txt)
    xbmc.log(msg=message, level=xbmc.LOGDEBUG)

def checksum(path):
    return hashlib.md5(path).hexdigest()

def create_cache(path, hexfile, randomize, current_images=None):
    images = walk(path)
    if not xbmcvfs.exists(CACHEFOLDER):
        xbmcvfs.mkdir(CACHEFOLDER)
    # remove old cache files, but preserve settings and the resume offset
    dirs, files = xbmcvfs.listdir(CACHEFOLDER)
    preserve = {'settings.xml', os.path.basename(RESUMEFILE)}
    for item in files:
        if item not in preserve:
            xbmcvfs.delete(os.path.join(CACHEFOLDER, item))
    if images:
        if randomize:
            if current_images:
                # preserve existing shuffle order: keep known images in place,
                # insert new ones at random positions, drop removed ones
                new_paths = set(img[0] for img in images)
                images_by_path = {img[0]: img for img in images}
                # retain existing order, removing any files that have since been deleted
                ordered = [img for img in current_images if img[0] in new_paths]
                # insert genuinely new files at random positions
                added = [images_by_path[p] for p in new_paths - set(img[0] for img in current_images)]
                for img in added:
                    ordered.insert(random.randint(0, len(ordered)), img)
                images = ordered
            else:
                random.seed()
                random.shuffle(images)
        # create cache file
        try:
            cache = xbmcvfs.File(CACHEFILE % hexfile, 'w')
            json.dump(images, cache)
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
        if xbmcvfs.exists(xbmcvfs.translatePath(folder)):
            dirs = []
            files = []
            if xbmc.getCondVisibility('System.HasAddon(imagedecoder.heif)'):
                IMAGE_TYPES.extend(HEIF_TYPES)
            if xbmc.getCondVisibility('System.HasAddon(imagedecoder.mpo)'):
                IMAGE_TYPES.extend(MPO_TYPES)
            if xbmc.getCondVisibility('System.HasAddon(imagedecoder.raw)'):
                IMAGE_TYPES.extend(RAW_TYPES)
            # get all files and subfolders
            if folder.startswith('plugin://'):
                getroot = xbmc.executeJSONRPC('{"jsonrpc":"2.0", "method":"Files.GetDirectory", "params":{"directory":"%s", "sort":{"method":"label"}}, "id":1 }' % folder)
                root = json.loads(getroot)
                if 'result' in root and 'files' in root["result"]:
                    for item in root["result"]["files"]:
                        if item["filetype"] == "file":
                            files.append(item)
                        elif item["filetype"] == "directory":
                            dirs.append(item["file"])
            else:
                dirs, files = xbmcvfs.listdir(folder)
            log('dirs: %s' % len(dirs))
            log('files: %s' % len(files))
            if not folder.startswith('plugin://'):
                # natural sort
                convert = lambda text: int(text) if text.isdigit() else text
                alphanum_key = lambda key: [convert(c) for c in re.split('([0-9]+)', key)]
                files.sort(key=alphanum_key)
            for item in files:
                # check pictureexcludes from as.xml
                fileskip = False
                if excludes:
                    for string in excludes:
                        regex = re.compile(string)
                        if folder.startswith('plugin://'):
                            match = regex.search(item["label"])
                        else:
                            match = regex.search(item)
                        if match:
                            fileskip = True
                            break
                # filter out all images
                if folder.startswith('plugin://'):
                    if os.path.splitext(item["label"])[1].lower() in IMAGE_TYPES and not fileskip:
                        images.append([item["file"], item["label"]])
                else:
                    if os.path.splitext(item)[1].lower() in IMAGE_TYPES and not fileskip:
                        images.append([os.path.join(folder,item), item])
            if xbmcaddon.Addon().getSettingBool('recursive'):
                for item in dirs:
                    # check pictureexcludes from as.xml
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
                        if item.startswith('plugin://'):
                            images += walk(item)
                        else:
                            images += walk(os.path.join(folder,item,'')) # make sure paths end with a slash
        else:
            log('folder does not exist')
    return images
