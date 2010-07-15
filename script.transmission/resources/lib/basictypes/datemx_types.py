"""mxDateTime-based date value-types

XXX Still need:
	full RelativeDateTime definition
"""
from mx.DateTime import *
from basictypes import datatypedefinition, registry
import time, re, traceback

__all__ = ( "mxDateTime_DT", "mxDateTimeDelta_DT", "mxTimeOfDay", 'RelativeDateTime')

class mxDateTime_DT( datatypedefinition.BaseType_DT ):
	"""Data type for an mx.DateTime.DateTime value
	"""
	baseType = DateTimeType
	dataType = 'datetime.mx'
	def check (cls, value):
		"""Determine whether value conforms to definition"""
		return isinstance( value, DateTimeType)
	check = classmethod (check)
	def coerce(cls, value):
		"""Coerce value to the appropriate data type

		Will accept:
			DateTimeType
			string or Unicode representations (DateTimeFrom)
			float (DateTimeFromTicks)
			time.struct_time (mktime)
		"""
		if cls.check( value ):
			return value
		if isinstance( value, unicode):
			value = value.encode()
		if isinstance(value, str):
			# need to parse the data...
			# XXX this isn't good, DateTimeFrom only raise an exception
			# if the format is close enough to "right" that it can determine
			# a format which "should" work.  As a result, it will ignore
			# such things as "2" or "23" and just treat them as though
			# they were start-of-today
			return DateTimeFrom(value)
		elif isinstance(value, float):
			# interpreted as a local-time second-since-the-epoch
			return DateTimeFromTicks( value )
		elif isinstance( value, time.struct_time ):
			return mktime( value )
		else:
			raise TypeError (
				"""Could not convert %r (type %s) to mxDateTime type"""% (value,type (value))
			)
	coerce = classmethod (coerce)
##	def factories ( cls ):
##		"""Get the factories for this data type"""
##		return [now,today]
##	factories = classmethod (factories)

#	def __store__( cls, value ):
#		"""Return a stable, low-level representation of the value
#
#		In this case, an ISO date-string for the UTC value of the
#		DateTime
#		"""
#		gm = value.gmtime()
#		return gm.Format('%Y-%m-%dT%H:%M:')+str(gm.second)
#	__store__ = classmethod( __store__ )
#	def __unstore__( cls, value ):
#		"""Take our opaque date-store value and convert to an instance
#		"""
#		gm = DateTimeFrom( value )
#		return gm.localtime()
#	__unstore__ = classmethod( __unstore__ )
registry.registerDT( DateTimeType, mxDateTime_DT )

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

class mxDateTimeDelta_DT( datatypedefinition.BaseType_DT ):
	"""Data type for an mx.DateTime.DateTimeDelta value
	"""
	baseType = DateTimeDeltaType
	dataType = 'datetimedelta.mx'
	def check (cls, value):
		"""Determine whether value conforms to definition"""
		return isinstance( value, DateTimeDeltaType)
	check = classmethod (check)
	def coerce(cls, value):
		"""Coerce value to the appropriate data type

		Will accept:
			DateTimeType
			string or Unicode representations (DateTimeFrom)
			float (DateTimeFromTicks)
		"""
		if cls.check( value ):
			return value
		if isinstance(value, (str,unicode)):
			# need to parse the data...
			return cls.parse(value)
		elif isinstance (value, (tuple,list)):
			return DateTimeDelta( * value )
		elif isinstance( value, float ):
			return DateTimeDelta( 0,0,0, value )
		else:
			raise TypeError (
				"""Could not convert %r (type %s) to mxDateTime type"""% (value,type (value))
			)
	coerce = classmethod (coerce)
##	def factories ( cls ):
##		"""Get factories for this data type"""
##		return []
##	factories = classmethod (factories)
	def parse( cls, text ):
		"""Takes text (user input) and returns a DateTimeDelta object

		Example inputs:
			2 hours, 3 days, 45 minutes
			3d2h45m
			45m
			2hours
			H:M:S (i.e. standard time format)

		XXX should eventually allow:
			2,3,45 -> directly to the constructor (d,h,m,s)
			2h 15 -> imply order based on previous item
			2.5 -> fractional day or hour (see next note)
		XXX should we take bare integer as _day_, not hour, as currently???
			seems more useful as-is, but it's not really in line
			with the base type
		"""
		if ':' in text:
			try:
				values = _TimeDeltaParser.parse( text )
				return DateTimeDelta(
					0, # days
					values['hour'],
					values['minute'],
					values['second'],
				)
			except (TypeError, ValueError):
				traceback.print_exc()
		units = [ 'd','h','m','s',]
		basePattern = '(\d+([.]\d+)?)\W*%s'
		fragments = []
		for unit in units:
			result = re.compile( basePattern%unit, re.I ).search( text )
			if result:
				fragment = result.group( 1 )
				if not result.group( 2 ):
					fragments.append( int(fragment))
				else:
					fragments.append( float(fragment))
			else:
				fragments.append( 0 )
		if fragments == [0,0,0,0] and text.strip():
			try:
				fragments[1] = int( text )
			except ValueError:
				pass
		
		fragments = cls._normalise(fragments)
		return DateTimeDelta( * fragments )
	parse = classmethod (parse)
	def _normalise( cls, value ):
		"""Local utility function... Push overflows into higher units, push fractions into lower units"""
		value = list(value)
		d,h,m,s = range(4)
		# push up
		for a,b,divisor in [(s,m,60),(m,h,60),(h,d,24)]:
			if value[a] > divisor: # more than x in y
				value[b] = value[b] + int( value[a]/divisor)
				value[a] = value[a] % divisor
		# push down
		for a,b,divisor in [(h,d,24),(m,h,60),(s,m,60),]:
			if value[b] % 1.0: # fraction present
				value[a] = value[a] + (value[b]%1.0 * divisor)
				value[b] = int(value[b])
		return tuple(value)
	_normalise = classmethod (_normalise)
	def format( cls, value ):
		"""Format as a string which is back-coercable"""
		result = []
		for (attr,fmt,always) in (('day','%i',0),('hour','%02i',1),('minute','%02i',1),('second','%0.2f',0)):
			v = getattr( value, attr )
			if v or always:
				result.append( fmt%v+attr[0] )
		return ", ".join( result )
	format = classmethod( format )
registry.registerDT( DateTimeDeltaType, mxDateTimeDelta_DT )


class mxTimeOfDay( _TimeParser, RelativeDateTime ):
	"""Representation of a time during a particular day

	This implementation is simply a sub-class of
	RelativeDateTime which provides the functionality
	of a data-type definition
	"""
	dataType = 'timeofday.mx'
	## Apparently the object type's __init__ is overriding the RelativeDateTime's
	__init__ = RelativeDateTime.__init__

	def __repr__( self ):
		"""Get a code-like representation of the time of day"""
		return """%s( %r )"""%( self.__class__.__name__, self.__class__.format( self ))
	def __str__( self ):
		"""Get the string representation of the time of day"""
		return self.__class__.format( self )
	def __eq__( self, other ):
		"""Are we equal to the other value?"""
		if not isinstance( other, RelativeDateTime ):
			return 0
		try:
			for attr in (
				'hour','minute','second',
				'year','month','day',
				'hours','minutes','seconds',
				'years','months','days',
			):
				if getattr( self, attr) != getattr( other, attr ):
					return 0
			return 1
		except (ValueError,TypeError,AttributeError):
			return 0
	### Data type definition API
	def check( cls, value ):
		"""Check that this is a RDT with only hour, minute and second"""
		if isinstance( value, cls ):
			for attribute in [ 'year','month','day','years','months','days','hours','minutes','seconds']:
				if getattr(value, attribute):
					return 0
			return 1
		return 0
	check = classmethod( check )
	def coerce( cls, value ):
		"""Coerce the value to our internal format (RelativeDateTime)

		Accepts:
			RelativeDateTime with only hour, minute, and second values
			tuple/list with up to 4 values for (default 0):
				hour, minute, second, millisecond
			RelativeDateTime with more data (copies to new with just time data)
			DateTime (creates a RelativeDateTime for the DateTime's TimeOfDay)
			float, int or long -> bare hours values
		"""
		def normalise( hour=0, minute=0, second=0.0 ):
			day, hour,minute,second = mxDateTimeDelta_DT._normalise(
				[0,hour,minute,second]
			)
			hour = hour % 24
			return hour, minute, second
		if cls.check( value ):
			return value
		elif isinstance( value, RelativeDateTime ):
			# create new with just time-of-day values
			hour, minute,second = normalise( value.hour, value.minute, value.second )
		elif isinstance( value, (str,unicode)):
			hour, minute,second = normalise( **cls.parse( value ))
		elif isinstance( value, (tuple, list)):
			# new RDT from:
			# up to 4 values, hour, minute, second, millisecond
			hour, minute, second, millisecond = list(value) + [0,0,0,0][len(value):]
			if millisecond:
				second = second + (millisecond/1000.0)
			hour, minute,second = normalise( hour, minute, second )
		elif isinstance( value, (float,int,long)):
			# interpreted as an hour value (can include fractions)
			hour, minute,second = normalise( value )
		else:
			try:
				DT = mxDateTime_DT.coerce( value )
				hour, minute,second = normalise( DT.hour, DT.minute, DT.second )
			except TypeError:
				raise TypeError(
					"""Unable to extract a time-of-day from value %r"""%(value)
				)
		# almost every path gets here...
		return cls(
			hour = hour,
			minute= minute,
			second = second
		)

	coerce = classmethod( coerce )
	def format( cls, value ):
		"""Format as a string which is back-coercable"""
		result = []
		for (attr,fmt,always) in (('hour','%02i',1),('minute','%02i',1)):
			v = getattr( value, attr )
			if v or always:
				result.append( fmt%(v or 0) )
		if value.second:
			if value.second < 10.0:
				result.append( '0'+str(value.second))
			else:
				result.append( str(value.second) )
		return ":".join( result )
	format = classmethod( format )
