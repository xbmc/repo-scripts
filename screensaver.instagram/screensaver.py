#   Copyright (C) 2018 Lunatixz
#
#
# This file is part of Instagram ScreenSaver.
#
# Instagram ScreenSaver is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# Instagram ScreenSaver is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Instagram ScreenSaver.  If not, see <http://www.gnu.org/licenses/>.

#inspired by https://github.com/dersphere/script.screensaver.multi_slideshow
import random, sys, os, json
import xbmc, xbmcaddon, xbmcvfs
from xbmcgui import ControlImage, ControlLabel, WindowDialog

# Plugin Info
ADDON_ID       = 'screensaver.instagram'
REAL_SETTINGS  = xbmcaddon.Addon(id=ADDON_ID)
ADDON_NAME     = REAL_SETTINGS.getAddonInfo('name')
SETTINGS_LOC   = REAL_SETTINGS.getAddonInfo('profile')
ADDON_PATH     = REAL_SETTINGS.getAddonInfo('path').decode('utf-8')
ADDON_VERSION  = REAL_SETTINGS.getAddonInfo('version')
ICON           = REAL_SETTINGS.getAddonInfo('icon')
FANART         = REAL_SETTINGS.getAddonInfo('fanart')
LANGUAGE       = REAL_SETTINGS.getLocalizedString

# Globals
MODES          = ('TableDrop',
                  'AppleTVLike')
CHUNK_WAIT_TIME = 250
ACTION_IDS_EXIT = [9, 10, 13, 92]

class ScreensaverManager(object):
    def __new__(cls):
        mode = MODES[int(REAL_SETTINGS.getSetting('mode'))]
        for subcls in ScreensaverBase.__subclasses__():
            if subcls.MODE == mode: return subcls()
        raise ValueError('Not a valid ScreensaverBase subclass: %s' % mode)


class ExitMonitor(xbmc.Monitor):
    def __init__(self, exit_callback):
        self.exit_callback = exit_callback

        
    def onScreensaverDeactivated(self):
        self.exit_callback()


class ScreensaverWindow(WindowDialog):
    def __init__(self, exit_callback):
        self.exit_callback = exit_callback

        
    def onAction(self, action):
        action_id = action.getId()
        if action_id in ACTION_IDS_EXIT:
            self.exit_callback()


class ScreensaverBase(object):
    MODE = None
    IMAGE_CONTROL_COUNT = 10
    FAST_IMAGE_COUNT = 0
    NEXT_IMAGE_TIME = 2000

    def __init__(self):
        self.log('__init__ start')
        self.exit_requested = False
        self.background_control = None
        self.preload_control = None
        self.image_count = 0
        self.image_controls = []
        self.global_controls = []
        self.exit_monitor = ExitMonitor(self.stop)
        self.xbmc_window = ScreensaverWindow(self.stop)
        self.xbmc_window.show()
        self.init_global_controls()
        self.load_settings()
        self.init_cycle_controls()
        self.stack_cycle_controls()
        self.log('__init__ end')

        
    def init_global_controls(self):
        self.log('init_global_controls start')
        loading_img = xbmc.validatePath('/'.join((ADDON_PATH, 'resources', 'media', 'loading.gif')))
        logo_img = xbmc.validatePath('/'.join((ADDON_PATH, 'resources', 'media', 'logo.png')))
        self.loading_control = ControlImage(480, 250, 400, 219, loading_img)
        self.preload_control = ControlImage(-1, -1, 1, 1, '')
        self.background_control = ControlImage(0, 0, 1280, 720, '')
        self.logo_control = ControlImage(25, 625, 250, 65, logo_img)
        self.logo_label = ControlLabel(98, 680, 250, 25, '', textColor='FFFFFFFF')
        self.global_controls = [self.preload_control, self.background_control, self.loading_control, self.logo_control, self.logo_label]
        self.xbmc_window.addControls(self.global_controls)
        self.log('init_global_controls end')

        
    def init_cycle_controls(self):
        self.log('init_cycle_controls start')
        for i in xrange(self.IMAGE_CONTROL_COUNT):
            img_control = ControlImage(0, 0, 0, 0, '', aspectRatio=2)
            self.image_controls.append(img_control)
        self.log('init_cycle_controls end')

        
    def stack_cycle_controls(self):
        self.log('stack_cycle_controls start')
        # add controls to the window in same order as image_controls list
        # so any new image will be in front of all previous images
        self.xbmc_window.addControls(self.image_controls)
        self.log('stack_cycle_controls end')

        
    def start_loop(self):
        self.log('start_loop start')
        images = self.get_images()
        if REAL_SETTINGS.getSetting('random_order') == 'true': random.shuffle(images)
        image_url_cycle = cycle(images)
        image_controls_cycle = cycle(self.image_controls)
        self.hide_loading_indicator()
        image_url = image_url_cycle.next()
        while not self.exit_requested:
            self.log('using image: %s' % repr(image_url))
            image_control = image_controls_cycle.next()
            self.process_image(image_control, image_url)
            image_url = image_url_cycle.next()
            if self.image_count < self.FAST_IMAGE_COUNT: self.image_count += 1
            else:
                self.preload_image(image_url)
                self.wait()
        self.log('start_loop end')

        
    def get_images(self):
        self.log('get_images')
        count = 0
        self.image_aspect_ratio = 16.0 / 9.0
        self.background_image = '%d.jpg'%(random.randint(1,13))
        userlist = self.getTargets()
        user     = userlist[random.randint(0,len(userlist)-1)]
        filename = xbmc.translatePath(os.path.join(SETTINGS_LOC,'%s.json'%(user)))
        while not xbmcvfs.exists(filename) and count <= 10:
            count += 1
            try: 
                user     = userlist[random.randint(0,len(userlist)-1)]
                filename = xbmc.translatePath(os.path.join(SETTINGS_LOC,'%s.json'%(user)))
            except: pass
        if not xbmcvfs.exists(filename):
            self.stop()
            return []
        self.logo_label.setLabel(user)
        return list(self.prepareImages(filename))
        

    def prepareImages(self, filename):
        for img in json.load(xbmcvfs.File(filename)): yield img['image']
        

    def getTargets(self):
        userList = []
        for i in range(1,11): userList.append((REAL_SETTINGS.getSetting('USER%d'%i)))
        return filter(None, userList)
        
        
    def hide_loading_indicator(self):
        bg_img = xbmc.validatePath('/'.join((ADDON_PATH, 'resources', 'media', self.background_image)))
        self.loading_control.setAnimations([('conditional','effect=fade start=100 end=0 time=500 condition=true')])
        self.background_control.setAnimations([('conditional','effect=fade start=0 end=100 time=500 delay=500 condition=true')])
        self.logo_control.setAnimations([('conditional','effect=fade start=0 end=100 time=500 delay=500 condition=true')])
        self.logo_label.setAnimations([('conditional','effect=fade start=0 end=100 time=500 delay=500 condition=true')])
        self.background_control.setImage(bg_img)

        
    def process_image(self, image_control, image_url):
        # Needs to be implemented in sub class
        raise NotImplementedError

        
    def preload_image(self, image_url):
        # set the next image to an unvisible image-control for caching
        self.log('preloading image: %s' % repr(image_url))
        self.preload_control.setImage(image_url)
        self.log('preloading done')

        
    def wait(self):
        # wait in chunks of 500ms to react earlier on exit request
        chunk_wait_time = int(CHUNK_WAIT_TIME)
        remaining_wait_time = int(self.NEXT_IMAGE_TIME)
        while remaining_wait_time > 0:
            if self.exit_requested:
                self.log('wait aborted')
                return
            if remaining_wait_time < chunk_wait_time: chunk_wait_time = remaining_wait_time
            remaining_wait_time -= chunk_wait_time
            xbmc.sleep(chunk_wait_time)

            
    def stop(self):
        self.log('stop')
        self.exit_requested = True
        self.exit_monitor = None

        
    def close(self):
        self.del_controls()

        
    def del_controls(self):
        self.log('del_controls start')
        self.xbmc_window.removeControls(self.image_controls)
        self.xbmc_window.removeControls(self.global_controls)
        self.preload_control = None
        self.background_control = None
        self.loading_control = None
        self.image_controls = []
        self.global_controls = []
        self.xbmc_window.close()
        self.xbmc_window = None
        self.log('del_controls end')

        
    def log(self, msg, level=xbmc.LOGDEBUG):
        xbmc.log(ADDON_ID + '-' + ADDON_VERSION + '-' + msg, level)


class TableDropScreensaver(ScreensaverBase):
    MODE = 'TableDrop'
    IMAGE_CONTROL_COUNT = 20
    FAST_IMAGE_COUNT = 0
    NEXT_IMAGE_TIME = 1500
    MIN_WIDTH = 500
    MAX_WIDTH = 700

    def load_settings(self):
        self.NEXT_IMAGE_TIME = int(REAL_SETTINGS.getSetting('tabledrop_wait'))

        
    def process_image(self, image_control, image_url):
        ROTATE_ANIMATION = ('effect=rotate start=0 end=%d center=auto time=%d ' 'delay=0 tween=circle condition=true')
        DROP_ANIMATION = ('effect=zoom start=%d end=100 center=auto time=%d ' 'delay=0 tween=circle condition=true')
        FADE_ANIMATION = ('effect=fade start=0 end=100 time=200 ' 'condition=true')
        # hide the image
        image_control.setVisible(False)
        image_control.setImage('')
        # re-stack it (to be on top)
        self.xbmc_window.removeControl(image_control)
        self.xbmc_window.addControl(image_control)
        # calculate all parameters and properties
        width = random.randint(self.MIN_WIDTH, self.MAX_WIDTH)
        height = int(width / self.image_aspect_ratio)
        x_position = random.randint(0, 1280 - width)
        y_position = random.randint(0, 720 - height)
        drop_height = random.randint(400, 800)
        drop_duration = drop_height * 1.5
        rotation_degrees = random.uniform(-20, 20)
        rotation_duration = drop_duration
        animations = [
            ('conditional', FADE_ANIMATION),
            ('conditional', ROTATE_ANIMATION % (rotation_degrees, rotation_duration)),
            ('conditional', DROP_ANIMATION % (drop_height, drop_duration)),
            ]
        # set all parameters and properties
        image_control.setImage(image_url)
        image_control.setPosition(x_position, y_position)
        image_control.setWidth(width)
        image_control.setHeight(height)
        image_control.setAnimations(animations)
        # show the image
        image_control.setVisible(True)

        
class AppleTVLikeScreensaver(ScreensaverBase):
    MODE = 'AppleTVLike'
    IMAGE_CONTROL_COUNT = 35
    FAST_IMAGE_COUNT = 2
    DISTANCE_RATIO = 0.7
    SPEED = 1.0
    CONCURRENCY = 1.0

    def load_settings(self):
        self.SPEED = float(REAL_SETTINGS.getSetting('appletvlike_speed'))
        self.CONCURRENCY = float(REAL_SETTINGS.getSetting('appletvlike_concurrency'))
        self.MAX_TIME = int(15000 / self.SPEED)
        self.NEXT_IMAGE_TIME = int(4500.0 / self.CONCURRENCY / self.SPEED)

        
    def stack_cycle_controls(self):
        # randomly generate a zoom in percent as betavariant
        # between 10 and 70 and assign calculated width to control.
        # Remove all controls from window and re-add sorted by size.
        # This is needed because the bigger (=nearer) ones need to be in front
        # of the smaller ones.
        # Then shuffle image list again to have random size order.

        for image_control in self.image_controls:
            zoom = int(random.betavariate(2, 2) * 40) + 10
            #zoom = int(random.randint(10, 70))
            width = 1280 / 100 * zoom
            image_control.setWidth(width)
        self.image_controls = sorted(self.image_controls, key=lambda c: c.getWidth())
        self.xbmc_window.addControls(self.image_controls)
        random.shuffle(self.image_controls)

        
    def process_image(self, image_control, image_url):
        MOVE_ANIMATION = ('effect=slide start=0,720 end=0,-720 center=auto time=%s ' 'tween=linear delay=0 condition=true')
        image_control.setVisible(False)
        image_control.setImage('')
        # calculate all parameters and properties based on the already set
        # width. We can not change the size again because all controls need
        # to be added to the window in size order.
        width = image_control.getWidth()
        zoom = width * 100 / 1280
        height = int(width / self.image_aspect_ratio)
        # let images overlap max 1/2w left or right
        center = random.randint(0, 1280)
        x_position = center - width / 2
        y_position = 0
        time = self.MAX_TIME / zoom * self.DISTANCE_RATIO * 100
        animations = [('conditional', MOVE_ANIMATION % time),]
        # set all parameters and properties
        image_control.setImage(image_url)
        image_control.setPosition(x_position, y_position)
        image_control.setWidth(width)
        image_control.setHeight(height)
        image_control.setAnimations(animations)
        # show the image
        image_control.setVisible(True)


def cycle(iterable):
    saved = []
    for element in iterable:
        yield element
        saved.append(element)
    while saved:
        for element in saved: yield element


if __name__ == '__main__':
    screensaver = ScreensaverManager()
    screensaver.start_loop()
    screensaver.close()
    del screensaver
    sys.modules.clear()
