"""Interface/base class for data type definitions"""

class DataTypeDefinition( object ):
	"""Interface for explicit data type definitions

	The data-type definition allows for creating
	stand-alone mechanisms for annotating a
	particular type without actually modifying the
	type itself.

	The API for the DataTypeDefinition can easily
	be implemented for new classes, but it is
	desirable to allow, for instance, built-in
	and extension classes to be annotated without
	requiring explicit support in those classes
	for basictypes.

	dataType "" -- required dotted-string identifier for data-type
	coerce( cls, value ) -- coerce loose value to type
	check( cls, value ) -- strict check for conformance
	factories( cls ) -- list of factory objects for the type
	commonValues( cls ) -- list of common values for the type
	format( cls, value ) -- get a coercable representation of value
	"""
	def coerce(cls, value):
		"""Coerce value to the appropriate data type

		This is a method for "fuzzy" conversion of values,
		and it should be fairly forgiving.  With that said,
		it should not be so forgiving that will allow user
		errors to be ignored.
		"""
		if cls.check( value ):
			return value
		raise TypeError ("""Value %r is not appropriate for data type %s"""%(value, self))
	coerce = classmethod(coerce)
	def factories( cls ):
		"""Determine a sequence of factory objects

		Factory objects are used to generate new instances
		conforming to this definition.  For many datatypes
		this is simply the class itself.  For others,
		it is the list of all sub-classes, or all
		specifically-registered sub-classes, or something
		entirely different.

		XXX The factory object's API has not yet been determined
		"""
		return ()
	factories = classmethod(factories)
	def check( cls, value ):
		"""Determine whether value conforms to definition

		This method is used to determine whether a particular
		value conforms to this definition.  This is a strict
		check, that is, it should return false if the value is
		in any way non-conformant, so that coercian can be
		attempted.

		Note:
			Must be callable as definition.check( value ), which
			requires classmethods for class-based definitions.

		Note:
			Because this method is called from coerce and from
			basicproperty objects, it should be as minimal as
			possible to avoid the possibility of infinite
			recursion errors.
		"""
		return 1
	check = classmethod(check)

class BaseType_DT( DataTypeDefinition ):
	"""Abstract base DataTypeDefinition w/ "defer-to-base" implementation
	"""
	baseType = None
	def check( cls, value ):
		"""Determine whether value conforms to definition"""
		if not isinstance( value, cls.baseType ):
			return 0
		return 1
	check = classmethod( check )
	def factories( cls ):
		"""Determine a sequence of factory objects"""
		if callable( cls.baseType ):
			return [cls.baseType]
		return []
	factories = classmethod( factories )
	def __new__( cls, *args, **named ):
		"""Create a new instance of our base-type"""
		return cls.baseType( *args, **named )
