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
Forecast.Updated           (date and time the forecast was retrieved by openweathermap)


CURRENT
-------
Current.IsFetched
Current.LowTemperature     (for large cities, the temp my vary from one side of the city to the other. this is the lowest current temperature in the city)
Current.HighTemperature    (for large cities, the temp my vary from one side of the city to the other. this is the highest current temperature in the city)
Current.Pressure           (air pressure)
Current.SeaLevel           (pressure at sealevel)
Current.GroundLevel        (pressure at groundlevel)
Current.WindGust           (sudden, brief increase in speed of the wind)
Current.WindDirStart       (wind direction at the start of the day)
Current.WindDirEnd         (wind direction at the end of the day)
Current.Rain               (amount of rain over the last 3 hours)
Current.Snow               (amount of snow over the last 3 hours)
Current.Precipitation      (total amount of rain and snow over the last 3 hours)
Current.Cloudiness         (cloud coverage)
Current.ShortOutlook       (eg. 'Rain')
Current.OutlookIcon        (eg. 28.png)


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
Daily.%i.ShortOutlook      (eg. 'Rain')
Daily.%i.OutlookIcon
Daily.%i.FanartCode
Daily.%i.WindSpeed
Daily.%i.WindDirection     (eg. 'SSW')
Daily.%i.WindDegree        (eg. '220°')
Daily.%i.Humidity
Daily.%i.TempMorn          (morning temperature)
Daily.%i.TempDay           (day temperature)
Daily.%i.TempEve           (evening temperature)
Daily.%i.TempNight         (night temperature)
Daily.%i.DewPoint
Daily.%i.FeelsLike
Daily.%i.WindGust
Daily.%i.HighTemperature   (highest temperature that will be reached today)
Daily.%i.LowTemperature    (lowest temperature that will be reached today)
Daily.%i.Pressure
Daily.%i.Cloudiness
Daily.%i.Rain              (amount of rain)
Daily.%i.Snow              (amount of snow)
Daily.%i.Precipitation     (total amount of rain and snow)


36HOUR [1-3]
------------
36Hour.IsFetched
36Hour.%i.Heading          ('Today, 'Tonight' or 'Tomorrow')
36Hour.%i.TemperatureHeading ('High' or 'Low')
36Hour.%i.LongDay          (eg. 'Monday')
36Hour.%i.ShortDay         (eg. 'Mon')
36Hour.%i.LongDate         (eg. '1 January')
36Hour.%i.ShortDate        (eg. '1 Jan')
36Hour.%i.Outlook          (eg. 'Very heavy rain')
36Hour.%i.ShortOutlook     (eg. 'Rain')
36Hour.%i.OutlookIcon
36Hour.%i.FanartCode
36Hour.%i.WindSpeed
36Hour.%i.WindDirection    (eg. 'SSW')
36Hour.%i.WindDegree       (eg. '220°')
36Hour.%i.Humidity
36Hour.%i.Temperature
36Hour.%i.DewPoint
36Hour.%i.FeelsLike
36Hour.%i.WindGust
36Hour.%i.HighTemperature  (highest temperature that will be reached today)
36Hour.%i.LowTemperature   (lowest temperature that will be reached today)
36Hour.%i.Pressure
36Hour.%i.Cloudiness
36Hour.%i.Rain             (amount of rain)
36Hour.%i.Snow             (amount of snow)
36Hour.%i.Precipitation    (total amount of rain and snow)


WEEKEND [1-2]
-------------
Weekend.IsFetched
Weekend.%i.LongDay
Weekend.%i.ShortDay
Weekend.%i.LongDate
Weekend.%i.ShortDate
Weekend.%i.Outlook
Weekend.%i.ShortOutlook
Weekend.%i.OutlookIcon
Weekend.%i.FanartCode
Weekend.%i.WindSpeed
Weekend.%i.WindDirection
Weekend.%i.WindDegree
Weekend.%i.Humidity
Weekend.%i.TempMorn
Weekend.%i.TempDay
Weekend.%i.TempEve
Weekend.%i.TempNight
Weekend.%i.DewPoint
Weekend.%i.FeelsLike
Weekend.%i.WindGust
Weekend.%i.HighTemperature (highest temperature that will be reached today)
Weekend.%i.LowTemperature  (lowest temperature that will be reached today)
Weekend.%i.Pressure
Weekend.%i.Cloudiness
Weekend.%i.Rain            (amount of rain)
Weekend.%i.Snow            (amount of snow)
Weekend.%i.Precipitation   (total amount of rain and snow)


HOURLY [1-34]              (NOTE: this is 3-hourly, eg. 0:00, 3:00, 6:00, 9:00 and so on) 
-------------
Hourly.IsFetched
Hourly.%i.Time             (eg. '12:00')
Hourly.%i.LongDate
Hourly.%i.ShortDate
Hourly.%i.Outlook
Hourly.%i.ShortOutlook
Hourly.%i.OutlookIcon
Hourly.%i.FanartCode
Hourly.%i.WindSpeed
Hourly.%i.WindDirection
Hourly.%i.WindDegree
Hourly.%i.WindGust
Hourly.%i.Humidity
Hourly.%i.Temperature
Hourly.%i.HighTemperature  (for large cities, the temp my vary from one side of the city to the other. this is the lowest temperature in the city at this hour)
Hourly.%i.LowTemperature   (for large cities, the temp my vary from one side of the city to the other. this is the lowest temperature in the city at this hour)
Hourly.%i.DewPoint
Hourly.%i.FeelsLike
Hourly.%i.Pressure
Hourly.%i.SeaLevel
Hourly.%i.GroundLevel
Hourly.%i.Cloudiness
Hourly.%i.Rain             (amount of rain)
Hourly.%i.Snow             (amount of snow)
Hourly.%i.Precipitation    (total amount of rain and snow)


MAP [1-5]
---------
Map.IsFetched
Map.%i.Area
Map.%i.Layer
Map.%i.Heading
Map.%i.Legend

