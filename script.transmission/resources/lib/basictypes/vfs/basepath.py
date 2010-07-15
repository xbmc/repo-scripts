"""Base-class for file-path strings
"""
import os

class BasePath (str):
	"""Representation of a path in a virtual file system
	
	Interact with the paths in an object-oriented way
	(following are ideas for what to do)
		* Support for standard os and os.path queries
			* listdir
			* isfile/dir/symlink
			* create sub-directory
			* join-with-string to get sub-path
			* absolute-path -> Path object
				* support .. and . directory resolution (and elimination)
		* Mime-types
		* assoc values
		* comparisons
			* parent, child -> boolean
			* shared path -> fragments
			* shared root -> boolean
		* open( *, ** )
			* for directories, create/open file based on standard file() call
			* for zipfile-embedded paths, use zipfile transparently to create/open sub-file
			* for directories, create the directory (possibly recursively)
			* for files, error normally, possibly useful for things
			  like zipfiles and db-interface files which want to provide
			  directory-like interface
		* file( name ) -> Path
			* create a sub-file path
		* sub( name ) -> Path
			* create a sub-directory path
	* Eventually support zipfiles as Directory paths

	XXX Need to raise appropriate exceptions and look at ways to
	reduce overhead beyond the naive implementation of many of the
	methods.

	XXX Need to deal with upcoming switch to unicode values for path
		names on OSes which support them.
	"""
	__slots__ = ()
	def check( cls, value ):
		"""Is the value an instance of this class?"""
		return isinstance( value, BasePath )
	check = classmethod( check )
	def coerce( cls, value ):
		"""Coerce value to an instance of this class"""
		if cls.check( value ):
			return value
		elif isinstance( value, BasePath ):
			return value
		elif isinstance( value, (str, unicode)):
			return cls( value )
		elif isinstance( value, file ) or hasattr( value, 'name'):
			return cls( value.name )
		else:
			raise TypeError( """Unable to coerce value %r to a %s object"""%(
				value, cls.__name__
			))
	coerce = classmethod( coerce )
		
	def __repr__( self ):
		return '%s(%s)'%(self.__class__.__name__, super(BasePath,self).__repr__( ))
	def __eq__( self, other ):
		"""Attempt to determine if we are equal to other__"""
		other = self.__class__.coerce( other )
		return self.canonical() == other.canonical()
	def isParent (self, other):
		"""Return true if we are the parent of the other path

		Other can be a string specifier or a Path object
		"""
		other = self.__class__.coerce( other )
		return other.parent() == self
	def isChild (self, other):
		"""Return true if we are a child of the other path"""
		other = self.__class__.coerce( other )
		return self.parent() == other
	def isAncestor( self, other ):
		"""Return true if we are an ancestor of the other path"""
		other = self.__class__.coerce( other )
		if self.shareRoot( other ):
			for item in self.__class__.coerce(other).parents():
				if item == self:
					return 1
		return 0
	def isDescendent( self, other ):
		"""Return true if we are a descendent of the other path"""
		other = self.__class__.coerce( other )
		return other.isAncestor( self )

	def shareRoot( self, other):
		"""Return true if we are descended from the same root in the file system"""
		other = self.__class__.coerce( other )
		return other.root() == self.root()

	def walk( self, file=None, pre=None, post=None ):
		"""Simple walking method

		For directories:
			pre(path) is called before starting to process each directory
			submember.walk(file,pre,post) is called on each sub-member
			post(path) is called after processing all sub-members of the directory
		For files:
			file( path ) is called for each file in each directory
		"""
		if not file and not pre and not post:
			return
		if self.isFile():
			# what to do about file+directory types?
			if file:
				file(self)
		if self.isDir():
			# is a directory
			if pre:
				pre( self )
			children = self.list()
			for child in children:
				child.walk( file, pre, post )
			if post:
				post( self )

	### virtual methods...
	def isFile( self ):
		"""Return true if we are a file path"""
	def isAbsolute (self):
		"""Return true if this path is an absolute path (i.e. fully specified from a root)"""
	def isRoot( self ):
		"""True iff this object is the root of its filesystem"""
	def baseOnly( self ):
		"""Is this path reachable using only the base file system"""

	def sharedRoot(self, other):
		"""Return the path of the longest shared prefix for ourselves and other"""
	def canonical(self):
		"""Get a canonical version of this path

		The new path will be absolute, expanded,
		case-normalized, normalized, and converted
		to a path of the same type as this one.

		It will include, where required, a pointer
		to the parent-filesystem-path which points
		to this path's root.
		"""
	def join( self, name ):
		"""Create a new Path from this path plus name"""
	def split( self ):
		"""Return our parent path (if available) and our name"""
	# make string split and join available via aliases
	sjoin = str.join
	ssplit = str.split
