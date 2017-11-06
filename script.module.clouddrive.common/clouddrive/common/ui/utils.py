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

import json
from threading import Lock
import threading
import time
import urllib

from clouddrive.common.utils import Utils
import dateutil.parser
import xbmc
import xbmcaddon
import xbmcgui


class KodiUtils:
    LOGDEBUG = xbmc.LOGDEBUG
    LOGNOTICE = xbmc.LOGNOTICE
    LOGERROR = xbmc.LOGERROR
    LOGWARNING = xbmc.LOGWARNING
    lock = Lock()
    
    @staticmethod
    def get_addon(addonid=None):
        if addonid:
            return xbmcaddon.Addon(addonid)
        else:
            return xbmcaddon.Addon()
    
    @staticmethod
    def get_system_monitor():
        return xbmc.Monitor()
    
    @staticmethod
    def get_window(window_id):
        return xbmcgui.Window(window_id)
    
    @staticmethod
    def execute_json_rpc(method, params=None, request_id=1):
        cmd = {'jsonrpc': '2.0', 'method': method, 'id': request_id}
        if params:
            cmd['params'] = params
        return json.loads(xbmc.executeJSONRPC(json.dumps(cmd)))
    
    @staticmethod
    def run_script(addonid, params=None, wait=False):
        cmd = 'RunScript(%s,0,%s)' % (addonid, '?%s' % urllib.urlencode(params))
        xbmc.executebuiltin(cmd, wait)
        
    @staticmethod
    def run_plugin(addonid, params=None, wait=False):
        url = 'plugin://%s/' % addonid
        if params:
            url += '?%s' % urllib.urlencode(params)
        cmd = 'RunPlugin(%s)' % url
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
        KodiUtils.lock.acquire()
        KodiUtils.set_addon_setting('%s.service.port' % service, Utils.str(port), addonid)
        KodiUtils.lock.release()
    
    @staticmethod
    def log(msg, level):
        xbmc.log('[%s][%s-%s]: %s' % (KodiUtils.get_addon_info('id'), threading.current_thread().name,threading.current_thread().ident, msg), level)

    @staticmethod
    def translate_path(path):
        return xbmc.translatePath(path)
    
    @staticmethod
    def to_timestamp(s):
        try:
            return int(time.mktime(dateutil.parser.parse(s).timetuple()))
        except:
            return None
    