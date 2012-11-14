from xml.sax import saxutils
import locale
defaultEncoding = locale.getdefaultlocale()[-1]

class Generator( saxutils.XMLGenerator ):
	"""Friendly generator for XML code"""
	def __init__( self, out=None, encoding="utf-8"):
		"""Initialise the generator

		Just overrides the default encoding of the base-class
		"""
		super( self, Generator ).__init__( file, encoding )
	def startElement( self, name, attributes=None ):
		"""Start a new element with given attributes"""
		super(Generator,self).startElement( name, self._fixAttributes(attributes) )
	def _fixAttributes( self, attributes=None ):
		"""Fix an attribute-set to be all unicode strings"""
		if attributes is None:
			attributes = {}
		for key,value in attributes.items():
			if not isinstance( value, (str,unicode)):
				attributes[key] = unicode( value )
			elif isinstance( value, str ):
				attributes[key] = value.decode( defaultEncoding )


class Store( Generator ):
	"""Store a set of objects to an XML representation"""
	def __init__( self, *arguments, **named ):
		"""Initialise the store"""
		super( Store, self ).__init__( *arguments, **named )
		self.classMapping = {
		}
		self.rClassMapping = {
		}
		self.todo = []
		self.alreadyDone = {}
	def classToElementName( self, classObject ):
		"""Get the element name for a given object"""
		name = classObject.__name__
		if self.rClassMapping.has_key( name ):
			return self.rClassMapping.get( name )
		short = name.split('.')[-1]
		count = 2
		while self.classMapping.has_key( short ):
			short = short + str(count)
			count += 1
		self.classMapping[ short ] = name
		self.rClassMapping[ name ] = short
		return short
	def encodeInAttributes( self, property, client ):
		"""Determine whether to encode this property as an element attribute"""
	def handleObject( self, object ):
		"""Produce code for a single object"""
		
