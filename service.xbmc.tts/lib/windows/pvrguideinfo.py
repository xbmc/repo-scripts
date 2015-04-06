# -*- coding: utf-8 -*-
from base import WindowReaderBase

class PVRGuideInfoReader(WindowReaderBase):
    ID = 'pvrguideinfo'

    def getWindowTexts(self): return self.getWindowExtraTexts()