# -*- coding: utf-8 -*-
# License: GPL v.3 https://www.gnu.org/copyleft/gpl.html

from __future__ import unicode_literals

import time
import calendar
import requests

import xml.etree.cElementTree as etree
try:
    etree.fromstring('<?xml version="1.0"?><foo><bar/></foo>')
except TypeError:
    import xml.etree.ElementTree as etree

__all__ = ['GismeteoError', 'GismeteoClient']


class GismeteoError(Exception):

    pass


class GismeteoClient(object):

    _base_url = 'https://services.gismeteo.net/inform-service/inf_chrome'

    def __init__(self, lang='en'):

        self._lang = lang

        self._client = requests.Session()

    def __del__(self):

        self._client.close()

    @staticmethod
    def _extract_xml(r):

        try:
            x = etree.fromstring(r.content)
        except ValueError as e:
            raise GismeteoError(e)

        return x

    def _get(self, url, params=None, *args, **kwargs):
        params = params or {}
        params['lang'] = self._lang

        r = self._client.get(url, params=params, *args, **kwargs)
        return r

    @staticmethod
    def _get_locations_list(root):

        result = []
        for item in root:

            location = {'name' : item.attrib['n'],
                        'id': item.attrib['id'],
                        'country': item.attrib['country_name'],
                        'district': item.attrib.get('district_name', ''),
                        'lat': item.attrib['lat'],
                        'lng': item.attrib['lng'],
                        'kind': item.attrib['kind'],
                        }

            result.append(location)

        return result

    @staticmethod
    def _get_date(source, tzone):

        if isinstance(source, float):
            local_stamp = source
            local_date = time.strftime('%Y-%m-%dT%H:%M:%S', time.gmtime(local_stamp))
        else:
            local_date = source if len(source) > 10 else source + 'T00:00:00'
            local_stamp = 0

            while local_stamp == 0:
                local_stamp = calendar.timegm(time.strptime(local_date, '%Y-%m-%dT%H:%M:%S'))

        utc_stamp = local_stamp - tzone * 60
        result = {'local': local_date,
                  'utc': time.strftime('%Y-%m-%dT%H:%M:%S', time.gmtime(utc_stamp)),
                  'unix': utc_stamp,
                  'offset': tzone}
        return result

    def _get_forecast_info(self, root):

        xml_location = root[0]

        return {'name' : xml_location.attrib['name'],
                'id': xml_location.attrib['id'],
                'kind': xml_location.attrib['kind'],
                'country': xml_location.attrib['country_name'],
                'district': xml_location.attrib.get('district_name', ''),
                'lat': xml_location.attrib['lat'],
                'lng': xml_location.attrib['lng'],
                'cur_time': self._get_date(xml_location.attrib['cur_time'], self._get_int(xml_location.attrib['tzone'])),
                'current': self._get_fact_forecast(xml_location),
                'days': self._get_days_forecast(xml_location),
                }

    def _get_item_forecast(self, xml_item, tzone):

        result = {}

        xml_values = xml_item[0]

        result['date'] = self._get_date(xml_item.attrib['valid'], tzone)
        if xml_item.attrib.get('sunrise') is not None:
            result['sunrise'] = self._get_date(self._get_float(xml_item.attrib['sunrise']), tzone)
        if xml_item.attrib.get('sunset') is not None:
            result['sunset'] = self._get_date(self._get_float(xml_item.attrib['sunset']), tzone)
        result['temperature'] = {'air': self._get_int(xml_values.attrib['t']),
                                 'comfort': self._get_int(xml_values.attrib['hi']),
                                 }
        if xml_values.attrib.get('water_t') is not None:
            result['temperature']['water'] = self._get_int(xml_values.attrib['water_t']),
        result['description'] = xml_values.attrib['descr']
        result['humidity'] = self._get_int(xml_values.attrib['hum'])
        result['pressure'] = self._get_int(xml_values.attrib['p'])
        result['cloudiness'] = xml_values.attrib['cl']
        result['storm'] = (xml_values.attrib['ts'] == '1')
        result['precipitation'] = {'type': xml_values.attrib['pt'],
                                   'amount': xml_values.attrib.get('prflt'),
                                   'intensity': xml_values.attrib['pr'],
                                   }
        if xml_values.attrib.get('ph') is not None \
          and xml_values.attrib['ph']:
            result['phenomenon'] = self._get_int(xml_values.attrib['ph'])
        if xml_item.attrib.get('tod') is not None:
            result['tod'] = self._get_int(xml_item.attrib['tod'])
        result['icon'] = xml_values.attrib['icon']
        result['gm'] = xml_values.attrib['grade']
        result['wind'] = {'speed': self._get_float(xml_values.attrib['ws']),
                          'direction': xml_values.attrib['wd'],
                          }

        return result

    def _get_fact_forecast(self, xml_location):
        fact = xml_location.find('fact')
        return self._get_item_forecast(fact, self._get_int(xml_location.attrib['tzone']))

    def _get_days_forecast(self, xml_location):
        tzone = self._get_int(xml_location.attrib['tzone'])

        result = []
        for xml_day in xml_location.findall('day'):

            if xml_day.attrib.get('icon') is None:
                continue

            day = {'date': self._get_date(xml_day.attrib['date'], tzone),
                   'sunrise': self._get_date(self._get_float(xml_day.attrib['sunrise']), tzone),
                   'sunset': self._get_date(self._get_float(xml_day.attrib['sunset']), tzone),
                   'temperature': {'min': self._get_int(xml_day.attrib['tmin']),
                                   'max': self._get_int(xml_day.attrib['tmax']),
                                   },
                   'description': xml_day.attrib['descr'],
                   'humidity': {'min': self._get_int(xml_day.attrib['hummin']),
                                'max': self._get_int(xml_day.attrib['hummax']),
                                'avg': self._get_int(xml_day.attrib['hum']),
                                },
                   'pressure': {'min': self._get_int(xml_day.attrib['pmin']),
                                'max': self._get_int(xml_day.attrib['pmax']),
                                'avg': self._get_int(xml_day.attrib['p']),
                                },
                   'cloudiness': xml_day.attrib['cl'],
                   'storm': (xml_day.attrib['ts'] == '1'),
                   'precipitation': {'type': xml_day.attrib['pt'],
                                     'amount': xml_day.attrib['prflt'],
                                     'intensity': xml_day.attrib['pr'],
                                     },
                   'icon': xml_day.attrib['icon'],
                   'gm': xml_day.attrib['grademax'],
                   'wind': {'speed': {'min': self._get_float(xml_day.attrib['wsmin']),
                                      'max': self._get_float(xml_day.attrib['wsmax']),
                                      'avg': self._get_float(xml_day.attrib['ws']),
                                      },
                            'direction': xml_day.attrib['wd'],
                            },
                   }
            if len(xml_day):
                day['hourly'] = self._get_hourly_forecast(xml_day, tzone)

            result.append(day)

        return result

    def _get_hourly_forecast(self, xml_day, tzone):
        result = []
        for xml_forecast in xml_day.findall('forecast'):
            item = self._get_item_forecast(xml_forecast, tzone)
            result.append(item)

        return result

    @staticmethod
    def _get_int(value):
        try:
            return int(value)
        except ValueError:
            return 0

    @staticmethod
    def _get_float(value):
        try:
            return float(value)
        except ValueError:
            return 0.0

    def cities_search(self, keyword):
        url = self._base_url + '/cities/'

        u_params = {'startsWith': keyword,
                    }

        r = self._get(url, params=u_params)
        x = self._extract_xml(r)
        return self._get_locations_list(x)

    def cities_ip(self, count=1):
        url = self._base_url + '/cities/'

        u_params = {'mode': 'ip',
                    'count': count,
                    'nocache': 1,
                    }

        r = self._get(url, params=u_params)
        x = self._extract_xml(r)
        return self._get_locations_list(x)

    def cities_nearby(self, lat, lng, count=5):
        url = self._base_url + '/cities/'

        u_params = {'lat': lat,
                    'lng': lng,
                    'count': count,
                    'nocache': 1,
                    }

        r = self._get(url, params=u_params)
        x = self._extract_xml(r)
        return self._get_locations_list(x)

    def forecast(self, city_id):
        url = self._base_url + '/forecast/'

        u_params = {'city': city_id,
                    }

        r = self._get(url, params=u_params)
        x = self._extract_xml(r)
        return self._get_forecast_info(x)
