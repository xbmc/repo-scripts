# -*- coding: utf-8 -*-
import re
import traceback
import xbmc
import xbmcaddon
import xbmcvfs
import xbmcgui
import datetime

# Import the common settings
from resources.lib.settings import log
from resources.lib.settings import Settings

ADDON = xbmcaddon.Addon(id='script.tvtunes')


# This class reads the advancedsettings.xml file like it was a text file
# Ideally it would be read as an XML file using ElementTree, but the problem with
# doing that is that we would end up removing all the comments, and if someone
# has gone to the trouble of adding comments, then we do not want to remove them
class AdvSettings():
    HEADER = '<!-- TvTunes: Section Start -->'
    FOOTER = '<!-- TvTunes: Section End -->'

    IGNORE_SECTION = '''        <excludefromscan action="append">\n{0}        </excludefromscan>
        <excludetvshowsfromscan action="append">\n{0}        </excludetvshowsfromscan>\n'''

    REGEX_SECTION = '            <regexp>{0}</regexp>\n'

    ADV_SET_START = '<advancedsettings>'
    ADV_SET_END = '</advancedsettings>'

    VIDEO_SECTION_START = '<video>'
    VIDEO_SECTION_END = '</video>'

    def __init__(self):
        # Find out where the advancedsettings.xml file is located
        self.advSettingsXmlFile = xbmc.translatePath('special://masterprofile/advancedsettings.xml').decode("utf-8")
        log("Advancedsettings.xml Location: %s" % self.advSettingsXmlFile)
        self.bak_timestamp = datetime.datetime.now().strftime("%Y%m%d%H%M%S")

    # Will process the advanced settings file
    def updateAdvancedSettings(self):
        xmlFileStr = None
        # Check if the advancessettings.xml file already exists
        if xbmcvfs.exists(self.advSettingsXmlFile):
            log("Loading existing advanced settings file")
            # Read in the existing file
            xmlFile = xbmcvfs.File(self.advSettingsXmlFile, 'r')
            xmlFileStr = xmlFile.read()
            xmlFile.close()

            # The file has now been read so we need to see if
            # there is already a tv tunes section in it
            if AdvSettings.HEADER in xmlFileStr:
                log("Updating existing TvTunes setting")
                # need to strip out the existing contents and replace it with
                # the new contents
                insertTxt = AdvSettings.HEADER + "\n"
                insertTxt += self._getNewSettingsXml()
                insertTxt += '        ' + AdvSettings.FOOTER
                regexCompiled = re.compile("(%s).*?(%s)" % (AdvSettings.HEADER, AdvSettings.FOOTER), re.IGNORECASE | re.DOTALL)
                xmlFileStr = regexCompiled.sub(insertTxt, xmlFileStr)
            elif AdvSettings.VIDEO_SECTION_END in xmlFileStr:
                log("Adding to existing video section")
                insertTxt = '    ' + AdvSettings.HEADER + "\n"
                insertTxt += self._getNewSettingsXml()
                insertTxt += '        ' + AdvSettings.FOOTER + "\n"
                insertTxt += '    ' + AdvSettings.VIDEO_SECTION_END
                # No Video Extras section yet, but there is a video section
                xmlFileStr = re.sub("(%s)" % AdvSettings.VIDEO_SECTION_END, insertTxt, xmlFileStr)
            elif AdvSettings.ADV_SET_END in xmlFileStr:
                log("Adding with new video section")
                # Need to add a video section as well
                insertTxt = '    ' + AdvSettings.VIDEO_SECTION_START + "\n"
                insertTxt += '        ' + AdvSettings.HEADER + "\n"
                insertTxt += self._getNewSettingsXml()
                insertTxt += '        ' + AdvSettings.FOOTER + "\n"
                insertTxt += '    ' + AdvSettings.VIDEO_SECTION_END + "\n"
                insertTxt += AdvSettings.ADV_SET_END
                xmlFileStr = re.sub("(%s)" % AdvSettings.ADV_SET_END, insertTxt, xmlFileStr)
            else:
                # This is an invalid advancedsettings.xml
                log("Invalid advancedsettings.xml detected")
                xmlFileStr = None
                # Show Error Dialog
                xbmcgui.Dialog().ok(ADDON.getLocalizedString(32001), ADDON.getLocalizedString(32153))

            # Make a backup of the file as we are going to change it
            if xmlFileStr is not None:
                xbmcvfs.copy(self.advSettingsXmlFile, "%s.tvtunes-%s.bak" % (self.advSettingsXmlFile, self.bak_timestamp))

        else:
            # The file didn't exist, so create it from scratch
            xmlFileStr = AdvSettings.ADV_SET_START + "\n"
            xmlFileStr += '    ' + AdvSettings.VIDEO_SECTION_START + "\n"
            xmlFileStr += '        ' + AdvSettings.HEADER + "\n"
            # Need to reduce the escaping of the forward-slash as we will not
            # be parsing this string again
            xmlFileStr += self._getNewSettingsXml().replace('\\\\\\', '\\\\')
            xmlFileStr += '        ' + AdvSettings.FOOTER + "\n"
            xmlFileStr += '    ' + AdvSettings.VIDEO_SECTION_END + "\n"
            xmlFileStr += AdvSettings.ADV_SET_END + "\n"

        # Now write the new file contents
        # A backup will have already been taken if there was an old file
        if xmlFileStr is not None:
            xmlFile = xbmcvfs.File(self.advSettingsXmlFile, 'w')
            xmlFile.write(xmlFileStr)
            xmlFile.close()

            xbmcgui.Dialog().ok(ADDON.getLocalizedString(32105), ADDON.getLocalizedString(32095))
            log("New advancedsettings.xml content: %s" % xmlFileStr)
        else:
            log("advancedsettings.xml has been left unchanged")

    # Generates the XML for the actual excludes
    def _getNewSettingsXml(self):
        regexSection = ''
        # Put together the regex section details
        # Check what the directory name is
        themeDir = Settings.getThemeDirectory()
        log("Setting Directory Name to: %s" % themeDir)
        regexSection += AdvSettings.REGEX_SECTION.format('/' + themeDir + '/')
        regexSection += AdvSettings.REGEX_SECTION.format('[\\\\\\/]' + themeDir + '[\\\\\\/]')

        # Put together the list of file endings
        videoFileTypes = Settings.getVideoThemeFileExtensions()
        if videoFileTypes not in [None, ""]:
            regexSection += AdvSettings.REGEX_SECTION.format('theme([0-9]*)\.(' + videoFileTypes.lower() + '|' + videoFileTypes.upper() + ')$')

        # Now put together the ignore section
        ignoreSection = AdvSettings.IGNORE_SECTION.format(regexSection)
        return ignoreSection


#########################
# Main
#########################
if __name__ == '__main__':
    log("TvTunes: Updating Advanced Settings (version %s)" % ADDON.getAddonInfo('version'))

    doUpdate = xbmcgui.Dialog().yesno(ADDON.getLocalizedString(32105), ADDON.getLocalizedString(32092))

    if doUpdate:
        try:
            advSet = AdvSettings()
            advSet.updateAdvancedSettings()
            del advSet
        except:
            log("TvTunes: %s" % traceback.format_exc(), xbmc.LOGERROR)
            xbmcgui.Dialog().ok(ADDON.getLocalizedString(32105), ADDON.getLocalizedString(32093), ADDON.getLocalizedString(32094))
