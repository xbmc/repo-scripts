import math
import xbmc

DAYS = { 'Mon': xbmc.getLocalizedString( 11 ),
         'Tue': xbmc.getLocalizedString( 12 ),
         'Wed': xbmc.getLocalizedString( 13 ),
         'Thu': xbmc.getLocalizedString( 14 ),
         'Fri': xbmc.getLocalizedString( 15 ),
         'Sat': xbmc.getLocalizedString( 16 ),
         'Sun': xbmc.getLocalizedString( 17 )}

def winddir(deg):
    if deg >= 12 and deg <= 34:
        wind = 'NNE'
    elif deg >= 35 and deg <= 56:
        wind = 'NE'
    elif deg >= 57 and deg <= 79:
        wind = 'ENE'
    elif deg >= 80 and deg <= 101:
        wind = 'E'
    elif deg >= 102 and deg <= 124:
        wind = 'ESE'
    elif deg >= 125 and deg <= 146:
        wind = 'SE'
    elif deg >= 147 and deg <= 169:
        wind = 'SSE'
    elif deg >= 170 and deg <= 191:
        wind = 'S'
    elif deg >= 192 and deg <= 214:
        wind = 'SSW'
    elif deg >= 215 and deg <= 236:
        wind = 'SW'
    elif deg >= 237 and deg <= 259:
        wind = 'WSW'
    elif deg >= 260 and deg <= 281:
        wind = 'W'
    elif deg >= 282 and deg <= 304:
        wind = 'WNW'
    elif deg >= 305 and deg <= 326:
        wind = 'NW'
    elif deg >= 327 and deg <= 349:
        wind = 'NNW'
    else:
        wind = 'N'
    return wind

#### thanks to FrostBox @ http://forum.xbmc.org/showthread.php?p=937168#post937168

def feelslike( T=10, V=25 ):
    """ The formula to calculate the equivalent temperature related to the wind chill is:
        T(REF) = 13.12 + 0.6215 * T - 11.37 * V**0.16 + 0.3965 * T * V**0.16
        Or:
        T(REF): is the equivalent temperature in degrees Celsius
        V: is the wind speed in km/h measured at 10m height
        T: is the temperature of the air in degrees Celsius
        source: http://zpag.tripod.com/Meteo/eolien.htm
        
        getFeelsLike( tCelsius, windspeed )
    """
    FeelsLike = T
    #Wind speeds of 4 mph or less, the wind chill temperature is the same as the actual air temperature.
    if round( ( V + .0 ) / 1.609344 ) > 4:
        FeelsLike = ( 13.12 + ( 0.6215 * T ) - ( 11.37 * V**0.16 ) + ( 0.3965 * T * V**0.16 ) )
    return str( round( FeelsLike ) )


def dewpoint( Tc=0, RH=93, minRH=( 0, 0.075 )[ 0 ] ):
    """ Dewpoint from relative humidity and temperature
        If you know the relative humidity and the air temperature,
        and want to calculate the dewpoint, the formulas are as follows.
        
        getDewPoint( tCelsius, humidity )
    """
    #First, if your air temperature is in degrees Fahrenheit, then you must convert it to degrees Celsius by using the Fahrenheit to Celsius formula.
    # Tc = 5.0 / 9.0 * ( Tf - 32.0 )
    #The next step is to obtain the saturation vapor pressure(Es) using this formula as before when air temperature is known.
    Es = 6.11 * 10.0**( 7.5 * Tc / ( 237.7 + Tc ) )
    #The next step is to use the saturation vapor pressure and the relative humidity to compute the actual vapor pressure(E) of the air. This can be done with the following formula.
    #RH=relative humidity of air expressed as a percent. or except minimum(.075) humidity to abort error with math.log.
    RH = RH or minRH #0.075
    E = ( RH * Es ) / 100
    #Note: math.log( ) means to take the natural log of the variable in the parentheses
    #Now you are ready to use the following formula to obtain the dewpoint temperature.
    try:
        DewPoint = ( -430.22 + 237.7 * math.log( E ) ) / ( -math.log( E ) + 19.08 )
    except ValueError:
        #math domain error, because RH = 0%
        #return "N/A"
        DewPoint = 0 #minRH
    #Note: Due to the rounding of decimal places, your answer may be slightly different from the above answer, but it should be within two degrees.
    return str( int( DewPoint ) )
