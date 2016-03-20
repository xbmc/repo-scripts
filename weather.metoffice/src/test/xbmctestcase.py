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

        self.info_labels = {'System.TemperatureUnits' : 'C',
                            'System.BuildVersion' : '16.0 Git:12345678-90a1234'}

        self.xbmc.getInfoLabel.side_effect = self.mock_getInfoLabel

    def mock_getInfoLabel(self, key):
        return self.info_labels[key]

    def tearDown(self):
        self.module_patcher.stop()
        self.addon_patcher.stop()
        self.translate_patcher.stop()
