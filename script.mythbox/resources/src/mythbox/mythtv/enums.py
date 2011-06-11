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
from odict import odict


class FlagMask(object):
    
    # from libs/libmythtv/programinfo.h
    FL_COMMFLAG       = 0x01
    FL_CUTLIST        = 0x02
    FL_AUTOEXP        = 0x04
    FL_EDITING        = 0x08
    FL_BOOKMARK       = 0x10
    FL_INUSERECORDING = 0x0020
    FL_INUSEPLAYING   = 0x0040
    FL_TRANSCODED     = 0x0400
    FL_WATCHED        = 0x0800
    FL_PRESERVED      = 0x1000


class RecordingStatus(object):

    DELETED             = -5
    STOPPED             = -4 
    RECORDED            = -3
    RECORDING           = -2
    WILL_RECORD         = -1
    UNKNOWN             = 0
    MANUAL_OVERRIDE     = 1
    PREVIOUS_RECORDING  = 2
    CURRENT_RECORDING   = 3
    EARLIER_SHOWING     = 4
    TOO_MANY_RECORDINGS = 5
    CANCELLED           = 6
    CONFLICT            = 7
    LATER_SHOWING       = 8
    REPEAT              = 9
    OVERLAP             = 10
    LOW_DISK_SPACE      = 11
    TUNER_BUSY          = 12
    
    translations = {
        DELETED            : 88,
        STOPPED            : 89,
        RECORDED           : 90,
        RECORDING          : 91,
        WILL_RECORD        : 92,
        UNKNOWN            : 93,
        MANUAL_OVERRIDE    : 94,
        PREVIOUS_RECORDING : 95,
        CURRENT_RECORDING  : 96,
        EARLIER_SHOWING    : 97,
        TOO_MANY_RECORDINGS: 98,
        CANCELLED          : 99,
        CONFLICT           :100,
        LATER_SHOWING      :101,
        REPEAT             :102,
        OVERLAP            :103,
        LOW_DISK_SPACE     :104,
        TUNER_BUSY         :105
    }


class ScheduleType(object):
    '''See recordingtypes.cpp'''
    
    NOT_RECORDING = 0
    ONCE          = 1
    DAILY         = 2
    CHANNEL       = 3
    ALWAYS        = 4
    WEEKLY        = 5
    FIND_ONE      = 6
    OVERRIDE      = 7
    DONT_RECORD   = 8
    FIND_DAILY    = 9
    FIND_WEEKLY   = 10
    
    translations = odict([
        (ONCE         ,111),
        (DAILY        ,112),
        (WEEKLY       ,115),
        (FIND_ONE     ,116),
        (FIND_DAILY   ,119),
        (FIND_WEEKLY  ,120),
        (CHANNEL      ,113),
        (ALWAYS       ,114),
        (OVERRIDE     ,117),
        (DONT_RECORD  ,118),
        (NOT_RECORDING,170)])
    
    long_translations = odict([
        (ONCE         ,135),
        (DAILY        ,136),
        (WEEKLY       ,139),
        (FIND_ONE     ,140),
        (FIND_DAILY   ,143),
        (FIND_WEEKLY  ,144),
        (CHANNEL      ,137),
        (ALWAYS       ,138),
        (OVERRIDE     ,141),
        (DONT_RECORD  ,142),
        (NOT_RECORDING,170)])
    

class EpisodeFilter(object):
    """
        Really part of the CheckForDupesIn enum, but separated out since 
        presented as a separate chooser on the UI.
        
        If the value is not NONE, logically OR with the CheckForDupesIn value
        to derive the correct value for the record.dupin column.  
    """
    
    # RecordingDupInType:
    #    kDupsNewEpi         = 0x10,  16
    #    kDupsExRepeats      = 0x20,  32
    #    kDupsExGeneric      = 0x40,  64
    #    kDupsFirstNew       = 0x80   128

    NONE                         = 0     
    NEW_EPISODES_ONLY            = 16    
    EXCLUDE_REPEATS              = 32  
    EXCLUDE_GENERICS             = 64  
    EXCLUDE_REPEATS_AND_GENERICS = 96  
    
    # Record new episode first showings - not supported yet
    # FIRST_NEW                  = 128 
    
    translations = odict([
        (NONE                        ,201),
        (NEW_EPISODES_ONLY           ,152),
        (EXCLUDE_REPEATS             ,151),
        (EXCLUDE_GENERICS            ,202),
        (EXCLUDE_REPEATS_AND_GENERICS,203)])
    

class CheckForDupesIn(object):
    """
    RecordingDupInType:
       kDupsInRecorded     = 0x01,  1
       kDupsInOldRecorded  = 0x02,  2
       kDupsInAll          = 0x0F,  15
    """
    
    CURRENT_RECORDINGS  = 1      
    PREVIOUS_RECORDINGS = 2      
    ALL_RECORDINGS      = 15     
    
    translations = odict([
        (ALL_RECORDINGS     ,153),
        (CURRENT_RECORDINGS ,149),
        (PREVIOUS_RECORDINGS,150)])

#   --------------------------------------------------------------------------------------------------------------
#   Duplicate Check Method    Check for Duplicates in    Episode Filter     dupin         dupmethod   Makes sense
#   --------------------------------------------------------------------------------------------------------------
#   None                      All Recordings             None               15            1           Y
#   Subtitle                  All Recordings             None               15            2           Y
#   Description               All Recordings             None               15            4           Y
#   Subtitle & Desc           All Recordings             None               15            6           Y
#   Subtitle then Desc        All Recordings             None               15            8           Y
#
#   None                      Current Recordings         None               1             1           Y
#   Subtitle                  Current Recordings         None               1             2           Y
#   
#   None                      Current Recordings         New Epi Only       17 (16+1)     1           Y
#   None                      All Recordings             New Epi Only       31 (16+15)    1           Y
#   None                      All Recordings             Exclude Generics   79 (64+15     1           Y 
#   None                      Previous Recordings        Exclude Rep&Gen    98 (64+32+2)  1           Y
#       
    
    
class CheckForDupesUsing(object):
    # TODO: Rename to RecordingDupMethodType
    
    NONE                      = 1
    SUBTITLE                  = 2
    DESCRIPTION               = 4
    SUBTITLE_AND_DESCRIPTION  = 6
    SUBTITLE_THEN_DESCRIPTION = 8 # TODO: Verify if exists in protocol 40
    
    translations = odict([
        (NONE,                      145), 
        (SUBTITLE,                  146), 
        (DESCRIPTION,               147), 
        (SUBTITLE_AND_DESCRIPTION,  148), 
        (SUBTITLE_THEN_DESCRIPTION, 200)])


class TVState(object):
    """
    Pre protocol version 44 TV State
    
    File    : /mythtv/libs/libmythtv/tv.h
    Object  : TVState - enumeration of the states used by TV and TVRec
    Protocol: QUERY_REMOTEENCODER::GETSTATE
    """
    
    #
    # Error State, if we ever try to enter this state errored is set.
    #
    Error = -1                  
    
    #
    # None State, this is the initial state in both TV and TVRec, it
    # indicates that we are ready to change to some other state.
    #
    OK = 0         
    
    #
    # Watching LiveTV is the state for when we are watching a
    # recording and the user has control over the channel and
    # the tuner to use. 
    #
    WatchingLiveTV = 1          
    
    #
    # Watching Pre-recorded is a TV only state for when we are
    # watching a pre-existing recording.
    #
    WatchingPreRecorded = 2
    
    #
    # Watching Recording is the state for when we are watching
    # an in progress recording, but the user does not have control
    # over the channel and tuner to use.
    #
    WatchingRecording = 3
    
    #
    # Recording Only is a TVRec only state for when we are recording
    # a program, but there is no one currently watching it.
    #
    RecordingOnly = 4
    
    #
    # This is a placeholder state which we never actualy enter,
    # but is returned by GetState() when we are in the process
    # of changing the state.
    #
    ChangingState = 5


class TVState44(object):
    """
    Protocol version 44 onwards TVState
    """
    
    #
    # Error State, if we ever try to enter this state errored is set.
    #
    Error = -1                  
    
    #
    # None State, this is the initial state in both TV and TVRec, it
    # indicates that we are ready to change to some other state.
    #
    OK = 0         
    
    #
    # Watching LiveTV is the state for when we are watching a
    # recording and the user has control over the channel and
    # the tuner to use. 
    #
    WatchingLiveTV = 1          
    
    #
    # Watching Pre-recorded is a TV only state for when we are
    # watching a pre-existing recording.
    #
    WatchingPreRecorded = 2
    
    #
    # Watching Video is the state when we are watching a video and is not
    # a dvd
    WatchingVideo = 3
    
    #
    # Watching DVD is the state when we are watching a DVD 
    #
    WatchingDVD = 4
    
    #
    # Watching Recording is the state for when we are watching
    # an in progress recording, but the user does not have control
    # over the channel and tuner to use.
    #
    WatchingRecording = 5
    
    #
    # Recording Only is a TVRec only state for when we are recording
    # a program, but there is no one currently watching it.
    #
    RecordingOnly = 6
    
    #
    # This is a placeholder state which we never actualy enter,
    # but is returned by GetState() when we are in the process
    # of changing the state.
    #
    ChangingState = 7


class TVState58(object):
    """
    Protocol version 58 onwards TVState
    """
    
    #
    # Error State, if we ever try to enter this state errored is set.
    #
    Error = -1                  
    
    #
    # None State, this is the initial state in both TV and TVRec, it
    # indicates that we are ready to change to some other state.
    #
    OK = 0         
    
    #
    # Watching LiveTV is the state for when we are watching a
    # recording and the user has control over the channel and
    # the tuner to use. 
    #
    WatchingLiveTV = 1          
    
    #
    # Watching Pre-recorded is a TV only state for when we are
    # watching a pre-existing recording.
    #
    WatchingPreRecorded = 2
    
    #
    # Watching Video is the state when we are watching a video and is not
    # a dvd
    WatchingVideo = 3
    
    #
    # Watching DVD is the state when we are watching a DVD 
    #
    WatchingDVD = 4

    #
    # Watching BD is the state when we are watching a Bluray Disc 
    #
    WatchingBD = 5
        
    #
    # Watching Recording is the state for when we are watching
    # an in progress recording, but the user does not have control
    # over the channel and tuner to use.
    #
    WatchingRecording = 6
    
    #
    # Recording Only is a TVRec only state for when we are recording
    # a program, but there is no one currently watching it.
    #
    RecordingOnly = 7
    
    #
    # This is a placeholder state which we never actualy enter,
    # but is returned by GetState() when we are in the process
    # of changing the state.
    #
    ChangingState = 8


class JobStatus(object):  
    """ 
    @see: Job.status
    """
    UNKNOWN  = 0x0000
    QUEUED   = 0x0001
    PENDING  = 0x0002
    STARTING = 0x0003
    RUNNING  = 0x0004
    STOPPING = 0x0005
    PAUSED   = 0x0006
    RETRYING = 0x0007
    ERRORING = 0x0008
    ABORTING = 0x0009
    
    DONE     = 0x0100 # Mask to indicate the job is done no matter what the status
    FINISHED = 0x0110 # 272
    ABORTED  = 0x0120 # 288
    ERRORED  = 0x0130 # 304
    CANCELED = 0x0140 # 320
    
    translations = odict([
        (UNKNOWN,  260),
        (QUEUED,   261),
        (PENDING,  262),
        (STARTING, 263),
        (RUNNING,  264),
        (STOPPING, 265),
        (PAUSED,   266),
        (RETRYING, 267),
        (ERRORING, 268),
        (ABORTING, 269),
        (DONE,     270),
        (FINISHED, 271),
        (ABORTED,  272),
        (ERRORED,  273),
        (CANCELED, 274)])


class JobType:  
    """ 
    @see: Job.jobType
    """
    NONE         = 0x0000
    
    SYSTEMJOB    = 0x00ff
    TRANSCODE    = 0x0001
    COMMFLAG     = 0x0002
    USERJOB      = 0xff00

    USERJOB1     = 0x0100
    USERJOB2     = 0x0200
    USERJOB3     = 0x0400
    USERJOB4     = 0x0800

    translations = odict([
        (NONE,      250),
        (SYSTEMJOB, 251),
        (TRANSCODE, 252),
        (COMMFLAG,  253),
        (USERJOB,   254),
        (USERJOB1,  255),
        (USERJOB2,  256),     
        (USERJOB3,  257),       
        (USERJOB4,  258)])


class Upcoming(object):
   
    # TODO: Verify MANUAL_OVERRIDE == ForceRecord from mythweb
    SCHEDULED = (RecordingStatus.WILL_RECORD, RecordingStatus.MANUAL_OVERRIDE)
    # TODO: MythWeb has 'NeverRecord' ... what is the equivalent enum?
    DUPLICATES = (RecordingStatus.PREVIOUS_RECORDING, RecordingStatus.CURRENT_RECORDING)
    CONFLICTS = (RecordingStatus.CONFLICT, RecordingStatus.OVERLAP)
    # TODO: All else...
    DEACTIVATED = () 


class CommercialDetectionType(object):
    
    COMMERCIAL_FREE = -2
    UNINITIALIZED   = -1
    OFF             = 0
    BLANK_FRAME     = 1 
    SCENE_CHANGE    = 2
    LOGO_CHANGE     = 4
    BLANK_FRAME_AND_SCENE_CHANGE = BLANK_FRAME | SCENE_CHANGE  # = 3  
    ALL = BLANK_FRAME | SCENE_CHANGE | LOGO_CHANGE             # = 7
    
    M2 = 0x00000100                                            # = 256
    M2_LOGO_CHANGE  = M2 | LOGO_CHANGE                         # = 260
    M2_BLANK_FRAME  = M2 | BLANK_FRAME                         # = 257
    M2_SCENE_CHANGE = M2 | SCENE_CHANGE                        # = 258
    M2_ALL = M2_LOGO_CHANGE | M2_BLANK_FRAME                   # = 262
    
    PREPOSTROLL = 0x00000200                                   # = 512 
    PREPOSTROLL_ALL = PREPOSTROLL | BLANK_FRAME | SCENE_CHANGE # = 515
