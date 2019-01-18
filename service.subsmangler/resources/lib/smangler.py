# This file includes code for SubsMangler's core functionality

import codecs
import os
import filecmp
import re
import string
import time
import urllib2
import xbmc
import xbmcgui
import xbmcaddon
import xbmcvfs
import common

from datetime import datetime
from json import loads
from shutil import copyfile
from threading import Timer
from resources.lib import pysubs2



# timer class
# from: https://stackoverflow.com/questions/3393612/run-certain-code-every-n-seconds/13151299
class RepeatedTimer(object):
    def __init__(self, interval, function, *args, **kwargs):
        self._timer = None
        self.interval = interval
        self.function = function
        self.args = args
        self.kwargs = kwargs
        self.is_running = False
        #self.start()  #do not start automatically

    def _run(self):
        self.is_running = False
        self.start()
        self.function(*self.args, **self.kwargs)

    def start(self):
        if not self.is_running:
            self._timer = Timer(self.interval, self._run)
            self._timer.start()
            self.is_running = True

    def stop(self):
        if self.is_running:
            self._timer.cancel()
            self.is_running = False



# Player class
# https://forum.kodi.tv/showthread.php?tid=130923
# all Player() events are asynchronous to addon script, so we need to wait for event to be triggered (to actually happen) before reading any data
# instead of monitoring player in loop with xbmc.Player().isPlayingVideo() and then launching action
class XBMCPlayer(xbmc.Player):

    def __init__( self, *args ):
        pass

    def onPlayBackStarted( self ):
        # Will be called when xbmc player is created
        # however stream may not be available at this point
        # for Kodi 18 use onAVStarted
        if int(common.__kodiversion__[:2]) == 17:
            GetSubtitles()

    def onAVStarted ( self ):
        # Will be called when xbmc has video
        # works only on Kodi 18 onwards
        # on Kodi >= 17 onPlaybackStarted seems to be failing very often: https://forum.kodi.tv/showthread.php?tid=334929
        if int(common.__kodiversion__[:2]) >= 18:
            GetSubtitles()

    def onPlayBackEnded( self ):
        # Will be called when xbmc stops playing a file
        global ClockTick
        # player finished playing video
        common.Log("VideoPlayer END detected.", xbmc.LOGINFO)

        # add 15 minutes to timer in case timer was close to 0 before playback start
        # this prevents starting cleanup immediatelly after playback ended
        # 1 tick per 5 sec * 15 min = 180 ticks
        ClockTick += 180

        # stop monitoring dir for changed files
        rt.stop()

    def onPlayBackStopped( self ):
        # Will be called when user stops xbmc playing a file
        global ClockTick
        # player has just been stopped
        common.Log("VideoPlayer STOP detected.", xbmc.LOGINFO)

        # add 15 minutes to timer in case timer was close to 0 before playback start
        # this prevents starting cleanup immediatelly after playback ended
        # 1 tick per 5 sec * 15 min = 180 ticks
        ClockTick += 180

        # stop monitoring dir for changed files
        rt.stop()



# Monitor class
# https://forum.kodi.tv/showthread.php?tid=198911&pid=1750890#pid1750890
class XBMCMonitor(xbmc.Monitor):

    def __init__(self, *args, **kwargs):
        xbmc.Monitor.__init__(self)

    def onAbortRequested(self):
        # Will be called when XBMC requests Abort
        rt.stop()
        common.Log("Abort requested in Monitor class.", xbmc.LOGDEBUG)

    def onSettingsChanged(self):
        # Will be called when addon settings are changed
        common.Log("Addon settings changed.", xbmc.LOGINFO)
        # re-read settings
        common.GetSettings()

        # if service is not enabled any more, stop timer
        if not common.setting_ConversionServiceEnabled:
            rt.stop()



# function prepares plugin environment
def PreparePlugin():
    """Prepare plugin environment
    """

    #
    # execution starts here
    #
    # watch out for encodings
    # https://forum.kodi.tv/showthread.php?tid=144677
    # https://nedbatchelder.com/text/unipain.html
    # https://www.joelonsoftware.com/2003/10/08/the-absolute-minimum-every-software-developer-absolutely-positively-must-know-about-unicode-and-character-sets-no-excuses/

    # path and file name of public definitions
    global deffileurl
    global localdeffilename
    global sampledeffilename
    global tempdeffilename
    deffileurl = "http://bkiziuk.github.io/kodi-repo/regexdef.txt"
    localdeffilename = os.path.join(common.__addonworkdir__, 'regexdef.def')
    sampledeffilename = os.path.join(common.__addondir__, 'resources', 'regexdef.def')
    tempdeffilename = os.path.join(common.__addonworkdir__, 'tempdef.def')

    # list of input file extensions
    # extensions in lowercase with leading dot
    # note: we do not include output extension .ass
    global SubExtList
    SubExtList = [ '.txt', '.srt', '.sub', '.subrip', '.microdvd', '.mpl', '.tmp' ]

    # list of video file extensions
    # extensions in lowercase with leading dot
    global VideoExtList
    VideoExtList = [ '.mkv', '.avi', '.mp4', '.mpg', '.mpeg' ]

    # initiate monitoring of xbmc.Player events
    global player
    player = XBMCPlayer()

    # initiate monitoring of xbmc events
    global monitor
    monitor = XBMCMonitor()

    xbmc.log("SubsMangler: started. Version: " + common.__version__.encode('utf-8') + ". Kodi version: " + common.__kodiversion__.encode('utf-8'), level=xbmc.LOGNOTICE)

    # prepare timer to launch
    global rt
    rt = RepeatedTimer(2.0, DetectNewSubs)

    # set initial values
    global DetectionIsRunning
    DetectionIsRunning = False
    global ClockTick
    ClockTick = 0

    # prepare datadir
    # directory and file is local to the filesystem
    # no need to use xbmcvfs
    if not os.path.isdir(common.__addonworkdir__):
        xbmc.log("SubsMangler: profile directory doesn't exist: " + common.__addonworkdir__.encode('utf-8') + "   Trying to create.", level=xbmc.LOGNOTICE)
        try:
            os.mkdir(common.__addonworkdir__)
            xbmc.log("SubsMangler: profile directory created: " + common.__addonworkdir__.encode('utf-8'), level=xbmc.LOGNOTICE)
        except OSError as e:
            xbmc.log("SubsMangler: Log: can't create directory: " + common.__addonworkdir__.encode('utf-8'), level=xbmc.LOGERROR)
            xbmc.Log("Exception: " + str(e.message).encode('utf-8'), xbmc.LOGERROR)

    # load settings
    common.GetSettings()

    # check if external log is configured
    if common.setting_SeparateLogFile == 1:
        xbmc.log("SubsMangler: External log enabled: " + os.path.join(common.__addonworkdir__, 'smangler.log').encode('utf-8'), level=xbmc.LOGNOTICE)



# supplementary code to be run periodically from main loop
def SupplementaryServices():
    """Supplementary services that have to run periodically
    """

    global deffilename
    global ClockTick

    # set definitions file location
    # dir is local, no need to use xbmcvfs()
    if os.path.isfile(localdeffilename):
        # downloaded file is available
        deffilename = localdeffilename
    else:
        # use sample file from addon's dir
        deffilename = sampledeffilename

    # housekeeping services
    if ClockTick <= 0 and not xbmc.getCondVisibility('Player.HasMedia'):
        # check if auto-update is enabled and player does not play any content
        if common.setting_AutoUpdateDef:
            # update regexdef file
            UpdateDefFile()

        if common.setting_AutoRemoveOldSubs:
            # clear old subtitle files
            RemoveOldSubs()

        # reset timer to 6 hours
        # 1 tick per 5 sec * 60 min * 6 hrs = 4320 ticks
        ClockTick = 4320

    # decrease timer if player is idle
    # avoid decreasing the timer to infinity
    if ClockTick > 0 and not xbmc.getCondVisibility('Player.HasMedia'):
        ClockTick -= 1



# function checks if stream is a local file and tries to find matching subtitles
# if subtitles are not found, it opens search dialog
def GetSubtitles():
    """Check if stream is a local file and launch subtitles. If subtitles are not present, open search dialog
    """
    global subtitlePath
    global playingFilename
    global playingFilenamePath
    global playingFps
    global SubsSearchWasOpened

    # stop subtitle detection in case it was already running
    # this prevents YesNo dialog from showing immediatelly after opening subtitle search dialog
    # in case playback of new file is started during playback of another file without prior stopping it
    rt.stop()

    # detect if Player is running by checking xbmc.Player().isPlayingVideo() or xbmc.getCondVisibility('Player.HasVideo')
    # use ConditionalVisibility checks: http://kodi.wiki/view/List_of_boolean_conditions
    if xbmc.getCondVisibility('Player.HasVideo'):
        # player has just been started, check what contents does it play and from
        common.Log("VideoPlayer START detected.", xbmc.LOGINFO)

        # get info on file being played
        playingFilenamePath = ''
        counter = 0
        # try to read info several times as sometimes reading fails
        while not (playingFilenamePath or counter >= 3):
            xbmc.sleep(500)
            subtitlePath, playingFilename, playingFilenamePath, playingFps, playingLang, playingSubs = GetPlayingInfo()
            counter += 1
        if counter > 1:
            common.Log("First GetPlayingInfo() read failed. Number of tries: " + str(counter), xbmc.LOGWARNING)

        # ignore all streaming videos
        # http://xion.io/post/code/python-startswith-tuple.html
        protocols = ("http", "https", "mms", "rtsp", "pvr", "plugin")
        if playingFilenamePath.lower().startswith(tuple(p + '://' for p in protocols)):
            common.Log("Video stream detected. Ignoring it.", xbmc.LOGINFO)
            return
        elif not playingFilenamePath:
            # string is empty, may happen when playing buffered streams
            common.Log("Empty 'playingFilenamePath' string detected. Not able to continue.", xbmc.LOGERROR)
            return

        # get information on Kodi language settings
        # GUI language:
        #   resource.language.en_gb == en, resource.language.pl_pl == pl, etc.
        # audio & subtitles languages:
        #   original == Original video language
        #   default == GUI interface language
        #   forced_only == (only for subtitles) only forced subtitles
        #   none == (only for subtitles) no subtitles
        #   English == English, Polish == Polish, etc.
        # GUI language
        guilanguage = GetKodiSetting('locale.language')
        # preferred audio language
        prefaudiolanguage = GetKodiSetting('locale.audiolanguage')
        # preferred subtitle language
        prefsubtitlelanguage = GetKodiSetting('locale.subtitlelanguage')

        # map values to ISO 639-2
        guilanguage = guilanguage.replace('resource.language.', '')
        guilanguage = GetIsoCode(guilanguage[:2])

        if prefaudiolanguage == 'default':
            prefaudiolanguage = guilanguage
        elif prefaudiolanguage == 'original':
            pass
        else:
            prefaudiolanguage = GetIsoCode(prefaudiolanguage)

        if prefsubtitlelanguage == 'default':
            prefsubtitlelanguage = guilanguage
        elif prefsubtitlelanguage == 'original' or prefsubtitlelanguage == 'none' or prefsubtitlelanguage == 'forced_only':
            prefsubtitlelanguage = 'none'
        else:
            prefsubtitlelanguage = GetIsoCode(prefsubtitlelanguage)

        common.Log("Kodi's GUI language: " + guilanguage, xbmc.LOGINFO)
        common.Log("Kodi's preferred audio language: " + prefaudiolanguage, xbmc.LOGINFO)
        common.Log("Kodi's preferred subtitles language: " + prefsubtitlelanguage, xbmc.LOGINFO)

        # check if there is .ass subtitle file already on disk matching video being played
        # if not, automatically open subtitlesearch dialog
        #
        # set initial value for SubsSearchWasOpened flag
        SubsSearchWasOpened = False
        # check if Subtitles Search window should be opened at player start
        if common.setting_AutoInvokeSubsDialog:
            # get all files matching name of file being played
            # also includes 'noautosubs' file and file with '.noautosubs' extension
            extlist = list()

            if common.setting_NoAutoInvokeIfLocalUnprocSubsFound:
                # optionally search for all subtitle extensions, not only '.ass'
                # assignment operator just makes an alias for the list
                # https://stackoverflow.com/questions/2612802/how-to-clone-or-copy-a-list
                extlist = list(SubExtList)

            # search for target extension '.ass'
            extlist.append('.ass')

            # get all file names matching name of file being played
            localsubs = GetSubtitleFiles(subtitlePath, extlist)

            # check if there is 'noautosubs' file or extension on returned file list
            noautosubs = False
            for item in localsubs:
                if "noautosubs" in item[-10:]:
                    # set noautosubs flag informing that subtitles search window should not be invoked
                    noautosubs = True
                    # delete this item from list to not falsely trigger enabling subtitles below
                    del localsubs[item]
                    break

            if not noautosubs:
                # noautosubs file or extension not found
                # it is possible to invoke SubsSearch dialog or enable locally found subtitles
                #
                # check if local subtitles exist (list should not be empty)
                # https://stackoverflow.com/questions/53513/how-do-i-check-if-a-list-is-empty/53522#53522
                if not localsubs:
                    # local subs don't exist on disk
                    # check Kodi preferences on subtitles and compare with currently played video to see if search dialog should be opened
                    #
                    # do not open search dialog if:
                    # - Kodi preferred audio language match audio language
                    # - Kodi preferred subtitle language match loaded subtitle language
                    if not ((prefaudiolanguage == playingLang) or (prefsubtitlelanguage == playingSubs)):
                        common.Log("No local subtitles matching video being played. Opening search dialog.", xbmc.LOGINFO)
                        # set flag to remember that subtitles search dialog was opened
                        SubsSearchWasOpened = True
                        # invoke subtitles search dialog
                        xbmc.executebuiltin('ActivateWindow(10153)')  # subtitles search
                        # hold further execution until window is closed
                        # wait for window to appear
                        while not xbmc.getCondVisibility("Window.IsVisible(10153)"):
                            xbmc.sleep(1000)
                        # wait for window to disappear
                        while xbmc.getCondVisibility("Window.IsVisible(10153)"):
                            xbmc.sleep(500)
                    else:
                        common.Log("Video or subtitle language match Kodi's preferred settings. Not opening subtitle search dialog.", xbmc.LOGINFO)
                else:
                    # enable .ass subtitles if they are present on the list
                    asssubs = False
                    for item in localsubs:
                        if ".ass" in item[-4:]:
                            common.Log("Local 'ass' subtitles matching video being played detected. Enabling subtitles: " + os.path.join(subtitlePath, item), xbmc.LOGINFO)
                            xbmc.Player().setSubtitles(os.path.join(subtitlePath, item))
                            asssubs = True
                            break

                    if not asssubs:
                        common.Log("Local non 'ass' subtitles matching video being played detected. Not opening subtitle search dialog.", xbmc.LOGINFO)
            else:
                common.Log("'noautosubs' file or extension detected. Not opening subtitle search dialog.", xbmc.LOGINFO)
        else:
            # enable subtitles if there are any
            xbmc.Player().showSubtitles(True)

        # check periodically if there are any files changed in monitored subdir that match file being played
        if common.setting_ConversionServiceEnabled:
            rt.start()



# function matches input string for language designation
# and outputs ISO 639-2 equivalent
# https://stackoverflow.com/questions/2879856/get-system-language-in-iso-639-3-letter-codes-in-python
# http://www.loc.gov/standards/iso639-2/ISO-639-2_utf-8.txt
def GetIsoCode(lang):
    """Find correct ISO-639-3 language code.

    Arguments:
        lang {str} -- language name, ISO-639-2 code or ISO-639-3 code

    Returns:
        str -- ISO-639-3 code
    """

    # "bibliographic" iso codes are derived from English word for the language
    # "terminologic" iso codes are derived from the pronunciation in the target
    # language (if different to the bibliographic code)

    outlang = ''

    if lang:
        # language code is not empty
        common.Log("Looking for language code for: " + lang, xbmc.LOGDEBUG)
        f = codecs.open(os.path.join(common.__addondir__, 'resources', 'ISO-639-2_utf-8.txt'), 'rb', 'utf-8')
        for line in f:
            iD = {}
            iD['bibliographic'], iD['terminologic'], iD['alpha2'], iD['english'], iD['french'] = line.strip().split('|')

            if iD['bibliographic'].lower() == lang.lower() or iD['alpha2'].lower() == lang.lower() or iD['english'].lower() == lang.lower():
                outlang = iD['bibliographic']
                break
        f.close()

        if outlang:
            common.Log("Language code found: " + outlang, xbmc.LOGDEBUG)
        else:
            common.Log("Language code not found.", xbmc.LOGWARNING)
    else:
        # language code is empty
        common.Log("Language code is empty. Skipping searching.", xbmc.LOGINFO)

    return outlang



# parse a list of definitions from file
# load only a particular section
def GetDefinitions(section):
    """Load a list of definitions for a given section.

    Arguments:
        section {str} -- name of section to load

    Returns:
        list -- list of loaded definitions
    """

    global deffilename
    importedlist = list()

    # check if definitions file exists
    if os.path.isfile(deffilename):
        # open file
        with open(deffilename, "rt") as f:
            thissection = False
            for line in f:
                # truncate any comment at the end of line
                # https://stackoverflow.com/questions/509211/understanding-pythons-slice-notation
                pos = line.find("#")
                # if there is no comment, pos==-1
                if pos >= 0:
                    # take only part before comment
                    line = line[:pos]
                # remove whitespaces at the beginning and end
                line = line.strip()

                # patterns for finding sections
                thissectionpattern = "\[" + section + "\]"    # matches: [SeCtIoNnAmE]
                othersectionpattern = "^\[.*?\]"    # matches: <BEGINLINE>[anything]
                if re.search(thissectionpattern, line, re.IGNORECASE):
                    # beginning of our section
                    thissection = True
                elif re.search(othersectionpattern, line):   # matches: <BEGINLINE>[anything]
                    # beginning of other section
                    thissection = False
                elif thissection:
                    # contents of our section - import to list
                    # check if line is not empty, empty line is "falsy"
                    # https://stackoverflow.com/questions/9573244/most-elegant-way-to-check-if-the-string-is-empty-in-python
                    if line:
                        # add to list
                        importedlist.append(line)

        common.Log("Definitions imported. Section: " + section, xbmc.LOGINFO)
        # dump imported list
        for entry in importedlist:
            common.Log("       " + entry, xbmc.LOGDEBUG)
    else:
        common.Log("Definitions file does not exist: " + deffilename, xbmc.LOGINFO)

    return importedlist



# remove all strings from line that match regex deflist
def RemoveStrings(line, deflist):
    """Remove all strings from line that match regex definition list

    Arguments:
        line {str} -- text line to process
        deflist {list} -- definitions list

    Returns:
        str -- filtered line
    """

    # iterate over every entry on the list
    for pattern in deflist:
        try:
            if re.search(pattern, line, re.IGNORECASE):
                common.Log("    matches regex: " + pattern, xbmc.LOGDEBUG)
                line = re.sub(pattern, '', line, flags=re.I)
                common.Log("    Resulting string: " + line, xbmc.LOGDEBUG)
        except Exception as e:
            common.Log("    Regex error: '" + e.message + "' in Regex: " + pattern, xbmc.LOGERROR)

    return line



# get subtitle location setting
# https://forum.kodi.tv/showthread.php?tid=209587&pid=1844182#pid1844182
def GetKodiSetting(name):
    """Get Kodi setting value from given section name.

    Arguments:
        name {str} -- Kodi section name

    Returns:
        str -- setting value
    """

    # Uses XBMC/Kodi JSON-RPC API to retrieve subtitles location settings values.
    command = '''{
    "jsonrpc": "2.0",
    "id": 1,
    "method": "Settings.GetSettingValue",
    "params": {
        "setting": "%s"
    }
}'''
    result = xbmc.executeJSONRPC(command % name)
    py = loads(result)
    common.Log("JSON-RPC: Settings.GetSettingValue: " + str(py), xbmc.LOGDEBUG)
    if 'result' in py and 'value' in py['result']:
        return py['result']['value']
    else:
        raise ValueError



# converts subtitles using pysubs2 library
# pysubs2 code is written by Tomas Karabela - https://github.com/tkarabela/pysubs2
def MangleSubtitles(originalinputfile):
    """Convert subtitle file using pysubs2 library

    Arguments:
        originalinputfile {str} -- file to be processed

    Returns:
        str -- processed file name
    """


    # tempfilename
    tempfile = "processed_subtitles"

    if not xbmcvfs.exists(originalinputfile):
        common.Log("File does not exist: " + originalinputfile, xbmc.LOGERROR)
        return

    # get subtitles language by splitting it from filename
    # split file and extension
    subfilebase, subfileext = os.path.splitext(originalinputfile)
    # from filename split language designation
    subfilecore, subfilelang = os.path.splitext(subfilebase)

    common.Log("Read subtitle language designation: " + subfilelang[1:],xbmc.LOGINFO)
    # try to find ISO639-2 designation
    # remove dot from language code ('.en')
    subslang = GetIsoCode(subfilelang.lower()[1:]).lower()

    # as pysubs2 library doesn't support Kodi's virtual file system and file can not be processed remotely on smb:// share,
    # file must be copied to temp folder for local processing
    # construct input_file name
    tempinputfile = os.path.join(common.__addonworkdir__, tempfile + "_in.txt")
    # construct output_file name
    tempoutputfile = os.path.join(common.__addonworkdir__, tempfile + "_out.ass")
    # copy file to temp
    copy_file(originalinputfile, tempinputfile)

    common.Log("Subtitle file processing started.", xbmc.LOGNOTICE)

    # record start time of processing
    MangleStartTime = time.time()



    # use proper encoding to decode subtitles
    # the current implementation first tries to use UTF-8 encoding and, if that fails,
    # uses an encoding based on language information
    # this approach should work for most cases assuming that Windows encodings are used
    #
    # https://www.science.co.il/language/Locale-codes.php
    charmap = {
        'ara': 'cp1256',
        'aze': 'cp1251',
        'bat': 'cp1257',
        'bel': 'cp1251',
        'bul': 'cp1251',
        'cze': 'cp1250',
        'est': 'cp1257',
        'grc': 'cp1253',
        'heb': 'cp1255',
        'hrv': 'cp1250',
        'hun': 'cp1250',
        'kaz': 'cp1251',
        'kir': 'cp1251',
        'lav': 'cp1257',
        'lit': 'cp1257',
        'mac': 'cp1251',
        'mon': 'cp1251',
        'per': 'cp1256',
        'pol': 'cp1250',
        'rum': 'cp1250',
        'rus': 'cp1251',
        'slo': 'cp1250',
        'slv': 'cp1250',
        'srp': 'cp1251',
        'tat': 'cp1251',
        'tur': 'cp1254',
        'ukr': 'cp1251',
        'urd': 'cp1256',
        'uzb': 'cp1251',
        'vie': 'cp1258'
        # else: cp1252
    }

    # first, check if the file can be properly read using UTF-8 encoding
    enc = ""
    try:
        with codecs.open(tempinputfile, mode="rb", encoding='utf-8') as reader:
            temp = reader.read()
            # still no exception - seems to be a success
            common.Log("UTF-8 encoding seems to be valid.", xbmc.LOGINFO)
            enc = "utf-8"
    except Exception as e:
        # reading as UTF-8 failed
        # try use encoding based on language

        # if reading as UTF-8 failed and the file language detection was a success
        if (not enc) and subslang:
            if charmap[subslang]:
                # encoding found on the list
                enc = charmap[subslang]
            else:
                # encoding not found on the list, use Western European encoding
                enc = "cp1252"

            # try to read file using language specific encoding
            try:
                with codecs.open(tempinputfile, mode="rb", encoding=enc) as reader:
                    temp = reader.read()
                    # still no exception - seems to be a success
                    common.Log("Chosen encoding: " + enc + " based on language: " + subslang + " seems to be valid.", xbmc.LOGINFO)
            except Exception as e:
                # reading based on assigned language encoding failed
                enc = ""

    # if identification tries failed, try a list of encodings as a last resort
    if not enc:
        # list of encodings to try
        # the last position should be "NO_MATCH" to detect end of list
        # https://msdn.microsoft.com/en-us/library/windows/desktop/dd317756(v=vs.85).aspx
        # https://stackoverflow.com/questions/436220/determine-the-encoding-of-text-in-python
        encodings = [ "utf-8", "cp1250", "cp1251", "cp1252", "cp1253", "cp1254", "cp1255", "cp1256", "cp1257", "cp1258", "NO_MATCH" ]

        common.Log("Trying a list of encodings.", xbmc.LOGINFO)
        # try to detect valid encoding
        # this actually detects the first encoding which allows a file to be read without errors
        for enc in encodings:
            try:
                with codecs.open(tempinputfile, mode="rb", encoding=enc) as reader:
                    temp = reader.read()
                    break
            except Exception as e:
                # no encoding fits the file
                if enc == "NO_MATCH":
                    break
                # encoding does not match
                common.Log("Input file test for: " + enc + " failed.", xbmc.LOGINFO)
                continue

        # no encodings match
        if enc == "NO_MATCH":
            common.Log("No tried encodings match input file.", xbmc.LOGNOTICE)
            # subtitle processing aborted
            return

    common.Log("Input encoding used: " + enc, xbmc.LOGINFO)
    common.Log("          Input FPS: " + str(playingFps), xbmc.LOGINFO)

    # load input_file into pysubs2 library
    subs = pysubs2.load(tempinputfile, encoding=enc, fps=float(playingFps))

    # translate foreground color to RGB
    if common.setting_ForegroundColor == 0:
        # black
        Foreground_R = 0
        Foreground_G = 0
        Foreground_B = 0
    elif common.setting_ForegroundColor == 1:
        # grey
        Foreground_R = 128
        Foreground_G = 128
        Foreground_B = 128
    elif common.setting_ForegroundColor == 2:
        # purple
        Foreground_R = 255
        Foreground_G = 0
        Foreground_B = 255
    elif common.setting_ForegroundColor == 3:
        # blue
        Foreground_R = 0
        Foreground_G = 0
        Foreground_B = 255
    elif common.setting_ForegroundColor == 4:
        # green
        Foreground_R = 0
        Foreground_G = 255
        Foreground_B = 0
    elif common.setting_ForegroundColor == 5:
        # red
        Foreground_R = 255
        Foreground_G = 0
        Foreground_B = 0
    elif common.setting_ForegroundColor == 6:
        # light blue
        Foreground_R = 0
        Foreground_G = 255
        Foreground_B = 255
    elif common.setting_ForegroundColor == 7:
        # yellow
        Foreground_R = 255
        Foreground_G = 255
        Foreground_B = 0
    elif common.setting_ForegroundColor == 8:
        # white
        Foreground_R = 255
        Foreground_G = 255
        Foreground_B = 255

    # translate background color to RGB
    if common.setting_BackgroundColor == 0:
        # black
        Background_R = 0
        Background_G = 0
        Background_B = 0
    elif common.setting_BackgroundColor == 1:
        # grey
        Background_R = 128
        Background_G = 128
        Background_B = 128
    elif common.setting_BackgroundColor == 2:
        # purple
        Background_R = 255
        Background_G = 0
        Background_B = 255
    elif common.setting_BackgroundColor == 3:
        # blue
        Background_R = 0
        Background_G = 0
        Background_B = 255
    elif common.setting_BackgroundColor == 4:
        # green
        Background_R = 0
        Background_G = 255
        Background_B = 0
    elif common.setting_BackgroundColor == 5:
        # red
        Background_R = 255
        Background_G = 0
        Background_B = 0
    elif common.setting_BackgroundColor == 6:
        # light blue
        Background_R = 0
        Background_G = 255
        Background_B = 255
    elif common.setting_BackgroundColor == 7:
        # yellow
        Background_R = 255
        Background_G = 255
        Background_B = 0
    elif common.setting_BackgroundColor == 8:
        # white
        Background_R = 255
        Background_G = 255
        Background_B = 255

    # calculate transparency
    # division of integers always gives integer
    Background_T = int((common.setting_BackgroundTransparency * 255) / 100)

    # change subs style
    subs.styles["Default"].primarycolor = pysubs2.Color(Foreground_R, Foreground_G, Foreground_B, 0)
    subs.styles["Default"].secondarycolor = pysubs2.Color(Foreground_R, Foreground_G, Foreground_B, 0)
    subs.styles["Default"].outlinecolor = pysubs2.Color(Background_R, Background_G, Background_B, Background_T)
    subs.styles["Default"].backcolor = pysubs2.Color(0, 0, 0, 0)
    subs.styles["Default"].fontsize = common.setting_SubsFontSize
    subs.styles["Default"].bold = -1
    subs.styles["Default"].borderstyle = 3
    subs.styles["Default"].shadow = 0

    # process subs contents
    # iterate over every sub line and process its text
    # http://pythonhosted.org/pysubs2/api-reference.html#ssafile-a-subtitle-file

    # load regexp definitions from file
    common.Log("Definitions file used: " + deffilename, xbmc.LOGINFO)
    if common.setting_RemoveCCmarks:
        # load CCmarks definitions
        CCmarksList = GetDefinitions("CCmarks")

    if common.setting_RemoveAds:
        # load Ads definitions
        AdsList = GetDefinitions("Ads")
        # load country specific definitions only if language was detected
        if subslang:
            AdsList += GetDefinitions("Ads_" + subslang)

    # iterate over every line of subtitles and process each subtitle line
    common.Log("Applying filtering lists.", xbmc.LOGINFO)

    # if nextlinestart == 0 then we are on the beginning of the list (last subtitle as list is reversed)
    nextlinestart = 0
    # iterate from last to first element to avoid skipping elements if current element was removed
    # https://stackoverflow.com/questions/14267722/python-list-remove-skips-next-element-in-list/14283447#14283447
    for line in reversed(subs):
        # load single line to temp variable for processing
        subsline = line.text.encode('utf-8')

        RemoveWhitespaces(subsline)

        # process subtitle line
        common.Log("Subtitle line: " + subsline, xbmc.LOGDEBUG)
        if common.setting_RemoveCCmarks:
            # remove CC texts from subsline
            subsline = RemoveStrings(subsline, CCmarksList)
        if common.setting_RemoveAds:
            # remove Advertisement strings from subsline
            subsline = RemoveStrings(subsline, AdsList)

        RemoveWhitespaces(subsline)

        # if line is empty after processing, remove line from subtitles file
        # https://stackoverflow.com/questions/9573244/most-elegant-way-to-check-if-the-string-is-empty-in-python
        if not subsline:
            # remove empty line
            subs.remove(line)
            common.Log("    Resulting line is empty. Removing from file.", xbmc.LOGDEBUG)
        else:
            # increase line spacing if subtitle is multiline
            # use Max Deryagin's solution: https://www.md-subs.com/line-spacing-in-ssa
            # FIXME - currently only 2-line is supported
            # check if subtitle is multiline
            if common.setting_MaintainBiggerLineSpacing and re.search(r"\N", subsline):
                # line is multiline - add tags
                subsline = r"{\org(-2000000,0)\fr0.00012}" + subsline
                subsline = subsline.replace(r"\N", r"{\r}\N")

            # adjust minimum subtitle display time
            # if calculated time is longer than actual time and if it does not overlap next sub time
            if common.setting_AdjustSubDisplayTime:
                # calculation formula for chars per second
                # https://backlothelp.netflix.com/hc/en-us/articles/219375728-English-Template-Timed-Text-Style-Guide
                # 500 ms for line + 67 ms per each character (15 chars per second)
                minCalcLength = 500 + (len(subsline) * 67)

                common.Log("    Actual length: " + str(line.duration) + " ms", xbmc.LOGDEBUG)
                common.Log("    Min. calculated length: " + str(minCalcLength) + " ms", xbmc.LOGDEBUG)

                # check next subtitle start time and compare it to this subtitle end time
                ## https://stackoverflow.com/questions/1011938/python-previous-and-next-values-inside-a-loop
                if nextlinestart != 0:
                    # if it is not the last subtitle (first on indexed list), calculate gap to next subtitle (previous on indexed list) object
                    #
                    # compare the next subtitle's start time with this subtitle's end time
                    nextlineclearance = nextlinestart - line.end
                    common.Log("    Clearance to next sub: " + str(nextlineclearance) + " ms", xbmc.LOGDEBUG)

                    if nextlineclearance < 2:
                        if common.setting_FixOverlappingSubDisplayTime:
                            line.duration = line.duration + nextlineclearance - 2
                            common.Log("    Time subtracted from subtitle duration: " + str(2 - nextlineclearance) + " ms", xbmc.LOGDEBUG)

                    elif minCalcLength > line.duration:
                        # calculate amount of time to increase visibility of subtitle to reach minimum time
                        expectedincrease = minCalcLength - line.duration

                        # find amount of time to safely increase subtitle display length
                        if nextlinestart != 0:
                            # calculate time increase that will satisfy expectedincrease but still does not overlap next subtitle
                            # maintain a gap of at least 2ms
                            timetoincrease = min(nextlineclearance, expectedincrease) - 2
                        else:
                            # for the last subtitle, there is no limitation of next subtitle start time, so increase to minimum calculated time
                            timetoincrease = expectedincrease

                        # check if line.duration is positive as negative line.duration will raise ValueError in pysubs2 library
                        if line.duration < 0:
                            line.duration = 0
                        # timetoincrease should be positive as well
                        if timetoincrease < 0:
                            timetoincrease = 0

                        # modify subtitle object
                        line.duration = line.duration + timetoincrease
                        common.Log("    Time added to subtitle duration: " + str(timetoincrease) + " ms", xbmc.LOGDEBUG)

                # remember start time of subtitle
                nextlinestart = line.start


            # save changed line
            line.plaintext = subsline.decode('utf-8')

    common.Log("Filtering lists applied.", xbmc.LOGINFO)

    #save subs
    subs.save(tempoutputfile)

    # wait until file is saved
    wait_for_file(tempoutputfile, True)

    # record end time of processing
    MangleEndTime = time.time()

    # truncating seconds: https://stackoverflow.com/questions/8595973/truncate-to-3-decimals-in-python/8595991#8595991
    common.Log("Subtitle file processing finished. Processing took: " + '%.3f'%(MangleEndTime - MangleStartTime) + " seconds.", xbmc.LOGNOTICE)

    # FIXME - debug check if file is already released
    try:
        fp = open(tempoutputfile)
        fp.close()
    except Exception as e:
        common.Log("tempoutputfile NOT released.", xbmc.LOGERROR)
        common.Log("Exception: " + str(e.message), xbmc.LOGERROR)

    # copy new file back to its original location changing only its extension
    filebase, fileext = os.path.splitext(originalinputfile)
    originaloutputfile = filebase + '.ass'
    copy_file(tempoutputfile, originaloutputfile)

    # make a backup copy of subtitle file or remove file
    if common.setting_BackupOldSubs:
        rename_file(originalinputfile, originalinputfile + '_backup')
    else:
        delete_file(originalinputfile)

    return originaloutputfile



def RemoveWhitespaces(subsline):
    """Removes unnecessary whitespaces from processed line

    Arguments:
        subsline {str} -- text to be processed
    """

    # remove orphan whitespaces from beginning and end of line
    subsline = subsline.strip()
    # convert double or more whitespaces to single ones
    subsline = re.sub(' {2,}', ' ', subsline)

    return subsline



# copy function
def copy_file(srcFile, dstFile):
    """Copy file using xbmcvfs.

    Arguments:
        srcFile {str} -- source file
        dstFile {str} -- destination file
    """

    try:
        common.Log("copy_file: srcFile: " + srcFile, xbmc.LOGINFO)
        common.Log("           dstFile: " + dstFile, xbmc.LOGINFO)
        if xbmcvfs.exists(srcFile):
            #FIXME - debug
            common.Log("copy_file: srcFile exists.", xbmc.LOGINFO)
        if xbmcvfs.exists(dstFile):
            common.Log("copy_file: dstFile exists. Trying to remove.", xbmc.LOGINFO)
            delete_file(dstFile)
        else:
            common.Log("copy_file: dstFile does not exist.", xbmc.LOGINFO)
        common.Log("copy_file: Copy started.", xbmc.LOGINFO)

        # as xbmcvfs.copy() sometimes fails, make more tries to check if lock is permanent - test only
        counter = 0
        success = 0
        while not (success != 0 or counter >= 3):
            success = xbmcvfs.copy(srcFile, dstFile)
            common.Log("copy_file: SuccessStatus: " + str(success), xbmc.LOGINFO)
            counter += 1
            xbmc.sleep(500)
        if counter > 1:
            common.Log("copy_file: First copy try failed. Number of tries: " + str(counter), xbmc.LOGWARNING)

        # #FIXME - debug
        # filehandle = xbmcvfs.File(srcFile)
        # buffer = filehandle.read()
        # filehandle.close()
        # Log("File data read: " + str(buffer), xbmc.LOGINFO)
        # filehandle = xbmcvfs.File(dstFile, 'w')
        # result = filehandle.write(buffer)
        # filehandle.close()
        # Log("File data write result: " + str(result), xbmc.LOGINFO)

    except Exception as e:
        common.Log("copy_file: Copy failed.", xbmc.LOGERROR)
        common.Log("Exception: " + str(e), xbmc.LOGERROR)

    wait_for_file(dstFile, True)



# rename function
def rename_file(oldfilepath, newfilepath):
    """Rename file using xbmcvfs.

    Arguments:
        oldfilepath {str} -- old file name
        newfilepath {str} -- new file name
    """

    try:
        common.Log("rename_file: srcFile: " + oldfilepath, xbmc.LOGINFO)
        common.Log("             dstFile: " + newfilepath, xbmc.LOGINFO)
        # check if new file already exists as in this case rename will fail
        if xbmcvfs.exists(newfilepath):
            common.Log("rename_file: dstFile exists. Trying to remove.", xbmc.LOGINFO)
            delete_file(newfilepath)
        else:
            common.Log("rename_file: dstFile does not exist.", xbmc.LOGINFO)
        # rename file
        success = xbmcvfs.rename(oldfilepath, newfilepath)
        common.Log("rename_file: SuccessStatus: " + str(success), xbmc.LOGINFO)
    except Exception as e:
        common.Log("Can't rename file: " + oldfilepath, xbmc.LOGERROR)
        common.Log("Exception: " + str(e.message), xbmc.LOGERROR)



# delete function
def delete_file(filepath):
    """Delete file using xbmcvfs.

    Arguments:
        filepath {str} -- file to delete
    """

    try:
        xbmcvfs.delete(filepath)
        common.Log("delete_file: File deleted: " + filepath, xbmc.LOGINFO)
    except Exception as e:
        common.Log("delete_file: Delete failed: " + filepath, xbmc.LOGERROR)
        common.Log("Exception: " + str(e.message), xbmc.LOGERROR)

    wait_for_file(filepath, False)



# function waits for file to appear or disappear, test purpose
def wait_for_file(file, exists):
    """Wait for file to appear or disappear.

    Arguments:
        file {str} -- file to watch
        exists {bool} -- True -> wait to appear; False -> wait to disappear

    Returns:
        bool -- True -> if successed
    """

    success = False
    if exists:
        common.Log("wait_for_file: if file exists: " + file, xbmc.LOGINFO)
    else:
        common.Log("wait_for_file: if file doesn't exist: " + file, xbmc.LOGINFO)

    count = 10
    while count:
        xbmc.sleep(500)  # this first sleep is intentional
        if exists:
            if xbmcvfs.exists(file):
                common.Log("wait_for_file: file appeared.", xbmc.LOGINFO)
                success = True
                break
        else:
            if not xbmcvfs.exists(file):
                common.Log("wait_for_file: file vanished.", xbmc.LOGINFO)
                success = True
                break
        count -= 1
    if not success:
        if exists:
            common.Log("wait_for_file: file DID NOT appear.", xbmc.LOGERROR)
        else:
            common.Log("wait_for_file: file DID NOT vanish.", xbmc.LOGERROR)
        return False
    else:
        return True



# get all subtitle file names in current directory contents for those matching video being played
# get 'noautosubs' file or extension in order to match per directory or per file behaviour
def GetSubtitleFiles(subspath, substypelist):
    """Get subtitle file names. Includes 'noautosubs' file and '.noautosubs' extension.

    Arguments:
        subspath {str} -- path to list files from
        substypelist {list} -- list of file extensions to include

    Returns:
        list -- list of files
    """

    # use dictionary solution - load all files in directory to dictionary and remove those not fulfiling criteria
    # Python doesn't support smb:// paths. Use xbmcvfs: https://forum.kodi.tv/showthread.php?tid=211821
    dirs, files = xbmcvfs.listdir(subtitlePath)
    SubsFiles = dict ([(f, None) for f in files])
    # filter dictionary, leaving only subtitle files matching played video
    # https://stackoverflow.com/questions/5384914/how-to-delete-items-from-a-dictionary-while-iterating-over-it
    playingFilenameBase, playingFilenameExt = os.path.splitext(playingFilename)

    for item in SubsFiles.keys():
        # split file and extension
        subfilebase, subfileext = os.path.splitext(item)
        # from filename split language designation
        subfilecore, subfilelang = os.path.splitext(subfilebase)
        # remove files that do not meet criteria
        if not ((((subfilebase.lower() == playingFilenameBase.lower() or subfilecore.lower() == playingFilenameBase.lower()) and (subfileext.lower() in substypelist)) \
            or ((subfilebase.lower() == playingFilenameBase.lower()) and (subfileext.lower() == ".noautosubs"))) \
            or (subfilebase.lower() == "noautosubs")):
            # NOT
            # subfilename matches video name AND fileext is on the list of supported extensions
            # OR subfilename matches video name AND fileext matches '.noautosubs'
            # OR subfilename matches 'noautosubs'
            # FIXME - now we assume that .ass subtitle will not be processed
            del SubsFiles[item]

    return SubsFiles



# pause playback
def PlaybackPause():
    """Pause playback if not paused."""

    # pause playback
    if not xbmc.getCondVisibility("player.paused"):
        xbmc.Player().pause()
        common.Log("Playback PAUSED.", xbmc.LOGINFO)
    else:
        common.Log("Playback already PAUSED.", xbmc.LOGINFO)



# resume playback
def PlaybackResume():
    """Resume playback if paused."""

    # resume playback
    if xbmc.getCondVisibility("player.paused"):
        common.Log("Playback is paused. Resuming.", xbmc.LOGINFO)
        xbmc.Player().pause()
        common.Log("Playback RESUMED.", xbmc.LOGINFO)
    else:
        common.Log("Playback not paused. No need to resume.", xbmc.LOGINFO)



# check if any files matching video being played are changed
# http://timgolden.me.uk/python/win32_how_do_i/watch_directory_for_changes.html
def DetectNewSubs():
    """Detect new subtitle files matching video name being played."""

    global DetectionIsRunning
    global SubsSearchWasOpened
    global subtitlePath

    # if function is already running, exit this instance
    if DetectionIsRunning:
        #Log("Duplicate DetectNewSubs call.", LogWARNING)
        return

    # stop timer in order to not duplicate threads
    #rt.stop()

    # setting process flag, process starts to run
    DetectionIsRunning = True

    # load all subtitle files matching video being played
    # also returns 'noautosubs' file and '.noautosubs' extension
    RecentSubsFiles = GetSubtitleFiles(subtitlePath, SubExtList)

    # check all remaining subtitle files for changed timestamp
    for f in RecentSubsFiles:
        # ignore 'noautosubs' file/extension to not trigger detection of subtitles
        if f[-10:].lower() == "noautosubs":
            continue

        pathfile = os.path.join(subtitlePath, f)
        epoch_file = xbmcvfs.Stat(pathfile).st_mtime()
        epoch_now = time.time()

        # check current directory contents for unprocessed subtitle files touched no later than a few seconds ago
        # or optionally for all unprocessed subtitle files
        if (epoch_file > epoch_now - 6) or common.setting_AlsoConvertExistingSubtitles:
            # Video filename matches subtitle filename
            # and either it was created/modified no later than 6 seconds ago or existing subtitles are taken into account as well
            common.Log("New subtitle file detected: " + pathfile, xbmc.LOGNOTICE)

            common.Log("Subtitles processing routine started.", xbmc.LOGNOTICE)
            # record start time of processing
            RoutineStartTime = time.time()

            # clear storage dir from subtitle files
            tempfilelist = [f for f in os.listdir(common.__addonworkdir__) if os.path.isfile(os.path.join(common.__addonworkdir__, f))]
            common.Log("Clearing temporary files.", xbmc.LOGINFO)
            for item in tempfilelist:
                filebase, fileext = os.path.splitext(item)
                if (fileext.lower() in SubExtList) or fileext.lower().endswith(".ass"):
                    os.remove(os.path.join(common.__addonworkdir__, item))
                    common.Log("       File: " + os.path.join(common.__addonworkdir__, item) + "  removed.", xbmc.LOGINFO)

            # hide subtitles
            xbmc.Player().showSubtitles(False)

            if common.setting_PauseOnConversion:
                # show busy animation
                # https://forum.kodi.tv/showthread.php?tid=280621&pid=2363462#pid2363462
                # https://kodi.wiki/view/Window_IDs
                # busydialog is going away in Kodi 18 - https://forum.kodi.tv/showthread.php?tid=333950&pid=2754978#pid2754978
                if int(common.__kodiversion__[:2]) == 17:
                    xbmc.executebuiltin('ActivateWindow(busydialog)')  # busydialog on - Kodi 17
                else:
                     if int(common.__kodiversion__[:2]) >= 18:
                        xbmc.executebuiltin('ActivateWindow(busydialognocancel)')  # busydialog on - Kodi 18

                # pause playback
                PlaybackPause()

            # process subtitle file
            ResultFile = MangleSubtitles(pathfile)
            common.Log("Output subtitle file: " + ResultFile, xbmc.LOGNOTICE)

            # check if destination file exists
            if xbmcvfs.exists(ResultFile):
                common.Log("Subtitles available.", xbmc.LOGNOTICE)

                # load new subtitles and turn them on
                xbmc.Player().setSubtitles(ResultFile)

                # resume playback
                PlaybackResume()
            else:
                common.Log("Subtitles NOT available.", xbmc.LOGNOTICE)

            # hide busy animation
            # https://forum.kodi.tv/showthread.php?tid=280621&pid=2363462#pid2363462
            if int(common.__kodiversion__[:2]) == 17:
                xbmc.executebuiltin('Dialog.Close(busydialog)')  # busydialog off - Kodi 17
            else:
                if int(common.__kodiversion__[:2]) >= 18:
                    xbmc.executebuiltin('Dialog.Close(busydialognocancel)')  # busydialog off - Kodi 18

            # record end time of processing
            RoutineEndTime = time.time()

            # truncating seconds: https://stackoverflow.com/questions/8595973/truncate-to-3-decimals-in-python/8595991#8595991
            common.Log("Subtitles processing routine finished. Processing took: " + '%.3f'%(RoutineEndTime - RoutineStartTime) + " seconds.", xbmc.LOGNOTICE)

            # clear subtitles search dialog flag to make sure that YesNo dialog will not be triggered
            SubsSearchWasOpened = False

            # sleep for 10 seconds to avoid processing newly added subititle file
            #this should not be needed since we do not support .ass as input file at the moment
            #xbmc.sleep(10000)

    # check if subtitles search window was opened but there were no new subtitles processed
    if SubsSearchWasOpened:
        if not common.setting_NoConfirmationInvokeIfDownloadedSubsNotFound:
            common.Log("Subtitles search window was opened but no new subtitles were detected. Opening YesNo dialog.", xbmc.LOGINFO)

            # pause playbcak
            PlaybackPause()

            # display YesNo dialog
            # http://mirrors.xbmc.org/docs/python-docs/13.0-gotham/xbmcgui.html#Dialog-yesno
            YesNoDialog = xbmcgui.Dialog().yesno("Subtitles Mangler", common.__addonlang__(32040).encode('utf-8'), line2=common.__addonlang__(32041).encode('utf-8'), nolabel=common.__addonlang__(32042).encode('utf-8'), yeslabel=common.__addonlang__(32043).encode('utf-8'))
            if YesNoDialog:
                # user does not want the subtitle search dialog to appear again for this file
                common.Log("Answer is Yes. Setting .noautosubs extension flag for file: " + playingFilenamePath.encode('utf-8'), xbmc.LOGINFO)

                # set '.noautosubs' extension for file being played
                filebase, fileext = os.path.splitext(playingFilenamePath)
                # create .noautosubs file
                common.CreateNoAutoSubsFile(filebase + ".noautosubs")

            else:
                # user wants the dialog to appear again next time the video is played
                common.Log("Answer is No. Doing nothing.", xbmc.LOGINFO)

            # resume playback
            PlaybackResume()

        else:
            common.Log("Subtitles search window was opened and no new subtitles were detected, but configuration prevents YesNo dialog from opening.", xbmc.LOGINFO)

        # clear the flag to prevent opening dialog on next call of DetectNewSubs()
        SubsSearchWasOpened = False

    # clearing process flag, process is not running any more
    DetectionIsRunning = False



# get information on file currently being played
# http://kodi.wiki/view/InfoLabels
def GetPlayingInfo():
    """Get information on file being played.

    Returns:
        subspath {str} -- subtitle file directory location
        filename {str} -- video file name being played
        filepathname {str} -- video file name being played including full path
        filefps {str} -- file fps
        audiolang {str} -- audio language designation
        filelang {str} -- subtitle language designation
    """

    # get settings from Kodi configuration on assumed subtitles location
    storagemode = GetKodiSetting("subtitles.storagemode") # 1=location defined by custompath; 0=location in movie dir
    custompath = GetKodiSetting("subtitles.custompath")   # path to non-standard dir with subtitles

    if storagemode == 1:    # location == custompath
        if xbmcvfs.exists(custompath):
            subspath = custompath
        else:
            subspath = xbmc.translatePath("special://temp")
    else:   # location == movie dir
        subspath = xbmc.getInfoLabel('Player.Folderpath')

    # get video details
    filename = xbmc.getInfoLabel('Player.Filename')
    filepathname = xbmc.getInfoLabel('Player.Filenameandpath')
    filefps = xbmc.getInfoLabel('Player.Process(VideoFPS)')
    audiolang = xbmc.getInfoLabel('VideoPlayer.AudioLanguage')
    filelang = xbmc.getInfoLabel('VideoPlayer.SubtitlesLanguage')

    common.Log("File currently played: " + filepathname, xbmc.LOGINFO)
    common.Log("Subtitles download path: " + subspath, xbmc.LOGINFO)
    common.Log("Audio language: " + audiolang, xbmc.LOGINFO)
    common.Log("Subtitles language (either internal or external): " + filelang, xbmc.LOGINFO)

    return subspath, filename, filepathname, filefps, audiolang, filelang



# updates regexdef file from server
def UpdateDefFile():
    """Update regex definitions file from server."""

    common.Log("Trying to update regexp definitions from: " + deffileurl, xbmc.LOGINFO)
    # download file from server
    # http://stackabuse.com/download-files-with-python/
    try:
        filedata = urllib2.urlopen(deffileurl)
        datatowrite = filedata.read()
        with open(tempdeffilename, 'wb') as f:
            f.write(datatowrite)

        # check if target file path exists
        if os.path.isfile(localdeffilename):
            # compare if downloaded temp file and current local file are identical
            if filecmp.cmp(tempdeffilename, localdeffilename, shallow=0):
                common.Log("Definitions file is up-to-date. Skipping update.", xbmc.LOGINFO)
            else:
                # remove current target file
                common.Log("Found different definitions file. Removing current file: " + localdeffilename, xbmc.LOGINFO)
                os.remove(localdeffilename)
                # copy temp file to target file
                copyfile(tempdeffilename, localdeffilename)
                common.Log("Regex definitions updated.", xbmc.LOGINFO)
        else:
            # copy temp file to target file
            copyfile(tempdeffilename, localdeffilename)
            common.Log("Regex definitions updated.", xbmc.LOGINFO)

        # remove temp file
        os.remove(tempdeffilename)

    except OSError as e:
        common.Log("Can not remove temporary definitions file: " + tempdeffilename, xbmc.LOGERROR)
    except urllib2.URLError as e:
        common.Log("Can not download definitions: " + deffileurl, xbmc.LOGERROR)
        common.Log("Exception: " + str(e.reason), xbmc.LOGERROR)
    except IOError as e:
        common.Log("Can not copy definitions file to: " + localdeffilename, xbmc.LOGERROR)



# walk through video sources and remove any subtitle files that do not acompany its own video any more
# also remove '.noautosubs' files
def RemoveOldSubs():
    """Remove unneeded subtitle files from video source directories."""


    # Uses XBMC/Kodi JSON-RPC API to retrieve video sources location
    # https://kodi.wiki/view/JSON-RPC_API/v8#Files.GetSources
    command = '''{
    "jsonrpc": "2.0",
    "id": 1,
    "method": "Files.GetSources",
    "params": {
        "media": "video"
    }
}'''
    result = xbmc.executeJSONRPC(command)
    sources = loads(result).get('result').get('sources')
    common.Log("JSON-RPC: Files.GetSources: " + str(sources), xbmc.LOGDEBUG)

    common.Log("Scanning video sources for orphaned subtitle files.", xbmc.LOGNOTICE)
    # record start time
    ClearStartTime = time.time()

    # create background dialog
    # http://mirrors.kodi.tv/docs/python-docs/13.0-gotham/xbmcgui.html#DialogProgressBG
    pDialog = xbmcgui.DialogProgressBG()
    pDialog.create('Subtitles Mangler', common.__addonlang__(32090).encode('utf-8'))

    # initiate empty lists
    videofiles = list()
    subfiles = list()

    # construct target list for file candidate extensions to be removed
    # remove processed subs and .noautosubs files
    extRemovalList = [ '.ass', '.noautosubs' ]
    # remove processed subs backup files
    if common.setting_RemoveSubsBackup:
        for ext in SubExtList:
            extRemovalList.append(ext + '_backup')
    # remove unprocessed subs
    if common.setting_RemoveUnprocessedSubs:
        for ext in SubExtList:
            extRemovalList.append(ext)

    # count number of sources
    # calculate progressbar increase per source
    progress = 0
    pIncrease = 80 / len(sources)

    # process every source path
    for source in sources:
        startdir = source.get('file')
        common.Log("Processing source path: " + startdir, xbmc.LOGINFO)

        # update background dialog
        progress += pIncrease
        pDialog.update(progress, message=common.__addonlang__(32090).encode('utf-8') + ': ' + source.get('label').encode('utf-8'))

        # http://code.activestate.com/recipes/435875-a-simple-non-recursive-directory-walker/
        directories = [startdir]
        while len(directories)>0:
            # take one element from directories list and process it
            directory = directories.pop()
            dirs, files = xbmcvfs.listdir(directory)
            # add every subdir to the list for checking
            for subdir in dirs:
                common.Log("Adding subpath: " + os.path.join(directory, subdir.decode('utf-8')), xbmc.LOGDEBUG)
                directories.append(os.path.join(directory, subdir.decode('utf-8')))
            # check every file in the current subdir and add it to appropriate list
            for thisfile in files:
                fullfilepath = os.path.join(directory, thisfile.decode('utf-8'))
                filebase, fileext = os.path.splitext(fullfilepath)
                if fileext in VideoExtList:
                    # this file is video - add to video list
                    common.Log("Adding to video list: " + fullfilepath.encode('utf-8'),xbmc.LOGDEBUG)
                    videofiles.append(fullfilepath)
                elif fileext in extRemovalList:
                    # this file is subs related - add to subs list
                    common.Log("Adding to subs list: " + fullfilepath.encode('utf-8'),xbmc.LOGDEBUG)
                    subfiles.append(fullfilepath)

    # process custom subtitle path if it is set in Kodi configuration
    # get settings from Kodi configuration on assumed subtitles location
    storagemode = GetKodiSetting("subtitles.storagemode") # 1=location defined by custompath; 0=location in movie dir
    custompath = GetKodiSetting("subtitles.custompath")   # path to non-standard dir with subtitles

    if storagemode == 1:    # location == custompath
        if xbmcvfs.exists(custompath):
            subspath = custompath
        else:
            subspath = ""
    else:   # location == movie dir
        subspath = ""

    if subspath:
        common.Log("Scanning for orphaned subtitle files on custom path: " + subspath, xbmc.LOGNOTICE)
        dirs, files = xbmcvfs.listdir(subspath)
        for thisfile in files:
            fullfilepath = os.path.join(subspath, thisfile.decode('utf-8'))
            filebase, fileext = os.path.splitext(fullfilepath)
            if fileext in extRemovalList:
                # this file is subs related - add to subs list
                common.Log("Adding to subs list: " + fullfilepath,xbmc.LOGDEBUG)
                subfiles.append(fullfilepath)

    # record scan time
    ClearScanTime = time.time()
    common.Log("Scanning for orphaned subtitle files finished. Processing took: " + '%.3f'%(ClearScanTime - ClearStartTime) + " seconds.", xbmc.LOGNOTICE)
    common.Log("Clearing orphaned subtitle files.", xbmc.LOGNOTICE)
    # update background dialog
    pDialog.update(85, message=common.__addonlang__(32091).encode('utf-8'))

    # lists filled, compare subs list with video list
    for subfile in subfiles:
        # split filename from full path
        subfilename = os.path.basename(subfile)
        # split filename and extension
        subfilebase, subfileext = os.path.splitext(subfilename)
        # from filename split language designation
        subfilecore, subfilelang = os.path.splitext(subfilebase)

        # check if there is a video matching subfile
        videoexists = False
        for videofile in videofiles:
            # split filename from full path
            videofilename = os.path.basename(videofile)
            # split filename and extension
            videofilebase, videofileext = os.path.splitext(videofilename)

            # check if subfile basename or corename equals videofile basename
            if subfilebase.lower() == videofilebase.lower() or subfilecore.lower() == videofilebase.lower():
                videoexists = True
                break

        if not videoexists:
            if common.setting_SimulateRemovalOnly:
                common.Log("There is no video file matching: " + subfile.encode('utf-8') + "  File would have been deleted if Simulate option had been off.", xbmc.LOGNOTICE)
            else:
                common.Log("There is no video file matching: " + subfile.encode('utf-8') + "  Deleting it.", xbmc.LOGNOTICE)
                delete_file(subfile)
        else:
            common.Log("Video file matching: " + subfile.encode('utf-8'), xbmc.LOGDEBUG)
            common.Log("              found: " + videofile.encode('utf-8'), xbmc.LOGDEBUG)

    # record end time
    ClearEndTime = time.time()
    common.Log("Clearing orphaned subtitle files finished. Processing took: " + '%.3f'%(ClearEndTime - ClearScanTime) + " seconds.", xbmc.LOGNOTICE)

    # close background dialog
    pDialog.close()
