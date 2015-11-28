#!/usr/bin/python
# -*- coding: utf-8 -*-

import random
import io
from Utils import *


#PIL fails on Android devices ?
hasPilModule = True
try:
    from PIL import Image
    im = Image.new("RGB", (1, 1))
    del im
except:
    hasPilModule = False

def createImageWall(images,windowProp,blackwhite=False,type="fanart"):
    if not hasPilModule:
        return []
    
    img_type = "RGBA"
    if blackwhite: img_type = "L"
    
    if type=="thumbnail":
        #square images
        img_columns = 11
        img_rows = 7
        img_width = 260
        img_height = 260
    elif type=="poster":
        #poster images
        img_columns = 15
        img_rows = 5
        img_width = 128
        img_height = 216
    else:
        #landscaped images
        img_columns = 8
        img_rows = 8
        img_width = 240
        img_height = 135
    size = img_width, img_height
    
    wallpath = "special://profile/addon_data/script.skin.helper.service/wallbackgrounds/"
    if not xbmcvfs.exists(wallpath):
        xbmcvfs.mkdirs(wallpath)
    
    wall_images = []
    return_images = []

    if SETTING("reuseWallBackgrounds") == "true":
        #reuse the existing images - do not rebuild
        dirs, files = xbmcvfs.listdir(wallpath)
        for file in files:
            if file.startswith(windowProp):
                return_images.append({"fanart": os.path.join(wallpath.decode("utf-8"),file)})
    
    if return_images: 
        return return_images
    
    logMsg("Building Wall background for %s - this might take a while..." %windowProp,0)
    images_required = img_columns*img_rows
    for image in images:
        image = image.get(type,"")
        if image and not image.startswith("music@") and not ".mp3" in image:
            file = xbmcvfs.File(image)
            try:
                img_obj = io.BytesIO(bytearray(file.readBytes()))
                img = Image.open(img_obj)
                img = img.resize(size)
                wall_images.append(img)
            except: pass
            finally: file.close()
    if wall_images:
        #duplicate images if we don't have enough
        
        while len(wall_images) < images_required:
            wall_images += wall_images
            
        for i in range(40):
            random.shuffle(wall_images)
            img_canvas = Image.new(img_type, (img_width * img_columns, img_height * img_rows))
            out_file = xbmc.translatePath(os.path.join(wallpath.decode("utf-8"),windowProp + "." + str(i) + ".jpg"))
            if xbmcvfs.exists(out_file):
                xbmcvfs.delete(out_file)
            
            counter = 0
            for x in range(img_rows):
                for y in range(img_columns):
                    img_canvas.paste(wall_images[counter], (y * img_width, x * img_height))
                    counter += 1

            img_canvas.save(out_file, "JPEG")
            return_images.append({"fanart": out_file })
    logMsg("Building Wall background %s DONE" %windowProp,0)
    return return_images