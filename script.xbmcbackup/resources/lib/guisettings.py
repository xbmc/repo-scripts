import utils as utils
from xml.dom import minidom
from xml.parsers.expat import ExpatError
import json
import xbmc,xbmcvfs


class GuiSettingsManager:
    settingsFile = None
    doc = None
    settings_allowed = list()
    found_settings = list()
    
    def __init__(self,settingsFile):
        self._readFile(xbmc.translatePath(settingsFile))
    
    def run(self):
        #get a list of all the settings we can manipulate via json
        json_response = json.loads(xbmc.executeJSONRPC('{"jsonrpc":"2.0", "id":1, "method":"Settings.GetSettings","params":{"level":"advanced"}}'))
        
        settings = json_response['result']['settings']
           
        for aSetting in settings:
            self.settings_allowed.append(aSetting['id'])
            
        #parse the existing xml file and get all the settings
        root_nodes = self.__parseNodes(self.doc.documentElement)
        
        for aNode in root_nodes:
            secondary_list = self.__parseNodes(self.doc.getElementsByTagName(aNode.name)[0])
            
            for secondNode in secondary_list:
                #if the node does not have children and is not default
                if(not secondNode.hasChildren and not secondNode.isDefault):
                    
                    if(secondNode.json_name() in self.settings_allowed):
                        self.found_settings.append(secondNode)
                    
        #go through all the found settings and update them
        for aSetting in self.found_settings:
            utils.log("updating: " + aSetting.json_name() + ", value: " + aSetting.value)
            
            #check for boolean and numeric values
            if(aSetting.value.isdigit() or (aSetting.value == 'true' or aSetting.value == 'false')):
                xbmc.executeJSONRPC('{"jsonrpc":"2.0", "id":1, "method":"Settings.SetSettingValue","params":{"setting":"' + aSetting.json_name() + '","value":' + aSetting.value + '}}')
            else:
                xbmc.executeJSONRPC('{"jsonrpc":"2.0", "id":1, "method":"Settings.SetSettingValue","params":{"setting":"' + aSetting.json_name() + '","value":"' + utils.encode(aSetting.value) + '"}}')
                
        #make a copy of the guisettings file to make user based restores easier
        xbmcvfs.copy(self.settingsFile, xbmc.translatePath("special://home/userdata/guisettings.xml.restored"))
            
    def __parseNodes(self,nodeList):
        result = []

        for node in nodeList.childNodes:
            if(node.nodeType == self.doc.ELEMENT_NODE):
                aSetting = SettingNode(node.nodeName)

                #detect if there are any element nodes
                if(len(node.childNodes) > 0):
                    for child_node in node.childNodes:
                        if(child_node.nodeType == self.doc.ELEMENT_NODE):
                            aSetting.hasChildren = True

                if(not aSetting.hasChildren and len(node.childNodes) > 0):
                    aSetting.value = node.firstChild.nodeValue
                    
                    if('default' not in node.attributes.keys()):
                        aSetting.isDefault = False
                        
                aSetting.parent = node.parentNode.nodeName
                
                result.append(aSetting)
        return result
    
    
    def _readFile(self,fileLoc):
        
        if(xbmcvfs.exists(fileLoc)):
            try:
                self.doc = minidom.parse(fileLoc)
                self.settingsFile = fileLoc
            except ExpatError:
                utils.log("Can't read " + fileLoc)
                
class SettingNode:
    name = ''
    value = ''
    hasChildren = False
    isDefault = True
    parent = ''
    
    def __init__(self,name):
        self.name = name
        
    def json_name(self):
        return self.parent + "." + self.name
                
        
