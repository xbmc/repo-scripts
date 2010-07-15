import unittest, os
from basictypes.vfs import path

class NTFilePathTests(unittest.TestCase):
	"""Note: these tests are Windows-specific"""
	def testRepr( self ):
		"""Test representation is as expected"""
		value = path( "test" )
		result = repr( value )
		expected = "%s(%s)"%( value.__class__.__name__, repr(str(value)))
		self.failUnlessEqual( result, expected, """Got:\n%s\t\nExpected:\n\t%s"""% (result, expected))
	def testSimpleRelative( self ):
		"""Test a simple relative path for basic operations"""
		fileName = "test.tmp"
		testFile = path(fileName)
		assert testFile == fileName,"""Path did not match an equal string"""
		assert str(testFile) == fileName,"""str(Path) did not match an equal string"""
		assert not testFile.isAbsolute(),"""relative path declared itself absolute"""
		assert not testFile.isRoot(),"""non-root path declared itself root"""
		assert testFile.baseOnly(),"""base file system path declared itself non-base"""
		open( fileName,'w' ).write( 'ha' )
		assert testFile.exists(),"""could not create file in current working directory, or exists method failure"""
		assert testFile.parent() == os.getcwd(),"""file created in current working directory does not report current working directory as parent"""
		assert testFile.size() == 2,"""file with two bytes written reports size other than 2, possible bug in size (or data writing)"""

		open( testFile, 'w').write( 'ham' )
		assert testFile.exists(),"""could not create file in current working directory, or exists method failure"""
		assert testFile.parent() == os.getcwd(),"""file created in current working directory does not report current working directory as parent"""
		assert testFile.size() == 3,"""file with 3 bytes written reports size other than 3, possible bug in size (or data writing)"""
	def testFullySpecified (self):
		"""Test a fully specified file path"""
		# now a fully-specified path
		fileName = "c:\\test.tmp"
		testFile = path(fileName)
		assert testFile == fileName,"""Path did not match an equal string"""
		assert str(testFile) == fileName,"""str(Path) did not match an equal string"""
		assert testFile.isAbsolute(),"""absolute path declared itself relative"""
		assert not testFile.isRoot(),"""root path declared itself non-root"""
		assert testFile.baseOnly(),"""base file system path declared itself non-base"""

		result = testFile.parent()
		assert result == "c:\\","""parent reported as %s"""% (result)
		assert result == path( "c:\\" ),"""parent reported as %s"""% (result)

		assert testFile.isChild( "c:\\" )
		assert testFile.drive() == 'c:\\', "got %s"%( repr(testFile.drive()))
		assert testFile.root() == 'c:\\' 
		assert path( "c:\\" ).isParent( testFile )
	def testRoot(self):
		"""Test a root for the file system"""
		# test a real root
		roots = [path("c:\\"), path( r"\\Raistlin\c")]
		for root in roots:
			assert root.isRoot()
			assert root.parent() == None
			assert root.root() == root
		assert path("c:\\").unc() == None
		assert path("c:\\").drive() == "c:\\"
		assert path("c:\\temp").drive() == "c:\\"
		assert path("c:\\temp").root() == "c:\\"
		assert path("c:\\temp").drive()[-1] == os.sep

		assert path(r"\\Raistlin\c").drive() == None
		assert path(r"\\Raistlin\c").unc() == r"\\raistlin\c"
		assert path(r"\\Raistlin\c").parent() == None
		assert path(r"\\Raistlin\c").root() == r"\\raistlin\c"
	def testFragments (self):
		"""Test ability to break paths into fragments"""
		assert path(
			"p:\\temp\\this\\that\\thos\\test.tmp"
		).fragments() == [ 'p:\\', 'temp','this','that','thos','test.tmp']
		assert path(
			"c:"
		).fragments() == [ 'c:\\']
		assert path(
			"p:\\temp\\this\\that\\thos\\test.tmp"
		).parents() == [
			'p:\\',
			'p:\\temp',
			'p:\\temp\\this',
			'p:\\temp\\this\\that',
			'p:\\temp\\this\\that\\thos',
		], "Got: %s"%( path(
			"p:\\temp\\this\\that\\thos\\test.tmp"
		).parents() )
	def testWalk (self):
		"""Test three-method walking functions"""
		dir = path(
			"p:\\temp"
		)
		assert dir.join('test') == "p:\\temp\\test"
		result = []
		# need a testing directory for this to be automated...
		dir.walk( result.append )
	def testFileDirectoryOperations (self):
		"""Test file and/or directory-specific operations"""
		dir = path(
			"p:\\temp\\this\\that"
		)
		try:
			dir.walk( file=os.remove, post= os.rmdir)
		except OSError, err:
			print 'failed to remove', err
		dir.createDirectory( mode = 0777 )
		f = dir+'test.txt'
		f.open('w').write( 'testing' )
		assert f.exists()
		assert f.open('r').read() == 'testing'
		


def getSuite():
	return unittest.makeSuite(NTFilePathTests,'test')

if __name__ == "__main__":
	unittest.main(defaultTest="getSuite")
