import xbmc
import xbmcaddon
import xbmcgui
import xbmcvfs
import xbmcplugin
import os, sys, time
import simplejson
import hashlib
from urllib.parse import unquote
import math
from PIL import Image, ImageOps, ImageEnhance, ImageDraw, ImageStat, ImageFilter
from .imageoperations import MyGaussianBlur
from decimal import *
from threading import Thread
ADDON =             xbmcaddon.Addon()
ADDON_ID =          ADDON.getAddonInfo('id')
ADDON_LANGUAGE =    ADDON.getLocalizedString
ADDON_DATA_PATH =   os.path.join(xbmcvfs.translatePath("special://profile/addon_data/%s" % ADDON_ID))
ADDON_COLORS =      os.path.join(ADDON_DATA_PATH, "colors.db")
#ADDON_SETTINGS =    os.path.join(ADDON_DATA_PATH, "settings.")
HOME =              xbmcgui.Window(10000)
ONE_THIRD =         round(1/3, 1)
ONE_SIXTH =         round(1/6, 1)
TWO_THIRD =         round(2/3, 1)
lgint =             10
lgsteps =           50
radius =            1
pixelsize =         2
bits =              1
black =             "#000000"
white =             "#ffffff"
quality =           8
blend =             1.0
color_comp =        "comp:" #[comp|main]:hls*-0.5;0.0;0.1@fhsv*-;-0.1;0.3@bump*[0-255] <- any amount of ops/any order, if no ops just use 'main:' or 'comp:'
color_main =        "main:" #[comp|main]:fhls*-;0.5;0.5@bump*[0-255] <- any amount of ops/any order, if no ops just use 'main:' or 'comp:'
colors_dict =       {}
def fnblur(): return str(radius) + str(quality)
def fnpixelate(): return str(pixelsize) + str(quality)
def fntwotone(): return str(black) + str(white) + str(quality)
def fnposterize(): return str(bits) + str(quality)
def ColorBox_go_map(filterimage, imageops, gqual=0):
    gqual = quality
    filename = hashlib.md5(filterimage.encode('utf-8')).hexdigest() + str(blend) + '-'
    for cmarg in imageops.strip().split('-'):
        filename = filename + cmarg + ColorBox_filename_map[cmarg]()
    targetfile = os.path.join(ADDON_DATA_PATH, filename + '.png')
    Cache = Check_XBMC_Cache(targetfile)
    if Cache != "":
        return Cache
    Img = Check_XBMC_Internal(targetfile, filterimage)
    if not Img:
        return
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
def set_blend(new_value):
    global blend
    blend = round(int(new_value) / 100, 1)
    xbmc.executebuiltin('Skin.SetString(colorbox_blend,'+str(new_value)+')')
def set_quality(new_value):
    global quality
    quality = int(new_value)
    xbmc.executebuiltin('Skin.SetString(colorbox_quality,'+str(new_value)+')')
def set_blursize(new_value):
    global radius
    radius = int(new_value)
    xbmc.executebuiltin('Skin.SetString(colorbox_blursize,'+str(new_value)+')')
def set_pixelsize(new_value):
    global pixelsize
    pixelsize = int(new_value)
    xbmc.executebuiltin('Skin.SetString(colorbox_pixelsize,'+str(pixelsize)+')')
def set_bitsize(new_value):
    global bits
    bits = int(new_value)
    if bits > 8: bits = 8
    if bits < 1: bits = 1
    xbmc.executebuiltin('Skin.SetString(colorbox_bitsize,'+str(new_value)+')')
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
def blur(img):
    imgfilter = MyGaussianBlur(radius=radius)
    img = img.filter(imgfilter)
    return img
def pixelate(img):
    return image_pixelate(img)
def twotone(img):
    return image_recolorize(img,black,white)
def posterize(img):
    return image_posterize(img,bits)
def image_recolorize(src, black="#000000", white="#FFFFFF"):
    return ImageOps.colorize(ImageOps.grayscale(src), black, white)
def image_posterize(img, bits=1):
    return ImageOps.posterize(img, bits)
def image_recolorize(src, black="#000000", white="#FFFFFF"):
    return ImageOps.colorize(ImageOps.grayscale(src), black, white)
def image_posterize(img, bits=1):
    return ImageOps.posterize(img, bits)
def image_pixelate(img):
    backgroundColor = (0,)*3
    image = img
    image = image.resize((image.size[0]//pixelsize, image.size[1]//pixelsize), Image.NEAREST)
    image = image.resize((image.size[0]*pixelsize, image.size[1]*pixelsize), Image.NEAREST)
    pixel = image.load()
    for i in range(0,image.size[0],pixelsize):
      for j in range(0,image.size[1],pixelsize):
        for r in range(pixelsize):
          pixel[i+r,j] = backgroundColor
          pixel[i,j+r] = backgroundColor
    return image
def Remove_Quotes(label):
    if label.startswith("'") and label.endswith("'") and len(label) > 2:
        label = label[1:-1]
        if label.startswith('"') and label.endswith('"') and len(label) > 2:
            label = label[1:-1]
    return label
def Color_Only(filterimage, cname, ccname, imagecolor='ff000000', cimagecolor='ffffffff'):
    md5 = hashlib.md5(filterimage.encode('utf-8')).hexdigest()
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
    #Black_White(maincolor, cname)
    imagecolor = Color_Modify(maincolor, cmaincolor, color_main)
    cimagecolor = Color_Modify(maincolor, cmaincolor, color_comp)
    tmc = Thread(target=linear_gradient, args=(cname, HOME.getProperty(var3)[2:8], imagecolor[2:8], lgsteps, lgint, var3))
    tmc.start()
    tmcc = Thread(target=linear_gradient, args=(ccname, HOME.getProperty(var4)[2:8], cimagecolor[2:8], lgsteps, lgint, var4))
    tmcc.start()
    #linear_gradient(cname, HOME.getProperty(var3)[2:8], imagecolor[2:8], 50, 10, var3)
    #linear_gradient(ccname, HOME.getProperty(var4)[2:8], cimagecolor[2:8], 50, 10, var4)
    return imagecolor, cimagecolor
def Color_Only_Manual(filterimage, cname, imagecolor='ff000000', cimagecolor='ffffffff'):
    md5 = hashlib.md5(filterimage.encode('utf-8')).hexdigest()
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
    #Black_White(maincolor, cname)
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
def Complementary_Color(hex_color):
    irgb = [hex_color[2:4], hex_color[4:6], hex_color[6:8]]
    hls0 = round(int(irgb[0], 16)/255, 1)
    hls1 = round(int(irgb[1], 16)/255, 1)
    hls2 = round(int(irgb[2], 16)/255, 1)
    hls = rgb_to_hls(hls0, hls1, hls2)
    hls = hls_to_rgb(one_max_loop(hls[0]+0.33), hls[1], hls[2])
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
        HOME.setProperty(cname, 'FF{:02x}{:02x}{:02x}'.format(curr_vector[0], curr_vector[1] , curr_vector[2]))
        #HOME.setProperty(cname, RGB_to_hex(curr_vector))
        xbmc.sleep(sleep)
    return
def hex_to_RGB(hex):
    return [int(hex[i:i+2], 16) for i in range(1,6,2)]
def RGB_to_hex(RGB):
    RGB = [int(x) for x in RGB]
    return "FF"+"".join(["0{0:x}".format(v) if v < 16 else "{0:x}".format(v) for v in RGB])
    #return 'FF{:02x}{:02x}{:02x}'.format(RGB[0], RGB[1] , RGB[2])
def rgb_to_hsv(r, g, b):
    maxc = max(r, g, b)
    minc = min(r, g, b)
    v = maxc
    if minc == maxc:
        return 0.0, 0.0, v
    s = (maxc-minc) // maxc
    rc = (maxc-r) // (maxc-minc)
    gc = (maxc-g) // (maxc-minc)
    bc = (maxc-b) // (maxc-minc)
    if r == maxc:
        h = bc-gc
    elif g == maxc:
        h = 2.0+rc-bc
    else:
        h = 4.0+gc-rc
    h = (h//6.0) % 1.0
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
    l1 = (minc+maxc)/2.0
    l = round(l1, 1)
    if minc == maxc:
        return 0.0, l, 0.0
    if l <= 0.5:
        s1 = (maxc-minc) / (maxc+minc)
        s = round(s1, 1)
    else:
        s2 = (maxc-minc) / (2.0-maxc-minc)
        s = round(s2, 1)
    rc = round((maxc-r) / (maxc-minc), 1)
    gc = round((maxc-g) / (maxc-minc), 1)
    bc = round((maxc-b) / (maxc-minc), 1)
    
    if r == maxc:
        h1 = bc-gc
    elif g == maxc:
        h1 = 2.0+rc-bc
    else:
        h1 = 4.0+gc-rc
    h = (h1/6.0) % 1.0
    h = round(h, 1)
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
            colour_tuple[channel] = clamp(sum(values) // len(values))
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
        return xbmcvfs.translatePath(xbmc_cache_filej)
    elif xbmcvfs.exists(xbmc_cache_filep):
        return xbmcvfs.translatePath(xbmc_cache_filep)
    elif xbmcvfs.exists(xbmc_vid_cache_file):
        return xbmcvfs.translatePath(xbmc_vid_cache_file)
    else:
        filterimage = Remove_Quotes(filterimage.replace("image://", ""))
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
        return xbmcvfs.translatePath(xbmc_cache_filej)
    elif xbmcvfs.exists(xbmc_cache_filep):
        return xbmcvfs.translatePath(xbmc_cache_filep)
    elif xbmcvfs.exists(xbmc_vid_cache_file):
        return xbmcvfs.translatePath(xbmc_vid_cache_file)
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
    qwidth = width // scale
    qheight = height // scale
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
        log ("no colors.db yet")
def Write_Colors_Dict(md5,imagecolor,cimagecolor):
    global colors_dict
    colors_dict[md5] = imagecolor + ':' + cimagecolor
    with open(ADDON_COLORS, 'w') as file:
        for id, values in colors_dict.items():
            file.write(':'.join([id] + values.split(':')) + '\n')
def log(txt, loglevel=xbmc.LOGDEBUG):
    """log message to kodi logfile"""
    if sys.version_info.major < 3:
        if isinstance(txt, unicode):
            txt = txt.encode('utf-8')
    if loglevel == xbmc.LOGDEBUG:
        loglevel = xbmc.LOGINFO
        xbmc.log("%s --> %s" % (ADDON_ID, txt), level=loglevel)
def prettyprint(string):
    log(simplejson.dumps(string, sort_keys=True, indent=4, separators=(',', ': ')))
ColorBox_filename_map = {
        'pixelate':     fnpixelate,
        'twotone':      fntwotone,
        'posterize':    fnposterize,
        'blur':         fnblur}
ColorBox_function_map = {
        'pixelate':     pixelate,
        'twotone':      twotone,
        'posterize':    posterize,
        'blur':         blur}
def try_encode(text, encoding="utf-8"):
    '''helper to encode a string to utf-8'''
    if sys.version_info.major == 3:
        return text
    else:
        try:
            return text.encode(encoding, "ignore")
        except Exception:
            return text