"""Object representing functional union of two types

(wrt. the basictypes/basicproperty type interfaces)
"""

class TypeUnion( tuple ):
	"""An object providing, as much as possible, the union of two types

	The TypeUnion is intended to allow specifying
	baseTypes which are actually 2 or more sub-
	types. The TypeUnion is responsible for
	mediating between the sub-types (for instance
	making sure that items which are instances of
	one type are not arbitrarily converted to
	instances of another).
	"""
	def __new__( cls, *arguments, **named ):
		"""Create a new TypeUnion object

		A class-name will be calculated by cls.createName
		"""
		base = super( TypeUnion, cls).__new__( cls, *arguments, **named )
		base.__name__ = cls.createName( base )
		return base
	def __repr__( self ):
		return self.__name__
	def createName( cls, base ):
		"""Try to create a type-name from base (tuple of sub-types)"""
		set = []
		for typ in base:
			if hasattr( typ, '__name__'):
				set.append( typ.__name__.split('.')[-1] )
			else:
				set.append( str(typ).split('.')[-1])
		return "".join( set )
	createName = classmethod( createName )
	def check( self, value ):
		"""Is the value acceptable as one of our types"""
		for typ in self:
			if hasattr( typ, 'check'):
				if typ.check( value ):
					return 1
			elif isinstance( value, typ ):
				return 1
		return 0
	def coerce( self, value ):
		"""Coerce the value to one of our types"""
		if self.check( value ):
			return value
		best = self.bestMatch( value )
		if best is not None:
			return best.coerce( value )
		else:
			err = None
			for typ in self:
				try:
					return typ.coerce( value )
				except (ValueError,TypeError), err:
					pass
			raise TypeError( """Couldn't convert %r value to any of %r (%s)"""%(
				value, tuple(self), err
			))
	def factories( self ):
		"""Get the default set of factory objects"""
		result = []
		for item in self:
			if hasattr( item, 'factories'):
				result.extend( list(item.factories()))
			elif callable( item ):
				result.append( item )
		return result
	def bestMatch( self, value ):
		"""Find the closest item to value's type

		Defaults to the first item
		"""
		# is value an instance of item or item.baseType?
		for typ in self:
			if isinstance(value,typ) or (
				hasattr( typ,'baseType') and
				isinstance(value, typ.baseType)
			):
				return typ
		# XXX should have meta-data on the types to allow better
		# recovery here
		return None
	