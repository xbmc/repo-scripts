import time
import pytz
from datetime import datetime, timedelta
import utilities
import json
from PIL import Image
import urlcache
from constants import ISSUEDAT_FORMAT, DATAPOINT_DATETIME_FORMAT, SHORT_DAY_FORMAT, DATAPOINT_DATE_FORMAT,\
                        WEATHER_ICON_PATH, WEATHER_CODES, WINDOW, DAILY_LOCATION_FORECAST_URL, API_KEY,\
                        ADDON_DATA_PATH, THREEHOURLY_LOCATION_FORECAST_URL, TEXT_FORECAST_URL,\
                        HOURLY_LOCATION_OBSERVATION_URL, FORECAST_LAYER_CAPABILITIES_URL,\
                        OBSERVATION_LAYER_CAPABILITIES_URL, RAW_DATAPOINT_IMG_WIDTH, CROP_WIDTH, CROP_HEIGHT,\
                        GOOGLE_SURFACE, GOOGLE_MARKER, MAPTIME_FORMAT, REGIONAL_LOCATION,\
                        REGIONAL_LOCATION_ID, FORECAST_LOCATION, FORECAST_LOCATION_ID, OBSERVATION_LOCATION,\
                        OBSERVATION_LOCATION_ID, FORECASTMAP_SLIDER, OBSERVATIONMAP_SLIDER, FORECASTMAP_LAYER_SELECTION,\
                        OBSERVATIONMAP_LAYER_SELECTION, TZ, TZUK

@utilities.panelbusy('LeftPane')
def observation():
    utilities.log( "Fetching Hourly Observation for '%s (%s)' from the Met Office..." % (OBSERVATION_LOCATION, OBSERVATION_LOCATION_ID))
    with urlcache.URLCache(ADDON_DATA_PATH) as cache:
        filename = cache.get(HOURLY_LOCATION_OBSERVATION_URL, observation_expiry)
        data=json.load(open(filename))
    try:
        dv = data['SiteRep']['DV']
        dataDate = utilities.strptime(dv.get('dataDate').rstrip('Z'), DATAPOINT_DATETIME_FORMAT).replace(tzinfo=pytz.utc)
        WINDOW.setProperty('HourlyObservation.IssuedAt', dataDate.astimezone(TZ).strftime(ISSUEDAT_FORMAT))#@UndefinedVariable
        try:
            latest_period = dv['Location']['Period'][-1]
        except KeyError:
            latest_period = dv['Location']['Period']
        try:
            latest_obs = latest_period['Rep'][-1]
        except KeyError:
            latest_obs = latest_period['Rep']
        WINDOW.setProperty('Current.Condition', WEATHER_CODES[latest_obs.get('W', 'na')][1])#@UndefinedVariable
        WINDOW.setProperty('Current.Visibility', latest_obs.get('V', 'n/a'))#@UndefinedVariable
        WINDOW.setProperty('Current.Pressure', latest_obs.get('P', 'n/a'))#@UndefinedVariable
        WINDOW.setProperty('Current.Temperature', str(round(float(latest_obs.get('T', 'n/a')))).split('.')[0])#@UndefinedVariable
        WINDOW.setProperty('Current.Wind', latest_obs.get('S', 'n/a'))#@UndefinedVariable
        WINDOW.setProperty('Current.WindDirection', latest_obs.get('D', 'n/a'))#@UndefinedVariable
        WINDOW.setProperty('Current.WindGust', latest_obs.get('G', 'n/a'))#@UndefinedVariable
        WINDOW.setProperty('Current.OutlookIcon', '%s.png' % WEATHER_CODES[latest_obs.get('W', 'na')][0])#@UndefinedVariable
        WINDOW.setProperty('Current.FanartCode', '%s.png' % WEATHER_CODES[latest_obs.get('W','na')][0])#@UndefinedVariable
        WINDOW.setProperty('Current.DewPoint', str(round(float(latest_obs.get('Dp', 'n/a')))).split('.')[0])#@UndefinedVariable
        WINDOW.setProperty('Current.Humidity', str(round(float(latest_obs.get('H', 'n/a')))).split('.')[0])#@UndefinedVariable

        WINDOW.setProperty('HourlyObservation.IsFetched', 'true')#@UndefinedVariable
    except KeyError as e:
        e.args = ("Key Error in JSON File", "Key '{0}' not found while processing file from url:".format(e.args[0]), HOURLY_LOCATION_OBSERVATION_URL)
        raise

@utilities.panelbusy('RightPane')
def daily():
    utilities.log( "Fetching Daily Forecast for '%s (%s)' from the Met Office..." % (FORECAST_LOCATION, FORECAST_LOCATION_ID))
    with urlcache.URLCache(ADDON_DATA_PATH) as cache:
        filename = cache.get(DAILY_LOCATION_FORECAST_URL, daily_expiry)
        data=json.load(open(filename))
    try:
        dv = data['SiteRep']['DV']
        dataDate = utilities.strptime(dv.get('dataDate').rstrip('Z'), DATAPOINT_DATETIME_FORMAT).replace(tzinfo=pytz.utc)
        WINDOW.setProperty('DailyForecast.IssuedAt', dataDate.astimezone(TZ).strftime(ISSUEDAT_FORMAT))#@UndefinedVariable
        for p, period in enumerate(dv['Location']['Period']):
            WINDOW.setProperty('Day%d.Title' %p, time.strftime(SHORT_DAY_FORMAT, time.strptime(period.get('value'), DATAPOINT_DATE_FORMAT)))#@UndefinedVariable
            for rep in period['Rep']:
                weather_type = rep.get('W', 'na')
                if rep.get('$') == 'Day':
                    WINDOW.setProperty('Day%d.HighTemp' %p, rep.get('Dm', 'na'))#@UndefinedVariable
                    WINDOW.setProperty('Day%d.HighTempIcon' %p, rep.get('Dm'))#@UndefinedVariable
                    WINDOW.setProperty('Day%d.Outlook' %p, WEATHER_CODES.get(weather_type)[1])#@UndefinedVariable
                    WINDOW.setProperty('Day%d.OutlookIcon' % p, WEATHER_ICON_PATH % WEATHER_CODES.get(weather_type, 'na')[0])#@UndefinedVariable
                    WINDOW.setProperty('Day%d.WindSpeed' % p,  rep.get('S', 'na'))#@UndefinedVariable
                    WINDOW.setProperty('Day%d.WindDirection' % p, rep.get('D', 'na').lower())#@UndefinedVariable

                elif rep.get('$') == 'Night':
                    WINDOW.setProperty('Day%d.LowTemp' %p, rep.get('Nm', 'na'))#@UndefinedVariable
                    WINDOW.setProperty('Day%d.LowTempIcon' %p, rep.get('Nm'))#@UndefinedVariable
    except KeyError as e:
        e.args = ("Key Error in JSON File", "Key '{0}' not found while processing file from url:".format(e.args[0]), DAILY_LOCATION_FORECAST_URL)
        raise

    WINDOW.setProperty('DailyForecast.IsFetched', 'true')#@UndefinedVariable

@utilities.panelbusy('RightPane')
def threehourly():
    utilities.log( "Fetching 3 Hourly Forecast for '%s (%s)' from the Met Office..." % (FORECAST_LOCATION, FORECAST_LOCATION_ID))
    with urlcache.URLCache(ADDON_DATA_PATH) as cache:
        filename = cache.get(THREEHOURLY_LOCATION_FORECAST_URL, threehourly_expiry)
        data=json.load(open(filename))
    try:
        dv = data['SiteRep']['DV']
        dataDate = utilities.strptime(dv.get('dataDate').rstrip('Z'), DATAPOINT_DATETIME_FORMAT).replace(tzinfo=pytz.utc)
        WINDOW.setProperty('3HourlyForecast.IssuedAt', dataDate.astimezone(TZ).strftime(ISSUEDAT_FORMAT))#@UndefinedVariable
        count = 0
        for period in dv['Location']['Period']:
            for rep in period['Rep']:
                #extra xbmc targeted info:
                weather_type = rep.get('W', 'na')
                WINDOW.setProperty('3Hourly%d.Outlook' % count, WEATHER_CODES.get(weather_type)[1])#@UndefinedVariable
                WINDOW.setProperty('3Hourly%d.WindSpeed' % count, rep.get('S', 'n/a'))#@UndefinedVariable
                WINDOW.setProperty('3Hourly%d.WindDirection' % count, rep.get('D', 'na').lower())#@UndefinedVariable
                WINDOW.setProperty('3Hourly%d.GustSpeed' % count, rep.get('G', 'n/a'))#@UndefinedVariable
                WINDOW.setProperty('3Hourly%d.UVIndex' % count, rep.get('U', 'n/a'))#@UndefinedVariable
                WINDOW.setProperty('3Hourly%d.Precipitation' % count, rep.get('Pp'))#@UndefinedVariable
                WINDOW.setProperty('3Hourly%d.OutlookIcon' % count, WEATHER_ICON_PATH % WEATHER_CODES.get(weather_type, 'na')[0])#@UndefinedVariable
                WINDOW.setProperty('3Hourly%d.Day' % count, time.strftime(SHORT_DAY_FORMAT, time.strptime(period.get('value'), DATAPOINT_DATE_FORMAT)))#@UndefinedVariable
                WINDOW.setProperty('3Hourly%d.Time' % count, utilities.minutes_as_time(int(rep.get('$'))))#@UndefinedVariable
                WINDOW.setProperty('3Hourly%d.ActualTemp' % count, utilities.rownd(utilities.localised_temperature(rep.get('T', 'na'))))#@UndefinedVariable
                WINDOW.setProperty('3Hourly%d.ActualTempIcon' % count, rep.get('T', 'na'))#@UndefinedVariable
                WINDOW.setProperty('3Hourly%d.FeelsLikeTemp' % count, utilities.rownd(utilities.localised_temperature(rep.get('F', 'na'))))#@UndefinedVariable
                WINDOW.setProperty('3Hourly%d.FeelsLikeTempIcon' % count, rep.get('F', 'na'))#@UndefinedVariable
                count +=1
    except KeyError as e:
        e.args = ("Key Error in JSON File", "Key '{0}' not found while processing file from url:".format(e.args[0]), THREEHOURLY_LOCATION_FORECAST_URL)
        raise
    WINDOW.setProperty('3HourlyForecast.IsFetched', 'true')#@UndefinedVariable

@utilities.panelbusy('RightPane')
def text():
    utilities.log( "Fetching Text Forecast for '%s (%s)' from the Met Office..." % (REGIONAL_LOCATION, REGIONAL_LOCATION_ID))
    with urlcache.URLCache(ADDON_DATA_PATH) as cache:
        filename = cache.get(TEXT_FORECAST_URL, text_expiry)
        data=json.load(open(filename))
    try:
        rf = data['RegionalFcst']
        issuedat = utilities.strptime(rf['issuedAt'].rstrip('Z'), DATAPOINT_DATETIME_FORMAT).replace(tzinfo=pytz.utc)
        WINDOW.setProperty('TextForecast.IssuedAt', issuedat.astimezone(TZ).strftime(ISSUEDAT_FORMAT))#@UndefinedVariable
        count = 0
        for period in rf['FcstPeriods']['Period']:
            #have to check type because json can return list or dict here
            if isinstance(period['Paragraph'],list):
                for paragraph in period['Paragraph']:
                    WINDOW.setProperty('Text.Paragraph%d.Title' % count, paragraph['title'].rstrip(':').lstrip('UK Outlook for'))#@UndefinedVariable
                    WINDOW.setProperty('Text.Paragraph%d.Content' % count, paragraph['$'])#@UndefinedVariable
                    count+=1
            else:
                WINDOW.setProperty('Text.Paragraph%d.Title' % count, period['Paragraph']['title'].rstrip(':').lstrip('UK Outlook for'))#@UndefinedVariable
                WINDOW.setProperty('Text.Paragraph%d.Content' % count, period['Paragraph']['$'])#@UndefinedVariable
                count+=1
    except KeyError as e:
        e.args = ("Key Error in JSON File", "Key '{0}' not found while processing file from url:".format(e.args[0]), TEXT_FORECAST_URL)
        raise
    WINDOW.setProperty('TextForecast.IsFetched', 'true')#@UndefinedVariable

@utilities.panelbusy('RightPane')
def forecastlayer():
    utilities.log( "Fetching '{0}' Forecast Map with index '{1}'...".format(FORECASTMAP_LAYER_SELECTION, FORECASTMAP_SLIDER))
    with urlcache.URLCache(ADDON_DATA_PATH) as cache:
        surface = cache.get(GOOGLE_SURFACE, lambda x:  datetime.utcnow() + timedelta(days=30))
        marker = cache.get(GOOGLE_MARKER, lambda x:  datetime.utcnow() + timedelta(days=30))

        filename = cache.get(FORECAST_LAYER_CAPABILITIES_URL, forecastlayer_capabilities_expiry)
        data = json.load(open(filename))
        #pull parameters out of capabilities file - TODO: consider using jsonpath here
        try:
            for thislayer in data['Layers']['Layer']:
                if thislayer['@displayName'] == FORECASTMAP_LAYER_SELECTION:
                    layer_name = thislayer['Service']['LayerName']
                    image_format = thislayer['Service']['ImageFormat']
                    default_time = thislayer['Service']['Timesteps']['@defaultTime']
                    timesteps = thislayer['Service']['Timesteps']['Timestep']
                    break
            else:
                raise Exception('Error', "Couldn't find layer '%s'" % FORECASTMAP_LAYER_SELECTION)
        except KeyError as e:
            e.args = ("Key Error in JSON File", "Key '{0}' not found while processing file from url:".format(e.args[0]), FORECAST_LAYER_CAPABILITIES_URL)
            raise

        issuedat = utilities.strptime(default_time, DATAPOINT_DATETIME_FORMAT).replace(tzinfo=pytz.utc)

        index = FORECASTMAP_SLIDER
        if int(index) < 0:
            utilities.log('Slider is negative. Fetching with index 0')
            WINDOW.setProperty('ForecastMap.Slider', '0') #@UndefinedVariable
            index = '0'
        elif int(index) > len(timesteps)-1:
            utilities.log('Slider exceeds available index range. Fetching with index {0}'.format(str(len(timesteps)-1)))
            WINDOW.setProperty('ForecastMap.Slider', str(len(timesteps)-1)) #@UndefinedVariable
            index = str(len(timesteps)-1)

        timestep = timesteps[int(index)]
        delta = timedelta(hours=timestep)
        maptime = TZUK.normalize(issuedat + delta)

        #get overlay using parameters from gui settings
        try:
            LayerURL = data['Layers']['BaseUrl']['$']
        except KeyError as e:
            e.args = ("Key Error in JSON File", "Key '{0}' not found while processing file from url:".format(e.args[0]), FORECAST_LAYER_CAPABILITIES_URL)
            raise

        url = LayerURL.format(LayerName=layer_name,
                                 ImageFormat=image_format,
                                 DefaultTime=default_time,
                                 Timestep=timestep,
                                 key=API_KEY)
        layer = cache.get(url, lambda x: datetime.utcnow() + timedelta(days=1), image_resize)

        WINDOW.setProperty('ForecastMap.Surface', surface)#@UndefinedVariable
        WINDOW.setProperty('ForecastMap.Marker', marker)#@UndefinedVariable
        WINDOW.setProperty('ForecastMap.IssuedAt', issuedat.astimezone(TZ).strftime(ISSUEDAT_FORMAT))#@UndefinedVariable
        WINDOW.setProperty('ForecastMap.MapTime', maptime.strftime(MAPTIME_FORMAT))#@UndefinedVariable
        WINDOW.setProperty('ForecastMap.Layer', layer)#@UndefinedVariable
        WINDOW.setProperty('ForecastMap.IsFetched', 'true')#@UndefinedVariable

@utilities.panelbusy('RightPane')
def observationlayer():
    utilities.log( "Fetching '{0}' Observation Map with index '{1}'...".format(OBSERVATIONMAP_LAYER_SELECTION, OBSERVATIONMAP_SLIDER))
    
    with urlcache.URLCache(ADDON_DATA_PATH) as cache:
        surface = cache.get(GOOGLE_SURFACE, lambda x:  datetime.utcnow() + timedelta(days=30))
        marker = cache.get(GOOGLE_MARKER, lambda x:  datetime.utcnow() + timedelta(days=30))

        filename = cache.get(OBSERVATION_LAYER_CAPABILITIES_URL, observationlayer_capabilities_expiry)
        data = json.load(open(filename))
        #pull parameters out of capabilities file - TODO: consider using jsonpath here
        try:
            issuedat = utilities.strptime(data['Layers']['Layer'][-1]['Service']['Times']['Time'][0], DATAPOINT_DATETIME_FORMAT).replace(tzinfo=pytz.utc)
            for thislayer in data['Layers']['Layer']:
                if thislayer['@displayName'] == OBSERVATIONMAP_LAYER_SELECTION:
                    layer_name = thislayer['Service']['LayerName']
                    image_format = thislayer['Service']['ImageFormat']
                    times = thislayer['Service']['Times']['Time']
                    break
            else:
                raise Exception('Error', "Couldn't find layer '%s'" % OBSERVATIONMAP_LAYER_SELECTION)
        except KeyError as e:
            e.args = ("Key Error in JSON File", "Key '{0}' not found while processing file from url:".format(e.args[0]), OBSERVATION_LAYER_CAPABILITIES_URL)
            raise

        index = OBSERVATIONMAP_SLIDER
        if int(index) < 0:
            utilities.log('Slider is negative. Fetching with index 0')
            WINDOW.setProperty('ObservationMap.Slider', '0')#@UndefinedVariable
            index = '0'
        elif int(index) > len(times)-1:
            utilities.log('Slider exceeds available index range. Fetching with index {0}'.format(str(len(times)-1)))
            WINDOW.setProperty('ObservationMap.Slider', str(len(times)-1))#@UndefinedVariable
            index = str(len(times)-1)

        indexedtime = times[int(index)]
        maptime = utilities.strptime(indexedtime, DATAPOINT_DATETIME_FORMAT).replace(tzinfo=pytz.utc)

        #get overlay using parameters from gui settings
        try:
            LayerURL = data['Layers']['BaseUrl']['$']
        except KeyError as e:
            e.args = ("Key Error in JSON File", "Key '{0}' not found while processing file from url:".format(e.args[0]), OBSERVATION_LAYER_CAPABILITIES_URL)
            raise

        url = LayerURL.format(LayerName=layer_name,
                                 ImageFormat=image_format,
                                 Time=indexedtime,
                                 key=API_KEY)
        layer = cache.get(url, lambda x: datetime.utcnow() + timedelta(days=1), image_resize)

        WINDOW.setProperty('ObservationMap.Surface', surface)#@UndefinedVariable
        WINDOW.setProperty('ObservationMap.Marker', marker)#@UndefinedVariable
        WINDOW.setProperty('ObservationMap.IssuedAt', issuedat.astimezone(TZ).strftime(ISSUEDAT_FORMAT))#@UndefinedVariable
        WINDOW.setProperty('ObservationMap.MapTime', maptime.astimezone(TZUK).strftime(MAPTIME_FORMAT))#@UndefinedVariable
        WINDOW.setProperty('ObservationMap.Layer', layer)#@UndefinedVariable
        WINDOW.setProperty('ObservationMap.IsFetched', 'true')#@UndefinedVariable

def daily_expiry(filename):
    data = json.load(open(filename))
    dataDate = data['SiteRep']['DV']['dataDate'].rstrip('Z')
    return utilities.strptime(dataDate, DATAPOINT_DATETIME_FORMAT) + timedelta(hours=1.5)

def threehourly_expiry(filename):
    data = json.load(open(filename))
    dataDate = data['SiteRep']['DV']['dataDate'].rstrip('Z')
    return utilities.strptime(dataDate, DATAPOINT_DATETIME_FORMAT) + timedelta(hours=1.5)

def text_expiry(filename):
    data = json.load(open(filename))
    issuedAt = data['RegionalFcst']['issuedAt'].rstrip('Z')
    return utilities.strptime(issuedAt, DATAPOINT_DATETIME_FORMAT) + timedelta(hours=12)

def observation_expiry(filename):
    data = json.load(open(filename))
    dataDate = data['SiteRep']['DV']['dataDate'].rstrip('Z')
    return utilities.strptime(dataDate, DATAPOINT_DATETIME_FORMAT) + timedelta(hours=1.5)

def forecastlayer_capabilities_expiry(filename):
    data = json.load(open(filename))
    defaultTime = data['Layers']['Layer'][0]['Service']['Timesteps']['@defaultTime']
    return utilities.strptime(defaultTime, DATAPOINT_DATETIME_FORMAT) + timedelta(hours=9)

def observationlayer_capabilities_expiry(filename):
    #TODO: Assumes 'Rainfall' is the last report in the file, and Rainfall is the best indicator of issue time
    data = json.load(open(filename))
    tyme = data['Layers']['Layer'][-1]['Service']['Times']['Time'][0]
    return utilities.strptime(tyme, DATAPOINT_DATETIME_FORMAT) + timedelta(minutes=30)

def image_resize(filename):
    #remove the 'cone' from the image
    img = Image.open(filename)
    (width, height) = img.size
    if width == RAW_DATAPOINT_IMG_WIDTH:
        img.crop((CROP_WIDTH, CROP_HEIGHT, width-CROP_WIDTH, height-CROP_HEIGHT)).save(filename, img.format)
    