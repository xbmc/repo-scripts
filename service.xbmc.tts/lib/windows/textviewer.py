# -*- coding: utf-8 -*-
import xbmc, time, re, hashlib
from base import WindowReaderBase

class TextViewerReader(WindowReaderBase):
    ID = 'textviewer'

    def init(self):
        self.start = time.time()
        self._last_md5sum = None
        self.doubleChecked = False

    def last(self,new):
        md5sum = new and hashlib.md5(''.join(new)).digest() or None
        if md5sum == self._last_md5sum: return True
        self._last_md5sum = md5sum

    def getViewerTexts(self):
        text = xbmc.getInfoLabel('Control.GetLabel(5)').decode('utf-8') or xbmc.getInfoLabel('Control.GetLabel(2000)').decode('utf-8')
        if text:
            return self.processLines(text.splitlines())
        else:
            return self.getLegacyTextbox()

    def getLegacyTextbox(self):
        folderPath = xbmc.getInfoLabel('Container.FolderPath')
        if folderPath.startswith('addons://'):
            import os, codecs
            changelog = os.path.join(xbmc.getInfoLabel('ListItem.Property(Addon.Path)'),'changelog.txt')
            if not os.path.exists(changelog): return None
            with codecs.open(changelog,'r','utf-8') as f:
                lines = f.readlines()
            return self.processLines(lines)
        return None

    def processLines(self,lines):
        ret = []
        for l in lines:
            if not re.search('\w',l): continue
            ret.append(l.strip())
        return ret

    def getWindowTexts(self):
        texts = self.getViewerTexts()
        if texts:
            self.last(texts)
            return texts
        return None

    def getControlText(self,controlID):
        return (u'',u'')

    def getMonitoredText(self,isSpeaking=False):
        if self.doubleChecked: return None
        if time.time() - self.start > 2:
            self.doubleChecked = True
            texts = self.getViewerTexts()
            if self.last(texts): return None
            return texts
