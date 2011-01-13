#
#  MythBox for XBMC - http://mythbox.googlecode.com
#  Copyright (C) 2010 analogue@yahoo.com
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
import md5

from mythbox.filecache import FileResolver
from mythbox.mythtv.conn import inject_conn
from mythbox.mythtv.db import inject_db
from mythbox.util import safe_str

log = logging.getLogger('mythbox.cache')


class MythThumbnailResolver(FileResolver):
    
    def __init__(self, conn=None, db=None):
        self._conn = conn
        self._db = db
    
    # non-injection for unit tests
    def db(self):
        return self._db

    # non-injection for unit tests
    def conn(self):
        return self._conn
    
    @inject_db
    @inject_conn
    def store(self, program, dest):
        """
        @type program : RecordedProgram  
        @param dest: file to save downloaded program thumbnail to
        """
        key = self.getKey(program)
        backend = self.db().toBackend(program.hostname())
        result = self.conn().transferFile(key, dest, backend.ipAddress)
        
        if not result:
            # thumb not generated -- generate thumb and retry
            if self.conn().generateThumbnail(program, backend.ipAddress):
                result = self.conn().transferFile(key, dest, backend.ipAddress)
                if not result:
                    # transfer failed
                    pass
            else:
                # remote thumb generation failed
                pass
            
    def hash(self, program):
        return md5.new(safe_str(self.getKey(program))).hexdigest()
    
    @inject_conn    
    def getKey(self, program):
        # TODO: Fix hack
        if self.conn().protocol.genPixMapPreviewFilename(program) == '<EMPTY>':
            return program.getFilename() + '.png'
        else:
            return program.getFilename() + '.640x360.png'


class MythChannelIconResolver(FileResolver):
    
    def __init__(self, conn=None):
        self._conn = conn
        
    def conn(self):
        return self._conn
    
    @inject_conn
    def store(self, channel, dest):
        """
        @type channel : Channel 
        @param dest: file to save downloaded chanel icon to
        """
        if channel.getIconPath():
            # TODO: Can channel icons be requested from slave backend? Replace None with backend hostname 
            #       if this turns out to be true.
            rc = self.conn().transferFile(channel.getIconPath(), dest, None)
            if not rc:
                log.error('Transfer of icon %s for channel %s failed.' % (channel.getIconPath(), channel.getChannelName()))
        else:
            log.debug('Channel %s has no icon' % channel.getChannelName())
            
    def hash(self, channel):
        if channel.getIconPath():
            return md5.new(safe_str(channel.getIconPath())).hexdigest()
        else:
            return u''
