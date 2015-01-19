# -*- coding: utf-8 -*-
#/*
# *      Copyright (C) 2005-2013 Team XBMC
# *      http://xbmc.org
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
# *  along with XBMC; see the file COPYING.  If not, see
# *  <http://www.gnu.org/licenses/>.
# *
# */


import os, sys
import xbmc
import xbmcgui

_ = sys.modules[ "__main__" ].__language__
__scriptname__ = sys.modules[ "__main__" ].__scriptname__
__version__    = sys.modules[ "__main__" ].__version__
__addon__      = sys.modules[ "__main__" ].__addon__


CANCEL_DIALOG = (  9, 10, 216, 247, 257, 275, 61448, 61467, )


class GUI( xbmcgui.WindowXMLDialog ):
	
    def __init__( self, *args, **kwargs ):
      global alsaMixerCore
      self.controlId = 0
      self.control_state = {}
      self.counter = 1
      
    def onInit( self ):
      if sys.platform == "darwin":
        import osascriptCore as alsaMixerCore
      else:  
        import alsaMixerCore

      self.alsaCore = alsaMixerCore.alsaMixerCore(int(__addon__.getSetting( "debug" ) == "true"))
      self.controls = self.alsaCore.getPlaybackControls()     
      self.get_values()


    def get_values(self):
      controls = self.controls
      first_set = False
      while controls:
        for aControl in controls:
          if self.alsaCore.hasSwitch(aControl) or first_set:
            self.log( "Testing Control [%s] output [%s]" % (aControl, str(self.alsaCore.getVolume(aControl))))
            self.set_gui_values(aControl)
            controls.remove(aControl)
            first_set = True
      self.getControl( 1000*self.counter ).setVisible( False )  
    
    def set_gui_values( self, aControl ):
      
      if not self.alsaCore.hasSwitch(aControl):
          self.getControl( self.counter + 900 ).setVisible( False )
      if not self.alsaCore.hasVolume(aControl):
          self.getControl( (1000*self.counter)+902 ).setVisible( False )
          self.getControl( (1000*self.counter)+903 ).setVisible( False )
      else:
          if not self.alsaCore.hasSwitch(aControl):
              self.getControl( self.counter + 900 -1 ).controlDown( self.getControl((1000*self.counter)+902) )
              self.getControl( self.counter + 900 +1 ).controlUp( self.getControl((1000*self.counter)+902) )  
              self.getControl( (1000*self.counter)+902 ).controlDown( self.getControl( self.counter + 900 +1 ))
              self.getControl( (1000*self.counter)+902 ).controlUp( self.getControl( self.counter + 900 -1 ))
      volume = str(self.alsaCore.getVolume(aControl))
      
      self.getControl( 1000*self.counter ).setVisible( True )
      self.getControl( (1000*self.counter)+900 ).setLabel( aControl )
      
      if volume =="on" or volume =="off":
        if volume =="off":
          self.getControl( self.counter + 900 ).setSelected( True )
        if not self.alsaCore.hasVolume(aControl):
          self.getControl( (1000*self.counter)+902 ).setVisible( False )
          self.getControl( (1000*self.counter)+903 ).setVisible( False )
        self.control_state[(1000*self.counter)+902] = 0
        self.getControl( (1000*self.counter)+903 ).setLabel( "00 %")
      elif volume.isdigit():
        if int(volume) == 0 :self.getControl( self.counter + 900 ).setSelected( True )
        try:
          self.control_state[(1000*self.counter)+902] = int(volume)
          self.getControl( (1000*self.counter)+902 ).setPercent(int(volume)) 
        except:
          pass
        self.getControl( (1000*self.counter)+903 ).setLabel( "%.2d %s" % (int(volume), "%",)) 
      
      self.counter += 1
    

    def set_mute( self, controlId, set_label = True ):
      
      i = controlId - 900
      control = self.getControl( (1000*i)+900 ).getLabel()
      label_value = self.getControl( (1000*i)+903 ).getLabel().replace(" %","" )
      if self.getControl( i + 900 ).isSelected():
        self.alsaCore.setVolume( control, "off" )
      else:
          if not self.alsaCore.hasVolume(control):
            self.alsaCore.setVolume( control, "on" )
          else:
            self.alsaCore.setVolume( control, "on" )
            if set_label:
              self.alsaCore.setVolume( control, label_value )
        

    def set_slider_value( self, controlId ):
      

      i = (controlId - 902)/1000
      self.set_mute(i+900, False)
      control = self.getControl( (1000*i)+900 ).getLabel()
      label_value = self.getControl( (1000*i)+903 ).getLabel().replace(" %","" )
      self.alsaCore.setVolume( control, label_value )

    def exit_script( self ):
      self.close()

    def onClick( self, controlId ):
     if ( controlId >= 1000 ):
        self.getControl( controlId + 1 ).setLabel("%.2d %s" % (int(self.getControl( controlId ).getPercent()), "%",))
        if self.getControl( controlId ).getPercent() == 0:
          self.getControl( (controlId/1000) + 900 ).setSelected( True )
        else:
          self.getControl( (controlId/1000) + 900 ).setSelected( False )  

     if ( controlId >= 900 ) and ( controlId <  1000 ):
        self.set_mute(controlId)
   
    def onFocus( self, controlId ):
        self.log("Focused: [%i] Previous [%s]" % (controlId,self.controlId,))
        if self.controlId == 0: self.controlId = controlId     
        if ( self.controlId >= 1000 ):
            self.slider_onfocus(controlId)
        self.controlId = controlId
       
    def slider_onfocus(self, controlId):
        cur_slider = self.getControl( self.controlId ).getPercent()
        try:
          if self.control_state[self.controlId] != cur_slider:
            slider_set = True
          else:
            slider_set = False
        except:
          slider_set = False 
        if ( self.controlId != controlId ) and slider_set :  
          self.set_slider_value(self.controlId)
          self.control_state[self.controlId] = cur_slider
       
    def log(self, msg):
      xbmc.log("##### [%s] - Debug msg: %s" % (__scriptname__,msg,),level=xbmc.LOGDEBUG )        
    
    def onAction( self, action ):
    
        if ( action.getButtonCode() == 61453 ):
          if ( self.controlId >= 1000 ):
              self.slider_onfocus(0)
          
        if ( action.getButtonCode() in CANCEL_DIALOG ):
          self.log("Exit")
          if ( self.controlId >= 1000 ) or (action.getId() == 92):
              self.slider_onfocus(0)
              self.controlId = 0
          self.exit_script()


