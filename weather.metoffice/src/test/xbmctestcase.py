import unittest
from mock import patch, Mock

class XBMCTestCase(unittest.TestCase):    
    def setUp(self):
        #Mock up any calls to modules that cannot be imported
        self.xbmc = Mock()
        self.xbmcgui = Mock()
        self.xbmcaddon = Mock()

        modules = {
            'xbmc' : self.xbmc,
            'xbmcgui': self.xbmcgui,
            'xbmcaddon': self.xbmcaddon
            }
        self.module_patcher = patch.dict('sys.modules', modules) #@UndefinedVariable
        self.addon_patcher = patch('xbmcaddon.Addon')
        self.translate_patcher = patch('xbmc.translatePath')
        self.module_patcher.start()
        self.addon_patcher.start()
        self.translate_patcher.start()

    def tearDown(self):
        self.module_patcher.stop()
        self.addon_patcher.stop()
        self.translate_patcher.stop()
