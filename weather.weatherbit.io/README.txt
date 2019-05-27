INFO FOR SKINNERS

All values returned by the addon will include their units.
Skinners won't have to bother with it.

---------------------------
DEFAULT KODI WEATHER LABELS
---------------------------


CURRENT
-------
Current.Location
Current.Condition
Current.Temperature
Current.Wind
Current.WindDirection
Current.Humidity
Current.FeelsLike
Current.DewPoint
Current.UVIndex
Current.ConditionIcon      (eg. resource://resource.images.weathericons.default/28.png)
Current.FanartCode


DAY [0-6]
---------
Day%i.Title
Day%i.HighTemp
Day%i.LowTemp
Day%i.Outlook
Day%i.OutlookIcon
Day%i.FanartCode


WEATHERPROVIDER
----------------
WeatherProvider
WeatherProviderLogo



-----------------------
EXTENDED WEATHER LABELS
-----------------------


FORECAST
--------
Forecast.IsFetched
Forecast.City
Forecast.Country
Forecast.Latitude
Forecast.Longitude
Forecast.Updated           (date and time the forecast was retrieved by weatherbit.io)


CURRENT
-------
Current.IsFetched
Current.Visibility         (visible distance)
Current.Pressure           (air pressure)
Current.SeaLevel           (pressure at sealevel)
Current.Snow               (amount of snow over the last 3 hours)
Current.Precipitation      (total amount of rain and snow over the last 3 hours)
Current.Cloudiness         (cloud coverage)


TODAY
-----
Today.IsFetched
Today.Sunrise
Today.Sunset


DAILY [1-16]
------------
Daily.IsFetched
Daily.%i.LongDay           (eg. 'Monday')
Daily.%i.ShortDay          (eg. 'Mon')
Daily.%i.LongDate          (eg. '1 January')
Daily.%i.ShortDate         (eg. '1 Jan')
Daily.%i.Outlook           (eg. 'Very heavy rain')
Daily.%i.OutlookIcon
Daily.%i.FanartCode
Daily.%i.WindSpeed
Daily.%i.WindDirection     (eg. 'SSW')
Daily.%i.WindDegree        (eg. '220°')
Daily.%i.Humidity
Daily.%i.DewPoint
Daily.%i.WindGust
Daily.%i.HighTemperature   (highest temperature that will be reached today)
Daily.%i.LowTemperature    (lowest temperature that will be reached today)
Daily.%i.Temperature       (average temperature)
Daily.%i.HighFeelsLike
Daily.%i.LowFeelsLike
Daily.%i.FeelsLike         (same as HighFeelsLike)
Daily.%i.Pressure
Daily.%i.SeaLevel
Daily.%i.Cloudiness
Daily.%i.CloudsLow         (cloud coverage at 0-3km hight)
Daily.%i.CloudsMid         (cloud coverage at 3-5km hight)
Daily.%i.CloudsHigh        (cloud coverage at >5km hight)
Daily.%i.Snow              (amount of snow)
Daily.%i.SnowDepth         (depth of snow on the ground)
Daily.%i.Precipitation     (total amount of rain and snow)
Daily.%i.Probability       (probability of precipitation)
Daily.%i.UVIndex
Daily.%i.Visibility
Daily.%i.Sunrise
Daily.%i.Sunset
Daily.%i.Moonrise
Daily.%i.Moonset
Daily.%i.MoonPhase         (moon phase fraction)
Daily.%i.Ozone             (average ozone level)


HOURLY [1-34]              (NOTE: this is 3-hourly, eg. 0:00, 3:00, 6:00, 9:00 and so on) 
-------------
Hourly.IsFetched
Hourly.%i.Time             (eg. '12:00')
Hourly.%i.LongDate
Hourly.%i.ShortDate
Hourly.%i.Outlook          (eg. 'Very heavy rain')
Hourly.%i.OutlookIcon
Hourly.%i.FanartCode
Hourly.%i.WindSpeed
Hourly.%i.WindDirection    (eg. 'SSW')
Hourly.%i.WindDegree       (eg. '220°')
Hourly.%i.Humidity
Hourly.%i.DewPoint
Hourly.%i.WindGust
Hourly.%i.Temperature
Hourly.%i.FeelsLike
Hourly.%i.Pressure
Hourly.%i.SeaLevel
Hourly.%i.Cloudiness
Hourly.%i.CloudsLow        (cloud coverage at 0-3km hight)
Hourly.%i.CloudsMid        (cloud coverage at 3-5km hight)
Hourly.%i.CloudsHigh       (cloud coverage at >5km hight)
Hourly.%i.Snow             (amount of snow)
Hourly.%i.SnowDepth        (depth of snow on the ground)
Hourly.%i.Precipitation    (total amount of rain and snow)
Hourly.%i.Probability      (probability of precipitation)
Hourly.%i.UVIndex
Hourly.%i.Visibility
Hourly.%i.Ozone            (average ozone level)


MAP [1-5]
---------
Map.IsFetched
Map.%i.Area
Map.%i.Layer
Map.%i.Heading
Map.%i.Legend

