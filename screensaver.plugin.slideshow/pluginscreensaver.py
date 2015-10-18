import sys, os, random, re
import xbmcaddon, xbmcgui, xbmc, xbmcvfs
import exifread
import tokenparser
import addonutil

#Most of the screensaver code was taken from the screensaver.xbmc.slideshow addon, so thanks for that go to the authors at Team XBMC

if 'xbmcplugin' in sys.modules:
    del(sys.modules["xbmcplugin"])
import fakexbmcplugin
fakexbmcplugin.reset()

__addon__    = xbmcaddon.Addon()
__addonid__  = __addon__.getAddonInfo('id')
LANG = __addon__.getLocalizedString

def log(txt):
    if isinstance (txt,str):
        txt = txt.decode("utf-8")
    message = u'%s: %s' % (__addonid__, txt)
    xbmc.log(msg=message.encode("utf-8"), level=xbmc.LOGNOTICE)

log('Version: ' + __addon__.getAddonInfo('version'))

def getPluginLibPath(plugin_path):
    sub = 'default.py'
    with open(os.path.join(plugin_path,'addon.xml'),'r') as f:
        xml = f.read()
        try:
            sub = re.search('library="([^"]*?)"',re.search('(?s)<extension[^>]*xbmc.python.pluginsource[^>].*?>',xml).group(0)).group(1)
        except AttributeError:
            pass
    lib = os.path.join(plugin_path,sub)
    if os.path.exists(lib): return lib
    return None

class MyMonitor(xbmc.Monitor):
    def __init__( self, *args, **kwargs ):
        self.action = kwargs['action']

    def onScreensaverDeactivated(self):
        self.action()

class Screensaver(xbmcgui.WindowXMLDialog):
    def __init__( self, *args, **kwargs ):
        pass

    def onInit(self):
        self.conts()
        items = None
        try:
            #xbmc.sleep(2000)
            #raise Exception('Test Exception')
            items = self.items()
            self.getControl(10).setVisible(False)
            self.show(items)
        except SystemExit:
            self.exit()
            log('SystemExit')
            return
        except:
            if self.stop or xbmc.abortRequested:
                self.exit()
                return
            import traceback
            traceback.print_exc()
            err = str(sys.exc_info()[1])
            self.setError(err)

    def onAction(self,action):
        self.exit()

    def setWinProperty(self,prop,val):
        xbmcgui.Window(self.winid).setProperty(prop, val)

    def setError(self,msg=''):
        self.setWinProperty('stop_animation','1')
        self.setWinProperty('loading_image','plugin-ss-screensaver-error.png')
        error = 'ERROR: %s' % msg
        self.getControl(101).setLabel(error)
        log(error)
        cont = self.getControl(10)
        self.setWinProperty('stop_animation','1')
        x = 608 ; y=328
        while (not xbmc.abortRequested) and (not self.stop):
            xbmc.sleep(1000)
            if xbmc.abortRequested or self.stop: break
            xbmc.sleep(1000)
            x = random.randint(16,1200)
            y = random.randint(16,440)
            cont.setPosition(x,y)

    def conts(self):
        self.winid = xbmcgui.getCurrentWindowDialogId()
        self.stop = False
        self.Monitor = MyMonitor(action = self.exit)
        self.image1 = self.getControl(1)
        self.image2 = self.getControl(2)
        self.preImage1 = self.getControl(3)
        self.preImage2 = self.getControl(4)
        self.title = self.getControl(200)
        self.slideshow_type = __addon__.getSetting('type')
        self.slideshow_path = __addon__.getSetting('path')
        self.slideshow_effect = __addon__.getSetting('effect')
        self.slideshow_random = __addon__.getSetting('randomize') == 'true'
        self.slideshow_caption = __addon__.getSetting('titles') == 'true'
        self.slideshow_advanced_caption = __addon__.getSetting('advanced_caption') == 'true'
        self.slideshow_caption_template = __addon__.getSetting('caption_template') or ''
        self.slideshow_time = (int('%02d' % int(__addon__.getSetting('time')))) * 1000
        self.slideshow_dim = hex(int('%.0f' % (float(__addon__.getSetting('level')) * 2.55)))[2:] + 'ffffff' # convert float to hex value usable by the skin

    def items(self):
        if self.slideshow_path.startswith('plugin://'):
            addonName = self.slideshow_path.split('://')[-1].split('/')[0]
            fakexbmcplugin.addonID = addonName
            fakexbmcplugin.WINID = self.winid
            localAddonsPath = os.path.join(xbmc.translatePath('special://home'),'addons')
            addonPath = os.path.join(localAddonsPath,addonName)
            libPath = getPluginLibPath(addonPath)
            if len(sys.argv) < 2:
                sys.argv.append(1)
            if len(sys.argv) < 3:
                sys.argv.append('test')
            if '?' in self.slideshow_path:
                args = '?' + self.slideshow_path.split('?',1)[-1] + '&plugin_slideshow_ss=true'
            else:
                args = '?plugin_slideshow_ss=true'
            sys.argv[0] = self.slideshow_path.split('?',1)[0]
            sys.argv[1] = 1
            sys.argv[2] = args
            #print sys.argv[2]
            from xbmcaddon import Addon
            class xbmcaddon_Addon_Wrapper():
                def __init__(self,id=addonName):
                    self.Addon = Addon(id)

                def __getattr__(self,name):
                    return getattr(self.Addon, name)

            xbmcaddon.Addon = xbmcaddon_Addon_Wrapper
            sys.path.insert(0,addonPath)

            try:
                #Add all the module paths to sys.path
                for p in addonutil.getAddonDependencyPaths(addonName):
                    if p in sys.path: continue
                    sys.path.insert(0,p)
            except:
                import traceback
                log(traceback.format_exc())

            glb = globals().copy() #make a copy of the current globals() so we can pass the expected stuff
            sys.modules['xbmcplugin'] = fakexbmcplugin
            sys.modules['xbmcaddon'] = xbmcaddon
            glb.update({'xbmcplugin':fakexbmcplugin,'xbmcaddon':xbmcaddon,'__name__':'__main__'}) #force __name__ and make sure xbmcplugin is ours
            execfile(libPath,glb)
            items = fakexbmcplugin.FINAL_ITEMS
            xbmcaddon.Addon = Addon
        else:
            try:
                import ShareSocial #@UnresolvedImport
                if not checkShareSocial(ShareSocial):
                    self.setError('ShareSocial: Version Too Old')
                    return []
            except:
                self.setError('ShareSocial Not Installed')
                return []
            user_target = self.slideshow_path.split('@',1)
            if len(user_target) > 1:
                uid, target = user_target
            else:
                uid = None
                target = user_target
            target = ShareSocial.ShareManager().getTarget(target)
            if not target: return []
            items = []
            shares = target.provide('imagestream',uid)
            if not shares: return []
            for s in shares:
                items.append({'url':s.media,'title':s.title})
        if self.slideshow_random: random.shuffle(items)
        return items

    def show(self, items):
        if not items: return
        log('Showing %s items' % len(items))
        # set window properties for the skin
        self.setWinProperty('SlideView.Dim', self.slideshow_dim)
        cur_img = self.image1
        next_img = self.image2
        cur_img.setImage(items[-1]['url'])
        while (not xbmc.abortRequested) and (not self.stop):
            ct = 0
            for item in items:
                self.preload(items, ct)
                img = item['url']
                if self.slideshow_effect == "2": cur_img.setImage(img)
                if self.slideshow_caption:
                    caption = item['title']
                    if self.slideshow_advanced_caption:
                        tokenParser = tokenparser.TitleTokenParser(item['title'].strip(),getEXIF(img))
                        caption = tokenParser.parse(self.slideshow_caption_template)
                    self.title.setLabel(caption)
                if cur_img == self.image1:
                    if self.slideshow_effect == "0":
                        self.setWinProperty('SlideView.Slide1', '0')
                        self.setWinProperty('SlideView.Slide2', '1')
                    else:
                        self.setWinProperty('SlideView.Fade1', '0')
                        if self.slideshow_effect == "2":
                            self.anim(self.winid, 1, 2, self.image1, self.image2, self.slideshow_time)
                    cur_img = self.image2
                    next_img = self.image1
                else:
                    if self.slideshow_effect == "0":
                        self.setWinProperty('SlideView.Slide2', '0')
                        self.setWinProperty('SlideView.Slide1', '1')
                    else:
                        self.setWinProperty('SlideView.Fade1', '1')
                        if self.slideshow_effect == "2":
                            self.anim(self.winid, 2, 1, self.image2, self.image1, self.slideshow_time)
                    cur_img = self.image1
                    next_img = self.image2
                if self.slideshow_effect != "2": next_img.setImage(img)
                count = int(self.slideshow_time / 1000)
                if self.slideshow_effect == "2":
                    count -= 1
                while (not xbmc.abortRequested) and (not self.stop) and count > 0:
                    count -= 1
                    xbmc.sleep(1000)
                if  self.stop or xbmc.abortRequested:
                    break
                ct+=1

    def preload(self,items,idx):
        if idx >= len(items) - 1: return
        self.preImage1.setImage(items[idx + 1]['url'])
        if idx >= len(items) - 2: return
        self.preImage2.setImage(items[idx + 2]['url'])

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
        prev_img.setPosition(-1280, -720)
        xbmcgui.Window(winid).setProperty('SlideView.Pan%i' % prev_prop, '0')
        xbmc.sleep(500)

    def exit(self):
        self.stop = True
        fakexbmcplugin.STOP = True
        self.close()

def checkShareSocial(ss):
    from distutils.version import StrictVersion
    if StrictVersion(ss.__version__) < StrictVersion('0.2.0'): return False
    return True

def chooseStream():
    try:
        import ShareSocial #@UnresolvedImport
        if not checkShareSocial(ShareSocial): raise Exception('ShareSocial: Version Too Old')
        idx = xbmcgui.Dialog().select('Choose Source',[LANG(32015),LANG(32016)])
    except:
        idx = 0
    if idx == None: return
    if idx == 0:
        path = xbmcgui.Dialog().browse(0,'Choose Plugin Path','files','',True,False,'addons://sources/image')
        if not path: return
        if path == 'addons://sources/image': return
        __addon__.setSetting('path',path)
    else:
        sm = ShareSocial.ShareManager()
        provider = sm.askForProvider('imagestream',overlay=True)
        if not provider: return
        __addon__.setSetting('path',provider.targetID())

def getEXIF(path):
    if xbmcvfs.exists(path):
        try:
            f = xbmcvfs.File(path) # @UndefinedVariable
            tags = exifread.process_file(f)
            f.close()
            return tags
        except:
            import traceback
            traceback.print_exc()
            return None
    else:
        return None

if __name__ == '__main__':
    if len(sys.argv) > 1 and sys.argv[1] == 'resetpath':
        __addon__.setSetting('path','addons://sources/image')
    elif len(sys.argv) > 1 and sys.argv[1] == 'choosestream':
        chooseStream()
    else:
        Screensaver('plugin-slideshow-screensaver.xml', __addon__.getAddonInfo('path'), 'default').doModal()
        del Screensaver
        del MyMonitor

