# -*- coding: utf-8 -*-

'''
    Funimation|Now Add-on
    Copyright (C) 2016 Funimation|Now

    This program is free software: you can redistribute it and/or modify
    it under the terms of the GNU General Public License as published by
    the Free Software Foundation, either version 3 of the License, or
    (at your option) any later version.

    This program is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU General Public License for more details.

    You should have received a copy of the GNU General Public License
    along with this program.  If not, see <http://www.gnu.org/licenses/>.
'''



import xbmc;
import xbmcaddon;
import xbmcvfs;
import logging;
import re;
import os;
import json;
import gc;
import time;


addon = xbmcaddon.Addon();
addonInfo = addon.getAddonInfo;

lang = addon.getLocalizedString;
makeFile = xbmcvfs.mkdir;
condVisibility = xbmc.getCondVisibility;
execute = xbmc.executebuiltin;
sleep = xbmc.sleep;

dataPath = xbmc.translatePath(addonInfo('profile')).decode('utf-8');
tokensFile = os.path.join(dataPath, 'tokens.db');
synchFile = os.path.join(dataPath, 'synch.db');
cacheFile = os.path.join(dataPath, 'cache.db');


logger = logging.getLogger('funimationnow');

#media_buttons = None;


def getAddonInfo(key):

    return addonInfo(key);


def getLogger():

    try:

        if not len(logger.handlers):
            logger = logging.getLogger('funimationnow');

        logger.debug('NEXT RUN');

    except:

        from resources.lib.modules.loghandler import loghandler;

        loglevel = (int(setting('loglvl')) + 1) * 10;
        logger = logging.getLogger('funimationnow');

        logger.setLevel(loglevel);

        formatter = logging.Formatter('[{0}] %(funcName)s : %(message)s'.format(getAddonInfo('id')));
        lh = loghandler();

        lh.setLevel(loglevel);
        lh.setFormatter(formatter);

        logger.addHandler(lh);

        logger.debug('INITIALRUN');

    return logger;


def setting(setting_id, setting_value=None):

    #Added down here because it does not appear to get updated settings unless called each time.
    addon = xbmcaddon.Addon();

    if setting_value is not None:
        return addon.setSetting(setting_id, setting_value);

    else:
        return addon.getSetting(setting_id);


def lock():

    xbmc.executebuiltin('ActivateWindow(busydialog)');


def unlock():

    gc.collect();

    xbmc.executebuiltin('Dialog.Close(busydialog)');
        
    while xbmc.getCondVisibility('Window.IsActive(busydialog)'):
        time.sleep(.1);
        

def idle():
    return execute('Dialog.Close(busydialog)');

    pass;


def getToken(system):
    import tokens;

    return tokens.getToken(system);


def setToken(token, user, system):
    import tokens;

    return tokens.setToken(token, user, system);


def text2HelpMultiSize(text, type, bgcolor, txtcolor, fontsize, bsize, twidth, font, filename, multiplier=1, sharpen=False, bgimage=None):

    import textwrap;

    from PIL import Image;
    from PIL import ImageFont;


    defaultpath = os.path.join(getAddonInfo('path'), 'resources/skins/default');
    font1 = ImageFont.truetype(os.path.join(defaultpath, 'fonts/OpenSans-%s.ttf' % font[0]), fontsize);
    font2 = ImageFont.truetype(os.path.join(defaultpath, 'fonts/OpenSans-%s.ttf' % font[1]), fontsize);

    if bgimage:
        textimgL = Image.open(os.path.join(defaultpath, 'media/%s' % bgimage));


    imgs = list();

    for idx, lineset in enumerate(text[0], 0):

        try:

            line1 = text[0][idx];
            line2 = text[1][idx];

            for line in line1:

                lines = textwrap.wrap(line, width=twidth);

                for ln in lines:

                    textsize = font1.getsize(ln);
                    imgs.append([ln, font1, textsize]);


            for line in line2:

                lines = textwrap.wrap(line, width=twidth);

                for ln in lines:

                    textsize = font2.getsize(ln);
                    imgs.append([ln, font2, textsize]);


            #textsize = font2.getsize('_+_+_+_');
            #imgs.append(['_+_+_+_', font2, textsize]);

            #textsize = font2.getsize('_+_+_+_');
            #imgs.append(['_+_+_+_', font2, textsize]);

            textsize = textimgL.size;
            imgs.append([textimgL, None, textsize]);

        except Exception as inst:
            logger.error(inst);
            logger.error(idx)

    '''for idx, lineset in enumerate(text[0], 0):

        line1 = lineset;
        line2 = text[1][idx];

        lines = textwrap.wrap(line1, width=twidth);

        #textsize = font1.getsize('_+_+_+_');
        #imgs.append(['_+_+_+_', font1, textsize]);

        for ln in lines:

            textsize = font1.getsize(ln);
            imgs.append([ln, font1, textsize]);


        #textsize = font2.getsize('_+_+_+_');
        #imgs.append(['_+_+_+_', font2, textsize]);

        lines = textwrap.wrap(line2, width=twidth);

        for ln in lines:

            ln = ln.replace(u"\u2022", u"~~~~~~\u2022")
            lns = ln.split('~~~~~~');

            for lnr in lns:

                logger.error(lnr.encode('utf-8'))

                textsize = font2.getsize(lnr);
                imgs.append([lnr, font2, textsize]);


        #textsize = font2.getsize('_+_+_+_');
        #imgs.append(['_+_+_+_', font2, textsize]);

        #textsize = font2.getsize('_+_+_+_');
        #imgs.append(['_+_+_+_', font2, textsize]);

        textsize = textimgL.size;
        imgs.append([textimgL, None, textsize]);
        '''

    ih = 0;
    iw = 2560;

    for img in imgs:
        ih += int(img[2][1] * .8);


    return ih;


def text2HelpSize(text, type, bgcolor, txtcolor, fontsize, bsize, twidth, font, filename, multiplier=1, sharpen=False, bgimage=None):

    import textwrap;

    from PIL import ImageFont;


    defaultpath = os.path.join(getAddonInfo('path'), 'resources/skins/default');
    font = ImageFont.truetype(os.path.join(defaultpath, 'fonts/OpenSans-%s.ttf' % font), fontsize);

    imgs = list();

    for line in text.split('~~~'):

        lines = textwrap.wrap(line, width=twidth);

        for ln in lines:

            textsize = font.getsize(ln);

            imgs.append([ln, font, textsize]);

    ih = 0;
    iw = 2560;

    for img in imgs:
        ih += int(img[2][1] * .8);


    return ih;


def text2HelpMultiWrap(text, type, bgcolor, txtcolor, fontsize, bsize, twidth, font, filename, multiplier=1, sharpen=False, bgimage=None):

    import textwrap;

    from PIL import Image;
    from PIL import ImageFont;
    from PIL import ImageDraw;
    from PIL import ImageFilter;

    
    defaultpath = os.path.join(getAddonInfo('path'), 'resources/skins/default');
    font1 = ImageFont.truetype(os.path.join(defaultpath, 'fonts/OpenSans-%s.ttf' % font[0]), fontsize);
    font2 = ImageFont.truetype(os.path.join(defaultpath, 'fonts/OpenSans-%s.ttf' % font[1]), fontsize);

    if bgimage:
        textimgL = Image.open(os.path.join(defaultpath, 'media/%s' % bgimage));


    imgs = list();

    try:

        for idx, lineset in enumerate(text[0], 0):

            line1 = text[0][idx];
            line2 = text[1][idx];

            for line in line1:

                lines = textwrap.wrap(line, width=twidth);

                for ln in lines:

                    textsize = font1.getsize(ln);
                    imgs.append([ln, font1, textsize]);


            for line in line2:

                lines = textwrap.wrap(line, width=twidth);

                for ln in lines:

                    textsize = font2.getsize(ln);
                    imgs.append([ln, font2, textsize]);


            #textsize = font2.getsize('_+_+_+_');
            #imgs.append(['_+_+_+_', font2, textsize]);

            #textsize = font2.getsize('_+_+_+_');
            #imgs.append(['_+_+_+_', font2, textsize]);

            textsize = textimgL.size;
            imgs.append([textimgL, None, textsize]);

            '''line1 = lineset;
            line2 = text[1][idx];

            lines = textwrap.wrap(line1, width=twidth);

            #textsize = font1.getsize('_+_+_+_');
            #imgs.append(['_+_+_+_', font1, textsize]);

            for ln in lines:

                textsize = font1.getsize(ln);
                imgs.append([ln, font1, textsize]);


            #textsize = font2.getsize('_+_+_+_');
            #imgs.append(['_+_+_+_', font2, textsize]);

            lines = textwrap.wrap(line2, width=twidth);

            for ln in lines:

                ln = ln.replace(u"\u2022", u"~~~~~~\u2022")
                lns = ln.split('~~~~~~');

                for lnr in lns:

                    textsize = font2.getsize(lnr);
                    imgs.append([lnr, font2, textsize]);


            #textsize = font2.getsize('_+_+_+_');
            #imgs.append(['_+_+_+_', font2, textsize]);

            #textsize = font2.getsize('_+_+_+_');
            #imgs.append(['_+_+_+_', font2, textsize]);

            textsize = textimgL.size;
            imgs.append([textimgL, None, textsize]);'''

        ih = 0;
        iw = 2560;

        for img in imgs:
            ih += int(img[2][1] * .8);

        textimg = Image.new(type, bsize, bgcolor);
        textdraw = ImageDraw.Draw(textimg);

        ih = -5;

        for idx, img in enumerate(imgs, 0):

            if img[0] == '_+_+_+_':
                textdraw.text((5, ih), img[0], (255, 255, 255), img[1]);

            elif img[1] is None:
                pass;
                textimg.paste(textimgL, (5, ih));

            else:
                textdraw.text((5, ih), img[0], txtcolor, img[1]);

            ih += int(img[2][1] * .8);

    except Exception as inst:
        logger.error(inst);


    textimg.filter(ImageFilter.SHARPEN);
    textimg.save(filename, 'PNG', optimize=1);


    return textimg;


def text2HelpWrap(text, type, bgcolor, txtcolor, fontsize, bsize, twidth, font, filename, multiplier=1, sharpen=False, bgimage=None):

    import textwrap;

    from PIL import Image;
    from PIL import ImageFont;
    from PIL import ImageDraw;
    from PIL import ImageFilter;

    defaultpath = os.path.join(getAddonInfo('path'), 'resources/skins/default');
    font = ImageFont.truetype(os.path.join(defaultpath, 'fonts/OpenSans-%s.ttf' % font), fontsize);

    imgs = list();

    for line in text.split('~~~'):

        lines = textwrap.wrap(line, width=twidth);
        
        for ln in lines:

            textsize = font.getsize(ln);

            imgs.append([ln, font, textsize]);

    ih = 0;
    iw = 2560;

    for img in imgs:
        ih += int(img[2][1] * .8);

    textimg = Image.new(type, bsize, bgcolor);
    textdraw = ImageDraw.Draw(textimg);

    ih = -5;

    for idx, img in enumerate(imgs, 0):

        if img[0] == '_+_+_+_':
            textdraw.text((5, ih), img[0], (255, 255, 255), img[1]);

        else:
            textdraw.text((5, ih), img[0], txtcolor, img[1]);

        ih += int(img[2][1] * .8);


    textimg.filter(ImageFilter.SHARPEN);
    textimg.save(filename, 'PNG', optimize=1);


    return textimg;


def text2Image(text, type, bgcolor, txtcolor, fontsize, font, filename, multiplier=1, sharpen=False, bgimage=None):

    from PIL import Image;
    from PIL import ImageFont;
    from PIL import ImageDraw;
    from PIL import ImageFilter;


    defaultpath = os.path.join(getAddonInfo('path'), 'resources/skins/default');
    font = ImageFont.truetype(os.path.join(defaultpath, 'fonts/OpenSans-%s.ttf' % font), fontsize);

    textimg = Image.new(type, (1, 1));
    textdraw = ImageDraw.Draw(textimg);
    textsize = textdraw.textsize(text, font);

    if bgcolor:

        textimg = Image.new(type, (textsize[0] * multiplier, textsize[1] * multiplier), bgcolor);
        textdraw = ImageDraw.Draw(textimg);

        textdraw.text((5, -9), text, txtcolor, font);

    else:

        textimg = Image.open(os.path.join(defaultpath, 'media/%s' % bgimage));
        textdraw = ImageDraw.Draw(textimg);

        imgsize = textimg.size;

        textdraw.text((int(((imgsize[0] - textsize[0]) / 2)), int(((imgsize[1] - textsize[1]) / 2))), text, txtcolor, font);

    

    if sharpen:
        textimg.filter(ImageFilter.SHARPEN);

    #textimg.save(os.path.join(defaultpath, 'media', '%s.png' % filename), 'PNG', optimize=1);
    textimg.save(filename, 'PNG', optimize=1);

    return textimg.size;


def text2Display(text, type, bgcolor, txtcolor, fontsize, font, filename, multiplier=1, sharpen=False, bgimage=None):

    from PIL import Image;
    from PIL import ImageFont;
    from PIL import ImageDraw;
    from PIL import ImageFilter;


    #savepath = xbmc.translatePath(os.path.join('special://userdata/addon_data', getAddonInfo('id')));
    defaultpath = os.path.join(getAddonInfo('path'), 'resources/skins/default');
    font = ImageFont.truetype(os.path.join(defaultpath, 'fonts/OpenSans-%s.ttf' % font), fontsize);

    textimg = Image.new(type, (1, 1));
    textdraw = ImageDraw.Draw(textimg);
    textsize = font.getsize(text);

    if bgcolor:

        textimg = Image.new(type, (textsize[0] * multiplier, textsize[1] * multiplier), bgcolor);
        textdraw = ImageDraw.Draw(textimg);

        textdraw.text((0, 0), text, txtcolor, font);

    else:

        textimg = Image.open(os.path.join(defaultpath, 'media/%s' % bgimage));
        textdraw = ImageDraw.Draw(textimg);

        imgsize = textimg.size;

        textdraw.text((int(((imgsize[0] - textsize[0]) / 2)), int(((imgsize[1] - textsize[1]) / 2))), text, txtcolor, font);
    

    if sharpen:
        textimg.filter(ImageFilter.SHARPEN);


    textimg.save(filename, 'PNG', optimize=True);

    while not os.path.isfile(filename):
        logger.debug(filename)
        logger.debug('FILE NOT READY SLEEPING')
        xbmc.sleep(200);
    #textimg.save(os.path.join(defaultpath, 'media', '%s.jpg' % filename), "JPEG", quality=100);#, optimize=True, progressive=True)

    return textimg.size;


def text2DisplayWrap(text, type, bgcolor, txtcolor, fontsize, bsize, twidth, font, filename, multiplier=1, sharpen=False, bgimage=None):

    import textwrap;

    from PIL import Image;
    from PIL import ImageFont;
    from PIL import ImageDraw;
    from PIL import ImageFilter;


    #savepath = xbmc.translatePath(os.path.join('special://userdata/addon_data', getAddonInfo('id')));
    defaultpath = os.path.join(getAddonInfo('path'), 'resources/skins/default');
    font = ImageFont.truetype(os.path.join(defaultpath, 'fonts/OpenSans-%s.ttf' % font), fontsize);

    imgs = list();

    lines = textwrap.wrap(text, width=twidth);

    for line in lines:

        textsize = font.getsize(line);

        imgs.append([line, font, textsize]);

    ih = 0;

    for img in imgs:
        ih += int(img[2][1] * .8);

    textimg = Image.new(type, bsize, bgcolor);
    textdraw = ImageDraw.Draw(textimg);

    ih = -5;

    for idx, img in enumerate(imgs, 0):

        textdraw.text((5, ih), img[0], txtcolor, img[1]);

        ih += int(img[2][1] * .8);


    textimg.filter(ImageFilter.SHARPEN);
    textimg.save(filename, 'PNG', optimize=1);

    while not os.path.isfile(filename):
        logger.debug(filename)
        logger.debug('FILE NOT READY SLEEPING')
        xbmc.sleep(200);


    return textimg;


def text2Button(text, type, bgcolor, txtcolor, fontsize, font, wh, offset, filename, sharpen=False, bgimage=None, filecheck=False):

    from PIL import Image;
    from PIL import ImageFont;
    from PIL import ImageDraw;
    from PIL import ImageFilter;


    media_buttons = runDirectoryChecks('media/buttons');

    defaultpath = os.path.join(getAddonInfo('path'), 'resources/skins/default');
    font = ImageFont.truetype(os.path.join(defaultpath, 'fonts/OpenSans-%s.ttf' % font), fontsize);   

    if bgcolor:

        texturefocusimg = Image.new(type, wh, bgcolor[0]);
        texturenofocusimg = Image.new(type, wh, bgcolor[1]);

    else:

        texturefocusimg = Image.open(os.path.join(defaultpath, 'media/%s' % bgimage[0]));
        texturenofocusimg = Image.open(os.path.join(defaultpath, 'media/%s' % bgimage[1]));


    texturefocusdraw = ImageDraw.Draw(texturefocusimg);
    texturenofocusdraw = ImageDraw.Draw(texturenofocusimg);

    texturefocusdraw.text(offset, text, txtcolor[0], font);
    texturenofocusdraw.text(offset, text, txtcolor[1], font);

    if sharpen:
        texturefocusimg.filter(ImageFilter.SHARPEN);
        texturenofocusimg.filter(ImageFilter.SHARPEN);

    #texturefocusimg.save(os.path.join(defaultpath, 'media', '%s.png' % filename[0]), 'PNG', optimize=1);
    #texturenofocusimg.save(os.path.join(defaultpath, 'media', '%s.png' % filename[1]), 'PNG', optimize=1);
    fileexists = False;

    mBtn1 = os.path.join(media_buttons, '%s.png' % filename[0]);
    mBtn2 = os.path.join(media_buttons, '%s.png' % filename[1]);

    if filecheck:

        file1 = os.path.isfile(mBtn1);
        file2 = os.path.isfile(mBtn2);

        if file1 and file2:
            fileexists = True;


    if fileexists is False:
        texturefocusimg.save(mBtn1, 'PNG', optimize=1);
        texturenofocusimg.save(mBtn2, 'PNG', optimize=1);


def text2HomeMenu(idx, text, filecheck=False):

    from PIL import Image;
    from PIL import ImageFont;
    from PIL import ImageDraw;
    from PIL import ImageFilter;

    try:

        media_buttons = runDirectoryChecks('media/buttons');

        defaultpath = os.path.join(getAddonInfo('path'), 'resources/skins/default');
        #savepath = xbmc.translatePath(os.path.join('special://userdata/addon_data', getAddonInfo('id'), 'menuitems'));

        menufont26 = ImageFont.truetype(os.path.join(defaultpath, 'fonts/OpenSans-ExtraBold.ttf'), 26);

        textimg = Image.new("RGBA", (1, 1));
        textdraw = ImageDraw.Draw(textimg);
        textsize = textdraw.textsize(text, menufont26);
        textimg = Image.new("RGB", textsize, (219, 219, 219));
        textdraw = ImageDraw.Draw(textimg);
        textdraw.text((0, -2), text, (0, 0, 0), menufont26);

        menuimg = Image.open(os.path.join(defaultpath, 'media/ArrowRIght.scale-200.png'));

        menusize = menuimg.size;

        total_width = sum([textsize[0], menusize[0]]);

        nofocusimg = Image.new('RGBA', (total_width, menusize[1]), (255, 0, 0, 0));
        focusimg = Image.new('RGBA', (total_width, menusize[1]), (255, 0, 0, 0));

        nofocusimg.paste(textimg, (0, 0));
        nofocusimg.paste(menuimg, (textimg.size[0], 0));

        textimg = Image.new("RGB", textsize, (219, 219, 219));
        textdraw = ImageDraw.Draw(textimg);
        textdraw.text((0, -2), text, (150, 39, 171), menufont26);

        focusimg.paste(textimg, (0, 0));
        focusimg.paste(menuimg, (textimg.size[0], 0));

        focusimg.filter(ImageFilter.SHARPEN);
        nofocusimg.filter(ImageFilter.SHARPEN);

        #logger.debug(defaultpath);
        logger.debug(media_buttons);

        fileexists = False;

        mBtn1 = os.path.join(media_buttons, 'gl-button-%s-focus.png' % idx);
        mBtn2 = os.path.join(media_buttons, 'gl-button-%s-no-focus.png' % idx);

        if filecheck:

            file1 = os.path.isfile(mBtn1);
            file2 = os.path.isfile(mBtn2);

            if file1 and file2:
                fileexists = True;


        if fileexists is False:
            focusimg.save(mBtn1, 'PNG', optimize=1);
            nofocusimg.save(mBtn2, 'PNG', optimize=1);
            
        #focusimg.save(os.path.join(defaultpath, 'media', 'gl-button-%s-focus.png' % idx), 'PNG', optimize=1);
        #nofocusimg.save(os.path.join(defaultpath, 'media', 'gl-button-%s-no-focus.png' % idx), 'PNG', optimize=1);


        return int(focusimg.size[0] / 2);


    except Exception as inst:
        logger.error(inst);

        return None;


def text2Title(titles, directory, imgname):

        import textwrap;

        from PIL import Image;
        from PIL import ImageFont;
        from PIL import ImageDraw;
        from PIL import ImageFilter;

        try:

            defaultpath = os.path.join(getAddonInfo('path'), 'resources/skins/default');

            menufont33 = ImageFont.truetype(os.path.join(defaultpath, 'fonts/OpenSans-ExtraBold.ttf'), 33);
            menufont28 = ImageFont.truetype(os.path.join(defaultpath, 'fonts/OpenSans-Semibold.ttf'), 28);

            imgs = list();

            for idx, text in enumerate(titles):

                if idx < 1:

                    lines = textwrap.wrap(text, width=40);

                    for line in lines:

                        textsize = menufont33.getsize(line);

                        imgs.append([line, menufont33, textsize]);

                else:

                    textsize = menufont28.getsize(line);

                    imgs.append([text, menufont28, textsize]);

            ih = 0;

            if len(imgs) < 2:
                imgs.insert(0, [' ', imgs[0][1], imgs[0][2]])

            for img in imgs:
                ih += int(img[2][1] * .8);

            title_img = Image.new('RGBA', (660, ih), (255, 0, 0, 0));
            title_draw = ImageDraw.Draw(title_img);

            ih = -5;

            for idx, img in enumerate(imgs, 0):
                
                #title_img.paste(img, (0, ih));

                title_draw.text((5, ih), img[0], (255, 255, 255), img[1]);

                ih += int(img[2][1] * .8);


            imgname = os.path.join(directory, imgname);

            title_img.filter(ImageFilter.SHARPEN);
            title_img.save(imgname, 'PNG', optimize=1);

            return imgname;

        except Exception as inst:
            logger.error(inst);


        return None;


def text2Select(text, type, bgcolor, txtcolor, fontsize, font, filename, multiplier=1, sharpen=False, bgimage=None):

    from PIL import Image;
    from PIL import ImageFont;
    from PIL import ImageDraw;
    from PIL import ImageFilter;


    #savepath = xbmc.translatePath(os.path.join('special://userdata/addon_data', getAddonInfo('id')));
    defaultpath = os.path.join(getAddonInfo('path'), 'resources/skins/default');
    font = ImageFont.truetype(os.path.join(defaultpath, 'fonts/OpenSans-%s.ttf' % font), fontsize);

    textimg = Image.new(type, (1, 1));
    textdraw = ImageDraw.Draw(textimg);
    textsize = font.getsize(text);

    if bgcolor:

        textimg = Image.new(type, (textsize[0] * multiplier, textsize[1] * multiplier), bgcolor);
        textdraw = ImageDraw.Draw(textimg);

        textdraw.text((0, 0), text, txtcolor, font);

    else:

        textimg = Image.open(os.path.join(defaultpath, 'media/%s' % bgimage));
        textdraw = ImageDraw.Draw(textimg);

        imgsize = textimg.size;

        #textdraw.text((int(((imgsize[0] - textsize[0]) / 2)), int(((imgsize[1] - textsize[1]) / 2))), text, txtcolor, font);
        textdraw.text((20, 18), text, txtcolor, font);
    

    if sharpen:
        textimg.filter(ImageFilter.SHARPEN);


    textimg.save(filename, 'PNG', optimize=True);

    while not os.path.isfile(filename):
        logger.debug(filename)
        logger.debug('FILE NOT READY SLEEPING')
        xbmc.sleep(200);
    #textimg.save(os.path.join(defaultpath, 'media', '%s.jpg' % filename), "JPEG", quality=100);#, optimize=True, progressive=True)

    return textimg.size;


def checkDirectory(savepath):

    if not os.path.exists(savepath):
        os.makedirs(savepath)


def sendNotification(msg, time):

    addonname = getAddonInfo('name');
    icon = getAddonInfo('icon');
     
    if not isinstance(msg, basestring):
        msg = lang(msg).encode('utf-8');
     
    xbmc.executebuiltin('Notification(%s, %s, %d, %s)'%(addonname, msg, time, icon));


def setSettings(results):

    try:

        parameters = results['authentication']['parameters'];
        headers = parameters['header'];

        keys = ['territory'];

        for k, v in headers.items():

            if k != 'Authorization':
                setting(('fn.%s' % k), str(headers.get(k, '')));

                keys.append(k);


        keys = filter(lambda a: a != 'territory', keys)

        setting('fn.territory', str(parameters.get('territory', '')));
        setting('fn.Headers', str(','.join(keys)));


        return True;

    except Exception as inst:

        resetSettings();
        
        logger.error(inst);

        return False;


def resetSettings():

    try:
        
        for hdr in setting('fn.Headers').split(','):
            setting(('fn.%s' % hdr), '');

        setting('fn.territory', '');

        
    except Exception as inst:
        logger.error(inst);

        pass;


def parseValue(item, paths, encoded=True, func=None):

    value = item;

    try:

        for path in paths:
            value = value[path];

        if func:
            value = globals()[func[0]](value, func);

        if encoded and value is not None:
            value = iencode('ascii', value);


    except Exception as inst:
        #logger.error(paths);
        #logger.error(inst);

        value = None;

        pass;


    return value;


def parseRegion(regions, func):

    rating = None;

    try:

        if not isinstance(regions, list):
            regions = list([regions]);

    except:
        pass;

    for region in regions:

        try:

            cregion = region[func[1]];
            rating = region['#text'] if cregion == func[2] else None;

            if rating is not None:
                break;

        except:
            pass;


    return rating;


def parseAlternateImg(alternate, func):
    #utils.parseValue(item, ['item', 'ratings', 'tv'], True, ['parseAlternateImg', '@platforms', 'xbox360']),

    altImg = None;

    try:

        if not isinstance(alternate, list):
            alternate = list([alternate]);

    except:
        pass;

    for alt in alternate:

        try:

            platform = alt[func[1]];
            altImg = alt['#text'] if platform == func[2] else None;

            if altImg is not None:
                break;

        except:
            pass;


    return altImg;


def parseProgress(position, duration):

    progress = 0;

    if position and duration:

        try:

            progress = int(round(((float(position) / abs(float(duration))) * 100.00), 4));

        except:
            progress = 0;


    return progress;


def parseBtnText(text, slookup):

    try:
        
        button = ' %s   ' % text if text is not None else lang(slookup).encode('utf-8');

        return button;

    except:
        return None;


def iencode(etype, text):

    if text is not None:
        return str(text.encode(etype, 'ignore'));

    else:
        return None;


def roundQuarter(rating):

    try:
        
        return (round(float(rating) * 4) / 4.0);

    except:
        return '0.0';


def setDate(current, count=25):

    import datetime;
    from dateutil.relativedelta import relativedelta;

    date = None;

    if current:

        date = datetime.datetime.now();
        date = str(date);

    else:

        date = datetime.datetime.now() + relativedelta(days =+ 1);
        date = str(date);


    return date;


def dateExpired(date):

    import datetime;
    from dateutil import parser;

    if date is not None:

        try:

            present = datetime.datetime.now();
            edate = parser.parse(date.encode('utf-8'));
                
            if present >= edate:
                return True;

            else:
                return False;

        except Exception as inst:
            logger.error(inst);

            pass;

        return True;

    else:
        return True;


def requestContinueProgress(progress):

    if progress > 0:

        import xbmcgui;
        import datetime;
        
        progresstext = str(datetime.timedelta(seconds=progress));

        pboptions = ['Resume from %s' % progresstext, 'Start from beginning'];

        dialog = xbmcgui.Dialog();

        try:
            continueplayback = dialog.contextmenu(pboptions)

        except:
            continueplayback = dialog.select('Playback Options', pboptions);


        return continueplayback;


def resolutionPicker(videourl):

    #We need to add a settings check to this later so the user can set bandwidth by default

    #requests is throwing SSL/TLS errors.  Not causing any trouble, but not guareented to work in the furture
    #import requests;
    import urllib2;

    newurl = None;

    try:

        #resolutions = requests.get(videourl);

        logger.debug(videourl);
        resolutions = urllib2.urlopen(videourl).read();

        #if int(resolutions.status_code) == 200:
        if resolutions:

            formats = re.compile(r'(?P<bandwidth>BANDWIDTH=\d+),.+,RESOLUTION=(?P<resolution>\d+x\d+)[\r\n].+(?P<extension>_Layer\d+)\.m3u8', re.I);

            pboptions = ['Best Resolution'];

            #for match in formats.finditer(resolutions.content):
            for match in formats.finditer(resolutions):
                
                gDict = match.groupdict()

                pboptions.append('%s - (%s)' % (gDict['bandwidth'], gDict['resolution']));


            if len(pboptions) > 1:

                vidQuality = setting('fn.video_quality');

                logger.debug('VIDQUALITY %s' % vidQuality);
                logger.debug('PBOPTIONS LENGTH %s' % len(pboptions));
                logger.debug('PBOPTIONS %s' % pboptions);

                if vidQuality is None or int(vidQuality) >= len(pboptions):
                    newurl = videourl;

                elif vidQuality is not None and int(vidQuality) < len(pboptions) and int(vidQuality) > 0:
                    newurl = re.sub(r'\.m3u8', ('_Layer%s.m3u8' % vidQuality), videourl);

                else:

                    import xbmcgui;

                    dialog = xbmcgui.Dialog();

                    try:
                        resolutionoption = dialog.contextmenu(pboptions);

                    except:
                        resolutionoption = dialog.select('Resolution Options', pboptions);


                    if resolutionoption >= 1:
                        newurl = re.sub(r'\.m3u8', ('_Layer%s.m3u8' % resolutionoption), videourl);

                    elif resolutionoption == 0:
                        newurl = videourl;

                    else:
                        newurl = None;

                logger.error('NEWURL %s' % newurl)

            else:
                newurl = videourl;

        else:
            newurl = videourl;


    except Exception as inst:
        newurl = videourl;
        logger.error('WE HAVE AN EXCEPTION')
        
        logger.error(inst);

        pass;
        


    return newurl;


def runDirectoryChecks(mbtn):

    #dsPath = xbmc.translatePath(os.path.join('special://userdata/addon_data', getAddonInfo('id')));
    dsPath = xbmc.translatePath(addonInfo('profile'));
    media_buttons = os.path.join(dsPath, mbtn);

    checkDirectory(media_buttons);

    return media_buttons;



def openBrowser(url):

    try:

        import webbrowser;
            

        osWin = xbmc.getCondVisibility('system.platform.windows');
        osOsx = xbmc.getCondVisibility('system.platform.osx');
        osLinux = xbmc.getCondVisibility('system.platform.linux');
        osAndroid = xbmc.getCondVisibility('System.Platform.Android');


        if osOsx:    
            
            try:
                webbrowser.open(url, new=0, autoraise=True);
                
            except:
                xbmc.executebuiltin("System.Exec(open '%s')" % url);

        elif osWin:
            
            try:
                webbrowser.open(url, new=0, autoraise=True);
                
            except:
                xbmc.executebuiltin("System.Exec(cmd.exe /c start '%s')" % url);

        elif osLinux and not osAndroid:
            
            try:
                webbrowser.open(url, new=0, autoraise=True);
                
            except:
                xbmc.executebuiltin("System.Exec(xdg-open '%s')" % url);
            
        elif osAndroid:
            
            xbmc.executebuiltin("StartAndroidActivity(com.android.chrome,,,%s)" % url);

    except:
        pass;