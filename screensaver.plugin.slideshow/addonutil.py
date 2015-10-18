# -*- coding: utf-8 -*-
import json, os, re
import xbmc

BASE = '{{ "jsonrpc": "2.0", "id": 1, "method": "Addons.GetAddonDetails", "params": {{"addonid":"{addonid}","properties": ["name","version","dependencies"]}}}}'
ADDONS_PATH = os.path.join(xbmc.translatePath('special://home').decode('utf-8'),'addons')

def getAddonDetails(addonid):
    cmd = BASE.format(addonid=addonid)
    data = json.loads(xbmc.executeJSONRPC(cmd))
    if not u'result' in data: return None
    details = data[u'result'][u'addon']
    return details

def getDependencies(details):
    deps = []
    _getDependencies(details,deps)
    return deps

def _getDependencies(details,deps):
    for d in details['dependencies']:
        addonid = d['addonid']
        if addonid.startswith('xbmc.python'): continue
        dt = getAddonDetails(addonid)
        if not dt:
            if not addonid in deps: deps.append(addonid)
            _getXMLDependencies(addonid,deps)
            continue
        else:
            if _isModuleXML(addonid):
                if not addonid in deps: deps.append(addonid)
                _getDependencies(dt,deps)

def _getXMLDependencies(addonid,deps):
    path = os.path.join(ADDONS_PATH,addonid,'addon.xml')
    if not os.path.exists(path):
        print 'ERROR: Missing addon.xml for {0}'.format(addonid)
        return False
    with open(path) as f:
        data = f.read()
    for depline in re.findall('(?s)<import [^>]+?>',data):
        try:
            depid = re.search('addon="([^"]+?)"',depline).group(1)
        except IndexError:
            continue
        if depid.startswith('xbmc.python'): continue
        if _isModuleXML(depid):
            if not depid in deps: deps.append(depid)
            _getXMLDependencies(depid,deps)

def _isModuleXML(addonid):
    path = os.path.join(ADDONS_PATH,addonid,'addon.xml')
    if not os.path.exists(path):
        print 'ERROR: Missing addon.xml for {0}'.format(addonid)
        return False
    with open(path) as f:
        return 'point="xbmc.python.module"' in f.read()
    return False

def getModuleLib(addonid):
    path = os.path.join(ADDONS_PATH,addonid,'addon.xml')
    if not os.path.exists(path):
        print 'ERROR: Missing addon.xml for {0}'.format(addonid)
        return
    with open(path) as f:
        data = f.read()
    extension = re.search('<(?s)extension [^>]*?point="xbmc.python.module"[^>]*?/>',data)
    if not extension: return None
    try:
        subPath = re.search('library="([^"]+?)"',extension.group(0)).group(1)
        return os.path.join(ADDONS_PATH,addonid,subPath)
    except IndexError:
        pass
    return None

def getAddonDependencies(addonid):
    details = getAddonDetails(addonid)
    return getDependencies(details)

def getAddonDependencyPaths(addonid):
    paths = []
    for depid in getAddonDependencies(addonid):
        path = getModuleLib(depid)
        if path: paths.append(path)
    return paths

#import xbmcgui, xbmcaddon
#import TextToSpeech
#
#
#class TestWindow(xbmcgui.WindowXML):
#	def onInit(self):
#		self.active = True
#		self.getControl(120).addItem(xbmcgui.ListItem('Click to test.'))
#		self.setFocusId(120)
#
#	def onClick(self,controlID):
#		print controlID
#		TextToSpeech.sayText(u'(""This is \'{}a ()test"")',interrupt=True)
#
#w = TestWindow('script-ruuk-testing.xml',xbmcaddon.Addon().getAddonInfo('path'),'default')
#w.doModal()
#del w

