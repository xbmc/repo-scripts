# TODO: clean all of this, split into separate classess and files.
import sys
sys.path.append("/usr/share/pyshared/xbmc/")
# Install xbmc-eventclients-common, then check where it is located:
# apt-get update
# apt-get install xbmc-eventclients-common
# find it (in cache): /var/cache/apt/archives/xbmc-eventclients-common*.deb
# every next run install as (or use preinstalled casper-sn.ext2/casper-rw):
# dpkg -i xbmc-eventclients-common
# 
# dpkg -L xbmc-eventclients-common
# look for /usr/share/pyshared/xbmc/xbmcclient.py and update the path above.
import os, sys
import xbmc
import xbmcaddon
import xbmcgui
import fnmatch
import os.path
import thread
import threading
import re
from xml.dom import minidom, Node

# Script constants
_ = sys.modules[ "__main__" ].__language__
__scriptname__ = sys.modules[ "__main__" ].__scriptname__
__scriptid__   = sys.modules[ "__main__" ].__scriptid__
__version__    = sys.modules[ "__main__" ].__version__
__addon__      = sys.modules[ "__main__" ].__addon__
__resource__   = sys.modules[ "__main__" ].__resource__
__cwd__        = sys.modules[ "__main__" ].__cwd__
__language__   = __addon__.getLocalizedString

def debuglog(msg):
    xbmc.log("### [%s]: %s" % (__scriptname__,msg),level=xbmc.LOGDEBUG)

from threading import Timer, Lock, Thread
try:
    from xbmcclient import *
except ImportError:
    debuglog("No xbmcclient, using HTTP API instead")
    XBMCClient = None

#get action codes from XBIRRemote.h
IR_SELECT = 11
IR_ENTER = 22
IR_MENU = 247
IR_BACK = 216
IR_PAUSE = 230
IR_STOP = 224
IR_NEXT = 223
IR_PREV = 221
IR_FORWARD = 227
IR_REWIND = 226
IR_PLAY = 234
IR_0 = 207
IR_1 = 206
IR_2 = 205
IR_3 = 204
IR_4 = 203
IR_5 = 202
IR_6 = 201
IR_7 = 200
IR_8 = 199
IR_9 = 198
#rest:
IR_LEFT = 169
IR_RIGHT = 168
IR_UP = 166
IR_DOWN = 167
IR_INFO = 195
IR_DISPLAY = 213
IR_TITLE = 229
IR_POWER = 196
IR_MY_TV = 49
IR_MY_MUSIC = 9
IR_MY_PICTURES = 6
IR_MY_VIDEOS = 7
IR_RECORD = 232
IR_START = 37
IR_VOL_PLUS = 208
IR_VOL_MINUS = 209
IR_CH_PLUS = 210
IR_CH_MINUS = 211
IR_MUTE = 192
IR_RECORDED_TV = 101
IR_LIVE_TV = 24
IR_STAR = 40
IR_HASH = 41
IR_CLEAR = 249
IR_TXT = 250
IR_RED = 251
IR_GREEN = 252
IR_YELLOW = 253
IR_BLUE = 254
IR_SUBTITLE = 44
IR_LANGUAGE = 45


BP_ACTION_NONE = 0
BP_ACTION_SELECT = 1
BP_ACTION_PREVIOUS_MENU = 2
BP_ACTION_PAUSE = 3
BP_ACTION_STOP = 4
BP_ACTION_NEXT_TRACK = 5
BP_ACTION_PREV_TRACK = 6
BP_ACTION_SETUP = 7
BP_ACTION_FORWARD = 8
BP_ACTION_BACKWARD = 9
BP_ACTION_PLAY = 10
BP_ACTION_0 = 11
BP_ACTION_1 = 12
BP_ACTION_2 = 13
BP_ACTION_3 = 14
BP_ACTION_4 = 15
BP_ACTION_5 = 16
BP_ACTION_6 = 17
BP_ACTION_7 = 18
BP_ACTION_8 = 19
BP_ACTION_9 = 20
BP_ACTION_STEP_FORWARD = 21
BP_ACTION_STEP_BACK = 22
BP_ACTION_BIG_STEP_FORWARD = 23
BP_ACTION_BIG_STEP_BACK = 24
BP_ACTION_NEXT_ALBUM = 25
BP_ACTION_PREV_ALBUM = 26
BP_ACTION_LOAD = 27
BP_ACTION_SAVE = 28
BP_ACTION_RESCAN = 29
BP_ACTION_PROGRAM = 30
BP_ACTION_NORMAL = 31
BP_ACTION_REPEAT = 32
BP_ACTION_REPEAT_ONE = 33
BP_ACTION_ALBUM = 34
BP_ACTION_OFF_ENABLE = 35
BP_ACTION_OFF_DISABLE = 36
BP_ACTION_REPEAT_AB = 37

BUTON_PERMANENT_MAPPING = {0		: BP_ACTION_NONE,
                  IR_SELECT		: BP_ACTION_SELECT,
                  IR_ENTER		: BP_ACTION_SELECT,
                  IR_MENU		: BP_ACTION_PREVIOUS_MENU,
                  IR_BACK		: BP_ACTION_PREVIOUS_MENU,
                  9			: BP_ACTION_PREVIOUS_MENU,
                  10			: BP_ACTION_PREVIOUS_MENU,
                  275			: BP_ACTION_PREVIOUS_MENU,
                  61467			: BP_ACTION_PREVIOUS_MENU,
                  216			: BP_ACTION_PREVIOUS_MENU,
                  257			: BP_ACTION_PREVIOUS_MENU,
                  IR_PAUSE		: BP_ACTION_PAUSE,
                  IR_STOP		: BP_ACTION_STOP,
                  IR_NEXT		: BP_ACTION_NEXT_TRACK,
                  IR_PREV		: BP_ACTION_PREV_TRACK,
                  IR_FORWARD		: BP_ACTION_FORWARD,
                  IR_REWIND		: BP_ACTION_BACKWARD,
                  IR_PLAY		: BP_ACTION_PLAY,
                  IR_0			: BP_ACTION_0,
                  IR_1			: BP_ACTION_1, 
                  IR_2			: BP_ACTION_2,
                  IR_3			: BP_ACTION_3,
                  IR_4			: BP_ACTION_4,
                  IR_5			: BP_ACTION_5,
                  IR_6			: BP_ACTION_6,
                  IR_7			: BP_ACTION_7,
                  IR_8			: BP_ACTION_8,
                  IR_9			: BP_ACTION_9}

BUTTON_MAPPING = [[0,"bStepForward",	BP_ACTION_STEP_FORWARD, 	2201, 2202],
                  [0,"bStepBack",	BP_ACTION_STEP_BACK, 		2301, 2302],
                  [0,"bBigStepForward",	BP_ACTION_BIG_STEP_FORWARD,	2401, 2402],
                  [0,"bBigStepBack",	BP_ACTION_BIG_STEP_BACK,	2501, 2502],
                  [0,"bNextAlbum",	BP_ACTION_NEXT_ALBUM,		2601, 2602],
                  [0,"bPrevAlbum",	BP_ACTION_PREV_ALBUM,		2701, 2702],
                  [0,"bLoadPlaylist",	BP_ACTION_LOAD,			2801, 2802],
                  [0,"bSavePlaylist",	BP_ACTION_SAVE,			2901, 2902],
                  [0,"bRescan",		BP_ACTION_RESCAN,		3001, 3002],
                  [0,"bProgramMode",	BP_ACTION_PROGRAM,		3101, 3102],
                  [0,"bNormalMode",	BP_ACTION_NORMAL,		3201, 3202],
                  [0,"bRepeat",		BP_ACTION_REPEAT,		3301, 3302],
                  [0,"bRepeatOne",	BP_ACTION_REPEAT_ONE,		3401, 3402],
                  [0,"bAlbumMode",	BP_ACTION_ALBUM,		3501, 3502],
                  [0,"bEnableTurnOff",	BP_ACTION_OFF_ENABLE,		3601, 3602],
                  [0,"bDisableTurnOff",	BP_ACTION_OFF_DISABLE,		3701, 3702],
                  [0,"bRepeatAB",	BP_ACTION_REPEAT_AB,		3801, 3802],
                  ["","bHotKey",	BP_ACTION_NONE	,		3901, 3902]]

#from ButtonTranslator.cpp and XBIRRemote.h
HOTKEY_MAPPING = {IR_SELECT	:"select",
                  IR_ENTER	:"enter",
                  IR_MENU	:"menu",
                  IR_BACK	:"back",
                  IR_PAUSE	:"pause",
                  IR_STOP	:"stop",
                  IR_NEXT	:"skipplus",
                  IR_PREV	:"skipminus",
                  IR_FORWARD	:"forward",
                  IR_REWIND	:"reverse",
                  IR_PLAY	:"play",
                  IR_0		:"zero",
                  IR_1		:"one",
                  IR_2		:"two",
                  IR_3		:"three",
                  IR_4		:"four",
                  IR_5		:"five",
                  IR_6		:"six",
                  IR_7		:"seven",
                  IR_8		:"eight",
                  IR_9		:"nine",
                  #rest:
                  IR_LEFT	:"left",
                  IR_RIGHT	:"right",
                  IR_UP		:"up",
                  IR_DOWN	:"down",
                  IR_INFO	:"info",
                  IR_DISPLAY	:"display",#xbox
                  IR_TITLE	:"title",#guide
                  IR_POWER	:"power",
                  IR_MY_TV	:"mytv",
                  IR_MY_MUSIC	:"mymusic",
                  IR_MY_PICTURES:"mypictures",
                  IR_MY_VIDEOS	:"myvideo",
                  IR_RECORD	:"record",
                  IR_START	:"start",
                  IR_VOL_PLUS	:"volumeplus",
                  IR_VOL_MINUS	:"volumeminus",
                  IR_CH_PLUS	:"channelplus",#pageplus
                  IR_CH_MINUS	:"channelminus",#pageminus
                  IR_MUTE	:"mute",
                  IR_RECORDED_TV:"recordedtv",
                  IR_LIVE_TV	:"livetv",
                  IR_STAR	:"star",
                  IR_HASH	:"hash",
                  IR_CLEAR	:"clear",
                  IR_TXT	:"teletext",
                  IR_RED	:"red",
                  IR_GREEN	:"green",
                  IR_YELLOW	:"yellow",
                  IR_BLUE	:"blue",
                  IR_SUBTITLE	:"subtitle",
                  IR_LANGUAGE	:"language"}

NUMBER_ACTION_NONE = 0
NUMBER_ACTION_SAVE = 1
NUMBER_ACTION_LOAD = 2
NUMBER_ACTION_BC_ALBUM = 3
NUMBER_ACTION_BC_TRACK = 4

LOOP_DISABLED = 0
LOOP_ALL = 1
LOOP_ONE = 2

PREV_THRESHOLD = 3 #sec, within this pressing 'prev' jump to previous track, above this to the beginning of current track
SKIP_SMALL = 30 #seconds
SKIP_BIG   = 300 #5 min
SKIP_TRACKS = 10 #number of tracks to jump in program mode pressing pg up/down

XBMC_DIR = xbmc.translatePath('special://xbmc/')
HOME_USERDATA_DIR = xbmc.translatePath('special://masterprofile/')
TEMP_DIR = xbmc.translatePath('special://temp/')
SOURCES_FILE = xbmc.translatePath( os.path.join(HOME_USERDATA_DIR, 'sources.xml') )
KEYMAP_DIR = xbmc.translatePath( os.path.join(HOME_USERDATA_DIR, 'keymaps') )
KEYMAP_FILE = "blindplayerkeymap.xml"

HOME_SCRIPT_DIR = __cwd__

AV_NONE = -1
AV_MUSIC = 0
AV_VIDEO = 1
BlindPlayerMode = AV_MUSIC
BlindPlayerAutoPowerOff = False

PATTERNS = [['*.mp3','*.wav','*.dts','*.ac3','*.wma','*.aac','*.mpa','*.ra','*.wma','*.flac'],
            ['*.avi','*.rmvb','*.divx','*.xvid','*.ts','*.flv','*.mov','*.mp4','*.mpg','*.mpeg','*.rm','*.swf','*.vob','*.wmv','*.mkv','*.264','*.m2t','*.m2ts','*.m2v']]
AV_NAMES = ["music", "video"]

SCAN_FILE = [xbmc.translatePath( os.path.join(TEMP_DIR, 'blindplayer.music') ),
             xbmc.translatePath( os.path.join(TEMP_DIR, 'blindplayer.video') )]
AV_PLAYLIST = [xbmc.PLAYLIST_MUSIC, xbmc.PLAYLIST_VIDEO]

PID_FILE = xbmc.translatePath( os.path.join(TEMP_DIR, "%s.lock" % __scriptid__) )

CENTER_X  = 2 #text label alignment code

# This is a workaround for not automounted cdrom
def MountCDROM():
    os.system("df -h /dev/cdrom && mount /media/cdrom")

class NoIdle:
    closing = False
    idleTime = 30

    def __init__(self):
        self.l = Lock()
        if XBMCClient:
            self.xbmc = XBMCClient(__scriptname__, "", ip="127.0.0.1")
            self.xbmc.connect()
        else:
            self.screensaver = xbmc.executehttpapi( "GetGUISetting(3;screensaver.mode)" ).replace( "<li>", "" )
            xbmc.executehttpapi( "SetGUISetting(3,screensaver.mode,None)" )
            #The repeat functionality could be used so the Timer would not be needed.
            #As we want to send events only if player is playing we use task.
            #xbmc.executehttpapi("KeyRepeat(%d)" % (self.idleTime * 1000))
            #xbmc.executehttpapi("SendKey(F11B)") #xbmc.executehttpapi("SendKey(EFFF;0;0)")
            xbmc.executehttpapi("KeyRepeat(0)")
        self.__schedule(self.__kick) #note: the self.t must be created here

    def __schedule(self, what):
        self.l.acquire()
        if not self.closing:
            #idle = xbmc.getGlobalIdleTime()
            #print "idle: %d" % idle
            self.t = Timer(self.idleTime, what)
            self.t.start()
        self.l.release()

    def __kick(self):
        if xbmc.Player().isPlaying():
            #xbmc.enableNavSounds(False)
            if XBMCClient:
                self.xbmc.send_keyboard_button("backspace")
                time.sleep(0.2)
                self.xbmc.release_button()
            else:
                xbmc.executehttpapi("SendKey(F108)") #backspace
                pass
            #xbmc.enableNavSounds(False)
        self.__schedule(self.__kick)

    def close(self):
        self.l.acquire()
        self.closing = True
        self.t.cancel()
        self.l.release()
        self.t.join()
        if XBMCClient:
            self.xbmc.close()
        else:
            xbmc.executehttpapi("KeyRepeat(0)")
            xbmc.executehttpapi( "SetGUISetting(3,screensaver.mode,%s)" % self.screensaver )
        del self.l

# http://www.experts-exchange.com/Programming/Languages/Scripting/Python/Q_22822225.html
def sortedWalk(path, patterns, symlinkDirs = False):
    from os.path import isdir, islink, join
    # Get the names from inside the path. Get directories and the files
    # into separate lists and then sort them.
    try:
        #print path
        names = os.listdir(path)
    except:
        return
    dirs = []
    nondirs = []
    for name in names:
        f = join(path, name)
        if isdir(f):
            #do not follow symlinked dirs
            if symlinkDirs or not islink(f):
                dirs.append(name)
        else:
            for p in patterns:
                if fnmatch.fnmatch(name, p):
                    nondirs.append(name)
    dirs.sort()
    nondirs.sort()

    # List the files in this directory first (as a generator).
    for name in nondirs:
        yield os.path.abspath(join(path, name))
        #yield join(path, name) #this is to return string instead tuple

    # Generate the content of the sub directories recursively.
    for subdir in dirs:
        for fname in sortedWalk(join(path, subdir), patterns):
            yield fname
    pass

def GetSources(fname, name):
    doc = minidom.parse(fname)
    if doc:
        rootNode = doc.documentElement
        for music in rootNode.getElementsByTagName(name):
            for path in music.getElementsByTagName("path"):
                if path.childNodes[0].nodeType == Node.TEXT_NODE:
                    #yield path.childNodes[0].data
                    yield path.childNodes[0].data.encode() # otherwise it gives unicode path that is problematic for  os.listdir()

def MediaScan(paths, patterns, file, rescan=False):
    if (not os.path.exists(file) or rescan):
        if sys.platform == 'linux2':
            MountCDROM()
        # create new scan
        try:
            f = open(file, 'w')
            for path in paths:
                try:
                    for fname in sortedWalk(path, patterns):
                        f.write(fname + '\n')
                except OSError:
                    pass
            f.close()
        except IOError, e:
            debuglog("Media scan %s" % e)
            return False
        except:
            return False
    return True

L_NORM = 0 #all tracks in album are on normal playback list
L_PROG = 2 #all tracks in album are on program playback list
L_BOTH = 1 #album tracks are on both normal and program lists

class Album:
    albums = []
    tracks = []
    pos = []
    npAlbums = []
    npTracks = []
    program = []

    def IsValidPos(self, pos):
        if pos and self.albums:
            if len(pos) == 2:
                a = pos[0]
                t = pos[1]
                if a and a <= len(self.albums):
                    if self.tracks[a-1]:
                        return (t and t <= len(self.tracks[a-1]))
        return False

    def Pos(self, pos = []):
        if self.IsValidPos(pos):
            self.pos = pos
            # move to new pos
            #print "Navigate [%d-%d]: \"%s\"\n( %s )" % (pos[0], pos[1], self.tracks[pos[0]-1][pos[1]-1], self.albums[pos[0]-1])
        return self.pos

    def AlbumName(self, a = 0):
        global IndexError
        if not a:
            a = self.pos[0]
        try:
            return self.albums[a-1]
        except IndexError:
            return ''

    def TrackName(self, pos = []):
        global IndexError
        if not pos:
            pos = self.pos
        try:
            return self.tracks[pos[0]-1][pos[1]-1]
        except IndexError:
            return ''

    def AlbumTrackName(self, pos = []):
        global IndexError
        if not pos or len(pos) < 2:
            pos = self.pos
        try:
            return os.path.join(self.albums[pos[0]-1], self.tracks[pos[0]-1][pos[1]-1])
        except IndexError:
            return ''

    def FindPos(self, name):
        global ValueError
        albumName = os.path.dirname(name)
        trackName = os.path.basename(name)
        try:
            a = self.albums.index(albumName)
            t = self.tracks[a].index(trackName)
            return [a + 1, t + 1]
        except ValueError:
            return []

    #search including current track position
    def SearchForPrevTrackWithinAlbum(self, which, a, t):
        global ValueError, IndexError
        try:
            npTrack = self.npTracks[a-1]
        except IndexError:
            return []
        pos = []
        npTrack.reverse()
        t = len(npTrack) - t
        try:
            t = npTrack.index(which, t)
            pos = [a, len(npTrack) - t]
        except (ValueError, IndexError):
            pass
        npTrack.reverse()
        return pos

    #search including current track position
    def SearchForNextTrackWithinAlbum(self, which, a, t):
        global ValueError, IndexError
        try:
            npTrack = self.npTracks[a-1]
        except IndexError:
            return []
        try:
            t = npTrack.index(which, t - 1) + 1
        except (ValueError, IndexError):
            return []
        return [a,t]

    # scan including startup position
    def __SearchForPrevAlbum(self, which, a):
        global IndexError
        for i in range(a, 0, -1):
            try:
                npAlbum = self.npAlbums[i-1]
            except IndexError:
                return 0
            if npAlbum == which or npAlbum == L_BOTH:
                #found
                return i
        return 0

    # scan including startup position
    def __SearchForNextAlbum(self, which, a):
        global IndexError
        for i in range(a-1, len(self.npAlbums)):
            try:
                npAlbum = self.npAlbums[i]
            except IndexError:
                return 0
            if npAlbum == which or npAlbum == L_BOTH:
                #found
                return i+1
        return 0

    # valid pos is expected
    def __PrevTrackProg(self, skip, loop, pos):
        global ValueError, IndexError
        nPos = []
        try:
            i = self.program.index([e-1 for e in pos])
            i -= (skip % len(self.program))
            if i < 0 and not loop:
                i = 0
            nPos = [e+1 for e in self.program[i]]
        except (ValueError, IndexError):
            pass
        return nPos

    # valid pos is expected
    def __NextTrackProg(self, skip, loop, pos):
        global ValueError, IndexError
        nPos = []
        try:
            i = self.program.index([e-1 for e in pos])
            i += skip
            if loop or i < len(self.program):
                i = i % len(self.program)
            else:
                i = -1
            nPos = [e+1 for e in self.program[i]]
        except (ValueError, IndexError):
            pass
        return nPos
        
    #which: L_NORM/L_PROG
    # For program mode its program list is used firs, if already in program list position
    def PrevTrack(self, which, thisAlbumOnly, loop, pos = []):
        if not self.IsValidPos(pos):
            pos = self.pos
        nPos = []
        if self.IsValidPos(pos):
            a = pos[0]
            t = pos[1]
            if which == L_PROG and self.npTracks[a-1][t-1] == L_PROG:
                nPos = self.__PrevTrackProg(1, loop, pos)
                if not nPos:
                    #fallback to current position
                    nPos = pos
            else:
                npAlbum = self.npAlbums[a-1]
                if thisAlbumOnly:
                    if npAlbum == which or npAlbum == L_BOTH: #if at least one track is on current list
                        nPos = self.SearchForPrevTrackWithinAlbum(which, a, t-1)
                        if not nPos: # if not found below current position
                            if loop:
                            # continue searching from the end (if loop)
                                nPos = self.SearchForPrevTrackWithinAlbum(which, a, len(self.npTracks[a-1]))
                            else:
                                # search forward for first valid track
                                nPos = self.SearchForNextTrackWithinAlbum(which, a, t)
                else:
                    if npAlbum == which or npAlbum == L_BOTH: #if at least one track is on current list
                        nPos = self.SearchForPrevTrackWithinAlbum(which, a, t-1)
                    if not nPos: # if not found below current position in current album
                        # search for previous album that has tracks on current list
                        nA = self.__SearchForPrevAlbum(which, a-1)
                        if not nA:
                            if loop:
                                #continue searching from the end
                                nA = self.__SearchForPrevAlbum(which, len(self.npAlbums))
                            else:
                                #search forward for first album with tracks from current list
                                nA = self.__SearchForNextAlbum(which, a)
                                #search for track within album
                                nPos = self.SearchForNextTrackWithinAlbum(which, nA, 1)
                                return nPos
                        if nA:
                            #continue searching from the end (current album if loop or last if not)
                            nPos = self.SearchForPrevTrackWithinAlbum(which, nA, len(self.npTracks[nA-1]))
        return nPos

    #which: L_NORM/L_PROG
    # For program mode its program list is used firs, if already in program list position 
    def NextTrack(self, which, thisAlbumOnly, loop, pos = [], omitThis = True):
        if not self.IsValidPos(pos):
            pos = self.pos
        nPos = []
        if self.IsValidPos(pos):
            a = pos[0]
            t = pos[1]
            if which == L_PROG and self.npTracks[a-1][t-1] == L_PROG:
                if omitThis == False:
                    #fallback to current position
                    nPos = pos
                else:
                    nPos = self.__NextTrackProg(1, loop, pos)
                    if not nPos:
                        #fallback to current position
                        nPos = pos
            else:
                npAlbum = self.npAlbums[a-1]
                if thisAlbumOnly:
                    if npAlbum == which or npAlbum == L_BOTH: #if at least one track is on current list
                        nPos = self.SearchForNextTrackWithinAlbum(which, a, t+int(omitThis))
                        if not nPos: # if not found above current position
                            if loop:
                                # continue searching from the beginning (if loop)
                                nPos = self.SearchForNextTrackWithinAlbum(which, a, 1)
                            else:
                                # search backward for first valid track
                                nPos = self.SearchForPrevTrackWithinAlbum(which, a, t)
                else:
                    if npAlbum == which or npAlbum == L_BOTH: #if at least one track is on current list
                        nPos = self.SearchForNextTrackWithinAlbum(which, a, t+int(omitThis))
                    if not nPos: # if not found above current position in current album
                        # search for next album that has tracks on current list
                        nA = self.__SearchForNextAlbum(which, a+1)
                        if not nA:
                            if loop:
                                #continue searching from the beginning
                                nA = self.__SearchForNextAlbum(which, 1)
                            else:
                                #search backward for first album with tracks from current list
                                nA = self.__SearchForPrevAlbum(which, a)
                                if nA:
                                    #search for track within album
                                    nPos = self.SearchForPrevTrackWithinAlbum(which, nA, len(self.npTracks[nA-1]))
                                return nPos
                        #continue searching from the end (current album if loop or last if not)
                        nPos = self.SearchForNextTrackWithinAlbum(which, nA, 1)
        return nPos

    # if the track is the first in album in this mode it will go to the previous album
    # otherwise it will go to the begginning of the current album
    # For program mode it jumops SKIP_TRACKS tracks backward, if already in program list position
    def PrevAlbum(self, which, loop, pos = []):
        global ValueError, IndexError
        if not self.IsValidPos(pos):
            pos = self.pos
        nPos = []
        if self.IsValidPos(pos):
            a = pos[0]
            t = pos[1]
            if which == L_PROG and self.npTracks[a-1][t-1] == L_PROG:
                nPos = self.__PrevTrackProg(SKIP_TRACKS, loop, pos)
                if not nPos:
                    #fallback to current position
                    nPos = pos
            else:
                if t == 1:
                    a = a - 1
                else:
                    npTrack = self.npTracks[a-1]
                    npTrack.reverse()
                    t = len(npTrack) - t
                    try:
                        npTrack.index(which, len(npTrack) + 1 - t)
                        a = a - 1
                    except (ValueError, IndexError):
                        pass
                    npTrack.reverse()
                nA = self.__SearchForPrevAlbum(which, a)
                if not nA:
                    if loop:
                        nA = self.__SearchForPrevAlbum(which, len(self.npAlbums))
                    else:
                        nA = self.__SearchForNextAlbum(which, a)
                if nA:
                    nPos = self.SearchForNextTrackWithinAlbum(which, nA, 1)
        return nPos


    # if pos is given it will search including given album,
    # if not given, search from next album that follows current album
    # For program mode it jumps SKIP_TRACKS tracks forward, if already in program list position
    def NextAlbum(self, which, loop, pos = []):
        offset = 0
        if not self.IsValidPos(pos):
            pos = self.pos
            offset = 1
        nPos = []
        if self.IsValidPos(pos):
            a = pos[0]
            t = pos[1]
            if which == L_PROG and self.npTracks[a-1][t-1] == L_PROG:
                nPos = self.__NextTrackProg(SKIP_TRACKS, loop, pos)
                if not nPos:
                    #fallback to current position
                    nPos = pos
            else:
                a += offset
                nA = self.__SearchForNextAlbum(which, a)
                if not nA:
                    if loop:
                        nA = self.__SearchForNextAlbum(which, 1)
                    else:
                        nA = self.__SearchForPrevAlbum(which, a-1)
                if nA:
                    nPos = self.SearchForNextTrackWithinAlbum(which, nA, 1)
        return nPos

    def ProgramTrack(self, n):
        if n > 0 and n < len(self.program):
            pos = [e+1 for e in self.program[n-1]]
        else:
            pos = []
        return pos

    #toWhich: L_NORM/L_PROG
    def MoveTrack(self, source, pos = []):
        global ValueError
        if not self.IsValidPos(pos):
            pos = self.pos
        if self.IsValidPos(pos):
            a = pos[0] - 1
            t = pos[1] - 1
            if source == L_NORM:
                destination = L_PROG
                self.program.append([a,t])
            else:
                destination = L_NORM
                try:
                    self.program.remove([a,t])
                except ValueError:
                    # the list is broken
                    pass
            self.npTracks[a][t] = destination
            if self.npTracks[a].count(source) == 0:
                self.npAlbums[a] = destination
            else:
                self.npAlbums[a] = L_BOTH

    def NumOfAlbum(self):
        return len(self.albums)

    def NumOfTracks(self, albumNr):
        global IndexError
        try:
            return len(self.tracks[albumNr - 1])
        except IndexError:
            return 0

    def Normalize(self):
        self.program[:] = []
        for a in range(len(self.npAlbums)):
            self.npAlbums[a] = L_NORM
            for t in range(len(self.npTracks[a])):
                self.npTracks[a][t] = L_NORM

    def OpenGeneral(self, fname):
        global IOError
        self.albums[:] = []
        self.tracks[:] = []
        self.npAlbums[:] = [] #empty it
        self.npTracks[:] = [] #empty it
        self.program[:] = [] #empty it
        try:
            f = open(fname, 'r')
            withinAlbumName = ''
            for track in f.readlines():
                track = track.strip('\n')
                albumName = os.path.dirname(track)
                trackName = os.path.basename(track)
                if albumName == withinAlbumName:
                    self.tracks[-1].append(trackName)
                    self.npTracks[-1].append(L_NORM)
                else:
                    withinAlbumName = albumName
                    self.albums.append(albumName)
                    self.tracks.append([trackName])
                    self.npAlbums.append(L_NORM)
                    self.npTracks.append([L_NORM])
            f.close()
        except IOError, e:
            debuglog("Open %s" % e)

    def OpenNormal(self, fname):
        global ValueError, IOError
        for a in range(len(self.npAlbums)):
            self.npAlbums[a] = L_PROG
            for t in range(len(self.npTracks[a])):
                self.npTracks[a][t] = L_PROG
                self.program.append([a,t])
        try:
            for l in f.readlines():
                l = l.strip('\n')
                pos = [(int(e) + 1) for e in l.split(',')]
                if self.IsValidPos(pos):
                    a = pos[0] - 1
                    t = pos[1] - 1
                    if self.npTracks[a][t] == L_PROG:
                        self.npTracks[a][t] = L_NORM #assign track to normal list
                        try: # if at least one track is still assigned to program list
                            self.npTracks[a].index(L_PROG)
                            self.npAlbums[a] = L_BOTH #assign album to both lists
                        except:
                            self.npAlbums[a] = L_NORM #assign album to normal list only
                        try:
                            self.program.remove([a,t])
                        except ValueError:
                            # the list is broken
                            pass                            
            f.close()
        except IOError, e:
            debuglog("Open %s" % e)

    def OpenProgram(self, fname):
        global IOError
        self.program[:] = [] #empty it
        for a in range(len(self.npAlbums)):
            self.npAlbums[a] = L_NORM
            for t in range(len(self.npTracks[a])):
                self.npTracks[a][t] = L_NORM
        try:
            f = open(fname, 'r')
            for l in f.readlines():
                l = l.strip('\n')
                pos = [(int(e) + 1) for e in l.split(',')]
                if self.IsValidPos(pos):
                    a = pos[0] - 1
                    t = pos[1] - 1
                    if self.npTracks[a][t] == L_NORM:
                        self.npTracks[a][t] = L_PROG #assign track to program list
                        try: # if at least one track is still assigned to normal list
                            self.npTracks[a].index(L_NORM)
                            self.npAlbums[a] = L_BOTH #assign album to both lists
                        except:
                            self.npAlbums[a] = L_PROG #assign album to program list only
                        self.program.append([a,t]) 
            f.close()
        except IOError, e:
            debuglog("Open %s" % e)

    def Open(self, fname, destination = L_BOTH):
        try:
            if destination == L_PROG:
                self.OpenProgram(fname)
            elif destination == L_NORM:
                self.OpenNormal(fname)
            else:
                self.OpenGeneral(fname)
        except:
            return False
        return True

    def ShortPlaylistNormal(self):
        for a in range(len(self.npAlbums)):
            if self.npAlbums[a] != L_PROG:
                for t in range(len(self.npTracks[a])):
                    if self.npTracks[a][t] == L_NORM:
                        yield "%d,%d" % (a,t)

    def ShortPlaylistProgram(self):
        for e in self.program:
            yield "%s" % (','.join(str(n) for n in e))
    
    def Save(self, fname, destination = L_BOTH):
        global IOError
        if destination == L_PROG:
            pL = self.ShortPlaylistProgram()
        elif destination == L_NORM:
            pL = self.ShortPlaylistNormal()
        else:
            pL = self.PlaylistGeneral()
        try:
            f = open(fname, 'w')
            f.writelines("%s\n" % e for e in pL)
            f.close()
        except IOError, e:
            debuglog("Save %s" % e)
            return False
        except:
            return False
        return True

    def PlaylistGeneral(self):
        for a, albumName in enumerate(self.albums):
            for trackName in self.tracks[a]:
                yield os.path.join(albumName, trackName)

    def PlaylistNormalA(self, a):
        global ValueError
        a = a-1
        if self.npAlbums[a] != L_PROG:
            t = -1
            try:
                while 1:
                    t = self.npTracks[a].index(L_NORM, t + 1)
                    yield os.path.join(self.albums[a], self.tracks[a][t])
            except ValueError:
                pass

    def PlaylistNormal(self):
        global ValueError
        for a, albumName in enumerate(self.albums):
            if self.npAlbums[a] != L_PROG:
                t = -1
                try:
                    while 1:
                        t = self.npTracks[a].index(L_NORM, t + 1)
                        yield os.path.join(albumName, self.tracks[a][t])
                except ValueError:
                    pass

    def PlaylistProgram(self):
        for pos in self.program:
            a = pos[0]
            t = pos[1]
            yield os.path.join(self.albums[a], self.tracks[a][t])

    def Playlist(self, a, which = L_BOTH):
        if which == L_PROG:
            f = self.PlaylistProgram()
        elif which == L_NORM:
            if a and a <= len(self.albums):
                f = self.PlaylistNormalA(a)
            else:
                f = self.PlaylistNormal()
        else:
            f = self.PlaylistGeneral(a)
        for g in f:
            yield g

    #def Content(self):
    #    print albums

AB_REPEATER_OFF = 0
AB_REPEATER_A = 1
AB_REPEATER_AB = 2
class ABRepeater:
    timeout = 1.0
    closing = False
    t = None

    def __init__ (self, player, callback=None):
        self.l = Lock()
        self.player = player
        self.timeA = None
        self.timeB = None
        self.callback = callback

    def __schedule(self):
        self.l.acquire()
        if not self.closing:
            self.t = Timer(self.timeout, self.__OnTimer)
            self.t.start()
        self.l.release()

    def Status(self):
        if self.timeA:
            if self.timeB:
                return AB_REPEATER_AB
            else:
                return AB_REPEATER_A
        else:
            return AB_REPEATER_OFF

    def __getTime(self):
        marker = None
        if self.player.isPlaying():
            try:
                marker = self.player.getTime()
            except:
                pass
        return marker

    def __Off(self, cancel=False):
        if cancel == True and self.t:
            self.l.acquire()
            self.closing = True
            self.t.cancel()
            self.l.release()
            self.t.join()
            self.t = None
            self.closing = False
        debuglog("Timer: OFF")
        if self.timeA != None:
            self.callback(AB_REPEATER_OFF)
        self.timeA = None
        self.timeB = None
    
    def Marker(self, cancel=False):
        if cancel == True or not self.player.isPlaying():
            self.__Off(True)
        elif self.timeA:
            if self.timeB:
                self.__Off(True)
            else:
                self.timeB = self.__getTime()
                if self.timeB == None or self.timeB <= self.timeA:
                    self.__Off()
                else:
                    self.__schedule()
                    self.callback(AB_REPEATER_AB)
                    debuglog("TimerA-B: %d %d" % (self.timeA, self.timeB))
        else:
            self.timeA = self.__getTime()
            if self.timeA == None:
                self.__Off()
            else:
                self.callback(AB_REPEATER_A)
                debuglog("TimerA-: %d" % self.timeA)
        return self.Status()

    def __OnTimer(self):
        position = self.__getTime()
        if position == None:
            self.__Off()
        else:
            if position >= self.timeB:
                try:
                    self.player.seekTime(self.timeA)
                except:
                    self.__Off()
                    return
            self.__schedule()

    def close(self):
        self.__Off(True)
        del self.l

class ButtonCollector:
    callback = None
    number = 0
    t = None
    pending = False

    def __init__ (self, callback, timeout = 0.9):
        self.timeout = timeout
        self.callback = callback

    def Press(self, nr):
        if self.t:
            self.t.cancel()
            self.t.join()
        if nr >= 0 and nr <= 9:
            self.pending = True
            self.number = 10 * self.number + nr
            self.t = Timer(self.timeout, self.__OnTimer)
            self.t.start()
        else:
            self.number = 0
            self.pending = False

    def __OnTimer(self):
        if self.callback:
            self.callback(self.number)
        self.number = 0
        self.pending = False

    def active(self):
        return self.pending

    def cancel(self):
        self.number = 0
        if self.t:
            self.t.cancel()
            self.t.join()

    def close(self):
        if self.t:
            self.t.cancel()
            self.t.join()

class CallbackPlayer(xbmc.Player):
    onPlayBackStartedCallback = None
    onPlayBackEndedCallback = None
    onPlayBackStoppedCallback = None
    onPlayBackABCallback = None
    paused = False # not thread safe among other APIs
    repeater = None

    def __init__ (self):
        self.lockClosing  = Lock()
        self.lock_onPlayBackStartedCallback  = Lock()
        self.lock_onPlayBackEndedCallback  = Lock()
        self.lock_onPlayBackStoppedCallback  = Lock()
        xbmc.Player.__init__(self)
        self.lock_onPlayBackABCallback  = Lock()
        self.repeater = ABRepeater(self, self.repeaterCallback)

    def play(self, *args, **kw): # not thread safe with other APIs
        self.paused = False
        xbmc.Player.play(self, *args, **kw)
        
    def stop(self, *args): # not thread safe with other APIs
        self.paused = False
        xbmc.Player.stop(self, *args)

    def pause(self, *args): # not thread safe with other APIs
        self.paused = not self.paused
        xbmc.Player.pause(self, *args)

    def resume(self): # not thread safe with other APIs
        if self.paused:
            self.paused = False
            xbmc.Player.pause(self)

    def playnext(self, *args): # not thread safe with other APIs
        self.paused = False
        xbmc.Player.playnext(self, *args)

    def playprevious(self, *args): # not thread safe with other APIs
        self.paused = False
        xbmc.Player.playprevious(self, *args)

    def playselected(self, *args): # not thread safe with other APIs
        self.paused = False
        xbmc.Player.playselected(self, *args)
                        
    def RegisterOnPlayBackStartedCallback(self, callback):
        if not self.lockClosing.acquire(False):
            return
        self.repeater.Marker(True)
        self.onPlayBackStartedCallback = callback
        self.lockClosing.release()

    def RegisterOnPlayBackEndedCallback(self, callback):
        if not self.lockClosing.acquire(False):
            return
        self.repeater.Marker(True)
        self.onPlayBackEndedCallback = callback
        self.lockClosing.release()

    def RegisterOnPlayBackStoppedCallback(self, callback):
        if not self.lockClosing.acquire(False):
            return
        self.repeater.Marker(True)
        self.onPlayBackStoppedCallback = callback
        self.lockClosing.release()

    def RegisterOnPlayBackABCallback(self, callback):
        if not self.lockClosing.acquire(False):
            return
        self.onPlayBackABCallback = callback
        self.lockClosing.release()

    def onPlayBackStarted(self):
        self.repeater.Marker(True)
        if self.onPlayBackStartedCallback:
            if not self.lock_onPlayBackStartedCallback.acquire(False):
                return
            xbmc.sleep(300) #It is a bug that this wait is needed to get the just started track name, otherwise old one is reported
            self.onPlayBackStartedCallback()
            self.lock_onPlayBackStartedCallback.release()
        #print "***CallbackPlayer: onPlayBackStarted()"

    def onPlayBackEnded(self):
        self.repeater.Marker(True)
        if self.onPlayBackEndedCallback:
            if not self.lock_onPlayBackEndedCallback.acquire(False):
                return
            self.onPlayBackEndedCallback()
            self.lock_onPlayBackEndedCallback.release()
        #print "***CallbackPlayer: onPlayBackEnded()"

    def onPlayBackStopped(self):
        self.repeater.Marker(True)
        if self.onPlayBackStoppedCallback:
            if not self.lock_onPlayBackStoppedCallback.acquire(False):
                return
            self.onPlayBackStoppedCallback()
            self.lock_onPlayBackStoppedCallback.release()
        #print "***CallbackPlayer: onPlayBackStopped()"

    def onPlayBackPaused(self):
        #print "***CallbackPlayer: onPlayBackPaused()"
        pass

    def onPlayBackResumed(self):
        #print "***CallbackPlayer: onPlayBackResumed()"
        pass
        
    def disableCallbacks(self):
        self.lockClosing.acquire()
        # No new callback functions will be assigned at this point
        onPlayBackStartedCallback = None
        onPlayBackEndedCallback = None
        onPlayBackStoppedCallback = None
        # No more callback functions will be called
        # Synchronize in case the callbacks are separate threads
        self.lock_onPlayBackStartedCallback.acquire()
        self.lock_onPlayBackEndedCallback.acquire()
        self.lock_onPlayBackStoppedCallback.acquire()
        #At this point there are no more active callback functions

    def repeaterCallback(self, status):
        if self.onPlayBackABCallback:
            if not self.lock_onPlayBackABCallback.acquire(False):
                return
            self.onPlayBackABCallback(status)
            self.lock_onPlayBackABCallback.release()
        #print "***CallbackPlayer: onPlayBackStopped()"
        
    def repeatAB(self, cancel=False):
        return self.repeater.Marker(cancel)

    def close(self):
        self.repeater.close()
        del self.repeater
    
def getSettingInt(setting, val=0):
  try:
     val = int(__addon__.getSetting(setting))
  except ValueError:
     pass
  return val

def getSettingStr(setting, val=""):
  try:
     val = str(__addon__.getSetting(setting))
  except ValueError:
     pass
  return val


class GUI( xbmcgui.WindowXMLDialog ):
    A = None
    player = None
    playlist = None
    mode = L_NORM
    loop = LOOP_DISABLED
    thisAlbumOnly = False
    movePos = []
    onNumberAction = [NUMBER_ACTION_NONE,NUMBER_ACTION_NONE]
    avMode = AV_NONE
    I = None
    BC = None
    pos = []
    setup = False
    setupSequence = BP_ACTION_NONE
    repeatAB = AB_REPEATER_OFF
    powerOff = False

    def __init__( self, *args, **kwargs ):
      self.lock_onAction = Lock()
      pass

    def onInit( self ):
      global BlindPlayerMode
      if self.avMode == AV_NONE:
        self.avMode = BlindPlayerMode if BlindPlayerMode < len(AV_NAMES) else AV_MUSIC
        self.lock_onAction.acquire()
        self.Setup(False)
        self.LoadButtons()
        self.I = NoIdle()
        self.InfoText(__language__(30115), __language__(30114))
        paths = list(p for p in GetSources(SOURCES_FILE, AV_NAMES[self.avMode]))
        if not MediaScan(paths, PATTERNS[self.avMode], SCAN_FILE[self.avMode]):
            self.close()
            self.I.close()
            self.lock_onAction.release()
            return False
        self.A = Album()
        if not self.A.Open(SCAN_FILE[self.avMode]):
            self.close()
            self.I.close()
            self.lock_onAction.release()
            return False
        self.InfoText()
        self.playerLock = Lock()
        self.playlist = xbmc.PlayList(AV_PLAYLIST[self.avMode])
        self.ComposeNewPlaylist()
        pos = self.A.NextAlbum(self.mode, False, [1,1])
        self.A.Pos(pos)
        self.player = CallbackPlayer() #remember to set volume=100% to play with DTS
        xbmc.executebuiltin('XBMC.SetVolume(100)')
        self.player.RegisterOnPlayBackStartedCallback(self.PlaybackStartedCallback)
        self.player.RegisterOnPlayBackEndedCallback(self.PlaybackEndedCallback)
        self.player.RegisterOnPlayBackABCallback(self.PlaybackABCallback)
        self.BC = ButtonCollector(self.ButtonCollectorCallback)
        if self.player.isPlaying():
                # make sure it plays this playlist from beginning
            self.player.play(self.playlist, None, True)
        else:
            xbmc.playSFX(xbmc.translatePath( os.path.join(XBMC_DIR, 'addons', 'skin.confluence', 'sounds', 'notify.wav') ))
        self.NavigationInfo(True)
        self.lock_onAction.release()
      pass

    def onFocus( self, controlId ):
       self.controlId = controlId
       pass

    def InfoText(self, text1 = "", text2 = ""):
        self.getControl(1101).setLabel(text1)
        self.getControl(1102).setLabel(text2)

    def StatusText(self):
        if self.setup == True:
           text = __language__(30100)
        else:
	 if self.mode == L_NORM:
	   if self.thisAlbumOnly == True:
	      text = __language__(30101) + "\n"
	   else:
	      text = __language__(30102) + "\n"
	 else:
	   text = __language__(30103) + "\n"
	 if self.repeatAB == AB_REPEATER_A:
	   text += __language__(30117) + "\n"
	 elif self.repeatAB == AB_REPEATER_AB:
	   text += __language__(30118) + "\n"
	 elif self.loop == LOOP_ONE:
	   text += __language__(30104) + "\n"
	 elif self.loop == LOOP_ALL:
	   text += __language__(30105) + "\n"
	 else:
	   text += __language__(30106) + "\n"
	 if self.powerOff == True:
	   text += __language__(30107)
	self.getControl(999).setLabel(text)

    def Setup(self, on = True):
        if on == True:
           self.getControl(1100).setVisible(False)
           self.getControl(2100).setVisible(True)
           self.setFocusId(2201)
        else:
           self.getControl(2100).setVisible(False)
           self.getControl(1100).setVisible(True)
        self.setup = on
        self.StatusText()

    def NavigationInfo(self, refresh = False):
        pos = self.A.Pos()
        if self.pos != pos and not self.player.isPlaying():
            self.pos = pos
            refresh = True
        if pos and refresh:
            self.InfoText("%s [%d-%d]: %s" % (__language__(30116), pos[0], pos[1], self.A.TrackName().decode('utf-8')), "%s" % self.A.AlbumName().decode('utf-8'))

    def ButtonCollectorCallback(self, number):
        self.playerLock.acquire()
        pos = self.A.Pos()
        if pos and number > 0:
            option = self.onNumberAction[1]
            if option == NUMBER_ACTION_BC_ALBUM and self.mode != L_PROG:
                pos = self.A.SearchForNextTrackWithinAlbum(self.mode, number, 1)
            elif option == NUMBER_ACTION_BC_TRACK:
                if self.mode == L_PROG:
                    pos = self.A.ProgramTrack(number)
                else:
                    pos = self.A.SearchForNextTrackWithinAlbum(self.mode, pos[0], number)
            else:
                pos = []
            if pos:
                self.movePos = []
                self.A.Pos(pos)
                i = self.PlayPos(pos)
                if i >= 0:
                    if not self.player.isPlaying():
                        self.player.play(self.playlist, None, True)
                        if i > 0:
                            self.player.playselected(i)
                        if self.loop == LOOP_ONE:
                            xbmc.executebuiltin("xbmc.playercontrol(repeatone)")
                        elif self.loop == LOOP_ALL:
                            xbmc.executebuiltin("xbmc.playercontrol(repeatall)")
                    else:
                        self.player.playselected(i)
                self.player.resume()
        self.playerLock.release()

    def PlaybackStartedCallback(self):
        self.playerLock.acquire()
        try:
            nowPlaying = self.player.getPlayingFile()
            pos = self.A.FindPos(nowPlaying)
            self.pos = self.A.Pos(pos)
            self.InfoText("[%d-%d]: %s" % (pos[0], pos[1], os.path.basename(nowPlaying)), "%s" % os.path.dirname(nowPlaying))
            debuglog("Playing: \"%s\"\n( %s )" % (os.path.basename(nowPlaying), os.path.dirname(nowPlaying)))
        except:
            pass
        self.playerLock.release()

    def PlaybackFinished(self):
        if self.thisAlbumOnly:
            pos = self.A.NextAlbum(self.mode, False)
        elif self.mode == L_PROG:
            pos = self.A.ProgramTrack(1)
        else:
            pos = self.A.NextAlbum(self.mode, False, [1,1])
        self.A.Pos(pos)
        self.NavigationInfo(True)

    def ContinueFromBeginning(self):
        self.movePos = []
        self.PlaybackFinished()
        isPlaying = self.player.isPlaying()
        if isPlaying:
            i = self.PlayPos(self.A.Pos())
            if i >= 0:
                self.player.playselected(i)
            self.player.resume()

    def PlaybackEndedCallback(self):
        self.playerLock.acquire()
        if self.loop == LOOP_DISABLED:
            self.PlaybackFinished()
        self.playerLock.release()
        if self.powerOff:
            Timer(1, self.__exit).start()

    def PlaybackABCallback(self, status):
        if self.repeatAB != status:
            self.repeatAB = status
            self.StatusText()

    def ComposeNewPlaylist(self, a = 0):
        self.playlist.clear()
        for item in self.A.Playlist(a, self.mode):
            self.playlist.add(item)

    def PrintPlaylist(self):
        for i in range(0, self.playlist.size()):
            listItem = self.playlist[i]
            itemName = listItem.getfilename()
            duration = listItem.getduration()
            debuglog("item #%d: (%ds)%s" % (i, duration, itemName))

    def PlayPos(self, pos):
        if pos:
            trackName = self.A.AlbumTrackName(pos)
            for i in range(0, self.playlist.size()):
                listItem = self.playlist[i]
                itemName = listItem.getfilename()
                if itemName == trackName:
                    return i
        return -1

    def LoadButtons(self):
        for b in BUTTON_MAPPING:
           status = True
           if b[4] == 3902: #HotKey
               b[0] = getSettingStr(b[1])
               if b[0] == "":
                  status = False
           else:
               b[0] = getSettingInt(b[1])
               if b[0] == 0:
                  status = False
           if status == False:
              self.getControl(b[4]).setLabel("")
              self.getControl(b[3]).setSelected(False)
           else:
              self.getControl(b[4]).setLabel(str(b[0]))
              self.getControl(b[3]).setSelected(True)
           debuglog("Button: [%s] code: [%s]" % (b[1], b[0]))

    def AssignHotKey(self, buttonCode):
          b = BUTTON_MAPPING[[g[4] for g in BUTTON_MAPPING].index(3902)]
          if buttonCode == 0:
             if os.path.isfile(xbmc.translatePath( os.path.join(KEYMAP_DIR, KEYMAP_FILE) )):
                 choice = xbmcgui.Dialog().yesno('Hot Key', "Do you want to remove the hot key?")
                 if choice == True:
                     try:
                         os.remove(xbmc.translatePath( os.path.join(KEYMAP_DIR, KEYMAP_FILE) ))
                         b[0] = ""
                         __addon__.setSetting(b[1], "")
                         xbmcgui.Dialog().ok('Hot Key', "A hot key has been removed.\nPlease restart XBMC to take effect.")
                     except:
                         xbmcgui.Dialog().ok('Hot Key', "Error while removing a hot key.")
          else:
              if buttonCode in HOTKEY_MAPPING:
                 choice = xbmcgui.Dialog().yesno('Hot Key', "Do you want to use <%s> as a hot key?" % HOTKEY_MAPPING[buttonCode])
                 if choice == True:
                    fsrc = open(xbmc.translatePath( os.path.join(__resource__, KEYMAP_FILE) ), 'r')
                    try:
                       fdst = open(xbmc.translatePath( os.path.join(KEYMAP_DIR, KEYMAP_FILE) ), 'w')
                       try:
                          lines = fsrc.readlines()
                          for line in lines:
                            fdst.write(re.sub('__hotkey__', HOTKEY_MAPPING[buttonCode], line))
                          b[0] = HOTKEY_MAPPING[buttonCode]
                          __addon__.setSetting(b[1], HOTKEY_MAPPING[buttonCode])
                          xbmcgui.Dialog().ok('Hot Key', "<%s> is set as the hot key.\nPlease restart XBMC to take effect." % HOTKEY_MAPPING[buttonCode])
                       finally:
                          fdst.close()
                    except:
                       xbmcgui.Dialog().ok('Hot Key', "Error setting a hot key.")
                    finally:
                       fsrc.close()
              else:
                 xbmcgui.Dialog().ok('Hot Key', "Button #%d doen not seem to be a standard key.\n To use it please create the xml file manually." % buttonCode)
          self.getControl(3902).setLabel(b[0])
          self.getControl(b[3]).setSelected(bool(b[0] != ""))
          return 

    def AssignButton(self, guiId, buttonCode):
        if guiId == 3902: #HotKey
           self.AssignHotKey(buttonCode)
           return
        if buttonCode == 0:
           return
        if buttonCode in BUTON_PERMANENT_MAPPING:
           debuglog("Button: [%s] is already associated with permanent action: [%s]" % (buttonCode, actionId))
           b = BUTTON_MAPPING[[g[4] for g in BUTTON_MAPPING].index(guiId)]
           self.getControl(guiId).setLabel("")
           self.getControl(b[3]).setSelected(False)
           __addon__.setSetting(b[1], "")
           return
        for b in BUTTON_MAPPING:
           if b[4] == guiId:
              b[0] = buttonCode
              self.getControl(guiId).setLabel(str(buttonCode))
              self.getControl(b[3]).setSelected(True)
              __addon__.setSetting(b[1], str(buttonCode))
           elif b[0] == buttonCode:
              b[0] = 0
              self.getControl(b[4]).setLabel("")
              self.getControl(b[3]).setSelected(False)
              __addon__.setSetting(b[1], "")
        return

    def MapAction(self, buttonCode):
        bpa = BP_ACTION_NONE
        try:
           bpa = BUTON_PERMANENT_MAPPING[buttonCode]
        except:
           try:
               bpa = BUTTON_MAPPING[[g[0] for g in BUTTON_MAPPING].index(buttonCode)][2]
           except:
               pass
        return bpa

    def onClick( self, controlId ):
      #debuglog("Click: [%i]" % controlId)
      pass

    def onAction(self, action):
        class BreakException(Exception):
            pass
            
        if not self.lock_onAction.acquire(False):
            return

        button = action.getButtonCode()
        actionId = self.MapAction(button)
        try:
            debuglog("Button: [%s] Action: [%s]" % (action.getButtonCode(), action.getId()))
            if self.setup == True:
               if actionId == BP_ACTION_PREVIOUS_MENU:
                  try:
                     b = BUTTON_MAPPING[[g[4] for g in BUTTON_MAPPING].index(self.controlId)]
                     if (self.controlId == 3902 and b[0] == "") or (self.controlId != 3902 and b[0] == 0):
                        self.getControl(b[4]).setLabel("")
                        self.getControl(b[3]).setSelected(False)
                     else:
                        self.getControl(b[4]).setLabel(str(b[0]))
                        self.getControl(b[3]).setSelected(True)
                     self.setFocusId(b[3])
                  except:
                     pass
                  self.Setup(False)
               else:
                 try:
                   b = BUTTON_MAPPING[[g[3] for g in BUTTON_MAPPING].index(self.controlId)]
                   if actionId == BP_ACTION_SELECT:
                     self.getControl(b[3]).setSelected(False)
                     self.setFocusId(b[4])
                     self.getControl(b[4]).setLabel("?")
                 except:
                   try:
                     b = BUTTON_MAPPING[[g[4] for g in BUTTON_MAPPING].index(self.controlId)]
                     if actionId == BP_ACTION_SELECT:
                        self.AssignButton(b[4], 0)
                     else:
                        self.AssignButton(b[4], button)
                     self.setFocusId(b[3])
                   except:
                     pass
               actionId = BP_ACTION_NONE
               raise BreakException

            
            if actionId == BP_ACTION_PREVIOUS_MENU:
               self.powerOff = False
               self.lock_onAction.release()
               self.__exit()
            elif actionId == BP_ACTION_SELECT:
                self.playerLock.acquire()
                pos = self.A.Pos()
                self.movePos = pos
                if pos:
                    isPlaying = self.player.isPlaying()
                    self.player.stop()
                    trackName = self.A.AlbumTrackName(pos)
                    self.playlist.remove(trackName)
                    self.A.MoveTrack(self.mode, pos)
                    pos = self.A.NextTrack(self.mode, self.thisAlbumOnly, self.loop)
                    pos = self.A.Pos(pos)
                    if isPlaying:
                        i = self.PlayPos(pos)
                        if i >= 0:
                            self.player.play()
                            self.player.playselected(i)
                            if self.loop == LOOP_ONE:
                                xbmc.executebuiltin("xbmc.playercontrol(repeatone)")
                            elif self.loop == LOOP_ALL:
                                xbmc.executebuiltin("xbmc.playercontrol(repeatall)")
                self.playerLock.release()
            elif actionId == BP_ACTION_PLAY:
                self.playerLock.acquire()
                self.movePos = []
                if not self.player.isPlaying():
                    i = self.PlayPos(self.A.Pos())
                    if i >= 0:
                        self.player.play(self.playlist, None, True)
                        if i > 0:
                            self.player.playselected(i)
                        if self.loop == LOOP_ONE:
                            xbmc.executebuiltin("xbmc.playercontrol(repeatone)")
                        elif self.loop == LOOP_ALL:
                            xbmc.executebuiltin("xbmc.playercontrol(repeatall)")
                self.player.resume()
                self.playerLock.release()
            elif actionId == BP_ACTION_STOP:
                self.playerLock.acquire()
                if self.player.isPlaying():
                    self.player.stop()
                self.movePos = []
                self.PlaybackFinished()
                self.playerLock.release()
            elif actionId >= BP_ACTION_0 and actionId <= BP_ACTION_9:
                number = actionId - BP_ACTION_0
                if self.onNumberAction[1] == NUMBER_ACTION_LOAD:
                    if number > 0:
                        self.playerLock.acquire()
                        self.InfoText("%s #%d" % (__language__(30110), number), __language__(30111))
                        fname = xbmc.translatePath( os.path.join(HOME_SCRIPT_DIR, "%s.%d" % (AV_NAMES[self.avMode], number)) )
                        self.movePos = []
                        self.thisAlbumOnly = False
                        self.loop = LOOP_DISABLED
                        xbmc.executebuiltin("xbmc.playercontrol(repeatoff)")
                        playing = self.player.isPlaying()
                        if playing:
                            self.player.stop()
                        if not self.A.Open(fname, self.mode):
                            self.A.Normalize()
                        self.ComposeNewPlaylist()
                        pos = self.A.NextAlbum(self.mode, False, [1,1])
                        self.A.Pos(pos)
                        self.InfoText()
                        if playing:
                            self.player.play(self.playlist, None, True)
                        self.playerLock.release()
                elif self.onNumberAction[1] == NUMBER_ACTION_SAVE:
                    if number > 0:
                        self.playerLock.acquire()
                        self.InfoText("%s #%d" % (__language__(30110), number), __language__(30112))
                        fname = xbmc.translatePath( os.path.join(HOME_SCRIPT_DIR, "%s.%d" % (AV_NAMES[self.avMode], number)) )
                        self.A.Save(fname, self.mode)
                        self.InfoText()
                        self.playerLock.release()
                else:
                    if not self.BC.active():
                        if number == 0:
                            self.onNumberAction[0] = NUMBER_ACTION_BC_ALBUM
                        else:
                            self.onNumberAction[0] = NUMBER_ACTION_BC_TRACK
                    else:
                        self.onNumberAction[0] = self.onNumberAction[1]
                    self.BC.Press(number)
            elif actionId == BP_ACTION_NEXT_TRACK:
                self.playerLock.acquire()
                self.movePos = []
                pos = self.A.NextTrack(self.mode, self.thisAlbumOnly, self.loop)
                self.A.Pos(pos)
                if self.player.isPlaying():
                    i = self.PlayPos(pos)
                    if i >= 0:
                        self.player.playselected(i)
                self.playerLock.release()
            elif actionId == BP_ACTION_PREV_TRACK:
                self.playerLock.acquire()
                isPlaying = self.player.isPlaying()
                if isPlaying:
                    if self.player.getTime() > PREV_THRESHOLD:
                        self.player.seekTime(0)
                    else:
                        self.movePos = []
                        pos = self.A.PrevTrack(self.mode, self.thisAlbumOnly, self.loop)
                        self.A.Pos(pos)
                        i = self.PlayPos(pos)
                        if i >= 0:
                            self.player.playselected(i)
                    self.player.resume()
                else:
                    self.movePos = []
                    pos = self.A.PrevTrack(self.mode, self.thisAlbumOnly, self.loop)
                    self.A.Pos(pos)
                self.playerLock.release()
            elif actionId == BP_ACTION_LOAD:
                self.onNumberAction[0] = NUMBER_ACTION_LOAD
            elif actionId == BP_ACTION_SAVE:
                self.onNumberAction[0] = NUMBER_ACTION_SAVE
            elif actionId == BP_ACTION_RESCAN:
                self.playerLock.acquire()
                self.movePos = []
                self.mode = L_NORM
                self.loop = LOOP_DISABLED
                xbmc.executebuiltin("xbmc.playercontrol(repeatoff)")
                playing = self.player.isPlaying()
                if playing:
                    self.player.stop()
                self.InfoText(__language__(30113), __language__(30114))
                paths = list(p for p in GetSources(SOURCES_FILE, AV_NAMES[self.avMode]))
                if not MediaScan(paths, PATTERNS[self.avMode], SCAN_FILE[self.avMode], True):
                    self.playerLock.release()
                    self.__exit()
                    raise BreakException
                if not self.A.Open(SCAN_FILE[self.avMode]):
                    self.playerLock.release()
                    self.__exit()
                    raise BreakException
                self.InfoText()
                self.ComposeNewPlaylist()
                pos = self.A.NextAlbum(self.mode, False, [1,1])
                self.A.Pos(pos)
                if playing:
                    self.player.play(self.playlist, None, True)
                else:
                    xbmc.playSFX(xbmc.translatePath( os.path.join(XBMC_DIR, 'addons', 'skin.confluence', 'sounds', 'notify.wav') ))
                self.playerLock.release()
                self.NavigationInfo(True)
            elif actionId == BP_ACTION_PROGRAM:
                self.playerLock.acquire()
                xbmc.executebuiltin("xbmc.playercontrol(repeatoff)")
                if self.mode != L_PROG:
                    self.thisAlbumOnly = False
                    isPlaying = self.player.isPlaying()
                    if isPlaying:
                        self.player.stop()
                    self.mode = L_PROG
                    self.ComposeNewPlaylist()
                    pos = self.movePos
                    self.movePos = []
                    if not pos:
                        pos = self.A.Pos()
                    pos = self.A.NextTrack(self.mode, self.thisAlbumOnly, False, pos, False)
                    self.A.Pos(pos)
                    if isPlaying:
                        i = self.PlayPos(self.A.Pos())
                        if i >= 0:
                            self.player.play(self.playlist, None, True)
                            if i > 0:
                                self.player.playselected(i)
                else:
                    if self.loop == LOOP_DISABLED:
                        self.ContinueFromBeginning()
                self.loop = LOOP_DISABLED
                self.StatusText()
                self.playerLock.release()
            elif actionId == BP_ACTION_NORMAL:
                self.playerLock.acquire()
                xbmc.executebuiltin("xbmc.playercontrol(repeatoff)")
                if self.mode != L_NORM or self.thisAlbumOnly == True:
                    isPlaying = self.player.isPlaying()
                    if isPlaying:
                        self.player.stop()
                    self.mode = L_NORM
                    self.ComposeNewPlaylist()
                    if self.thisAlbumOnly == True:
                        self.thisAlbumOnly = False
                        self.A.Normalize()
                    else:
                        pos = self.movePos
                        if not pos:
                            pos = self.A.Pos()
                        pos = self.A.NextTrack(self.mode, self.thisAlbumOnly, False, pos, False)
                        self.A.Pos(pos)
                    self.movePos = []
                    if isPlaying:
                        i = self.PlayPos(self.A.Pos())
                        if i >= 0:
                            self.player.play(self.playlist, None, True)
                            if i > 0:
                                self.player.playselected(i)
                else:
                    if self.loop == LOOP_DISABLED:
                        self.ContinueFromBeginning()
                self.loop = LOOP_DISABLED
                self.StatusText()
                self.playerLock.release()
            elif actionId == BP_ACTION_REPEAT: #loop
                self.playerLock.acquire()
                xbmc.executebuiltin("xbmc.playercontrol(repeatall)")
                self.loop = LOOP_ALL
                self.player.repeatAB(True)
                self.StatusText()
                self.playerLock.release()
            elif actionId == BP_ACTION_REPEAT_ONE: #repeat-one loop
                self.playerLock.acquire()
                if self.player.isPlaying():
                    xbmc.executebuiltin("xbmc.playercontrol(repeatone)")
                self.loop = LOOP_ONE
                self.player.repeatAB(True)
                self.StatusText()
                self.playerLock.release()
            elif actionId == BP_ACTION_REPEAT_AB:
                self.playerLock.acquire()
                self.player.repeatAB()
                self.StatusText()
                self.playerLock.release()
            elif actionId == BP_ACTION_ALBUM:
                self.playerLock.acquire()
                xbmc.executebuiltin("xbmc.playercontrol(repeatoff)")
                if self.thisAlbumOnly == False:
                    self.thisAlbumOnly = True
                    if self.mode == L_NORM:
                        pos = self.A.Pos()
                        isPlaying = self.player.isPlaying()
                        if isPlaying:
                            self.player.stop()
                        self.A.Normalize()
                        self.movePos = []
                        pos = self.A.NextAlbum(self.mode, False, pos)
                        self.A.Pos(pos)
                        if pos:
                            a = pos[0]
                        else:
                            a = 1
                        self.ComposeNewPlaylist(a)
                        if isPlaying:
                            i = self.PlayPos(self.A.Pos())
                            if i >= 0:
                                self.player.play(self.playlist, None, True)
                                if i > 0:
                                    self.player.playselected(i)
                    else:
                        pos = self.movePos
                        if not pos:
                            pos = self.A.Pos()
                        isPlaying = self.player.isPlaying()
                        if isPlaying:
                            self.player.stop()
                        self.mode = L_NORM
                        self.movePos = []
                        pos = self.A.NextAlbum(self.mode, False, pos)
                        self.A.Pos(pos)
                        if pos:
                            a = pos[0]
                        else:
                            a = 1
                        self.ComposeNewPlaylist()
                        if isPlaying:
                            i = self.PlayPos(self.A.Pos())
                            if i >= 0:
                                self.player.play(self.playlist, None, True)
                                if i > 0:
                                    self.player.playselected(i)
                else:
                    if self.loop == LOOP_DISABLED:
                       self.ContinueFromBeginning()
                self.loop = LOOP_DISABLED
                self.StatusText()
                self.playerLock.release()
            elif actionId == BP_ACTION_OFF_ENABLE:
                self.powerOff = True
                self.StatusText()
            elif actionId == BP_ACTION_OFF_DISABLE:
                self.powerOff = False
                self.StatusText()
            elif actionId == BP_ACTION_NEXT_ALBUM:
                self.playerLock.acquire()
                self.movePos = []
                pos = self.A.NextAlbum(self.mode, self.loop)
                if self.player.isPlaying():
                    if self.thisAlbumOnly == True:
                        self.player.stop()
                        self.A.Pos(pos)
                        if pos:
                            a = pos[0]
                        else:
                            a = 1
                        self.ComposeNewPlaylist(a)
                    i = self.PlayPos(pos)
                    if i >= 0:
                        if self.thisAlbumOnly == True:
                            self.player.play(self.playlist, None, True)
                            if self.loop == LOOP_ONE:
                                xbmc.executebuiltin("xbmc.playercontrol(repeatone)")
                            elif self.loop == LOOP_ALL:
                                xbmc.executebuiltin("xbmc.playercontrol(repeatall)")
                            if i > 0:
                                self.player.playselected(i)
                        else:
                            self.player.playselected(i)
                else:
                    self.A.Pos(pos)
                self.playerLock.release()
            elif actionId == BP_ACTION_PREV_ALBUM:
                self.playerLock.acquire()
                self.movePos = []
                pos = self.A.PrevAlbum(self.mode, self.loop)
                if self.player.isPlaying():
                    if self.thisAlbumOnly == True:
                        self.player.stop()
                        self.A.Pos(pos)
                        if pos:
                            a = pos[0]
                        else:
                            a = 1
                        self.ComposeNewPlaylist(a)
                    i = self.PlayPos(pos)
                    if i >= 0:
                        if self.thisAlbumOnly == True:
                            self.player.play(self.playlist, None, True)
                            if self.loop == LOOP_ONE:
                                xbmc.executebuiltin("xbmc.playercontrol(repeatone)")
                            elif self.loop == LOOP_ALL:
                                xbmc.executebuiltin("xbmc.playercontrol(repeatall)")
                            if i > 0:
                                self.player.playselected(i)
                        else:
                            self.player.playselected(i)
                else:
                    self.A.Pos(pos)
                self.playerLock.release()
            elif actionId == BP_ACTION_STEP_FORWARD:
                self.playerLock.acquire()
                if self.player.isPlaying():
                    total = self.player.getTotalTime()
                    jump = self.player.getTime() + SKIP_SMALL
                    if jump > total:
                        self.movePos = []
                        pos = self.A.NextTrack(self.mode, self.thisAlbumOnly, self.loop)
                        self.A.Pos(pos)
                        i = self.PlayPos(pos)
                        if i >= 0:
                            self.player.playselected(i)
                    else:
                        self.player.seekTime(jump)
                    self.player.resume()
                self.playerLock.release()
            elif actionId == BP_ACTION_STEP_BACK:
                self.playerLock.acquire()
                if self.player.isPlaying():
                    jump = self.player.getTime() - SKIP_SMALL
                    if jump < 0:
                        self.movePos = []
                        pos = self.A.PrevTrack(self.mode, self.thisAlbumOnly, self.loop)
                        self.A.Pos(pos)
                        i = self.PlayPos(pos)
                        if i >= 0:
                            self.player.playselected(i)
                            if self.loop == LOOP_ONE:
                                pass
                            else:
                                jump = self.player.getTotalTime() - SKIP_SMALL
                                if jump > 0:
                                    self.player.seekTime(jump)
                    else:
                        self.player.seekTime(jump)
                    self.player.resume()
                self.playerLock.release()
            elif actionId == BP_ACTION_BIG_STEP_FORWARD:
                self.playerLock.acquire()
                if self.player.isPlaying():
                    total = self.player.getTotalTime()
                    jump = self.player.getTime() + SKIP_BIG
                    if jump > total:
                        self.movePos = []
                        pos = self.A.NextTrack(self.mode, self.thisAlbumOnly, self.loop)
                        self.A.Pos(pos)
                        i = self.PlayPos(pos)
                        if i >= 0:
                            self.player.playselected(i)
                    else:
                        self.player.seekTime(jump)
                    self.player.resume()
                self.playerLock.release()
            elif actionId == BP_ACTION_BIG_STEP_BACK:
                self.playerLock.acquire()
                if self.player.isPlaying():
                    jump = self.player.getTime() - SKIP_BIG
                    if jump < 0:
                        self.movePos = []
                        pos = self.A.PrevTrack(self.mode, self.thisAlbumOnly, self.loop)
                        self.A.Pos(pos)
                        i = self.PlayPos(pos)
                        if i >= 0:
                            self.player.playselected(i)
                            if self.loop == LOOP_ONE:
                                pass
                            else:
                                jump = self.player.getTotalTime() - SKIP_BIG
                                if jump > 0:
                                    self.player.seekTime(jump)
                    else:
                        self.player.seekTime(jump)
                    self.player.resume()
                self.playerLock.release()
            elif actionId == BP_ACTION_FORWARD:
                self.playerLock.acquire()
                if self.player.isPlaying():
                    self.player.repeatAB(True)
                self.playerLock.release()
                if self.setupSequence == BP_ACTION_STOP:
                    self.Setup()
            elif actionId == BP_ACTION_BACKWARD:
                self.playerLock.acquire()
                if self.player.isPlaying():
                    self.player.repeatAB(True)
                self.playerLock.release()
            else:
                actionId = BP_ACTION_NONE
        except BreakException:
            pass
        if actionId != BP_ACTION_NONE:
            self.setupSequence = actionId
            if self.onNumberAction[0] != NUMBER_ACTION_BC_ALBUM and self.onNumberAction[0] != NUMBER_ACTION_BC_TRACK:
                self.BC.cancel()
            self.onNumberAction[1:len(self.onNumberAction)] = self.onNumberAction[0:len(self.onNumberAction)-1]
            self.onNumberAction[0] = NUMBER_ACTION_NONE
            self.NavigationInfo()
        self.lock_onAction.release()

    def __exit(self):
        global BlindPlayerAutoPowerOff
        if self.BC:
            self.BC.close()
        # Synchronize any onAction leftover
        self.lock_onAction.acquire()
        if self.player:
            self.player.disableCallbacks()
            if self.player.isPlaying():
                self.player.stop()
            self.player.close()
            del self.player
        if self.I:
            self.I.close()
        BlindPlayerAutoPowerOff = self.powerOff
        self.close()

def BlindPlayer(mode=""):
    global BlindPlayerMode
    global BlindPlayerAutoPowerOff
    debuglog("%s start..." % __scriptname__)
    BlindPlayerMode = [n for n in AV_NAMES].index(mode) if mode in AV_NAMES else AV_MUSIC
    win = GUI("%s.xml" % __scriptid__.replace(".","-") , __cwd__, "Default")
    win.doModal()
    del win
    if BlindPlayerAutoPowerOff:
        xbmc.shutdown()
    debuglog("%s exit..." % __scriptname__)
    pass

