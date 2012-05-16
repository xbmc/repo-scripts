import xbmc
import xbmcaddon
import xbmcgui
import qfpynm
import time
import sys

#enable localization
getLS   = sys.modules[ "__main__" ].__language__
__cwd__ = sys.modules[ "__main__" ].__cwd__



#TODO Connect to hidden network
#TODO Re-add connect button and add connect dialog with more options
#TODO Display network detail window
#TODO Create a new con name if name=ssid is taken

class GUI(xbmcgui.WindowXMLDialog):

    def __init__(self, *args, **kwargs):
        xbmcgui.WindowXMLDialog.__init__(self, *args, **kwargs)
        self.doModal()


    def onInit(self):
        self.defineControls()

        self.status_msg = ""
        self.status_label.setLabel(self.status_msg)
        
        self.showDialog()
                
        self.status_label.setLabel(self.status_msg)
        self.remove_auto_button.setEnabled(False)
        #self.disconnect_button.setEnabled(False)
       
        
    def defineControls(self):
        #actions
        self.action_cancel_dialog = (9, 10)
        #control ids
        self.control_heading_label_id         = 2
        self.control_list_label_id            = 3
        self.control_list_id                  = 10
        self.control_add_hidden_button_id     = 11
        self.control_refresh_button_id        = 13
        self.control_remove_auto_button_id    = 14
        self.control_install_button_id        = 18
        self.control_cancel_button_id         = 19
        self.control_status_label_id          = 100
        
        #controls
        self.heading_label      = self.getControl(self.control_heading_label_id)
        self.list_label         = self.getControl(self.control_list_label_id)
        self.list               = self.getControl(self.control_list_id)
        self.control_add_hidden_button = self.getControl(self.control_add_hidden_button_id)
        self.remove_auto_button = self.getControl(self.control_remove_auto_button_id)
        self.refresh_button  = self.getControl(self.control_refresh_button_id)
        self.install_button     = self.getControl(self.control_install_button_id)
        self.cancel_button      = self.getControl(self.control_cancel_button_id)
        self.status_label       = self.getControl(self.control_status_label_id)

    def showDialog(self):
        self.updateList()

    def closeDialog(self):        
        import gui
        mainUI = gui.GUI("script_linux_nm-main.xml", __cwd__, "default")
        self.close()
        del mainUI

    def onClick(self, controlId):
        self.status_msg = ""
        self.status_label.setLabel(self.status_msg)
        
        #Add connection from list
        if controlId == self.control_list_id:
            position = self.list.getSelectedPosition()
            #Get SSID!!
            item = self.list.getSelectedItem()

            ssid =  item.getLabel2()  
            encryption = item.getProperty('encryption')
            self.add_wireless(ssid,encryption)        
            self.closeDialog()
       
        #Refresh
        elif controlId == self.control_refresh_button_id:
            msg = getLS(30115) #Refreshing
            self.status_label.setLabel(msg)
            self.updateList()
            msg = ""
            self.status_label.setLabel(msg)
        
        #Add hidden button
        elif controlId == self.control_add_hidden_button_id:
            self.add_hidden()
            self.closeDialog()

        #cancel dialog
        elif controlId == self.control_cancel_button_id:
            self.closeDialog()

    
    def onAction(self, action):
        if action in self.action_cancel_dialog:
            self.closeDialog()

    def onFocus(self, controlId):
        msg = ""
        if hasattr(self, 'status_label'):
            self.status_label.setLabel(msg)

    def add_hidden(self):
        ssid = ''
        kb = xbmc.Keyboard("", getLS(30123), False)
        kb.doModal()
        if (kb.isConfirmed()):
            ssid=kb.getText()
        if ssid == '':
            msg = getLS(30108)  
            self.status_label.setLabel(msg)
            return        
        
        encryption = ''
        kb = xbmc.Keyboard("", getLS(30124), False)
        kb.doModal()
        if (kb.isConfirmed()):
            encryption=kb.getText()
            if encryption != '':
                encryption = encryption.upper()
                
        if encryption == '' or not any(encryption in s for s in ['NONE', 'WEP', 'WPA']):
            msg = getLS(30125)  
            self.status_label.setLabel(msg)
            return  
        self.add_wireless(ssid, encryption)
        
    def add_wireless(self, ssid, encryption):
        finished = False
        while not finished  :
            finished = self.add_wireless_sub(ssid, encryption)
         
    def add_wireless_sub(self, ssid, encryption):
        #Prompt for key
        key = ""
        if not encryption == 'NONE':
            kb = xbmc.Keyboard("", getLS(30104), False)
            kb.doModal()
            if (kb.isConfirmed()):
                key=kb.getText()
                errors = qfpynm.validate_wifi_input(key,encryption)
           
            if key == "" or errors != '':
                msg = getLS(30109)  
                self.status_label.setLabel(msg)
                return True
        if encryption == 'WEP':
            wep_alg = 'shared'
        else:
            wep_alg = ''
            
        con_path = qfpynm.add_wifi(ssid,key,encryption,wep_alg)
        for i in range(1, 150):
            state,stateTXT = qfpynm.get_device_state(qfpynm.get_wifi_device())
            msg = stateTXT
            self.status_label.setLabel(msg)
            # Do not exit directly just to be sure.
            # If trying with a bad key when wifi is disconnected do not give state 60 but 30....
            # better never to disconnect wifi and only deactivate c
            if (i > 10 and state == 60) or (i > 10 and state == 30)  or (state == 100 and i >2):
                break
            time.sleep(1)
            msg = ''
            self.status_label.setLabel(msg)
            time.sleep(1)
        if state == 100:
            msg = getLS(30120) #"Connected!"
            self.status_label.setLabel(msg)
            return True
        if (state == 60  or state == 30) and encryption != "NONE":
            msg = getLS(30121) #"Not Autorized!"
            self.status_label.setLabel(msg)
            return False
        
        msg = getLS(30122) #"Connection failed"
        self.status_label.setLabel(msg)      
        return True


    def updateList(self):
        print "updating list"
        self.list.reset()
        
        #qfpynm.scan_wireless()
        wlessL = qfpynm.get_wireless_networks()        
        for net_dict in wlessL:
            if net_dict['connected'] == True:
                sts = '>'
            elif net_dict['automatic'] == '1':
                sts = 'a'
            else:
                sts = ''
                
            item = xbmcgui.ListItem (label=sts, label2 = net_dict['essid'])
            item.setProperty('channel',str(net_dict['channel']))
            item.setProperty('encryption',str(net_dict['encrypt']))
            item.setProperty('signal',str(net_dict['signal']))
            self.list.addItem(item)
    
    
            
