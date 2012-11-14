"""Simple Enumeration (choice-from-set) data-type"""
from basicproperty import basic, propertied
from basictypes import basic_types

def defaultFriendly(property, client):
	"""Determine the default friendly name (the name)"""
	return client.name

class EnumerationChoice( propertied.Propertied ):
	"""A particular choice within an enumeration set

	The enumeration choice is a particular choice
	stored within the enumeration set.  Its name
	is used to index the choice within its set, while
	its value is the actual value being enumerated.
	"""
	name = basic.BasicProperty(
		"name","""The internal name/key used to identify the choice""",
		baseType = basic_types.String_DT,
	)
	value = basic.BasicProperty(
		"value","""The data value associated with this choice""",
	)
	friendlyName = basic.BasicProperty(
		"friendlyName","""Friendly name used to describe this choice to users""",
		setDefaultOnGet = 0,
		defaultFunction = defaultFriendly,
		baseType = basic_types.String_DT,
	)
	def __repr__( self ):
		"""Get a code-like representation of this choice"""
		if self.friendlyName != self.name:
			return """%s( name=%r, value=%r, friendlyName=%r)"""%(
				self.__class__.__name__,
				self.name,
				self.value,
				self.friendlyName,
			)
		else:
			return """%s( name=%r, value=%r)"""%(
				self.__class__.__name__,
				self.name,
				self.value,
			)

class EnumerationSet( dict ):
	"""EnumerationSet classes (set from which values may be chosen)

	The struct mimics a C enumeration with
	names mapping to integer values. 

	Note:
		name values must be hashable


	XXX Needed features:
		* ordered sets (e.g. month names)
		* multiple input (name -> value) mappings
		* preferred name-set (value -> name) mappings
		* set-union, difference
	"""
	choiceClass = EnumerationChoice
	def getName( self, value ):
		"""Get the name of a choice whose value matches value or None"""
		for choice in self.values():
			if choice.value == value:
				return choice.name
		return None
	def new( self, **namedarguments ):
		"""Add a new choice to this enumeration

		namedarguments -- passed to self.choiceClass initialiser
		"""
		choice = self.choiceClass( **namedarguments)
		self.append( choice )
		return choice
	def append( self, choice ):
		"""Register a choice with the set"""
		self[choice.name] = choice
	__iter__ = dict.itervalues
	def coerce( cls, value ):
		"""Coerce a value to an enumeration-set value

		Accepted value formats:
			None # empty dictionary/set
			[ stringValue, ... ] # value == name
			{ 'name': value, ... }
			[ (name,value), ... ]
			[ choiceClass(), ... ]
			[ { }, ... ] # arguments for choice-class
		"""
		if cls.check( value ):
			return value
		elif value is None:
			value = ()
		if isinstance( value, dict ):
			value = value.items()
		try:
			set = [ cls.coerceSingle(item) for item in value ]
			return cls(
				[(choice.name,choice) for choice in set]
			)
		except (TypeError, KeyError,ValueError), err:
			raise TypeError( """Couldn't coerce %r to a %s value: %s"""%(value,cls.__name__, err))
	coerce = classmethod( coerce )
	def check( cls, value ):
		"""Check whether item is compatible with this set"""
		return isinstance( value, cls )
	check = classmethod( check )
	def checkSingle( cls, item ):
		"""Check whether item is compatible with this set"""
		return isinstance( item, cls.choiceClass )
	checkSingle = classmethod( checkSingle )
	def coerceSingle( cls, item ):
		"""Coerce an individual value/values to an item

		This doesn't actually add the item, as the cls
		doesn't store such data.

		Accepted formats:
			'key' # str or unicode only, converted to unicode for key
			('key',value)
			{'name':'key','value':value,...} # passed directly to the initialiser
			choiceClass instance
		"""
		if cls.checkSingle( item ):
			return item
		elif isinstance( item, (str,unicode)):
			return cls.choiceClass( name =  item, value=item )
		elif isinstance( item, (tuple,list)) and len(item) == 2:
			if cls.checkSingle( item[1] ):
				return item[1].clone( name = item[0])
			else:
				return cls.choiceClass( name = item[0], value=item[1])
		elif isinstance( item, dict ):
			return cls.choiceClass( **item )
		else:
			raise TypeError( """%r unknown item-type"""%item)
	coerceSingle = classmethod( coerceSingle )
		

class Enumeration (propertied.Propertied):
	"""A choice from an enumerated set of data values

	This class also operates as the base-type for the
	enumeration properties, via the data-type-definition
	API.
	"""
	dataType = "enumeration"
	## set must be class-data, not just instance data
	## should probably be a metaclass property of EnumerationSet type
	set = None
	name = basic.BasicProperty(
		"name", """Data-value choice within one of our sets""",
		defaultValue = "",
		baseType = unicode,
	)
	def __init__( self, name="", *arguments, **named ):
		if not isinstance( name, (str,unicode)):
			name = self.__class__.set.getName( name )
		super( Enumeration, self).__init__( name=name, *arguments, **named )
		if not self.choice():
			raise ValueError( """Name %r is not part of %s"""%(self.name, self.__class__.__name__))
	def choice( self ):
		"""Get the choice object associated with this value or None"""
		return self.set.get( self.name )
	def value( self ):
		"""Get the value associated with this choice"""
		choice = self.choice( )
		if choice is not None:
			return choice.value
		raise ValueError ("""Could not get value for name %r for %s"""%(self.name,self.__class__.__name__))
	def __cmp__( self, other ):
		"""Compare this value to another value"""
		if isinstance( other, Enumeration):
			return cmp( self.value(), other.value())
		else:
			return cmp( self.value(), other )
	def __repr__( self ):
		"""Return a code-like representation of this object"""
		return """%s( name=%r)"""%( self.__class__.__name__, self.name )
	def __str__( self ):
		"""Return the enumeration value as a name"""
		return self.name or self.value()

	### Data-type-definition API
	def check( cls, value ):
		"""Check whether value is of cls type, and has the same set"""
		return isinstance( value, cls ) and cls.set == value.set
	check = classmethod( check )
	def coerce (cls, value):
		"""Coerce a value into an Enumeration value

		Accepted types:
			Enumeration objects
			integers/longs
			([name,name,name],remainder) tuples
			[name,name,name,value] lists (values are |'d together)
		"""
		if cls.check( value ):
			return value
		elif isinstance( value, (str, unicode)):
			return cls.parse( value)
		else:
			return cls.fromValue( value )
	coerce = classmethod( coerce )
	def fromValue( cls, value ):
		"""Create from an integer value"""
		name = cls.set.getName( value )
		if name is None:
			raise ValueError( """Value %r is not part of %s"""%(value, cls.__name__))
		else:
			return cls( name = name )
	fromValue = classmethod( fromValue )

	def parse ( cls, value):
		"""Create from a string value

		Possible formats:
			"coreName"
			"23"
			"friendlyName"
		"""
		value = value.strip ()
		current = cls.set.get( value)
		if current is not None:
			return cls( name = value )
		else:
			return cls.fromValue( value )
	parse = classmethod (parse)

	def allInstances( cls ):
		"""Return cls instances for each of this class's set"""
		items = [
			(choice.friendlyName, cls( name= choice.name))
			for choice in cls.set.values()
		]
		items.sort()
		items = [ v[1] for v in items ]
		return items
	allInstances = classmethod( allInstances )

def new( dataType, names, values ):
	"""Utility function to create a new enumeration set"""
	enum = EnumerationSet.coerce(
		map(None, names, values ),
	)
	enum.dataType = dataType
	return enum


class EnumerationProperty( object ):
	"""Mix-in for Enumeration properties to return/accept enums"""
	def _getValue( self, client ):
		"""Retrieve the current value of the property for the client

		returns an instance of self.baseType if possible
		"""
		raw = super( EnumerationProperty,self)._getValue( client )
		base = self.getBaseType()
		if base:
			return base.fromValue( raw )
		return raw
	def _setValue( self, client, value ):
		"""Set the current value of the property for the client

		accepts instances of self.baseType as well as raw values
		"""
		if isinstance(value, Enumeration ):
			value = value.value()
		return super( EnumerationProperty,self)._setValue( client, value )
##
##try:
##	from wxoo.resources import enumeration32_png, enumeration16_png
##	from wxoo import typeregistry
##except ImportError:
##	pass
##else:
##	typeregistry.TYPEICONSNORMAL.Register( Enumeration, enumeration32_png.getBitmap())
##	typeregistry.TYPEICONSSMALL.Register( Enumeration, enumeration16_png.getBitmap())
##
	