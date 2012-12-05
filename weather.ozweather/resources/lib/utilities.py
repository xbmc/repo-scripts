# -*- coding: utf-8 -*-
import xbmc

DAYS = { "Mon": xbmc.getLocalizedString( 11 ),
         "Tue": xbmc.getLocalizedString( 12 ),
         "Wed": xbmc.getLocalizedString( 13 ),
         "Thu": xbmc.getLocalizedString( 14 ),
         "Fri": xbmc.getLocalizedString( 15 ),
         "Sat": xbmc.getLocalizedString( 16 ),
         "Sun": xbmc.getLocalizedString( 17 )}

WEATHER_CODES = { 'Clearing Shower'                 : '39',
                  'Cloudy'                          : '26',
                  'Cloud And Wind Increasing'       : '23',
                  'Cloud Increasing'                : '26',
                  'Drizzle'                         : '11',
                  'Drizzle Clearing'                : '39',
                  'Fog Then Sunny'                  : '34',
                  'Frost Then Sunny'                : '34',
                  'Hazy'                            : '21',
                  'Heavy Rain'                      : '40',
                  'Heavy Showers'                   : '12',
                  'Increasing Sunshine'             : '30',
                  'Late Shower'                     : '45',
                  'Late Thunder'                    : '47',
                  'Mostly Cloudy'                   : '26',
                  'Mostly Sunny'                    : '34',
                  'Overcast'                        : '26',
                  'Possible Shower'                 : '11',
                  'Possible Thunderstorm'           : '37',
                  'Rain'                            : '40',
                  'Rain And Snow'                   : '5',
                  'Rain Clearing'                   : '39',
                  'Rain Developing'                 : '12',
                  'Rain Tending To Snow'            : '5',
                  'Showers'                         : '11',
                  'Showers Easing'                  : '11',
                  'Showers Increasing'              : '11',
                  'Snow'                            : '41',
                  'Snowfalls Clearing'              : '5',
                  'Snow Developing'                 : '13',
                  'Snow Showers'                    : '41',
                  'Snow Tending To Rain'            : '5',
                  'Sunny'                           : '32',
                  'Thunderstorms'                   : '38',
                  'ThunderStorms'                   : '38',
                  'Thunderstorms Clearing'          : '37',
                  'Windy'                           : '23',
                  'Windy With Rain'                 : '2',
                  'Windy With Showers'              : '2',
                  'Windy With Snow'                 : '43',
                  'Wind And Rain Increasing'        : '2',
                  'Wind And Showers Easing'         : '11',
                  'Unknown'                         : 'na',
                  'nt_unknown'                      : 'na'}

"""   These are the weather codes fro XBMC is seems
N/A Not Available
0 Rain/Lightning
01 Windy/Rain
02 Same as 01
03 Same as 00
04 Same as 00
05 Cloudy/Snow-Rain Mix
06 Hail
07 Icy/Clouds Rain-Snow
08 Icy/Haze Rain
09 Haze/Rain
10 Icy/Rain
11 Light Rain
12 Moderate Rain
13 Cloudy/Flurries
14 Same as 13
15 Flurries
16 Same as 13
17 Same as 00
18 Same as 00
19 Dust
20 Fog
21 Haze
22 Smoke
23 Windy
24 Same as 23
25 Frigid
26 Mostly Cloudy
27 Mostly Cloudy/Night
28 Mostly Cloudy/Sunny
29 Partly Cloudy/Night
30 Partly Cloudy/Day
31 Clear/Night
32 Clear/Day
33 Hazy/Night
34 Hazy/Day
35 Same as 00
36 Hot!
37 Lightning/Day
38 Lightning
39 Rain/Day
40 Rain
41 Snow
42 Same as 41
43 Windy/Snow
44 Same as 30
45 Rain/Night
46 Snow/Night
47 Thunder Showers/Night
"""