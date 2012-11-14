#
#  MythBox for XBMC - http://mythbox.googlecode.com
#  Copyright (C) 2011 analogue@yahoo.com
#
#  This program is free software; you can redistribute it and/or
#  modify it under the terms of the GNU General Public License
#  as published by the Free Software Foundation; either version 2
#  of the License, or (at your option) any later version.
#
#  This program is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with this program; if not, write to the Free Software
#  Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301, USA.
#
import os
import sys
import traceback
import xbmc
import xbmcgui

from mythbox.bus import EventBus


class BootStrapper(object):
    
    def __init__(self, splash):
        self.log = None
        self.platform = None
        self.stage = 'Initializing'
        self.shell = None
        self.splash = splash
        self.failSilent = False
        
    def run(self):
        try:
            try:
                self.bootstrapLogger()
                self.bootstrapPlatform()
                self.bootstrapEventBus()            
                self.bootstrapCaches()
                self.bootstrapSettings()
                self.bootstrapUpdater()
                self.bootstrapFeeds()
                # TODO: Re-enable when twisted not loaded from dist-packages
                #self.bootstrapDebugShell()
                self.bootstrapHomeScreen()
            except Exception, ex:
                if not self.failSilent:
                    self.handleFailure(ex)
        finally:
            self.splash.close()
            
    def handleFailure(self, cause):
        msg = 'MythBox:%s - Error: %s' % (self.stage, cause)
        xbmc.log(msg)
        print traceback.print_exc()
        if self.log:
            self.log.exception(str(cause))
        xbmcgui.Dialog().ok('MythBox Error', 'Stage: %s' % self.stage, 'Exception: %s' % str(cause))
        
    def updateProgress(self, msg):
        self.log.info(msg)

    def bootstrapLogger(self):
        import logging
        import logging.config
        self.stage = 'Initializing Logger'
        
        import xbmcaddon
        scriptDir = xbmcaddon.Addon('script.mythbox').getAddonInfo('path')
        
#        if 'win32' in sys.platform:
#            loggerIniFile = os.path.join(scriptDir, 'mythbox_win32_log.ini')
#        elif 'darwin' in sys.platform:
#            import StringIO, re
#            loggerIniFile = os.path.join(scriptDir, 'mythbox_log.ini')
#            logconfig = open(loggerIniFile, 'r').read()
#            loggerIniFile = StringIO.StringIO(re.sub('mythbox\.log', os.path.expanduser(os.path.join('~', 'Library', 'Logs', 'mythbox.log')) , logconfig, 1))
#        else:
        loggerIniFile = os.path.join(scriptDir, 'mythbox_log.ini')

        # needs to be in local scope for fileConfig to find it
        from mythbox.log import XbmcLogHandler
        
        xbmc.log('MythBox: loggerIniFile = %s' % loggerIniFile)
        logging.config.fileConfig(loggerIniFile)
        self.log = logging.getLogger('mythbox.core')
        self.log.info('Mythbox Logger Initialized')

    def bootstrapPlatform(self):
        self.stage = 'Initializing Platform'
        import mythbox.platform
        self.platform = mythbox.platform.getPlatform()
        self.platform.addLibsToSysPath()
        sys.setcheckinterval(0)
        cacheDir = self.platform.getCacheDir()
        from mythbox.util import requireDir
        requireDir(cacheDir)
        
        self.log.info('MythBox %s Initialized' % self.platform.addonVersion())

    def bootstrapEventBus(self):
        self.bus = EventBus()

    def bootstrapCaches(self):
        self.stage = 'Initializing Caches'
        
        from mythbox.util import NativeTranslator
        from mythbox.filecache import FileCache, HttpResolver, MythThumbnailFileCache
        from mythbox.mythtv.resolver import MythChannelIconResolver, MythThumbnailResolver 
        from os.path import join

        from mythbox.mythtv.cache import DomainCache
        self.domainCache = DomainCache(bus=self.bus)
        
        cacheDir = self.platform.getCacheDir()
        self.translator = NativeTranslator(self.platform.getScriptDir())
        self.mythThumbnailCache = MythThumbnailFileCache(join(cacheDir, 'thumbnail'), MythThumbnailResolver(), self.bus, self.domainCache)
        self.mythChannelIconCache = FileCache(join(cacheDir, 'channel'), MythChannelIconResolver())
        self.httpCache = FileCache(join(cacheDir, 'http'), HttpResolver())
        
        self.cachesByName = {
            'mythThumbnailCache'  : self.mythThumbnailCache, 
            'mythChannelIconCache': self.mythChannelIconCache, 
            'httpCache'           : self.httpCache,
            'domainCache'         : self.domainCache
        }

    def bootstrapSettings(self):
        self.stage = 'Initializing Settings'
        from mythbox.settings import MythSettings
        self.settings = MythSettings(self.platform, self.translator, 'settings.xml', self.bus)

        #from fanart import FanArt
        #self.log.debug('Settings = \n %s' % self.settings)

        class DelayedInstantiationProxy(object):
            '''Could use a little introspection to sort this out but eh...'''
            
            def __init__(self, *args, **kwargs):
                self.args = args
                self.kwargs = kwargs
                self.fanArt = None
                
            def requireDelegate(self):
                if self.fanArt is None:
                    from fanart import FanArt
                    self.fanArt = FanArt(*self.args, **self.kwargs)
            
            def getSeasonAndEpisode(self, program):
                self.requireDelegate()
                return self.fanArt.getSeasonAndEpisode(program)
            
            def getRandomPoster(self, program):
                self.requireDelegate()
                return self.fanArt.getRandomPoster(program)
            
            def getPosters(self, program):
                self.requireDelegate()
                return self.fanArt.getPosters(program)
        
            def hasPosters(self, program):
                self.requireDelegate()
                return self.fanArt.hasPosters(program)
            
            def clear(self):
                self.requireDelegate()
                self.fanArt.clear() 
        
            def shutdown(self):
                self.requireDelegate()
                self.fanArt.shutdown()
                
            def configure(self, settings):
                self.requireDelegate()
                self.fanArt.configure(settings)
            
            def onEvent(self, event):
                self.requireDelegate()
                self.fanArt.onEvent(event)
                    
        from fanart import FanArt
        self.fanArt = FanArt(self.platform, self.httpCache, self.settings, self.bus)
        #self.fanArt = DelayedInstantiationProxy(self.platform, self.httpCache, self.settings, self.bus)
        
        try:
            import socket
            socket.setdefaulttimeout(float(os.getenv('MYTHBOX_TIMEOUT', '30')))
        except:
            self.log.exception('Error setting socket timeout')
            
        self.bus.register(self)

        # Generate fake event to reflect value in settings.xml instead of mythbox_log.ini
        from bus import Event
        self.onEvent({'id': Event.SETTING_CHANGED, 'tag':'logging_enabled', 'old':'DontCare', 'new':self.settings.get('logging_enabled')})
        
    def bootstrapUpdater(self):
        self.stage = 'Initializing Updater'
        from mythbox.updater import UpdateChecker
        UpdateChecker(self.platform).run()

    def bootstrapFeeds(self):
        from mythbox.feeds import FeedHose
        self.feedHose = FeedHose(self.settings, self.bus)

    def bootstrapDebugShell(self):
        # debug shell only packaged with bin/package-debug-zip
        try: 
            from mythbox.shell import DebugShell
            globals()['bootstrapper'] = self
            self.shell = DebugShell(self.bus, namespace=globals())
            self.shell.start()
        except ImportError:
            self.log.debug('Punting on debug shell -- not packaged')

    def bootstrapXbmcShutdownListener(self):
        from threading import Thread
        
        class XbmcShutdownListener(Thread):        

            def __init__(self, home, bus, log):
                Thread.__init__(self)
                self.home = home
                self.log = log
                self.shutdownReceived = False
                bus.register(self)
             
            def onEvent(self, event):
                from bus import Event
                if event['id'] == Event.SHUTDOWN:
                    self.shutdownReceived = True
                    self.join()
                    xbmc.log('Joined shutdown listener') 
                
            def run(self):
                import time
                xbmc.log('XbmcShutdownListener thread running..')
                cnt = 1
                while not xbmc.abortRequested and not self.shutdownReceived:
                    #xbmc.sleep(1000)
                    time.sleep(1)
                    xbmc.log('XbmcShutdownListner abort = %s user = %s tick %d ...' % (xbmc.abortRequested, self.shutdownReceived, cnt))
                    cnt += 1
                    
                if xbmc.abortRequested:
                    xbmc.log('XBMC requested shutdown..')
                    self.home.shutdown()
                    xbmc.log('XBMC requested shutdown complete')
                    
                xbmc.log('XbmcShutdownListener thread terminating')
                
        self.shutdownListener = XbmcShutdownListener(self.home, self.bus, self.log)
        self.shutdownListener.start()

    def bootstrapHomeScreen(self):
        
        from mythbox.ui.home import HomeWindow
        self.home = HomeWindow(
                'mythbox_home.xml', 
                self.platform.getScriptDir(), 
                settings=self.settings, 
                translator=self.translator, 
                platform=self.platform, 
                fanArt=self.fanArt, 
                cachesByName=self.cachesByName,
                bus=self.bus,
                feedHose=self.feedHose)
        self.splash.close()
        #self.bootstrapXbmcShutdownListener()
        self.home.doModal()

    def onEvent(self, event):
        from bus import Event
        
        #
        # Apply changes to logger when user turns debug logging on/off
        #
        if event['id'] == Event.SETTING_CHANGED and event['tag'] == 'logging_enabled':
            import logging
            logging.root.debug('Setting changed: %s %s %s' % (event['tag'], event['old'], event['new']))

            if event['new'] == 'True': 
                level = logging.DEBUG
            else: 
                level = logging.WARN
                
            loggerNames = 'unittest mysql core method skin ui perf fanart settings cache event'.split() # wire inject'.split()
                
            for name in loggerNames:
                logger = logging.getLogger('mythbox.%s' %  name)
                logger.setLevel(level)

            # TODO: Adjust xbmc loglevel 
            #savedXbmcLogLevel = xbmc.executehttpapi("GetLogLevel").replace("<li>", "")
            #xbmc.executehttpapi('SetLogLevel(3)')
