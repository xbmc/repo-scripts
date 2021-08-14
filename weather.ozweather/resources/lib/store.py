# -*- coding: utf-8 -*-
class Store:
    """
    Helper class to to provide a centralised store for CONSTANTS and globals
    """

    # Static class variables, referred to by Store.whatever
    # https://docs.python.org/3/faq/programming.html#how-do-i-create-static-class-data-and-static-class-methods

    # CONSTANTS
    # ABC WEATHER VIDEO - scraping
    ABC_URL = "https://www.abc.net.au/news/newschannel/weather-in-90-seconds/"
    ABC_WEATHER_VIDEO_PATTERN = "//abcmedia.akamaized.net/news/news24/wins/(.+?)/WIN(.*?)_512k.mp4"
    ABC_STUB = "https://abcmedia.akamaized.net/news/news24/wins/"
    # WEATHERZONE - scraping, only used as a fallback data source if BOM not configured or fails
    WEATHERZONE_URL = 'https://www.weatherzone.com.au'
    WEATHERZONE_SEARCH_URL = WEATHERZONE_URL + "/search/"
    # BOM - JSON API
    BOM_URL = 'http://www.bom.gov.au'
    BOM_API_URL = 'https://api.weather.bom.gov.au/v1'
    BOM_API_LOCATIONS_URL = BOM_API_URL + '/locations'
    # BOM - RADARS - FTP
    BOM_RADAR_FTPSTUB = "ftp://anonymous:someone%40somewhere.com@ftp.bom.gov.au//anon/gen/radar/"
    BOM_RADAR_BACKGROUND_FTPSTUB = "ftp://anonymous:someone%40somewhere.com@ftp.bom.gov.au//anon/gen/radar_transparencies/"
    BOM_RADAR_HTTPSTUB = "http://www.bom.gov.au/products/radar_transparencies/"
    # The below list is generated using the scraper: python3 resources/lib/bom/bom_radar_scrape_latest.py
    # Just cut and paste the output of that below....
    # The master URL is: http://www.bom.gov.au/australia/radar/about/radar_site_info.shtml
    # Can cross check with: https://github.com/theOzzieRat/bom-radar-card/blob/master/src/bom-radar-card.ts around line 130
    BOM_RADAR_LOCATIONS = [
        # http://www.bom.gov.au/australia/radar/info/nsw_info.shtml
        (-29.96, 146.81, "Brewarrina", "IDR933"),
        (-35.66, 149.51, "Canberra (Captain's Flat)", "IDR403"),
        (-29.62, 152.97, "Grafton", "IDR283"),
        (-29.50, 149.85, "Moree", "IDR533"),
        (-31.0240, 150.1915, "Namoi (Blackjack Mountain)", "IDR693"),
        (-32.730, 152.027, "Newcastle", "IDR043"),
        (-29.033, 167.933, "Norfolk Island", "IDR623"),
        (-33.701, 151.210, "Sydney (Terrey Hills)", "IDR713"),
        (-35.17, 147.47, "Wagga Wagga", "IDR553"),
        (-34.264, 150.874, "Wollongong (Appin)", "IDR033"),
        # http://www.bom.gov.au/australia/radar/info/vic_info.shtml
        (-37.86, 144.76, "Melbourne", "IDR023"),
        (-34.28, 141.59, "Mildura", "IDR973"),
        (-37.89, 147.56, "Bairnsdale", "IDR683"),
        (-35.99, 142.01, "Rainbow", "IDR953"),
        (-36.03, 146.03, "Yarrawonga", "IDR493"),
        # http://www.bom.gov.au/australia/radar/info/qld_info.shtml
        (-19.88, 148.08, "Bowen", "IDR243"),
        (-27.718, 153.240, "Brisbane (Mt. Stapylton)", "IDR663"),
        (-16.82, 145.68, "Cairns", "IDR193"),
        (-23.5494, 148.2392, "Emerald (Central Highlands)", "IDR723"),
        (-23.86, 151.26, "Gladstone", "IDR233"),
        (-25.957, 152.577, "Gympie (Mt Kanigan)", "IDR083"),
        (-23.43, 144.29, "Longreach", "IDR563"),
        (-21.12, 149.22, "Mackay", "IDR223"),
        (-27.61, 152.54, "Marburg", "IDR503"),
        (-16.67, 139.17, "Mornington Island", "IDR363"),
        (-20.7114, 139.5553, "Mount Isa", "IDR753"),
        (-19.42, 146.55, "Townsville (Hervey Range)", "IDR733"),
        (-26.44, 147.35, "Warrego", "IDR673"),
        (-12.67, 141.92, "Weipa", "IDR783"),
        (-16.288, 149.965, "Willis Island", "IDR413"),
        # http://www.bom.gov.au/australia/radar/info/wa_info.shtml
        (-34.94, 117.80, "Albany", "IDR313"),
        (-17.95, 122.23, "Broome", "IDR173"),
        (-24.88, 113.67, "Carnarvon", "IDR053"),
        (-20.65, 116.69, "Dampier", "IDR153"),
        (-31.78, 117.95, "South Doodlakine", "IDR583"),
        (-33.83, 121.89, "Esperance", "IDR323"),
        (-28.80, 114.70, "Geraldton", "IDR063"),
        (-25.03, 128.30, "Giles", "IDR443"),
        (-18.23, 127.66, "Halls Creek", "IDR393"),
        (-30.79, 121.45, "Kalgoorlie-Boulder", "IDR483"),
        (-22.10, 114.00, "Learmonth", "IDR293"),
        (-33.097, 119.009, "Newdegate", "IDR383"),
        (-32.39, 115.87, "Perth (Serpentine)", "IDR703"),
        (-20.37, 118.63, "Port Hedland", "IDR163"),
        (-30.36, 116.29, "Watheroo", "IDR793"),
        (-15.45, 128.12, "Wyndham", "IDR073"),
        # http://www.bom.gov.au/australia/radar/info/sa_info.shtml
        (-34.617, 138.469, "Adelaide (Buckland Park)", "IDR643"),
        (-35.33, 138.50, "Adelaide (Sellicks Hill)", "IDR463"),
        (-32.13, 133.70, "Ceduna", "IDR333"),
        (-37.75, 140.77, "Mt Gambier", "IDR143"),
        (-31.16, 136.80, "Woomera", "IDR273"),
        # http://www.bom.gov.au/australia/radar/info/tas_info.shtml
        (-43.1122, 147.8061, "Hobart (Mt Koonya)", "IDR763"),
        (-41.181, 145.579, "West Takone", "IDR523"),
        (-42.83, 147.51, "Hobart Airport", "IDR373"),
        # http://www.bom.gov.au/australia/radar/info/nt_info.shtml
        (-23.82, 133.90, "Alice Springs", "IDR253"),
        (-12.46, 130.93, "Darwin/Berrimah", "IDR633"),
        (-12.28, 136.82, "Gove", "IDR093"),
        (-14.51, 132.45, "Katherine/Tindal", "IDR423"),
        (-11.6494, 133.38, "Warruwi", "IDR773"),
    ]

    DAYS = {"Mon": "Monday",
            "Tue": "Tuesday",
            "Wed": "Wednesday",
            "Thu": "Thursday",
            "Fri": "Friday",
            "Sat": "Saturday",
            "Sun": "Sunday"}

    WEATHER_CODES = {'clearing_shower': '39',
                     'clear': '32',
                     'cloudy': '26',
                     'cloud_and_wind_increasing': '23',
                     'cloud_increasing': '26',
                     'drizzle': '11',
                     'drizzle_clearing': '39',
                     'fog': '20',
                     'fog_then_sunny': '34',
                     'frost_then_sunny': '34',
                     'hazy': '21',
                     'heavy_rain': '40',
                     'heavy_showers': '12',
                     'increasing_sunshine': '30',
                     'late_shower': '45',
                     'light_shower': '11',
                     'late_thunder': '47',
                     'mostly_cloudy': '26',
                     'mostly_sunny': '34',
                     'overcast': '26',
                     'possible_shower': '11',
                     'possible_thunderstorm': '37',
                     'rain': '40',
                     'rain_and_snow': '5',
                     'rain_clearing': '39',
                     'rain_developing': '12',
                     'rain_tending to_snow': '5',
                     'shower': '11',
                     'showers': '11',
                     'showers_easing': '11',
                     'showers_increasing': '11',
                     'snow': '41',
                     'snowfalls_clearing': '5',
                     'snow_developing': '13',
                     'snow_showers': '41',
                     'snow_tending to_rain': '5',
                     'storm': '38',
                     'sunny': '32',
                     'thunderstorms': '38',
                     'thunderstorms_clearing': '37',
                     'windy': '23',
                     'windy_with_rain': '2',
                     'windy_with_showers': '2',
                     'windy_with_snow': '43',
                     'wind_and_rain_increasing': '2',
                     'wind_and_showers_easing': '11',
                     'unknown': 'na',
                     'nt_unknown': 'na'}

    WEATHER_CODES_NIGHT = {'clearing_shower': '45',
                           'clear': '31',
                           'cloudy': '29',
                           'cloud_and_wind_increasing': '27',
                           'cloud_increasing': '27',
                           'drizzle': '45',
                           'drizzle_clearing': '45',
                           'fog': '20',
                           'fog_then_sunny': '33',
                           'frost_then_sunny': '33',
                           'hazy': '33',
                           'heavy_rain': '47',
                           'heavy_showers': '45',
                           'increasing_sunshine': '31',
                           'late_shower': '45',
                           'light_shower': '45',
                           'late_thunder': '47',
                           'mostly_cloudy': '27',
                           'mostly_sunny': '31',
                           'overcast': '29',
                           'possible_shower': '45',
                           'possible_thunderstorm': '47',
                           'rain': '45',
                           'rain_and_snow': '46',
                           'rain_clearing': '45',
                           'rain_developing': '45',
                           'rain_tending to_snow': '45',
                           'shower': '45',
                           'showers': '45',
                           'showers_easing': '45',
                           'showers_increasing': '45',
                           'snow': '46',
                           'snowfalls_clearing': '46',
                           'snow_developing': '46',
                           'snow_showers': '46',
                           'snow_tending to_rain': '46',
                           'storm': '47',
                           'sunny': '31',
                           'thunderstorms': '47',
                           'thunder-storms': '47',
                           'thunderstorms_clearing': '47',
                           'windy': '29',
                           'windy_with_rain': '45',
                           'windy_with_showers': '45',
                           'windy_with_snow': '46',
                           'wind_and_rain_increasing': '45',
                           'wind_and_showers_easing': '45',
                           'unknown': 'na',
                           'nt_unknown': 'na'}

    """
    These are the weather codes for Kodi it seems
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

    NIGHT SUBSET:
    27 Mostly Cloudy/Night
    29 Partly Cloudy/Night
    31 Clear/Night
    33 Hazy/Night
    45 Rain/Night
    46 Snow/Night
    47 Thunder Showers/Night
    """

    # Just a store!
    def __init__(self):
        pass

