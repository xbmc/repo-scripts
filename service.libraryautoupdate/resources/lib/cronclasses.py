import xml.dom.minidom
import json
import utils as utils
import xbmcvfs
import xbmc

class CronSchedule:
    expression = ''
    name = 'library'
    timer_type = 'xbmc'
    command = 'UpdateLibrary(video)'
    next_run = 0
    on_delay = False  #used to defer processing until after player finishes

    def cleanLibrarySchedule(self,selectedIndex):
        if(selectedIndex == 1):
            #once per day
            return "* * *"
        elif (selectedIndex == 2):
            #once per week
            return "* * 0"
        else:
            #once per month
            return "1 * *"

class CustomPathFile:
    jsonFile = xbmc.translatePath(utils.data_dir() + "custom_paths.json")
    paths = None
    
    def __init__(self):
        self.paths = []
        
        #try and read in the custom file
        self._readFile()

    def getSchedules(self):
        schedules = []

        #create schedules from the path information
        for aPath in self.paths:
            schedules.append(self._createSchedule(aPath))

        return schedules

    def addPath(self,path):
        self.paths.append(path)

        #save the file
        self._writeFile()

    def deletePath(self,index):
        del self.paths[index]

        #save the file
        self._writeFile()
    
    def getPaths(self):
        return self.paths

    def _writeFile(self):
        #create the custom file
        aFile = xbmcvfs.File(self.jsonFile,'w')
        aFile.write(json.dumps(self.paths))
        aFile.close()
    
    def _readFile(self):
        
        if(xbmcvfs.exists(self.jsonFile)):

            #read in the custom file
            aFile = xbmcvfs.File(self.jsonFile)

            #load paths in the format {path:path,expression:expression}
            self.paths = json.loads(aFile.read())
            aFile.close()
        else:
            #write a blank file
            self._writeFile()
        
    
    def _createSchedule(self,aPath):
        
        aSchedule = CronSchedule()
        aSchedule.name = aPath['path']
        aSchedule.command = 'UpdateLibrary(video,' + aPath['path'] + ')'
        aSchedule.expression = aPath['expression']
        
        return aSchedule
            
