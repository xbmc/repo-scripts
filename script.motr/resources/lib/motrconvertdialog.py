# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from traceback import print_exc
import os, sys, re, socket, urllib, unicodedata, threading, time
from resources.lib import kodiutils
#from resources.lib import kodilogging
import logging
import xbmc, xbmcgui, xbmcaddon, xbmcvfs

ADDON = xbmcaddon.Addon()
__lang__ = ADDON.getLocalizedString

#Groups in profiles
aHandBreakPresetsGroups = [
['General', 0,16],
['Web', 16, 19],
['Devices', 19, 45],
['Matroska', 45, 61],
['Legacy', 61, 72]
]

aHandBreakPresets = [
#General
'Very Fast 1080p30',
'Very Fast 720p30',
'Very Fast 576p25',
'Very Fast 480p30',
'Fast 1080p30',
'Fast 720p30',
'Fast 576p25',
'Fast 480p30',
'HQ 1080p30 Surround',
'HQ 720p30 Surround',
'HQ 576p25 Surround',
'HQ 480p30 Surround',
'Super HQ 1080p30 Surround',
'Super HQ 720p30 Surround',
'Super HQ 576p25 Surround',
'Super HQ 480p30 Surround',
#Web
'Gmail Large 3 Minutes 720p30',
'Gmail Medium 5 Minutes 480p30',
'Gmail Small 10 Minutes 288p30',
#Devices
'Android 1080p30',
'Android 720p30',
'Android 576p25',
'Android 480p30',
'Apple 1080p60 Surround',
'Apple 1080p30 Surround',
'Apple 720p30 Surround',
'Apple 540p30 Surround',
'Apple 240p30',
'Chromecast 1080p30 Surround',
'Fire TV 1080p30 Surround',
'Playstation 1080p30 Surround',
'Playstation 720p30',
'Playstation 540p30',
'Roku 2160p60 4K Surround',
'Roku 2160p30 4K Surround',
'Roku 1080p30 Surround',
'Roku 720p30 Surround',
'Roku 576p25',
'Roku 480p30',
'Windows Mobile 1080p30',
'Windows Mobile 720p30',
'Windows Mobile 540p30',
'Windows Mobile 480p30',
'Xbox 1080p30 Surround',
'Xbox Legacy 1080p30 Surround',
#Matroska
'H.264 MKV 1080p30',
'H.264 MKV 720p30',
'H.264 MKV 576p25',
'H.264 MKV 480p30',
'H.265 MKV 1080p30',
'H.265 MKV 720p30',
'H.265 MKV 576p25',
'H.265 MKV 480p30',
'VP8 MKV 1080p30',
'VP8 MKV 720p30',
'VP8 MKV 576p25',
'VP8 MKV 480p30',
'VP9 MKV 1080p30',
'VP9 MKV 720p30',
'VP9 MKV 576p25',
'VP9 MKV 480p30',
#Legacy
'Normal',
'High Profile',
'Universal',
'iPod',
'iPhone & iPod touch',
'iPad',
'AppleTV',
'AppleTV 2',
'AppleTV 3',
'Android',
'Android Tablet',
'Windows Phone 8'
]

aHandBreakPresetsDescription = [
#General
'General - seperator, not selectable',
'Small H.264 video (up to 1080p30) and AAC stereo audio, in an MP4 container.',
'Small H.264 video (up to 720p30) and AAC stereo audio, in an MP4 container.',
'Small H.264 video (up to 576p25) and AAC stereo audio, in an MP4 container.',
'Small H.264 video (up to 480p30) and AAC stereo audio, in an MP4 container.',
'H.264 video (up to 1080p30) and AAC stereo audio, in an MP4 container.',
'H.264 video (up to 720p30) and AAC stereo audio, in an MP4 container.',
'H.264 video (up to 576p25) and AAC stereo audio, in an MP4 container.',
'H.264 video (up to 480p30) and AAC stereo audio, in an MP4 container.',
'High quality H.264 video (up to 1080p30), AAC stereo audio, and Dolby Digital (AC-3) surround audio, in an MP4 container.',
'High quality H.264 video (up to 720p30), AAC stereo audio, and Dolby Digital (AC-3) surround audio, in an MP4 container.',
'High quality H.264 video (up to 576p25), AAC stereo audio, and Dolby Digital (AC-3) surround audio, in an MP4 container.',
'High quality H.264 video (up to 480p30), AAC stereo audio, and Dolby Digital (AC-3) surround audio, in an MP4 container.',
'Super high quality H.264 video (up to 1080p30), AAC stereo audio, and Dolby Digital (AC-3) surround audio, in an MP4 container.',
'Super high quality H.264 video (up to 720p30), AAC stereo audio, and Dolby Digital (AC-3) surround audio, in an MP4 container.',
'Super high quality H.264 video (up to 576p25), AAC stereo audio, and Dolby Digital (AC-3) surround audio, in an MP4 container.',
'Super high quality H.264 video (up to 480p30), AAC stereo audio, and Dolby Digital (AC-3) surround audio, in an MP4 container.',
#Web
'Web - seperator, not selectable',
'Encode up to 3 minutes of video in large size for Gmail (25 MB or less). H.264 video (up to 720p30) and AAC stereo audio, in an MP4 container.',
'Encode up to 5 minutes of video in medium size for Gmail (25 MB or less). H.264 video (up to 720p30) and AAC stereo audio, in an MP4 container.',
'Encode up to 10 minutes of video in small size for Gmail (25 MB or less). H.264 video (up to 720p30) and AAC stereo audio, in an MP4 container.',
#Devices
'Devices - seperator, not selectable',
'H.264 video (up to 1080p30) and AAC stereo audio, in an MP4 container. Compatible with Android devices.',
'H.264 video (up to 720p30) and AAC stereo audio, in an MP4 container. Compatible with Android devices.',
'H.264 video (up to 576p25) and AAC stereo audio, in an MP4 container. Compatible with Android devices.',
'H.264 video (up to 480p30) and AAC stereo audio, in an MP4 container. Compatible with Android devices.',
'H.264 video (up to 1080p60), AAC stereo audio, and Dolby Digital (AC-3) surround audio, in an MP4 container. Compatible with Apple iPad Pro; iPad Air; iPad mini 2nd, 3rd Generation and later; Apple TV 4th Generation and later.',
'H.264 video (up to 1080p30), AAC stereo audio, and Dolby Digital (AC-3) surround audio, in an MP4 container. Compatible with Apple iPhone 5, 5S, 6, 6s, and later; iPod touch 6th Generation and later; iPad Pro; iPad Air; iPad 3rd, 4th Generation and later; iPad mini; Apple TV 3rd Generation and later.',
'H.264 video (up to 720p30), AAC stereo audio, and Dolby Digital (AC-3) surround audio, in an MP4 container. Compatible with Apple iPhone 4 and later; iPod touch 4th, 5th Generation and later; Apple TV 2nd Generation and later.',
'H.264 video (up to 540p30), AAC stereo audio, and Dolby Digital (AC-3) surround audio, in an MP4 container. Compatible with Apple iPhone 1st Generation, 3G, 3GS, and later; iPod touch 1st, 2nd, 3rd Generation and later; iPod Classic; Apple TV 1st Generation and later.',
'H.264 video (up to 240p30) and AAC stereo audio, in an MP4 container. Compatible with Apple iPod 5th Generation and later.',
'H.264 video (up to 1080p30), AAC stereo audio, and Dolby Digital (AC-3) surround audio, in an MP4 container. Compatible with Google Chromecast.',
'H.264 video (up to 1080p30), AAC stereo audio, and Dolby Digital (AC-3) audio, in an MP4 container. Compatible with Amazon Fire TV.',
'H.264 video (up to 1080p30), AAC stereo audio, and Dolby Digital (AC-3) surround audio, in an MP4 container. Compatible with Playstation 3 and 4.',
'H.264 video (up to 720p30) and AAC stereo audio, in an MP4 container. Compatible with Playstation Vita TV.',
'H.264 video (up to 540p30) and AAC stereo audio, in an MP4 container. Compatible with Playstation Vita.',
'H.265 video (up to 2160p60), AAC stereo audio, and surround audio, in an MKV container. Compatible with Roku 4.',
'H.265 video (up to 2160p30), AAC stereo audio, and surround audio, in an MKV container. Compatible with Roku 4.',
'H.264 video (up to 1080p30), AAC stereo audio, and Dolby Digital (AC-3) surround audio, in an MP4 container. Compatible with Roku 1080p models.',
'H.264 video (up to 720p30), AAC stereo audio, and Dolby Digital (AC-3) surround audio, in an MP4 container. Compatible with Roku 720p models.',
'H.264 video (up to 576p25) and AAC stereo audio, in an MP4 container. Compatible with Roku standard definition models.',
'H.264 video (up to 480p30) and AAC stereo audio, in an MP4 container. Compatible with Roku standard definition models.',
'H.264 video (up to 1080p30) and AAC stereo audio, in an MP4 container. Compatible with Windows Mobile devices with Qualcomm Snapdragon 800 (MSM8974), S4 (MSM8x30, MSM8960), and better CPUs.',
'H.264 video (up to 720p30) and AAC stereo audio, in an MP4 container. Compatible with Windows Mobile devices with Qualcomm Snapdragon S4 (MSM8x27), S2 (MSM8x55), S1 (MSM8x50), and better CPUs.',
'H.264 video (up to 540p30) and AAC stereo audio, in an MP4 container. Compatible with Windows Mobile devices with Qualcomm Snapdragon 200 (MSM8210, MSM8212) and better CPUs.',
'H.264 video (up to 480p30) and AAC stereo audio, in an MP4 container. Compatible with Windows Mobile devices with Qualcomm Snapdragon S1 (MSM7x27a) and better CPUs.',
'H.264 video (up to 1080p30), AAC stereo audio, and Dolby Digital (AC-3) surround audio, in an MP4 container. Compatible with Xbox One.',
'H.264 video (up to 1080p30), AAC stereo audio, and Dolby Digital (AC-3) surround audio, in an MP4 container. Compatible with Xbox 360.',
#Matroska
'Matroska - seperator, not selectable',
'H.264 video (up to 1080p30) and AAC stereo audio, in an MKV container.',
'H.264 video (up to 720p30) and AAC stereo audio, in an MKV container.',
'H.264 video (up to 576p25) and AAC stereo audio, in an MKV container.',
'H.264 video (up to 480p30) and AAC stereo audio, in an MKV container.',
'H.265 video (up to 1080p30) and AAC stereo audio, in an MKV container.',
'H.265 video (up to 720p30) and AAC stereo audio, in an MKV container.',
'H.265 video (up to 576p25) and AAC stereo audio, in an MKV container.',
'H.265 video (up to 480p30) and AAC stereo audio, in an MKV container.',
'VP8 video (up to 1080p30) and Vorbis stereo audio, in an MKV container.',
'VP8 video (up to 720p30) and Vorbis stereo audio, in an MKV container.',
'VP8 video (up to 576p25) and Vorbis stereo audio, in an MKV container.',
'VP8 video (up to 480p30) and Vorbis stereo audio, in an MKV container.',
'VP9 video (up to 1080p30) and Opus stereo audio, in an MKV container.',
'VP9 video (up to 720p30) and Opus stereo audio, in an MKV container.',
'VP9 video (up to 576p25) and Opus stereo audio, in an MKV container.',
'VP9 video (up to 480p30) and Opus stereo audio, in an MKV container.',
#Legacy
'Legacy - seperator, not selectable',
'Legacy HandBrake 0.10.x H.264 Main Profile preset.',
'Legacy HandBrake 0.10.x H.264 High Profile preset.',
'Legacy HandBrake 0.10.x preset including Dolby Digital (AC-3) surround sound and compatible with nearly all Apple devices.',
'Legacy HandBrake 0.10.x preset compatible with Apple iPod 5th Generation and later.',
'Legacy HandBrake 0.10.x preset compatible with Apple iPhone 4, iPod touch 3rd Generation, and later devices.',
'Legacy HandBrake 0.10.x preset compatible with Apple iPad (all generations).',
'Legacy HandBrake 0.10.x preset including Dolby Digital (AC-3) surround sound, compatible with Apple TV 1st Generation and later.',
'Legacy HandBrake 0.10.x preset including Dolby Digital (AC-3) surround sound, compatible with Apple TV 2nd Generation and later.',
'Legacy HandBrake 0.10.x preset including Dolby Digital (AC-3) surround sound, compatible with Apple TV 3rd Generation and later.',
'Legacy HandBrake 0.10.x preset compatible with Android 2.3 and later handheld devices.',
'Legacy HandBrake 0.10.x preset compatible with Android 2.3 and later tablets.',
'Legacy HandBrake 0.10.x preset compatible with most Windows Phone 8 devices.'
]

class DialogConvertSelect(xbmcgui.WindowXMLDialog):
    def __init__(self, *args, **kwargs):
        xbmcgui.WindowXMLDialog.__init__( self, *args, **kwargs)
        #for count, thing in enumerate(args):
        #    print( '{0}. {1}'.format(count, thing))
        self.sFileName = "Filename not set"
        self.sProfile = ""
        self.nReturnStatus = 0 #0 = cancel, #1 = add top, #2 = add bottom
        for name, value in list(kwargs.items()):
            if name == 'filename':
                self.sFullFileName = value
                self.sFileName, self.FileExtension = os.path.splitext(self.sFullFileName)
            #print( '{0} = {1}'.format(name, value))
        
    def onInit(self):
        self.AddProfiles()
        self.SetFilename("") #No profile selected at startup

    def onAction(self, action):
        if action.getId() in ( 9, 10, 92, 216, 247, 257, 275, 61467 ):
            self.close()
        
    def onClick(self, controlID):
        if controlID == 9601:
            nPos = self.getControl( 9601 ).getSelectedPosition()
            if nPos != -1:
                sTemp = aHandBreakPresetsDescription[nPos]
                if sTemp.find('not selectable') != -1:
                    return
                self.getControl( 9602 ).setText( sTemp )
                self.sProfile = self.getControl( 9601 ).getSelectedItem().getLabel()
                self.SetFilename( self.sProfile )
                
        if controlID == 9610: #Add top
            self.CheckIfValidProfile(1) #Add top
        if controlID == 9611: #Add bottom
            self.CheckIfValidProfile(2) #Add bottom
        if controlID == 9612: #Add top
            self.CheckIfValidProfile(0) #Cancel
            
    def CheckIfValidProfile(self, nReturn):
        if len(self.sProfile) == 0 and nReturn != 0:
            kodiutils.dialogokerror(__lang__(30300), __lang__(30301))
            return
        self.nReturnStatus = nReturn
        self.close()
            
    def AddProfiles(self):
        for x in range(0, len(aHandBreakPresetsGroups)):
            self.AddProfileSeparator(aHandBreakPresetsGroups[x][0])
            for y in range(aHandBreakPresetsGroups[x][1], aHandBreakPresetsGroups[x][2]):
                self.AddToProfile(aHandBreakPresets[y])
        self.setFocusId( 9601 )
        self.getControl( 9601 ).selectItem(0)
        self.onClick(9601) #Trigger a selection
        
    def AddToProfile(self, header):
        myitem = xbmcgui.ListItem()
        myitem.setLabel(header)
        myitem.setProperty('separator', "0") #Not a seperator
        self.getControl( 9601 ).addItem( myitem )

    def AddProfileSeparator(self, header):
        myitem = xbmcgui.ListItem()
        myitem.setProperty('header', header)
        myitem.setProperty('separator', "1") #As a seperator
        self.getControl( 9601 ).addItem( myitem )

    def SetFilename(self, sProfile):
        self.getControl( 9603 ).setText(self.sFileName + "-MOTR[" + sProfile + "]" + self.FileExtension)

    def GetFilename(self):
        sReturn = self.getControl( 9603 ).getText()
        if len(sReturn) == 0:
            sReturn = self.SetFilename("")
            sReturn = self.getControl( 9603 ).getText()
        return sReturn

    def GetProfile(self):
        return self.sProfile
    
    def GetReturnStatus(self):
        return self.nReturnStatus
