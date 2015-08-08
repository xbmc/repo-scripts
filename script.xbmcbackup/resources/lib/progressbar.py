import utils as utils
import xbmcgui

class BackupProgressBar:
    NONE = 2
    DIALOG = 0
    BACKGROUND = 1

    mode = 2
    progressBar = None
    override = False
    
    def __init__(self,progressOverride):
        self.override = progressOverride
        
        #check if we should use the progress bar
        if(int(utils.getSetting('progress_mode')) != 2):
            #check if background or normal
            if(int(utils.getSetting('progress_mode')) == 0 and not self.override):
                self.mode = self.DIALOG
                self.progressBar = xbmcgui.DialogProgress()
            else:
                self.mode = self.BACKGROUND
                self.progressBar = xbmcgui.DialogProgressBG()

    def create(self,heading,message):
        if(self.mode != self.NONE):
            self.progressBar.create(heading,message)

    def updateProgress(self,percent,message=None):
        
        #update the progress bar
        if(self.mode != self.NONE):
            if(message != None):
                #need different calls for dialog and background bars
                if(self.mode == self.DIALOG):
                    self.progressBar.update(percent,message)
                else:
                    self.progressBar.update(percent,message=message)
            else:
                self.progressBar.update(percent)

    def checkCancel(self):
        result = False

        if(self.mode == self.DIALOG):
            result = self.progressBar.iscanceled()

        return result

    def close(self):
        if(self.mode != self.NONE):
            self.progressBar.close()
