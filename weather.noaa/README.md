# weather.noaa a Kodi Plugin for weather.gov (NOAA) weather forecasts


This Kodi plugin fetches weather reports from the National Weather Service https://www.weather.gov (eg NOAA). 

The best source for the latest release is to pull from my repo, (using either the Matrix or the Leia version)

* https://github.com/randallspicher/randalls-repo/tree/Leia/repository.randalls.repo
* https://github.com/randallspicher/randalls-repo/tree/Matrix/repository.randalls.repo

Note weather.gov only provides weather forecasts for USA.  The forecasts can be extremely localized (use the map-click feature from the weather.gov web site to get the latitude/longitude for the exact location you want the forecast for.)

weather.gov provides separate forecasts for Days and Nights, rather than just one per day. It also provides much more verbose forecasts.  It requires skin support to make use of the additional features.
https://github.com/randallspicher/skin.lyrebird.rmod is a skin that makes use of the additional features.  (including an option to use the weather.gov icons instead of the default kodi icons)


Skinners:

* Note that weather.gov does not supply forecasts as one-per-day.  It instead provides separate forecasts for Daytime and Overnight.  Hard-coding the text "Today" and "Tomorrow" will not be accurate, (since first 2 actual forecasts may be for "This Afternoon" and "Tonight" depending on the current time-of-day.  The "Title" property is best to use.  Since the forecast for Day and Night are separate records, the daytime forecast does not provide a "LowTemperature", and the night-time forecast does not provide a "HighTemperature"  The respective non-relevant properties will be left blank in the Daily.n.xxx properties (you will get either Daily.n.HighTemperature, or Daily.n.LowTemperature, depending on if it's a day or night forecast.)  Since Day0.HighTemp and Day0.LowTemp are raw numbers that Kodi insists on calculating, the same temperature is populated and returned in both, to keep kodi happy.  It is recommended that the skin only make use of the Daily properties.

* Weather.gov has much more verbose descriptive forecasts (can be paragraphs of info, instead of just a couple words).  A new screen (or pop-up dialog) is recommended to display the overview.

* The plugin adds new properties for the weather.gov forecast icons, "Daily.1.RemoteIcon", or "Day0.RemoteIcon", "Hourly.1.RemoteIcon" etc, which is the url for the icon that weather.gov provides.  The weather.gov icons are more expansive and dynamic (a large variety of conditions, including "split view" icons, for when the weather changes during the day (eg, 1/2 of the icon shows sunny, and 1/2 shows thunderstorms).  Plus, the icons include an overlay for the %chance of rain/snow. 



