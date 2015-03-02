import sys
from mock import Mock
from test.xbmctestcase import XBMCTestCase

class TestDefault(XBMCTestCase):

    def test_main(self):
        from metoffice import utilities
        utilities.failgracefully = lambda f: f
        from metoffice import default
        
        default.properties = Mock()
        default.urlcache.URLCache = Mock()
        default.ADDON = Mock()
        default.ADDON.getSetting = Mock(return_value='false')
        default._ = lambda x : x

        #Test no API Key Exception raising
        default.API_KEY = ''
        with self.assertRaises(Exception) as cm:
            default.main()
        self.assertEqual(('No API Key.', 'Enter your Met Office API Key under settings.',), cm.exception.args)
        self.assertFalse(default.properties.observation.called)#@UndefinedVariable
        self.assertFalse(default.properties.daily.called)#@UndefinedVariable
        self.assertFalse(default.properties.threehourly.called)#@UndefinedVariable
        self.assertFalse(default.properties.forecastlayer.called)#@UndefinedVariable
        self.assertFalse(default.properties.observationlayer.called)#@UndefinedVariable
        self.assertFalse(default.properties.text.called)#@UndefinedVariable
        default.properties.reset_mock()#@UndefinedVariable

        #Test call with digit
        default.API_KEY = '12345'
        default.CURRENT_VIEW = '' #Implicit request for daily forecast
        sys.argv = ['default.py', '1']
        default.main()
        self.assertTrue(default.properties.observation.called)#@UndefinedVariable
        self.assertTrue(default.properties.daily.called)#@UndefinedVariable
        self.assertFalse(default.properties.threehourly.called)#@UndefinedVariable
        self.assertFalse(default.properties.forecastlayer.called)#@UndefinedVariable
        self.assertFalse(default.properties.observationlayer.called)#@UndefinedVariable
        self.assertFalse(default.properties.text.called)#@UndefinedVariable
        default.properties.reset_mock()#@UndefinedVariable

        default.CURRENT_VIEW = '3hourly'
        sys.argv = ['default.py']
        default.main()
        self.assertFalse(default.properties.observation.called)#@UndefinedVariable
        self.assertFalse(default.properties.daily.called)#@UndefinedVariable
        self.assertTrue(default.properties.threehourly.called)#@UndefinedVariable
        self.assertFalse(default.properties.forecastlayer.called)#@UndefinedVariable
        self.assertFalse(default.properties.observationlayer.called)#@UndefinedVariable
        self.assertFalse(default.properties.text.called)#@UndefinedVariable
        default.properties.reset_mock()#@UndefinedVariable

        default.CURRENT_VIEW = 'forecastmap'
        default.main()
        self.assertFalse(default.properties.observation.called)#@UndefinedVariable
        self.assertFalse(default.properties.daily.called)#@UndefinedVariable
        self.assertFalse(default.properties.threehourly.called)#@UndefinedVariable
        self.assertTrue(default.properties.forecastlayer.called)#@UndefinedVariable
        self.assertFalse(default.properties.observationlayer.called)#@UndefinedVariable
        self.assertFalse(default.properties.text.called)#@UndefinedVariable
        default.properties.reset_mock()#@UndefinedVariable

        default.CURRENT_VIEW = 'observationmap'
        default.main()
        self.assertFalse(default.properties.observation.called)#@UndefinedVariable
        self.assertFalse(default.properties.daily.called)#@UndefinedVariable
        self.assertFalse(default.properties.threehourly.called)#@UndefinedVariable
        self.assertFalse(default.properties.forecastlayer.called)#@UndefinedVariable
        self.assertTrue(default.properties.observationlayer.called)#@UndefinedVariable
        self.assertFalse(default.properties.text.called)#@UndefinedVariable
        default.properties.reset_mock()#@UndefinedVariable

        default.CURRENT_VIEW = 'text'
        default.main()
        self.assertFalse(default.properties.observation.called)#@UndefinedVariable
        self.assertFalse(default.properties.daily.called)#@UndefinedVariable
        self.assertFalse(default.properties.threehourly.called)#@UndefinedVariable
        self.assertFalse(default.properties.forecastlayer.called)#@UndefinedVariable
        self.assertFalse(default.properties.observationlayer.called)#@UndefinedVariable
        self.assertTrue(default.properties.text.called)#@UndefinedVariable
        default.properties.reset_mock()#@UndefinedVariable

        #Test erase cache setting
        default.ADDON.getSetting = Mock(return_value='true')
        default.main()
        self.assertTrue(default.urlcache.URLCache.return_value.erase.called)#@UndefinedVariable
        default.ADDON.setSetting.assert_called_once_with('EraseCache', 'false')#@UndefinedVariable
        