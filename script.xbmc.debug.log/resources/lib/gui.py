import sys
import os
import xbmc
import xbmcaddon
import xbmcgui
import shutil
import time
import glob

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
    
      self.log,self.log_old,self.log_crash = self.get_log()
      if self.log != "":
        log_size = os.path.getsize(self.log)
        self.getControl( 2502 ).setLabel( self.convert_bytes(log_size) )
        self.getControl( 2502 ).setVisible(False)  
      if self.log_old != "" and os.path.isfile (self.log_old):
        log_old_size = os.path.getsize(self.log_old)
        self.getControl( 2503 ).setLabel( self.convert_bytes(log_old_size) )
        self.getControl( 2503 ).setVisible(False)
      else:
        self.getControl( 1503 ).setVisible(False)                
      if self.log_crash != "":
        log_crash_size = os.path.getsize(self.log_crash)
        self.getControl( 2501 ).setLabel( self.convert_bytes(log_crash_size) )
        self.getControl( 2501 ).setVisible(False)
      else:
        self.getControl( 1501 ).setVisible(False)
        
      self.tmp_log_folder = os.path.join( xbmc.translatePath( "special://profile/" ), "addon_data", os.path.basename( __cwd__ ),"tmp" )
      if not self.tmp_log_folder.endswith(':') and not os.path.exists(self.tmp_log_folder):
        os.makedirs(self.tmp_log_folder)
      else:
        self.rem_files(self.tmp_log_folder)
      self.tmp_log = os.path.join(self.tmp_log_folder,"tmp.log")        
        
    def convert_bytes(self, bytes):
        bytes = float(bytes)
        if bytes >= 1099511627776:
            terabytes = bytes / 1099511627776
            size = '%.2fTb' % terabytes
        elif bytes >= 1073741824:
            gigabytes = bytes / 1073741824
            size = '%.2fGb' % gigabytes
        elif bytes >= 1048576:
            megabytes = bytes / 1048576
            size = '%.2fMb' % megabytes
        elif bytes >= 1024:
            kilobytes = bytes / 1024
            size = '%.2fKb' % kilobytes
        else:
            size = '%.2fb' % bytes
        return size        


    def get_log(self):
      
      log = log_old = log_crash = ""
      
      if sys.platform == "darwin":
        self.platform = "OSX"
        log = os.path.join(os.path.expanduser("~"),"Library","Logs","xbmc.log")
        log_old = os.path.join(os.path.expanduser("~"),"Library","Logs","xbmc.old.log")
        
        dirpath = os.path.join(os.path.expanduser("~"),"Library","Logs","CrashReporter")
        a = [s for s in os.listdir(dirpath)
              if (os.path.isfile(os.path.join(dirpath, s))) and (s.startswith("XBMC"))]
        a.sort(key=lambda s: os.path.getmtime(os.path.join(dirpath, s)))
        try:
          log_crash = os.path.join(dirpath,a[-1])
        except:
          pass
      elif (sys.platform.startswith('linux')):
        self.platform = "Linux"
        dirpath = os.path.expanduser("~")
        a = [s for s in os.listdir(dirpath)
              if (os.path.isfile(os.path.join(dirpath, s))) and (s.startswith("xbmc_crashlog"))]
        a.sort(key=lambda s: os.path.getmtime(os.path.join(dirpath, s)))
        try:
          log_crash = os.path.join(dirpath,a[-1])
        except:
          pass
        log = os.path.join(xbmc.translatePath( "special://home/temp"),"xbmc.log")
        log_old = os.path.join(xbmc.translatePath( "special://home/temp"),"xbmc.old.log")
   
      elif (sys.platform.startswith('win')):
        self.platform = "Win"
        log = os.path.join(xbmc.translatePath( "special://home"),"xbmc.log")
        log_old = os.path.join(xbmc.translatePath( "special://home"),"xbmc.old.log") 
        
      return log,log_old,log_crash
    
    def debug(self,msg):
      xbmc.output("### [%s] - %s" % (__scriptname__,msg,),level=xbmc.LOGDEBUG )
    
    def pastebin(self,log,e_mail,name):
      import pastebin
      Pastebin = pastebin.Pastebin()
      data = open(log, 'r'+'b').read()
      url = Pastebin.submit(paste_code = data,
                    paste_name = name, paste_email = e_mail, paste_subdomain = None,
                    paste_private = 1, paste_expire_date = "1M",
                    paste_format = None)
      return url
    
            
    def uploadToPastebin(self):
      e_mail = __settings__.getSetting( "email" )
      if e_mail == "":
        kb = xbmc.Keyboard("", _( 30101 ), False)
        kb.doModal()
        if (kb.isConfirmed()): __settings__.setSetting( id='email', value=kb.getText())
      e_mail = __settings__.getSetting( "email" )
      if e_mail == "":
        e_mail = None

      have_log, msg = self.collect_logs(self.tmp_log)
      if have_log:
        self.status_label(_( 30104 ))
        url = self.pastebin(self.tmp_log, e_mail, __scriptname__ )
        return_msg = _( 30106 ) % url
      else:
        return_msg = _( 30107 )  
      return return_msg
        

    def copyToFolder(self):
      msg = ""
      folder = __settings__.getSetting( "folderpath" )
      if folder == "":
#        dialog = xbmcgui.Dialog()
#        folder = dialog.browse(0, _( 30103 ), 'files')
        if folder != "":
          __settings__.setSetting( id='folderpath', value=folder)
          self.status_label("")
        else:
          return "Error: %s" % _( 30103 )
      log_name = "script.xbmc.debug.log_%s.log" % time.strftime("%H_%M_%S", time.localtime())     
      new_log = os.path.join(folder,log_name)
      
      have_log, msg = self.collect_logs(new_log)
      if not have_log: os.remove(new_log)
      
      return msg

    def collect_logs(self,destination_log):
      have_log = False
      outfile = open(xbmc.translatePath( destination_log ), 'wb')
      if self.platform == "Linux":
        if self.getControl( 1501 ).isSelected(): 
          outfile.write(open(self.log_crash, 'rb').read())
          have_log = True
          return  have_log, _( 30108 )
      else:
        if self.getControl( 1501 ).isSelected():
          outfile.write("################### crashlog start #####################\n")
          outfile.write(open(self.log_crash, 'r'+'b').read())
          outfile.write("###################  crashlog end  #####################\n")
          have_log = True
          
      if self.getControl( 1502 ).isSelected():
        if self.platform == "Win":
          log = os.path.join(self.tmp_log_folder,"tmp_win.log")
          cmd = 'copy "%s" "%s" /Y' % (self.log, log)
          ffmpeg = os.popen(cmd)
          xbmc.sleep(1000)
        else:
          log = self.log
        outfile.write("################### xbmc.log start #####################\n")
        outfile.write(open(log, 'r'+'b').read())
        outfile.write("###################  xbmc.log end  #####################\n")
        have_log = True
      if self.getControl( 1503 ).isSelected():
        outfile.write("################### xbmc.old.log start #####################\n") 
        outfile.write(open(self.log_old, 'r'+'b').read())
        outfile.write("###################  xbmc.old.log end  #####################\n")
        have_log = True                
      outfile.flush()
      outfile.close()
      return have_log, _( 30105 ) % (os.path.basename(destination_log) , os.path.dirname(destination_log),)
                  
    def status_label(self, msg):
      self.getControl( 180 ).setLabel( msg )
       
 
    def onClick( self, controlId ): 
      
      if controlId == 1098:
        self.exit_script()
      
      if controlId == 1096:
        msg = self.uploadToPastebin()
        self.status_label(msg)
      
      if controlId == 1097:
        msg = self.copyToFolder()
        self.status_label(msg)
      
      if controlId >= 1501 and controlId <= 1503:
         if controlId == 1501 and self.platform == "Linux":
           if not self.getControl( 1501 ).isSelected():
             self.getControl( 1502 ).setEnabled(True)
             self.getControl( 1503 ).setEnabled(True)  
             self.getControl( 2501 ).setVisible(False)
             if self.getControl( 1502 ).isSelected(): self.getControl( 2502 ).setVisible(True)
             if self.getControl( 1503 ).isSelected(): self.getControl( 2503 ).setVisible(True)
           else:
             self.getControl( 1502 ).setEnabled(False)
             self.getControl( 1503 ).setEnabled(False)
             self.getControl( 2501 ).setVisible(True)  
             if self.getControl( 1502 ).isSelected(): self.getControl( 2502 ).setVisible(False)
             if self.getControl( 1502 ).isSelected(): self.getControl( 2503 ).setVisible(False)
         else:
             if not self.getControl( controlId ).isSelected():
               self.getControl( controlId + 1000 ).setVisible(False)
             else:
               self.getControl( controlId + 1000 ).setVisible(True)           
    
    def onFocus( self, controlId ):
        self.controlId = controlId 
        
    def exit_script( self, restart=False ):
        self.close()        
    
    def onAction( self, action ):
        if ( action.getId() in CANCEL_DIALOG):
            self.exit_script()        

    def rem_files( self, directory):
      try:
        for root, dirs, files in os.walk(directory, topdown=False):
          for items in dirs:
            shutil.rmtree(os.path.join(root, items), ignore_errors=True, onerror=None)
          for name in files:
            os.remove(os.path.join(root, name))
      except:
        try:
          for root, dirs, files in os.walk(directory, topdown=False):
            for items in dirs:
              shutil.rmtree(os.path.join(root, items).decode("utf-8"), ignore_errors=True, onerror=None)
            for name in files:
              os.remove(os.path.join(root, name).decode("utf-8"))
        except:
          pass 

