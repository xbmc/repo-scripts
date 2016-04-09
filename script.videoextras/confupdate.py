# -*- coding: utf-8 -*-
import os
import traceback
import xbmc
import xbmcaddon
import xbmcvfs
import xbmcgui
import datetime

# Import the common settings
from resources.lib.settings import log
from resources.lib.settings import os_path_join

ADDON = xbmcaddon.Addon(id='script.videoextras')
CWD = ADDON.getAddonInfo('path').decode("utf-8")
RES_DIR = xbmc.translatePath(os.path.join(CWD, 'resources').encode("utf-8")).decode("utf-8")


# Ideally we would use an XML parser to do this like ElementTree
# However they all end up re-ordering the attributes, so doing a diff
# between changed files is very hard, so for this reason we do it
# all manually without the aid of an XML parser
#
# The names in the Windows XML files map as follows to the display names
# PosterWrapView            Poster Wrap          ViewVideoLibrary.xml
# PosterWrapView2_Fanart    Fanart               ViewVideoLibrary.xml
# MediaListView2            Media Info           ViewVideoLibrary.xml
# MediaListView3            Media Info 2         ViewVideoLibrary.xml
# MediaListView4            Media Info 3         ViewVideoLibrary.xml
# CommonRootView            List                 ViewFileMode.xml
# ThumbnailView             Thumbnail            ViewFileMode.xml
# WideIconView              Wide (TV Only)       ViewFileMode.xml
# FullWidthList             Big List             ViewFileMode.xml
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
        # Start by copying the include file, will return if the copy worked and the file was created
        if not self._addIncludeFile():
            xbmcgui.Dialog().ok(ADDON.getLocalizedString(32001), ADDON.getLocalizedString(32160), ADDON.getLocalizedString(32161))
            return

        # Update the files one at a time
        self._updateDialogVideoInfo()
        self._updateViewsVideoLibrary()
        self._updateViewsFileMode()

        # Now either print the complete message or the "check log" message
        if self.errorToLog:
            xbmcgui.Dialog().ok(ADDON.getLocalizedString(32001), ADDON.getLocalizedString(32157), ADDON.getLocalizedString(32152))
        else:
            xbmcgui.Dialog().ok(ADDON.getLocalizedString(32001), ADDON.getLocalizedString(32158), ADDON.getLocalizedString(32159))

    # Copies over the include file used for icon overlays
    def _addIncludeFile(self):
        # copy over the video extras include file
        skinsDir = xbmc.translatePath(os_path_join(RES_DIR, 'skins').encode("utf-8")).decode("utf-8")
        incFile = os_path_join(skinsDir, 'IncludesVideoExtras.xml')
        # Work out where it is going to go
        tgtFile = os_path_join(self.confpath, 'IncludesVideoExtras.xml')
        log("IncludesVideoExtras: Copy from %s to %s" % (incFile, tgtFile))
        xbmcvfs.copy(incFile, tgtFile)

        # Now the file should be copied to the target location
        # Check to make sure it worked, if it did not then the directory may not
        # have the correct permissions for us to write to
        return xbmcvfs.exists(tgtFile)

    # Save the new contents, taking a backup of the old file
    def _saveNewFile(self, dialogXml, dialogXmlStr):
        log("SaveNewFile: New file content: %s" % dialogXmlStr)

        # Now save the file to disk, start by backing up the old file
        xbmcvfs.copy(dialogXml, "%s.videoextras-%s.bak" % (dialogXml, self.bak_timestamp))

        # Now save the new file
        dialogXmlFile = xbmcvfs.File(dialogXml, 'w')
        dialogXmlFile.write(dialogXmlStr)
        dialogXmlFile.close()

    # Adds the line to the XML that imports the extras include file
    def _addIncludeToXml(self, xmlStr):
        INCLUDE_CMD = '<include file="IncludesVideoExtras.xml"/>'
        updatedXml = xmlStr
        # First check if the include command is already in the XML
        if INCLUDE_CMD not in updatedXml:
            # We want the include at the top, so add it after the first window
            tag = '<window>'
            if tag not in updatedXml:
                tag = '<includes>'
            # Make sure the tag we are about to use is still there
            if tag in updatedXml:
                insertTxt = tag + "\n\t" + INCLUDE_CMD
                updatedXml = updatedXml.replace(tag, insertTxt)
        return updatedXml

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

        # Now check to see if the skin file has already had the video extras bits added
        if 'script.videoextras' in dialogXmlStr:
            # Already have video extras referenced, so we do not want to do anything else
            # to this file
            log("DialogVideoInfo: Video extras already referenced in %s, skipping file" % dialogXml, xbmc.LOGINFO)
            self.errorToLog = True
            return

        # Now add the include link to the file
        dialogXmlStr = self._addIncludeToXml(dialogXmlStr)

        # Start by adding the onLoad section
        previousOnLoad = '<controls>'

        if previousOnLoad not in dialogXmlStr:
            # The file has had a standard component deleted, so quit
            log("DialogVideoInfo: Could not find controls command, skipping file", xbmc.LOGERROR)
            self.errorToLog = True
            return

        # Now add the Video Extras onLoad command after the allowoverlay one
        DIALOG_VIDEO_INFO_ONLOAD = '<onload condition="System.HasAddon(script.videoextras)">RunScript(script.videoextras,check,"$INFO[ListItem.FilenameAndPath]")</onload>\n\t'
        insertTxt = DIALOG_VIDEO_INFO_ONLOAD + previousOnLoad
        dialogXmlStr = dialogXmlStr.replace(previousOnLoad, insertTxt)

        # Now we need to add the button after the Final button
        previousButton = '<label>13511</label>'

        if previousButton not in dialogXmlStr:
            # The file has had a standard component deleted, so quit
            log("DialogVideoInfo: Could not find final button, skipping file", xbmc.LOGERROR)
            self.errorToLog = True
            return

        # Check to make sure we use a unique ID value for the button
        idOK = False
        idval = 101
        while not idOK:
            idStr = "id=\"%d\"" % idval
            if idStr not in dialogXmlStr:
                idOK = True
            else:
                idval = idval + 1

        # Now add the Video Extras button after the Final one
        DIALOG_VIDEO_INFO_BUTTON = '''\n\t\t\t\t\t</control>\n\t\t\t\t\t<control type="button" id="%d">
\t\t\t\t\t\t<description>Extras</description>
\t\t\t\t\t\t<include>ButtonInfoDialogsCommonValues</include>
\t\t\t\t\t\t<label>$ADDON[script.videoextras 32001]</label>
\t\t\t\t\t\t<onclick>RunScript(script.videoextras,display,"$INFO[ListItem.FilenameAndPath]")</onclick>
\t\t\t\t\t\t<visible>System.HasAddon(script.videoextras) + [Container.Content(movies) | Container.Content(episodes) | Container.Content(TVShows) | Container.Content(musicvideos)] + IsEmpty(Window(movieinformation).Property("HideVideoExtrasButton"))</visible>'''

        insertTxt = previousButton + (DIALOG_VIDEO_INFO_BUTTON % idval)
        dialogXmlStr = dialogXmlStr.replace(previousButton, insertTxt)

        # Now add the section for the icon overlay
        iconPrevious = 'VideoTypeHackFlaggingConditions</include>'
        if iconPrevious not in dialogXmlStr:
            log("DialogVideoInfo: Could not find point to add icon overlay, skipping overlay addition", xbmc.LOGERROR)
            self.errorToLog = True
            return

        DIALOG_VIDEO_INFO_ICON = '''\n\t\t\t\t\t<!-- Add the Video Extras Icon -->
\t\t\t\t\t<include>VideoExtrasLargeIcon</include>
\t\t\t\t</control>
\t\t\t\t<control type="grouplist">
\t\t\t\t\t<description>Add the Video Extras Icon</description>
\t\t\t\t\t<left>210</left>
\t\t\t\t\t<top>480</top>
\t\t\t\t\t<width>600</width>
\t\t\t\t\t<align>left</align>
\t\t\t\t\t<itemgap>2</itemgap>
\t\t\t\t\t<orientation>horizontal</orientation>
\t\t\t\t\t<include>VisibleFadeEffect</include>
\t\t\t\t\t<visible>!Control.IsVisible(50) + Container.Content(tvshows) + !Container.Content(Episodes)</visible>
\t\t\t\t\t<include>VideoExtrasLargeIcon</include>'''

        insertTxt = iconPrevious + DIALOG_VIDEO_INFO_ICON
        dialogXmlStr = dialogXmlStr.replace(iconPrevious, insertTxt)

        self._saveNewFile(dialogXml, dialogXmlStr)

    ##########################################################################
    # UPDATES FOR ViewsVideoLibrary.xml
    ##########################################################################
    def _updateViewsVideoLibrary(self):
        # Get the location of the information dialog XML file
        dialogXml = os_path_join(self.confpath, 'ViewsVideoLibrary.xml')
        log("ViewsVideoLibrary: Confluence dialog XML file: %s" % dialogXml)

        # Make sure the file exists (It should always exist)
        if not xbmcvfs.exists(dialogXml):
            log("ViewsVideoLibrary: Unable to find the file ViewsVideoLibrary.xml, skipping file", xbmc.LOGERROR)
            self.errorToLog = True
            return

        # Load the DialogVideoInfo.xml into a string
        dialogXmlFile = xbmcvfs.File(dialogXml, 'r')
        dialogXmlStr = dialogXmlFile.read()
        dialogXmlFile.close()

        # Now check to see if the skin file has already had the video extras bits added
        if 'IncludesVideoExtras' in dialogXmlStr:
            # Already have video extras referenced, so we do not want to do anything else
            # to this file
            log("ViewsVideoLibrary: Video extras already referenced in %s, skipping file" % dialogXml, xbmc.LOGINFO)
            self.errorToLog = True
            return

        # Update the different view sections
        dialogXmlStr = self._updatePosterWrapView(dialogXmlStr)
        dialogXmlStr = self._updatePosterWrapView2_Fanart(dialogXmlStr)
        dialogXmlStr = self._updateMediaListView3(dialogXmlStr)
        dialogXmlStr = self._updateMediaListView2(dialogXmlStr)
        dialogXmlStr = self._updateMediaListView4(dialogXmlStr)

        # Now add the include link to the file
        dialogXmlStr = self._addIncludeToXml(dialogXmlStr)

        self._saveNewFile(dialogXml, dialogXmlStr)

    # Update the PosterWrapView section of the ViewsVideoLibrary.xml file
    def _updatePosterWrapView(self, dialogXmlStr):
        log("ViewsVideoLibrary: Updating PosterWrapView")
        # Split the text up into lines, this will enable us to process each line
        # to insert the data expected
        lines = dialogXmlStr.splitlines(True)
        totalNumLines = len(lines)
        currentLine = 0

        log("ViewsVideoLibrary: File split into %d lines" % totalNumLines)

        # Go through each line of the original file until we get to the section
        # we are looking for
        while (currentLine < totalNumLines) and ('PosterWrapView' not in lines[currentLine]):
            currentLine = currentLine + 1

        # Found the start of the PosterWrapView, now find where it ends
        sectionEnd = currentLine + 1
        while (sectionEnd < totalNumLines) and ('<include name=' not in lines[sectionEnd]):
            sectionEnd = sectionEnd + 1
        # Set the totalNumLines to the end of this section
        totalNumLines = sectionEnd

        # Now we have started the PosterWrapView we need to go until we get to the tag
        # that contains </itemlayout>
        while (currentLine < totalNumLines) and ('</itemlayout>' not in lines[currentLine]):
            currentLine = currentLine + 1

        if currentLine < totalNumLines:
            insertData = '''\t\t\t\t\t<!-- Add the Video Extras Icon -->
\t\t\t\t\t<control type="group">
\t\t\t\t\t\t<description>VideoExtras Flagging Images</description>
\t\t\t\t\t\t<left>10</left>
\t\t\t\t\t\t<top>310</top>
\t\t\t\t\t\t<include>VideoExtrasOverlayIcon</include>
\t\t\t\t\t</control>\n'''
            lines.insert(currentLine, insertData)
            totalNumLines = totalNumLines + 1
            currentLine = currentLine + 1
        else:
            log("PosterWrapView: Icon Overlay for non selected thumbnails not added", xbmc.LOGERROR)
            self.errorToLog = True

        # Now work until the end of the focus layout as we want to add something before it
        while (currentLine < totalNumLines) and ('</focusedlayout>' not in lines[currentLine]):
            currentLine = currentLine + 1

        if currentLine < totalNumLines:
            insertData = '''\t\t\t\t\t<!-- Add the Video Extras Icon -->
\t\t\t\t\t<control type="group">
\t\t\t\t\t\t<description>VideoExtras Flagging Images</description>
\t\t\t\t\t\t<left>10</left>
\t\t\t\t\t\t<top>300</top>
\t\t\t\t\t\t<include>VideoExtrasOverlayIcon</include>
\t\t\t\t\t\t<animation type="focus">
\t\t\t\t\t\t\t<effect type="fade" start="0" end="100" time="200"/>
\t\t\t\t\t\t\t<effect type="slide" start="0,0" end="-20,40" time="200"/>
\t\t\t\t\t\t</animation>
\t\t\t\t\t\t<animation type="unfocus">
\t\t\t\t\t\t\t<effect type="fade" start="100" end="0" time="200"/>
\t\t\t\t\t\t\t<effect type="slide" end="0,0" start="-20,40" time="200"/>
\t\t\t\t\t\t</animation>
\t\t\t\t\t</control>\n'''
            lines.insert(currentLine, insertData)
            totalNumLines = totalNumLines + 1
            currentLine = currentLine + 1
        else:
            log("PosterWrapView: Icon Overlay for selected thumbnails not added", xbmc.LOGERROR)
            self.errorToLog = True

        # Now find the Codec flag section and add the extras flag to it
        while (currentLine < totalNumLines) and ('VideoTypeHackFlaggingConditions' not in lines[currentLine]):
            currentLine = currentLine + 1

        if currentLine < totalNumLines:
            insertData = '\t\t\t\t<!-- Add the Video Extras Icon -->\n\t\t\t\t<include>VideoExtrasLargeIcon</include>\n'
            lines.insert(currentLine + 1, insertData)
        else:
            log("PosterWrapView: Codec Icon not added", xbmc.LOGERROR)
            self.errorToLog = True

        # Now join all the data together
        return ''.join(lines)

    # Update the PosterWrapView2_Fanart section of the ViewsVideoLibrary.xml file
    def _updatePosterWrapView2_Fanart(self, dialogXmlStr):
        log("ViewsVideoLibrary: Updating PosterWrapView2_Fanart")
        # Split the text up into lines, this will enable us to process each line
        # to insert the data expected
        lines = dialogXmlStr.splitlines(True)
        totalNumLines = len(lines)
        currentLine = 0

        log("ViewsVideoLibrary: File split into %d lines" % totalNumLines)

        # Go through each line of the original file until we get to the section
        # we are looking for
        while (currentLine < totalNumLines) and ('PosterWrapView2_Fanart' not in lines[currentLine]):
            currentLine = currentLine + 1

        # Found the start of the PosterWrapView2_Fanart, now find where it ends
        sectionEnd = currentLine + 1
        while (sectionEnd < totalNumLines) and ('<include name=' not in lines[sectionEnd]):
            sectionEnd = sectionEnd + 1
        # Set the totalNumLines to the end of this section
        totalNumLines = sectionEnd

        # Now find the Codec flag section and add the extras flag to it
        while (currentLine < totalNumLines) and ('VideoTypeHackFlaggingConditions' not in lines[currentLine]):
            currentLine = currentLine + 1

        if currentLine < totalNumLines:
            insertData = '\t\t\t\t<!-- Add the Video Extras Icon -->\n\t\t\t\t<include>VideoExtrasLargeIcon</include>\n'
            lines.insert(currentLine + 1, insertData)
        else:
            log("PosterWrapView2_Fanart: Codec Icon not added", xbmc.LOGERROR)
            self.errorToLog = True

        # Now join all the data together
        return ''.join(lines)

    # Update the MediaListView3 section of the ViewsVideoLibrary.xml file
    def _updateMediaListView3(self, dialogXmlStr):
        log("ViewsVideoLibrary: Updating MediaListView3")
        # Split the text up into lines, this will enable us to process each line
        # to insert the data expected
        lines = dialogXmlStr.splitlines(True)
        totalNumLines = len(lines)
        currentLine = 0

        log("ViewsVideoLibrary: File split into %d lines" % totalNumLines)

        # Go through each line of the original file until we get to the section
        # we are looking for
        while (currentLine < totalNumLines) and ('MediaListView3' not in lines[currentLine]):
            currentLine = currentLine + 1

        # Found the start of the MediaListView3, now find where it ends
        sectionEnd = currentLine + 1
        while (sectionEnd < totalNumLines) and ('<include name=' not in lines[sectionEnd]):
            sectionEnd = sectionEnd + 1
        # Set the totalNumLines to the end of this section
        totalNumLines = sectionEnd

        # Need to add an overlay image for when it is a TV Show
        while (currentLine < totalNumLines) and ('$VAR[BannerThumb]' not in lines[currentLine]):
            currentLine = currentLine + 1
        # Now skip to the end of the control with the banner on, we will overlay our image there
        while (currentLine < totalNumLines) and ('</control>' not in lines[currentLine]):
            currentLine = currentLine + 1

        if currentLine < totalNumLines:
            insertData = '''\t\t\t\t<!-- Add the Video Extras Icon -->
\t\t\t\t<control type="group">
\t\t\t\t\t<top>140</top>
\t\t\t\t\t<left>10</left>
\t\t\t\t\t<align>left</align>
\t\t\t\t\t<include>VideoExtrasLargeIcon</include>
\t\t\t\t</control>\n'''
            lines.insert(currentLine + 1, insertData)
            totalNumLines = totalNumLines + 1
            currentLine = currentLine + 1
        else:
            log("MediaListView3: Overlay for TV Shows not added", xbmc.LOGERROR)
            self.errorToLog = True

        # There are 2 occurrences of the codec flags, one is for TV Episodes, which do not get flagged
        # So skip the first one
        while (currentLine < totalNumLines) and ('VideoTypeHackFlaggingConditions' not in lines[currentLine]):
            currentLine = currentLine + 1
        currentLine = currentLine + 1
        # Now find the Codec flag section and add the extras flag to it
        while (currentLine < totalNumLines) and ('VideoTypeHackFlaggingConditions' not in lines[currentLine]):
            currentLine = currentLine + 1

        if currentLine < totalNumLines:
            insertData = '\t\t\t\t\t<!-- Add the Video Extras Icon -->\n\t\t\t\t\t<include>VideoExtrasLargeIcon</include>\n'
            lines.insert(currentLine + 1, insertData)
        else:
            log("MediaListView3: Codec Icon not added", xbmc.LOGERROR)
            self.errorToLog = True

        # Now join all the data together
        return ''.join(lines)

    # Update the MediaListView2 section of the ViewsVideoLibrary.xml file
    def _updateMediaListView2(self, dialogXmlStr):
        log("ViewsVideoLibrary: Updating MediaListView2")
        # Split the text up into lines, this will enable us to process each line
        # to insert the data expected
        lines = dialogXmlStr.splitlines(True)
        totalNumLines = len(lines)
        currentLine = 0

        log("ViewsVideoLibrary: File split into %d lines" % totalNumLines)

        # Go through each line of the original file until we get to the section
        # we are looking for
        while (currentLine < totalNumLines) and ('MediaListView2' not in lines[currentLine]):
            currentLine = currentLine + 1

        # Found the start of the MediaListView2, now find where it ends
        sectionEnd = currentLine + 1
        while (sectionEnd < totalNumLines) and ('<include name=' not in lines[sectionEnd]):
            sectionEnd = sectionEnd + 1
        # Set the totalNumLines to the end of this section
        totalNumLines = sectionEnd

        # There are 2 occurrences of the codec flags, one is for TV Episodes, which do not get flagged
        # That is the second, so just do the first

        # Now find the Codec flag section and add the extras flag to it
        while (currentLine < totalNumLines) and ('VideoTypeHackFlaggingConditions' not in lines[currentLine]):
            currentLine = currentLine + 1

        if currentLine < totalNumLines:
            # Need to make sure this one only appears on the movies, otherwise it will
            # position it over the image
            # We add a separate control after that for the TV Show
            insertData = '''\t\t\t\t\t<!-- Add the Video Extras Icon -->
\t\t\t\t\t<control type="group">
\t\t\t\t\t\t<include>VideoExtrasLargeIcon</include>
\t\t\t\t\t\t<visible>Container.Content(Movies)</visible>
\t\t\t\t\t</control>
\t\t\t\t</control>
\t\t\t\t<!-- Add the Video Extras Icon -->
\t\t\t\t<control type="group">
\t\t\t\t\t<top>345</top>
\t\t\t\t\t<left>10</left>
\t\t\t\t\t<align>left</align>
\t\t\t\t\t<include>VideoExtrasLargeIcon</include>
\t\t\t\t\t<visible>Container.Content(TVShows)</visible>\n'''
            lines.insert(currentLine + 1, insertData)
        else:
            log("MediaListView2: Codec Icon not added", xbmc.LOGERROR)
            self.errorToLog = True

        # Now join all the data together
        return ''.join(lines)

    # Update the MediaListView4 section of the ViewsVideoLibrary.xml file
    def _updateMediaListView4(self, dialogXmlStr):
        log("ViewsVideoLibrary: Updating MediaListView4")
        # Split the text up into lines, this will enable us to process each line
        # to insert the data expected
        lines = dialogXmlStr.splitlines(True)
        totalNumLines = len(lines)
        currentLine = 0

        log("ViewsVideoLibrary: File split into %d lines" % totalNumLines)

        # Go through each line of the original file until we get to the section
        # we are looking for
        while (currentLine < totalNumLines) and ('MediaListView4' not in lines[currentLine]):
            currentLine = currentLine + 1

        # Found the start of the MediaListView4, now find where it ends
        sectionEnd = currentLine + 1
        while (sectionEnd < totalNumLines) and ('<include name=' not in lines[sectionEnd]):
            sectionEnd = sectionEnd + 1
        # Set the totalNumLines to the end of this section
        totalNumLines = sectionEnd

        # There are 2 occurrences of the codec flags, one is for TV Episodes, which do not get flagged
        # That is the second, so just do the first

        # Now find the Codec flag section and add the extras flag to it
        while (currentLine < totalNumLines) and ('VideoTypeHackFlaggingConditions' not in lines[currentLine]):
            currentLine = currentLine + 1

        if currentLine < totalNumLines:
            insertData = '\t\t\t\t\t<!-- Add the Video Extras Icon -->\n\t\t\t\t\t<include>VideoExtrasLargeIcon</include>\n'
            lines.insert(currentLine + 1, insertData)
        else:
            log("MediaListView4: Codec Icon not added", xbmc.LOGERROR)
            self.errorToLog = True

        # Now add the overlay image for the TV Show
        # Go to the TVSHow section
        while (currentLine < totalNumLines) and ('Container.Content(TVShows)' not in lines[currentLine]):
            currentLine = currentLine + 1
        # Now move forward to the next </bordersize>
        while (currentLine < totalNumLines) and ('</bordersize>' not in lines[currentLine]):
            currentLine = currentLine + 1

        if currentLine < totalNumLines:
            insertData = '''\t\t\t\t</control>\n\t\t\t\t<!-- Add the Video Extras Icon -->
\t\t\t\t<control type="group">
\t\t\t\t\t<description>VideoExtras Flagging Images</description>
\t\t\t\t\t<left>570</left>
\t\t\t\t\t<top>535</top>
\t\t\t\t\t<include>VideoExtrasOverlayIcon</include>\n'''
            lines.insert(currentLine + 1, insertData)
        else:
            log("MediaListView4: TVShows Overlay Icon not added", xbmc.LOGERROR)
            self.errorToLog = True

        # Now join all the data together
        return ''.join(lines)

    ##########################################################################
    # UPDATES FOR ViewsFileMode.xml
    ##########################################################################
    def _updateViewsFileMode(self):
        # Get the location of the information dialog XML file
        dialogXml = os_path_join(self.confpath, 'ViewsFileMode.xml')
        log("ViewsVideoLibrary: Confluence dialog XML file: %s" % dialogXml)

        # Make sure the file exists (It should always exist)
        if not xbmcvfs.exists(dialogXml):
            log("ViewsVideoLibrary: Unable to find the file ViewsFileMode.xml, skipping file", xbmc.LOGERROR)
            self.errorToLog = True
            return

        # Load the DialogVideoInfo.xml into a string
        dialogXmlFile = xbmcvfs.File(dialogXml, 'r')
        dialogXmlStr = dialogXmlFile.read()
        dialogXmlFile.close()

        # Now check to see if the skin file has already had the video extras bits added
        if 'IncludesVideoExtras' in dialogXmlStr:
            # Already have video extras referenced, so we do not want to do anything else
            # to this file
            log("ViewsFileMode: Video extras already referenced in %s, skipping file" % dialogXml, xbmc.LOGINFO)
            self.errorToLog = True
            return

        # Update the different view sections
        dialogXmlStr = self._updateCommonRootView(dialogXmlStr)
        dialogXmlStr = self._updateThumbnailView(dialogXmlStr)
        dialogXmlStr = self._updateWideIconView(dialogXmlStr)
        dialogXmlStr = self._updateFullWidthList(dialogXmlStr)

        # Now add the include link to the file
        dialogXmlStr = self._addIncludeToXml(dialogXmlStr)

        self._saveNewFile(dialogXml, dialogXmlStr)

    # Update the CommonRootView section of the ViewsFileMode.xml file
    def _updateCommonRootView(self, dialogXmlStr):
        log("ViewsFileMode: Updating CommonRootView")
        # Split the text up into lines, this will enable us to process each line
        # to insert the data expected
        lines = dialogXmlStr.splitlines(True)
        totalNumLines = len(lines)
        currentLine = 0

        log("ViewsFileMode: File split into %d lines" % totalNumLines)

        # Go through each line of the original file until we get to the section
        # we are looking for
        while (currentLine < totalNumLines) and ('CommonRootView' not in lines[currentLine]):
            currentLine = currentLine + 1

        # Found the start of the PosterWrapView2_Fanart, now find where it ends
        sectionEnd = currentLine + 1
        while (sectionEnd < totalNumLines) and ('<include name=' not in lines[sectionEnd]):
            sectionEnd = sectionEnd + 1
        # Set the totalNumLines to the end of this section
        totalNumLines = sectionEnd

        # Now find the end of the non focused section
        while (currentLine < totalNumLines) and ('$VAR[PosterThumb]' not in lines[currentLine]):
            currentLine = currentLine + 1
        # We actually want the second one
        currentLine = currentLine + 1
        while (currentLine < totalNumLines) and ('$VAR[PosterThumb]' not in lines[currentLine]):
            currentLine = currentLine + 1
        # Now find the end of the control
        while (currentLine < totalNumLines) and ('</control>' not in lines[currentLine]):
            currentLine = currentLine + 1

        if currentLine < totalNumLines:
            insertData = '''\t\t\t\t</control>\n\t\t\t\t<!-- Add the Video Extras Icon -->
\t\t\t\t<control type="group">
\t\t\t\t\t<description>VideoExtras Flagging Images</description>
\t\t\t\t\t<left>15</left>
\t\t\t\t\t<top>490</top>
\t\t\t\t\t<include>VideoExtrasOverlayIcon</include>\n'''
            lines.insert(currentLine, insertData)
        else:
            log("CommonRootView: Thumb overlay not added", xbmc.LOGERROR)
            self.errorToLog = True

        # Now join all the data together
        return ''.join(lines)

    # Update the ThumbnailView section of the ViewsFileMode.xml file
    def _updateThumbnailView(self, dialogXmlStr):
        log("ViewsFileMode: Updating ThumbnailView")
        # Split the text up into lines, this will enable us to process each line
        # to insert the data expected
        lines = dialogXmlStr.splitlines(True)
        totalNumLines = len(lines)
        currentLine = 0

        log("ViewsFileMode: File split into %d lines" % totalNumLines)

        # Go through each line of the original file until we get to the section
        # we are looking for
        while (currentLine < totalNumLines) and ('ThumbnailView' not in lines[currentLine]):
            currentLine = currentLine + 1

        # Found the start of the PosterWrapView2_Fanart, now find where it ends
        sectionEnd = currentLine + 1
        while (sectionEnd < totalNumLines) and ('<include name=' not in lines[sectionEnd]):
            sectionEnd = sectionEnd + 1
        # Set the totalNumLines to the end of this section
        totalNumLines = sectionEnd

        # Now find the end of the non focused section
        while (currentLine < totalNumLines) and ('</itemlayout>' not in lines[currentLine]):
            currentLine = currentLine + 1
        # We actually want the second one, as the first section is not for videos
        currentLine = currentLine + 1
        while (currentLine < totalNumLines) and ('</itemlayout>' not in lines[currentLine]):
            currentLine = currentLine + 1

        insertData = '''\t\t\t\t\t<!-- Add the Video Extras Icon -->
\t\t\t\t\t<control type="group">
\t\t\t\t\t\t<description>VideoExtras Flagging Images</description>
\t\t\t\t\t\t<left>30</left>
\t\t\t\t\t\t<top>203</top>
\t\t\t\t\t\t<include>VideoExtrasOverlayIcon</include>
\t\t\t\t\t</control>\n'''

        if currentLine < totalNumLines:
            lines.insert(currentLine, insertData)
            totalNumLines = totalNumLines + 1
            currentLine = currentLine + 1
        else:
            log("ThumbnailView: Non focused overlay not added", xbmc.LOGERROR)
            self.errorToLog = True

        # Now find the end of the focused section
        while (currentLine < totalNumLines) and ('</focusedlayout>' not in lines[currentLine]):
            currentLine = currentLine + 1

        if currentLine < totalNumLines:
            lines.insert(currentLine, insertData)
        else:
            log("ThumbnailView: Focused overlay not added", xbmc.LOGERROR)
            self.errorToLog = True

        # Now join all the data together
        return ''.join(lines)

    # Update the WideIconView section of the ViewsFileMode.xml file
    def _updateWideIconView(self, dialogXmlStr):
        log("ViewsFileMode: Updating WideIconView")
        # Split the text up into lines, this will enable us to process each line
        # to insert the data expected
        lines = dialogXmlStr.splitlines(True)
        totalNumLines = len(lines)
        currentLine = 0

        log("ViewsFileMode: File split into %d lines" % totalNumLines)

        # Go through each line of the original file until we get to the section
        # we are looking for
        while (currentLine < totalNumLines) and ('WideIconView' not in lines[currentLine]):
            currentLine = currentLine + 1

        # Found the start of the PosterWrapView2_Fanart, now find where it ends
        sectionEnd = currentLine + 1
        while (sectionEnd < totalNumLines) and ('<include name=' not in lines[sectionEnd]):
            sectionEnd = sectionEnd + 1
        # Set the totalNumLines to the end of this section
        totalNumLines = sectionEnd

        # Now find the end of the non focused section
        while (currentLine < totalNumLines) and ('</itemlayout>' not in lines[currentLine]):
            currentLine = currentLine + 1

        insertData = '''\t\t\t\t\t<!-- Add the Video Extras Icon -->
\t\t\t\t\t<control type="group">
\t\t\t\t\t\t<description>VideoExtras Flagging Images</description>
\t\t\t\t\t\t<left>15</left>
\t\t\t\t\t\t<top>65</top>
\t\t\t\t\t\t<include>VideoExtrasOverlayIcon</include>
\t\t\t\t\t</control>\n'''

        if currentLine < totalNumLines:
            lines.insert(currentLine, insertData)
            totalNumLines = totalNumLines + 1
            currentLine = currentLine + 1
        else:
            log("WideIconView: Non focused overlay not added", xbmc.LOGERROR)
            self.errorToLog = True

        # Now find the end of the focused section
        while (currentLine < totalNumLines) and ('</focusedlayout>' not in lines[currentLine]):
            currentLine = currentLine + 1

        if currentLine < totalNumLines:
            lines.insert(currentLine, insertData)
        else:
            log("WideIconView: Focused overlay not added", xbmc.LOGERROR)
            self.errorToLog = True

        # Now join all the data together
        return ''.join(lines)

    # Update the FullWidthList section of the ViewsFileMode.xml file
    def _updateFullWidthList(self, dialogXmlStr):
        log("ViewsFileMode: Updating FullWidthList")
        # Split the text up into lines, this will enable us to process each line
        # to insert the data expected
        lines = dialogXmlStr.splitlines(True)
        totalNumLines = len(lines)
        currentLine = 0

        log("ViewsFileMode: File split into %d lines" % totalNumLines)

        # Go through each line of the original file until we get to the section
        # we are looking for
        while (currentLine < totalNumLines) and ('FullWidthList' not in lines[currentLine]):
            currentLine = currentLine + 1

        # Found the start of the PosterWrapView2_Fanart, now find where it ends
        sectionEnd = currentLine + 1
        while (sectionEnd < totalNumLines) and ('<include name=' not in lines[sectionEnd]):
            sectionEnd = sectionEnd + 1
        # Set the totalNumLines to the end of this section
        totalNumLines = sectionEnd

        # This processing is a little different from the others, as we work backwards, as we
        # want to read the element that is the label2 part first
        newLeftVal = 965
        labelLine = totalNumLines - 1
        while (labelLine > currentLine) and ('$INFO[ListItem.Label2]' not in lines[labelLine]):
            labelLine = labelLine - 1
        # Now find the <left> element for this one
        while (labelLine > currentLine) and ('<left>' not in lines[labelLine]):
            labelLine = labelLine - 1
        if labelLine > currentLine:
            log("FullWidthList: Found the label2 left line: %s" % lines[labelLine].strip())
            # Extract the current number for the left value
            try:
                newLeftVal = int(lines[labelLine].strip().replace('<left>', '').replace('</left>', '').strip())
                newLeftVal = newLeftVal - 40
            except:
                newLeftVal = 965
            log("FullWidthList: New value for label2 left element is: %d" % newLeftVal)
            # Now update the value
            lines[labelLine] = "\t\t\t\t\t\t<left>%d</left>\n" % newLeftVal

        # Now look back up for the itemlayout
        while (labelLine > currentLine) and ('</itemlayout>' not in lines[labelLine]):
            labelLine = labelLine - 1
        # Then for the next label2
        while (labelLine > currentLine) and ('$INFO[ListItem.Label2]' not in lines[labelLine]):
            labelLine = labelLine - 1
        # Now find the <left> element for this one
        while (labelLine > currentLine) and ('<left>' not in lines[labelLine]):
            labelLine = labelLine - 1
        if labelLine > currentLine:
            lines[labelLine] = "\t\t\t\t\t\t<left>%d</left>\n" % newLeftVal

        # Now find the end of the non focused section
        while (currentLine < totalNumLines) and ('</itemlayout>' not in lines[currentLine]):
            currentLine = currentLine + 1

        insertData = '''\t\t\t\t\t<!-- Add the Video Extras Icon -->
\t\t\t\t\t<control type="group">
\t\t\t\t\t\t<description>VideExtras Flagging Images</description>
\t\t\t\t\t\t<left>1010</left>
\t\t\t\t\t\t<top>8</top>
\t\t\t\t\t\t<include>VideoExtrasListIcon</include>
\t\t\t\t\t\t<visible>Window.IsVisible(Videos) + Container.Content(TVShows)</visible>
\t\t\t\t\t\t<visible>!ListItem.IsStereoscopic</visible>
\t\t\t\t\t</control>
\t\t\t\t\t<control type="group">
\t\t\t\t\t\t<description>VideExtras Flagging Images</description>
\t\t\t\t\t\t<left>968</left>
\t\t\t\t\t\t<top>8</top>
\t\t\t\t\t\t<include>VideoExtrasListIcon</include>
\t\t\t\t\t\t<visible>Window.IsVisible(Videos) + [Container.Content(Movies) | Container.Content(MusicVideos)]</visible>
\t\t\t\t\t\t<visible>!ListItem.IsStereoscopic</visible>
\t\t\t\t\t</control>\n'''

        if currentLine < totalNumLines:
            lines.insert(currentLine, insertData)
            totalNumLines = totalNumLines + 1
            currentLine = currentLine + 1
        else:
            log("FullWidthList: Non focused icon not added", xbmc.LOGERROR)
            self.errorToLog = True

        # Now find the end of the focused section
        while (currentLine < totalNumLines) and ('</focusedlayout>' not in lines[currentLine]):
            currentLine = currentLine + 1

        if currentLine < totalNumLines:
            lines.insert(currentLine, insertData)
        else:
            log("FullWidthList: Focused icon not added", xbmc.LOGERROR)
            self.errorToLog = True

        # Now join all the data together
        return ''.join(lines)


#########################
# Main
#########################
if __name__ == '__main__':
    log("VideoExtras: Updating Confluence Skin (version %s)" % ADDON.getAddonInfo('version'))

    doUpdate = xbmcgui.Dialog().yesno(ADDON.getLocalizedString(32001), ADDON.getLocalizedString(32155))

    if doUpdate:
        try:
            confUp = ConfUpdate()
            confUp.updateSkin()
            del confUp
        except:
            log("VideoExtras: %s" % traceback.format_exc(), xbmc.LOGERROR)
            xbmcgui.Dialog().ok(ADDON.getLocalizedString(32001), ADDON.getLocalizedString(32156), ADDON.getLocalizedString(32152))
