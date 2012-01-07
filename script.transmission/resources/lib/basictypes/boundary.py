"""Boundary objects for checking data values

You use a boundary object by passing a sequence of boundaries
in to a BasicProperty as the keyword argument "boundaries".
Boundaries must conform to the interface described by the
Boundary class, but do not necessarily need to be derived from
them.  For instance, if you would like to define boundaries
as functions or methods, feel free.

The Boundary will always be called with all three arguments
from BasicProperty, the allowance for property or client being
None is just a convenience if you want to re-use the boundary
checking code.

NOTE:
	The API for Boundary objects changed the order of the
	arguments in version 0.6.2!  If you were somehow using
	Boundary objects before this you *must* change your code
	to use the new API!
"""
NULL = []
from basictypes import latebind

class Boundary(object):
	"""Base class from which boundary conditions should be derived"""
	def __call__(self, value, property=None, client=None):
		"""Check value against boundary conditions

		Your boundary should override this method, check the value
		and raise appropriate BoundaryError's if the value is
		outside of bounds
		"""

class Type(Boundary):
	"""Restrict the type of the value to a subclass of a boundary type (or types)

	Type provides a way of checking that a value
	is an instance of a particular type, or one of a set of
	types.  Objects are within the boundary if:
		isinstance( object, boundaryTypes )
	"""
	__resolved = 0
	def __init__(self, boundaryType):
		"""Initialize the Type object with a boundaryType specifier

		The boundaryType specifier can be any of the following:

			string -- dotted-name specifying the full class name
				(including module) for a single class/type
				for example "wxPython.wx.wxFramePtr"

				This specification allows for late-binding of the
				data type, which avoids mutual import problems in certain
				situations.

				Note: if this specification is used, the type boundary
				may raise BoundaryTypeError exceptions on the first
				__call__ of the Boundary when the attempt is made
				to import the class/type.

			class -- a single class/type object,
				for example str or wxPython.wx.wxFramePtr

			tuple -- a tuple of class/type objects,
				for example ( str, list, tuple, unicode ) or
				string specifiers (as above)
		"""
		self.boundaryType = boundaryType
	def __repr__( self ):
		return """<Type(Boundary): type=%s>"""%(self.boundaryType,)
	def __call__(self, value, property=None, client=None):
		"""Check value against boundary conditions"""
		if not self.__resolved:
			self.boundaryType = self.resolveBoundary( self.boundaryType, property, client, value )
			self.__resolved = 1
		if not isinstance(value, self.boundaryType):
			raise BoundaryTypeError(
				property, self, client, value,
				"Value %s was not of required type %s"%( repr(value), self.boundaryType)
			)
	def resolveBoundary( self, boundarySpecifier, property, client, value ):
		"""Resolve a particular boundary specifier into a boundary class"""
		try:
			return latebind.bind( boundarySpecifier )
		except (ImportError, AttributeError):
			raise BoundaryTypeError(
				property, self, client, value,
				"Class/type %s could not be imported"""%(boundarySpecifier,)
			)

class Range(Boundary):
	"""Restrict the value to between/above/below boundary minimum and/or maximum values

	The Range allows you to constrain values based on
	comparisons with minimum and/or maximum values.  The class
	allows for specifying one or both of the boundary conditions.

	Note: minimum and maximum are included in the set of valid values

	Note: although the obvious use for Range boundaries is for
	simple data types (integers, floats, strings), there is nothing
	in the Boundary itself which restricts the use to simple data
	types.  All that is required is the ability to compare instances
	using the < and > operators
	"""
	def __init__(self, minimum = NULL, maximum = NULL):
		"""Specify minimum and/or maximum, if one or both is left off, that bound is not checked

		Note: minimum and maximum are included in the set of valid values
		(i.e. the range is inclusive of the end points)
		"""
		self.minimum = minimum
		self.maximum = maximum
	def __repr__( self ):
		return """<Range(Boundary): min=%s max=%s>"""%(repr(self.minimum), repr(self.maximum))
	def __call__(self, value, property=None, client=None):
		"""Check value against boundary conditions"""
		if self.minimum is not NULL and value < self.minimum:
			raise BoundaryValueError(
				property, self, client, value,
				"Value was < minimum"
			)
		if self.maximum is not NULL and value > self.maximum:
			raise BoundaryValueError(
				property, self, client, value,
				"Value was > maximum"
			)

class Function( Boundary ):
	"""Boundary where function( value ) must return given value"""
	TRUE_VALUES = []
	FALSE_VALUES = []
	def __init__(self, function, required=TRUE_VALUES):
		"""Specify the function, and the required result to pass the test
		
		function -- the boundary function, taking a single value as parameter
		required -- if Function.TRUE_VALUES, test is that the value returned
			from function is "true" in the Python sense, 
			if Function.FALSE_VALUES, test for "falseness" in Python sense,
			otherwise, require that result value be == to required to pass 
		"""
		self.function = function
		self.required = required 
	def __call__(self, value, property=None, client=None):
		"""Check value against boundary conditions"""
		result = self.function( value )
		if self.required is self.TRUE_VALUES:
			if not result:
				raise BoundaryValueError(
					property, self, client, value,
					"%s(%s) gave false value, required a true value"%(
						getattr(self.function, '__name__', self.function), 
						repr(value)[:50],
					)
				)
		elif self.required is self.FALSE_VALUES:
			if result:
				raise BoundaryValueError(
					property, self, client, value,
					"%s(%s) gave true value, required a false value"%(
						getattr(self.function, '__name__', self.function), 
						repr(value)[:50],
					)
				)
		elif self.required != result:
			raise BoundaryValueError(
				property, self, client, value,
				"%s(%s) gave value different from required value %r"%(
					getattr(self.function, '__name__', self.function), 
					repr(value)[:50],
					self.required,
				)
			)
		

class Length( Boundary ):
	"""Restrict the length of value to between/above/below boundary minimum and/or maximum lengths

	Conceptually, Length boundary is a very minor sub-class of
	Range, where the result of passing the value to
	a function (in this case len) is compared with the boundary
	values, rather then the initial value.  This implementation
	doesn't currently take advantage of this abstraction.
	"""
	def __init__(self, minimum = NULL, maximum = NULL):
		"""Specify minimum and/or maximum, if one or both is left off, that bound is not checked"""
		self.minimum = minimum
		self.maximum = maximum
	def __repr__( self ):
		return """<Length(Boundary): min=%s max=%s>"""%(self.minimum, self.maximum)
	def __call__(self, value, property=None, client=None):
		"""Check value against boundary conditions"""
		length = len(value)
		if self.minimum is not NULL and length < self.minimum:
			raise BoundaryValueError(
				property, self, client, value,
				"Value was shorter than minimum, length == %s"%(len(value))
			)
		if self.maximum is not NULL and length > self.maximum:
			raise BoundaryValueError(
				property, self, client, value,
				"Value was longer than maximum, length == %s"%(len(value))
			)

class NotNull( Boundary ):
	"""Require that value evaluate to true (non-null)
	"""
	def __call__(self, value, property=None, client=None):
		"""Check value against boundary conditions"""
		if not value:
			raise BoundaryValueError(
				property, self, client, value,
				"""Value was "null" (evaluates as false)"""
			)

class ForEach( Boundary ):
	"""For iterable objects, checks a given boundary for each item in object

	The ForEach boundary is used to apply another Boundary
	object to each object in an iterable value.  This allows you
	to define checks such as this:

		constraints = [
			Type( list ),
			ForEach( Type( int )),
			ForEach( Range( min=0, max=100 )),
		]

	which would require that the property value be a list of
	integers from 0 to 100 (inclusive).
	"""
	def __init__(self, base):
		self.base = base
	def __repr__( self ):
		return """<ForItemInList %s>"""%( repr(self.base))
	def __call__(self, value, property=None, client=None):
		"""Check each item in value against base boundary condition"""
		try:
			index = 0
			for item in value:
				self.base( item, property, client )
				index = index + 1
		except BoundaryError, error:
			error.boundary = self
			error.message = error.message + """ (Offending element was %s (index %s))"""%(item,index)
			error.index = index
			error.value = value
			raise error
			


class BoundaryError:
	"""Base class for all Boundary exceptions

	This class keeps references to the objects involved in the
	transgression of the boundary.  This allows for higher level
	systems (such as a GUI application) to provide interactive
	support for fixing the boundary transgression.
	"""
	index = None
	def __init__( self, property, boundary, client, value, message="" ):
		"""Initialize the error, just stores the references to minimize overhead where the error isn't actually needed"""
		self.property, self.boundary, self.client, self.value, self.message = property, boundary, client, value, message
	def __repr__( self ):
		"""Get a short user-friendly representation of the error"""
		return """%s val=%s type=%s prop=%s bound=%s obj=%s msg=%s"""%(
			self.__class__.__name__,
			repr( self.value ),
			type(self.value),
			self.property,
			self.boundary,
			self.client,
			self.message,
		)
	def __str__( self ):
		"""Get a full user-friendly string representation of the error"""
		return """%s: value %s (type %s) for property %s failed boundary check %s for object %s with message %s"""%(
			self.__class__.__name__,
			repr( self.value ),
			repr( type(self.value)),
			self.property,
			self.boundary,
			self.client,
			self.message,
		)
class BoundaryTypeError( BoundaryError, TypeError ):
	"""A Boundary object which checks data type found a non-conforming value/type

	This error is primarily raised by the TypeBoundary class.
	
	It can be caught explicitly, or as a TypeError, depending
	on your application's requirements.
	"""

class BoundaryValueError( BoundaryError, ValueError ):
	"""A Boundary object which checks data value found a non-conforming value

	This error is raised by most Boundary classes.

	It can be caught explicitly, or as a TypeError, depending
	on your application's requirements.
	"""
	
