# *  This Program is free software; you can redistribute it and/or modify
# *  it under the terms of the GNU General Public License as published by
# *  the Free Software Foundation; either version 2, or (at your option)
# *  any later version.
# *
# *  This Program is distributed in the hope that it will be useful,
# *  but WITHOUT ANY WARRANTY; without even the implied warranty of
# *  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# *  GNU General Public License for more details.
# *
# *  You should have received a copy of the GNU General Public License
# *  along with Kodi; see the file COPYING.  If not, write to
# *  the Free Software Foundation, 675 Mass Ave, Cambridge, MA 02139, USA.
# *  http://www.gnu.org/copyleft/gpl.html

import random, copy, threading
import xbmcgui, xbmcaddon
import EXIFvfs
from iptcinfovfs import IPTCInfo
from XMPvfs import XMP_Tags
from xml.dom.minidom import parse
from utils import *
import json

ADDON    = sys.modules[ '__main__' ].ADDON
ADDONID  = sys.modules[ '__main__' ].ADDONID
CWD      = sys.modules[ '__main__' ].CWD
SKINDIR  = xbmc.getSkinDir().decode('utf-8')

# images types that can contain exif/iptc data
EXIF_TYPES  = ('.jpg', '.jpeg', '.tif', '.tiff')

# random effect list to choose from
EFFECTLIST = ["('conditional', 'effect=zoom start=100 end=400 center=auto time=%i condition=true'),",
              "('conditional', 'effect=slide start=1280,0 end=-1280,0 time=%i condition=true'), ('conditional', 'effect=zoom start=%i end=%i center=auto time=%i condition=true')",
              "('conditional', 'effect=slide start=-1280,0 end=1280,0 time=%i condition=true'), ('conditional', 'effect=zoom start=%i end=%i center=auto time=%i condition=true')",
              "('conditional', 'effect=slide start=0,720 end=0,-720 time=%i condition=true'), ('conditional', 'effect=zoom start=%i end=%i center=auto time=%i condition=true')",
              "('conditional', 'effect=slide start=0,-720 end=0,720 time=%i condition=true'), ('conditional', 'effect=zoom start=%i end=%i center=auto time=%i condition=true')",
              "('conditional', 'effect=slide start=1280,720 end=-1280,-720 time=%i condition=true'), ('conditional', 'effect=zoom start=%i end=%i center=auto time=%i condition=true')",
              "('conditional', 'effect=slide start=-1280,720 end=1280,-720 time=%i condition=true'), ('conditional', 'effect=zoom start=%i end=%i center=auto time=%i condition=true')",
              "('conditional', 'effect=slide start=1280,-720 end=-1280,720 time=%i condition=true'), ('conditional', 'effect=zoom start=%i end=%i center=auto time=%i condition=true')",
              "('conditional', 'effect=slide start=-1280,-720 end=1280,720 time=%i condition=true'), ('conditional', 'effect=zoom start=%i end=%i center=auto time=%i condition=true')"]

# get local dateformat to localize the exif date tag
DATEFORMAT = xbmc.getRegion('dateshort')

class Screensaver(xbmcgui.WindowXMLDialog):
    def __init__( self, *args, **kwargs ):
        pass

    def onInit(self):
        # load constants
        self._get_vars()
        # get addon settings
        self._get_settings()
        # get the effectslowdown value from the current skin
        effectslowdown = self._get_animspeed()
        # use default if we couldn't find the effectslowdown value
        if not effectslowdown:
            effectslowdown = 1
        # calculate the animation time
        speedup = 1 / float(effectslowdown)
        self.adj_time = int(101000 * speedup)
        # get the images
        self._get_items()
        if self.slideshow_type == '2' and self.slideshow_random == 'false' and self.slideshow_resume == 'true':
            self._get_offset()
        if self.items:
            # hide startup splash
            self._set_prop('Splash', 'hide')
            # start slideshow
            self._start_show(copy.deepcopy(self.items))

    def _get_vars(self):
        # get the screensaver window id
        self.winid    = xbmcgui.Window(xbmcgui.getCurrentWindowDialogId())
        # init the monitor class to catch onscreensaverdeactivated calls
        self.Monitor  = MyMonitor(action = self._exit)
        self.stop     = False
        self.startup  = True
        self.offset   = 0

    def _get_settings(self):
        # read addon settings
        self.slideshow_type   = ADDON.getSetting('type')
        self.slideshow_path   = ADDON.getSetting('path')
        self.slideshow_effect = ADDON.getSetting('effect')
        self.slideshow_time   = int(ADDON.getSetting('time'))
        # convert float to hex value usable by the skin
        self.slideshow_dim    = hex(int('%.0f' % (float(100 - int(ADDON.getSetting('level'))) * 2.55)))[2:] + 'ffffff'
        self.slideshow_random = ADDON.getSetting('random')
        self.slideshow_resume = ADDON.getSetting('resume')
        self.slideshow_scale  = ADDON.getSetting('scale')
        self.slideshow_name   = ADDON.getSetting('label')
        self.slideshow_date   = ADDON.getSetting('date')
        self.slideshow_iptc   = ADDON.getSetting('iptc')
        self.slideshow_music  = ADDON.getSetting('music')
        self.slideshow_bg     = ADDON.getSetting('background')
        # select which image controls from the xml we are going to use
        if self.slideshow_scale == 'false':
            self.image1 = self.getControl(1)
            self.image2 = self.getControl(2)
            self.getControl(3).setVisible(False)
            self.getControl(4).setVisible(False)
            if self.slideshow_bg == 'true':
                self.image3 = self.getControl(5)
                self.image4 = self.getControl(6)
        else:
            self.image1 = self.getControl(3)
            self.image2 = self.getControl(4)
            self.getControl(1).setVisible(False)
            self.getControl(2).setVisible(False)
            self.getControl(5).setVisible(False)
            self.getControl(6).setVisible(False)
        if self.slideshow_name == '0':
            self.getControl(99).setVisible(False)
        else:
            self.namelabel = self.getControl(99)
        self.datelabel = self.getControl(100)
        self.textbox = self.getControl(101)
        # set the dim property
        self._set_prop('Dim', self.slideshow_dim)
        # show music info during slideshow if enabled
        if self.slideshow_music == 'true':
            self._set_prop('Music', 'show')
        # show background if enabled
        if self.slideshow_bg == 'true':
            self._set_prop('Background', 'show')

    def _start_show(self, items):
        # we need to start the update thread after the deep copy of self.items finishes
        thread = img_update(data=self._get_items)
        thread.start()
        # start with image 1
        cur_img = self.image1
        order = [1,2]
        # loop until onScreensaverDeactivated is called
        while (not self.Monitor.abortRequested()) and (not self.stop):
            # keep track of image position, needed to save the offset
            self.position = self.offset
            # iterate through all the images
            for img in items[self.offset:]:
                # cache file may be outdated
                if self.slideshow_type == '2' and not xbmcvfs.exists(img[0]):
                    continue
                # add image to gui
                cur_img.setImage(img[0],False)
                # add background image to gui
                if self.slideshow_scale == 'false' and self.slideshow_bg == 'true':
                    if order[0] == 1:
                        self.image3.setImage(img[0],False)
                    else:
                        self.image4.setImage(img[0],False)
                # give xbmc some time to load the image
                if not self.startup:
                    xbmc.sleep(1000)
                else:
                    self.startup = False
                # get exif and iptc tags if enabled in settings and we have an image that can contain this data
                datetime = ''
                title = ''
                description = ''
                keywords = ''
                exif = False
                iptc_ti = False
                iptc_de = False
                iptc_ke = False
                if self.slideshow_type == '2' and ((self.slideshow_date == 'true') or (self.slideshow_iptc == 'true')) and (os.path.splitext(img[0])[1].lower() in EXIF_TYPES):
                    imgfile = xbmcvfs.File(img[0])
                    # get exif date
                    if self.slideshow_date == 'true':
                        try:
                            exiftags = EXIFvfs.process_file(imgfile, details=False, stop_tag='DateTimeOriginal')
                            if exiftags.has_key('EXIF DateTimeOriginal'):
                                datetime = str(exiftags['EXIF DateTimeOriginal']).decode('utf-8')
                                # sometimes exif date returns useless data, probably no date set on camera
                                if datetime == '0000:00:00 00:00:00':
                                    datetime = ''
                                else:
                                    try:
                                        # localize the date format
                                        date = datetime[:10].split(':')
                                        time = datetime[10:]
                                        if DATEFORMAT[1] == 'm':
                                            datetime = date[1] + '-' + date[2] + '-' + date[0] + '  ' + time
                                        elif DATEFORMAT[1] == 'd':
                                            datetime = date[2] + '-' + date[1] + '-' + date[0] + '  ' + time
                                        else:
                                            datetime = date[0] + '-' + date[1] + '-' + date[2] + '  ' + time
                                    except:
                                        pass
                                    exif = True
                        except:
                            pass
                    # get iptc title, description and keywords
                    if self.slideshow_iptc == 'true':
                        try:
                            iptc = IPTCInfo(imgfile)
                            iptctags = iptc.data
                            if iptctags.has_key(105):
                                title = iptctags[105].decode('utf-8')
                                iptc_ti = True
                            if iptctags.has_key(120):
                                description = iptctags[120].decode('utf-8')
                                iptc_de = True
                            if iptctags.has_key(25):
                                keywords = ', '.join(iptctags[25]).decode('utf-8')
                                iptc_ke = True
                        except:
                            pass
                        if (not iptc_ti or not iptc_de or not iptc_ke):
                            try:
                                tags = XMP_Tags().get_xmp(img[0]) # passing the imgfile object does not work for some reason
                                if (not iptc_ti) and tags.has_key('dc:title'):
                                    title = tags['dc:title']
                                    iptc_ti = True
                                if (not iptc_de) and tags.has_key('dc:description'):
                                    description = tags['dc:description']
                                    iptc_de = True
                                if (not iptc_ke) and tags.has_key('dc:subject'):
                                    keywords = tags['dc:subject'].replace('||',', ')
                                    iptc_ke = True
                            except:
                                pass
                    imgfile.close()
                # display exif date if we have one
                if exif:
                    self.datelabel.setLabel('[I]' + datetime + '[/I]')
                    self.datelabel.setVisible(True)
                else:
                    self.datelabel.setVisible(False)
                # display iptc data if we have any
                if iptc_ti or iptc_de or iptc_ke:
                    self.textbox.setText(
                        '[CR]'.join([title, keywords] if title == description
                                    else [title, description, keywords]))
                    self.textbox.setVisible(True)
                else:
                    self.textbox.setVisible(False)
                # get the file or foldername if enabled in settings
                if self.slideshow_name != '0':
                    if self.slideshow_name == '1':
                        if self.slideshow_type == '2':
                            NAME, EXT = os.path.splitext(os.path.basename(img[0]))
                        else:
                            NAME = img[1]
                    elif self.slideshow_name == '2':
                        ROOT, NAME = os.path.split(os.path.dirname(img[0]))
                    elif self.slideshow_name == '3':
                        if self.slideshow_type == '2':
                            ROOT, FOLDER = os.path.split(os.path.dirname(img[0]))
                            FILE, EXT = os.path.splitext(os.path.basename(img[0]))
                            NAME = FOLDER + ' / ' + FILE
                        else:
                            ROOT, FOLDER = os.path.split(os.path.dirname(img[0]))
                            NAME = FOLDER + ' / ' + img[1]
                    self.namelabel.setLabel(NAME)
                # set animations
                if self.slideshow_effect == '0':
                    # add slide anim
                    self._set_prop('Slide%d' % order[0], '0')
                    self._set_prop('Slide%d' % order[1], '1')
                else:
                    # add random slide/zoom anim
                    if self.slideshow_effect == '2':
                        # add random slide/zoom anim
                        self._anim(cur_img)
                    # add fade anim, used for both fade and slide/zoom anim
                    self._set_prop('Fade%d' % order[0], '0')
                    self._set_prop('Fade%d' % order[1], '1')
                # add fade anim to background images
                if self.slideshow_bg == 'true':
                    self._set_prop('Fade1%d' % order[0], '0')
                    self._set_prop('Fade1%d' % order[1], '1')
                # define next image
                if cur_img == self.image1:
                    cur_img = self.image2
                    order = [2,1]
                else:
                    cur_img = self.image1
                    order = [1,2]
                # slideshow time in secs (we already slept for 1 second)
                count = self.slideshow_time - 1
                # display the image for the specified amount of time
                while (not self.Monitor.abortRequested()) and (not self.stop) and count > 0:
                    count -= 1
                    xbmc.sleep(1000)
                # break out of the for loop if onScreensaverDeactivated is called
                if  self.stop or self.Monitor.abortRequested():
                    break
                self.position += 1
            self.offset = 0
            items = copy.deepcopy(self.items)

    def _get_items(self, update=False):
        self.slideshow_type   = ADDON.getSetting('type')
        log('slideshow type: %s' % self.slideshow_type)
	    # check if we have an image folder, else fallback to video fanart
        if self.slideshow_type == '2':
            hexfile = checksum(self.slideshow_path) # check if path has changed, so we can create a new cache at startup
            log('image path: %s' % self.slideshow_path)
            log('update: %s' % update)
            if (not xbmcvfs.exists(CACHEFILE % hexfile)) or update: # create a new cache if no cache exits or during the background scan
                log('create cache')
                create_cache(self.slideshow_path, hexfile)
            self.items = self._read_cache(hexfile)
            log('items: %s' % len(self.items))
            if not self.items:
                self.slideshow_type = '0'
                # delete empty cache file
                if xbmcvfs.exists(CACHEFILE % hexfile):
                    xbmcvfs.delete(CACHEFILE % hexfile)
	    # video fanart
        if self.slideshow_type == '0':
            methods = [('VideoLibrary.GetMovies', 'movies'), ('VideoLibrary.GetTVShows', 'tvshows')]
	    # music fanart
        elif self.slideshow_type == '1':
            methods = [('AudioLibrary.GetArtists', 'artists')]
        # query the db
        if not self.slideshow_type == '2':
            self.items = []
            for method in methods:
                json_query = xbmc.executeJSONRPC('{"jsonrpc": "2.0", "method": "' + method[0] + '", "params": {"properties": ["fanart"]}, "id": 1}')
                json_query = unicode(json_query, 'utf-8', errors='ignore')
                json_response = json.loads(json_query)
                if json_response.has_key('result') and json_response['result'] != None and json_response['result'].has_key(method[1]):
                    for item in json_response['result'][method[1]]:
                        if item['fanart']:
                            self.items.append([item['fanart'], item['label']])
        # randomize
        if self.slideshow_random == 'true':
            random.seed()
            random.shuffle(self.items, random.random)

    def _get_offset(self):
        try:
            offset = xbmcvfs.File(RESUMEFILE)
            self.offset = int(offset.read())
            offset.close()
        except:
            self.offset = 0

    def _save_offset(self):
        if not xbmcvfs.exists(CACHEFOLDER):
            xbmcvfs.mkdir(CACHEFOLDER)
        try:
            offset = xbmcvfs.File(RESUMEFILE, 'w')
            offset.write(str(self.position))
            offset.close()
        except:
            log('failed to save resume point')

    def _read_cache(self, hexfile):
        images = ''
        try:
            cache = xbmcvfs.File(CACHEFILE % hexfile)
            images = eval(cache.read())
            cache.close()
        except:
            pass
        return images

    def _anim(self, cur_img):
        # reset position the current image
        cur_img.setPosition(0, 0)
        # pick a random anim
        number = random.randint(0,8)
        posx = 0
        posy = 0
        # add 1 sec fadeout time to showtime
        anim_time = self.slideshow_time + 1
        # set zoom level depending on the anim time
        zoom = 110 + anim_time
        if number == 1 or number == 5 or number == 7:
            posx = int(-1280 + (12.8 * anim_time) + 0.5)
        elif number == 2 or number == 6 or number == 8:
            posx = int(1280 - (12.8 * anim_time) + 0.5)
        if number == 3 or number == 5 or number == 6:
            posy = int(-720 + (7.2 * anim_time) + 0.5)
        elif number == 4 or number == 7 or number == 8:
            posy = int(720 - (7.2 * anim_time) + 0.5)
        # position the current image
        cur_img.setPosition(posx, posy)
        # add the animation to the current image
        if number == 0:
            cur_img.setAnimations(eval(EFFECTLIST[number] % (self.adj_time)))
        else:
            cur_img.setAnimations(eval(EFFECTLIST[number] % (self.adj_time, zoom, zoom, self.adj_time)))

    def _get_animspeed(self):
        # find the skindir
        json_query = xbmc.executeJSONRPC('{"jsonrpc": "2.0", "method": "Addons.GetAddonDetails", "params": {"addonid": "%s", "properties": ["path", "extrainfo"]}, "id": 1}' % SKINDIR)
        json_query = unicode(json_query, 'utf-8', errors='ignore')
        json_response = json.loads(json_query)
        if json_response.has_key('result') and (json_response['result'] != None) and json_response['result'].has_key('addon') and json_response['result']['addon'].has_key('path'):
            skinpath = json_response['result']['addon']['path']
        skinxml = xbmc.translatePath( os.path.join( skinpath, 'addon.xml' ).encode('utf-8') ).decode('utf-8')
        try:
            # parse the skin addon.xml
            self.xml = parse(skinxml)
            # find all extension tags
            tags = self.xml.documentElement.getElementsByTagName( 'extension' )
            for tag in tags:
                # find the effectslowdown attribute
                for (name, value) in tag.attributes.items():
                    if name == 'effectslowdown':
                        anim = value
                        return anim
        except:
            return

    def _set_prop(self, name, value):
        self.winid.setProperty('SlideView.%s' % name, value)

    def _clear_prop(self, name):
        self.winid.clearProperty('SlideView.%s' % name)

    def _exit(self):
        # exit when onScreensaverDeactivated gets called
        self.stop = True
        # clear our properties on exit
        self._clear_prop('Slide1')
        self._clear_prop('Slide2')
        self._clear_prop('Fade1')
        self._clear_prop('Fade2')
        self._clear_prop('Fade11')
        self._clear_prop('Fade12')
        self._clear_prop('Dim')
        self._clear_prop('Music')
        self._clear_prop('Splash')
        self._clear_prop('Background')
        # save the current position  to file
        if self.slideshow_type == '2' and self.slideshow_random == 'false' and self.slideshow_resume == 'true':
            self._save_offset()
        self.close()


class img_update(threading.Thread):
    def __init__( self, *args, **kwargs ):
        self._get_items =  kwargs['data']
        threading.Thread.__init__(self)
        self.stop = False
        self.Monitor = MyMonitor(action = self._exit)

    def run(self):
        while (not self.Monitor.abortRequested()) and (not self.stop):
            # create a fresh index as quickly as possible after slidshow started
            self._get_items(True)
            count = 0
            while count != 3600: # check for new images every hour
                xbmc.sleep(1000)
                count += 1
                if self.Monitor.abortRequested() or self.stop:
                    return

    def _exit(self):
        # exit when onScreensaverDeactivated gets called
        self.stop = True

class MyMonitor(xbmc.Monitor):
    def __init__( self, *args, **kwargs ):
        self.action = kwargs['action']

    def onScreensaverDeactivated(self):
        self.action()
