#!/usr/bin/python
# coding: utf-8

#################################################################################################

from __future__ import division

import xbmc
import xbmcaddon
import xbmcvfs
import os
from PIL import ImageFilter,Image,ImageOps,ImageEnhance

from resources.lib.helper import *

#################################################################################################

BLUR_CONTAINER = xbmc.getInfoLabel('Skin.String(BlurContainer)') or 100000
BLUR_RADIUS = xbmc.getInfoLabel('Skin.String(BlurRadius)') or ADDON.getSetting('blur_radius')
BLUR_SATURATION = xbmc.getInfoLabel('Skin.String(BlurSaturation)') or '1.0'
OLD_IMAGE = ''

#################################################################################################


''' create image storage folders
'''
try:
    if not os.path.exists(ADDON_DATA_IMG_PATH):
        os.makedirs(ADDON_DATA_IMG_PATH)
        os.makedirs(ADDON_DATA_IMG_TEMP_PATH)

except OSError as e:
    # fix for race condition
    if e.errno != os.errno.EEXIST:
        raise
    pass


''' blur image and store result in addon data folder
'''
class ImageBlur():
    def __init__(self,prop='listitem',file=None,radius=None,saturation=None):
        global OLD_IMAGE
        self.image = file if file is not None else xbmc.getInfoLabel('Control.GetLabel(%s)' % BLUR_CONTAINER)
        self.radius = int(radius) if radius is not None else int(BLUR_RADIUS)
        self.saturation = float(saturation) if saturation is not None else float(BLUR_SATURATION)

        if self.image:
            if self.image != OLD_IMAGE:
                log('Image blurring: Image changed. Blur %s.' % self.image, DEBUG)
                OLD_IMAGE = self.image

                self.filepath = self.blur()
                self.avgcolor = self.color()

                winprop(prop + '_blurred', self.filepath)
                winprop(prop + '_color', self.avgcolor)
                winprop(prop + '_color_noalpha', self.avgcolor[2:])

    def __str__(self):
        return self.filepath, self.avgcolor

    def blur(self):
        filename = md5hash(self.image) + str(self.radius) + str(self.saturation) + '.png'
        targetfile = os.path.join(ADDON_DATA_IMG_PATH, filename)

        try:
            if xbmcvfs.exists(targetfile):
                touch_file(targetfile)
            else:
                img = _openimage(self.image,ADDON_DATA_IMG_PATH,filename)
                img.thumbnail((200, 200), Image.ANTIALIAS)
                img = img.convert('RGB')
                img = img.filter(ImageFilter.GaussianBlur(self.radius))

                if self.saturation:
                    converter = ImageEnhance.Color(img)
                    img = converter.enhance(self.saturation)

                img.save(targetfile)

            return targetfile

        except Exception:
            return ''

    ''' get average image color
    '''
    def color(self):
        imagecolor = 'FFF0F0F0'

        try:
            img = Image.open(self.filepath)
            imgResize = img.resize((1,1), Image.ANTIALIAS)
            col = imgResize.getpixel((0,0))
            imagecolor = 'FF%s%s%s' % (format(col[0], '02x'), format(col[1], '02x'), format(col[2], '02x'))
            log('Average color: ' + imagecolor, DEBUG)

        except:
            log('Use fallback average color: ' + imagecolor, DEBUG)
            pass

        return imagecolor


''' generate genre thumb and store result in addon data folder
'''
class CreateGenreThumb():
    def __init__(self,genre,images):
        self.images = images
        self.filename = 'genre_' + md5hash(images) + '.jpg'
        self.filepath = os.path.join(ADDON_DATA_IMG_PATH, self.filename)

        if xbmcvfs.exists(self.filepath):
            self.thumb = self.filepath
            touch_file(self.filepath)
        else:
            self.temp_files = self.copy_files()
            self.thumb = self.create_thumb()

    def __str__(self):
        return self.thumb

    def copy_files(self):
        ''' copy source posters to addon_data/img/tmp
        '''
        posters = list()
        for poster in self.images:
            posterfile = self.images.get(poster)
            temp_filename = md5hash(posterfile) + '.jpg'
            image = _openimage(posterfile,ADDON_DATA_IMG_TEMP_PATH,temp_filename)

            if image:
                posters.append(image)

        return posters

    def create_thumb(self):
        ''' create collage with copied posteres
        '''
        width, height = 500, 750
        cols, rows = 2, 2
        thumbnail_width = int(width / cols)
        thumbnail_height = int(height / rows)
        size = thumbnail_width, thumbnail_height

        try:
            collage_images = []
            for poster in self.temp_files:
                image = ImageOps.fit(poster, (size), method=Image.ANTIALIAS, bleed=0.0, centering=(0.5, 0.5))
                collage_images.append(image)

            collage = Image.new('RGB', (width, height), (5,5,5))
            i, x, y = 0, 0 ,0
            for row in range(rows):
                for col in range(cols):
                    try:
                        collage.paste(collage_images[i],(int(x), int(y)))
                    except Exception:
                        pass
                    i += 1
                    x += thumbnail_width
                y += thumbnail_height
                x = 0

            collage.save(self.filepath,optimize=True,quality=75)

            return self.filepath

        except Exception:
            return ''


''' get image dimension and aspect ratio
'''
def image_info(image):
    width, height, ar = '', '', ''

    if image:
        try:
            filename = md5hash(image) + '.jpg'
            img = _openimage(image,ADDON_DATA_IMG_TEMP_PATH,filename)
            width,height = img.size
            ar = round(width / height,2)
        except Exception:
            pass

    return width, height, ar


''' get cached images or copy to temp if file has not been cached yet
'''
def _openimage(image,targetpath,filename):
    # some paths require unquoting to get a valid cached thumb hash
    cached_image_path = url_unquote(image.replace('image://', ''))
    if cached_image_path.endswith('/'):
        cached_image_path = cached_image_path[:-1]

    cached_files = []
    for path in [xbmc.getCacheThumbName(cached_image_path), xbmc.getCacheThumbName(image)]:
        cached_files.append(os.path.join('special://profile/Thumbnails/', path[0], path[:-4] + '.jpg'))
        cached_files.append(os.path.join('special://profile/Thumbnails/', path[0], path[:-4] + '.png'))
        cached_files.append(os.path.join('special://profile/Thumbnails/Video/', path[0], path))

    for i in range(1, 4):
        try:
            ''' Try to get cached image at first
            '''
            for cache in cached_files:
                if xbmcvfs.exists(cache):
                    try:
                        img = Image.open(xbmcvfs.translatePath(cache))
                        return img

                    except Exception as error:
                        log('Image error: Could not open cached image --> %s' % error, WARNING)

            ''' Skin images will be tried to be accessed directly. For all other ones
                the source will be copied to the addon_data folder to get access.
            '''
            if xbmc.skinHasImage(image):
                if not image.startswith('special://skin'):
                    image = os.path.join('special://skin/media/', image)

                try: # in case image is packed in textures.xbt
                    img = Image.open(xbmcvfs.translatePath(image))
                    return img

                except Exception:
                    return ''

            else:
                targetfile = os.path.join(targetpath, filename)
                if not xbmcvfs.exists(targetfile):
                    xbmcvfs.copy(image, targetfile)

                img = Image.open(targetfile)
                return img

        except Exception as error:
            log('Image error: Could not get image for %s (try %d) -> %s' % (image, i, error), ERROR)
            xbmc.sleep(500)
            pass

    return ''