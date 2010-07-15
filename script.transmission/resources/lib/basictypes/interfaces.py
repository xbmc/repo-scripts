"""Interfaces for basictypes and basicproperty

XXX Should we do adapters from basicproperty objects to
	zope schema field objects?
"""
from zope.interface import Interface, Attribute

### Really generic interfaces...
class IName( Interface ):
	"""Provide a generic name for an object"""
	name = Attribute (
		"name",
		"""Provides an internal name for an object, may be
		used for user interface, but this is of secondary
		importance to internal use.  Should be, as much as
		possible, a valid name in most programming contexts.
		""",
	)
class IFriendlyName( Interface):
	"""Provide a friendly name for an object"""
	friendlyName = Attribute (
		"friendlyName",
		"""user-friendly name for use in UIs and the like,
		defaults to the current value of name""",
	)
class IPyName( Interface):
	"""Object providing a generic name as __name__"""
	__name__ = Attribute (
		"__name__",
		"""Provides an internal name for an object, may be
		used for user interface, but this is of secondary
		importance to internal use.  Should be, as much as
		possible, a valid name in most programming contexts.
		""",
	)
class IPyDocumented(Interface):
	"""Object providing documentation strings"""
	__doc__ = Attribute (
		"__doc__", """Documentation string for the object""",
	)

class ICloneProperties(Interface):
	"""Live-object duplication mechanism with property substitution"""
	def clone( **newValues ):
		"""Clone the object, with (optional) new property values
		"""
	

### General DataTypeDefinition interfaces
class ITypeCoercion( Interface ):
	"""Convert/coerce a value to instance of type"""
	def coerce( value ):
		"""Coerce value to the appropriate data type

		This is a method for "fuzzy" conversion of values,
		and it should be fairly forgiving.  With that said,
		it should not be so forgiving that will allow user
		errors to be ignored.
		"""
class ITypeCheck( Interface ):
	"""Interface checking whether value is proper instance of type"""
	def check (value):
		"""Determine whether value value is proper instance of type

		This method is used to determine whether a particular
		value conforms to this type's restrictions.  This is
		a strict check, that is, it should return false if
		the value is in any way non-conformant, so that
		coercian can be attempted.
		"""
class ITypeFactories(Interface):
	"""Interface providing factory instances for a given type"""
	def factories( ):
		"""Determine a sequence of factory objects for type

		Factory objects are used to generate new instances
		conforming to this definition.  For many datatypes
		this is simply the class itself.  For others,
		it is the list of all sub-classes, or all
		specifically-registered sub-classes, or something
		entirely different.
		"""

class IDataTypeDeclaration (Interface):
	"""Object provides a dataType compatible with wxoo"""
	dataType = Attribute ("dataType","""The string data type specifier

	The specifier is used throughout wxoo to identify
	an abstract data type for processing.
	""")

class ITypeBaseType (Interface):
	"""Objects with base data types for dependent objects"""
	baseType = Attribute (
		"baseType","""A type or type-like object providing type-like services""",
	)
	

### Propertied object interfaces
class ITypeProperties(Interface):
	"""Allows retrieval of property-set for a type"""
	def getProperties( ):
		"""Get the properties for the type"""
	
### Callable-object interfaces
class ICallableArgument( IName ):
	"""Describes an argument to a callable object

	Note that ITypeBaseType may be provided by particular
	subclasses to allow for type checking.
	"""
	default = Attribute(
		'default', """Default-value for the argument, may be NULL/unavailable""",
	)
	def __eq__( other ):
		"""Determine whether other is our equivalent

		returns true if other is of the same class, with
		the same primary attributes
		"""

class ICallable (IName):
	"""Describes and provides access to a callable object"""
	name = Attribute(
		'name', """The callable-object's name""",
	)
	arguments = Attribute(
		'arguments', """Argument-list for the callable object""",
	)
	shortHelp = Attribute(
		'shortHelp', """Short help-string suitable for tooltips/status-bars""",
	)
	longHelp = Attribute(
		'longHelp', """Longer help-string suitable for context-sensitive help""",
	)
	coerce = Attribute(
		"coerce","""Whether to coerce arguments if possible""",
	)
	def __init__(
		implementation, name=None,
		arguments=None,
		shortHelp = None, longHelp=None,
		**named
	):
		"""Initialize the Callable object

		implementation -- a callable python object
		name -- if provided, will override the given name
		arguments -- if provided, will override calculated arguments
		shortHelp -- short help-string, first line of __doc__ if not given
		longHelp -- long help-string, entire __doc__ string if not given
		"""
	def __call__( *arguments, **named ):
		"""Do the actual calling of the callable object"""
	def getArgument( name ):
		"""Retieve an argument-wrapper object by name"""

### Boundary-related interfaces
class IBoundary (Interface):
	"""A boundary object for checking a value"""
	def __call__( value, client = None, property = None ):
		"""Check value against boundary conditions

		Raises BoundaryError exceptions if the value
		is not within the bounds defined by the boundary.
		"""
class IBoundaryError (Interface):
	"""Provides rich information about a boundary error"""
	def __init__( property, boundary, client, value, message="" ):
		"""Initialize the error with data values"""
	property = Attribute ("property","""The property passed to the boundary's __call__ method""")
	boundary = Attribute ("boundary","""The boundary object raising the exception""")
	client = Attribute ("client","""The client passed to the boundary's __call__ method""")
	value = Attribute ("value","""The value which failed the boundary check""")
	message = Attribute ("message","""Human-friendly string describing the error""")
	
### XXX Enumeration-related interfaces, when we get those sorted out
### Property-related interfaces...
class IPropertyDefaults(Interface):
	"""Property interface providing default-value semantics"""
	setDefaultOnGet = Attribute (
		"setDefaultOnGet",
		"""if true (default), then retrieving a
		default value causes the value to be explicitly set as the
		current value""",
	)
	default = Attribute (
		"default",
		"""If present, an IPropertyDefaultHolder object returning an object
		to be used as the default for the property""",
	)
class IPropertyDefaultHolder(Interface):
	"""Callable-object producing a default value for property"""
	def __call__( property, client ):
		"""Return the appropriate default value"""

class IProperty(Interface):
	"""High-level functionality of BasicProperty-like objects"""
	name = Attribute (
		"name","""name of the property, used for storage and reporting""",
	)
	trueProperty = Attribute (
		"trueProperty",
		"""if true, this property really does describe a
		property, that is, a descriptor for an attribute which is
		accessed using object.x notation.
		
		if false, this property is used to interact with the
		property system, but is not actually a property of an
		object (for instance when the object is an old-style class
		which cannot support properties, you can define virtual
		properties for use with the class)  The property system
		can examine the value of trueProperty to determine whether
		to use setattr(object,name,value) or call
		property.__set__(object, value) to use the property.""",
	)
			
	def __get__( client, klass=None ):
		"""Retrieve the current value of the property for the client

		Performs coercion and retrieval of the property value
		from the client, including potential default-value
		retrieval.
		"""
	def __set__( client, value ):
		"""Set the current value of the property for the client

		Perform coercion and storage of the property value
		for the client.  Returns the actual value set (which
		may be different than the passed value).
		"""
	def __delete__( client ):
		"""Delete the current value of the property for the client
		"""
class IPropertyPickle (Interface):
	"""Provide pickle support to retrieve/set property values"""
	def getState( client ):
		"""Helper for client.__getstate__, gets storable value for this property"""
	def setState( client, value ):
		"""Helper for client.__setstate__, sets storable value"""
class IPropertyMethodStore(Interface):
	"""Objects using client methods for data storage/retrieval"""
	setMethod = Attribute (
		"setMethod","""Method name used to set the data value on client""",
	)
	getMethod = Attribute (
		"getMethod","""Method name used to get the data value from the client""",
	)
	delMethod = Attribute (
		"delMethod","""Method name used to delete the data value from the client""",
	)

class IPropertyReadOnly(Interface):
	"""Read-only flags for Property-like objects"""
	readOnly = Attribute(
		'readOnly', """If true, disallow editing of the property through the property editors (doesn't change the underlying property's capabilities, just prevents changes through the property editors)""",
	)
