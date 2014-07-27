"""Stand-alone type-definition objects for basic data types

Rather than add class-methods to the built-in data types
module designs stand in datatypes which can be used to
define basicproperty property classes.
"""
from basictypes import latebind, datatypedefinition, registry, booleanfix
import types, traceback

class Object_DT( datatypedefinition.BaseType_DT ):
	"""Generic "object" data-type
	"""
	dataType = 'object'
	baseType = object
	def coerce(cls, value):
		"""Coerce value to the appropriate data type"""
		if cls.check( value):
			return value
		raise TypeError( """Don't know how to convert %r to a %s"""%( value, cls.dataType))
	coerce = classmethod( coerce )

registry.registerDT( object, Object_DT )
class String_DT( datatypedefinition.BaseType_DT ):
	"""String (Unicode) data-type specifier"""
	dataType = "str"
	baseType = unicode
	def coerce(cls, value):
		"""Coerce value to Unicode value

		Accepted values:
			None -- u""
			str instance -- value.decode()
			int,float,long,complex -- unicode(value)
		"""
		if cls.check( value ):
			return value
		if value is None:
			return u""
		if isinstance( value, str ):
			value = value.decode()
		if isinstance( value, (int, float, long, complex)):
			value = unicode( value)
		### XXX Should be raising an error here!
		return value
	coerce = classmethod( coerce )
registry.registerDT( unicode, String_DT )
class Numeric_DT( datatypedefinition.BaseType_DT ):
	def coerce(cls, value):
		"""Coerce value to Numeric value (using baseType)

		Accepted values:
			"", "0" -- 0
			numeric values
			ascii strings -- base type attempts to interpret
		"""
		if cls.check( value):
			return value
		try:
			if value in ("0.0","0"):
				value = 0
		except TypeError, err:
			# something which doesn't return integer on comparison
			# such as a pg_numeric data-type
			pass
		try:
			return cls.baseType(value)
		except Exception, err:
			# is this potentially a floating-point-formatted long or int?
			try:
				test = float(value)
				newValue = cls.baseType(round(test,0))
			except Exception:
				raise ValueError( """Fail: Coerce %r -> %r: %s"""%(
					value, cls.dataType, err,
				))
			else:
				if test == newValue:
					return newValue
				else:
					raise ValueError( """Fail: Coerce %r -> %s: Data loss would occur"""%( test, cls.dataType))
	coerce = classmethod( coerce )
	
class Int_DT( Numeric_DT ):
	"""Integer data-type specifier"""
	dataType = "int"
	baseType = int
registry.registerDT( int, Int_DT )
class Float_DT( Numeric_DT ):
	"""Integer data-type specifier"""
	dataType = "float"
	baseType = float
registry.registerDT( float, Float_DT )
class Long_DT( Numeric_DT ):
	"""Long-integer data-type specifier"""
	dataType = "long"
	baseType = long
registry.registerDT( long, Long_DT )
class Boolean_DT( datatypedefinition.BaseType_DT ):
	"""Boolean-integer data-type specifier"""
	dataType = 'bool'
	falseValues = (
		0,
		None,
		'0',
		'zero',
		'null',
		'none',
		'false',
		'f',
		'no',
		'',
	)
	baseType = booleanfix.bool
	def coerce(cls, value):
		"""Coerce value to Boolean value

		Accepted Values:
			(any value in self.falseValues) -- False
			__nonzero__ False -- False
			otherwise True
		"""
		# interpret as a Boolean...
		if cls.check( value ):
			return value
		test = value
		if type(value) in (str, unicode):
			test = str(test.lower())
		if test in cls.falseValues:
			return booleanfix.False
		elif not test:
			return booleanfix.False
		else:
			return booleanfix.True
	coerce = classmethod( coerce )
	def check( cls, value ):
		"""Determine whether value conforms to definition"""
		if not isinstance( value, cls.baseType ):
			return 0
		if value not in (booleanfix.False,booleanfix.True):
			return 0
		return 1
	check = classmethod( check )
try:
	registry.registerDT( bool, Boolean_DT )
except NameError:
	pass
registry.registerDT( booleanfix.bool, Boolean_DT )

class StringLocale_DT( datatypedefinition.BaseType_DT ):
	"""String data-type specifier"""
	dataType = "str.locale"
	baseType = str
	def coerce(cls, value):
		"""Coerce the value to string (true string) value

		Acceptable Values:
			Unicode -- value.encode()
			None --  ""
			integer, float, long, complex -- str(value)
		"""
		if cls.check( value ):
			return value
		if value is None:
			return ""
		if isinstance( value, unicode ):
			value = value.encode()
		if isinstance( value, (int, float, long, complex)):
			value = str( value)
		return value
	coerce = classmethod( coerce )
registry.registerDT( str, StringLocale_DT )

class ClassName_DT( datatypedefinition.BaseType_DT ):
	"""Class-name data-type specifier"""
	dataType = 'str.classname'
	baseType = str
	def coerce( cls, value ):
		"""Coerce to a string

		Acceptable Values:
			class name (string or Unicode, Unicode will be encoded)
			class object (with __module__ and __name__)
		"""
		if cls.check( value ):
			return value
		if hasattr( value, "__module__") and hasattr(value, "__name__"):
			return ".".join( (value.__module__, value.__name__))
		elif isinstance( value, str ):
			return value
		elif isinstance( value, unicode):
			return value.encode()
		else:
			raise ValueError( """Unable to convert value %r to a class specifier"""%(value))
	coerce = classmethod( coerce )

class Class_DT( datatypedefinition.BaseType_DT ):
	"""Class-object data-type specifier"""
	dataType = 'class'
	baseType = (
		type,
		types.ClassType,
		types.FunctionType,
		types.MethodType,
		types.BuiltinFunctionType,
		types.BuiltinMethodType,
		types.InstanceType,
		types.LambdaType,
		types.UnboundMethodType,
	)
	def coerce( cls, value ):
		"""Coerce to a class

		Acceptable Values:
			Unicode/string class name
			a class
		"""
		if cls.check( value ):
			return value
		if isinstance( value, unicode ):
			value = str(value)
		if isinstance( value, str):
			try:
				return latebind.bind( value )
			except ImportError, error:
				raise ValueError(
					"""ImportError loading class %r: %s"""%(
						value, error
					)
				)
				
			except Exception, error:
				traceback.print_exc()
				raise ValueError(
					"""%s loading class from specifier %r: %s"""%(
						error.__class__.__name__, value, error,
					)
				)
		else:
			raise TypeError( """Unable to convert value %s (%s) to a class"""%(value, ))
	coerce = classmethod( coerce )
##	def factories( cls ):
##		"""Determine a sequence of factory objects"""
##		return [_classFactory]
##	factories = classmethod( factories )
##
##def _classFactory( ):
##	"""Create a new default class object"""
##	return type( "", (object,), {} )
	

class List_DT( datatypedefinition.BaseType_DT ):
	"""List-of-objects data-type (no coercion of items)

	Conceptually this is a listof_objects, but that would
	make an inefficient type for such a common datatype.
	"""
	baseType = list
	def coerce(cls, value ):
		"""Attempt to coerce the value to a list

		Strings and unicode values are converted to
		[ value ].  Anything else which can be processed with
		list( value ) is, everything else raises errors
		when list(value) is called.
		"""
		if cls.check( value ):
			return value
		if isinstance( value, (str,unicode)):
			value = [value]
		value = list(value)
		return value
	coerce = classmethod( coerce )
registry.registerDT( list, List_DT )
	
