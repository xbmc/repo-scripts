# -*- coding: utf-8 -*-
import traceback
import xbmc
import xbmcaddon
import xbmcvfs
import xbmcgui
import datetime

# Import the common settings
from resources.lib.settings import log
from resources.lib.settings import os_path_join

ADDON = xbmcaddon.Addon(id='script.tvtunes')


# Ideally we would use an XML parser to do this like ElementTree
# However they all end up re-ordering the attributes, so doing a diff
# between changed files is very hard, so for this reason we do it
# all manually without the aid of an XML parser
class ConfUpdate():
    def __init__(self):
        # Find out where the confluence skin files are located
        confAddon = xbmcaddon.Addon(id='skin.confluence')
        self.confpath = xbmc.translatePath(confAddon.getAddonInfo('path'))
        self.confpath = os_path_join(self.confpath, '720p')
        log("Confluence Location: %s" % self.confpath)
        # Create the timestamp centrally, as we want all files changed for a single
        # run to have the same backup timestamp so it can be easily undone if the
        # user wishes to switch it back
        self.bak_timestamp = datetime.datetime.now().strftime("%Y%m%d%H%M%S")
        self.errorToLog = False

    # Method to update all of the required Confluence files
    def updateSkin(self):
        # Update the files one at a time
        self._updateDialogVideoInfo()

        # Now either print the complete message or the "check log" message
        if self.errorToLog:
            xbmcgui.Dialog().ok(ADDON.getLocalizedString(32105), ADDON.getLocalizedString(32137), ADDON.getLocalizedString(32135))
        else:
            xbmcgui.Dialog().ok(ADDON.getLocalizedString(32105), ADDON.getLocalizedString(32138), ADDON.getLocalizedString(32139))

    # Save the new contents, taking a backup of the old file
    def _saveNewFile(self, dialogXml, dialogXmlStr):
        log("SaveNewFile: New file content: %s" % dialogXmlStr)

        # Now save the file to disk, start by backing up the old file
        xbmcvfs.copy(dialogXml, "%s.tvtunes-%s.bak" % (dialogXml, self.bak_timestamp))

        # Now save the new file
        dialogXmlFile = xbmcvfs.File(dialogXml, 'w')
        dialogXmlFile.write(dialogXmlStr)
        dialogXmlFile.close()

    ##########################################################################
    # UPDATES FOR DialogVideoInfo.xml
    ##########################################################################
    # Makes all the required changes to DialogVideoInfo.xml
    def _updateDialogVideoInfo(self):
        # Get the location of the information dialog XML file
        dialogXml = os_path_join(self.confpath, 'DialogVideoInfo.xml')
        log("DialogVideoInfo: Confluence dialog XML file: %s" % dialogXml)

        # Make sure the file exists (It should always exist)
        if not xbmcvfs.exists(dialogXml):
            log("DialogVideoInfo: Unable to find the file DialogVideoInfo.xml, skipping file", xbmc.LOGERROR)
            self.errorToLog = True
            return

        # Load the DialogVideoInfo.xml into a string
        dialogXmlFile = xbmcvfs.File(dialogXml, 'r')
        dialogXmlStr = dialogXmlFile.read()
        dialogXmlFile.close()

        # Now check to see if the skin file has already had the tvtunes bits added
        if 'script.tvtunes' in dialogXmlStr:
            # Already have tvtunes referenced, so we do not want to do anything else
            # to this file
            log("DialogVideoInfo: TvTunes already referenced in %s, skipping file" % dialogXml, xbmc.LOGINFO)
            self.errorToLog = True
            return

        # Now we need to add the button after the Final button
        previousButton = '<label>13511</label>'

        if previousButton not in dialogXmlStr:
            # The file has had a standard component deleted, so quit
            log("DialogVideoInfo: Could not find final button, skipping file", xbmc.LOGERROR)
            self.errorToLog = True
            return

        # Check to make sure we use a unique ID value for the button
        idOK = False
        idval = 100
        while not idOK:
            idStr = "id=\"%d\"" % idval
            if idStr not in dialogXmlStr:
                idOK = True
            else:
                idval = idval + 1

        # Now add the Video Extras button after the Final one
        DIALOG_VIDEO_INFO_BUTTON = '''\n\t\t\t\t\t</control>\n\t\t\t\t\t<control type="button" id="%d">
\t\t\t\t\t\t<description>TvTunes</description>
\t\t\t\t\t\t<include>ButtonInfoDialogsCommonValues</include>
\t\t\t\t\t\t<label>$ADDON[script.tvtunes 32105]</label>
\t\t\t\t\t\t<onclick>RunScript(script.tvtunes,mode=solo)</onclick>
\t\t\t\t\t\t<visible>System.HasAddon(script.tvtunes) + [Container.Content(TVShows) | Container.Content(movies) | Container.Content(musicvideos)] + IsEmpty(Window(movieinformation).Property("TvTunes_HideVideoInfoButton"))</visible>'''

        insertTxt = previousButton + (DIALOG_VIDEO_INFO_BUTTON % idval)
        dialogXmlStr = dialogXmlStr.replace(previousButton, insertTxt)

        self._saveNewFile(dialogXml, dialogXmlStr)


#########################
# Main
#########################
if __name__ == '__main__':
    log("TvTunes: Updating Confluence Skin (version %s)" % ADDON.getAddonInfo('version'))

    doUpdate = xbmcgui.Dialog().yesno(ADDON.getLocalizedString(32105), ADDON.getLocalizedString(32134))

    if doUpdate:
        try:
            confUp = ConfUpdate()
            confUp.updateSkin()
            del confUp
        except:
            log("VideoExtras: %s" % traceback.format_exc(), xbmc.LOGERROR)
            xbmcgui.Dialog().ok(ADDON.getLocalizedString(32105), ADDON.getLocalizedString(32134), ADDON.getLocalizedString(32135))
