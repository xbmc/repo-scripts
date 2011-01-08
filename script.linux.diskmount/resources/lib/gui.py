import sys
import os
import xbmc
import xbmcaddon
import xbmcgui

_ = sys.modules[ "__main__" ].__language__
__scriptname__ = sys.modules[ "__main__" ].__scriptname__
__settings__ = sys.modules[ "__main__" ].__settings__
__cwd__ = sys.modules[ "__main__" ].__cwd__

EXIT_SCRIPT = ( 9, 10, 247, 275, 61467, )
CANCEL_DIALOG = EXIT_SCRIPT + ( 216, 257, 61448, )

class GUI( xbmcgui.WindowXMLDialog ):
        
    def __init__( self, *args, **kwargs ):
      pass
               
    def onInit( self ):
      pass
           
    def run( self ):

	msg = _( 30106 )  
       	self.status_label(msg)
	aPassword = ""
     
    	kb = xbmc.Keyboard("", _( 30101 ), False)
      	kb.doModal()
      	if (kb.isConfirmed()):
		aPassword=kb.getText()

	if not aPassword == "":

 		if self.getControl( 1501 ).isSelected(): 
			#session
			
			sudo_command = "diskmounter"
			p = os.system('echo %s|sudo -S %s' % (aPassword, sudo_command))

			p = os.system("sudo -K")

			return_msg = _( 30103 )


      		if self.getControl( 1502 ).isSelected():
			#enable
			sudo_command = "sed -i 's/,nodiskmount//g' /etc/default/grub"
			p = os.system('echo %s|sudo -S %s' % (aPassword, sudo_command))

			sudo_command = "update-grub"
			p = os.system('echo %s|sudo -S %s' % (aPassword, sudo_command))

			p = os.system("sudo -K")

			return_msg = _( 30104 )

		if self.getControl( 1503 ).isSelected():
			#disable
			sudo_command = "sed -i 's/xbmc=autostart/xbmc=autostart,nodiskmount/g' /etc/default/grub"
			p = os.system('echo %s|sudo -S %s' % (aPassword, sudo_command))

			sudo_command = "update-grub"
			p = os.system('echo %s|sudo -S %s' % (aPassword, sudo_command))

			p = os.system("sudo -K")

			return_msg = _( 30105 )
	else:
			# No pwd
			return_msg = _( 30107 )  

	return return_msg
        
  
    def status_label(self, msg):
      self.getControl( 180 ).setLabel( msg )
       
 
    def onClick( self, controlId ): 
      
      if controlId == 1098:
        self.exit_script() 

      if controlId == 1096:
        msg = self.run()
        self.status_label(msg)

      if controlId >= 1501 and controlId <= 1503:
         msg = _( 30106 )  
         self.status_label(msg)
         if controlId == 1501: 
		if self.getControl( 1501 ).isSelected():
			self.getControl( 1502 ).setSelected(False)
			self.getControl( 1503 ).setSelected(False)
			
		else:
			pass
	
         if controlId == 1502: 
		if self.getControl( 1502 ).isSelected():
			self.getControl( 1501 ).setSelected(False)
			self.getControl( 1503 ).setSelected(False)
		else:
			pass
         if controlId == 1503: 
		if self.getControl( 1503 ).isSelected():
			self.getControl( 1501 ).setSelected(False)
			self.getControl( 1502 ).setSelected(False)
		else:
			pass

    
    def onFocus( self, controlId ):
        self.controlId = controlId 
        
    def exit_script( self, restart=False ):
        self.close()        
    
    def onAction( self, action ):
        if ( action.getId() in CANCEL_DIALOG):
            self.exit_script()        

  
