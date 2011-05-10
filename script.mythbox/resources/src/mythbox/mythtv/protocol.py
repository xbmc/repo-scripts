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

from mythbox.mythtv.enums import TVState, TVState44, TVState58

# MythTV Protcol Constants
initVersion = 8
initToken = ''
separator = u'[]:[]'
serverVersion = None


class ProtocolException(Exception):
    '''
    Thrown on protcol version mismatch between frontend and backend or
    general protocol related errors.
    ''' 
    pass


class BaseProtocol(object):
    
    def version(self):
        raise Exception, 'Abstract method'
    
    def recordSize(self):
        return len(self.recordFields())
    
    def tvState(self):
        raise Exception, 'Abstract method'
    
    def buildAnnounceFileTransferCommand(self, hostname, filePath):
        raise Exception, 'Abstract method'
    
    def getLiveTvBrain(self, settings, translator):
        raise Exception, 'Abstract method'

    def recordFields(self):
        return Exception, 'Abstract method'

    def emptyRecordFields(self):
        return []
    
    def protocolToken(self):
        return ""

    def mythVersion(self):
        raise Exception, 'Abstract method'

    def supportsStreaming(self, platform):
        raise Exception, 'Abstract method'


class Protocol40(BaseProtocol):
    
    def version(self):
        return 40
    
    def mythVersion(self):
        return '0.21'

    def recordFields(self):
        # Based on from https://github.com/MythTV/mythtv/blob/v0.23.1/mythtv/bindings/python/MythTV/MythData.py
        return [ 'title',        'subtitle',     'description',
                 'category',     'chanid',       'channum',
                 'callsign',     'channame',     'filename',
                 'fs_high',      'fs_low',       'starttime',
                 'endtime',      'duplicate',    'shareable',
                 'findid',       'hostname',     'sourceid',
                 'cardid',       'inputid',      'recpriority',
                 'recstatus',    'recordid',     'rectype',
                 'dupin',        'dupmethod',    'recstartts',
                 'recendts',     'repeat',       'programflags',
                 'recgroup',     'commfree',     'outputfilters',
                 'seriesid',     'programid',    'lastmodified',
                 'stars',        'airdate',      'hasairdate',
                 'playgroup',    'recpriority2', 'parentid',
                 'storagegroup', 'audio_props',  'video_props',
                 'subtitle_type']
    
    def tvState(self):
        return TVState
    
    def buildAnnounceFileTransferCommand(self, hostname, filePath):
        return ["ANN FileTransfer %s" % hostname, filePath]        

    def getLiveTvBrain(self, settings, translator):
        from mythbox.ui.livetv import MythLiveTvBrain
        return MythLiveTvBrain(settings, translator)

    def getFileSize(self, program):
        from mythbox.mythtv.conn import decodeLongLong
        return decodeLongLong(int(program.getField('fs_low')), int(program.getField('fs_high'))) / 1024.0

    def genPixMapCommand(self):
        return ['QUERY_GENPIXMAP']        

    def genQueryRecordingsCommand(self):
        return ['QUERY_RECORDINGS Play']

    def genPixMapPreviewFilename(self, program):
        return program.getBareFilename() + '.640x360.png'

    def supportsStreaming(self, platform):
        return True

class Protocol41(Protocol40):
    
    def version(self):
        return 41


class Protocol42(Protocol41):
    
    def version(self):
        return 42


class Protocol43(Protocol42):

    def version(self):
        return 43
    
    def recordFields(self):
        # Copied from https://github.com/MythTV/mythtv/blob/v0.23.1/mythtv/bindings/python/MythTV/MythData.py
        return [ 'title',        'subtitle',     'description',
                 'category',     'chanid',       'channum',
                 'callsign',     'channame',     'filename',
                 'fs_high',      'fs_low',       'starttime',
                 'endtime',      'duplicate',    'shareable',
                 'findid',       'hostname',     'sourceid',
                 'cardid',       'inputid',      'recpriority',
                 'recstatus',    'recordid',     'rectype',
                 'dupin',        'dupmethod',    'recstartts',
                 'recendts',     'repeat',       'programflags',
                 'recgroup',     'commfree',     'outputfilters',
                 'seriesid',     'programid',    'lastmodified',
                 'stars',        'airdate',      'hasairdate',
                 'playgroup',    'recpriority2', 'parentid',
                 'storagegroup', 'audio_props',  'video_props',
                 'subtitle_type','year']


class Protocol44(Protocol43):
    
    def version(self):
        return 44
    
    def tvState(self):
        return TVState44


class Protocol45(Protocol44):
    
    def version(self):
        return 45

    def buildAnnounceFileTransferCommand(self, hostname, filePath):
        # TODO: Storage group should be non-empty for recordings
        storageGroup = ''
        return ['ANN FileTransfer %s' % hostname, filePath, storageGroup]        


class Protocol46(Protocol45):
    
    def version(self):
        return 46


class Protocol47(Protocol46):
    
    def version(self):
        return 47


class Protocol48(Protocol47):
    
    def version(self):
        return 48


class Protocol49(Protocol48):
    
    def version(self):
        return 49


class Protocol50(Protocol49):
    
    def version(self):
        return 50

    def mythVersion(self):
        return '0.22'


class Protocol56(Protocol50):
    
    def version(self):
        return 56

    def mythVersion(self):
        return '0.23'


class Protocol23056(Protocol56):
    
    def version(self):
        return 23056
    
    def mythVersion(self):
        return '0.23.1'


class Protocol57(Protocol56):
    
    def version(self):
        return 57

    def mythVersion(self):
        return '0.24'

    def recordFields(self):
        return ['title','subtitle','description',
                'category','chanid','channum',
                'callsign','channame','filename',
                'filesize','starttime','endtime',
                'findid','hostname','sourceid',
                'cardid','inputid','recpriority',
                'recstatus','recordid','rectype',
                'dupin','dupmethod','recstartts',
                'recendts','programflags','recgroup',
                'outputfilters','seriesid','programid',
                'lastmodified','stars','airdate',
                'playgroup','recpriority2','parentid',
                'storagegroup','audio_props','video_props',
                'subtitle_type','year']
    
    def buildAnnounceFileTransferCommand(self, hostname, filePath):
        return ["ANN FileTransfer %s 0" % hostname, filePath, 'Default']

    def getFileSize(self, program):
        return int(program.getField('filesize')) / 1024.0

    def supportsStreaming(self, platform):
        # Eden and up
        return platform.xbmcVersion() >= 11.0 


class Protocol58(Protocol57):
    
    def tvState(self):
        return TVState58

    def version(self):
        return 58
    
    
class Protocol59(Protocol58):
    
    def version(self):
        return 59    


class Protocol60(Protocol59):
    
    def version(self):
        return 60
    
    def buildAnnounceFileTransferCommand(self, hostname, filePath):
        return ["ANN FileTransfer %s 0 1 10000" % hostname, filePath, 'Default']

    def genPixMapCommand(self):
        return ['QUERY_GENPIXMAP2', 'do_not_care']

    def genPixMapPreviewFilename(self, program):
        return '<EMPTY>'


class Protocol61(Protocol60):
    
    def version(self):
        return 61


class Protocol62(Protocol61):
    
    def version(self):
        return 62
    
    def protocolToken(self):
        return "78B5631E"


class Protocol63(Protocol62):
    
    def version(self):
        return 63
    
    def protocolToken(self):
        return "3875641D"


class Protocol64(Protocol63):
    
    def version(self):
        return 64
    
    def protocolToken(self):
        return "8675309J"


class Protocol65(Protocol64):
    
    def version(self):
        return 65
    
    def protocolToken(self):
        return "D2BB94C2"

    def genQueryRecordingsCommand(self): 
        # technically the old query recs command works but actually causes sorting which would be redundant and may be removed in the future
        return ['QUERY_RECORDINGS Unsorted']


# Current rev in mythversion.h
protocols = {
    40: Protocol40(),
    41: Protocol41(),
    42: Protocol42(),
    43: Protocol43(),
    44: Protocol44(),
    45: Protocol45(),
    46: Protocol46(),
    47: Protocol47(),
    48: Protocol48(),
    49: Protocol49(),
    50: Protocol50(),  # 0.22
    56: Protocol56(),  # 0.23
    23056: Protocol23056(), # 0.23.1 - mythbuntu weirdness    
    57: Protocol57(),  # 0.24
    58: Protocol58(),  # 0.24
    59: Protocol59(),  # 0.24
    60: Protocol60(),  # 0.24
    61: Protocol61(),  # 0.24
    62: Protocol62(),  # 0.24
    63: Protocol63(),  # 0.24
    64: Protocol64(),  # 0.24
    65: Protocol65()   # 0.24
}    