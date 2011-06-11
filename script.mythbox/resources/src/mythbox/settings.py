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
import socket
import string
import mythbox.msg as m

from mythbox.bus import Event, EventBus
from mythbox.mythtv.db import MythDatabase
from mythbox.util import requireDir, safe_str
from xml.dom import minidom

slog = logging.getLogger('mythbox.settings')


class SettingsException(Exception):
    """Thrown when a setting fails validation in MythSettings""" 
    pass


class MythSettings(object):
    """Settings reside in $HOME/.xbmc/userdata/script_data/MythBox/settings.xml"""

    def __init__(self, platform, translator, filename='settings.xml', bus=None):
        self.platform = platform
        self.initDefaults()
        self.d = self.defaults.copy()
        self.translator = translator
        self.settingsFilename = filename
        self.settingsPath = os.path.join(self.platform.getScriptDataDir(), self.settingsFilename)
        
        #
        # Hack alert: defer event publishing until after initial load
        #
        self.bus = None
        try:
            self.load()
        except SettingsException:
            pass
        self.bus = bus

    def isConfirmOnDelete(self): return self.getBoolean('confirm_on_delete')
    
    def isAggressiveCaching(self): return self.getBoolean('aggressive_caching')
            
    def setMySqlHost(self, host): self.put('mysql_host', host)

    def setMySqlPort(self, port): self.put('mysql_port', '%s' % port)

    def setMySqlDatabase(self, db): self.put('mysql_database', db)
    
    def setMySqlUser(self, user): self.put('mysql_user', user)

    def setMySqlPassword(self, password): self.put('mysql_password', password)

    def setRecordingDirs(self, dirs):
        """
        @type dirs: str  - one or more separated by os.pathsep      
        @type dirs: str[] 
        """
        if type(dirs) == str:
            self.put('paths_recordedprefix', dirs)
        elif type(dirs) == list:
            self.put('paths_recordedprefix', os.pathsep.join(dirs))
        else:
            raise Exception("unsupported param type for dirs: %s" + type(dirs))
        
    def getRecordingDirs(self):
        """
        @return: MythTV recording directories on the local filesystem
        @rtype: str[]
        """
        return self.get('paths_recordedprefix').split(os.pathsep)
        
    def get(self, tag):
        if self.d.has_key(tag):
            return self.d[tag]
        else:
            return None

    def put(self, tag, value):
        old = None
        if self.d.has_key(tag):
            old = self.d[tag]
        self.d[tag] = value
        
        # Only notify of changes if the new value is different
        if old is not None and old != value:
            if self.bus:
                self.bus.publish({'id': Event.SETTING_CHANGED, 'tag': tag, 'old': old, 'new': value})
                
    def initDefaults(self):
        self.defaults = {
            'mysql_host'                 : 'localhost',
            'mysql_port'                 : '3306',
            'mysql_database'             : 'mythconverg',
            'mysql_user'                 : 'mythtv',
            'mysql_password'             : 'change_me',
            'mysql_encoding_override'    : 'latin1',
            'streaming_enabled'          : 'True',
            'paths_recordedprefix'       : self.platform.getDefaultRecordingsDir(),
            'aggressive_caching'         : 'True',
            'recorded_view_by'           : '2', 
            'upcoming_view_by'           : '2',
            'confirm_on_delete'          : 'True',
            'fanart_tvdb'                : 'True',
            'fanart_tmdb'                : 'True',
            'fanart_imdb'                : 'True',
            'fanart_tvrage'              : 'True',
            'fanart_google'              : 'True',
            'feeds_twitter'              : 'mythboxfeed',
            'logging_enabled'            : 'False',

            'schedules_last_selected'    : '0',
            'schedules_sort_by'          : 'Title',
            
            'livetv_last_selected'       : '0',

            'recordings_last_selected'   : '0',
            'recordings_selected_group'  : u'',
            'recordings_selected_program': u'',
            'recordings_group_sort'      : 'Date',
            'recordings_title_sort'      : 'Date',
            
            'tv_guide_last_selected'     : '0',
            'upcoming_sort_by'           : 'Date',
            'upcoming_sort_ascending'    : 'False',
        }

    def load(self):
        """
        @raise SettingsException: when settings file not found
        """
        filePath = self.settingsPath
        slog.debug("Loading settings from %s" % filePath)
        if not os.path.exists(filePath):
            raise SettingsException('File %s does not exist.' % filePath)
        else:
            # use saved configuration
            dom = minidom.parse(filePath)
            mythtv = dom.getElementsByTagName('mythtv')[0]
            assert(mythtv is not None)
            for tag in self.defaults.keys():
                results = mythtv.getElementsByTagName(tag)
                if len(results) > 0:
                    #print results[0].toxml()
                    if hasattr(results[0].firstChild, 'nodeValue'):
                        self.d[tag] = string.strip(results[0].firstChild.nodeValue)
                    else:
                        # empty nodes default to empty string instead of None
                        self.d[tag] = u''
                else:
                    slog.error('no tag found for %s ' % tag)
                    
    def save(self):
        settingsDir = self.platform.getScriptDataDir()
        requireDir(settingsDir)

        dom = minidom.parseString('<mythtv></mythtv>'.encode('utf-8'))
        for key in self.d.keys():
            e = dom.createElement(key)
            n = dom.createTextNode(self.d[key].strip())
            e.appendChild(n)
            dom.childNodes[0].appendChild(e)
        slog.debug('Saving settings to %s' % self.settingsPath)
        fh = file(self.settingsPath, 'w')
        fh.write(dom.toxml(encoding='utf-8'))
        fh.close()

    def getBoolean(self, tag):
        return self.get(tag) in ('True', 'true', '1')
    
    def verify(self):
        """
        @raise SettingsException: on invalid settings
        """
        for tag in self.defaults.keys():
            if self.get(tag) is None:
                raise SettingsException('%s %s' % (self.translator.get(m.MISSING_SETTINGS_TAG), tag))
        
        MythSettings.verifyMySQLHost(self.get('mysql_host'))
        MythSettings.verifyMySQLPort(self.get('mysql_port'))
        MythSettings.verifyMySQLDatabase(self.get('mysql_database'))
        MythSettings.verifyString(self.get('mysql_user'), 'Enter MySQL user. Hint: mythtv is the MythTV default')
        self.verifyMySQLConnectivity()
        self.verifyMythTVConnectivity()
        
        if not self.getBoolean('streaming_enabled'): 
            MythSettings.verifyRecordingDirs(self.get('paths_recordedprefix'))
        
        MythSettings.verifyBoolean(self.get('confirm_on_delete'), 'Confirm on delete must be True or False')
        MythSettings.verifyBoolean(self.get('aggressive_caching'), 'Aggressive Caching must be True or False')
        slog.debug('verified settings')

    def verifyMythTVConnectivity(self):
        domainCache = None
        db = MythDatabase(self, self.translator, domainCache)
        self.master = db.getMasterBackend()
        
        try:
            from mythbox.mythtv.conn import Connection
            session = Connection(self, translator=self.translator, platform=self.platform, bus=EventBus(), db=db)
            session.close()
        except Exception, ex:
            slog.exception(ex)
            raise SettingsException('Connection to MythTV host %s failed: %s' % (db.getMasterBackend().ipAddress, ex))
    
    def verifyMySQLConnectivity(self):
        try:
            domainCache = None
            db = MythDatabase(self, self.translator, domainCache)
            db.close()
            del db
        except Exception, ex:
            raise SettingsException("Connect to MySQL failed: %s" % ex)
    
    def __repr__(self):
        sb = ''
        for tag in self.defaults.keys():
            sb += '%s = %s\n' % (tag, [safe_str(self.get(tag)), '<EMPTY>'][self.get(tag) is None]) 
        return sb
    
    @staticmethod    
    def verifyRecordingDirs(recordingDirs):
        # TODO: Check for empty recordings dir
        MythSettings.verifyString(recordingDirs, "Enter one or more '%s' separated MythTV recording directories" % os.pathsep)
        for dir in recordingDirs.split(os.pathsep):
            if not os.path.exists(dir):
                raise SettingsException("Recording directory '%s' does not exist." % dir)
            if not os.path.isdir(dir):
                raise SettingsException("Recording directory '%s' is not a directory." % dir)
        
    @staticmethod    
    def verifyMySQLHost(host):
        MythSettings.verifyString(host, 'Enter MySQL server hostname or IP address')
        MythSettings.verifyHostnameOrIPAddress(host, "Hostname '%s' cannot be resolved to an IP address." % host)

    @staticmethod
    def verifyMySQLPort(port):
        errMsg = 'Enter MySQL server port. Hint: 3306 is the MySQL default'
        MythSettings.verifyString(port, errMsg)
        MythSettings.verifyNumberBetween(port, 0, 65336, errMsg)

    @staticmethod
    def verifyMySQLUser(user):
        errMsg = 'Enter MySQL user name for MythTV database'
        MythSettings.verifyString(user, errMsg)
        
    @staticmethod    
    def verifyMySQLDatabase(dbName):
        MythSettings.verifyString(dbName, 'Enter MySQL database name. Hint: mythconverg is the MythTV default')
    
    @staticmethod    
    def verifyHostnameOrIPAddress(host, errMsg):
        try:
            socket.gethostbyname(host)
        except Exception:
            raise SettingsException("%s %s" % (errMsg, ''))

    @staticmethod
    def verifyBoolean(s, errMsg):
        MythSettings.verifyString(s, errMsg)
        if not s in ('True', 'False', '0', '1'):
            raise SettingsException(errMsg)
            
    @staticmethod
    def verifyString(s, errMsg):
        """
        @param s: string to verify
        @param errMsg: Error message
        @raise SettingsException: if passed in string is None or blank. 
        """
        if s is None or s.strip() == '':
            raise SettingsException(errMsg)
    
    @staticmethod    
    def verifyNumberBetween(num, min, max, errMsg):
        n = None
        try:
            n = int(num)
        except Exception:
            raise SettingsException("%s %s" % (errMsg, ''))
        if not min <= n <= max:
            raise SettingsException(errMsg)