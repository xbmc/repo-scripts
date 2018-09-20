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
import urlparse

class KodiUtils:
    HOME_WINDOW = 10000
    LOGDEBUG = 0
    LOGNOTICE = 1
    LOGWARNING = 2
    LOGERROR = 3
    lock = Lock()
    common_addon_id = 'script.module.clouddrive.common'
    
    @staticmethod
    def get_addon(addonid=None):
        import xbmcaddon
        if addonid:
            return xbmcaddon.Addon(addonid)
        else:
            return xbmcaddon.Addon()
    @staticmethod
    def get_common_addon():
        return KodiUtils.get_addon(KodiUtils.common_addon_id)
    
    @staticmethod
    def get_common_addon_path():
        from clouddrive.common.utils import Utils
        return Utils.unicode(KodiUtils.get_addon_info("path", KodiUtils.common_addon_id))
    
    @staticmethod
    def localize(string_id, addonid=None, addon=None):
        if string_id < 32000:
            import xbmc
            return xbmc.getLocalizedString(string_id) 
        if not addon:
            addon = KodiUtils.get_addon(addonid)
        return addon.getLocalizedString(string_id)
    
    @staticmethod
    def create_list_item(id, label):
        import xbmcgui
        from clouddrive.common.utils import Utils
        list_item = xbmcgui.ListItem(label)
        list_item.setProperty('id', Utils.str(id))
        return list_item
    
    @staticmethod
    def get_language_code():
        import xbmc
        return xbmc.getLanguage(format=xbmc.ISO_639_1, region=True)
         
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
        cmd = json.dumps(cmd)
        return json.loads(xbmc.executeJSONRPC(cmd)) 
    
    @staticmethod
    def get_cond_visibility(cmd):
        import xbmc
        xbmc.getCondVisibility(cmd)
        
    @staticmethod
    def update_library(database, wait=False):
        KodiUtils.executebuiltin('UpdateLibrary(%s)' % database, wait)
        
    @staticmethod
    def executebuiltin(cmd, wait=False):
        import xbmc
        xbmc.executebuiltin(cmd, wait)
        
    @staticmethod
    def run_script(script, params=None, wait=False):
        import xbmc
        if params:
            params = urllib.urlencode(params)
        cmd = 'RunScript(%s,0,?%s)' % (script, params)
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
        with KodiUtils.lock:
            port = KodiUtils.get_addon_setting('%s.service.port' % service, addonid)
        return port

    @staticmethod
    def set_service_port(service, port, addonid=None):
        from clouddrive.common.utils import Utils
        with KodiUtils.lock:
            KodiUtils.set_addon_setting('%s.service.port' % service, Utils.str(port), addonid)
    
    @staticmethod
    def get_signin_server(addonid=None):
        return KodiUtils.get_addon_setting('sign-in-server', addonid)
    
    @staticmethod
    def get_cache_expiration_time(addonid=None):
        from clouddrive.common.utils import Utils
        return int(Utils.default(KodiUtils.get_addon_setting('cache-expiration-time', addonid), '5'))
    
    @staticmethod
    def log(msg, level):
        import xbmc
        from clouddrive.common.utils import Utils
        if level == 0:
            level = xbmc.LOGDEBUG
        elif level == 1:
            level = xbmc.LOGNOTICE
        elif level == 2:
            level = xbmc.LOGWARNING
        elif level == 3:
            level = xbmc.LOGERROR
        xbmc.log('[%s][%s-%s]: %s' % (KodiUtils.get_addon_info('id'), threading.current_thread().name,threading.current_thread().ident, Utils.str(msg)), level)

    @staticmethod
    def translate_path(path):
        import xbmc
        return xbmc.translatePath(path)
    
    @staticmethod
    def to_kodi_item_date_str(dt):
        s = None
        if dt:
            s = '%02d.%02d.%04d' % (dt.day, dt.month, dt.year,)
        return s
    
    @staticmethod
    def to_db_date_str(dt):
        s = None
        if dt:
            s = '%04d-%02d-%02d %02d:%02d:%02d' % (dt.year, dt.month, dt.day, dt.hour, dt.minute, dt.second)
        return s
    
    @staticmethod
    def to_datetime(s):
        import dateutil.parser
        try:
            return dateutil.parser.parse(s)
        except:
            return None
        
    @staticmethod
    def to_timestamp(s):
        dt = KodiUtils.to_datetime(s)
        if dt:
            dt = int(time.mktime(dt.timetuple()))
        return dt
    
    @staticmethod
    def file(f, opts):
        import xbmcvfs
        return xbmcvfs.File(f, opts)
    
    @staticmethod
    def file_exists(f):
        import xbmcvfs
        return xbmcvfs.exists(f)
    
    @staticmethod
    def file_delete(f):
        import xbmcvfs
        return xbmcvfs.delete(f)
    
    @staticmethod
    def file_rename(f, newFile):
        import xbmcvfs
        return xbmcvfs.rename(f, newFile)
    
    @staticmethod
    def mkdirs(f):
        import xbmcvfs
        return xbmcvfs.mkdirs(f)
    
    @staticmethod
    def rmdir(f, force=False):
        import xbmcvfs
        return xbmcvfs.rmdir(f, force)
    
    @staticmethod
    def read_content_file(file_path):
        content = None
        f = None
        try:
            f = KodiUtils.file(file_path, 'r')
            content = f.read()
        finally:
            if f:
                f.close()
        return content

    @staticmethod
    def kodi_player_class():
        import xbmc
        return xbmc.Player
    
    @staticmethod
    def get_info_label(label):
        import xbmc
        return xbmc.getInfoLabel(label)
    
    @staticmethod
    def get_current_library_info():
        dbtype = KodiUtils.get_info_label('ListItem.DBTYPE')
        dbid = KodiUtils.get_info_label('ListItem.DBID')
        path = KodiUtils.get_info_label('ListItem.FileNameAndPath')
        if path:
            return {'type': dbtype, 'id': dbid, 'path': path}
    
    @staticmethod
    def find_video_in_library(itemtype, item_id, filename):
        KodiUtils.log('find_video_in_library - %s - %s - %s' % (itemtype, item_id, filename), KodiUtils.LOGDEBUG)
        db = itemtype + 's'
        params = {'properties':['file'], 'filter': {"field": "filename", "operator": "contains", "value": filename}}
        response = KodiUtils.execute_json_rpc('videolibrary.get' + db, params)
        if response['result']['limits']['total'] > 0:
            collection = response['result'][db]
            for video in collection:
                path = video['file']
                content = KodiUtils.read_content_file(path)
                if content:
                    params = urlparse.parse_qs(urlparse.urlparse(content).query)
                    if 'item_id' in params:
                        if params['item_id'][0] == item_id:
                            KodiUtils.log('FOUND!', KodiUtils.LOGDEBUG)
                            return {'type': itemtype, 'id': video[itemtype+'id'], 'path': path}

    @staticmethod
    def find_exported_video_in_library(item_id, filename):
        info = KodiUtils.find_video_in_library('episode', item_id, filename)
        if not info:
            info = KodiUtils.find_video_in_library('movie', item_id, filename)
        return info
    
    @staticmethod
    def get_video_details(itemtype, dbid):
        params = {'properties':['resume','playcount'], itemtype + 'id': int(dbid)}
        key = itemtype + 'details'
        response = KodiUtils.execute_json_rpc('videolibrary.get' + key, params)
        if 'result' in response and key in response['result']:
            return response['result'][key]
    
    @staticmethod
    def save_video_details(itemtype, dbid, details):
        details[itemtype + 'id'] = int(dbid)
        key = itemtype + 'details'
        return KodiUtils.execute_json_rpc('videolibrary.set' + key, details)
    
    @staticmethod
    def get_home_property(key):
        win = KodiUtils.get_window(KodiUtils.HOME_WINDOW)
        value = win.getProperty(key)
        del win
        return value
    
    @staticmethod
    def set_home_property(key, value):
        win = KodiUtils.get_window(KodiUtils.HOME_WINDOW)
        win.setProperty(key, value)
        del win
    
    @staticmethod
    def clear_home_property(key):
        win = KodiUtils.get_window(KodiUtils.HOME_WINDOW)
        win.clearProperty(key)
        del win
