import xbmc
import xbmcaddon
import xbmcgui
import xbmcvfs
import xbmcplugin
import os, sys
import simplejson
import hashlib
import urllib
import random
import math
from PIL import Image, ImageOps, ImageEnhance, ImageDraw, ImageStat, ImageFilter
from ImageOperations import MyGaussianBlur
from decimal import *
from xml.dom.minidom import parse
from threading import Thread
from random import shuffle
from collections import deque
ADDON =             xbmcaddon.Addon()
ADDON_ID =          ADDON.getAddonInfo('id')
ADDON_LANGUAGE =    ADDON.getLocalizedString
ADDON_DATA_PATH =   os.path.join(xbmc.translatePath("special://profile/addon_data/%s" % ADDON_ID))
ADDON_COLORS =      os.path.join(ADDON_DATA_PATH, "colors.db")
#ADDON_SETTINGS =    os.path.join(ADDON_DATA_PATH, "settings.")
image_formats =     ['.jpg', '.jpeg', '.png', '.tif', '.bmp', 'gif', 'tiff']
HOME =              xbmcgui.Window(10000)
ONE_THIRD =         1.0/3.0
ONE_SIXTH =         1.0/6.0
TWO_THIRD =         2.0/3.0
min_stripes =       20
max_stripes =       200
orientation =       'vertical'
lgint =             10
lgsteps =           50
black_pixel =       (0, 0, 0, 255)
white_pixel =       (255, 255, 255, 255)
randomness =        (0)
threshold =         100
clength =           50
angle =             float(0)
delta_x =           40
delta_y =           90
radius =            1
pixelsize =         20
blocksize =         64
sigma =             0.05
iterations =        1920
pthreshold =        100
pclength =          50
pangle =            00
prandomness =       10
lightsize =         192
black =             "#000000"
white =             "#ffffff"
bits =              1
doffset =           100
desat =             0.3
sharp =             0.0
atsample =          10
atscale =           1
atpercentage =      0
atangles =          [0,15,30,45]
blend =             1.0
quality =           8
color_comp =        "main:hls*0.33;0;0@hsv*0;-0.1;0.3" #[comp|main]:hls*-0.5;0.0;0.1@fhsv*-;-0.1;0.3@bump*[0-255] <- any amount of ops/any order, if no ops just use 'main:' or 'comp:'
color_main =        "main:" #[comp|main]:fhls*-;0.5;0.5@bump*[0-255] <- any amount of ops/any order, if no ops just use 'main:' or 'comp:'
colors_dict =       {}
shuffle_numbers =   ['zero', 'one', 'two', 'three', 'four', 'five', 'six', 'seven', 'eight', 'nine']
def fnblur(): return str(radius) + str(quality)
def fnpixelate(): return str(pixelsize) + str(quality)
def fnshiftblock(): return str(blocksize) + str(sigma) + str(iterations) + str(quality)
def fnpixelnone(): return str(pthreshold) + str(pclength) + str(pangle) + str(prandomness) + str(quality)
def fnpixelwaves(): return str(pthreshold) + str(pclength) + str(pangle) + str(prandomness) + str(quality)
def fnpixelrandom(): return str(pthreshold) + str(pclength) + str(pangle) + str(prandomness) + str(quality)
def fnpixelfile(): return str(pthreshold) + str(pclength) + str(pangle) + str(prandomness) + str(quality)
def fnpixelfedges(): return str(pthreshold) + str(pclength) + str(pangle) + str(prandomness) + str(quality)
def fnpixeledges(): return str(pthreshold) + str(pclength) + str(pangle) + str(prandomness) + str(quality)
def fnfakelight(): return str(lightsize) + str(quality)
def fntwotone(): return str(black) + str(white) + str(quality)
def fnposterize(): return str(bits) + str(quality)
def fndistort(): return str(delta_x) + str(delta_y) + str(quality)
def fnhalftone(): return str(quality)
def fnangletone(): return str(atsample) + str(atscale) + str(atpercentage) + ''.join(str(v) for v in atangles) + str(quality)
def fndither(): return str(quality)
def fndataglitch(): return str(doffset) + str(quality)
def fndesaturate(): return str(desat) + str(quality)
def fnsharpness(): return str(sharp) + str(quality)
def fnsplicer(): return str(min_stripes) + str(max_stripes) + str(orientation) + str(quality)
def ColorBox_go_map(filterimage, imageops, gqual=0):
    if gqual == 0: gqual = quality
    filename = hashlib.md5(filterimage).hexdigest() + str(blend) + '-'
    for cmarg in imageops.strip().split('-'):
        filename = filename + cmarg + ColorBox_filename_map[cmarg]()
    targetfile = os.path.join(ADDON_DATA_PATH, filename + '.png')
    Cache = Check_XBMC_Cache(targetfile)
    if Cache != "": return Cache
    Img = Check_XBMC_Internal(targetfile, filterimage)
    if not Img: return
    try:
        img = Image.open(Img)
    except Exception as e:
        log("go_mapof: %s ops: %s" % (e,filterimage))
    else:
        img = Resize_Image(img, gqual)
        img = img.convert('RGB')
        imgor = img
    try:
        for cmarg in imageops.strip().split('-'):
            img = ColorBox_function_map[cmarg](img)
    except Exception as e:
        log("go_mapop: %s cmarg: %s" % (e,cmarg))
    else:
        if blend < 1:
            orwidth, orheight = imgor.size
            width, height = img.size
            if width != orwidth or height != orheight:
                img = img.resize((orwidth, orheight), Image.ANTIALIAS)
            img = Image.blend(imgor, img, blend)
        img.save(targetfile)
        return targetfile
def set_quality(new_value):
    global quality
    quality = int(new_value)
    xbmc.executebuiltin('Skin.SetString(colorbox_quality,'+str(new_value)+')')
def set_blursize(new_value):
    global radius
    radius = int(new_value)
    xbmc.executebuiltin('Skin.SetString(colorbox_blursize,'+str(new_value)+')')
def set_bitsize(new_value):
    global bits
    bits = int(new_value)
    xbmc.executebuiltin('Skin.SetString(colorbox_bitsize,'+str(new_value)+')')
def set_pixelsize(new_value):
    global pixelsize
    pixelsize = int(new_value)
    xbmc.executebuiltin('Skin.SetString(colorbox_pixelsize,'+str(pixelsize)+')')
def set_black(new_value):
    global black
    black = "#" + str(new_value)
    xbmc.executebuiltin('Skin.SetString(colorbox_black,'+str(new_value)+')')
def set_white(new_value):
    global white
    white = "#" + str(new_value)
    xbmc.executebuiltin('Skin.SetString(colorbox_white,'+str(new_value)+')')
def set_lgint(new_value):
    global lgint
    lgint = int(new_value)
    xbmc.executebuiltin('Skin.SetString(colorbox_lgint,'+str(new_value)+')')
def set_lgsteps(new_value):
    global lgsteps
    lgsteps = int(new_value)
    xbmc.executebuiltin('Skin.SetString(colorbox_lgsteps,'+str(new_value)+')')
def set_comp(new_value):
    global color_comp
    color_comp = str(new_value)
    xbmc.executebuiltin('Skin.SetString(colorbox_comp,'+str(new_value)+')')
def set_main(new_value):
    global color_main
    color_main = str(new_value)
    xbmc.executebuiltin('Skin.SetString(colorbox_main,'+str(new_value)+')')
def set_desat(new_value):
    global desat
    desat = int(new_value) / 100.0
    xbmc.executebuiltin('Skin.SetString(colorbox_desat,'+str(new_value)+')')
def set_sharp(new_value):
    global sharp
    sharp = int(new_value) / 100.0
    xbmc.executebuiltin('Skin.SetString(colorbox_sharp,'+str(new_value)+')')
def set_blend(new_value):
    global blend
    blend = int(new_value) / 100.0
    xbmc.executebuiltin('Skin.SetString(colorbox_blend,'+str(new_value)+')')
def dataglitch(img):
    return Dataglitch_Image(img)
def blur(img):
    imgfilter = MyGaussianBlur(radius=radius)
    img = img.filter(imgfilter)
    return img
def desaturate(img):
    converter = ImageEnhance.Color(img)
    img = converter.enhance(desat)
    return img
def sharpness(img):
    converter = ImageEnhance.Sharpness(img)
    img = converter.enhance(sharp)
    return img
def pixelate(img):
    return Pixelate_Image(img)
def splicer(images_path):
    images_path = xbmc.getInfoLabel('ListItem.Path')
    images = get_all_images_from_the_input_dir(images_path)
    return Splice_Images(images, MIN_STRIPES, MAX_STRIPES, orientation=ORIENTATION)
def shiftblock(img):
    qiterations = iterations / quality    
    return Shiftblock_Image(img, blocksize, sigma, qiterations)
def pixelnone(img):
    return pixelshift(img, "none")
def pixelwaves(img):
    return pixelshift(img, "waves")
def pixelrandom(img):
    return pixelshift(img, "random")
def pixelfile(img):
    return pixelshift(img, "file")
def pixelfedges(img):
    return pixelshift(img, "fedges")
def pixeledges(img):
    return pixelshift(img, "edges")
def pixelshift(img, ptype="none"):
    #stype; 1=random, 2=edges, 3=waves, 4=file, 5=file_edges, 0=none
    global threshold, clength, angle, randomness
    threshold = int(pthreshold)
    clength = int(pclength)
    angle = int(pangle)
    randomness = float(prandomness)    
    img = Pixelshift_Image(img, ptype)
    return img
def fakelight(img):
    return fake_light(img,lightsize)
def twotone(img):
    return image_recolorize(img,black,white)
def posterize(img):
    return image_posterize(img,bits)
def distort(img):
    return image_distort(img,delta_x,delta_y)
def halftone(img):
    return Halftone_Image(img)
def angletone(img):
    return Angletone_Image(img, atsample, atscale, atpercentage, atangles)
def dither(img):
    return Dither_Image(img)
def Pixelate_Image(img):
    backgroundColor = (0,)*3
    image = img
    image = image.resize((image.size[0]/pixelsize, image.size[1]/pixelsize), Image.NEAREST)
    image = image.resize((image.size[0]*pixelsize, image.size[1]*pixelsize), Image.NEAREST)
    pixel = image.load()
    for i in range(0,image.size[0],pixelsize):
      for j in range(0,image.size[1],pixelsize):
        for r in range(pixelsize):
          pixel[i+r,j] = backgroundColor
          pixel[i,j+r] = backgroundColor
    return image
def Dataglitch_Image(img, channel='r'):
    img.load()
    r, g, b = img.split()
    eval_getdata = channel + ".getdata()"
    channel_data = eval(eval_getdata)
    channel_deque = deque(channel_data)
    channel_deque.rotate(random.randint(0, doffset))
    eval_putdata = channel + ".putdata(channel_deque)"
    eval(eval_putdata)
    shifted_image = Image.merge('RGB', (r, g, b))
    return shifted_image
def Shiftblock_Image(image, blocksize=64, sigma=1.05, iterations=300):
    seed = random.random()
    r = random.Random(seed)
    for i in xrange(iterations):
        bx = int(r.uniform(0, image.size[0]-blocksize))
        by = int(r.uniform(0, image.size[1]-blocksize))
        block = image.crop((bx, by, bx+blocksize-1, by+blocksize-1))
        mx = int(math.floor(r.normalvariate(0, sigma)))
        my = int(math.floor(r.normalvariate(0, sigma)))
        image.paste(block, (bx+mx, by+my))
    return image
def Angletone_Image(img, sample, scale, percentage, angles):
    cmyk = anglegcr(img, percentage)
    dots = anglehalftone(img, cmyk, sample, scale, angles)
    image = Image.merge('CMYK', dots)
    return image.convert('RGB')
def get_pixel(image, i, j):
    gw, gh = image.size
    if i > gw or j > gh:
        return None
    gp = image.getpixel((i, j))
    return gp
def get_saturation(gv, gq):
    if gv > 223:
        return 255
    elif gv > 159:
        if gq != 1:
            return 255
        return 0
    elif gv > 95:
        if gq == 0 or gq == 3:
            return 255
        return 0
    elif gv > 32:
        if gq == 1:
            return 255
        return 0
    else:
        return 0
def Halftone_Image(img):
    qw, qh = img.size
    if qw % 2 != 0:
        qw += 1
    if qh % 2 != 0:
        qh += 1
    img = img.resize((qw, qh), Image.ANTIALIAS)
    hinew = Image.new('RGB', (qw, qh), "white")
    hipixels = hinew.load()
    for i in range(0, qw, 2):
        for j in range(0, qh, 2):
            p1 = get_pixel(img, i, j)
            p2 = get_pixel(img, i, j + 1)
            p3 = get_pixel(img, i + 1, j)
            p4 = get_pixel(img, i + 1, j + 1)
            gray1 = (p1[0] * 0.299) + (p1[1] * 0.587) + (p1[2] * 0.114)
            gray2 = (p2[0] * 0.299) + (p2[1] * 0.587) + (p2[2] * 0.114)
            gray3 = (p3[0] * 0.299) + (p3[1] * 0.587) + (p3[2] * 0.114)
            gray4 = (p4[0] * 0.299) + (p4[1] * 0.587) + (p4[2] * 0.114)
            sat = (gray1 + gray2 + gray3 + gray4) / 4
            if sat > 223:
                hipixels[i, j]         = (255, 255, 255)
                hipixels[i, j + 1]     = (255, 255, 255)
                hipixels[i + 1, j]     = (255, 255, 255)
                hipixels[i + 1, j + 1] = (255, 255, 255)
            elif sat > 159:
                hipixels[i, j]         = (255, 255, 255)
                hipixels[i, j + 1]     = (0, 0, 0)
                hipixels[i + 1, j]     = (255, 255, 255)
                hipixels[i + 1, j + 1] = (255, 255, 255)
            elif sat > 95:
                hipixels[i, j]         = (255, 255, 255)
                hipixels[i, j + 1]     = (0, 0, 0)
                hipixels[i + 1, j]     = (0, 0, 0)
                hipixels[i + 1, j + 1] = (255, 255, 255)
            elif sat > 32:
                hipixels[i, j]         = (0, 0, 0)
                hipixels[i, j + 1]     = (255, 255, 255)
                hipixels[i + 1, j]     = (0, 0, 0)
                hipixels[i + 1, j + 1] = (0, 0, 0)
            else:
                hipixels[i, j]         = (0, 0, 0)
                hipixels[i, j + 1]     = (0, 0, 0)
                hipixels[i + 1, j]     = (0, 0, 0)
                hipixels[i + 1, j + 1] = (0, 0, 0)
    return hinew
def Dither_Image(img):
    qw, qh = img.size
    if qw % 2 != 0:
        qw += 1
    if qh % 2 != 0:
        qh += 1
    img = img.resize((qw, qh), Image.ANTIALIAS)
    dinew = Image.new('RGB', (qw, qh), "white")
    dipixels = dinew.load()
    for i in range(0, qw, 2):
        for j in range(0, qh, 2):
            p1 = get_pixel(img, i, j)
            p2 = get_pixel(img, i, j + 1)
            p3 = get_pixel(img, i + 1, j)
            p4 = get_pixel(img, i + 1, j + 1)
            red   = (p1[0] + p2[0] + p3[0] + p4[0]) / 4
            green = (p1[1] + p2[1] + p3[1] + p4[1]) / 4
            blue  = (p1[2] + p2[2] + p3[2] + p4[2]) / 4
            r = [0, 0, 0, 0]
            g = [0, 0, 0, 0]
            b = [0, 0, 0, 0]
            for x in range(0, 4):
                r[x] = get_saturation(red, x)
                g[x] = get_saturation(green, x)
                b[x] = get_saturation(blue, x)
            dipixels[i, j]         = (r[0], g[0], b[0])
            dipixels[i, j + 1]     = (r[1], g[1], b[1])
            dipixels[i + 1, j]     = (r[2], g[2], b[2])
            dipixels[i + 1, j + 1] = (r[3], g[3], b[3])
    return dinew
def Splice_Images(images, min_stripes=20, max_stripes=200, orientation="verticle", random_coords=False):
    max_area = 0
    no_of_stripes = random.randint(min_stripes, max_stripes)
    # Get the largest dims
    for image in images:
        w, h = image.size
        area = h * w
        if area > max_area:
            max_area = area
            max_width, max_height = w, h
    max_width = max_width - (max_width % no_of_stripes)
    max_height = max_height - (max_height % no_of_stripes)
    output_image = Image.new('RGB', (max_width, max_height))
    # Resize all to the largest dimensions
    resized_images = []
    for image in images:
        resized_image = image.resize((max_width, max_height), 3)
        resized_images.append(resized_image)
    coords_list = []
    if orientation == "verticle":
        split = range(0, int(w), int(int(w) / int(no_of_stripes)))
        for coord in split:
            stripe_coords = (coord, 0, int(coord + w / no_of_stripes), h)
            coords_list.append(stripe_coords)
    else: # horizontal
        split = range(0, int(h), int(int(h) / int(no_of_stripes)))
        for coord in split:
            stripe_coords = (0, coord, w, int(coord + h / no_of_stripes))
            coords_list.append(stripe_coords)
    for coords in coords_list:
        if random_coords:
            source_coords = coords_list[random.randint(0, len(coords_list) - 1)]
        else:
            source_coords = coords
        stripe = resized_images[random.randint(0, len(resized_images) - 1)].crop(source_coords)
        output_image.paste(stripe, coords)
    return output_image
def get_all_images_from_the_input_dir(input_dir):
    images = []
    for file in os.listdir(input_dir):
        filepath = os.path.join(input_dir, file)
        if os.path.isfile(filepath):
            if os.path.splitext(filepath)[1].lower() in image_formats:
                img = Image.open(filepath)
                images.append(img)
    return images
def anglegcr(img, percentage):
    cmyk_im = img.convert('CMYK')
    if not percentage:
        return cmyk_im
    cmyk_im = cmyk_im.split()
    cmyk = []
    for i in xrange(4):
        cmyk.append(cmyk_im[i].load())
    for x in xrange(img.size[0]):
        for y in xrange(img.size[1]):
            gray = min(cmyk[0][x,y], cmyk[1][x,y], cmyk[2][x,y]) * percentage / 100
            for i in xrange(3):
                cmyk[i][x,y] = cmyk[i][x,y] - gray
            cmyk[3][x,y] = gray
    return Image.merge('CMYK', cmyk_im)
def anglehalftone(img, cmyk, sample, scale, angles):
    cmyk = cmyk.split()
    dots = []
    for channel, angle in zip(cmyk, angles):
        channel = channel.rotate(angle, expand=1)
        size = channel.size[0]*scale, channel.size[1]*scale
        half_tone = Image.new('L', size)
        draw = ImageDraw.Draw(half_tone)
        for x in xrange(0, channel.size[0], sample):
            for y in xrange(0, channel.size[1], sample):
                box = channel.crop((x, y, x + sample, y + sample))
                stat = ImageStat.Stat(box)
                diameter = (stat.mean[0] / 255)**0.5
                edge = 0.5*(1-diameter)
                x_pos, y_pos = (x+edge)*scale, (y+edge)*scale
                box_edge = sample*diameter*scale
                draw.ellipse((x_pos, y_pos, x_pos + box_edge, y_pos + box_edge), fill=255)
        half_tone = half_tone.rotate(-angle, expand=1)
        width_half, height_half = half_tone.size
        xx=(width_half-img.size[0]*scale) / 2
        yy=(height_half-img.size[1]*scale) / 2
        half_tone = half_tone.crop((xx, yy, xx + img.size[0]*scale, yy + img.size[1]*scale))
        dots.append(half_tone)
    return dots
def sort_interval(interval):
	if interval == []:
		return []
	else:
		return(sorted(interval, key = lambda x: x[0] + x[1] + x[2]))
def random_width():
	x = random.random()
	width = int(clength*(1-x))
	return(width)
def int_edges(pixels, img):
	edges = img.filter(ImageFilter.FIND_EDGES)
	edges = edges.convert('RGB')
	edge_data = edges.load()
	filter_pixels = []
	edge_pixels = []
	intervals = []
	for y in range(img.size[1]):
		filter_pixels.append([])
		for x in range(img.size[0]):
			filter_pixels[y].append(edge_data[x, y])
	for y in range(len(pixels)):
		edge_pixels.append([])
		for x in range(len(pixels[0])):
			if filter_pixels[y][x][0] + filter_pixels[y][x][1] + filter_pixels[y][x][2] < threshold:
				edge_pixels[y].append(white_pixel)
			else:
				edge_pixels[y].append(black_pixel)
	for y in range(len(pixels)-1,1,-1):
		for x in range(len(pixels[0])-1,1,-1):
			if edge_pixels[y][x] == black_pixel and edge_pixels[y][x-1] == black_pixel:
				edge_pixels[y][x] = white_pixel
	for y in range(len(pixels)):
		intervals.append([])
		for x in range(len(pixels[0])):
			if edge_pixels[y][x] == black_pixel:
				intervals[y].append(x)
		intervals[y].append(len(pixels[0]))
	return(intervals)
def int_random(pixels, img):
	intervals = []
	for y in range(len(pixels)):
		intervals.append([])
		x = 0
		while True:
			width = random_width()
			x += width
			if x > len(pixels[0]):
				intervals[y].append(len(pixels[0]))
				break
			else:
				intervals[y].append(x)
	return(intervals)
def int_waves(pixels, img):
	intervals = []
	for y in range(len(pixels)):
		intervals.append([])
		x = 0
		while True:
			width = clength + random.randint(0,10)
			x += width
			if x > len(pixels[0]):
				intervals[y].append(len(pixels[0]))
				break
			else:
				intervals[y].append(x)
	return(intervals)
def int_file(pixels, img):
	intervals = []
	file_pixels = []
	data = img.load()
	for y in range(img.size[1]):
		file_pixels.append([])
		for x in range(img.size[0]):
			file_pixels[y].append(data[x, y])
	for y in range(len(pixels)-1,1,-1):
		for x in range(len(pixels[0])-1,1,-1):
			if file_pixels[y][x] == black_pixel and file_pixels[y][x-1] == black_pixel:
				file_pixels[y][x] = white_pixel
	for y in range(len(pixels)):
		intervals.append([])
		for x in range(len(pixels[0])):
			if file_pixels[y][x] == black_pixel:
				intervals[y].append(x)
		intervals[y].append(len(pixels[0]))
	return(intervals)
def int_file_edges(pixels, img):
	img = img.resize((len(pixels[0]), len(pixels)), Image.ANTIALIAS)
	edges = img.filter(ImageFilter.FIND_EDGES)
	edges = edges.convert('RGB')
	edge_data = edges.load()
	filter_pixels = []
	edge_pixels = []
	intervals = []
	for y in range(img.size[1]):
		filter_pixels.append([])
		for x in range(img.size[0]):
			filter_pixels[y].append(edge_data[x, y])
	for y in range(len(pixels)):
		edge_pixels.append([])
		for x in range(len(pixels[0])):
			if filter_pixels[y][x][0] + filter_pixels[y][x][1] + filter_pixels[y][x][2] < threshold:
				edge_pixels[y].append(white_pixel)
			else:
				edge_pixels[y].append(black_pixel)
	for y in range(len(pixels)-1,1,-1):
		for x in range(len(pixels[0])-1,1,-1):
			if edge_pixels[y][x] == black_pixel and edge_pixels[y][x-1] == black_pixel:
				edge_pixels[y][x] = white_pixel
	for y in range(len(pixels)):
		intervals.append([])
		for x in range(len(pixels[0])):
			if edge_pixels[y][x] == black_pixel:
				intervals[y].append(x)
		intervals[y].append(len(pixels[0]))
	return(intervals)
def int_none(pixels, img):
	intervals = []
	for y in range(len(pixels)):
		intervals.append([len(pixels[y])])
	return(intervals)
def sort_image(pixels, intervals):
	sorted_pixels=[]
	for y in range(len(pixels)):
		row=[]
		xMin = 0
		for xMax in intervals[y]:
			interval = []
			for x in range(xMin, xMax):
				interval.append(pixels[y][x])
			if random.randint(0,100) >= randomness:
				row = row + sort_interval(interval)
			else:
				row = row + interval
			xMin = xMax
		row.append(pixels[y][0])
		sorted_pixels.append(row)
	return(sorted_pixels)
def pixel_sort(img, int_function):
	img = img.rotate(angle, expand = True)
	data = img.load()
	new = Image.new('RGB', img.size)
	pixels = []
	for y in range(img.size[1]):
		pixels.append([])
		for x in range(img.size[0]):
			pixels[y].append(data[x, y])
	intervals = int_function(pixels, img)
	sorted_pixels = sort_image(pixels, intervals)
	for y in range(img.size[1]):
		for x in range(img.size[0]):
			new.putpixel((x, y), sorted_pixels[y][x])
	new = new.rotate(-angle)
	return new
def Pixelshift_Image(img, stype):
    if stype == 'random':
        int_function = int_random
    elif stype == 'none':
        int_function = int_none
    elif stype == 'edges':
        int_function = int_edges
    elif stype == 'waves':
        int_function = int_waves
    elif stype == 'file':
        int_function = int_file
    elif stype == 'fedges':
        int_function = int_file_edges
    image = pixel_sort(img, int_function)
    return image
def image_recolorize(src, black="#000000", white="#FFFFFF"):
    return ImageOps.colorize(ImageOps.grayscale(src), black, white)
def image_posterize(img, bits=1):
    return ImageOps.posterize(img, bits)
def fake_light(img, tilesize=50):
    WIDTH, HEIGHT = img.size
    for x in xrange(0, WIDTH, tilesize):
        for y in xrange(0, HEIGHT, tilesize):
            br = int(255 * (1 - x / float(WIDTH) * y / float(HEIGHT)))
            tile = Image.new('RGB', (tilesize, tilesize), (255,255,255,128))
            img.paste((br,br,br), (x, y, x + tilesize, y + tilesize), mask=tile)
    return img
def image_distort(img, delta_x=50, delta_y=90):
    WIDTH, HEIGHT = img.size
    img_data = img.load()
    output = Image.new('RGB',img.size,"gray")
    output_img = output.load()
    pix=[0, 0]
    for x in range(WIDTH):
        for y in range(HEIGHT):
            x_shift, y_shift =  ( int(abs(math.sin(x) * WIDTH / delta_x)) ,
                                  int(abs(math.tan(math.sin(y))) * HEIGHT / delta_y))
            if x + x_shift < WIDTH:
                pix[0] = x + x_shift
            else:
                pix[0] = x
            if y + y_shift < HEIGHT :
                pix[1] = y + y_shift
            else:
                pix[1] = y
            output_img[x,y] = img_data[tuple(pix)]
    return output
def Shuffle_Set(amount,timed=40):
    timed = int(timed)
    board = [[i] for i in range(int(amount))]
    shuffle(board)
    HOME.setProperty('Colorbox_shuffle', '1')
    for peg in board:
        peg = list(peg)
        npeg = []
        for p in peg:
            npeg.append(shuffle_numbers[int(p)])
        npegs = ''.join(npeg)
        HOME.setProperty('Colorbox_shuffle.' + npegs, '1')
        xbmc.sleep(timed)
    shuffle(board)
    HOME.setProperty('Colorbox_shuffle', '0')
    for peg in board:
        peg = list(peg)
        npeg = []
        for p in peg:
            npeg.append(shuffle_numbers[int(p)])
        npegs = ''.join(npeg)
        HOME.clearProperty('Colorbox_shuffle.' + npegs)
        xbmc.sleep(timed)
def Remove_Quotes(label):
    if label.startswith("'") and label.endswith("'") and len(label) > 2:
        label = label[1:-1]
        if label.startswith('"') and label.endswith('"') and len(label) > 2:
            label = label[1:-1]
    return label
def Show_Percentage():
    try:
        stot = int(xbmc.getInfoLabel('ListItem.Property(TotalEpisodes)'))
        wtot = int(xbmc.getInfoLabel('ListItem.Property(WatchedEpisodes)'))
        getcontext().prec = 6
        perc = "{:.0f}".format(100 / Decimal(stot) * Decimal(wtot))
        HOME.setProperty("Show_Percentage", perc)
    except:
        return
def Color_Only(filterimage, cname, ccname, imagecolor='ff000000', cimagecolor='ffffffff'):
    md5 = hashlib.md5(filterimage).hexdigest()
    var3 = 'Old' + cname
    var4 = 'Old' + ccname
    if not colors_dict: Load_Colors_Dict()
    if md5 not in colors_dict:
        filename = md5 + ".png"
        targetfile = os.path.join(ADDON_DATA_PATH, filename)
        Img = Check_XBMC_Internal(targetfile, filterimage)
        if not Img: return
        try:
            img = Image.open(Img)
        except Exception as e:
            log("co: %s img: %s" % (e,filterimage))
            return
        img.thumbnail((200, 200))
        img = img.convert('RGB')
        maincolor, cmaincolor = Get_Colors(img, md5)
    else:
        maincolor, cmaincolor = colors_dict[md5].split(':')
    Black_White(maincolor, cname)
    cimagecolor = Color_Modify(maincolor, cmaincolor, color_comp)
    imagecolor = Color_Modify(maincolor, cmaincolor, color_main)
    tmc = Thread(target=linear_gradient, args=(cname, HOME.getProperty(var3)[2:8], imagecolor[2:8], lgsteps, lgint, var3))
    tmc.start()
    tmcc = Thread(target=linear_gradient, args=(ccname, HOME.getProperty(var4)[2:8], cimagecolor[2:8], lgsteps, lgint, var4))
    tmcc.start()
    #linear_gradient(cname, HOME.getProperty(var3)[2:8], imagecolor[2:8], 50, 10, var3)
    #linear_gradient(ccname, HOME.getProperty(var4)[2:8], cimagecolor[2:8], 50, 10, var4)
    return imagecolor, cimagecolor
def Color_Only_Manual(filterimage, cname, imagecolor='ff000000', cimagecolor='ffffffff'):
    md5 = hashlib.md5(filterimage).hexdigest()
    if not colors_dict: Load_Colors_Dict()
    if md5 not in colors_dict:
        filename = md5 + ".png"
        targetfile = os.path.join(ADDON_DATA_PATH, filename)
        Img = Check_XBMC_Internal(targetfile, filterimage)
        if not Img: return "", ""
        try:
            img = Image.open(Img)
        except Exception as e:
            log("com: %s img: %s" % (e,filterimage))
            return "", ""
        img.thumbnail((200, 200))
        img = img.convert('RGB')
        maincolor, cmaincolor = Get_Colors(img, md5)
    else:
        maincolor, cmaincolor = colors_dict[md5].split(':')
    Black_White(maincolor, cname)
    return Color_Modify(maincolor, cmaincolor, color_main), Color_Modify(maincolor, cmaincolor, color_comp)
def Color_Modify(im_color, com_color, color_eqn):
    get_cm_color = color_eqn.strip().split(':')
    if get_cm_color[0] == 'main':
        cc_color = [int(im_color[2:4], 16), int(im_color[4:6], 16), int(im_color[6:8], 16)]
    else:
        cc_color = [int(com_color[2:4], 16), int(com_color[4:6], 16), int(com_color[6:8], 16)]
    for ccarg in get_cm_color[1].strip().split('@'):
        arg = ccarg.strip().split('*')
        if arg[0] == 'hls':
            color_mod = arg[1].strip().split(';')
            color_mod = (float(color_mod[0]), float(color_mod[1]), float(color_mod[2]))
            hls = rgb_to_hls(int(cc_color[0])/255., int(cc_color[1])/255., int(cc_color[2])/255.)
            cc_color = hls_to_rgb(one_max_loop(hls[0]+color_mod[0]), one_max_loop(hls[1]+color_mod[1]), one_max_loop(hls[2]+color_mod[2]))
        elif arg[0] == 'fhls':
            hls = rgb_to_hls(int(cc_color[0])/255., int(cc_color[1])/255., int(cc_color[2])/255.)
            color_mod = arg[1].strip().split(';')
            color_mod = (float(check_mod(color_mod[0], hls[0])), float(check_mod(color_mod[1], hls[1])), float(check_mod(color_mod[2], hls[2])))
            cc_color = hls_to_rgb(one_max_loop(color_mod[0]), one_max_loop(color_mod[1]), one_max_loop(color_mod[2]))
        elif arg[0] == 'hsv':
            color_mod = arg[1].strip().split(';')
            color_mod = (float(color_mod[0]), float(color_mod[1]), float(color_mod[2]))
            hsv = rgb_to_hsv(int(cc_color[0])/255., int(cc_color[1])/255., int(cc_color[2])/255.)
            cc_color = hsv_to_rgb(one_max_loop(hsv[0]+color_mod[0]), one_max_loop(hsv[1]+color_mod[1]), one_max_loop(hsv[2]+color_mod[2]))
        elif arg[0] == 'fhsv':
            hsv = rgb_to_hsv(int(cc_color[0])/255., int(cc_color[1])/255., int(cc_color[2])/255.)
            color_mod = arg[1].strip().split(';')
            color_mod = (float(check_mod(color_mod[0]), hsv[0]), float(check_mod(color_mod[1]), hsv[1]), float(check_mod(color_mod[2]), hsv[2]))
            cc_color = hsv_to_rgb(one_max_loop(color_mod[0]), one_max_loop(color_mod[1]), one_max_loop(color_mod[2]))
        elif arg[0] == 'bump':
            color_mod = int(arg[1])
            cc_color = (clamp(int(cc_color[0]) + color_mod), clamp(int(cc_color[1]) + color_mod), clamp(int(cc_color[2]) + color_mod))
    return RGB_to_hex(cc_color)
def Random_Color():
    return "ff" + "%06x" % random.randint(0, 0xFFFFFF)
def Complementary_Color(hex_color):
    irgb = [hex_color[2:4], hex_color[4:6], hex_color[6:8]]
    hls = rgb_to_hls(int(irgb[0], 16)/255., int(irgb[1], 16)/255., int(irgb[2], 16)/255.)
    hls = hls_to_rgb(one_max_loop(hls[0]+0.5), hls[1], hls[2])
    return RGB_to_hex(hls)
def Black_White(hex_color, prop):
    comp = hex_to_RGB(hex_color)
    contrast = "{:.0f}".format((int(comp[0]) * 0.299) + (int(comp[1]) * 0.587) + (int(comp[2]) * 0.144))
    luma = "{:.0f}".format((int(comp[0]) * 0.2126) + (int(comp[1]) * 0.7152) + (int(comp[2]) * 0.0722))
    #luma = "{:.0f}".format(math.sqrt(0.241 * math.pow(int(comp[0]),2) + 0.691 * math.pow(int(comp[1]),2) + 0.068 * math.pow(int(comp[2]),2)))
    HOME.setProperty('BW'+prop, str(contrast))
    HOME.setProperty('LUMA'+prop, str(luma))
def linear_gradient(cname, start_hex="000000", finish_hex="FFFFFF", n=10, sleep=50, s_thread_check=""):
    if start_hex == '' or finish_hex == '':
        return
    s = hex_to_RGB('#' + start_hex)
    f = hex_to_RGB('#' + finish_hex)
    RGB_list = [s]
    for t in range(1, n):
        if HOME.getProperty(s_thread_check)[2:8] != start_hex:
            return
        curr_vector = [
            int(s[j] + (float(t)/(n-1))*(f[j]-s[j]))
            for j in range(3)
        ]
        HOME.setProperty(cname, RGB_to_hex(curr_vector))
        xbmc.sleep(sleep)
    return
def hex_to_RGB(hex):
    return [int(hex[i:i+2], 16) for i in range(1,6,2)]
def RGB_to_hex(RGB):
    RGB = [int(x) for x in RGB]
    return "FF"+"".join(["0{0:x}".format(v) if v < 16 else "{0:x}".format(v) for v in RGB])
def rgb_to_hsv(r, g, b):
    maxc = max(r, g, b)
    minc = min(r, g, b)
    v = maxc
    if minc == maxc:
        return 0.0, 0.0, v
    s = (maxc-minc) / maxc
    rc = (maxc-r) / (maxc-minc)
    gc = (maxc-g) / (maxc-minc)
    bc = (maxc-b) / (maxc-minc)
    if r == maxc:
        h = bc-gc
    elif g == maxc:
        h = 2.0+rc-bc
    else:
        h = 4.0+gc-rc
    h = (h/6.0) % 1.0
    return h, s, v
def hsv_to_rgb(h, s, v):
    if s == 0.0: v*=255; return (int(v), int(v), int(v))
    i = int(h*6.)
    f = (h*6.)-i; p,q,t = int(255*(v*(1.-s))), int(255*(v*(1.-s*f))), int(255*(v*(1.-s*(1.-f)))); v*=255; i%=6
    if i == 0: return (int(v), int(t), int(p))
    if i == 1: return (int(q), int(v), int(p))
    if i == 2: return (int(p), int(v), int(t))
    if i == 3: return (int(p), int(q), int(v))
    if i == 4: return (int(t), int(p), int(v))
    if i == 5: return (int(v), int(p), int(q))
def rgb_to_hls(r, g, b):
    maxc = max(r, g, b)
    minc = min(r, g, b)
    l = (minc+maxc)/2.0
    if minc == maxc:
        return 0.0, l, 0.0
    if l <= 0.5:
        s = (maxc-minc) / (maxc+minc)
    else:
        s = (maxc-minc) / (2.0-maxc-minc)
    rc = (maxc-r) / (maxc-minc)
    gc = (maxc-g) / (maxc-minc)
    bc = (maxc-b) / (maxc-minc)
    if r == maxc:
        h = bc-gc
    elif g == maxc:
        h = 2.0+rc-bc
    else:
        h = 4.0+gc-rc
    h = (h/6.0) % 1.0
    return h, l, s
def hls_to_rgb(h, l, s):
    if s == 0.0:
        return int(l*255), int(l*255), int(l*255)
    if l <= 0.5:
        m2 = l * (1.0+s)
    else:
        m2 = l+s-(l*s)
    m1 = 2.0*l - m2
    return (int(_v(m1, m2, h+ONE_THIRD)*255), int(_v(m1, m2, h)*255), int(_v(m1, m2, h-ONE_THIRD)*255))
def _v(m1, m2, hue):
    hue = hue % 1.0
    if hue < ONE_SIXTH:
        return m1 + (m2-m1)*hue*6.0
    if hue < 0.5:
        return m2
    if hue < TWO_THIRD:
        return m1 + (m2-m1)*(TWO_THIRD-hue)*6.0
    return m1
def one_max_loop(oml):
    if abs(oml) > 1.0:
        return abs(oml) - 1.0
    else:
        return abs(oml)
def check_mod(mod, hls):
    if mod == '-':
        return float(hls)
    return float(mod)
def Get_Colors(img, md5):
    if not colors_dict: Load_Colors_Dict()
    if md5 not in colors_dict:
        colour_tuple = [None, None, None]
        for channel in range(3):
            pixels = img.getdata(band=channel)
            values = []
            for pixel in pixels:
                values.append(pixel)
            colour_tuple[channel] = clamp(sum(values) / len(values))
        imagecolor = 'ff%02x%02x%02x' % tuple(colour_tuple)
        cimagecolor = Complementary_Color(imagecolor)
        Write_Colors_Dict(md5,imagecolor,cimagecolor)
    else:
        imagecolor, cimagecolor = colors_dict[md5].split(':')
    return imagecolor, cimagecolor
def Check_XBMC_Internal(targetfile, filterimage):
    cachedthumb = xbmc.getCacheThumbName(filterimage)
    xbmc_vid_cache_file = os.path.join("special://profile/Thumbnails/Video", cachedthumb[0], cachedthumb)
    xbmc_cache_filep = os.path.join("special://profile/Thumbnails/", cachedthumb[0], cachedthumb[:-4] + ".jpg")
    xbmc_cache_filej = os.path.join("special://profile/Thumbnails/", cachedthumb[0], cachedthumb[:-4] + ".png")
    if xbmcvfs.exists(xbmc_cache_filej):
        return xbmc.translatePath(xbmc_cache_filej)
    elif xbmcvfs.exists(xbmc_cache_filep):
        return xbmc.translatePath(xbmc_cache_filep)
    elif xbmcvfs.exists(xbmc_vid_cache_file):
        return xbmc.translatePath(xbmc_vid_cache_file)
    else:
        filterimage = urllib.unquote(filterimage.replace("image://", "")).decode('utf8')
        if filterimage.endswith("/"):
            filterimage = filterimage[:-1]
        xbmcvfs.copy(filterimage, targetfile)
        return targetfile
    return
def Check_XBMC_Cache(targetfile):
    cachedthumb = xbmc.getCacheThumbName(targetfile)
    xbmc_vid_cache_file = os.path.join("special://profile/Thumbnails/Video", cachedthumb[0], cachedthumb)
    xbmc_cache_filep = os.path.join("special://profile/Thumbnails/", cachedthumb[0], cachedthumb[:-4] + ".jpg")
    xbmc_cache_filej = os.path.join("special://profile/Thumbnails/", cachedthumb[0], cachedthumb[:-4] + ".png")
    if xbmcvfs.exists(xbmc_cache_filej):
        return xbmc.translatePath(xbmc_cache_filej)
    elif xbmcvfs.exists(xbmc_cache_filep):
        return xbmc.translatePath(xbmc_cache_filep)
    elif xbmcvfs.exists(xbmc_vid_cache_file):
        return xbmc.translatePath(xbmc_vid_cache_file)
    if xbmcvfs.exists(targetfile):
        return targetfile
    return ""
def Get_Frequent_Color(img):
    w, h = img.size
    pixels = img.getcolors(w * h)
    most_frequent_pixel = pixels[0]
    for count, colour in pixels:
        if count > most_frequent_pixel[0]:
            most_frequent_pixel = (count, colour)
    return 'ff%02x%02x%02x' % tuple(most_frequent_pixel[1])
def Resize_Image(img, scale):
    width, height = img.size
    qwidth = width / scale
    qheight = height / scale
    if qwidth % 2 != 0:
        qwidth += 1
    if qheight % 2 != 0:
        qheight += 1
    return img.resize((qwidth, qheight), Image.ANTIALIAS)
def clamp(x):
    return max(0, min(x, 255))
def Load_Colors_Dict():
    try:
        with open(ADDON_COLORS) as file:
            for line in file:
                a, b, c = line.strip().split(':')
                global colors_dict
                colors_dict[a] = b + ':' + c
    except:
        log ("no colors.txt yet")
def Write_Colors_Dict(md5,imagecolor,cimagecolor):
    global colors_dict
    colors_dict[md5] = imagecolor + ':' + cimagecolor
    with open(ADDON_COLORS, 'w') as file:
        for id, values in colors_dict.items():
            file.write(':'.join([id] + values.split(':')) + '\n')
def log(txt):
    if isinstance(txt, str):
        txt = txt.decode("utf-8")
    message = u'%s: %s' % (ADDON_ID, txt)
    xbmc.log(msg=message.encode("utf-8"), level=xbmc.LOGNOTICE)
def prettyprint(string):
    log(simplejson.dumps(string, sort_keys=True, indent=4, separators=(',', ': ')))
ColorBox_filename_map = {
        'blur':         fnblur,
        'pixelate':     fnpixelate,
        'shiftblock':   fnshiftblock,
        'pixelnone':    fnpixelnone,
        'pixelwaves':   fnpixelwaves,
        'pixelrandom':  fnpixelrandom,
        'pixelfile':    fnpixelfile,
        'pixelfedges':  fnpixelfedges,
        'pixeledges':   fnpixeledges,
        'fakelight':    fnfakelight,
        'twotone':      fntwotone,
        'posterize':    fnposterize,
        'distort':      fndistort,
        'halftone':     fnhalftone,
        'angletone':    fnangletone,
        'dither':       fndither,
        'desaturate':   fndesaturate,
        'sharpness':    fnsharpness,
        'splicer':      fnsplicer,
        'dataglitch':   fndataglitch}
ColorBox_function_map = {
        'blur':         blur,
        'pixelate':     pixelate,
        'shiftblock':   shiftblock,
        'pixelnone':    pixelnone,
        'pixelwaves':   pixelwaves,
        'pixelrandom':  pixelrandom,
        'pixelfile':    pixelfile,
        'pixelfedges':  pixelfedges,
        'pixeledges':   pixeledges,
        'fakelight':    fakelight,
        'twotone':      twotone,
        'posterize':    posterize,
        'distort':      distort,
        'halftone':     halftone,
        'angletone':    angletone,
        'dither':       dither,
        'desaturate':   desaturate,
        'sharpness':    sharpness,
        'splicer':      splicer,
        'dataglitch':   dataglitch}