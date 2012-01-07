"""Preliminary callable-object modelling classes"""
from basicproperty import propertied, basic, common
import inspect
from basictypes import list_types

__NULL__ = []

class Argument( propertied.Propertied ):
	"""Representation of a single argument on a callable object"""
	name = common.StringLocaleProperty(
		'name', """The argument's name, as a simple string""",
	)
	default = basic.BasicProperty(
		'default', """Default-value for the argument, may be NULL/unavailable""",
	)
	baseType = basic.BasicProperty(
		'baseType', """Base data-type for the argument, may be NULL/unavailable""",
	)
	def __init__(self, name, default =__NULL__, baseType=__NULL__, **named):
		"""Initialize the Callable object

		name -- the argument name
		default -- if provided, will provide the default value
			for the argument
		baseType -- if provided, will allow for type checking
			and coercion of arguments before calling the callable
			object.
		"""
		if default is not __NULL__:
			named ["default"] = default
		if baseType is not __NULL__:
			named ["baseType"] = baseType
		super (Argument, self).__init__(
			name = name,
			**named
		)
	def __str__(self,):
		"""Create a friendly string representation"""
		fragments = [repr(self.name)]
		if hasattr( self, "default"):
			fragments.append (repr(self.default))
		if hasattr( self, "baseType"):
			fragments.append (repr(self.baseType))
		return """%s(%s)"""%(
			self.__class__.__name__,
			", ".join(fragments),
		)
	__repr__=__str__
	def __eq__( self, other ):
		"""Determine whether other is our equivalent

		returns true if other is of the same class, with
		the same primary attributes
		"""
		if self.__class__ is not other.__class__:
			return 0
		NULL = []
		for nm in ['name','default','baseType']:
			if hasattr( self, nm) and not hasattr( other, nm):
				return 0
			elif not hasattr( self, nm) and hasattr( other, nm):
				return 0
			elif hasattr( self, nm ):
				if getattr( self, nm) != getattr(other,nm):
					return 0
		return 1

	### Data-type API
	def check( cls, value ):
		"""Strict check to see if value is an instance of cls"""
		return isinstance( value, cls)
	check = classmethod(check)
	def coerce( cls, value ):
		"""Coerce value to a cls instance

		Accepted forms:
			("name",)
			("name",default)
			("name",default,baseType)
			"name"
			{ ** } # passed to the initialiser
		"""
		if cls.check( value ):
			return value
		if isinstance( value, (tuple, list)) and value and len(value) < 4:
			items = {}
			for item,name in zip(value,['name','default','baseType'][:len(value)]):
				items[name] = item
			return cls( **items )
		elif isinstance( value, str ):
			return cls( name = value )
		elif isinstance( value, dict ):
			return cls( **value )
		raise TypeError( """Don't know how to convert %r to a %s object"""%( value, cls.__name__))
	coerce = classmethod(coerce)

	
listof_Arguments = list_types.listof(
	Argument,
	name = "listof_Arguments",
	dataType = 'list.Arguments',
)

class Callable( propertied.Propertied ):
	"""Modelling of a callable Python object"""
	name = common.StringProperty(
		'name', """The callable object's-name (may be different from underlying object)""",
	)
	implementation = basic.BasicProperty(
		"implementation", """The underlying implementation (callable Python object)""",
	)
	arguments = common.ListProperty(
		'arguments', """Argument-list for the callable object""",
		baseType = listof_Arguments,
	)
	shortHelp = common.StringProperty(
		'shortHelp', """Short help-string suitable for tooltips/status-bars""",
	)
	longHelp = common.StringProperty(
		'longHelp', """Longer help-string suitable for context-sensitive help""",
	)
	coerce = common.BooleanProperty (
		"coerce","""Whether to coerce arguments if possible""",
		defaultValue = 0,
	)
	def __init__(
		self, implementation, name=__NULL__,
		arguments=__NULL__,
		shortHelp = __NULL__, longHelp=__NULL__,
		**named
	):
		"""Initialize the Callable object

		implementation -- a callable python object
		name -- if provided, will override the given name
		arguments -- if provided, will override calculated arguments
		shortHelp -- short help-string, first line of __doc__ if not given
		longHelp -- long help-string, entire __doc__ string if not given
		"""
		if name is __NULL__:
			name = self._name( implementation )
		if arguments is __NULL__:
			arguments = self._arguments (implementation)
		if shortHelp is __NULL__:
			shortHelp = self._shortHelp(implementation)
		if longHelp is __NULL__:
			longHelp = self._longHelp(implementation)
		super (Callable, self).__init__(
			implementation = implementation,
			name = name,
			arguments = arguments,
			**named
		)
	def __str__(self):
		"""Return a friendly string representation"""
		return """%s( %s )"""% (self.__class__.__name__, self.implementation)
	def __call__( self, *arguments, **named ):
		"""Do the actual calling of the callable object"""
		set = {}
		for argument,value in zip(arguments,self.arguments):
			set[argument.name] = (argument,value)
		# XXX potentially there are missing positional arguments!
		if named:
			nameSet = dict([(arg.name,arg) for arg in self.arguments])
			for key,value in named.items():
				if set.has_key( key ):
					raise ValueError("""Redefinition of argument order for argument %s"""%(set.get(key)))
				else:
					# note that argument may be None
					set [key] = nameSet.get(key), value
		for key,(argument,value) in set.items():
			if self.coerce and argument and argument.baseType and hasattr(argument.baseType, "coerce"):
				value = argument.baseType.coerce(argument)
			set[key] = value
		# XXX Should keep arguments in order to allow for *args set :(
		return self.implementation( **set )
	def getArgument( self, name ):
		"""Retieve an argument by name"""
		for argument in self.arguments:
			if argument.name == name:
				return argument
		raise KeyError( """%r object doesn't have a %s argument"""%(self, name))

	def _name( self, value ):
		"""Try to find a decent name for a callable object"""
		name = "<unknown>"
		for attribute in [ '__name__','name','func_name','co_name','__file__',"friendlyName"]:
			if hasattr( value, attribute):
				v = getattr( value, attribute)
				if isinstance( v, (str,unicode)):
					name = v
		if '.' in name:
			return name.split('.')[-1]
		return name

	def _shortHelp( self, value ):
		"""Try to find the short-docstring for an object"""
		if hasattr( value, '__doc__') and value.__doc__:
			return value.__doc__.split( '\n')[0]
		else:
			return ""
	def _longHelp( self, value ):
		"""Try to find the short-docstring for an object"""
		if hasattr( value, '__doc__') and value.__doc__:
			return value.__doc__
		else:
			return ""

	def _useCall( self, value ):
		"""Can we use __call__ to call this object?

		returns true if we should be able to use it
		"""
		return (
			# must have __call__
			hasattr( value, '__call__') and
			(
				# call should be a function or method...
				hasattr( value.__call__, 'im_func') or
				hasattr( value.__call__, 'im_code')
			)
		)

	def _arguments( self, value ):
		"""Get a list of arguments for a callable object"""
		if self._useCall( value ):
			value = value.__call__
		if hasattr(value, 'im_func'):
			# receiver is a method. Drop the first argument, usually 'self'.
			func = value.im_func
			arguments = inspect.getargspec( func )
			if value.im_self is not None:
				# a bound instance or class method
				arguments = inspect.getargspec( func )
				del arguments[0][0]
			else:
				# an un-bound method
				pass
		elif hasattr(value, 'func_code') or hasattr(value, 'im_code'):
			# receiver is a function.
			func = value
			arguments = inspect.getargspec( func )
		else:
			raise ValueError('unknown reciever type %s %s'%(receiver, type(receiver)))
		names, vararg, varnamed, defaults = arguments
		defaults = defaults or ()
		result = [ Argument( name = name ) for name in names ]
		for name,default in zip( names[-len(defaults):],defaults):
			for item in result:
				if item.name == name:
					item.default = default
		return result


	def check( cls, value ):
		"""Strict check to see if value is an instance of cls"""
		return isinstance( value, cls)
	check = classmethod(check)

	def coerce( cls, value ):
		"""Coerce value to a Callable-object"""
		if cls.check( value ):
			return value
		if callable( value ):
			return cls(
				implementation = value,
			)
		else:
			raise TypeError( "Don't know how to convert %r to a %s object"%(
				value, cls.__name__,
			))
	coerce = classmethod(coerce)

	def __eq__( self, other ):
		"""Determine whether other is our equivalent

		returns true if other is of the same class, with
		the same primary attributes
		"""
		if self.__class__ is not other.__class__:
			return 0
		NULL = []
		for nm in ['name','implementation','arguments']:
			if hasattr( self, nm) and not hasattr( other, nm):
				return 0
			elif not hasattr( self, nm) and hasattr( other, nm):
				return 0
			elif hasattr( self, nm ):
				if getattr( self, nm) != getattr(other,nm):
					return 0
		return 1

Callables = list_types.listof(
	Callable,
	name = "Callables",
	dataType = 'list.Callables',
)

		
##class Curry( propertied.Propertied ):
##	"""A curried Callable with particular arguments pre-set"""
##	values = common.DictionaryProperty(
##		"values", """Partial value-set to be applied to callable""",
##	)
##	implementation = basic.BasicProperty(
##		'implementation', """The underlying implementation of the curry""",
##		baseType = callable.Callable,
##	)
##
