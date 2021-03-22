# This file includes code for SubsMangler's core functionality

import codecs
import os
import filecmp
import re
import time
import urllib.request, urllib.error
import xbmc
import xbmcgui
import xbmcvfs
from .common import Log, GetSettings, CreateNoAutoSubsFile, InitiateLogger
from resources.lib import globals
from json import loads
from shutil import copyfile
from threading import Timer
import pysubs2


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
        # self.start()  #do not start automatically

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

    def __init__(self, *args):
        pass

    def onPlayBackStarted(self):
        # Will be called when xbmc player is created
        # however stream may not be available at this point
        # for Kodi 18 use onAVStarted
        if int(globals.__kodiversion__[:2]) == 17:
            GetSubtitles()

    def onAVStarted(self):
        # Will be called when xbmc has video
        # works only on Kodi 18 onwards
        # on Kodi >= 17 onPlaybackStarted seems to be failing very often: https://forum.kodi.tv/showthread.php?tid=334929
        if int(globals.__kodiversion__[:2]) >= 18:
            GetSubtitles()

    def onPlayBackEnded(self):
        # Will be called when xbmc stops playing a file
        # player finished playing video
        Log("VideoPlayer END detected.", xbmc.LOGINFO)

        # add 15 minutes to timer in case timer was close to 0 before playback started
        # this prevents starting cleanup immediatelly after playback ended
        # 1 tick per 5 sec * 15 min = 180 ticks
        globals.ClockTick += 180

        # stop monitoring dir for changed files
        globals.rt.stop()

    def onPlayBackStopped(self):
        # Will be called when user stops xbmc playing a file
        # player has just been stopped
        Log("VideoPlayer STOP detected.", xbmc.LOGINFO)

        # add 15 minutes to timer in case timer was close to 0 before playback started
        # this prevents starting cleanup immediatelly after playback ended
        # 1 tick per 5 sec * 15 min = 180 ticks
        globals.ClockTick += 180

        # stop monitoring dir for changed files
        globals.rt.stop()


# Monitor class
# https://forum.kodi.tv/showthread.php?tid=198911&pid=1750890#pid1750890
class XBMCMonitor(xbmc.Monitor):

    def __init__(self, *args, **kwargs):
        xbmc.Monitor.__init__(self)

    def onAbortRequested(self):
        # Will be called when XBMC requests Abort
        globals.rt.stop()
        Log("Abort requested in Monitor class.", xbmc.LOGDEBUG)

    def onSettingsChanged(self):
        # Will be called when addon settings are changed
        Log("Addon settings changed.", xbmc.LOGINFO)
        # re-read settings
        GetSettings()

        # if service is not enabled any more, stop timer
        if not globals.setting_ConversionServiceEnabled:
            globals.rt.stop()


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

    xbmc.log("SubsMangler: started. Version: " + globals.__version__ + ". Kodi version: " + globals.__kodiversion__,
             level=xbmc.LOGINFO)

    # prepare datadir
    # directory and file is local to the filesystem
    # no need to use xbmcvfs
    if not os.path.isdir(globals.__addonworkdir__):
        xbmc.log("SubsMangler: profile directory doesn't exist: " + globals.__addonworkdir__ + "   Trying to create.",
                 level=xbmc.LOGINFO)
        try:
            os.mkdir(globals.__addonworkdir__)
            xbmc.log("SubsMangler: profile directory created: " + globals.__addonworkdir__, level=xbmc.LOGINFO)
        except OSError as e:
            xbmc.log("SubsMangler: Log: can't create directory: " + globals.__addonworkdir__, level=xbmc.LOGERROR)
            xbmc.log("Exception: " + str(e), xbmc.LOGERROR)

    # initiate external log handler
    InitiateLogger()

    # prepare timer to launch
    globals.rt = RepeatedTimer(2.0, DetectNewSubs)

    # get Kodi's subtitle settings
    GetKodiSubtitleSettings()

    # load addon settings
    GetSettings()

    # check if external log is configured
    if globals.setting_SeparateLogFile == 1:
        xbmc.log("SubsMangler: External log enabled: " + os.path.join(globals.__addonworkdir__, 'smangler.log'),
                 level=xbmc.LOGINFO)

    # initiate monitoring of xbmc.Player events
    globals.player = XBMCPlayer()

    # initiate monitoring of xbmc events
    globals.monitor = XBMCMonitor()


# function checks if stream is a local file and tries to find matching subtitles
# if subtitles are not found, it opens search dialog
def GetSubtitles():
    """Check if stream is a local file or online stream and launch subtitles. If subtitles are not present, open search dialog
    """
    # stop subtitle detection in case it was already running
    # this prevents YesNo dialog from showing immediatelly after opening subtitle search dialog
    # in case playback of new file is started during playback of another file without prior stopping it
    globals.rt.stop()

    # detect if Player is running by checking xbmc.Player().isPlayingVideo() or xbmc.getCondVisibility('Player.HasVideo')
    # use ConditionalVisibility checks: http://kodi.wiki/view/List_of_boolean_conditions
    if xbmc.getCondVisibility('Player.HasVideo'):
        # player has just been started, check what contents does it play and from
        Log("VideoPlayer START detected.", xbmc.LOGINFO)

        # get info on file being played
        globals.playingFilenamePath = ''
        counter = 0
        # try to read info several times as sometimes reading fails
        while not (globals.playingFilenamePath or counter >= 3):
            xbmc.sleep(500)
            globals.subtitlePath, globals.playingFilename, globals.playingFilenamePath, globals.playingFps, playingLang, playingSubs = GetPlayingInfo()
            counter += 1
        if counter > 1:
            Log("First GetPlayingInfo() read failed. Number of tries: " + str(counter), xbmc.LOGWARNING)

        # ignore streaming videos if configuration says so
        if InternetStream(globals.playingFilenamePath) and not globals.setting_AutoInvokeSubsDialogOnStream:
            Log("Video stream detected but AutoInvokeSubsDialogOnStream is disabled. Ignoring.", xbmc.LOGINFO)
            return
        elif not globals.playingFilenamePath:
            # string is empty, may happen when playing buffered streams
            Log("Empty 'playingFilenamePath' string detected. Not able to continue.", xbmc.LOGERROR)
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

        if prefaudiolanguage == 'mediadefault':
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

        Log("Kodi's GUI language: " + guilanguage, xbmc.LOGINFO)
        Log("Kodi's preferred audio language: " + prefaudiolanguage, xbmc.LOGINFO)
        Log("Kodi's preferred subtitles language: " + prefsubtitlelanguage, xbmc.LOGINFO)

        # check if there is .utf subtitle file already on disk matching video being played
        # if not, automatically open subtitlesearch dialog
        #
        # set initial value for SubsSearchWasOpened flag
        globals.SubsSearchWasOpened = False
        # check if Subtitles Search window should be opened at player start
        if globals.setting_AutoInvokeSubsDialog:
            # get all files matching name of file being played
            # also includes 'noautosubs' file and file with '.noautosubs' extension
            extlist = list()

            if globals.setting_NoAutoInvokeIfLocalUnprocSubsFound:
                # optionally search for all subtitle extensions, not only '.utf'
                # assignment operator just makes an alias for the list
                # https://stackoverflow.com/questions/2612802/how-to-clone-or-copy-a-list
                extlist = list(globals.SubExtList)

            # search for target extension '.utf'
            extlist.append('.utf')

            # get all subtitle file names from the given path
            localsubs = GetSubtitleFiles(globals.subtitlePath, extlist)

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
                        Log("No local subtitles matching video being played. Opening search dialog.", xbmc.LOGINFO)
                        # set flag to remember that subtitles search dialog was opened
                        globals.SubsSearchWasOpened = True
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
                        Log(
                            "Video or subtitle language match Kodi's preferred settings. Not opening subtitle search dialog.",
                            xbmc.LOGINFO)
                else:
                    # enable .utf subtitles if they are present on the list
                    utfsubs = False
                    for item in localsubs:
                        if ".utf" in item[-4:]:
                            Log(
                                "Local 'utf' subtitles matching video being played detected. Enabling subtitles: " + os.path.join(
                                    globals.subtitlePath, item), xbmc.LOGINFO)
                            xbmc.Player().setSubtitles(os.path.join(globals.subtitlePath, item))
                            utfsubs = True
                            break

                    if not utfsubs:
                        Log(
                            "Local non 'utf' subtitles matching video being played detected. Not opening subtitle search dialog.",
                            xbmc.LOGINFO)
            else:
                Log("'noautosubs' file or extension detected. Not opening subtitle search dialog.", xbmc.LOGINFO)
        else:
            Log("AutoInvokeSubsDialog option is disabled. Not opening subtitle search dialog", xbmc.LOGINFO)
            # enable subtitles if there are any
            xbmc.Player().showSubtitles(True)

        # check periodically if there are any files changed in monitored subdir that match file being played
        if globals.setting_ConversionServiceEnabled:
            globals.rt.start()


# function matches input string for language designation
# and outputs ISO 639-2 equivalent
# https://stackoverflow.com/questions/2879856/get-system-language-in-iso-639-3-letter-codes-in-python
# http://www.loc.gov/standards/iso639-2/ISO-639-2_utf-8.txt
def GetIsoCode(lang):
    """Find correct ISO-639-2 language code.

    Arguments:
        lang {str} -- language name, ISO-639-1 code or ISO-639-2 code

    Returns:
        str -- ISO-639-2 code
    """

    # "bibliographic" iso codes are derived from English word for the language
    # "terminologic" iso codes are derived from the pronunciation in the target
    # language (if different to the bibliographic code)

    outlang = ''

    if lang:
        # language code is not empty
        Log("Looking for language code for: " + lang, xbmc.LOGDEBUG)
        outlang = xbmc.convertLanguage(lang, xbmc.ISO_639_2)

        if outlang:
            Log("Language code found: " + outlang, xbmc.LOGDEBUG)
        else:
            Log("Language code not found.", xbmc.LOGWARNING)
    else:
        # language code is empty
        Log("Language code is empty. Skipping searching.", xbmc.LOGINFO)

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

    importedlist = list()

    # check if definitions file exists
    if os.path.isfile(globals.deffilename):
        # open file
        with open(globals.deffilename, "rt") as f:
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
                thissectionpattern = "\[" + section + "\]"  # matches: [SeCtIoNnAmE]
                othersectionpattern = "^\[.*?\]"  # matches: <BEGINLINE>[anything]
                if re.search(thissectionpattern, line, re.IGNORECASE):
                    # beginning of our section
                    thissection = True
                elif re.search(othersectionpattern, line):  # matches: <BEGINLINE>[anything]
                    # beginning of other section
                    thissection = False
                elif thissection:
                    # contents of our section - import to list
                    # check if line is not empty, empty line is "falsy"
                    # https://stackoverflow.com/questions/9573244/most-elegant-way-to-check-if-the-string-is-empty-in-python
                    if line:
                        # add to list
                        importedlist.append(line)

        Log("Definitions imported. Section: " + section, xbmc.LOGINFO)
        # dump imported list
        for entry in importedlist:
            Log("       " + entry, xbmc.LOGDEBUG)
    else:
        Log("Definitions file does not exist: " + globals.deffilename, xbmc.LOGINFO)

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
                Log("    matches regex: " + pattern, xbmc.LOGDEBUG)
                line = re.sub(pattern, '', line, flags=re.I)
                Log("    Resulting string: " + line, xbmc.LOGDEBUG)
        except Exception as e:
            Log("    Regex error: '" + str(e) + "' in Regex: " + pattern, xbmc.LOGERROR)

    return line


# get Kodi subtitle settings
def GetKodiSubtitleSettings():
    """
    load Kodi's subtitle settings and save them to local addon settings
    """
    Log("Reading Kodi's subtitle settings and writing the local copy", xbmc.LOGDEBUG)
    globals.__addon__.setSetting("FontSize", str(GetKodiSetting('subtitles.height')))
    globals.__addon__.setSetting("FontStyle", str(GetKodiSetting('subtitles.style')))
    globals.__addon__.setSetting("FontColor", str(GetKodiSetting('subtitles.color')))
    globals.__addon__.setSetting("FontOpacity", str(GetKodiSetting('subtitles.opacity')))
    globals.__addon__.setSetting("BackgroundColor", str(GetKodiSetting('subtitles.bgcolor')))
    globals.__addon__.setSetting("BackgroundOpacity", str(GetKodiSetting('subtitles.bgopacity')))


# get Kodi system setting
# https://forum.kodi.tv/showthread.php?tid=209587&pid=1844182#pid1844182
def GetKodiSetting(name):
    """Get Kodi setting value from given section name.

    Arguments:
        name {str} -- Kodi section name

    Returns:
        str -- setting value
    """

    # Uses XBMC/Kodi JSON-RPC API to retrieve values.
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
    Log("JSON-RPC: Settings.GetSettingValue: " + str(py), xbmc.LOGDEBUG)
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
        Log("File does not exist: " + originalinputfile, xbmc.LOGERROR)
        return

    # get subtitles language by splitting it from filename
    # split file and extension
    subfilebase, _subfileext = os.path.splitext(originalinputfile)
    # from filename split language designation
    _subfilecore, subfilelang = os.path.splitext(subfilebase)

    Log("Read subtitle language designation: " + subfilelang[1:], xbmc.LOGINFO)
    # try to find ISO639-2 designation
    # remove dot from language code ('.en')
    subslang = GetIsoCode(subfilelang.lower()[1:]).lower()

    # as pysubs2 library doesn't support Kodi's virtual file system and file can not be processed remotely on smb:// share,
    # file must be copied to temp folder for local processing
    # construct input_file name
    tempinputfile = os.path.join(globals.__addonworkdir__, tempfile + "_in.txt")
    # construct output_file name
    tempoutputfile = os.path.join(globals.__addonworkdir__, tempfile + "_out.utf")
    # copy file to temp
    copy_file(originalinputfile, tempinputfile)

    Log("Subtitle file processing started.", xbmc.LOGINFO)

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
            _temp = reader.read()
            # still no exception - seems to be a success
            Log("UTF-8 encoding seems to be valid.", xbmc.LOGINFO)
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
                    _temp = reader.read()
                    # still no exception - seems to be a success
                    Log("Chosen encoding: " + enc + " based on language: " + subslang + " seems to be valid.",
                        xbmc.LOGINFO)
            except Exception as e:
                # reading based on assigned language encoding failed
                enc = ""

    # if identification tries failed, try a list of encodings as a last resort
    if not enc:
        # list of encodings to try
        # https://msdn.microsoft.com/en-us/library/windows/desktop/dd317756(v=vs.85).aspx
        # https://stackoverflow.com/questions/436220/determine-the-encoding-of-text-in-python
        encodings = ["utf-8", "cp1250", "cp1251", "cp1252", "cp1253", "cp1254", "cp1255", "cp1256", "cp1257", "cp1258"]

        Log("Trying a list of encodings.", xbmc.LOGINFO)
        # try to detect valid encoding
        # this actually detects the first encoding which allows a file to be read without errors
        for enc in encodings:
            try:
                with codecs.open(tempinputfile, mode="rb", encoding=enc) as reader:
                    _temp = reader.read()
                    break
            except Exception as e:
                # encoding does not match
                Log("Input file test for: " + enc + " failed.", xbmc.LOGINFO)
                continue
        else:
            # no encodings match
            Log("No tried encodings match input file.", xbmc.LOGINFO)
            # subtitle processing aborted
            return

    Log("Input encoding used: " + enc, xbmc.LOGINFO)
    Log("          Input FPS: " + str(globals.playingFps), xbmc.LOGINFO)

    # load input_file into pysubs2 library
    subs = pysubs2.load(tempinputfile, encoding=enc, fps=float(globals.playingFps))

    # process subs contents
    # iterate over every sub line and process its text
    # http://pythonhosted.org/pysubs2/api-reference.html#ssafile-a-subtitle-file

    # load regexp definitions from file
    Log("Definitions file used: " + globals.deffilename, xbmc.LOGINFO)
    if globals.setting_RemoveCCmarks:
        # load CCmarks definitions
        CCmarksList = GetDefinitions("CCmarks")

    if globals.setting_RemoveAds:
        # load Ads definitions
        AdsList = GetDefinitions("Ads")
        # load country specific definitions only if language was detected
        if subslang:
            AdsList += GetDefinitions("Ads_" + subslang)

    # iterate over every line of subtitles and process each subtitle line
    Log("Applying filtering lists.", xbmc.LOGINFO)

    # if nextlinestart == 0 then we are on the beginning of the list (last subtitle as list is reversed)
    nextlinestart = 0
    # iterate from last to first element to avoid skipping elements if current element was removed
    # https://stackoverflow.com/questions/14267722/python-list-remove-skips-next-element-in-list/14283447#14283447
    for line in reversed(subs):
        # load single line to temp variable for processing
        subsline = line.text

        RemoveWhitespaces(subsline)

        # process subtitle line
        Log("Subtitle line: " + subsline, xbmc.LOGDEBUG)
        if globals.setting_RemoveCCmarks:
            # remove CC texts from subsline
            subsline = RemoveStrings(subsline, CCmarksList)
        if globals.setting_RemoveAds:
            # remove Advertisement strings from subsline
            subsline = RemoveStrings(subsline, AdsList)

        RemoveWhitespaces(subsline)

        # if line is empty after processing, remove line from subtitles file
        # https://stackoverflow.com/questions/9573244/most-elegant-way-to-check-if-the-string-is-empty-in-python
        if not subsline:
            # remove empty line
            subs.remove(line)
            Log("    Resulting line is empty. Removing from file.", xbmc.LOGDEBUG)
        else:
            # adjust minimum subtitle display time
            # if calculated time is longer than actual time and if it does not overlap next sub time
            if globals.setting_AdjustSubDisplayTime:
                # calculation formula for chars per second
                # https://backlothelp.netflix.com/hc/en-us/articles/219375728-English-Template-Timed-Text-Style-Guide
                # 500 ms for line + 67 ms per each character (15 chars per second)
                minCalcLength = 500 + (len(subsline) * 67)

                Log("    Actual length: " + str(line.duration) + " ms", xbmc.LOGDEBUG)
                Log("    Min. calculated length: " + str(minCalcLength) + " ms", xbmc.LOGDEBUG)

                # check next subtitle start time and compare it to this subtitle end time
                ## https://stackoverflow.com/questions/1011938/python-previous-and-next-values-inside-a-loop
                if nextlinestart != 0:
                    # if it is not the last subtitle (first on indexed list), calculate gap to next subtitle (previous on indexed list) object
                    #
                    # compare the next subtitle's start time with this subtitle's end time
                    nextlineclearance = nextlinestart - line.end
                    Log("    Clearance to next sub: " + str(nextlineclearance) + " ms", xbmc.LOGDEBUG)

                    if nextlineclearance < 2:
                        if globals.setting_FixOverlappingSubDisplayTime:
                            line.duration = line.duration + nextlineclearance - 2
                            Log("    Time subtracted from subtitle duration: " + str(2 - nextlineclearance) + " ms",
                                xbmc.LOGDEBUG)

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
                        Log("    Time added to subtitle duration: " + str(timetoincrease) + " ms", xbmc.LOGDEBUG)

                # remember start time of subtitle
                nextlinestart = line.start

            # save changed line
            line.plaintext = subsline

    Log("Filtering lists applied.", xbmc.LOGINFO)

    # save subs in a proper format
    subs.save(tempoutputfile, format_="srt")

    # wait until file is saved
    wait_for_file(tempoutputfile, True)

    # record end time of processing
    MangleEndTime = time.time()

    # truncating seconds: https://stackoverflow.com/questions/8595973/truncate-to-3-decimals-in-python/8595991#8595991
    Log("Subtitle file processing finished. Processing took: " + '%.3f' % (
            MangleEndTime - MangleStartTime) + " seconds.", xbmc.LOGINFO)

    # FIXME - debug check if file is already released
    try:
        fp = open(tempoutputfile)
        fp.close()
    except Exception as e:
        Log("tempoutputfile NOT released.", xbmc.LOGERROR)
        Log("Exception: " + str(e), xbmc.LOGERROR)

    # copy new file back to its original location changing only its extension
    filebase, _fileext = os.path.splitext(originalinputfile)
    originaloutputfile = filebase + '.utf'
    copy_file(tempoutputfile, originaloutputfile)

    # make a backup copy of subtitle file or remove file
    if globals.setting_BackupOldSubs:
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


def InternetStream(srcurl):
    """Checks if the file is an internet stream

    Arguments:
        srcurl {string} -- [Path and filename of file being played]

    Returns:
        bool -- True is stream is internet stream
    """
    # http://xion.io/post/code/python-startswith-tuple.html
    protocols = ("http", "https", "mms", "rtsp", "pvr", "plugin")
    if srcurl.lower().startswith(tuple(p + '://' for p in protocols)):
        return True
    else:
        return False


# copy function
def copy_file(srcFile, dstFile):
    """Copy file using xbmcvfs.

    Arguments:
        srcFile {str} -- source file
        dstFile {str} -- destination file
    """

    try:
        Log("copy_file: srcFile: " + srcFile, xbmc.LOGINFO)
        Log("           dstFile: " + dstFile, xbmc.LOGINFO)
        if xbmcvfs.exists(srcFile):
            Log("copy_file: srcFile exists.", xbmc.LOGDEBUG)
        if xbmcvfs.exists(dstFile):
            Log("copy_file: dstFile exists. Trying to remove.", xbmc.LOGDEBUG)
            delete_file(dstFile)
        else:
            Log("copy_file: dstFile does not exist.", xbmc.LOGDEBUG)
        Log("copy_file: Copy started.", xbmc.LOGDEBUG)

        # as xbmcvfs.copy() sometimes fails, make more tries to check if lock is permanent - test only
        counter = 0
        success = 0
        while not (success != 0 or counter >= 3):
            success = xbmcvfs.copy(srcFile, dstFile)
            Log("copy_file: SuccessStatus: " + str(success), xbmc.LOGDEBUG)
            counter += 1
            xbmc.sleep(500)
        if counter > 1:
            Log("copy_file: First copy try failed. Number of tries: " + str(counter), xbmc.LOGWARNING)

    except Exception as e:
        Log("copy_file: Copy failed.", xbmc.LOGERROR)
        Log("Exception: " + str(e), xbmc.LOGERROR)

    wait_for_file(dstFile, True)


# rename function
def rename_file(oldfilepath, newfilepath):
    """Rename file using xbmcvfs.

    Arguments:
        oldfilepath {str} -- old file name
        newfilepath {str} -- new file name
    """

    try:
        Log("rename_file: srcFile: " + oldfilepath, xbmc.LOGINFO)
        Log("             dstFile: " + newfilepath, xbmc.LOGINFO)
        # check if new file already exists as in this case rename will fail
        if xbmcvfs.exists(newfilepath):
            Log("rename_file: dstFile exists. Trying to remove.", xbmc.LOGINFO)
            delete_file(newfilepath)
        else:
            Log("rename_file: dstFile does not exist.", xbmc.LOGINFO)
        # rename file
        success = xbmcvfs.rename(oldfilepath, newfilepath)
        Log("rename_file: SuccessStatus: " + str(success), xbmc.LOGINFO)
    except Exception as e:
        Log("Can't rename file: " + oldfilepath, xbmc.LOGERROR)
        Log("Exception: " + str(e), xbmc.LOGERROR)


# delete function
def delete_file(filepath):
    """Delete file using xbmcvfs.

    Arguments:
        filepath {str} -- file to delete
    """

    try:
        xbmcvfs.delete(filepath)
        Log("delete_file: File deleted: " + filepath, xbmc.LOGINFO)
    except Exception as e:
        Log("delete_file: Delete failed: " + filepath, xbmc.LOGERROR)
        Log("Exception: " + str(e), xbmc.LOGERROR)

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
        Log("wait_for_file: if file exists: " + file, xbmc.LOGINFO)
    else:
        Log("wait_for_file: if file doesn't exist: " + file, xbmc.LOGINFO)

    count = 10
    while count:
        xbmc.sleep(500)  # this first sleep is intentional
        if exists:
            if xbmcvfs.exists(file):
                Log("wait_for_file: file appeared.", xbmc.LOGINFO)
                success = True
                break
        else:
            if not xbmcvfs.exists(file):
                Log("wait_for_file: file vanished.", xbmc.LOGINFO)
                success = True
                break
        count -= 1
    if not success:
        if exists:
            Log("wait_for_file: file DID NOT appear.", xbmc.LOGERROR)
        else:
            Log("wait_for_file: file DID NOT vanish.", xbmc.LOGERROR)
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
    _dirs, files = xbmcvfs.listdir(subspath)
    subs_files = dict([(f, None) for f in files])
    # filter dictionary, leaving only subtitle files matching played video
    # https://stackoverflow.com/questions/5384914/how-to-delete-items-from-a-dictionary-while-iterating-over-it
    playingFilenameBase, _playingFilenameExt = os.path.splitext(globals.playingFilename)

    for item in list(subs_files.keys()):
        # split file and extension
        subfilebase, subfileext = os.path.splitext(item)
        # from filename split language designation
        subfilecore, _subfilelang = os.path.splitext(subfilebase)
        # remove files that do not meet criteria
        if not ((((
                          subfilebase.lower() == playingFilenameBase.lower() or subfilecore.lower() == playingFilenameBase.lower()) and (
                          subfileext.lower() in substypelist))
                 or ((subfilebase.lower() == playingFilenameBase.lower()) and (subfileext.lower() == ".noautosubs")))
                or (subfilebase.lower() == "noautosubs")):
            # NOT
            # subfilename matches video name AND fileext is on the list of supported extensions
            # OR subfilename matches video name AND fileext matches '.noautosubs'
            # OR subfilename matches 'noautosubs'
            # note: we assume that .utf subtitle will not be processed
            del subs_files[item]

    return subs_files


# pause playback
def PlaybackPause():
    """Pause playback if not paused."""

    # pause playback
    if not xbmc.getCondVisibility("player.paused"):
        xbmc.Player().pause()
        Log("Playback PAUSED.", xbmc.LOGINFO)
    else:
        Log("Playback already PAUSED.", xbmc.LOGINFO)


# resume playback
def PlaybackResume():
    """Resume playback if paused."""

    # resume playback
    if xbmc.getCondVisibility("player.paused"):
        Log("Playback is paused. Resuming.", xbmc.LOGINFO)
        xbmc.Player().pause()
        Log("Playback RESUMED.", xbmc.LOGINFO)
    else:
        Log("Playback not paused. No need to resume.", xbmc.LOGINFO)


# check if any files matching video being played are changed
# http://timgolden.me.uk/python/win32_how_do_i/watch_directory_for_changes.html
def DetectNewSubs():
    """Detect new subtitle files matching video name being played."""

    #Log("DetectNewSubs process called.", xbmc.LOGDEBUG)
    # if function is already running, exit this instance
    if globals.DetectionIsRunning:
        # Log("Duplicate DetectNewSubs call.", xbmc.LOGWARNING)
        return

    # stop timer in order to not duplicate threads
    # globals.rt.stop()

    # setting process flag, process starts to run
    globals.DetectionIsRunning = True

    # load all subtitle files in the given directory
    # also returns 'noautosubs' file and '.noautosubs' extension
    recent_subs_files = GetSubtitleFiles(globals.subtitlePath, globals.SubExtList)

    # check all found subtitle files for changed timestamp
    for f in recent_subs_files:
        # ignore 'noautosubs' file/extension to not trigger detection of subtitles
        if f[-10:].lower() == "noautosubs":
            continue

        pathfile = os.path.join(globals.subtitlePath, f)
        epoch_file = xbmcvfs.Stat(pathfile).st_mtime()
        epoch_now = time.time()

        # check current directory contents for unprocessed subtitle files touched no later than a few seconds ago
        # or optionally for all unprocessed subtitle files
        if (epoch_file > epoch_now - 6) or globals.setting_AlsoConvertExistingSubtitles:
            # Video filename matches subtitle filename
            # and either it was created/modified no later than 6 seconds ago or existing subtitles are taken into account as well
            Log("New subtitle file detected: " + pathfile, xbmc.LOGINFO)

            Log("Subtitles processing routine started.", xbmc.LOGINFO)
            # record start time of processing
            RoutineStartTime = time.time()

            # clear storage dir from subtitle files
            tempfilelist = [f for f in os.listdir(globals.__addonworkdir__) if
                            os.path.isfile(os.path.join(globals.__addonworkdir__, f))]
            Log("Clearing temporary files.", xbmc.LOGINFO)
            for item in tempfilelist:
                filebase, fileext = os.path.splitext(item)
                if (fileext.lower() in globals.SubExtList) or fileext.lower().endswith(".utf"):
                    os.remove(os.path.join(globals.__addonworkdir__, item))
                    Log("       File: " + os.path.join(globals.__addonworkdir__, item) + "  removed.", xbmc.LOGINFO)

            # hide subtitles
            xbmc.Player().showSubtitles(False)

            if globals.setting_PauseOnConversion:
                # show busy animation
                # https://forum.kodi.tv/showthread.php?tid=280621&pid=2363462#pid2363462
                # https://kodi.wiki/view/Window_IDs
                # busydialog is going away in Kodi 18 - https://forum.kodi.tv/showthread.php?tid=333950&pid=2754978#pid2754978
                if int(globals.__kodiversion__[:2]) == 17:
                    xbmc.executebuiltin('ActivateWindow(busydialog)')  # busydialog on - Kodi 17
                else:
                    if int(globals.__kodiversion__[:2]) >= 18:
                        xbmc.executebuiltin('ActivateWindow(busydialognocancel)')  # busydialog on - Kodi 18

                # pause playback
                PlaybackPause()

            # process subtitle file
            ResultFile = MangleSubtitles(pathfile)
            Log("Output subtitle file: " + ResultFile, xbmc.LOGINFO)

            # check if destination file exists
            if xbmcvfs.exists(ResultFile):
                Log("Subtitles available and enabled.", xbmc.LOGINFO)

                # load new subtitles and turn them on
                xbmc.Player().setSubtitles(ResultFile)

                # resume playback
                PlaybackResume()
            else:
                Log("Subtitles NOT available.", xbmc.LOGINFO)

            # hide busy animation
            # https://forum.kodi.tv/showthread.php?tid=280621&pid=2363462#pid2363462
            xbmc.executebuiltin('Dialog.Close(busydialognocancel)')  # busydialog off - Kodi >= 18

            # record end time of processing
            RoutineEndTime = time.time()

            # truncating seconds: https://stackoverflow.com/questions/8595973/truncate-to-3-decimals-in-python/8595991#8595991
            Log("Subtitles processing routine finished. Processing took: " + '%.3f' % (
                    RoutineEndTime - RoutineStartTime) + " seconds.", xbmc.LOGINFO)

            # clear subtitles search dialog flag to make sure that YesNo dialog will not be triggered
            globals.SubsSearchWasOpened = False

            # sleep for 10 seconds to avoid processing newly added subititle file
            # this should not be needed since we do not support .utf as input file at the moment
            # xbmc.sleep(10000)

    # check if subtitles search window was opened but there were no new subtitles processed
    if globals.SubsSearchWasOpened:
        if not globals.setting_NoConfirmationInvokeIfDownloadedSubsNotFound and not InternetStream(
                globals.playingFilenamePath):
            Log("Subtitles search window was opened but no new subtitles were detected. Opening YesNo dialog.",
                xbmc.LOGINFO)

            # pause playbcak
            PlaybackPause()

            # display YesNo dialog
            # http://mirrors.xbmc.org/docs/python-docs/13.0-gotham/xbmcgui.html#Dialog-yesno
            YesNoDialog = xbmcgui.Dialog().yesno("Subtitles Mangler",
                                                 globals.__addonlang__(32040) + "\n" + globals.__addonlang__(32041),
                                                 nolabel=globals.__addonlang__(32042),
                                                 yeslabel=globals.__addonlang__(32043))
            if YesNoDialog:
                # user does not want the subtitle search dialog to appear again for this file
                Log("Answer is Yes. Setting .noautosubs extension flag for file: " + globals.playingFilenamePath,
                    xbmc.LOGINFO)

                # set '.noautosubs' extension for file being played
                filebase, fileext = os.path.splitext(globals.playingFilenamePath)
                # create .noautosubs file
                CreateNoAutoSubsFile(filebase + ".noautosubs")

            else:
                # user wants the dialog to appear again next time the video is played
                Log("Answer is No. Doing nothing.", xbmc.LOGINFO)

            # resume playback
            PlaybackResume()

        else:
            Log(
                "Subtitles search window was opened and no new subtitles were detected, but configuration prevents YesNo dialog from opening.",
                xbmc.LOGINFO)

        # clear the flag to prevent opening dialog on next call of DetectNewSubs()
        globals.SubsSearchWasOpened = False

    # clearing process flag, process is not running any more
    globals.DetectionIsRunning = False


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
    storagemode = GetKodiSetting("subtitles.storagemode")  # 1=location defined by custompath; 0=location in movie dir
    custompath = GetKodiSetting(
        "subtitles.custompath")  # path to non-standard dir with subtitles, also returned by "special://subtitles"

    # get video details
    filename = xbmc.getInfoLabel('Player.Filename')
    filepathname = xbmc.getInfoLabel('Player.Filenameandpath')
    filefps = xbmc.getInfoLabel('Player.Process(VideoFPS)')
    audiolang = xbmc.getInfoLabel('VideoPlayer.AudioLanguage')
    filelang = xbmc.getInfoLabel('VideoPlayer.SubtitlesLanguage')

    # check if file is played from internet or it is a local file and based on this adjust predicted subtitle location
    if InternetStream(filepathname):
        # internet stream
        if custompath:
            subspath = custompath
        else:
            subspath = xbmcvfs.translatePath("special://temp")
    else:
        # local file
        if storagemode == 1:  # location == custompath
            if xbmcvfs.exists(custompath):
                subspath = custompath
            else:
                subspath = xbmcvfs.translatePath("special://temp")
        else:  # location == movie dir
            subspath = xbmc.getInfoLabel('Player.Folderpath')

    Log("File currently played: " + filepathname, xbmc.LOGINFO)
    Log("Subtitles download path: " + subspath, xbmc.LOGINFO)
    Log("Audio language: " + audiolang, xbmc.LOGINFO)
    Log("Subtitles language (either internal or external): " + filelang, xbmc.LOGINFO)

    return subspath, filename, filepathname, filefps, audiolang, filelang


# updates regexdef file from server
def UpdateDefFile():
    """Update regex definitions file from server."""

    Log("Trying to update regexp definitions from: " + globals.deffileurl, xbmc.LOGINFO)
    # download file from server
    # http://stackabuse.com/download-files-with-python/
    try:
        filedata = urllib.request.urlopen(globals.deffileurl)
        datatowrite = filedata.read()
        with open(globals.tempdeffilename, 'wb') as f:
            f.write(datatowrite)

        # check if target file path exists
        if os.path.isfile(globals.localdeffilename):
            # compare if downloaded temp file and current local file are identical
            if filecmp.cmp(globals.tempdeffilename, globals.localdeffilename, shallow=0):
                Log("Definitions file is up-to-date. Skipping update.", xbmc.LOGINFO)
            else:
                # remove current target file
                Log("Found different definitions file. Removing current file: " + globals.localdeffilename,
                    xbmc.LOGINFO)
                os.remove(globals.localdeffilename)
                # copy temp file to target file
                copyfile(globals.tempdeffilename, globals.localdeffilename)
                Log("Regex definitions updated.", xbmc.LOGINFO)
        else:
            # copy temp file to target file
            copyfile(globals.tempdeffilename, globals.localdeffilename)
            Log("Regex definitions updated.", xbmc.LOGINFO)

        # remove temp file
        os.remove(globals.tempdeffilename)

    except urllib.error.URLError as e:
        Log("Can not download definitions: " + globals.deffileurl, xbmc.LOGERROR)
        Log("Exception: " + str(e.reason), xbmc.LOGERROR)
    except IOError as e:
        Log("Can not copy definitions file to: " + globals.localdeffilename, xbmc.LOGERROR)


#    except OSError as e:
#        Log("Can not remove temporary definitions file: " + globals.tempdeffilename, xbmc.LOGERROR)


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
    Log("JSON-RPC: Files.GetSources: " + str(sources), xbmc.LOGDEBUG)

    Log("Scanning video sources for orphaned subtitle files.", xbmc.LOGINFO)
    # record start time
    ClearStartTime = time.time()

    # create background dialog
    # http://mirrors.kodi.tv/docs/python-docs/13.0-gotham/xbmcgui.html#DialogProgressBG
    pDialog = xbmcgui.DialogProgressBG()
    pDialog.create('Subtitles Mangler', globals.__addonlang__(32090))

    # initiate empty lists
    videofiles = list()
    subfiles = list()

    # construct target list for file candidate extensions to be removed
    # remove processed subs and .noautosubs files
    extRemovalList = ['.utf', '.noautosubs']
    # remove processed subs backup files
    if globals.setting_RemoveSubsBackup:
        for ext in globals.SubExtList:
            extRemovalList.append(ext + '_backup')
    # remove unprocessed subs
    if globals.setting_RemoveUnprocessedSubs:
        for ext in globals.SubExtList:
            extRemovalList.append(ext)

    # count number of sources
    # calculate progressbar increase per source
    source_number = 0
    # process every source path
    for source in sources:
        startdir = source.get('file')
        Log("Processing source path: " + startdir, xbmc.LOGINFO)
        # calculate progressbar increase
        progress = source_number // len(sources)
        # update background dialog
        pDialog.update(progress, message=globals.__addonlang__(32090) + ': ' + source.get('label'))
        source_number += 100

        # http://code.activestate.com/recipes/435875-a-simple-non-recursive-directory-walker/
        directories = [startdir]
        while len(directories) > 0:
            # take one element from directories list and process it
            directory = directories.pop()
            dirs, files = xbmcvfs.listdir(directory)
            # add every subdir to the list for checking
            for subdir in dirs:
                Log("Adding subpath: " + os.path.join(directory, subdir), xbmc.LOGDEBUG)
                directories.append(os.path.join(directory, subdir))
            # check every file in the current subdir and add it to appropriate list
            for thisfile in files:
                fullfilepath = os.path.join(directory, thisfile)
                _filebase, fileext = os.path.splitext(fullfilepath)
                if fileext in globals.VideoExtList:
                    # this file is video - add to video list
                    Log("Adding to video list: " + fullfilepath, xbmc.LOGDEBUG)
                    videofiles.append(fullfilepath)
                elif fileext in extRemovalList:
                    # this file is subs related - add to subs list
                    Log("Adding to subs list: " + fullfilepath, xbmc.LOGDEBUG)
                    subfiles.append(fullfilepath)

    # process custom subtitle path if it is set in Kodi configuration
    custompath = xbmcvfs.translatePath("special://subtitles")  # path to non-standard dir with subtitles

    if custompath:
        if xbmcvfs.exists(custompath):
            subspath = custompath
        else:
            subspath = ""
    else:
        subspath = ""

    if subspath:
        Log("Scanning for orphaned subtitle files on custom path: " + subspath, xbmc.LOGINFO)
        dirs, files = xbmcvfs.listdir(subspath)
        for thisfile in files:
            fullfilepath = os.path.join(subspath, thisfile)
            _filebase, fileext = os.path.splitext(fullfilepath)
            if fileext in extRemovalList:
                # this file is subs related - add to subs list
                Log("Adding to subs list: " + fullfilepath, xbmc.LOGDEBUG)
                subfiles.append(fullfilepath)
    else:
        Log("Custom path not set. Skipping scanning it.", xbmc.LOGINFO)

    # process temp folder
    Log("Scanning for orphaned subtitle files on temp path: " + xbmcvfs.translatePath("special://temp"), xbmc.LOGINFO)
    dirs, files = xbmcvfs.listdir(xbmcvfs.translatePath("special://temp"))
    for thisfile in files:
        fullfilepath = os.path.join(xbmcvfs.translatePath("special://temp"), thisfile)
        _filebase, fileext = os.path.splitext(fullfilepath)
        if fileext in extRemovalList:
            # this file is subs related - add to subs list
            Log("Adding to subs list: " + fullfilepath, xbmc.LOGDEBUG)
            subfiles.append(fullfilepath)

    # record scan time
    ClearScanTime = time.time()
    Log("Scanning for orphaned subtitle files finished. Processing took: " + '%.3f' % (
            ClearScanTime - ClearStartTime) + " seconds.", xbmc.LOGINFO)
    Log("Clearing orphaned subtitle files.", xbmc.LOGINFO)

    subfile_number = 0
    # lists filled, compare subs list with video list
    for subfile in subfiles:
        # calculate progressbar increase
        progress = subfile_number // len(subfiles)
        # update background dialog
        pDialog.update(progress, message=globals.__addonlang__(32091))
        subfile_number += 100

        # split filename from full path
        subfilename = os.path.basename(subfile)
        # split filename and extension
        subfilebase, _subfileext = os.path.splitext(subfilename)
        # from filename split language designation
        subfilecore, _subfilelang = os.path.splitext(subfilebase)

        # check if there is a video matching subfile
        videoexists = False
        for videofile in videofiles:
            # split filename from full path
            videofilename = os.path.basename(videofile)
            # split filename and extension
            videofilebase, _videofileext = os.path.splitext(videofilename)

            # check if subfile basename or corename equals videofile basename
            if subfilebase.lower() == videofilebase.lower() or subfilecore.lower() == videofilebase.lower():
                videoexists = True
                break

        if not videoexists:
            if globals.setting_SimulateRemovalOnly:
                Log(
                    "There is no video file matching: " + subfile + "  File would have been deleted if Simulate option had been off.",
                    xbmc.LOGINFO)
            else:
                Log("There is no video file matching: " + subfile + "  Deleting it.", xbmc.LOGINFO)
                delete_file(subfile)
        else:
            Log("Video file matching: " + subfile, xbmc.LOGDEBUG)
            Log("              found: " + videofile, xbmc.LOGDEBUG)

    # record end time
    ClearEndTime = time.time()
    Log("Clearing orphaned subtitle files finished. Processing took: " + '%.3f' % (
            ClearEndTime - ClearScanTime) + " seconds.", xbmc.LOGINFO)

    # close background dialog
    pDialog.close()


# supplementary code to be run periodically from main loop
def SupplementaryServices():
    """Supplementary services that have to run periodically
    """

    # set definitions file location
    # dir is local, no need to use xbmcvfs()
    if os.path.isfile(globals.localdeffilename):
        # downloaded file is available
        globals.deffilename = globals.localdeffilename
    else:
        # use sample file from addon's dir
        globals.deffilename = globals.sampledeffilename

    # housekeeping services
    if globals.ClockTick <= 0 and not xbmc.getCondVisibility('Player.HasMedia'):
        # check if auto-update is enabled and player does not play any content
        if globals.setting_AutoUpdateDef:
            # update regexdef file
            UpdateDefFile()

        if globals.setting_AutoRemoveOldSubs:
            # clear old subtitle files
            RemoveOldSubs()

        # reset timer to 6 hours
        # 1 tick per 5 sec * 60 min * 6 hrs = 4320 ticks
        globals.ClockTick = 4320

    # decrease timer if player is idle
    # avoid decreasing the timer to infinity
    if globals.ClockTick > 0 and not xbmc.getCondVisibility('Player.HasMedia'):
        globals.ClockTick -= 1
