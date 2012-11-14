"""This belongs over in basicproperty/basictypes, obviously"""
class RestrictedString( unicode ):
	"""Data-type definition for a string with restricted contents
	
	ACCEPTED_CHARACTERS -- set of (unicode) characters accepted by
		the string-type 
	REPLACE_CHARACTER -- character with which to replace unaccepted
		characters (*must* be in ACCEPTED_CHARACTERS!)
	"""
	ACCEPTED_CHARACTERS = u''
	REPLACE_CHARACTER = u''
	def __new__( cls, value ):
		"""Initialise the restricted string/unicode value"""
		if isinstance( value, unicode ):
			cleaned = cls.clean( value )
			return super(RestrictedString,cls).__new__( cls, cleaned )
		else:
			return cls.coerce( value )
	def coerce( cls, value ):
		"""Coerce the value to the correct data-type"""
		# first get a unicode value...
		if value is None:
			value = u""
		if isinstance( value, str ):
			value = value.decode( ) # default encoding must be set...
		if isinstance( value, (int,float,long)):
			value = unicode( value )
		if not isinstance( value, unicode ):
			raise TypeError( """Don't know how to convert a %r instance (%r) to a restricted unicode value"""%(
				type(value), value,
			))
		return cls( cls.clean( value ))
	coerce = classmethod( coerce )
	def clean( cls, value ):
		"""Return only those characters in value in ACCEPTED_CHARACTERS"""
		result = []
		for x in value:
			if x in cls.ACCEPTED_CHARACTERS:
				result.append( x )
			else:
				result.append( cls.REPLACE_CHARACTER )
		return u"".join( result )
	clean = classmethod( clean )

if __name__ == "__main__":
	from basicproperty import common, propertied, basic
	class Test( RestrictedString ):
		ACCEPTED_CHARACTERS = (
			'tis' +
			"' ."
		).decode( 'latin-1' )
	class Test2( Test ):
		REPLACE_CHARACTER = ' '
	
	class PTest( propertied.Propertied ):
		value = basic.BasicProperty(
			"value", """Testing value""",
			baseType = Test2,
		)
	t = Test( 'this\tand that' )
	print t
	t = Test2( 'this\tand that' )
	print t
	c = PTest( value = 'this\tand that' )
	print c.value
	c = PTest( value = '2322.5' )
	print c.value
