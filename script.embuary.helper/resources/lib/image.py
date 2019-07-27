#!/usr/bin/python
#Based on script.toolbox by phil65 - https://github.com/phil65/script.toolbox/

#################################################################################################

import xbmc
import xbmcaddon
import xbmcvfs
import hashlib
import os
from PIL import ImageFilter,Image,ImageOps

''' Python 2<->3 compatibility
'''
try:
    import urllib2 as urllib
except ImportError:
    import urllib.request as urllib

from resources.lib.helper import *

#################################################################################################

BLUR_CONTAINER = xbmc.getInfoLabel('Skin.String(BlurContainer)') or 100000
BLUR_RADIUS = xbmc.getInfoLabel('Skin.String(BlurRadius)') or ADDON.getSetting('blur_radius')
OLD_IMAGE = ''

#################################################################################################


if not os.path.exists(ADDON_DATA_IMG_PATH):
    log('Create missing image folder', force=True)
    os.makedirs(ADDON_DATA_IMG_PATH)


def image_filter(prop='listitem',file=None,radius=BLUR_RADIUS):
    global OLD_IMAGE
    image = file if file is not None else xbmc.getInfoLabel('Control.GetLabel(%s)' % BLUR_CONTAINER)

    try:
        radius = int(radius)
    except ValueError:
        log('No valid radius defined for blurring')
        return

    if image:
        if image == OLD_IMAGE:
            log('Image blurring: Image has not changed. Skip %s.' % image, DEBUG)
        else:
            log('Image blurring: Image changed. Blur %s.' % image, DEBUG)
            OLD_IMAGE = image
            blurred_image, imagecolor = image_blur(image,radius)
            winprop(prop + '_blurred', blurred_image)
            winprop(prop + '_color', imagecolor)


def image_blur(image,radius):
    md5 = hashlib.md5(image).hexdigest()
    filename = md5 + str(radius) + '.png'
    targetfile = os.path.join(ADDON_DATA_IMG_PATH, filename)
    cachedthumb = xbmc.getCacheThumbName(image)
    xbmc_vid_cache_file = os.path.join('special://profile/Thumbnails/Video', cachedthumb[0], cachedthumb)
    xbmc_cache_file = os.path.join('special://profile/Thumbnails/', cachedthumb[0], cachedthumb[:-4] + '.jpg')

    if not xbmcvfs.exists(targetfile):
        img = None

        for i in range(1, 4):
            try:
                if os.path.isfile(xbmc_cache_file):
                    img = Image.open(xbmc.translatePath(xbmc_cache_file))
                    break
                elif os.path.isfile(xbmc_vid_cache_file):
                    img = Image.open(xbmc.translatePath(xbmc_vid_cache_file))
                    break
                else:
                    image = urllib.unquote(image.replace('image://', ''))
                    if image.endswith('/'):
                        image = image[:-1]
                    log('Copy image from source: ' + image, DEBUG)
                    xbmcvfs.copy(image, targetfile)
                    img = Image.open(targetfile)
                    break
            except Exception as error:
                log('Could not get image for %s (try %i)' % (image, i))
                xbmc.sleep(500)

        if not img:
            return '', ''

        img.thumbnail((200, 200), Image.ANTIALIAS)
        img = img.convert('RGB')
        imgfilter = BlurImage(radius=radius)
        img = img.filter(imgfilter)
        img.save(targetfile)

    else:
        log('Blurred img already created: ' + targetfile, DEBUG)
        img = Image.open(targetfile)

    imagecolor = get_colors(img)

    return targetfile, imagecolor


def get_colors(img):
    width, height = img.size
    imagecolor = 'FFF0F0F0'

    try:
        pixels = img.load()

        data = []
        for x in range(width / 2):
            for y in range(height / 2):
                cpixel = pixels[x * 2, y * 2]
                data.append(cpixel)

        r = 0
        g = 0
        b = 0
        counter = 0
        for x in range(len(data)):
            brightness = data[x][0] + data[x][1] + data[x][2]
            if brightness > 150 and brightness < 720:
                r += data[x][0]
                g += data[x][1]
                b += data[x][2]
                counter += 1

        if counter > 0:
            rAvg = int(r / counter)
            gAvg = int(g / counter)
            bAvg = int(b / counter)
            Avg = (rAvg + gAvg + bAvg) / 3
            minBrightness = 130

            if Avg < minBrightness:
                Diff = minBrightness - Avg

                if rAvg <= (255 - Diff):
                    rAvg += Diff
                else:
                    rAvg = 255
                if gAvg <= (255 - Diff):
                    gAvg += Diff
                else:
                    gAvg = 255
                if bAvg <= (255 - Diff):
                    bAvg += Diff
                else:
                    bAvg = 255

            imagecolor = 'FF%s%s%s' % (format(rAvg, '02x'), format(gAvg, '02x'), format(bAvg, '02x'))
            log('average color: ' + imagecolor, DEBUG)

        else:
            raise Exception

    except Exception:
        log('Use fallback average color: ' + imagecolor, DEBUG)
        pass

    return imagecolor


class BlurImage(ImageFilter.Filter):
    NAME = "GaussianBlur"

    def __init__(self,radius):
        self.radius = radius

    def filter(self,image):
        return image.gaussian_blur(self.radius)