import os
import shutil
from xbmctestcase import XBMCTestCase

from mock import Mock, patch

TEST_FOLDER = os.path.dirname(__file__)
RESULTS_FOLDER = os.path.join(TEST_FOLDER, 'results')
DATA_FOLDER = os.path.join(TEST_FOLDER, 'data')
FORECASTSITELIST = os.path.join(DATA_FOLDER, 'forecastsitelist.json')
REGIONALSITELIST = os.path.join(DATA_FOLDER, 'regionalsitelist.json')
GEOIP = os.path.join(DATA_FOLDER, 'ip-api.json')

class TestSetLocation(XBMCTestCase):    
    def setUp(self):
        super(TestSetLocation, self).setUp()
        #create a disposable area for testing
        try:
            os.mkdir(RESULTS_FOLDER)
        except OSError:
            pass

        self.settings = {'ApiKey' : '12345',
                         'GeoLocation' : 'true',
                         'GeoIPProvider' : '0',
                         'ForecastLocation' : 'CAMBRIDGE NIAB',
                         'ForecastLocationID' : '99123',
                         'ForecastLocationLatitude' : '52.245',
                         'ForecastLocationLongitude' : '0.103',
                         'ObservationLocation' : 'BEDFORD',
                         'ObservationLocationID' : '3560',
                         'RegionalLocation' : 'Wales',
                         'RegionalLocationID' : '516',
                         }

        self.xbmc.translatePath.return_value = RESULTS_FOLDER
        addon = self.xbmcaddon.Addon.return_value
        addon.getSetting.side_effect = self.mock_getSetting
        addon.setSetting.side_effect = self.mock_setSetting

        from metoffice import constants
        self.constants = constants

    def mock_getSetting(self, key):
        return self.settings[key]

    def mock_setSetting(self, key, value):
        self.settings[key] = value

    def mock_get(self, url, callback):
        if url == self.constants.FORECAST_SITELIST_URL:
            return FORECASTSITELIST
        elif url == self.constants.REGIONAL_SITELIST_URL:
            return REGIONALSITELIST
        elif url == self.constants.GEOIP_PROVIDER['url']:
            return GEOIP
        else:
            return None

    @patch('metoffice.utilities.failgracefully')
    def test_noapikey(self, mock_failgracefully):
        mock_failgracefully.side_effect = lambda f: f
        from metoffice import setlocation
        setlocation.API_KEY = ''
        setlocation._ = lambda x : x
        with self.assertRaises(Exception) as cm:
            setlocation.main('ForecastLocation')
        self.assertEqual(('No API Key.', 'Enter your Met Office API Key under settings.',), cm.exception.args)

    @patch('metoffice.utilities.xbmcbusy')
    @patch('metoffice.urlcache.URLCache')
    def test_getsitelist(self, mock_cache, mock_xbmcbusy):
        mock_cache.return_value.__enter__.return_value.get = Mock(side_effect=self.mock_get)
        mock_xbmcbusy.side_effect = lambda f: f
        from metoffice import setlocation

        #Get Regional sitelist
        result = setlocation.getsitelist('RegionalLocation', 'Northeast England')
        expected = [{'display': 'Northeast England', u'id': u'508', u'name': 'Northeast England'}]
        self.assertEqual(expected, result)

        #Get Forecast sitelist
        result = setlocation.getsitelist('ForecastLocation', 'Cairnwell')
        expected = [{'distance': 640,
                     u'elevation': u'933.0',
                     u'name': u'Cairnwell',
                     u'region': u'ta',
                     u'longitude': u'-3.42',
                     'display': 'Cairnwell (640km)',
                     u'nationalPark': u'Cairngorms National Park',
                     u'latitude': u'56.879',
                     u'unitaryAuthArea': u'Perth and Kinross',
                     u'id': u'3072'}]
        self.assertEqual(expected, result)

        #Same request for forecast location, but with geolocation off
        setlocation.GEOLOCATION = 'false'
        result = setlocation.getsitelist('ForecastLocation', 'Cairnwell')
        expected = [{u'elevation': u'933.0',
                     u'name': u'Cairnwell',
                     u'region': u'ta',
                     u'longitude': u'-3.42',
                     'display': u'Cairnwell',
                     u'nationalPark': u'Cairngorms National Park',
                     u'latitude': u'56.879',
                     u'unitaryAuthArea': u'Perth and Kinross',
                     u'id': u'3072'}]
        self.assertEqual(expected, result)

    @patch('metoffice.utilities.failgracefully')
    @patch('metoffice.urlcache.URLCache')
    def test_main(self, mock_cache, mock_failgracefully):
        #allow main to use getsitelist
        #Pontpandy shouldn't be found, and a message should be displayed saying so
        mock_cache.return_value.__enter__.return_value.get = Mock(side_effect=self.mock_get)
        mock_failgracefully.side_effect = lambda f: f
        self.xbmc.Keyboard.return_value.getText = Mock(return_value='Pontypandy')
        self.xbmc.Keyboard.return_value.isConfirmed = Mock(return_value=True)
        from metoffice import setlocation
        setlocation.main('ForecastLocation')
        self.assertTrue(self.xbmcgui.Dialog.return_value.ok.called)

        #Rosehearty Samos should be found given search text 'hearty'
        self.xbmc.Keyboard.return_value.getText = Mock(return_value='hearty')
        self.xbmcgui.Dialog.return_value.select = Mock(return_value = 0)
        setlocation.main('ForecastLocation')
        self.assertTrue(self.xbmcgui.Dialog.return_value.select.called)
        expected = [(('ForecastLocation', 'Rosehearty Samos'),),
                   (('ForecastLocationID', '3094'),),
                   (('ForecastLocationLatitude', '57.698'),),
                   (('ForecastLocationLongitude', '-2.121'),)]
        self.assertEqual(expected, self.xbmcaddon.Addon.return_value.setSetting.call_args_list)

    def tearDown(self):
        super(TestSetLocation, self).tearDown()
        shutil.rmtree(RESULTS_FOLDER)