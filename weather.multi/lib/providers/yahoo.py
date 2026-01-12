from ..conversions import *

class Weather():
    def __init__():
        pass

    def get_weather(data, loc, locid):
    #current - standard
        set_property('Location'                    , loc)
        set_property('Current.Location'            , '%s, %s' % (data['location']['town'],data['location']['country']))
        set_property('Current.Condition'           , data['location']['outlook'])
        set_property('Current.Temperature'         , convert_temp(data['location']['temperature'], 'F', 'C'))
        if  data['conditions']['conditions']['uv']:
            set_property('Current.UVIndex'             , str(data['conditions']['conditions']['uv']['value']))
        else:
            set_property('Current.UVIndex'              , '')
        if  data['conditions']['conditions']['airQuality']:
            set_property('Current.AirQuality'          , data['conditions']['conditions']['airQuality']['value'] + ' UAQI')
        else:
            set_property('Current.AirQuality'              , '')
        if  data['conditions']['conditions']['pollen']:
            set_property('Current.Pollen'              , data['conditions']['conditions']['pollen']['value'])
        else:
            set_property('Current.Pollen'              , '')
        if data['location']['outlook'] in ['Mostly Cloudy', 'Partly Cloudy', 'Fair']:
            condition = '%s Day' % data['location']['outlook']
        else:
            condition = data['location']['outlook']
        set_property('Current.OutlookIcon'         , '%s.png' % OUTLOOK[condition]) # Kodi translates it to Current.ConditionIcon
        set_property('Current.FanartCode'          , OUTLOOK[condition])
        set_property('Current.Wind'                , convert_speed(data['forecasts'][0]['windForecasts'][0]['speed'], 'mph', 'kmh'))
        set_property('Current.WindDirection'       , xbmc.getLocalizedString(WINDDIR[data['forecasts'][0]['windForecasts'][0]['direction']]))
        set_property('Current.Humidity'            , data['conditions']['condition']['value'].rstrip('%'))
        set_property('Current.DewPoint'            , convert_temp(data['conditions']['condition']['text'].split('.')[0].lstrip('The dew point is ').rstrip('°F'), 'F', 'C'))
        set_property('Current.FeelsLike'           , convert_temp(data['location']['realfeel'], 'F', 'C'))
    #current - extended
        set_property('Current.WindChill'           , convert_temp(windchill(data['location']['temperature'], data['forecasts'][0]['windForecasts'][0]['speed']), 'F') + TEMPUNIT)
        if 'F' in TEMPUNIT:
            set_property('Current.Visibility'      , data['conditions']['conditions']['visibility']['value'] + ' mi')
            set_property('Current.Pressure'        , str(round(float(data['conditions']['conditions']['barometricPressure']['value']),2)) + ' inHg')
        else:
            set_property('Current.Visibility'      , str(round(1.60934 * int(data['conditions']['conditions']['visibility']['value']))) + ' km')
            set_property('Current.Pressure'        , str(int(round((33.864 * float(data['conditions']['conditions']['barometricPressure']['value']))))) + ' mbar')
        set_property('Current.Precipitation'       , str(data['forecasts'][0]['precipitationForecasts'][0]['probabilityOfPrecipitation']) + '%')
        if 'F' in TEMPUNIT:
            set_property('Current.PrecipitationAmount' , str(data['forecasts'][0]['precipitationForecasts'][0]['absoluteQuantity']) + 'in')
        else:
            set_property('Current.PrecipitationAmount' , str(round(data['forecasts'][0]['precipitationForecasts'][0]['absoluteQuantity'] * 25.4)) + 'mm')
        set_property('Current.IsFetched'           , 'true')
    #forecast - extended
        set_property('Forecast.City'               , data['location']['town'])
        set_property('Forecast.Country'            , data['location']['country'])
        set_property('Forecast.IsFetched'          , 'true')
    #today - extended
        set_property('Today.Sunrise'               , convert_datetime(data['location']['sunrise'], 'ampm', None, None))
        set_property('Today.Sunset'                , convert_datetime(data['location']['sunset'], 'ampm', None, None))
        set_property('Today.Moonphase'             , MOONPHASE[data['conditions']['conditions']['moon']['title'].lower()])
        set_property('Today.IsFetched'             , 'true')
    #hourly - extended
        skip = []
        for count, item in enumerate(data['forecasts'][0]['conditionsForecasts']):
            if item['text'] == 'Sunrise' or item['text'] == 'Sunset':
                skip.append(count)
                continue
            set_property('Hourly.%i.Time'          % (count + 1), convert_datetime(item['time'], 'ampm', None, None))
            set_property('Hourly.%i.ShortDate'     % (count + 1), xbmc.getLocalizedString(33006))
            set_property('Hourly.%i.Temperature'   % (count + 1), convert_temp(item['temperature'], 'F') + TEMPUNIT)
            set_property('Hourly.%i.Outlook'       % (count + 1), CONDITION.get(item['iconLabel'], item['iconLabel']))
            if item['iconLabel'] in ['Mostly Cloudy', 'Partly Cloudy', 'Fair']:
                if 'Night' in item['icon']:
                    condition = '%s Night' % item['iconLabel']
                else:
                    condition = '%s Day' % item['iconLabel']
            else:
                condition = item['iconLabel']
            set_property('Hourly.%i.OutlookIcon'   % (count + 1), '%s.png' % OUTLOOK[condition])
            set_property('Hourly.%i.FanartCode'    % (count + 1), OUTLOOK[condition])
        for count, item in enumerate(data['forecasts'][0]['precipitationForecasts']):
            if count in skip:
                continue
            if 'F' in TEMPUNIT:
                set_property('Hourly.%i.PrecipitationAmount'   % (count + 1), str(item['absoluteQuantity']) + 'in')
            else:
                set_property('Hourly.%i.PrecipitationAmount'   % (count + 1), str(round(item['absoluteQuantity'] * 25.4)) + 'mm')
            set_property('Hourly.%i.Precipitation'             % (count + 1), str(item['probabilityOfPrecipitation']) + '%')
        for count, item in enumerate(data['forecasts'][0]['windForecasts']):
            if count in skip:
                continue
            set_property('Hourly.%i.WindDirection' % (count + 1), xbmc.getLocalizedString(WINDDIR[item['direction']]))
            set_property('Hourly.%i.WindSpeed'     % (count + 1), convert_speed(item['speed'], 'mph') + SPEEDUNIT)
        if count < 23:
            offset = count + 1
            skip = []
            for count, item in enumerate(data['forecasts'][1]['conditionsForecasts']):
                if item['text'] == 'Sunrise' or item['text'] == 'Sunset':
                    skip.append(count)
                    continue
                set_property('Hourly.%i.Time'            % (offset + count + 1), convert_datetime(item['time'], 'ampm', None, None))
                set_property('Hourly.%i.ShortDate'       % (offset + count + 1), xbmc.getLocalizedString(33007))
                set_property('Hourly.%i.Temperature'     % (offset + count + 1), convert_temp(item['temperature'], 'F') + TEMPUNIT)
                set_property('Hourly.%i.Outlook'         % (offset + count + 1), CONDITION.get(item['iconLabel'], item['iconLabel']))
                if item['iconLabel'] in ['Mostly Cloudy', 'Partly Cloudy', 'Fair']:
                    if 'Night' in item['icon']:
                        condition = '%s Night' % item['iconLabel']
                    else:
                        condition = '%s Day' % item['iconLabel']
                else:
                    condition = item['iconLabel']
                set_property('Hourly.%i.OutlookIcon'     % (offset + count + 1), '%s.png' % OUTLOOK[condition])
                set_property('Hourly.%i.FanartCode'      % (offset + count + 1), OUTLOOK[condition])
                if (offset + count + 1) == 24:
                    break
            for count, item in enumerate(data['forecasts'][1]['precipitationForecasts']):
                if count in skip:
                    continue
                if 'F' in TEMPUNIT:
                    set_property('Hourly.%i.PrecipitationAmount' % (count + 1), str(item['absoluteQuantity']) + 'in')
                else:
                    set_property('Hourly.%i.PrecipitationAmount' % (count + 1), str(round(item['absoluteQuantity'] * 25.4)) + 'mm')
                set_property('Hourly.%i.Precipitation'           % (count + 1), str(item['probabilityOfPrecipitation']) + '%')
                if (offset + count + 1) == 24:
                    break
            for count, item in enumerate(data['forecasts'][1]['windForecasts']):
                if count in skip:
                    continue
                set_property('Hourly.%i.WindDirection'   % (count + 1), xbmc.getLocalizedString(WINDDIR[item['direction']]))
                set_property('Hourly.%i.WindSpeed'       % (count + 1), convert_speed(item['speed'], 'mph') + SPEEDUNIT)
                if (offset + count + 1) == 24:
                    break
        set_property('Hourly.IsFetched'          , 'true')

    def get_daily_weather(data):
    #daily - standard
        for count, item in enumerate(data['forecasts']):
            try:
                day, date = item['date'].split(' ')
                set_property('Day%i.Title'       % count, xbmc.getLocalizedString(LONGDAY[day]) + ' ' + date)
            except:
                day = item['date']
                set_property('Day%i.Title'       % count, xbmc.getLocalizedString(LONGDAY[day]))
            set_property('Day%i.HighTemp'        % count, convert_temp(item['highTemperature'], 'F', 'C'))
            set_property('Day%i.LowTemp'         % count, convert_temp(item['lowTemperature'], 'F', 'C'))
            set_property('Day%i.Outlook'         % count, item['iconLabel'])
            if item['iconLabel'] in ['Mostly Cloudy', 'Partly Cloudy', 'Fair']:
                condition = '%s Day' % item['iconLabel']
            else:
                condition = item['iconLabel']
            set_property('Day%i.OutlookIcon'      % count, '%s.png' % OUTLOOK[condition])
            set_property('Day%i.FanartCode'       % count, OUTLOOK[condition])
            if count == MAXDAYS:
                break
    #daily - extended
        for count, item in enumerate(data['forecasts']):
            try:
                day, date = item['date'].split(' ')
                set_property('Daily.%i.ShortDay'     % (count + 1), xbmc.getLocalizedString(SHORTDAY[day]))
                set_property('Daily.%i.LongDay'      % (count + 1), xbmc.getLocalizedString(LONGDAY[day]))
                set_property('Daily.%i.ShortDate'    % (count + 1), date)
                set_property('Daily.%i.LongDate'     % (count + 1), date)
            except:
                day = item['date']
                set_property('Daily.%i.ShortDay'     % (count + 1), xbmc.getLocalizedString(SHORTDAY[day]))
                set_property('Daily.%i.LongDay'      % (count + 1), xbmc.getLocalizedString(LONGDAY[day]))
                set_property('Daily.%i.ShortDate'    % (count + 1), '')
                set_property('Daily.%i.LongDate'     % (count + 1), '')
            set_property('Daily.%i.HighTemperature'  % (count + 1), convert_temp(item['highTemperature'], 'F') + TEMPUNIT)
            set_property('Daily.%i.LowTemperature'   % (count + 1), convert_temp(item['lowTemperature'], 'F') + TEMPUNIT)
            set_property('Daily.%i.Outlook'          % (count + 1), CONDITION.get(item['iconLabel'], item['iconLabel']))

            if item['iconLabel'] in ['Mostly Cloudy', 'Partly Cloudy', 'Fair']:
                condition = '%s Day' % item['iconLabel']
            else:
                condition = item['iconLabel']
            set_property('Daily.%i.OutlookIcon'      % (count + 1), '%s.png' % OUTLOOK[condition])
            set_property('Daily.%i.FanartCode'       % (count + 1), OUTLOOK[condition])
        set_property('Daily.IsFetched'               , 'true')
