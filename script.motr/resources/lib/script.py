# -*- coding: utf-8 -*-

from __future__ import unicode_literals

from traceback import print_exc
import os, sys, re, socket, urllib, unicodedata, threading, time, traceback, ssl
from urllib.request import urlopen
from resources.lib import kodiutils

import logging
import xbmc, xbmcgui, xbmcaddon, xbmcvfs
import datetime
import gc
import json

from .motrwebsocket import MOTRWebsocket
from .motrconvertdialog import DialogConvertSelect

__pluginname__      = 'script.motr'
__addon__           = xbmcaddon.Addon(id=__pluginname__)
__addonid__         = __addon__.getAddonInfo('id')
__addonname__       = __addon__.getAddonInfo('name')
__cwd__             = __addon__.getAddonInfo('path')
__author__          = __addon__.getAddonInfo('author')
__version__         = __addon__.getAddonInfo('version')
__language__        = __addon__.getLocalizedString
__internaldebug__   = False
__loggerlevel__     = xbmc.LOGDEBUG


def log(msg, level=__loggerlevel__):
    if __internaldebug__ == False and level != xbmc.LOGERROR:
        return
    if level == xbmc.LOGERROR:
        msg += ' ,' + traceback.format_exc()
        #return
    xbmc.log(__addonid__ + '-' + __version__ + '-' + msg, level)

class MOTRPlayer(xbmc.Player):
    def __init__(self):
        xbmc.Player.__init__(self)
        self.is_active = True
        self.seek_done = False

    def onInit(self):
        self.is_active = True
        self.seek_done = False

    def SeekDone(self):
        self.seek_done = True
        
    def onPlayBackStarted(self):
        self.is_active = True

    def onPlayBackStopped(self):
        self.is_active = False

    def onPlayBackEnded(self):
        self.is_active = False
        self.onPlayBackStopped()
    
    def sleep(self, s):
        xbmc.sleep(s) 
        
class GUIandWebsocket(xbmcgui.WindowXML):
    def __init__(self, *args, **kwargs):
        xbmcgui.WindowXML.__init__( self, *args, **kwargs )
        self.WS = MOTRWebsocket(self)
        self.Download = False #Set to true when downloading a file and not streaming
        self.DownloadFilename = '' #The filename we want it to be
        self.LastDirectoryID = -1 #Used to store last ID when you go back
        self.MyPlayer = MOTRPlayer()
        self.StreamResumePosition = 0

    def CleanUp(self):
        try:
            if self.WS.isSocketConnected() == True:
                self.WS.terminate()
            del self.WS
        except Exception as e:
            log(__language__(30000) + repr(e), xbmc.LOGERROR)
            kodiutils.dialogokerror(__language__(30000) + repr(e))
        finally:
            log("Cleanup finished")

    def onInit(self):
        log("Window onInit method called from Kodi")

        self.getControl( 11 ).setVisible(False)
        
        #If we are connected, then this is probably a second time init, called after playback is finished
        if self.WS.isSocketConnected() == True:
            return
            
        self.GUIOnConnection(False)
        xbmcgui.Window (xbmcgui.getCurrentWindowId()).setFocusId( 9100 ) #Connect selected
        
        if kodiutils.get_setting_as_bool('autoconnect') == True:
            self.onClick( 9100 )
        
    def ClearAllListviews(self):
        self.getControl( 100 ).reset()
        self.getControl( 100 ).selectItem(-1)
        self.getControl( 500 ).reset()
        self.getControl( 500 ).selectItem(-1)
        self.getControl( 600 ).reset()
        self.getControl( 600 ).selectItem(-1)

    def AddToQueue(self, queueid, filename, profile, drive, progress, eta, status):
        myitem = xbmcgui.ListItem()
        myitem.setLabel(filename)
        myitem.setLabel2(profile)
        myitem.setProperty('queueid', str(queueid))
        myitem.setProperty('drive', drive)
        myitem.setProperty('progress', str(progress))
        myitem.setProperty('eta', eta)
        myitem.setProperty('status', status)
        myitem.setProperty('separator', "0") #Not a seperator
        self.getControl( 600 ).addItem( myitem )

    def AddQueueSeparator(self, header):
        myitem = xbmcgui.ListItem()
        myitem.setProperty('queueid', str(-1))
        myitem.setProperty('header', header)
        myitem.setProperty('separator', "1") #As a seperator
        self.getControl( 600 ).addItem( myitem )
        
    def AddToDirectory(self, text, nID):
        myitem = xbmcgui.ListItem()
        myitem.setLabel(text)
        myitem.setArt({'icon':'folder.png'})
        myitem.setProperty('nID', str(nID))
        self.getControl( 100 ).addItem( myitem )
    
    def AddToFileList(self, sFileName, nID, bFolder, sFileSize):
        strText = sFileName.encode('ascii', 'ignore').decode('ascii')
        myitem = xbmcgui.ListItem()
        myitem.setLabel(sFileName)
        myitem.setLabel2(sFileSize)
        if bFolder == True:
            myitem.setArt({'icon':'folder.png'})
        else:
            myitem.setProperty('bIsMovie', "False")
            myitem.setProperty('bIsArchive', "False")
            filename, file_extension = os.path.splitext( sFileName )
            file_extension = file_extension.upper()
            if file_extension.endswith(('.MP4','.M4V', '.MKV', '.MPG', '.MPEG', '.AVI', '.WMV', '.FLV', '.WEBM', '.TS', '.MTS', '.M2TS', '.MOV')):
                myitem.setArt({'icon':'video.png'}) 
                myitem.setProperty('bIsMovie', "True")
                myitem.setInfo(type='video', infoLabels={'title': 'DummyTitle', 'plot': 'DummyPlot'})
            elif file_extension == '.ZIP':
                myitem.setArt({'icon':'zip.png'})
            elif file_extension == '.RAR' or re.search(r'\.R\d+$', file_extension):
                myitem.setArt({'icon':'rar.png'})
                myitem.setProperty('bIsArchive', "True")
            else:
                myitem.setArt({'icon':'file.png'})
        myitem.setProperty('nID', str(nID))
        myitem.setProperty('bFolder', str(bFolder))
        self.getControl( 500 ).addItem( myitem )
    
    def SetSorting(self, selectedsort, bSendCommand = False):
        if selectedsort == "NAME":
            self.getControl ( 9500 ).setSelected(True)
            self.getControl ( 9501 ).setSelected(False)
            self.getControl ( 9502 ).setSelected(False)
        if selectedsort == "MODIFY":
            self.getControl ( 9500 ).setSelected(False)
            self.getControl ( 9501 ).setSelected(True)
            self.getControl ( 9502 ).setSelected(False)
        if selectedsort == "SIZE":
            self.getControl ( 9500 ).setSelected(False)
            self.getControl ( 9501 ).setSelected(False)
            self.getControl ( 9502 ).setSelected(True)
        if bSendCommand == True:
            self.WS.SendMOTRCommand("SETFILESORTING", selectedsort)            
    
    def SetCleanFilename(self, isclean, bSendCommand = False):
        #if isinstance(isclean, basestring):
        #    bClean = isclean.upper() == 'TRUE'
        #else
        if isinstance(isclean, bool) == False:
            isclean = isclean.upper()
            bClean = isclean == "TRUE"
        else:
            bClean = isclean
        isclean = 'false'
        if bClean == True:
            isclean = 'true'
        self.getControl ( 9503 ).setSelected(bClean)
        if bSendCommand == True:
            self.WS.SendMOTRCommand("CLEANFILENAMES", isclean)            

    def onClickDirectory(self):
        testitem = self.getControl( 100 ).getSelectedItem()
        nID = testitem.getProperty('nID')
        self.WS.SendMOTRCommand("SETDRIVE",nID);
    
    def onClickFilelist(self):
        testitem = self.getControl( 500 ).getSelectedItem()
        nID = testitem.getProperty('nID')
        bFolder = testitem.getProperty('bFolder')
        if bFolder.upper() == 'TRUE':
            self.WS.SendMOTRCommand("SETFOLDER", nID);
        else:
            sMovie = testitem.getProperty('bIsMovie')
            if sMovie == "True":
                ret = kodiutils.dialogstreamordownload( testitem.getLabel() )
                if ret == 0: #stream
                    log("Streaming movie " + testitem.getLabel())
                    self.Download = False
                    self.StreamResumePosition = 0 #We don't know if the user has a resume yet
                    self.Streamname = testitem.getLabel()
                    self.StreamID = nID #Store the stream ID for after resume-dialog
                    #self.WS.SendMOTRCommand("DOWNLOAD", self.StreamID)
                    self.WS.SendMOTRCommand("GETSTOREDPARAMETER", nID+";PLAYPOSITION") #Ask for resumedata
                elif ret == 1: #View movie information
                    self.MovieQueryID = nID #Store when replied
                    self.WS.SendMOTRCommand("MOVIEINFOQUERY", nID+";"+testitem.getLabel())                
                elif ret == 2: #Convert dialog
                    myconvertdlg = DialogConvertSelect("script-motr-convertdialog.xml", __cwd__, "Default", filename = testitem.getLabel())
                    myconvertdlg.doModal( ) #Gives the selected item as parameter
                    sProfile = myconvertdlg.GetProfile()
                    sFileName = myconvertdlg.GetFilename()
                    nReturn = myconvertdlg.GetReturnStatus()
                    #del myconvertdlg
                    
                    #Cancel = nReturn == 0
                    if nReturn == 0:
                        return
                    
                    #Check if we are converting
                    if len(sProfile) == 0:
                        kodiutils.dialogokerror(__language__(30004))
                        return
                        
                    #Now send the convert message to MOTR based on the filename / profile
                    sTop = "False"
                    if nReturn == 1:
                        sTop = "True"
                    self.WS.SendMOTRCommand("QUEUEADD", nID + ";" + sFileName + ";" + sProfile + ";" + sTop)
                    kodiutils.notification(__language__(30005), sFileName + " " + __language__(30006) )
                    log("Converting movie " + testitem.getLabel() + " with profile: " + sProfile)

                elif ret == 3: #Download
                    self.onDownloadFile(nID, testitem.getLabel() )
            else:
                sArchive = testitem.getProperty('bIsArchive')
                if sArchive == "True":
                    ret = kodiutils.dialogunpackordownload( testitem.getLabel() )
                    if ret == 0: #Extract
                        self.WS.SendMOTRCommand("QUEUEADD", nID+';;Extracting file(s);false')
                        log("Extracting file " + testitem.getLabel())
                    if ret == 1: #Download
                        self.onDownloadFile(nID, testitem.getLabel() )
                else:
                    ret = kodiutils.dialogyesno(__language__(30007), testitem.getLabel())
                    if ret == True:
                        self.onDownloadFile(nID, testitem.getLabel() )
                  
    def onDownloadFile(self, nID, label):
        sPath = kodiutils.get_setting('saveto')
        if len(sPath) == 0: #No path no go
            kodiutils.dialogok(__language__(30001), __language__(30002), __language__(30003), "")
            kodiutils.show_settings()
            return
        #Notify the WS feedback of handling
        self.Download = True
        self.DownloadFilename = label #The filename we want it to be
        self.WS.SendMOTRCommand("DOWNLOAD", nID)
        log("Requesting download for " + label)

    def onClickQueue(self):
        testitem = self.getControl( 600 ).getSelectedItem()
        nQueueID = testitem.getProperty('queueid')
        if nQueueID == "-1":
            return

        nStatus = testitem.getProperty('status')

        #Handle running tasks
        if nStatus == "RUNNING":
            ret = kodiutils.dialogqueuerunning() #0 = view text output, #1 = stop current, #2 = stop all
            if ret == 0:
                self.WS.SendMOTRCommand("SETQUEUESELECTED", nQueueID)
            if ret == 1:
                self.QueueManagementMessage(nQueueID, "stop-running")
            if ret == 2:
                self.QueueManagementMessage(nQueueID, "remove-running")

        #Handle queued items
        if nStatus == "NOT_RUNNING":
            ret = kodiutils.dialogqueuenotrunning()
            if ret == 0: #Run
                self.QueueManagementMessage(nQueueID, "run")
            if ret == 1: #Move top
                self.QueueManagementMessage(nQueueID, "move-top")
            if ret == 2: #Move up
                self.QueueManagementMessage(nQueueID, "move-up")
            if ret == 3: #Move down
                self.QueueManagementMessage(nQueueID, "move-down")
            if ret == 4: #Move bottom
                self.QueueManagementMessage(nQueueID, "move-bottom")
            if ret == 5: #Remove
                self.QueueManagementMessage(nQueueID, "remove")

        #Finished shows only the output
        if nStatus == "FINISHED" or nStatus == "FINISHEDANDFAIL":
            self.WS.SendMOTRCommand("SETQUEUESELECTED", nQueueID)

    def QueueManagementMessage(self, nQueueID, sAction):
            self.WS.SendMOTRCommand("QUEUEMANAGEMENT", nQueueID+";"+sAction)

    def onAction(self, action):
        if action.getId() in ( 9, 10, 92, 216, 247, 257, 275, 61467, 61448 ):
            self.CleanUp()
            self.close()
            
    def onClick(self, controlID):
        if controlID == 9100:
            self.ClearAllListviews()
            sHost = kodiutils.get_setting('host')
            iPort = kodiutils.get_setting_as_int('port')
            bUseSSL = kodiutils.get_setting_as_bool('usessl')

            #Show error if we don't have any port or host
            if len(sHost) == 0:
                kodiutils.dialogok(__language__(30008), __language__(30009), __language__(30010), "")
                kodiutils.show_settings()
                return
                
            self.getControl( 9002 ).setLabel( kodiutils.get_setting('host') ) #print the host we connect to
            log("Connecting to: " + sHost)
            self.WS.ConnectTo(sHost, iPort, bUseSSL, "directory")
        if controlID == 9102:
            self.ClearAllListviews()
            self.WS.terminate()
        if controlID == 6000:
            self.CleanUp()
            self.close()
        if controlID == 9500:
            self.SetSorting("NAME", True)
        if controlID == 9501:
            self.SetSorting("MODIFY", True)
        if controlID == 9502:
            self.SetSorting("SIZE", True)
        if controlID == 9503:
            self.SetCleanFilename( self.getControl ( 9503 ).isSelected() == 1, True)
        if controlID == 100:
            self.onClickDirectory()
        if controlID == 500:
            self.onClickFilelist()
        if controlID == 9101:
            kodiutils.show_settings()
            self.getControl( 9002 ).setLabel( kodiutils.get_setting('host') )
        if controlID == 600:
            self.onClickQueue()
        if controlID == 601:
            if kodiutils.dialogyesno(__language__(30011), __language__(30012)) == True:
                self.WS.SendMOTRCommand("QUEUEMANAGEMENT", "-1;clear-finished") #QueueID = -1 when default commands are used 
        if controlID == 602:
            if kodiutils.dialogyesno(__language__(30011), __language__(30013)) == True:
                self.WS.SendMOTRCommand("QUEUEMANAGEMENT", "-1;stop-all-running") #QueueID = -1 when default commands are used 
        if controlID == 603:
            if kodiutils.dialogyesno(__language__(30011), __language__(30014)) == True:
                self.WS.SendMOTRCommand("QUEUEMANAGEMENT", "-1;remove-all") #QueueID = -1 when default commands are used 

    def GUIOnConnection(self, bConnected):
        if bConnected == True:
            self.getControl( 9100 ).setVisible(False)
            xbmcgui.Window(xbmcgui.getCurrentWindowId()).setFocusId( 9102 )
            self.getControl( 9503 ).controlDown( self.getControl( 9102 ) )
            self.getControl( 9101 ).controlUp( self.getControl( 9102 ) )
        else:
            self.getControl( 9100 ).setVisible(True)
            xbmcgui.Window(xbmcgui.getCurrentWindowId()).setFocusId( 9100 )
            self.getControl( 9503 ).controlDown( self.getControl( 9100 ) )
            self.getControl( 9101 ).controlUp( self.getControl( 9100 ) )
            self.ClearAllListviews()
        self.getControl( 9500 ).setEnabled( bConnected )
        self.getControl( 9501 ).setEnabled( bConnected )
        self.getControl( 9502 ).setEnabled( bConnected )
        self.getControl( 9503 ).setEnabled( bConnected )
        self.getControl( 100 ).setEnabled( bConnected )
        self.getControl( 500 ).setEnabled( bConnected )

    def onWebsocketConnect(self):
        self.getControl( 9100 ).setEnabled( False ) #Disable the connect button when we try to connect
        kodiutils.notification(__language__(30015), __language__(30016), time=1000)
        
    def onWebsocketConnected(self):
        self.getControl( 9100 ).setEnabled( True ) #Enable the connect button when we try to connect
        kodiutils.notification(__language__(30015), __language__(30017), time=1000)
        self.GUIOnConnection(True)
        SessionID = kodiutils.get_setting('SessionID')
        AuthID = kodiutils.get_setting('AuthID')
        Username = kodiutils.get_setting('username')
        self.WS.SendMOTRCommand("SESSIONRESTORE", SessionID+";"+AuthID+";"+Username)

    def onWebsocketDisconnected(self):
        self.getControl( 9100 ).setEnabled( True ) #Disable the connect button when we try to connect
        self.GUIOnConnection(False)
        self.ClearAllListviews()

    def onWebsocketMessage(self, m):
        self.HandleJSONData(m)
        
    def onWebsocketError(self, sLine1, sLine2): #Typical during connection
        kodiutils.dialogokerror(sLine1, sLine2, '')
        self.getControl( 9100 ).setEnabled( True ) #Enable the connect button when we try to connect
        
    def HandleJSONData(self, m):
        if m.is_text:
            textreceived = m.data.decode("utf-8")
        else:
            return

        #Nothing received, nothing todo
        if len(textreceived) == 0:
            return
        #Here catch all exceptions
        try:
            JSONData = json.loads(textreceived)
        except Exception as e:
            log(__language__(30021) + repr(e) + "-->" +  textreceived, xbmc.LOGERROR)
            kodiutils.dialogokerror(__language__(30021) + repr(e) + ": " +  textreceived)
            return

        Command = JSONData['command']
        if Command == 'ERRORNOTLOGGEDIN':
            sUser = kodiutils.get_setting('username')
            sPassword = kodiutils.get_setting('password')
            self.WS.SendMOTRCommand("APPLOGIN", sUser+";"+sPassword)
        if Command == 'APPLOGIN':
            kodiutils.set_setting('SessionID', JSONData['aArray'][0])
            kodiutils.set_setting('AuthID', JSONData['aArray'][2])
            self.WS.SendMOTRCommand("GETAVAILABLEDIRS", "") #Same as "Sessionrestore" handling
        if Command == 'SESSIONRESTORE':
            self.WS.SendMOTRCommand("GETAVAILABLEDIRS", "")
        if Command == 'AVAILABLEDIRS':
            for x in range(0, int(JSONData['count'])):
                self.AddToDirectory(JSONData['aArray'][x]['sDisplayName'], JSONData['aArray'][x]['nID'])
            self.WS.SendMOTRCommand("GETFILESORTING", "")
        if Command == 'FILESORTING':
            sTmpSorting = JSONData['aArray'][0]
            sTmpSetting = kodiutils.get_setting('sorting')
            if sTmpSetting == "":
                sTmpSetting = sTmpSorting
            if sTmpSetting == "0":
                sTmpSetting = "NAME"
            if sTmpSetting == "1":
                sTmpSetting = "MODIFY"
            if sTmpSetting == "2":
                sTmpSetting = "SIZE"
            if sTmpSetting == sTmpSorting:
                self.SetSorting( sTmpSorting )
            else:
                self.SetSorting( sTmpSetting, True ) #Local override, always
            
            self.WS.SendMOTRCommand("GETCLEANFILENAMES", "")
            
        if Command == 'GETCLEANFILENAMES':
            sTmpCleanFile = JSONData['aArray'][0]
            sTmpCleanSetting = kodiutils.get_setting('cleanfilename')
            if sTmpCleanFile == sTmpCleanSetting:
                self.SetCleanFilename( sTmpCleanFile )
            else:
                self.SetCleanFilename( sTmpCleanSetting, True )
            self.WS.SendMOTRCommand("QUEUEREFRESH", "")
            
        if Command == 'QUEUEREFRESH':
            self.getControl( 600 ).reset()
            self.getControl( 600 ).selectItem(-1)
            
            sLastStatus = ""
            for x in range(0, int(JSONData['count'])):
                sStatus = JSONData['aArray'][x]['sDisplayStatus']
                if sStatus != sLastStatus:
                    sLastStatus = sStatus
                    self.AddQueueSeparator(sStatus)
                
                QueueID = JSONData['aArray'][x]['nQueueID']
                sFilename = JSONData['aArray'][x]['sDisplayName']
                sProfile = JSONData['aArray'][x]['sHandbrakeProfile']
                sDrive = JSONData['aArray'][x]['sDisplayDirectory']
                nPercent = JSONData['aArray'][x]['iProcentage']
                sETA = JSONData['aArray'][x]['sETA']
                nStatus = JSONData['aArray'][x]['nStatus']
                
                #Set the finished as actually finished
                if nStatus == "FINISHED":
                    nPercent = 100
                    
                if nStatus == "FINISHEDANDFAIL":
                    nPercent = 100
                
                self.AddToQueue(QueueID, sFilename, sProfile, sDrive, nPercent, sETA, nStatus)
            
            self.WS.SendMOTRCommand("RESTOREFILELIST", "")
            
        if Command == 'UPDATEQUEUEPROCENTAGE':
            nQueueID = JSONData['aArray'][0]
            nPercent = JSONData['aArray'][1]
            sETA = JSONData['aArray'][2]
            
            for x in range(0, self.getControl( 600 ).size()):
                oListItem = self.getControl( 600 ).getListItem(x)
                if oListItem.getProperty('queueid') == str(nQueueID):
                    oListItem.setProperty('progress', str(nPercent))
                    oListItem.setProperty('eta', sETA)
                    break
        
        if Command == 'RESTOREFILELIST':
            #Selects the correct directory after connection
            oDirs = self.getControl( 100 )
            for x in range(0, oDirs.size() ):
                if oDirs.getListItem(x).getLabel() == JSONData['aArray'][0]:
                    oDirs.selectItem(x)
                    break;
                
        if Command == 'FILELIST':
            self.getControl( 500 ).reset()
            for x in range(0, int(JSONData['count'])):
                self.AddToFileList(JSONData['aArray'][x]['sDisplayName'], JSONData['aArray'][x]['nID'], JSONData['aArray'][x]['bIsFolder'], JSONData['aArray'][x]['sFileSize'])
                
            self.WS.SendMOTRCommand("LASTFOLDER", "")
        if Command == 'LASTFOLDER':
            oFiles = self.getControl( 500 )
            for x in range(0, oFiles.size() ):
                if oFiles.getListItem(x).getLabel() == JSONData['aArray'][0]:
                    oFiles.selectItem(x)
                    break;
            
        if Command == 'ERROR':
            kodiutils.dialogokerror( JSONData['aArray'][0] )
            self.onClick(9102) #disconnect after showing error
            kodiutils.show_settings()

        if Command == 'DOWNLOAD':
            sWebConnect = self.DownloadLink('MOTR-download') + JSONData['aArray'][0]
            log("Download/stream link: " + sWebConnect)
            if self.Download == False:
                listitem = xbmcgui.ListItem( self.Streamname ) #To add the filename / streamname we are showing
                self.MyPlayer.onInit() #Zero before start
                self.MyPlayer.play(sWebConnect + "|verifypeer=false", listitem, False, self.StreamResumePosition) #Resume position is not 0 when seek to is selected
                if self.StreamResumePosition == 0: #No resume, no need to trigger seek
                    self.MyPlayer.SeekDone()
                self.TmpPosition = 0
                nTimeCounter = 0
                nTimeCheckSpan = 3
                while self.MyPlayer.is_active:
                    if self.MyPlayer.isPlaying() == True:
                        #Get position in movie
                        nPositionNow = self.MyPlayer.getTime()
                                                
                        #Handle resume
                        if self.MyPlayer.seek_done == False:
                            self.MyPlayer.seekTime(self.StreamResumePosition)
                            nTimeCheck = self.MyPlayer.getTime()
                            if nTimeCheck <= self.StreamResumePosition + nTimeCheckSpan and nTimeCheck >= self.StreamResumePosition - nTimeCheckSpan:
                                kodiutils.notification(__language__(30025), __language__(30026) )
                                self.MyPlayer.SeekDone()

                        #Seek detection, show message when seeking manually, not resume
                        if nPositionNow >= self.TmpPosition + nTimeCheckSpan or nPositionNow <= self.TmpPosition - nTimeCheckSpan:
                            kodiutils.notification(__language__(30027), __language__(30028) )
                            nTimeCounter = 0
                            
                        #Get status from player
                        bCaching = xbmc.getCondVisibility("Player.Caching")
                        bPlaying = xbmc.getCondVisibility("Player.Playing")
                                                    
                        #Reset the timer if we are not caching, 
                        if bPlaying == True and bCaching == False and nTimeCounter > 0:
                            nTimeCounter = 0

                        #If cache, then start counting
                        if bCaching == True:
                            nTimeCounter = nTimeCounter + 1
                                
                        #Showing messages when you are waiting for cache to be handleded
                        if nTimeCounter == 10:
                            kodiutils.notification(__language__(30029), __language__(30030) )                            
                        if nTimeCounter == 20:
                            kodiutils.notification(__language__(30029), __language__(30031) )                            
                        if nTimeCounter == 30:
                            kodiutils.notification(__language__(30029), __language__(30032) )                            
                        if nTimeCounter == 40:
                            kodiutils.notification(__language__(30029), __language__(30033) )                            
                        if nTimeCounter == 50:
                            kodiutils.notification(__language__(30029), __language__(30034) )                            
                        if nTimeCounter == 60:
                            kodiutils.notification(__language__(30029), __language__(30035) )                            

                        #Store the position for saving 
                        self.TmpPosition = self.MyPlayer.getTime()
                    self.MyPlayer.sleep(1000)
                #Set position only during the 30 first secs and no position was set. After that ignore if you past 30 secs and sets it below that (eg start from beginning with an error)
                if (self.TmpPosition > 30 and self.StreamResumePosition > 0) or (self.TmpPosition <= 30 and self.StreamResumePosition <=30) or self.StreamResumePosition == 0:
                    self.WS.SendMOTRCommand("SETSTOREDPARAMETER", self.StreamID+";PLAYPOSITION;"+str(self.TmpPosition)) #Store the position
            else:
                sPath = kodiutils.get_setting('saveto')
                self.DownloadURL(sWebConnect + "|verifypeer=false", sPath + self.DownloadFilename)

        if Command == 'SETQUEUESELECTED':
            iOutput = JSONData['count'] - 1
            sOutput = ""
            for x in range(len(JSONData['aArray'][iOutput])-1, 0, -1 ):
                sOutput += JSONData['aArray'][iOutput][x] + "\n"
            kodiutils.dialogtext(__language__(30018), sOutput)
            
        if Command == 'GETSTOREDPARAMETER':
            sCommand = JSONData['aArray'][0]
            sValue = JSONData['aArray'][1]
            
            if sCommand == "PLAYPOSITION":
                if len(sValue) == 0:
                    self.WS.SendMOTRCommand("DOWNLOAD", self.StreamID)
                else:
                    nTime = int(round(float(sValue)))
                    sTime = " (" + str(datetime.timedelta( seconds=nTime )) + ")"
                    DialogReturn = xbmcgui.Dialog().select(__language__(30022), [__language__(30023) + sTime, __language__(30024)])
                    if DialogReturn == -1: #Cancel...
                        return
                    if DialogReturn == 0: #We resuming position
                        self.StreamResumePosition = nTime #Sets the new position we are going to seek
                    self.WS.SendMOTRCommand("DOWNLOAD", self.StreamID)
        
        if Command == 'MOVIEINFOQUERY':
            #log("MOVIEINFOQUERY aArray: " + JSONData['aArray'] )
            #movieList = json.loads(JSONData['aArray'])
            if JSONData['count'] == 0:
                kodiutils.notification("Movie information", "No information found on that query")
                return
            nSel = 0 #Default select first item
            if JSONData['count'] > 1: #If there are more than one item show a selector
                nSel = xbmcgui.Dialog().select("Movie information", JSONData['aArray'])
                if nSel == -1:
                    return
            self.WS.SendMOTRCommand("MOVIEINFOSELECT", self.MovieQueryID + ";" + str(nSel))
        if Command == 'MOVIEINFO':
            if JSONData['count'] > 0:
                #sHTTPSource = "https://image.tmdb.org/t/p/original/" #alternative directly on tmdb.org
                sHTTPSource = self.DownloadLink("MovieInfo")
                sMovieReceived = JSONData['aArray'][0]
                MovieJSON = json.loads(sMovieReceived)
                liz = xbmcgui.ListItem(MovieJSON['Title'])
                liz.setProperty("IsPlayable", "false")
                liz.setArt({ 'poster': sHTTPSource + MovieJSON['PosterPath'] + "|verifypeer=false", 'banner': 'logo.png'})
                liz.setInfo(type='Video', infoLabels={ 'plot': MovieJSON['Overview'], 'year':  MovieJSON['ReleaseDate'], 'genre': MovieJSON['Genres']})
                liz.setRating("tmdb", MovieJSON['VoteAverage'], MovieJSON['VoteCount'], True)
                liz.setPath('/')
                self.getControl( 11 ).setImage(sHTTPSource + MovieJSON['BackdropPath'] + "|verifypeer=false")
                self.getControl( 11 ).setVisible(True)
                xbmcgui.Dialog().info(liz)
                self.getControl( 11 ).setVisible(False)

    def DownloadLink(self, sDirectory):
        sHost = kodiutils.get_setting('host')
        sPort = kodiutils.get_setting('port')
        bUseSSL = kodiutils.get_setting_as_bool('usessl')
        sWebConnect = 'http://'
        if bUseSSL == True:
            sWebConnect = 'https://'
        return sWebConnect + sHost + ":" + sPort + "/" + sDirectory + "/"
                
    def DownloadURL(self, remote, local):
        if "https" in remote:
            #gcontext = ssl.SSLContext(ssl.PROTOCOL_TLSv1)
            gcontext = ssl._create_unverified_context()
            u = urlopen(remote, context=gcontext)
        else:
            u = urlopen(remote)
        h = u.info()
        totalSize = int(h["Content-Length"])

        log("Downloading " + str(totalSize) + " bytes...")
        
        fp = open(local, 'wb')
        dp = xbmcgui.DialogProgress()
        dp.create(__language__(30019), self.DownloadFilename)

        start_time = time.time()
        
        blockSize = 5 * 1024 * 1024 #5242880 pr block
        count = 0
        lastpercent = -1
        lastsecond = -1
        bUpdateProgress = True
        while True:
            chunk = u.read(blockSize)
            if not chunk:
                break
            fp.write(chunk)
            
            count += 1
            if totalSize > 0:
                #Calculations
                duration = time.time() - start_time
                progress_size = int(count * blockSize)
                speed = int(progress_size / (1024 * duration))
                percent = min(int(count * blockSize * 100 / totalSize),100)
            
                if lastpercent < percent:
                    lastpercent = percent
                    bUpdateProgress = True
                if lastsecond < duration:
                    lastsecond = duration
                    bUpdateProgress = True
            
                if bUpdateProgress == True:
                    progresstring = ("(%d%%, %d MB, %d KB/s, %s %d)" %
                    (percent, progress_size / (1024 * 1024), speed, __language__(30020), duration))
                    dp.update(percent, self.DownloadFilename + "[CR][CR]" + progresstring)
                    bUpdateProgress = False

            if dp.iscanceled():
                break

        dp.close()
        fp.flush()
        fp.close()

def show_dialog():
    mydisplay = GUIandWebsocket("script-motr-main.xml", __cwd__, "Default")
    mydisplay.doModal()
    del mydisplay
    pass
