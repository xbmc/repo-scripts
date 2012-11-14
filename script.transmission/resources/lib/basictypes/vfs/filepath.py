"""Spike test for filesystem-path objects


## Create a path representing an existing directory

>>> from filepath import path
>>> p = path( 'c:\\temp' )
>>> p
FileSystemPath('c:\\temp')

## Lists the current contents of the directory

>>> p.list()
[FileSystemPath('c:\\temp\\abook.mab'), FileSystemPath('c:\\temp\\impab.mab'), FileSystemPath('c:\\temp\\test.dat')]

## Create a new path pointing to a non-existent directory

>>> sd = p+'somewhere'
>>> sd.exists()
0

## Create the directory pointed to by our path
>>> sd.createDirectory()
>>> sd.exists()
1

## Get the parent of the path
>>> sd.parent()
FileSystemPath('c:\\temp')

## Compare two different versions of the same path
>>> sd.parent() == p
1

## Explore the hierarchy of parents a little
## note that sd.parent().parent().parent() returns None
## so isn't really fun to look at in an interactive session
>>> sd.parent().parent()
FileSystemPath('c:\\')
>>> sd.root()
FileSystemPath('c:')

## Create a deeply nested directory
>>> deep = sd.join( 'this', 'that', 'those' )
>>> deep.createDirectory()
>>> deep.exists()
1

## Create a path for a file (deep + 'test.txt') also works
>>> f = deep.join( 'test.txt' )
>>> f.open('w').write( 'some text' )
>>> f
FileSystemPath('c:\\temp\\somewhere\\this\\that\\those\\test.txt')
>>> f.exists()
1
>>> f.size()
9L
>>> f.remove()
>>> f.exists()
0
>>> f.open('w').write( 'some text' )

## Remove the entire deeply nested directory
## including files
>>> sd.remove()
>>> f.exists()
0

## Demonstrate walking a path hierarchy with simple callbacks
>>> newDirectories = ["why", "not", "me"]
>>> for directory in newDirectories:
... 	sub = sd+directory
... 	sub.createDirectory ()
... 	(sub + 'test.txt').open('w').write( "hello world!")
... 	
>>> fileList = []
>>> sd.walk( file = fileList.append )
>>> fileList
[FileSystemPath('c:\\temp\\somewhere\\me\\test.txt'), FileSystemPath('c:\\temp\\somewhere\\not\\test.txt'), FileSystemPath('c:\\temp\\somewhere\\why\\test.txt')]
>>> directoryList = []
>>> sd.walk( pre = directoryList.append )
>>> directoryList
[FileSystemPath('c:\\temp\\somewhere'), FileSystemPath('c:\\temp\\somewhere\\me'), FileSystemPath('c:\\temp\\somewhere\\not'), FileSystemPath('c:\\temp\\somewhere\\why')]
>>> 
"""

import os
from basictypes.vfs import path, basepath

class FilePath( basepath.BasePath ):
	"""Representation of a path in the FileSystem

	XXX More documentation
	XXX Need better support for unc names
	
	"""
	root = None
	fragments = None
		
	def isFile( self ):
		"""Return true if we are a file path"""
		return os.path.isfile( self )
	def isDir( self ):
		"""Return true if we are a directory path"""
		return os.path.isdir( self )
	def isRoot( self ):
		"""True if this object is the root of its filesystem"""
		unc = self.unc()
		if not unc:
			return os.path.ismount( self )
		else:
			return unc == self.canonical()
	def isAbsolute (self):
		"""Return true if this path is an absolute path"""
		return os.path.isabs( self )

	def baseOnly( self ):
		"""Is this path reachable using only the base file system"""
		return 1
	def parent( self ):
		"""Get the parent of this path as a Path"""
		# rather than using canonical, we should instead
		# first try splitting ourselves, only forcing the
		# canonical conversion if we find that doesn't tell
		# us whether we have parents... alternately, raise
		# an error saying we can't tell what the parent is
		# at the moment...
		if self.isRoot():
			return None
		parent, rest = os.path.split( self.canonical() )
		if rest and parent:
			# managed to split something off
			return path(parent, self.__class__)
		else:
			return None
	def baseName (self):
		"""Get the final fragment of the path as a string"""
		return os.path.basename( self )
		
	def exists( self ):
		"""Return true if this path exists

		XXX Should catch primitive errors and raise more useful ones
		"""
		if os.path.exists( self ):
			return 1
		else:
			return 0
	def root( self ):
		"""Get the root of this path"""
		full = path(self.canonical(), self.__class__)
		unc = full.unc()
		if unc:
			return unc
		drive = full.drive()
		if drive:
			return drive
		else:
			return None

	def unc( self, ):
		"""Get the root UNC Path, or None if it doesn't exist

		XXX This appears to always return the unc name as lowercase?
		"""
		unc,rest = os.path.splitunc( self.canonical())
		if unc:
			return path( unc, self.__class__ )
		else:
			return None
	def drive (self,):
		"""Get the root drive Path, or None if it doesn't exist"""
		drive,rest = os.path.splitdrive( self.canonical())
		if drive:
			return path( drive+os.sep, self.__class__ )
		else:
			return None

	def fragments (self):
		"""Get the path as a set of string fragments"""
		fragments = []
		fragment = 1
		full = path(self.canonical(), self.__class__ )
		while full and fragment:
			full, fragment = full.split()
			if fragment:
				fragments.append( fragment )
			else:
				fragments.append( full )
		fragments.reverse()
		return fragments
	def parents( self ):
		"""Return all of our parents up to our root"""
		fragments = self.fragments()
		if not fragments:
			# XXX fix this
			raise ValueError( "parents of a NULL path?" )
		current = None
		result = []
		for value in fragments[:-1]:
			if current is None:
				current = value
			else:
				current = current + value
			result.append( current )
		return result
		

	def canonical(self):
		"""Get a canonical version of this path

		The new path will be absolute, expanded,
		case-normalized, and normalized.
		"""
		return os.path.normcase(
				os.path.normpath(
					os.path.expanduser(
						os.path.expandvars(
							os.path.realpath(self)
						)
					)
				)
			)


	def join( self, * name ):
		"""Create a new Path from this path plus name"""
		return path(
			os.path.join(str(self), *name),
			self.__class__
		)
	__add__ = join
		
	def split( self ):
		"""Return our parent path (if available) and our name"""
		head, tail = os.path.split( self )
		return path(head, self.__class__), path(tail, self.__class__)
	def extension (self):
		"""Return the file extension, or "" if there is no extension"""
		return os.path.splitext(self)[1]
	splitext = extension

	def stat( self ):
		"""Attempt to run a stat on the object"""
		return os.stat( self )
	def size( self ):
		"""Attempt to get the (byte) size of the object on disk

		Note: calling this on directories does a recursive call
		adding up the sizes up the files in the directory, which can
		be rather expensive.
		"""
		if self.exists():
			if self.isFile():
				return os.stat( self).st_size
			else:
				class collect(object):
					total = 0
					def __call__( self, filePath ):
						self.total = self.total + filePath.size()
				c = collect()
				self.walk( file = c )
				return c.total
		raise NotImplementedError( """Couldn't get size for path %s"""%(repr(self)))
	def permissions (self, mode=None ):
		"""Attempt to update and/or read permissions for the path

		if mode is None --> attempt to read permissions, return None if couldn't succeed
		if mode is anything else --> call chmod with the value

		XXX Eventually, this should support platform-specific permission
		specifications, such as Secure Linux or WinNT permissions,
		though I'm not sure how
		"""
		if mode is None:
			# get
			if self.exists():
				if self.isFile():
					return os.stat( self).st_mode
				else:
					return None
			raise NotImplementedError( """Couldn't get permissions for path %s"""%(repr(self)))
		else:
			if self.exists():
				os.chmod( self, mode )

	def remove( self ):
		"""(Recursively) remove this object from the filesystem

		XXX Should provide options to change permissions if they are
		incorrectly set (e.g. read-only), and maybe clobber
		locks/holds if they exist (not even sure that's possible)
		"""
		self.walk(
			file=os.remove,
			post= os.rmdir
		)

	### APIs that assume directory/file status...
	def list( self, glob="" ):
		"""Return a list of Path objects representing the current contents of this directory"""
		return [
			self.join( name )
			for name in os.listdir( self )
		]
	def createDirectory(self,*arguments,**namedarguments):
		"""Ensure that a directory exists, if possible

		Note: will not work with zipfile directories as they
		don't really exist, zipfiles should probably recurse
		down to the ZIP file, create the ZIP file and then,
		if there is an embedded filesystem (such as an embedded
		zipfile) create that, otherwise ignore the remainder
		of the path.
		"""
		return os.makedirs( self, *arguments, **namedarguments )
	def file (self, name ):
		"""Create a new file path within this directory"""
		if self.isDir():
			return self.join( name )
		else:
			raise ValueError( """Can't currently create a file in a file""" )
		
	def subDir(self, name,*arguments,**namedarguments):
		"""Create a new subdirectory path within this directory"""
		if self.isDir():
			return self.join( name )
		else:
			raise ValueError( """Can't currently create a directory in a file""" )

	def open(self, *arguments,**namedarguments):
		"""Attempt to open a file path for reading/writing/appending

		returns file( self, *arguments, **namedarguments) for the moment
		might return a file sub-class eventually
		"""
		return file( self, *arguments, **namedarguments)

	### "Somday" functionality
	def mimeType( self ):
		"""Attempt to determine the platform-specific mime type mapping for this path

		XXX Only source I know with this info is wxPython
		"""
	def association (self):
		"""Attempt to determine the platform-specific application association for the path

		XXX This is going to be a guess on most platforms I'd assume
		Windows -- assoc + ftype, or a registry access
		Mac -- resource fork of the file
		"""
	def start (self):
		"""Attempt to start the system's default application for this file

		This is a serious security consideration, but it's something people
		are wanting to do all the time, not sure where to stand on it.
		"""
	def touch( self ):
		"""Attempt to update times on the path"""

