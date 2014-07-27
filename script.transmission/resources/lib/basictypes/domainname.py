"""String sub-class representing a domain name"""

class DomainName( str ):
	"""Domain-name data-type"""
	def __new__( cls, value ):
		"""Create a new DomainName from a (non-null) string value"""
		if not value:
			raise ValueError( """Null domain-name specified""" )
		else:
			return str.__new__( cls, value )
	def check( cls, value ):
		"""Check whether value is a valid domain-name

		Just checks that the value is an instance of the class.
		"""
		if isinstance( value, cls ):
			return 1
		return 0
	check = classmethod( check )
	def coerce( cls, value ):
		"""Coerce value to a string domain-name

		Will accept a string value, a unicode value (encoded to
		utf-8), must be a non-null value.
		"""
		if cls.check( value ):
			return value
		if not isinstance( value, (str,unicode)):
			raise TypeError( """Don't know how to convert %r type %r to a domain name object"""%(
				value, value.__class__,
			))
		if isinstance( value, unicode ):
			value = value.encode( 'utf-8')
		if not value:
			raise ValueError( """Null domain-name %r specified"""%(value,) )
		return cls( value )
	coerce = classmethod( coerce )
