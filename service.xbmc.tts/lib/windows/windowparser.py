# -*- coding: utf-8 -*-
import xbmc, os, re
import xml.dom.minidom as minidom
from lib import xpath

def currentWindowXMLFile():
    base = xbmc.getInfoLabel('Window.Property(xmlfile)')
    if os.path.exists(base): return base
    path = getXBMCSkinPath(base)
    if os.path.exists(path): return path
    return None

def currentWindowIsAddon():
    path = xbmc.getInfoLabel('Window.Property(xmlfile)')
    if not path: return None
    return os.path.exists(path)

def getXBMCSkinPath(fname):
    for res in ('720p','1080i'):
        skinpath = os.path.join(xbmc.translatePath('special://skin'),res)
        if os.path.exists(skinpath): break
    else:
        aspect = xbmc.getInfoLabel('Skin.AspectRatio')
        addonXMLPath = os.path.join(xbmc.translatePath('special://skin'),'addon.xml')
        skinpath = ''
        if os.path.exists(addonXMLPath):
            with open(addonXMLPath,'r') as f:
                lines = f.readlines()
            for l in lines:
                if 'aspect="{0}"'.format(aspect) in l:
                    folder = l.split('folder="',1)[-1].split('"',1)[0]
                    skinpath = os.path.join(xbmc.translatePath('special://skin'),folder)
    path = os.path.join(skinpath,fname)
    if os.path.exists(path): return path
    path = os.path.join(skinpath, fname.lower())
    if os.path.exists(path): return path
    return ''

tagRE = re.compile(r'\[/?(?:B|I|COLOR|UPPERCASE|LOWERCASE)[^\]]*\](?i)')
varRE = re.compile(r'\$VAR\[([^\]]*)\]')
localizeRE = re.compile(r'\$LOCALIZE\[([^\]]*)\]')
addonRE = re.compile(r'\$ADDON\[[\w+\.]+ (\d+)\]')
infoLableRE = re.compile(r'\$INFO\[([^\]]*)\]')

def getInfoLabel(info,container):
    if container:
        info = info.replace('ListItem.','Container({0}).ListItem.'.format(container))
    return xbmc.getInfoLabel(info).decode('utf-8')

def nodeParents(dom,node):
    parents = []
    parent = xpath.findnode('..',node)
    while parent and not isinstance(parent,minidom.Document):
        parents.append(parent)
        parent = xpath.findnode('..',parent)
    return parents

def extractInfos(text,container):
    pos = 0
    while pos > -1:
        pos = text.find('$INFO[')
        if pos < 0: break
        lbracket = pos + 6
        i = lbracket
        depth = 1
        for c in text[pos + 6:]:
            if c == '[':
                depth+=1
            elif c == ']':
                depth-=1
            if depth < 1: break
            i+=1
        middle = text[lbracket:i]

        parts = middle.split(',')
        if len(parts) > 2:
            info = getInfoLabel(parts[0],container)
            if info:
                middle = parts[1] + info + parts[2]
            else:
                middle = ''
        elif len(parts) > 1:
            info = getInfoLabel(parts[0],container)
            if info:
                middle = parts[1] + info
            else:
                middle = ''
        else:
            middle = getInfoLabel(middle,container)

        if middle: middle += '... '
        text = text[:pos] + middle + text[i+1:]
    return text.strip(' .')


class WindowParser:
    def __init__(self,xml_path):
        self.xml = minidom.parse(xml_path)
        self.currentControl = None
        self.includes = None
        if not currentWindowIsAddon():
            self.processIncludes()
#            import codecs
#            with codecs.open(os.path.join(getXBMCSkinPath(''),'TESTCurrent.xml'),'w','utf-8') as f: f.write(self.soup.prettify())

    def processIncludes(self):
        self.includes = Includes()
        for i in xpath.find('//include',self.xml):
            conditionAttr = i.attributes.get('condition')
            if conditionAttr and not xbmc.getCondVisibility(conditionAttr.value):
                xpath.findnode('..',i).removeChild(i)
                continue
            matchingInclude = self.includes.getInclude(i.childNodes[0].data)
            if not matchingInclude:
                #print 'INCLUDE NOT FOUND: %s' % i.string
                continue
            #print 'INCLUDE FOUND: %s' % i.string
            new = matchingInclude.cloneNode(True)
            xpath.findnode('..',i).replaceChild(new,i)

    def addonReplacer(self,m):
        return xbmc.getInfoLabel(m.group(0)).decode('utf-8')

    def variableReplace(self,m):
        return self.includes.getVariable(m.group(1))

    def localizeReplacer(self,m):
        return xbmc.getLocalizedString(int(m.group(1)))

    def parseFormatting(self,text):
        text = varRE.sub(self.variableReplace,text)
        text = localizeRE.sub(self.localizeReplacer,text)
        text = addonRE.sub(self.addonReplacer,text)
        text = extractInfos(text,self.currentControl)
        text = tagRE.sub('',text).replace('[CR]','... ').strip(' .')
        #text = infoLableRE.sub(self.infoReplacer,text)
        return text

    def getControl(self,controlID):
        return xpath.findnode("//control[attribute::id='{0}']".format(controlID),self.xml)

    def getLabelText(self,label):
        l = xpath.findnode('label',label)
        text = None
        if label.attributes.get('id'):
            #Try getting programatically set label first.
            text = xbmc.getInfoLabel('Control.GetLabel({0})'.format(label.attributes.get('id').value)).decode('utf-8')
        if not text or text == '-':
            text = None
            if l and l.childNodes: text = l.childNodes[0].data
            if text:
                if text.isdigit(): text = '$LOCALIZE[{0}]'.format(text)
            else:
                i = xpath.findnode('info',label)
                if i and i.childNodes:
                    text = i.childNodes[0].data
                    if text.isdigit():
                        text = '$LOCALIZE[{0}]'.format(text)
                    else:
                        text = '$INFO[{0}]'.format(text)
        if not text: return None
        return tagRE.sub('',text).replace('[CR]','... ').strip(' .')

    def processTextList(self,text_list):
        texts = []
        check = []
        for t in text_list:
            parsed = self.parseFormatting(t)
            if parsed and not t in check:
                texts.append(parsed)
                check.append(t)
        return texts

    def getListItemTexts(self,controlID):
        self.currentControl = controlID
        try:
            clist = self.getControl(controlID)
            if not clist: return None
            fl = xpath.findnode("focusedlayout",clist)
            if not fl: return None
            lt = xpath.find("//control[attribute::type='label' or attribute::type='fadelabel' or attribute::type='textbox']",fl)
            texts = []
            for l in lt:
                if not self.controlIsVisibleGlobally(l): continue
                text = self.getLabelText(l)
                if text and not text in texts: texts.append(text)
            return self.processTextList(texts)
        finally:
            self.currentControl = None

    def getWindowTexts(self):
        lt = xpath.find("//control[attribute::type='label' or attribute::type='fadelabel' or attribute::type='textbox']",self.xml)
        texts = []
        for l in lt:
            if not self.controlIsVisible(l): continue
            for p in nodeParents(self.xml,l):
                if not self.controlIsVisible(p): break
                typeAttr = p.attributes.get('type')
                if typeAttr and typeAttr.value in ('list','fixedlist','wraplist','panel'): break
            else:
                text = self.getLabelText(l)
                if text and not text in texts: texts.append(text)
        return self.processTextList(texts)

    def controlGlobalPosition(self,control):
        x, y = self.controlPosition(control)
        for p in nodeParents(self.xml,control):
            if p.get('type') == 'group':
                px,py = self.controlPosition(p)
                x+=px
                y+=py
        return x, y

    def controlPosition(self,control):
        posx = control.find('posx')
        x = posx and posx.string or '0'
        if 'r' in x:
            x = int(x.strip('r')) * -1
        else:
            x = int(x)
        posy = control.find('posy')
        y = int(posy and posy.string or '0')
        return x,y

    def controlIsVisibleGlobally(self,control):
        for p in nodeParents(self.xml,control):
            if not self.controlIsVisible(p): return False
        return self.controlIsVisible(control)

    def controlIsVisible(self,control):
        visible = xpath.findnode('visible',control)
        if not visible: return True
        if not visible.childNodes: return True
        condition = visible.childNodes[0].data
        if self.currentControl:
            condition = condition.replace('ListItem.Property','Container({0}).ListItem.Property'.format(self.currentControl))
        if not xbmc.getCondVisibility(condition):
            return False
        else:
            return True

class Includes:
    def __init__(self):
        path = getXBMCSkinPath('Includes.xml')
        self.xml = minidom.parse(path)
        self._includesFilesLoaded = False
        self.includesMap = {}

    def loadIncludesFiles(self):
        if self._includesFilesLoaded: return
        basePath = getXBMCSkinPath('')
        for i in xpath.find('//include',xpath.findnode('//includes',self.xml)):
            fileAttr = i.attributes.get('file')
            if fileAttr:
                xmlName = xbmc.validatePath(fileAttr.value)
                p = os.path.join(basePath,xmlName)
                if not os.path.exists(p):
                    continue
                xml = minidom.parse(p)
                includes = xpath.findnode('includes',xml)
                xpath.findnode('..',i).replaceChild(includes,i)
                for sub_i in xpath.find('.//include',includes):
                    nameAttr = sub_i.attributes.get('name')
                    if nameAttr:
                        self.includesMap[nameAttr.value] = sub_i
            else:
                nameAttr = i.attributes.get('name')
                if nameAttr: self.includesMap[nameAttr.value] = i.cloneNode(True)
        self._includesFilesLoaded = True
#        import codecs
#        with codecs.open(os.path.join(getXBMCSkinPath(''),'Includes_Processed.xml'),'w','utf-8') as f: f.write(self.soup.prettify())

    def getInclude(self,name):
        self.loadIncludesFiles()
        return self.includesMap.get(name)
        #return self.soup.find('includes').find('include',{'name':name})

    def getVariable(self,name):
        var = xpath.findnode(".//variable[attribute::name='{0}']".format(name),xpath.findnode('includes',self.xml))
        if not var: return ''
        for val in xpath.find('.//value',var):
            conditionAttr = val.attributes.get('condition')
            if not conditionAttr:
                return val.childNodes[0].data or ''
            else:
                if xbmc.getCondVisibility(conditionAttr.value):
                    #print condition
                    #print repr(val.string)
                    return val.childNodes[0].data or ''
        return ''

def getWindowParser():
    path = currentWindowXMLFile()
    if not path: return
    return WindowParser(path)