"""Python 2.3 datetime (+dateutils) implementation
"""
import datetime
from dateutil import parser 
from dateutil import relativedelta
from basictypes import datatypedefinition, registry
import time, re, traceback

class DateTime( datetime.datetime ):
	"""Datatype for the standard Python 2.3+ datetime.datetime type
	"""
	dataType = 'datetime.datetime'
	__slots__ = ()
##	def __new__( cls, value=None ):
##		if value is None:
##			return cls.copy(cls.now())
##		elif isinstance( value, datetime.datetime
	def check (cls, value):
		"""Determine whether value conforms to definition"""
		return isinstance( value, cls )
	check = classmethod (check)
	def copy( cls, source ):
		"""Produce a version of given datetime as this class' instance"""
		return cls(
			source.year, 
			source.month, 
			source.day, 
			source.hour, 
			source.minute, 
			source.second, 
			source.microsecond,
			source.tzinfo
		)
	copy = classmethod( copy )
	def coerce(cls, value):
		"""Coerce value to the appropriate data type
		
		Accepts:
			datetime.datetime instances 
			datetime.date instances (assumes midnight)
			datetime.time instances (assumes today for local tz (watch out!))
			string/unicode (using parser.parse)
			float (interpreted as time module times)
			time.struct_time instances (note that DST setting is not retained!)
			
		"""
		if cls.check( value ):
			return value
		elif isinstance( value, datetime.datetime ):
			return cls.copy( value )
		elif isinstance( value, datetime.date ):
			return cls( value.year, value.month, value.day, tzinfo=value.tzinfo )
		elif isinstance( value, datetime.time ):
			# XXX May be corner cases here where due to timezone,
			# today is actually tomorrow or yesterday...
			# what we'd really like to do is figure out what day it is
			# in the value's timezone right now and use *that*
			return cls.combine(
				datetime.date.today(),
				value
			)
		if isinstance(value, (str,unicode)):
			return cls.copy( parser.parse( value ) )
		elif isinstance(value, float):
			# interpreted as a local-time second-since-the-epoch
			return cls.fromtimestamp( value )
		elif isinstance( value, time.struct_time ):
			# no built-in function for this!?!
			return cls(
				value[0], # year
				value[1], # month
				value[2], # day
				value[3], # hour
				value[4], # minute 
				int(value[5]), # second
				int((value[5]%1.0)*1000000), # microseconds
				# XXX note that we lose the daylight savings time info!
			)
		elif type(value).__name__ == 'DateTime':
			return cls(
				value.year,
				value.month,
				value.day,
				value.hour,
				value.minute,
				int(value.second),
				int(round((value.second%1)*1000, 0)),
				# tz is the *name* of the timezone, which we likely won't have...
			)
		else:
			raise TypeError (
				"""Could not convert %r (type %s) to DateTime type"""% (value,type (value))
			)
	coerce = classmethod (coerce)
	def asMx( self ):
		"""Produce an mxDateTime instance for this value"""
		from mx.DateTime import DateTime
		return DateTime.DateTime(
			source.year, 
			source.month, 
			source.day, 
			source.hour, 
			source.minute, 
			source.second + (source.microsecond/1000.0), 
			#source.tzinfo
		)

class _TimeParser(object):
	"""Class providing time-parsing functionality"""
	HOUR_RE = '\d+'
	MINUTE_RE = '\d+'
	SECOND_RE = '(\d+([.]\d+)?)|([.]\d+)'
	PM_RE = 'p[.]?[m]?[.]?'
	AM_RE = 'a[.]?[m]?[.]?'
	
	TEMPLATE_RE = """
	(?P<hour>%(hour)s)
	(
		[:,.]
		(?P<minute>%(minute)s)?
		(
			[:,.]
			(?P<second>%(second)s)
		)?
	)?
	[ \t]*
	(
		(?P<am>%(am)s)
		|
		(?P<pm>%(pm)s)
	)?
	"""
	
	def parse( cls, text ):
		"""Takes user input and returns partial value dict

		Defaults to 24 hours clock

		Example inputs:
			2:13pm -> 14:13:00
			2:13 -> 2:13:00
			14:13:00 -> 14:13:00
			3pm -> 15:00:00
			4 -> 04:00:00
		AM and PM formats:
			a, p, am, pm, a.m., p.m., 
		"""
		re_fragments = {
			'hour':cls.HOUR_RE, 'minute':cls.MINUTE_RE, 'second':cls.SECOND_RE,
			'am':cls.AM_RE, 'pm':cls.PM_RE,
		}
		searcher = re.compile( cls.TEMPLATE_RE % re_fragments, re.IGNORECASE|re.VERBOSE )
		
		result = searcher.search( text )
		if result:
			if len( result.group(0)) != len(text.strip()):
				raise ValueError( """Could not parse the entirety of %r as a TimeOfDay value, parsed %r"""% (text, result.group(0)))
			if result.group('minute'):
				minute = int( result.group('minute'), 10)
			else:
				minute = 0
			values = {
				'hour': int( result.group('hour'), 10),
				'minute': minute,
				'second': float( result.group('second') or 0),
			}
			if result.group( 'pm'):
				# Forces the value to be in the PM, regardless
				# of whether it already is (so 14pm works fine).
				if (values['hour']%24) != 12:
					values['hour'] = (values['hour'] % 12)+12
			if result.group( 'am'):
				# 12am gets subtraction...
				if (values['hour'] %24) ==  12:
					values['hour'] = 0
			return values
		raise ValueError( """Unable to parse value %r into a TimeOfDay value"""%(text,))
	parse = classmethod (parse)
	
class _TimeDeltaParser( _TimeParser ):
	"""Time parser with negative-value support"""
	HOUR_RE = '[+ -]*\d+'
	def parse( cls, text ):
		"""Takes user input and returns partial value dict
		
		This just adds support for negative values, which
		consists of negating all values if the hour value is
		negative.
		"""
		values = super( _TimeDeltaParser, cls).parse( text )
		if values['hour'] < 0:
			values['minute'] = -values['minute']
			values['second'] = -values['second']
		return values
	parse = classmethod( parse )

