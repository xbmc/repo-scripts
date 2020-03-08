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
from clouddrive.common.ui.logger import Logger


class Utils:
    
    _extension_map = {
        'html' : 'text/html',
        'htm' : 'text/html',
        'txt' : 'text/plain',
        'rtf' : 'application/rtf',
        'odf' : 'application/vnd.oasis.opendocument.text',
        'pdf' : 'application/pdf',
        'doc' : 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
        'docx' : 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
        'epub' : 'application/epub+zip',
        'xls' : 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        'sxc' : 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        'csv' : 'text/csv',
        'ppt' : 'application/vnd.openxmlformats-officedocument.presentationml.presentation',
        'pptx' : 'application/vnd.openxmlformats-officedocument.presentationml.presentation',
        'sxi' : 'application/vnd.oasis.opendocument.presentation',
        'json' : 'application/json',
        'mkv' : 'video/x-matroska'
    }   
    
    @staticmethod
    def get_extension(name):
        index = name.rfind('.')
        if index > -1:
            return name[index+1:].lower()
        return ''
    
    @staticmethod
    def remove_extension(name):
        index = name.rfind('.')
        if index > -1:
            return name[:index]
        return name
    
    @staticmethod
    def replace_extension(name, newExtension):
        index = name.rfind('.')
        if index > -1:
            return name[:index+1] + newExtension
        return name
    
    @staticmethod
    def get_safe_value(dictionary, key, default_value=None):
        if dictionary and key in dictionary:
            return dictionary[key]
        return default_value
    
    @staticmethod
    def default(value, default_value):
        return value if value else default_value
    
    @staticmethod
    def unicode(txt):
        if isinstance (txt,str):
            txt = txt.decode("utf-8")
        return u'%s' % (txt)
    
    @staticmethod
    def str(txt):
        return Utils.unicode(txt).encode("utf-8", 'replace')
    
    @staticmethod
    def ascii(txt):
        return Utils.unicode(txt).encode('ascii', 'ignore')
   
    @staticmethod
    def get_fqn(o):
        return o.__module__ + "." + o.__class__.__name__
    
    @staticmethod
    def get_class(fqn):
        data = fqn.split('.')
        module = __import__(data[0])
        for comp in data[1:]:
            module = getattr(module, comp)
        return module
    
    @staticmethod
    def get_file_buffer():
        try:
            from cStringIO import StringIO
        except ImportError:
            from StringIO import StringIO
            
        return StringIO()
    
    @staticmethod
    def get_parent_path(path):
        index = path.rfind('/')
        if index > -1:
            return path[:index]
        return ''
    
    @staticmethod
    def get_mimetype_by_extension(extension):
        return Utils.get_safe_value(Utils._extension_map, Utils.default(extension, ''))
    
    @staticmethod
    def get_source_id(ip):
        data = ip.split('.')
        source_id = 0
        Logger.debug("ip is:" + ip)
        for n in data:
            Logger.debug("part: " + n)
            source_id += int(n)
        return source_id

    @staticmethod
    def remove_folder(folder_path, system_monitor=None):
        from clouddrive.common.ui.utils import KodiUtils
        if not KodiUtils.rmdir(folder_path, True):
            if not system_monitor:
                system_monitor=KodiUtils.get_system_monitor()
            if system_monitor.waitForAbort(3):
                return False
            return KodiUtils.rmdir(folder_path, True)
        return True