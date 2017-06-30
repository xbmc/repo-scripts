import xml.dom.minidom
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
    jobs = None
    
    def __init__(self):
        self.jobs = []
        
        #try and read in the custom file
        self._readFile()
        
    def getJobs(self):
        return self.jobs
    
    def _readFile(self):
        
        if(xbmcvfs.exists(xbmc.translatePath(utils.data_dir() + "custom_paths.xml"))):
            
            xmlFile = xml.dom.minidom.parse(xbmc.translatePath(utils.data_dir() + "custom_paths.xml"));
            
            #video paths
            if(len(xmlFile.getElementsByTagName("video")) > 0):
                vNode = xmlFile.getElementsByTagName("video")[0]
                
                for aNode in vNode.getElementsByTagName("path"):
                    self.jobs.append(self._createSchedule(aNode, "video"))
                    
            #music paths
            if(len(xmlFile.getElementsByTagName("music")) > 0):
                mNode = xmlFile.getElementsByTagName("music")[0]
                
                for aNode in mNode.getElementsByTagName("path"):
                    self.jobs.append(self._createSchedule(aNode, "music"))
             
            utils.log("Found " + str(len(self.jobs)) + " custom paths",xbmc.LOGDEBUG)
                   
        else:
            utils.log("No custom file, skipping")
            
    def _createSchedule(self,aNode,dbType):
        
        aSchedule = CronSchedule()
        aSchedule.name = aNode.getAttribute("name")
        aSchedule.command = 'UpdateLibrary(' + dbType + ',' + aNode.firstChild.data + ')'
        aSchedule.expression = aNode.getAttribute("cron")
        
        return aSchedule
            