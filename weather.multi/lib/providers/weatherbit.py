from ..conversions import *

class Weather():
    def __init__():
        pass

    def get_weather(data):
    #daily - standard (weatherbit)
        for count, item in enumerate(data['data']):
            code = str(item['weather']['code'])
            code = code + 'd'
            weathercode = WEATHER_CODES[code]
            set_property('Day%i.Title'              % count, convert_datetime(item['ts'], 'timestamp', 'weekday', 'long'))
            set_property('Day%i.HighTemp'           % count, str(int(round(item['max_temp']))))
            set_property('Day%i.LowTemp'            % count, str(int(round(item['min_temp']))))
            set_property('Day%i.Outlook'            % count, FORECAST.get(item['weather']['code'], item['weather']['description']))
            set_property('Day%i.OutlookIcon'        % count, '%s.png' % weathercode)
            set_property('Day%i.FanartCode'         % count, weathercode)
            if count == MAXDAYS:
                break
    #daily - extended (weatherbit)
        for count, item in enumerate(data['data']):
            code = str(item['weather']['code'])
            code = code + 'd'
            weathercode = WEATHER_CODES[code]
            set_property('Daily.%i.LongDay'         % (count+1), convert_datetime(item['ts'], 'timestamp', 'weekday', 'long'))
            set_property('Daily.%i.ShortDay'        % (count+1), convert_datetime(item['ts'], 'timestamp', 'weekday', 'short'))
            set_property('Daily.%i.LongDate'        % (count+1), convert_datetime(item['ts'], 'timestamp', 'monthday', 'long'))
            set_property('Daily.%i.ShortDate'       % (count+1), convert_datetime(item['ts'], 'timestamp', 'monthday', 'short'))
            set_property('Daily.%i.Outlook'         % (count+1), FORECAST.get(str(item['weather']['code']), item['weather']['description']))
            set_property('Daily.%i.OutlookIcon'     % (count+1), WEATHER_ICON % weathercode)
            set_property('Daily.%i.FanartCode'      % (count+1), weathercode)
            set_property('Daily.%i.WindDirection'   % (count+1), xbmc.getLocalizedString(int(round(WIND_DIR(item['wind_dir'])))))
            set_property('Daily.%i.WindDegree'      % (count+1), str(item['wind_dir']) + u'°')
            set_property('Daily.%i.Humidity'        % (count+1), str(item['rh']) + '%')
            set_property('Daily.%i.Temperature'     % (count+1), convert_temp(item['temp'], 'C') + TEMPUNIT)
            set_property('Daily.%i.HighTemperature' % (count+1), convert_temp(item['max_temp'], 'C') + TEMPUNIT)
            set_property('Daily.%i.LowTemperature'  % (count+1), convert_temp(item['min_temp'], 'C') + TEMPUNIT)
            set_property('Daily.%i.FeelsLike'       % (count+1), convert_temp(int(round(item['app_max_temp'])), 'C') + TEMPUNIT)
            set_property('Daily.%i.HighFeelsLike'   % (count+1), convert_temp(int(round(item['app_max_temp'])), 'C') + TEMPUNIT)
            set_property('Daily.%i.LowFeelsLike'    % (count+1), convert_temp(int(round(item['app_min_temp'])), 'C') + TEMPUNIT)
            set_property('Daily.%i.DewPoint'        % (count+1), convert_temp(int(round(item['dewpt'])), 'C') + TEMPUNIT)
            if 'F' in TEMPUNIT:
                set_property('Daily.%i.Pressure'      % (count+1), str(round(item['pres'] / 33.86 ,2)) + ' in')
                set_property('Daily.%i.SeaLevel'      % (count+1), str(round(item['slp'] / 33.86 ,2)) + ' in')
                set_property('Daily.%i.Snow'          % (count+1), str(round(item['snow'] * 0.04 ,2)) + ' in')
                set_property('Daily.%i.SnowDepth'     % (count+1), str(round(item['snow_depth'] * 0.04 ,2)) + ' in')
                if item['precip']:
                    set_property('Daily.%i.Precipitation' % (count+1), str(round(item['precip'] * 0.04 ,2)) + ' in')
                else:
                    set_property('Daily.%i.Precipitation' % (count+1), '')
                set_property('Daily.%i.Visibility'    % (count+1), str(round(item['vis'] * 0.621371 ,2)) + ' mi')
            else:
                set_property('Daily.%i.Pressure'      % (count+1), str(item['pres']) + ' mb')
                set_property('Daily.%i.SeaLevel'      % (count+1), str(round(item['slp'])) + ' mb')
                set_property('Daily.%i.Snow'          % (count+1), str(round(item['snow'])) + ' mm')
                set_property('Daily.%i.SnowDepth'     % (count+1), str(round(item['snow_depth'])) + ' mm')
                if item['precip']:
                    set_property('Daily.%i.Precipitation' % (count+1), str(round(item['precip'])) + ' mm')
                else:
                    set_property('Daily.%i.Precipitation' % (count+1), '')
                set_property('Daily.%i.Visibility'    % (count+1), str(item['vis']) + ' km')
            set_property('Daily.%i.WindSpeed'         % (count+1), convert_speed(item['wind_spd'], 'mps') + SPEEDUNIT)
            set_property('Daily.%i.WindGust'          % (count+1), convert_speed(item['wind_gust_spd'], 'mps') + SPEEDUNIT)
            set_property('Daily.%i.Cloudiness'        % (count+1), str(item['clouds']) + '%')
            set_property('Daily.%i.CloudsLow'         % (count+1), str(item['clouds_low']) + '%')
            set_property('Daily.%i.CloudsMid'         % (count+1), str(item['clouds_mid']) + '%')
            set_property('Daily.%i.CloudsHigh'        % (count+1), str(item['clouds_hi']) + '%')
            set_property('Daily.%i.Probability'       % (count+1), str(item['pop']) + '%')
            if item['uv']:
                set_property('Daily.%i.UVIndex'       % (count+1), str(int(round(item['uv']))) + '%')
            else:
                set_property('Daily.%i.UVIndex'       % (count+1), '')
            set_property('Daily.%i.Sunrise'           % (count+1), convert_datetime(item['sunrise_ts'], 'timestamp', 'timedate', None))
            set_property('Daily.%i.Sunset'            % (count+1), convert_datetime(item['sunset_ts'], 'timestamp', 'timedate', None))
            set_property('Daily.%i.Moonrise'          % (count+1), convert_datetime(item['moonrise_ts'], 'timestamp', 'timedate', None))
            set_property('Daily.%i.Moonset'           % (count+1), convert_datetime(item['moonset_ts'], 'timestamp', 'timedate', None))
            set_property('Daily.%i.MoonPhase'         % (count+1), str(item['moon_phase']))
            if item['ozone']:
                set_property('Daily.%i.Ozone'         % (count+1), str(int(round(item['ozone']))) + ' DU')
            else:
                set_property('Daily.%i.Ozone'         % (count+1), '')
        set_property('Daily.IsFetched'                , 'true')
