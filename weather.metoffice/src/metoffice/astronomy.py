"""
Sunrise and Sunset calculations courtesy of Michel Anders
http://michelanders.blogspot.co.uk/2010/12/calulating-sunrise-and-sunset-in-python.html
"""
from math import cos, sin, acos, asin, tan
from math import degrees as deg, radians as rad
from datetime import datetime, time

from constants import TZ

# this module is not provided here. See text.
#from timezone import LocalTimezone

class Sun:
    """
    Calculate sunrise and sunset based on equations from NOAA
    http://www.srrb.noaa.gov/highlights/sunrise/calcdetails.html

    typical use, calculating the sunrise at the present day:

    import datetime
    import sunrise
    s = sun(lat=49,long=3)
    print('sunrise at ',s.sunrise(when=datetime.datetime.now())
    """
    def __init__(self, lat=52.37, lng=4.90): # default Amsterdam
        self.lat = lat
        self.lng = lng

    def sunrise(self, when=None):
        """
        return the time of sunrise as a datetime.time object
        when is a datetime.datetime object. If none is given
        a local time zone is assumed (including daylight saving
        if present)
        """
        if when is None:
            when = datetime.now(tz=TZ)
        self.__preptime(when)
        self.__calc()
        return Sun.__timefromdecimalday(self.sunrise_t)

    def sunset(self, when=None):
        if when is None:
            when = datetime.now(tz=TZ)
        self.__preptime(when)
        self.__calc()
        return Sun.__timefromdecimalday(self.sunset_t)

    def solarnoon(self, when=None):
        if when is None:
            when = datetime.now(tz=TZ)
        self.__preptime(when)
        self.__calc()
        return Sun.__timefromdecimalday(self.solarnoon_t)

    @staticmethod
    def __timefromdecimalday(day):
        """
        returns a datetime.time object.

        day is a decimal day between 0.0 and 1.0, e.g. noon = 0.5
        """
        hours = 24.0*day
        h = int(hours)
        minutes = (hours-h)*60
        m = int(minutes)
        seconds = (minutes-m)*60
        s = int(seconds)
        return time(hour=h, minute=m, second=s)

    def __preptime(self, when):
        """
        Extract information in a suitable format from when,
        a datetime.datetime object.
        """
        # datetime days are numbered in the Gregorian calendar
        # while the calculations from NOAA are distibuted as
        # OpenOffice spreadsheets with days numbered from
        # 1/1/1900. The difference are those numbers taken for
        # 18/12/2010
        self.day = when.toordinal()-(734124-40529)
        t = when.time()
        self.time = (t.hour + t.minute/60.0 + t.second/3600.0)/24.0

        self.timezone = 0
        offset = when.utcoffset()
        if not offset is None:
            self.timezone = offset.seconds/3600.0

    def __calc(self):
        """
        Perform the actual calculations for sunrise, sunset and
        a number of related quantities.

        The results are stored in the instance variables
        sunrise_t, sunset_t and solarnoon_t
        """
        timezone = self.timezone # in hours, east is positive
        longitude = self.lng     # in decimal degrees, east is positive
        latitude = self.lat      # in decimal degrees, north is positive

        time = self.time # percentage past midnight, i.e. noon  is 0.5
        day = self.day     # daynumber 1=1/1/1900

        jday = day+2415018.5+time-timezone/24 # Julian day
        jcent = (jday-2451545)/36525    # Julian century

        manom = 357.52911+jcent*(35999.05029-0.0001537*jcent)
        mlong = 280.46646+jcent*(36000.76983+jcent*0.0003032)%360
        eccent = 0.016708634-jcent*(0.000042037+0.0001537*jcent)
        mobliq = 23+(26+((21.448-jcent*(46.815+jcent*(0.00059-jcent*0.001813))))/60)/60
        obliq = mobliq+0.00256*cos(rad(125.04-1934.136*jcent))
        vary = tan(rad(obliq/2))*tan(rad(obliq/2))
        seqcent = sin(rad(manom))*(1.914602-jcent*(0.004817+0.000014*jcent))+\
            sin(rad(2*manom))*(0.019993-0.000101*jcent)+sin(rad(3*manom))*0.000289
        struelong = mlong+seqcent
        sapplong = struelong-0.00569-0.00478*sin(rad(125.04-1934.136*jcent))
        declination = deg(asin(sin(rad(obliq))*sin(rad(sapplong))))

        eqtime = 4*deg(vary*sin(2*rad(mlong))-2*eccent*sin(rad(manom))+\
            4*eccent*vary*sin(rad(manom))*cos(2*rad(mlong))-\
            0.5*vary*vary*sin(4*rad(mlong))-1.25*eccent*eccent*sin(2*rad(manom)))

        hourangle = deg(acos(cos(rad(90.833))/(cos(rad(latitude))*\
            cos(rad(declination)))-tan(rad(latitude))*tan(rad(declination))))

        self.solarnoon_t = (720-4*longitude-eqtime+timezone*60)/1440
        self.sunrise_t = self.solarnoon_t-hourangle*4/1440
        self.sunset_t = self.solarnoon_t+hourangle*4/1440

"""
if __name__ == "__main__":
 s=Sun(lat=52.37,long=4.90)
 print(datetime.today())
 print(s.sunrise(),s.solarnoon(),s.sunset())
"""
