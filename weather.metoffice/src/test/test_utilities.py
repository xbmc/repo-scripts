from datetime import datetime
from mock import Mock
from xbmctestcase import XBMCTestCase

class TestUtilities(XBMCTestCase):

    def setUp(self):
        super(TestUtilities, self).setUp()
        from metoffice import constants
        self.constants = constants
        from metoffice import utilities
        self.utilities = utilities

    def test_strptime(self):
        date = '23:06 Mon 4 Jan 2013'
        fmt = '%H:%M %a %d %b %Y'
        self.assertEqual(datetime.strptime(date, fmt), self.utilities.strptime(date,fmt))
        
    def test_log(self):
        msg = "Log message"
        self.utilities.log(msg)
        self.xbmc.log.assert_called_with('weather.metoffice: {0}'.format(msg), self.xbmc.LOGNOTICE)

    def test_xbmcbusy(self):
        mock_func = Mock()
        mock_func.__name__ = "Mock"
        self.xbmcgui.getCurrentWindowId = Mock(return_value=self.constants.WEATHER_WINDOW_ID)
        decorated_func = self.utilities.xbmcbusy(mock_func)
        decorated_func(1,2,3)
        self.assertEqual(2, len(self.xbmc.executebuiltin.call_args_list))
        self.assertEqual(self.xbmc.executebuiltin.call_args_list[0], (("ActivateWindow(busydialog)",),))
        self.assertEqual(self.xbmc.executebuiltin.call_args_list[1], (("Dialog.Close(busydialog)",),))
        mock_func.assert_called_with(1,2,3)

    def test_panelbusy(self):
        mock_func = Mock()
        mock_func.__name__ = "Mock"
        rightbusy = self.utilities.panelbusy("RightPanel")
        decorated_func = rightbusy(mock_func)
        decorated_func(1,2,3)
        self.xbmcgui.Window.return_value.setProperty.assert_called_once_with('RightPanel.IsBusy', 'true')
        self.xbmcgui.Window.return_value.clearProperty.assert_called_once_with('RightPanel.IsBusy')
        mock_func.assert_called_with(1,2,3)

    #Have to write a stubby because lambdas contain explressions not statements
    def lambda_raise(self):
        raise IOError('An IOError occurred')

    def test_failgracefully(self):
        message = ('Oh no', 'It all went wrong')
        mock_func = Mock(side_effect = IOError(*message))
        mock_func.__name__ = "Mock"
        self.xbmcgui.getCurrentWindowId = Mock(return_value=self.constants.WEATHER_WINDOW_ID)
        decorated_func = self.utilities.failgracefully(mock_func)
        decorated_func(1,2,3)
        mock_func.assert_called_once_with(1,2,3)
        self.assertTrue(self.xbmc.log.called)
        self.assertTrue(self.xbmcgui.Dialog.return_value.ok.called)
        self.xbmcgui.Dialog.return_value.ok.assert_called_once_with(message[0].title(), message[1])

        #Test when exception called with only one arg
        self.xbmcgui.Dialog.return_value.ok.reset_mock()
        message = ('Oh no',)
        mock_func.side_effect = IOError(*message)
        decorated_func(1,2,3)
        self.xbmcgui.Dialog.return_value.ok.assert_called_once_with(message[0].title(), 'See log file for details')

        #Test when exception called with no args
        self.xbmcgui.Dialog.return_value.ok.reset_mock()
        mock_func.side_effect = IOError()
        decorated_func(1,2,3)
        self.xbmcgui.Dialog.return_value.ok.assert_called_once_with('Error', 'See log file for details')

    def test_minutes_as_time(self):
        self.assertEqual("03:00", self.utilities.minutes_as_time(180))

    def test_localise_temperature(self):
        self.utilities.TEMPERATUREUNITS = 'C'
        self.assertEqual('0', self.utilities.localised_temperature('0'))
        self.assertEqual('-20', self.utilities.localised_temperature('-20'))
        self.assertEqual('20', self.utilities.localised_temperature('20'))
        self.utilities.TEMPERATUREUNITS = 'F'
        self.assertEqual('32', self.utilities.localised_temperature('0'))
        self.assertEqual('-4', self.utilities.localised_temperature('-20'))
        self.assertEqual('68', self.utilities.localised_temperature('20'))
        self.assertEqual('', self.utilities.localised_temperature(''))

    def test_rownd(self):
        self.assertEqual('11', self.utilities.rownd('10.7'))
        self.assertEqual('10', self.utilities.rownd('10.1'))
        self.assertEqual('11', self.utilities.rownd('10.5'))
        self.assertEqual('', self.utilities.rownd(''))

    def test_gettext(self):
        trans = "Nire aerolabangailua aingirez beteta dago"
        known_string = "Observation Location"
        unknown_string = "Observation Position"
        self.utilities.log = Mock()
        self.utilities.ADDON = Mock()
        self.utilities.ADDON.getLocalizedString = Mock(return_value=trans)
        self.utilities.xbmc.LOGWARNING = 3

        #successful translation
        result = self.utilities.gettext(known_string)
        self.utilities.ADDON.getLocalizedString.assert_called
        self.assertEqual(trans, result)

        #KeyError
        result = self.utilities.gettext(unknown_string)
        self.utilities.ADDON.getLocalizedString.assert_called
        self.utilities.log.assert_called
        self.assertEqual(unknown_string, result)

        #TranslationError
        self.utilities.ADDON.getLocalizedString = Mock(return_value='')
        result = self.utilities.gettext(known_string)
        self.utilities.ADDON.getLocalizedString.assert_called
        self.assertEqual(known_string, result)