#-------------------------------------------------------------------------------
# Copyright (C) 2017 Carlos Guzman (cguZZman) carlosguzmang@protonmail.com
# 
# This file is part of Cloud Drive Common Module for Kodi
# 
# Cloud Drive Common Module for Kodi is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
# 
# Cloud Drive Common Module for Kodi is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
# 
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
#-------------------------------------------------------------------------------


from threading import Lock
import threading
import time
import urllib
from clouddrive.common.utils import Utils

class KodiUtils:
    LOGDEBUG = 0
    LOGNOTICE = 1
    LOGWARNING = 2
    LOGERROR = 3
    lock = Lock()
    
    @staticmethod
    def get_addon(addonid=None):
        import xbmcaddon
        if addonid:
            return xbmcaddon.Addon(addonid)
        else:
            return xbmcaddon.Addon()
    
    @staticmethod
    def get_system_monitor():
        import xbmc
        return xbmc.Monitor()
    
    @staticmethod
    def get_window(window_id):
        import xbmcgui
        return xbmcgui.Window(window_id)
    
    @staticmethod
    def get_current_window_id():
        import xbmcgui
        return xbmcgui.getCurrentWindowId()
    
    @staticmethod
    def get_supported_media(media_type):
        import xbmc
        return xbmc.getSupportedMedia(media_type).replace(".","").split("|")
    
    @staticmethod
    def execute_json_rpc(method, params=None, request_id=1):
        import xbmc
        import json
        cmd = {'jsonrpc': '2.0', 'method': method, 'id': request_id}
        if params:
            cmd['params'] = params
        return json.loads(xbmc.executeJSONRPC(json.dumps(cmd)))
    
    @staticmethod
    def get_cond_visibility(cmd):
        import xbmc
        xbmc.getCondVisibility(cmd)
        
    @staticmethod
    def executebuiltin(cmd, wait=False):
        import xbmc
        xbmc.executebuiltin(cmd, wait)
        
    @staticmethod
    def run_script(addonid, params=None, wait=False):
        import xbmc
        cmd = 'RunScript(%s,0,%s)' % (addonid, '?%s' % urllib.urlencode(params))
        xbmc.executebuiltin(cmd, wait)
        
    @staticmethod
    def run_plugin(addonid, params=None, wait=False):
        import xbmc
        url = 'plugin://%s/' % addonid
        if params:
            url += '?%s' % urllib.urlencode(params)
        cmd = 'RunPlugin(%s)' % url
        xbmc.executebuiltin(cmd, wait)
        
    @staticmethod
    def activate_window(addon_url, window_id=None, params=None, wait=False):
        import xbmc
        if not window_id:
            window_id = KodiUtils.get_current_window_id()
        if params:
            addon_url += '?%s' % urllib.urlencode(params)
        cmd = 'ActivateWindow(%d,%s)' % (window_id, addon_url)
        xbmc.executebuiltin(cmd, wait)
        
    @staticmethod
    def replace_window(addon_url, window_id=None, params=None, wait=False):
        import xbmc
        if not window_id:
            window_id = KodiUtils.get_current_window_id()
        if params:
            addon_url += '?%s' % urllib.urlencode(params)
        cmd = 'ReplaceWindow(%d,%s)' % (window_id, addon_url)
        xbmc.executebuiltin(cmd, wait)
    
    @staticmethod
    def is_addon_enabled(addonid):
        response = KodiUtils.execute_json_rpc('Addons.GetAddonDetails', {'addonid': addonid})
        return response["result"]["addon"]["enabled"]

    @staticmethod
    def get_addon_setting(setting_id, addonid=None):
        addon = KodiUtils.get_addon(addonid)
        setting = addon.getSetting(setting_id)
        del addon
        return setting
    
    @staticmethod
    def set_addon_setting(setting_id, value, addonid=None):
        from clouddrive.common.utils import Utils
        addon = KodiUtils.get_addon(addonid)
        setting = addon.setSetting(setting_id, Utils.str(value))
        del addon
        return setting
    
    @staticmethod
    def get_addon_info(info_id, addonid=None):
        addon = KodiUtils.get_addon(addonid)
        info = addon.getAddonInfo(info_id)
        del addon
        return info
    
    @staticmethod
    def get_service_port(service, addonid=None):
        KodiUtils.lock.acquire()
        port = KodiUtils.get_addon_setting('%s.service.port' % service, addonid)
        KodiUtils.lock.release()
        return port

    @staticmethod
    def set_service_port(service, port, addonid=None):
        from clouddrive.common.utils import Utils
        KodiUtils.lock.acquire()
        KodiUtils.set_addon_setting('%s.service.port' % service, Utils.str(port), addonid)
        KodiUtils.lock.release()
    
    @staticmethod
    def get_signin_server(addonid=None):
        return KodiUtils.get_addon_setting('sign-in-server', addonid)
    
    @staticmethod
    def get_cache_expiration_time(addonid=None):
        return int(Utils.default(KodiUtils.get_addon_setting('cache-expiration-time', addonid), '5'))
    
    @staticmethod
    def log(msg, level):
        import xbmc
        if level == 0:
            level = xbmc.LOGDEBUG
        elif level == 1:
            level = xbmc.LOGNOTICE
        elif level == 2:
            level = xbmc.LOGWARNING
        elif level == 3:
            level = xbmc.LOGERROR
        xbmc.log('[%s][%s-%s]: %s' % (KodiUtils.get_addon_info('id'), threading.current_thread().name,threading.current_thread().ident, msg), level)

    @staticmethod
    def translate_path(path):
        import xbmc
        return xbmc.translatePath(path)
    
    @staticmethod
    def to_timestamp(s):
        import dateutil.parser
        try:
            return int(time.mktime(dateutil.parser.parse(s).timetuple()))
        except:
            return None
    
    @staticmethod
    def file_exists(f):
        import xbmcvfs
        return xbmcvfs.exists(f)
    
    @staticmethod
    def mkdirs(f):
        import xbmcvfs
        return xbmcvfs.mkdirs(f)