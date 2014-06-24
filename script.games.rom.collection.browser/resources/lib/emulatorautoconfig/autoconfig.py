
import os, sys
import xml.etree.ElementTree as ET

class OperatingSystem:
    name = ''
    platforms = []
    
class DetectionMethod:
    name = ''
    command = ''
    packagename = ''
    
class Platform:
    name = ''
    aliases = []
    emulators = []
        
class Emulator:
    detectionMethods = []
    name = ''
    os = ''
    platform = ''
    isInstalled = False
    installdir = ''
    emuCmd = ''
    emuParams = ''



class EmulatorAutoconfig:
    
    configFile = ''
    tree = None
    
    operatingSystems = []
    
    
    
    def __init__(self, configFile):
        self.configFile = configFile
        
    
    def initXml(self):
        
        if(not os.path.isfile(self.configFile)):
           print 'EmulatorAutoconfig ERROR: File emu_autoconfig.xml does not exist. Place a valid config file here: %s' %self.configFile
           return None
            
        tree = ET.ElementTree().parse(self.configFile)
        if(tree == None):
            print 'EmulatorAutoconfig ERROR: Could not read emu_autoconfig.xml'
            return None
        
        return tree
        
    
    def readXml(self):
        
        self.tree = self.initXml()
        if(self.tree == None):
            return
        
        self.operatingSystems = self.readOperatingSystems(self.tree)
        
        
    def readOperatingSystems(self, tree):
        
        osRows = self.tree.findall('os')
        if(osRows == None):
            print 'EmulatorAutoconfig ERROR: Could not find node os in emu_autoconfig.xml'
            return []
                
        operatingSystems = []
                
        for osRow in osRows:
            operatingSystem = OperatingSystem()
            operatingSystem.name = osRow.attrib.get('name')
            operatingSystem.platforms = self.readPlatforms(osRow)
            operatingSystems.append(operatingSystem)
            
        return operatingSystems
            
            
    def readPlatforms(self, osRow):
        
        platformRows = osRow.findall('platform')
        if(platformRows == None):
            print 'EmulatorAutoconfig ERROR: Could not find node os/platform in emu_autoconfig.xml'
            return []
            
        platforms = []
            
        for platformRow in platformRows:
            platform = Platform()
            platform.name = platformRow.attrib.get('name')
            aliases = []
            aliasRows = platformRow.findall('alias')
            if(aliasRows != None):
                for aliasRow in aliasRows:
                    aliases.append(aliasRow.text)
            platform.aliases = aliases
            platform.emulators = self.readEmulators(platformRow, osRow)
            platforms.append(platform)
            
        return platforms
            
            
    def readEmulators(self, platformRow, osRow):
        
        emulatorRows = platformRow.findall('emulator')
        if(emulatorRows == None):
            print 'EmulatorAutoconfig ERROR: Could not find node os/platform/emulator in emu_autoconfig.xml'
            return []
        
        emulators = []
        
        for emulatorRow in emulatorRows:
            emulator = Emulator()
            emulator.name = emulatorRow.attrib.get('name')
            emulator.os = osRow.attrib.get('name')
            emulator.platform = platformRow.attrib.get('name')
            emulator.emuCmd = self.readTextElement(emulatorRow, 'configuration/emulatorCommand')
            emulator.emuParams = self.readTextElement(emulatorRow, 'configuration/emulatorParams')
            emulator.detectionMethods = self.readDetectionMethods(emulatorRow, osRow)
            
            emulators.append(emulator)
            
        return emulators
                
    
    def readDetectionMethods(self, emulatorRow, osRow):
        
        detectionMethodRows = emulatorRow.findall('detectionMethod')
        if(detectionMethodRows == None):
            print 'EmulatorAutoconfig WARNING: Could not find node os/platform/emulator/detectionMethod in emu_autoconfig.xml'
            return []
        
        globalDMRows = osRow.findall('detectionMethods/detectionMethod')
        if(globalDMRows == None):
            globalDMRows = []
        
        detectionMethods = []
        
        for detectionMethodRow in detectionMethodRows:
            detectionMethod = DetectionMethod()
            detectionMethod.name = detectionMethodRow.attrib.get('name')
            
            if(detectionMethod.name == 'packagename'):
                for globalDMRow in globalDMRows:
                    if(globalDMRow.attrib.get('name') == 'packagename'):
                        detectionMethod.command = self.readTextElement(globalDMRow, 'command')
                        
                detectionMethod.packagename = self.readTextElement(detectionMethodRow, 'packagename')
            
            detectionMethods.append(detectionMethod)
            
        return detectionMethods
                
            
                

    def findEmulators(self, operatingSystemName, platformName, checkInstalledState=False):
        
        print 'EmulatorAutoconfig: findEmulators(). os = %s, platform = %s, checkInstalled = %s' %(operatingSystemName, platformName, str(checkInstalledState))
        
        #read autoconfig.xml file
        if(self.tree == None or len(self.operatingSystems) == 0):
            self.readXml()
        
        osFound = None
        for operatingSystem in self.operatingSystems:
            if(operatingSystem.name == operatingSystemName):
                osFound = operatingSystem
        
        if(osFound == None):
            print 'EmulatorAutoconfig ERROR: Could not find os %s in emu_autoconfig.xml' %operatingSystemName
            return None
            
        platformFound = None
        for platform in osFound.platforms:
            if(platform.name == platformName):
                platformFound = platform
            else:
                if(platform.aliases):
                    for alias in platform.aliases:
                        if(alias == platformName):
                            platformFound = platform 
            
        if(platformFound == None):
            print 'EmulatorAutoconfig ERROR: Could not find platform %s for os %s in emu_autoconfig.xml' %(platformName, operatingSystemName)
            return None
        
        if(checkInstalledState):            
            for emulator in platformFound.emulators:
                emulator.isInstalled = self.isInstalled(emulator)
        
        return platformFound.emulators
    
    
    
    def isInstalled(self, emulator):
        
        print 'EmulatorAutoconfig: isInstalled(). emulator = %s' %emulator.name
        
        for detectionMethod in emulator.detectionMethods:
            print 'EmulatorAutoconfig: detectionMethod.name = ' +detectionMethod.name
            if(detectionMethod.name == 'packagename'):
                try:                    
                    packages = os.popen(detectionMethod.command).readlines()
                    print 'EmulatorAutoconfig: packages = ' +str(packages)
                    for package in packages:
                        print 'EmulatorAutoconfig: package = ' +package
                        print 'EmulatorAutoconfig: detectionMethod.packagename = ' +detectionMethod.packagename
                        if(package.strip() == detectionMethod.packagename.strip()):
                            print 'EmulatorAutoconfig: emulator is installed!'
                            return True
                    
                except Exception, (exc):
                    print 'EmulatorAutoconfig ERROR: error while reading list of packages: %s' %exc
        
        return False
                
    
    
    def readTextElement(self, parent, elementName):
        element = parent.find(elementName)
        if(element != None and element.text != None):
            return element.text
        else:
            return ''
        
            
        