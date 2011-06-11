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
import logging
import os
import xbmcgui
import mythbox.msg as m

from mythbox.settings import MythSettings, SettingsException
from mythbox.ui.toolkit import window_busy, BaseWindow, enterNumeric, enterText, Action
from mythbox.util import catchall, timed, safe_str
from mythbox.advanced import AdvancedSettings

log = logging.getLogger('mythbox.ui')


class SettingValidator(object):
    
    def __init__(self, errorMessage):
        self.errorMessage = errorMessage
        
    def validate(self, value):
        """
        @raise SettingsException: On validation failure
        """
        raise SettingsException("%s : %s" % (self.errorMessage, value))
    
    def isValid(self, value):
        try:
            self.validate(value)
            return True
        except:
            return False


class ExternalizedSettingValidator(SettingValidator):
    
    def __init__(self, validatorMethod, arg1=None):
        self.validatorMethod = validatorMethod
        self.arg1 = arg1
        
    def validate(self, value):
        """
        @raise SettingsException: On validation failure
        """
        try:
            if not self.arg1:
                self.validatorMethod(value)
            else:
                self.validatorMethod(value, self.arg1)
        except Exception, ex:
            raise SettingsException(str(ex))


class Setting(object):
    """
    Binds MythSettings, validation mechanism, ui rendering, and xbmc controls together
    to simplify input, update, validation, and ui presentation of settings.
    
    @todo Convert to use window properies instead of widget.get()/set()
    """
    
    def __init__(self, store, key, type, validator, widget):
        """
        @param store: MythSettings backing store for settings that gets persisted
        @param key: string index into MythSettings get(...)  set(...) methods
        @param type: class of preferred native type (int, bool, str). Used to determine input method: numeric or string
        @param validator: Validator class that encapsulates validation run on entry by user. 
                          If not valid, useful error message should be thrown
        @param widget: xbmc.Control* type to set value for presentation - ControlButton, ControlCheckBox
        """
        self.store = store
        self.key = key
        self.type = type
        self.widget = widget
        if validator is None:
            self.validator = None
        else:
            self.validator = validator.validate

    def readInput(self):
        ok = False
        if self.type == str:
            ok, value = enterText(control=self.widget, validator=self.validator)
        elif self.type in (int, Seconds,):
            ok, value = enterNumeric(control=self.widget, validator=self.validator, current=self.store.get(self.key))
        elif self.type == NegativeSeconds:
            ok, value = enterNumeric(control=self.widget, validator=self.validator, current= str(int(self.store.get(self.key)) * -1))
            if value != '0':
                value = '-' + value
        elif self.type == bool and type(self.widget) == xbmcgui.ControlRadioButton:
            ok, value = True, ['False', 'True'][self.widget.isSelected()]
        else:
            log.warn('readinput() not activated for type %s and widget %s' % (self.type, type(self.widget)))

        if ok:
            self.store.put(self.key, value)
            self.render() # re-render since enterNumeric(...) doesn't handle special cases like Seconds

    def render(self):
        value = self.store.get(self.key)
        
        if type(self.widget) == xbmcgui.ControlButton:
            if self.type == str:
                self.widget.setLabel(label=self.widget.getLabel(), label2=value)
            elif self.type == int:
                self.widget.setLabel(label=self.widget.getLabel(), label2=str(value))
            elif self.type == Seconds:
                self.widget.setLabel(label=self.widget.getLabel(), label2='%s seconds' % value)
            elif self.type == NegativeSeconds:
                self.widget.setLabel(label=self.widget.getLabel(), label2='%s seconds' % str(int(value) * -1))                
            else:
                raise Exception('Dont know how to handle type %s in render()' % self.type)
        elif type(self.widget) == xbmcgui.ControlRadioButton:
            if self.type == bool:
                self.widget.setSelected(self.store.get(self.key) in ('True', 'true', '1'))
            else:
                raise Exception('Dont know how to handle type %s in render()' % self.type)
        else:
            raise Exception('Unknown widget in render(): %s' % type(self.widget))
            
class Seconds(object):
    
    def __init__(self, min, max):
        self.min = min
        self.max = max
        
    def validate(self, value):
        try:
            s = int(value)
            if s < min or s > max:
                raise SettingsException('out of bounds')
        except Exception, e:
            raise SettingsException(e.message)
    
class NegativeSeconds(object):
    pass

class SettingsWindow(BaseWindow):
    
    def __init__(self, *args, **kwargs):
        BaseWindow.__init__(self, *args, **kwargs)
        [setattr(self,k,v) for k,v in kwargs.iteritems() if k in ('settings','translator','platform','fanArt','cachesByName',)]
        self.settingsMap = {}  # key = controlId,  value = Setting
        self.t = self.translator.get
        self.advanced = AdvancedSettings(platform=self.platform)
        log.debug('Advanced settings:\n %s' % self.advanced)
                 
    def register(self, setting):
        self.settingsMap[setting.widget.getId()] = setting
    
    @timed 
    def onInit(self):
        if not self.win:
            log.debug('onInit')
            self.win = xbmcgui.Window(xbmcgui.getCurrentWindowId())
            
            # Nav Buttons
            self.testSettingsButton = self.getControl(253)
            self.clearCacheButton = self.getControl(405)
            
            self.streamingEnabledRadioButton = self.getControl(208)
            self.recordingsButton = self.getControl(205) 
            
            # MythTV Settings
            if hasattr(self.settings, 'master') and self.settings.master:
                self.setWindowProperty('MasterBackendHostname', '%s / %s' % (self.settings.master.hostname, self.settings.master.ipAddress))
                self.setWindowProperty('MasterBackendPort', str(self.settings.master.port))
            
            self.register(Setting(self.settings, 'streaming_enabled', bool, None, self.getControl(208)))
            self.register(Setting(self.settings, 'paths_recordedprefix', str, ExternalizedSettingValidator(MythSettings.verifyRecordingDirs), self.getControl(205)))
            self.register(Setting(self.settings, 'confirm_on_delete', bool, None, self.getControl(206)))
            self.register(Setting(self.settings, 'aggressive_caching', bool, None, self.getControl(207)))
            
            # MySQL Settings
            self.register(Setting(self.settings, 'mysql_host', str, ExternalizedSettingValidator(MythSettings.verifyMySQLHost), self.getControl(301)))
            self.register(Setting(self.settings, 'mysql_port', int, ExternalizedSettingValidator(MythSettings.verifyMySQLPort), self.getControl(302)))
            self.register(Setting(self.settings, 'mysql_database', str, ExternalizedSettingValidator(MythSettings.verifyMySQLDatabase), self.getControl(303)))
            self.register(Setting(self.settings, 'mysql_user', str, ExternalizedSettingValidator(MythSettings.verifyMySQLUser), self.getControl(304)))              
            self.register(Setting(self.settings, 'mysql_password', str, None, self.getControl(305)))
    
            # Fanart Settings
            self.register(Setting(self.settings, 'fanart_tvdb',   bool, None, self.getControl(401)))
            self.register(Setting(self.settings, 'fanart_tvrage', bool, None, self.getControl(406)))
            self.register(Setting(self.settings, 'fanart_tmdb',   bool, None, self.getControl(402)))
            self.register(Setting(self.settings, 'fanart_imdb',   bool, None, self.getControl(403)))
            self.register(Setting(self.settings, 'fanart_google', bool, None, self.getControl(404)))
    
            # Advanced Settings
            self.register(Setting(self.settings, 'logging_enabled', bool, None, self.getControl(502)))
            self.register(Setting(self.settings, 'feeds_twitter', str, None, self.getControl(503)))
            self.setWindowProperty('debugLogLocation', self.translator.get(m.DEBUG_LOG_LOCATION) % self.platform.getDebugLog())
                        
            # Playback settings
            self.advanced.get = self.advanced.getSetting
            self.advanced.put = self.advanced.setSetting
            self.register(Setting(self.advanced, 'video/timeseekforward', Seconds, None, self.getControl(602)))
            self.register(Setting(self.advanced, 'video/timeseekbackward', NegativeSeconds, None, self.getControl(603)))
            self.register(Setting(self.advanced, 'video/timeseekforwardbig', Seconds, None, self.getControl(604)))
            self.register(Setting(self.advanced, 'video/timeseekbackwardbig', NegativeSeconds, None, self.getControl(605)))

            self.render()
            
    @catchall    
    @window_busy
    def onClick(self, controlId):
        log.debug('onClick %s ' % controlId)
        source = self.getControl(controlId)

        mappedSetting = self.settingsMap.get(controlId)
        if mappedSetting:
            mappedSetting.readInput()
            if mappedSetting.store == self.advanced:
                self.advanced.put('video/usetimeseeking', 'true') # required for seek values to take effect
                self.advanced.save()
                log.debug(self.advanced)
            else:
                if self.streamingEnabledRadioButton == source: 
                    self.renderStreaming()
                self.settings.save()
        elif self.testSettingsButton == source: self.testSettings()
        elif self.clearCacheButton == source: self.clearCache()
        else: log.debug("nothing done onClick")
        log.debug('=================================\n%s' % self.settings)
            
    def onFocus(self, controlId):
        pass
            
    @catchall
    def onAction(self, action):
        if action.getId() in (Action.PREVIOUS_MENU, Action.PARENT_DIR):
            self.close()

    def renderStreaming(self):
        # special mutual exclusion for handling of streaming enabled
        self.recordingsButton.setEnabled(not self.streamingEnabledRadioButton.isSelected())

    @window_busy
    def render(self):
        for setting in self.settingsMap.values():
            log.debug('Rendering %s' % safe_str(setting.key))
            setting.render()

        self.renderStreaming()
                    
        import default
        about = "[B]%s[/B]\n\n%s\n\n%s\n\n%s\n\n\n\nMythBox would not be possible without the\nfollowing opensource software and services" % (default.__scriptname__, default.__author__, default.__url__, self.platform.addonVersion())
        opensource = """
        [B]Software[/B]
        
        BiDict
        BeautifulSoup
        Decorator
        Eclipse
        ElementTree
        FeedParser
        GNU/Linux
        HTMLTestRunner
        IMDBPy
        Mockito
        MythTV
        MySQL-Connector-Python
        ODict
        PyDev for Eclipse
        Python
        Python-Twitter 
        SimpleJSON
        TheMovieDb Python API
        TVDB Python API
        TVRage Python API
        Twisted
        XBMC
        
        [B]Services[/B]
        
        Google Image Search
        Google Code Project Hosting
        Internet Movie Database
        The Movie Database
        TVDB
        TVRage
        Twitter
        """
        self.setWindowProperty('AboutText', about)
        self.setWindowProperty('OpensourceText', opensource)
        self.setWindowProperty('ReadmeText', '%s\n%s' % (
            open(os.path.join(self.platform.getScriptDir(), 'README'), 'r').read(),
            open(os.path.join(self.platform.getScriptDir(), 'FAQ'), 'r').read()))

    @window_busy
    def testSettings(self):
        try:
            self.settings.verify()
            self.setWindowProperty('MasterBackendHostname', '%s / %s' % (self.settings.master.hostname, self.settings.master.ipAddress))
            self.setWindowProperty('MasterBackendPort', str(self.settings.master.port))
            xbmcgui.Dialog().ok(self.t(m.INFO), u'', self.t(m.SETTINGS_OK))
        except SettingsException, ex:
            self.settings.master = None
            self.setWindowProperty('MasterBackendHostname', '')
            self.setWindowProperty('MasterBackendPort', '')
            xbmcgui.Dialog().ok(self.t(m.ERROR), u'', str(ex))
            
    @window_busy    
    def clearCache(self):
        for fileCache in self.cachesByName.values():
            fileCache.clear()
        self.fanArt.clear()
        xbmcgui.Dialog().ok(self.t(m.INFO), u'', self.t(m.CACHES_CLEARED))
        