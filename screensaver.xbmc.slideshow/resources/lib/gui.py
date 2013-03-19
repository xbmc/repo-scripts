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
# *  along with XBMC; see the file COPYING.  If not, write to
# *  the Free Software Foundation, 675 Mass Ave, Cambridge, MA 02139, USA.
# *  http://www.gnu.org/copyleft/gpl.html

import random
import xbmcgui, xbmcaddon
import EXIFvfs
from iptcinfovfs import IPTCInfo
from xml.dom.minidom import parse
from utils import *
if sys.version_info < (2, 7):
    import simplejson
else:
    import json as simplejson

__addon__    = sys.modules[ "__main__" ].__addon__
__addonid__  = sys.modules[ "__main__" ].__addonid__
__cwd__      = sys.modules[ "__main__" ].__cwd__
__skindir__  = xbmc.getSkinDir().decode('utf-8')
__skinhome__ = xbmc.translatePath( os.path.join( 'special://home/addons/', __skindir__, 'addon.xml' ).encode('utf-8') ).decode('utf-8')
__skinxbmc__ = xbmc.translatePath( os.path.join( 'special://xbmc/addons/', __skindir__, 'addon.xml' ).encode('utf-8') ).decode('utf-8')

# images types that can contain exif/iptc data
EXIF_TYPES  = ('.jpg', '.jpeg', '.tif', '.tiff')

# random effect list to choose from
if xbmcaddon.Addon(id='xbmc.addon').getAddonInfo('version') == '12.0.0':
    EFFECTLIST = ["('effect=zoom start=100 end=400 center=auto time=%i condition=true', 'conditional'),",
                 "('effect=slide start=1280,0 end=-1280,0 time=%i condition=true', 'conditional'), ('effect=zoom start=%i end=%i center=auto time=%i condition=true', 'conditional')",
                 "('effect=slide start=-1280,0 end=1280,0 time=%i condition=true', 'conditional'), ('effect=zoom start=%i end=%i center=auto time=%i condition=true', 'conditional')",
                 "('effect=slide start=0,720 end=0,-720 time=%i condition=true', 'conditional'), ('effect=zoom start=%i end=%i center=auto time=%i condition=true', 'conditional')",
                 "('effect=slide start=0,-720 end=0,720 time=%i condition=true', 'conditional'), ('effect=zoom start=%i end=%i center=auto time=%i condition=true', 'conditional')",
                 "('effect=slide start=1280,720 end=-1280,-720 time=%i condition=true', 'conditional'), ('effect=zoom start=%i end=%i center=auto time=%i condition=true', 'conditional')",
                 "('effect=slide start=-1280,720 end=1280,-720 time=%i condition=true', 'conditional'), ('effect=zoom start=%i end=%i center=auto time=%i condition=true', 'conditional')",
                 "('effect=slide start=1280,-720 end=-1280,720 time=%i condition=true', 'conditional'), ('effect=zoom start=%i end=%i center=auto time=%i condition=true', 'conditional')",
                 "('effect=slide start=-1280,-720 end=1280,720 time=%i condition=true', 'conditional'), ('effect=zoom start=%i end=%i center=auto time=%i condition=true', 'conditional')"]
else:
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
        items = self._get_items()
        if items:
            # hide startup splash
            self._set_prop('Splash', 'hide')
            # start slideshow
            self._start_show(items)

    def _get_vars(self):
        # get the screensaver window id
        self.winid   = xbmcgui.Window(xbmcgui.getCurrentWindowDialogId())
        # init the monitor class to catch onscreensaverdeactivated calls
        self.Monitor = MyMonitor(action = self._exit)
        self.stop    = False
        self.startup = True

    def _get_settings(self):
        # read addon settings
        self.slideshow_type   = __addon__.getSetting('type')
        self.slideshow_path   = __addon__.getSetting('path')
        self.slideshow_effect = __addon__.getSetting('effect')
        self.slideshow_time   = int(__addon__.getSetting('time'))
        # convert float to hex value usable by the skin
        self.slideshow_dim    = hex(int('%.0f' % (float(__addon__.getSetting('level')) * 2.55)))[2:] + 'ffffff'
        self.slideshow_random = __addon__.getSetting('random')
        self.slideshow_scale  = __addon__.getSetting('scale')
        self.slideshow_name   = __addon__.getSetting('label')
        self.slideshow_date   = __addon__.getSetting('date')
        self.slideshow_iptc   = __addon__.getSetting('iptc')
        self.slideshow_music  = __addon__.getSetting('music')
        self.slideshow_cache  = __addon__.getSetting('cache')
        # select which image controls from the xml we are going to use
        if self.slideshow_scale == 'false':
            self.image1 = self.getControl(1)
            self.image2 = self.getControl(2)
            self.getControl(3).setVisible(False)
            self.getControl(4).setVisible(False)
        else:
            self.image1 = self.getControl(3)
            self.image2 = self.getControl(4)
            self.getControl(1).setVisible(False)
            self.getControl(2).setVisible(False)
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

    def _start_show(self, items):
        # start with image 1
        cur_img = self.image1
        order = [1,2]
        # loop until onScreensaverDeactivated is called
        while (not xbmc.abortRequested) and (not self.stop):
            # iterate through all the images
            for img in items:
                # add image to gui
                cur_img.setImage(img[0])
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
                iptc = False
                if ((self.slideshow_date == 'true') or (self.slideshow_iptc == 'true')) and (os.path.splitext(img[0])[1].lower() in EXIF_TYPES):
                    imgfile = xbmcvfs.File(img[0])
                    # get exif date
                    if self.slideshow_date == 'true':
                        try:
                            exiftags = EXIFvfs.process_file(imgfile, details=False, stop_tag="DateTimeOriginal")
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
                                        else:
                                            datetime = date[2] + '-' + date[1] + '-' + date[0] + '  ' + time
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
                                iptc = True
                            if iptctags.has_key(120):
                                description = iptctags[120].decode('utf-8')
                                iptc = True
                            if iptctags.has_key(25):
                                keywords = ', '.join(iptctags[25]).decode('utf-8')
                                iptc = True
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
                if iptc:
                    self.textbox.setText(title + '[CR]' + description + '[CR]' + keywords)
                    self.textbox.setVisible(True)
                else:
                    self.textbox.setVisible(False)
                # get the file or foldername if enabled in settings
                if self.slideshow_name != '0':
                    if self.slideshow_name == '1':
                        if self.slideshow_type == "2":
                            NAME, EXT = os.path.splitext(os.path.basename(img[0]))
                        else:
                            NAME = img[1]
                    elif self.slideshow_name == '2':
                        ROOT, NAME = os.path.split(os.path.dirname(img[0]))
                    self.namelabel.setLabel('[B]' + NAME + '[/B]')
                # set animations
                if self.slideshow_effect == "0":
                    # add slide anim
                    self._set_prop('Slide%d' % order[0], '0')
                    self._set_prop('Slide%d' % order[1], '1')
                else:
                    # add random slide/zoom anim
                    if self.slideshow_effect == "2":
                        # add random slide/zoom anim
                        self._anim(cur_img)
                    # add fade anim, used for both fade and slide/zoom anim
                    self._set_prop('Fade%d' % order[0], '0')
                    self._set_prop('Fade%d' % order[1], '1')
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
                while (not xbmc.abortRequested) and (not self.stop) and count > 0:
                    count -= 1
                    xbmc.sleep(1000)
                # break out of the for loop if onScreensaverDeactivated is called
                if  self.stop or xbmc.abortRequested:
                    break

    def _get_items(self):
	# check if we have an image folder, else fallback to video fanart
        if self.slideshow_type == "2":
            if self.slideshow_cache == 'true' and xbmcvfs.exists(CACHEFILE):
                items = self._read_cache()
            else:
                items = walk(self.slideshow_path)
            if not items:
                self.slideshow_type = "0"
	# video fanart
        if self.slideshow_type == "0":
            methods = [('VideoLibrary.GetMovies', 'movies'), ('VideoLibrary.GetTVShows', 'tvshows')]
	# music fanart
        elif self.slideshow_type == "1":
            methods = [('AudioLibrary.GetArtists', 'artists')]
        # query the db
        if not self.slideshow_type == "2":
            items = []
            for method in methods:
                json_query = xbmc.executeJSONRPC('{"jsonrpc": "2.0", "method": "' + method[0] + '", "params": {"properties": ["fanart"]}, "id": 1}')
                json_query = unicode(json_query, 'utf-8', errors='ignore')
                json_response = simplejson.loads(json_query)
                if json_response.has_key('result') and json_response['result'] != None and json_response['result'].has_key(method[1]):
                    for item in json_response['result'][method[1]]:
                        if item['fanart']:
                            items.append([item['fanart'], item['label']])
        # randomize
        if self.slideshow_random == 'true':
            random.shuffle(items, random.random)
        return items

    def _read_cache(self):
        images = ''
        try:
            cache = xbmcvfs.File(CACHEFILE)
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
        if xbmcvfs.exists( __skinxbmc__ ):
            # xbmc addon dir
            skinxml = __skinxbmc__
        elif xbmcvfs.exists( __skinhome__ ):
            # user addon dir
            skinxml = __skinhome__
        else:
            return
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
        self._clear_prop('Dim')
        self._clear_prop('Music')
        self._clear_prop('Splash')
        self.close()

class MyMonitor(xbmc.Monitor):
    def __init__( self, *args, **kwargs ):
        self.action = kwargs['action']

    def onScreensaverDeactivated(self):
        self.action()
