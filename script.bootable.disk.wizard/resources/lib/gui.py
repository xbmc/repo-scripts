# -*- coding: utf-8 -*-
# *
# *      Copyright (C) 2005-2010 Team XBMC
# *      http://www.xbmc.org
# *
# *  This Program is free software; you can redistribute it and/or modify
# *  it under the terms of the GNU General Public License as published by
# *  the Free Software Foundation; either version 2, or (at your option)
# *  any later version.
# *
# *  This Program is distributed in the hope that it will be useful,
# *  but WITHOUT ANY WARRANTY; without even the implied warranty of
# *  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# *  GNU General Public License for more details.
# *
# *  You should have received a copy of the GNU General Public License
# *  along with XBMC; see the file COPYING.  If not, write to
# *  the Free Software Foundation, 675 Mass Ave, Cambridge, MA 02139, USA.
# *  http://www.gnu.org/copyleft/gpl.html
# *
# */


import os, re, sys, time
import subprocess
import random
import shutil
import statvfs
import optparse
import xbmc
import xbmcgui

import wizardCore

_ = sys.modules[ "__main__" ].__language__
__scriptname__ = sys.modules[ "__main__" ].__scriptname__
__version__ = sys.modules[ "__main__" ].__version__
__settings__ = sys.modules[ "__main__" ].__settings__

CONTROL_END = 1098
CONTROL_NEXT = 1099


class GUI( xbmcgui.WindowXMLDialog ):
	
    def __init__( self, *args, **kwargs ):
      self.debugLogLevel = int(__settings__.getSetting( "debug" ) == "true")
      self.wCore = wizardCore.WizardCore(self.debugLogLevel)
      
    def onInit( self ):
      self.setup_all()

    def setup_all( self ):      
      self.liveDirectory = ""

      # One (hidden) setting may be used to set a custom bootVolume, only for testing/developing purposes
      if (__settings__.getSetting( "cust_liveDirectory" ) == "true"): self.liveDirectory = __settings__.getSetting( "liveDirectory" )
      
      self.availableDisks = []
      self.screen = 1
      self.targetDevice = None
      self.password_confirmed = "xbmc"
      self.password = "xbmc"
      self.hide_all()
      self.storage_size = 0

      # Check the platform for compliance 
      if self.wCore.checkPlatform() == 0:
      #if self.wCore.checkPlatform() != 0: #### ---- For amet to test on Mac ------ ####
           print "This script is supposed to be run only from within XBMCLive." #TODO Remove - Debug Only
           self.screen_9( _(910) )
      else:
           diskMinSize = self.wCore.getMinDiskSize()
           self.getControl( 1100 ).setVisible( True )
           self.getControl( 1006 ).setLabel( "%s[CR][CR][B]%s[/B]" % (_(105),_(106), ) % ( diskMinSize,) )
           
      self.setFocus( self.getControl( 9000 ) )
      
      #### ---- For amet to test screen 5 update on Mac (will be removed :) )------ ####
      #self.hide_all()
      #self.screen_5()
      
      #self.screen_5()


    def hide_all( self ):
      self.getControl( 1100 ).setVisible( False )
      self.getControl( 1200 ).setVisible( False )
      self.getControl( 1300 ).setVisible( False )
      self.getControl( 1400 ).setVisible( False )
      self.getControl( 1500 ).setVisible( False )
      self.getControl( 1600 ).setVisible( False )
      self.getControl( 1700 ).setVisible( False )
      self.getControl( 1900 ).setVisible( False )
      self.getControl( 1510 ).setVisible( False )
      self.getControl( 1502 ).setVisible( False )
      self.getControl( 2000 ).setVisible( False )
   
      
    def screen_next( self, screen ):      
      self.screen = screen + 1
      exec ( "self.screen_%s()" % (self.screen) )
      
##--------- Screen 2 -----------##
    def screen_2( self ):

      self.getControl( 1100 ).setVisible( False )

      self.liveDirectory = self.wCore.findLiveDirectory(self.liveDirectory)
      if self.liveDirectory == None:
         print "Cannot find Live Directory"
         self.screen_9(_(911), _(912))
         return

      self.getControl( 1297 ).setLabel("Using system files at: %s" % (self.liveDirectory,))

      print "Live Directory = '%s'" % (self.liveDirectory) #TODO Remove - Debug Only 
      self.getControl( 1200 ).setVisible( True )
      print "Screen 2" #TODO Remove - Debug Only

##--------- Screen 3 -----------##
    def screen_3( self ):
      self.getControl( 1200 ).setVisible( False )
      print "Screen 3" #TODO Remove - Debug Only

      diskList = self.wCore.findRemovableDisks()
      if len(diskList) == 0:
         print "Cannot find any suitable removable disks" #TODO Remove - Debug Only
         self.screen_9(_(908), _(909))
         return

      guiList = self.getControl(1301)
      for aDisk in diskList:
         guiList.addItem(aDisk)

      # self.setFocus(guiList)
      
      self.getControl( 1300 ).setVisible( True ) 
      self.setFocus( self.getControl( 9000 ) )
      xbmc.executebuiltin("Control.SetFocus(1098,0)")
      
##--------- Screen 4 -----------##
    def screen_4( self ):
      self.hide_all()
      self.getControl( 1400 ).setVisible( True )
      
      diskList = self.getControl(1301)
      selectedDisk = diskList.getSelectedItem().getLabel()
      self.targetDevice = selectedDisk[:selectedDisk.find(" ")]

      self.maxSize = self.wCore.getMaxPermStorageSize(self.targetDevice)
      #self.maxSize = 300
      
      self.getControl( 1402 ).setLabel("%sMB" % (str(self.maxSize), ) )
      self.setFocus( self.getControl( 1401 ) )
      xbmc.executebuiltin("Control.SetFocus(1098,0)")
      print "Screen 4" #TODO Remove - Debug Only

##--------- Screen 5 -----------##
    def screen_5( self ):
      self.hide_all()
      self.getControl( 1500 ).setVisible( True )
      if __settings__.getSetting( "enable_custom_password" ) == "true" :
          self.getControl( 1502 ).setVisible( False )
          self.setFocus( self.getControl( 1503 ) )
      else:
          self.getControl( 1502 ).setVisible( True )    
          self.setFocus( self.getControl( 1502 ) )
         
      self.getControl( 1510 ).setVisible( __settings__.getSetting( "enable_custom_password" ) == "true" )
      
      diskList = self.getControl(1301)
      selectedDisk = diskList.getSelectedItem()
      self.getControl( 1501 ).setLabel(selectedDisk.getLabel())

      print "Screen 5" #TODO Remove - Debug Only      

##--------- Screen 6 -----------##
    def screen_6( self ):
      self.hide_all()
      self.getControl( 1600 ).setVisible( True )
      self.getControl( 2000 ).setVisible( True )
      print "Screen 6" #TODO Remove - Debug Only

      try:
        
        #### ---- For amet to test on Mac ------ ####
        #self.screen_6_updater(1, 10 ,"/Volumes/Macintosh/10.txt" )
        #xbmc.sleep(3000)
        #self.screen_6_updater(2, 20, "/Volumes/Macintosh/20.txt" )
        #xbmc.sleep(3000)
        #self.screen_6_updater(3, 31, "/Volumes/Macintosh/31.txt" )
        #xbmc.sleep(3000)
        #self.screen_6_updater(4, 43, "/Volumes/Macintosh/43.txt" )
                
        self.wCore.createBootableDisk(self.liveDirectory, self.targetDevice, self.storage_size, self.password, self.screen_6_updater)
      except Exception, error:
	eCode = int(str(error))

        errorDescription1 = {
          1:   _(607),
          2:   _(609),
          3:   _(611),
          4:   _(619),
          99:  _(613),
	  -99: _(615)
        }[eCode]

        errorDescription2 = {
          1:   _(608),
          2:   _(610),
          3:   _(612),
          4:   _(620),
          99:  _(614),
	  -99: _(616)
        }[eCode]

        self.screen_9(errorDescription1, errorDescription2)
        return

      self.screen_9(_(904), _(905))

    def screen_6_updater(self, step, percentage = None, item = None):
      statusString = "Step#: %s" % (str(step),)
      if not item == None:
        statusString = "%s - %s" % (statusString,item,)
      if not percentage == None:
        statusString = "%s - %s%%" % (statusString,str(percentage),)
      xbmc.output(statusString, level=xbmc.LOGDEBUG )
#      if self.debugLogLevel>0:
#        statusString = "Step#: " + str(step)
#        if not item == None:
#          statusString = statusString + " - " + item
#        if not percentage == None:
#          statusString = statusString + " - " + str(percentage) + "%"
#        print statusString
      percentage = min(100, percentage)
      self.getControl( 2000 ).setPercent(percentage)### Progress bar :)

      if step == 1:                                 # Partitioning/Formatting
        self.getControl( 1604 ).setVisible( False ) ### First line screen 6,
        self.getControl( 1606 ).setVisible( False ) ###
        self.getControl( 1608 ).setVisible( False ) ###
      if step == 2:                                 # File copy
        self.getControl( 1603 ).setVisible( False ) ### Second line screen 6, 
        self.getControl( 1604 ).setVisible( True )  ### 
      if step == 3:                                 # Install GRUB
        self.getControl( 1605 ).setVisible( False ) ### Third line screen 5, 
        self.getControl( 1606 ).setVisible( True )  ###
      if step == 4:                                 # Permanent storage
        self.getControl( 1607 ).setVisible( False ) ### Fourth line screen 5, 
        self.getControl( 1608 ).setVisible( True )  ###
  
##--------- Screen 9 -----------##
    def screen_9(self, msg_line1 = "" , msg_line2 = "" ):
      self.hide_all()
      self.getControl( 1099 ).setVisible( False )
      if msg_line1 != "": self.getControl( 1902 ).setLabel( msg_line1 ) #----------NOTE ---------
      if msg_line2 != "": self.getControl( 1903 ).setLabel( msg_line2 ) # only change labels if we actually send the msg_line1 and msg_line2 
      self.getControl( 1900 ).setVisible( True )
      print "Screen 9" #TODO Remove - Debug Only
      self.setFocus( self.getControl( 9000 ) )
      xbmc.executebuiltin("Control.SetFocus(1098,0)")

##--------- End Script -----------##


    def exit_script( self, restart=False ):
      self.close()

##--------- Click -----------##

    def onClick( self, controlId ):
      print "controlId: %s" % (controlId) #TODO: Remove - Debug Only
      if ( controlId == CONTROL_END ):
        self.exit_script()
        
      if ( controlId == CONTROL_NEXT ):      
        self.screen_next(self.screen)

      if ( controlId == 1502 ): #Confirm Installation
        self.getControl( 1099 ).setVisible( self.getControl( 1502 ).isSelected() )
              
      if ( controlId == 1503 ): #Password
        self.password = self.keyboard(_(505), True )
        self.getControl( 1503 ).setLabel( self.hide_pass(self.password) )
        if __settings__.getSetting( "enable_custom_password" ) == "true" :
          self.getControl( 1502 ).setVisible((self.password == self.password_confirmed) and self.password_confirmed != "")
          self.getControl( 1099 ).setVisible((self.password == self.password_confirmed) and self.password_confirmed != "" and self.getControl( 1502 ).isSelected())
      if ( controlId == 1504 ): #Confirm Password
        self.password_confirmed = self.keyboard(_(506), True )
        self.getControl( 1504 ).setLabel( self.hide_pass(self.password_confirmed) )
        if __settings__.getSetting( "enable_custom_password" ) == "true" :
          self.getControl( 1502 ).setVisible((self.password == self.password_confirmed) and self.password != "")
          self.getControl( 1099 ).setVisible((self.password == self.password_confirmed) and self.password != "" and self.getControl( 1502 ).isSelected())
      
      if ( controlId == 1401 ):
        slider_percent = int(self.getControl( 1401 ).getPercent())
        print slider_percent #TODO: Remove - Debug Only
        self.storage_size = (self.maxSize / 100) * slider_percent
        self.getControl( 1403 ).setLabel(_(406) % (str(self.storage_size),))

##--------- Keyboard -----------##
    def keyboard(self, header, hidden = False):
        kb = xbmc.Keyboard("", header , hidden)
        kb.doModal()
        if (kb.isConfirmed()): 
            text = kb.getText()
        else:
            text = ""
        return text


##--------- hide password -----------##        
    def hide_pass(self, text):
        text_hidden = "" 
        for i in xrange(len(text)):
    	    text_hidden += "*"
    	return text_hidden             

##--------- Focus -----------##
   
    def onFocus( self, controlId ):
    	self.controlId = controlId
    	
##--------- End Script -----------##
	
def onAction( self, action ):
    if ( action.getButtonCode() in CANCEL_DIALOG ):
      self.exit_script()



