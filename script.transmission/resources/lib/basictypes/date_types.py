"""Stand-alone type-definition objects for date-based data types

Three possible sources (1 implemented):

	* mx.DateTime (prefered, and implemented)
	* Python 2.3 datetime
	* standard time module (least interesting)

XXX Would be nice to get a Python 2.3 datetime module
implementation, but it's pretty low on my list of
priorities
"""
try:
	from datemx_types import *
	from mx import DateTime as mx_DateTime
	haveMX = 1
	DateTime_DT = mxDateTime_DT
	DateTimeDelta_DT = mxDateTimeDelta_DT
	TimeOfDay = mxTimeOfDay
	
	DateTime = mx_DateTime.DateTimeFrom
	DateTimeDelta = mx_DateTime.DateTimeDelta
	now = mx_DateTime.now
	today = mx_DateTime.today
except ImportError:
	haveMX = 0

haveImplementation = haveMX # or havePy23 or haveTimeModule

# month enumeration...
from basictypes import enumeration
import calendar

def allInstances( cls ):
	"""Return cls instances for each of this class's set"""
	items = [
		(choice.value, cls( name= choice.name))
		for choice in cls.set.values()
	]
	items.sort()
	items = [ v[1] for v in items ]
	return items


class WeekDay( enumeration.Enumeration ):
	"""Locale-specific day-of-week enumeration

	Uses both calendar and mx.DateTime's standard of
	Monday = 0, Sunday = 6
	"""
	dataType = 'enumeration.weekday'
	set = enumeration.EnumerationSet.coerce(
		zip(
			calendar.day_name,
			range(len(calendar.day_name))
		)
	)
	allInstances = classmethod( allInstances )
		
class WeekDayAbbr( enumeration.Enumeration ):
	"""Locale-specific day-of-week (abbreviated) enumeration

	Uses both calendar and mx.DateTime's standard of
	Mon = 0, Sun = 6
	"""
	dataType = 'enumeration.weekday.abbr'
	set = enumeration.EnumerationSet.coerce(
		zip(
			calendar.day_abbr,
			range(len(calendar.day_abbr))
		)
	)
	allInstances = classmethod( allInstances )

class Month( enumeration.Enumeration ):
	"""Locale-specific month enumeration

	Uses calendar/mx.DateTime standard of January=1,
	December = 12
	"""
	dataType = 'enumeration.month'
	data = zip(
			calendar.month_name[1:],
			range(len(calendar.month_name))[1:]
		)
	set = enumeration.EnumerationSet.coerce(
		data
	)
	allInstances = classmethod( allInstances )

class MonthAbbr( enumeration.Enumeration ):
	"""Locale-specific month (abbreviated) enumeration

	Uses calendar/mx.DateTime standard of January=1,
	December = 12
	"""
	dataType = 'enumeration.month.abbr'
	set = enumeration.EnumerationSet.coerce(
		zip(
			calendar.month_abbr[1:],
			range(len(calendar.month_abbr))[1:]
		)
	)
	allInstances = classmethod( allInstances )


del calendar
del enumeration
