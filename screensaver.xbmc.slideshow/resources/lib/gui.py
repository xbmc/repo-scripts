import os, sys, random, urllib
import xbmc, xbmcgui, xbmcaddon, xbmcvfs
if sys.version_info < (2, 7):
    import simplejson
else:
    import json as simplejson

__addon__   = sys.modules[ "__main__" ].__addon__
__addonid__ = sys.modules[ "__main__" ].__addonid__
__cwd__     = sys.modules[ "__main__" ].__cwd__

IMAGE_TYPES = ('.png', '.jpg', '.jpeg', '.bmp', '.gif', '.ico', '.tif', '.tiff', '.tga', '.pcx')

def log(txt):
    if isinstance (txt,str):
        txt = txt.decode("utf-8")
    message = u'%s: %s' % (__addonid__, txt)
    xbmc.log(msg=message.encode("utf-8"), level=xbmc.LOGDEBUG)

class Screensaver(xbmcgui.WindowXMLDialog):
    def __init__( self, *args, **kwargs ):
        pass

    def onInit(self):
        self.conts()
        items = self.items()
        if items:
            self.show(items)

    def conts(self):
        self.winid = xbmcgui.getCurrentWindowDialogId()
        self.stop = False
        self.Monitor = MyMonitor(action = self.exit)
        self.image1 = self.getControl(1)
        self.image2 = self.getControl(2)
        self.slideshow_type = __addon__.getSetting('type')
        self.slideshow_path = __addon__.getSetting('path')
        self.slideshow_effect = __addon__.getSetting('effect')
        self.slideshow_time = (int('%02d' % int(__addon__.getSetting('time'))) + 1) * 1000
        self.slideshow_dim = hex(int('%.0f' % (float(__addon__.getSetting('level')) * 2.55)))[2:] + 'ffffff' # convert float to hex value usable by the skin

    def items(self):
	# image folder (fallback to video fanart in case ..)
        if self.slideshow_type == "2":
            if not self.slideshow_path:
                self.slideshow_type = "0"
	# video fanart
        if self.slideshow_type == "0":
            methods = [('VideoLibrary.GetMovies', 'movies'), ('VideoLibrary.GetTVShows', 'tvshows')]
	# music fanart
        elif self.slideshow_type == "1":
            methods = [('AudioLibrary.GetArtists', 'artists')]
        if self.slideshow_type == "2":
            items = self.walk(self.slideshow_path)
        else:
            items = []
            for method in methods:
                json_query = xbmc.executeJSONRPC('{"jsonrpc": "2.0", "method": "' + method[0] + '", "params": {"properties": ["fanart"]}, "id": 1}')
                json_query = unicode(json_query, 'utf-8', errors='ignore')
                json_response = simplejson.loads(json_query)
                if json_response.has_key('result') and json_response['result'] != None and json_response['result'].has_key(method[1]):
                    for item in json_response['result'][method[1]]:
                        if item['fanart']:
                            items.append(item['fanart'])
        # randomize
        random.shuffle(items, random.random)
        return items

    def show(self, items):
        # set window properties for the skin
        xbmcgui.Window(self.winid).setProperty('SlideView.Dim', self.slideshow_dim)
        cur_img = self.image1
        while (not xbmc.abortRequested) and (not self.stop):
            for img in items:
                cur_img.setImage(img)
                if cur_img == self.image1:
                    if self.slideshow_effect == "0":
                        xbmcgui.Window(self.winid).setProperty('SlideView.Slide1', '0')
                        xbmcgui.Window(self.winid).setProperty('SlideView.Slide2', '1')
                    else:
                        xbmcgui.Window(self.winid).setProperty('SlideView.Fade1', '0')
                        xbmcgui.Window(self.winid).setProperty('SlideView.Fade2', '1')
                        if self.slideshow_effect == "2":
                            self.anim(self.winid, 1, 2, self.image1, self.image2, self.slideshow_time)
                    cur_img = self.image2
                else:
                    if self.slideshow_effect == "0":
                        xbmcgui.Window(self.winid).setProperty('SlideView.Slide2', '0')
                        xbmcgui.Window(self.winid).setProperty('SlideView.Slide1', '1')
                    else:
                        xbmcgui.Window(self.winid).setProperty('SlideView.Fade2', '0')
                        xbmcgui.Window(self.winid).setProperty('SlideView.Fade1', '1')
                        if self.slideshow_effect == "2":
                            self.anim(self.winid, 2, 1, self.image2, self.image1, self.slideshow_time)
                    cur_img = self.image1
                count = int(self.slideshow_time / 1000)
                if self.slideshow_effect == "2":
                    count -= 1
                while (not xbmc.abortRequested) and (not self.stop) and count > 0:
                    count -= 1
                    xbmc.sleep(1000)
                if  self.stop or xbmc.abortRequested:
                    break

    def walk(self, path):
        images = []
        folders = []
        if path.startswith('multipath://'):
            paths = path[12:-1].split('/')
            for item in paths:
                folders.append(urllib.unquote_plus(item))
        else:
            folders.append(path)
        for folder in folders:
            if xbmcvfs.exists(xbmc.translatePath(folder)):
                dirs,files = xbmcvfs.listdir(folder)
                for item in files:
                    if os.path.splitext(item)[1].lower() in IMAGE_TYPES:
                        images.append(os.path.join(folder,item))
                for item in dirs:
                    images += self.walk(os.path.join(folder,item))
        return images

    def anim(self, winid, next_prop, prev_prop, next_img, prev_img, showtime):
        number = random.randint(1,9)
        posx = 0
        posy = 0
        # calculate posx and posy offset depending on the selected time per image (add 0.5 sec fadeout time)
        if number == 2 or number == 6 or number == 8:
            posx = int(-128 + (12.8 * ((showtime + 0.5) / 1000)))
        elif number == 3 or number == 7 or number == 9:
            posx = int(128 - (12.8 * ((showtime + 0.5) / 1000)))
        if number == 4 or number == 6 or number == 7:
            posy = int(-72 + (7.2 * ((showtime + 0.5) / 1000)))
        elif number == 5 or number == 8 or number == 9:
            posy = int(72 - (7.2 * ((showtime + 0.5) / 1000)))
        next_img.setPosition(posx, posy)
        xbmcgui.Window(winid).setProperty('SlideView.Pan%i' % next_prop, str(number))
        xbmc.sleep(500)
        prev_img.setPosition(0, 0)
        xbmcgui.Window(winid).setProperty('SlideView.Pan%i' % prev_prop, '0')
        xbmc.sleep(500)

    def exit(self):
        self.stop = True
        self.close()

class MyMonitor(xbmc.Monitor):
    def __init__( self, *args, **kwargs ):
        self.action = kwargs['action']

    def onScreensaverDeactivated(self):
        self.action()
