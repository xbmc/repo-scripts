"""Core-python interface definitions"""
from protocols import Interface, Attribute, declareImplementation
import sys
### Python-object protocols
class IObjectPyDoc(Interface):
	"""Object which contains python doc string
	"""
	__doc__ = Attribute(
		"__doc__","""Python documentation string for the object""",
	)
class IObjectPyDict(Interface):
	"""Object with a Python __dict__ attribute
	"""
	__dict__ = Attribute(
		"__dict__","""Python object dictionary""",
	)
class IObjectContains(Interface):
	"""Object which can determine whether it contains other
	"""
	def __contains__( other ):
		"""Determine whether object contains other"""

class IObjectEq(Interface):
	"""Object which can compute whether other is equal

	XXX should have adapters both ways for eq and ne
	"""
	def __eq__( other ):
		"""Determine whether object == other"""
class IObjectNe(Interface):
	"""Object which can compute whether other is not equal

	XXX should have adapters both ways for eq and ne
	"""
	def __ne__( other ):
		"""Determine whether object != other"""

class IObjectPyName(Interface):
	"""Object with a __name__ attribute"""
	__name__ = Attribute(
		"__name__","""Integral name for the object""",
	)

class IObjectComparable(Interface):
	"""Object which can be compared to other objects using cmp

	There's a considerable number of methods, or a
	very large number of interfaces.  Not sure what
	should be done, so for now it's just a marker.
	"""

class IObjectGetItem( Interface):
	"""Object which retrieves a sub-item by key (random access)"""
	def __getitem__( key ):
		"""Get sub-item by key or index"""
class IObjectSetItem( Interface):
	"""Object which sets a sub-item by key (random access)"""
	def __setitem__( key, other ):
		"""Set sub-item by key or index"""
class IObjectDelItem( Interface):
	"""Object which deletes a sub-item by key (random access)"""
	def __delitem__( key ):
		"""Delete sub-item by key or index"""

class IObjectLength( Interface ):
	"""Objects which can report a total length (number of sub-elements)"""
	def __len__( ):
		"""Return the length as an integer or long"""
class IObjectNonZero( Interface ):
	"""Objects which can determine their Boolean truth value directly

	XXX Should be an adapter for IObjectLength?
	"""
	def __nonzero__( ):
		"""Determine if the object is True (not False)"""

class IObjectHash( Interface ):
	"""Objects which can calculate a hash/key value"""
	def __hash__( ):
		"""Return the hash as an integer"""

class IObjectIter(Interface):
	"""Object which provides explicit iteration support"""
	def __iter__():
		"""Return an iterator for the items of this object"""

### Pickle (and copy) protocols
## The code for these mechanisms includes "fallback" interfaces
## such as "has a dictionary", along with the ability to exclude
## 0,1,2 or even all 3 sub-interface.  An object is pickleable/copyable
## even without any of these interfaces, they are merely extra
## functionality interfaces that can be used.
class IPickleable(Interface):
	"""Marker interface declaring that object is pickleable"""
class IPickleGetState(Interface):
	"""Object which allows retrieval of current state"""
	def __getstate__():
		"""Retrieve an object representing the current state"""
class IPickleSetState(Interface):
	"""Object which allows initialization from an archive of current state"""
	def __setstate__(state):
		"""Initialize the object from the given state"""
class IPickleGetInitArgs(Interface):
	"""Object which allows retrieval of "recreation" arguments"""
	def __getinitargs__():
		"""Retrieve initialization arguments to re-create current state"""
# XXX should have the __reduce__ interface as well, but I've
# never actually used that to document it.

# I don't like the names for these interfaces, suggestions? -- mcf
class ICopyable(Interface):
	"""Marker interface declaring that object is copyable"""
class ICopyCopy(ICopyable):
	"""Object which defines explicit shallow __copy__ method"""
	def __copy__():
		"""Return a shallow copy of the object"""
class IDeepCopyable(Interface):
	"""Marker interface declaring that object is copyable"""
class ICopyDeepCopy(IDeepCopyable):
	"""Object which defines explicit __deepcopy__ method"""
	def __deepcopy__(memory):
		"""Return a deep copy of the object

		memory -- dictionary of already-copied elements
		"""
### Sequence protocols
class ISequenceGetItem( Interface):
	"""Sequence version of get-item, integer keys

	This is the "random access" integer key retrieval
	interface, whereas the IIterator interface gives
	the more limited sequential interface.
	"""
	def __getitem__( index ):
		"""Get sub-item by index"""
class ISequenceSetItem( Interface):
	"""Sequence version of set-item, integer keys"""
	def __setitem__( index, other ):
		"""Set sub-item by index"""
class ISequenceDelItem( Interface):
	"""Sequence version of get-item, integer keys"""
	def __delitem__( index ):
		"""Delete sub-item by index"""

class ISequenceGetSlice( Interface ):
	"""Sequence which can retrieve a "slice" of sub-objects by index"""
	def __getslice__( start, stop):
		"""Get sub-items by index-range"""
class ISequenceSetSlice( Interface ):
	"""Sequence which can set a "slice" of sub-objects by index"""
	def __setslice__( start, stop, other):
		"""Set sub-items by index-range"""
class ISequenceDelSlice( Interface ):
	"""Sequence which can delete a "slice" of sub-objects by index"""
	def __delslice__( start, stop):
		"""Delete sub-items by index-range"""

class ISequenceAppend(Interface):
	"""Sequence object to which items may be appended"""
	def append( item):
		"""Append the particular item to the sequence"""
class ISequenceCount(Interface):
	"""Sequence object which can count instances of items"""
	def count(item):
		"""Return the number of occurrences of the item in the sequence"""
class ISequenceExtend(Interface):
	"""Sequence object which can be extended with another sequence"""
	def extend(other):
		"""Extend this sequence with the other sequence"""
class ISequenceIndex(Interface):
	"""Sequence object which can determine index of a sub-item"""
	def index(item):
		"""Return integer index of first occurrence of item in sequence"""
class ISequenceInsert(Interface):
	"""Sequence object which can insert item at a given index

	XXX Should have adapters for ISequenceAppend and ISequenceExtend
	"""
	def insert(index, item):
		"""Insert the given item at the given index

		(sequence[index] should be item afterward)
		"""
class ISequenceRemove(Interface):
	"""Sequence object which can remove an instance of an item"""
	def remove(item):
		"""Remove the first instance of the given item from sequence"""
class ISequenceReverse(Interface):
	"""Sequence whose order can be reversed in-place"""
	def reverse():
		"""Reverse the sequence's order in-place"""
class ISequenceSort(Interface):
	"""Sequence whose order can be sorted in-place"""
	def sort(function = None):
		"""Sort the sequence in-place

		function -- if specified, the comparison function
			to use for sorting, otherwise cmp
		"""
class ISequencePop(Interface):
	"""Sequence which can "pop" last item"""
	def pop():
		"""Remove and return the last item of the sequence"""
class ISequencePopAny(Interface):
	"""Sequence which can "pop" any item"""
	def pop(index =-1):
		"""Remove and return the given item from the sequence"""

### The rather simple iterator protocol
class IIterator(Interface):
	"""Object which can operate as an iterator"""
	def __iter__():
		"""Return the object itself to allow for x in Iterator operation"""
	def next():
		"""Return the next item in the sequence"""

### Text-type objects (strings and Unicode)
## Sub-API: joining and splitting
class ITextJoin( Interface):
	"""Text which can join sequences of text objects"""
	def join(sequence):
		"""Return texts within sequence joined by this text"""
class ITextSplit( Interface):
	"""Text which can create sequences by splitting on a sub-string"""
	def split(substring, maximum=None):
		"""Return text intervals between instances of substring in text"""
class ITextReplace(Interface):
	"""Text which can generate copies with replaced sub-strings"""
	def replace(old, new, maximum = None):
		"""Return text with instances of old substring replaced by new substring

		maximum -- if specified, limits total number of substitutions
		"""
class ITextSplitLines(Interface):
	"""Text which can split itself on line breaks"""
	def splitlines(keepends= 0):
		"""Return text intervals between newline characters

		keepends -- if true, retain the newline characters
			as part of the intervals (lines)
		"""

## Sub-API: Create new versions of objects with different formatting/encoding
class ITextCapitalize(Interface):
	"""Text which can generate word-capitalized copies"""
	def capitalize():
		"""Return copy of text with the first characters capitalized"""
class ITextCenterAlign(Interface):
	"""Text which can generate center-aligned copy of a given width"""
	def center(width):
		"""Return copy of text centered in string of given width"""
class ITextRightAlign(Interface):
	"""Text which can generate right-aligned copy of a given width"""
	def rjust(width):
		"""Return copy of text right-aligned in string of given width"""
class ITextLeftAlign(Interface):
	"""Text which can generate left-aligned copy of a given width"""
	def ljust(width):
		"""Return copy of text left-aligned in string of given width"""
class ITextZeroFill(Interface):
	"""Text which can generate left-zero-padded copies of itself"""
	def zfill(width):
		"""Return copy of text left-zero-padded in string of given width"""

class ITextTranslate(Interface):
	"""Text which can generate translation-table modified copies of itself"""
	def translate(table, toDelete=""):
		"""Return copy of text translated via table with to toDelete characters removed"""

class ITextExpandTabs( Interface):
	"""Text which can generate tab-expanded copies"""
	def expandtabs( tabsize = 8 ):
		"""Return copy of text with tabs expanded to tabsize spaces"""

## Case manipulation
class ITextCaseUpper(Interface):
	"""Text which can generate upper case copies"""
	def upper():
		"""Return a copy of text in all uppercase"""
class ITextCaseLower(Interface):
	"""Text which can generate lower case copies"""
	def lower():
		"""Return a copy of text in all lowercase"""
class ITextCaseSwap(Interface):
	"""Text which can generate case-swapped copies"""
	def swapcase():
		"""Return a copy of text with case of all characters swapped"""
class ITextCaseTitle(Interface):
	"""Text which can generate title-cased copies"""
	def title():
		"""Return a copy of text in title-case"""


class ITextStripLeft(Interface):
	"""Text which can generate copies with leftmost whitespace trimmed"""
	def lstrip(whitespace = None):
		"""Return copy of text with leftmost whitespace trimmed

		whitespace -- None, indicating regular whitespace, otherwise
			set of characters which should be trimmed.
		"""
class ITextStripRight(Interface):
	"""Text which can generate copies with rightmost whitespace trimmed"""
	def rstrip(whitespace = None):
		"""Return copy of text with rightmost whitespace trimmed

		whitespace -- None, indicating regular whitespace, otherwise
			set of characters which should be trimmed.
		"""
class ITextStrip(Interface):
	"""Text which can generate copies with leading and trailing whitespace trimmed"""
	def strip(whitespace = None):
		"""Return copy of text with leading and trailing whitespace trimmed

		whitespace -- None, indicating regular whitespace, otherwise
			set of characters which should be trimmed.
		"""

class ITextDecode(Interface):
	"""Text which can be decoded using a particular codec"""
	def decode(encoding = None, errors = "strict"):
		"""Decode text using the codec registered for encoding.

		encoding defaults to the default encoding. errors may be given
		to set a different error handling scheme. Default is 'strict'
		meaning that encoding errors raise a ValueError. Other possible
		values are 'ignore' and 'replace'.
		"""
class ITextEncode(Interface):
	"""Text which can be encoded using a particular codec"""
	def encode(encoding = None, errors = "strict"):
		"""Encode text using the codec registered for encoding.

		encoding defaults to the default encoding. errors may be given
		to set a different error handling scheme. Default is 'strict'
		meaning that encoding errors raise a ValueError. Other possible
		values are 'ignore' and 'replace'.
		"""
## Sub-API: Query for contents based on sub-strings
class ITextStartsWith( Interface):
	"""Text which can determine whether it starts with a particular sub-string"""
	def startswith( prefix, start = 0, end = sys.maxint):
		"""Return true if the text (in the given slice) starts with the given suffix """
class ITextEndsWith( Interface):
	"""Text which can determine whether it ends with a particular sub-string"""
	def endswith( suffix, start = 0, end = sys.maxint):
		"""Return true if the text (in the given slice) ends with the given suffix """
class ITextCount(ISequenceCount):
	"""Text which can count substring occurrences in a given range"""
	def count( sub, start= 0, end=sys.maxint):
		"""Count the number of occurrences of substring in given slice"""
class ITextFind(Interface):
	"""Text which can find start of contained sub-strings"""
	def find( sub, start = 0, end =sys.maxint):
		"""Return lowest index where substring found in slice, -1 if not found"""
class ITextIndex( ISequenceIndex ):
	"""Text providing sequence-style index method with extra arguments"""
	def index(sub, start=0, end= sys.maxint):
		"""Return lowest index where substring found in slice, ValueError if not found"""
class ITextFindRight(Interface):
	"""Text which can find start of contained sub-strings from end of text"""
	def rfind( sub, start = 0, end =sys.maxint):
		"""Return highest index where substring found in slice, -1 if not found"""
class ITextIndexRight( ISequenceIndex ):
	"""Text which can find start of contained sub-strings from end of text, sequence style"""
	def rindex(sub, start=0, end= sys.maxint):
		"""Return highest index where substring found in slice, ValueError if not found"""
		
class ITextIsAlphaNumeric( Interface ):
	"""Text providing test whether the text is all-alphanumeric (and non-null)"""
	def isalnum():
		"""Return whether len(text) > 0 and text is entirely alphanumeric"""
class ITextIsAlpha( Interface ):
	"""Text providing test whether the text is all-alphabetic (and non-null)"""
	def isalpha():
		"""Return whether len(text) > 0 and text is entirely alphabetic"""
class ITextIsDigit( Interface ):
	"""Text providing test whether the text is all-digits"""
	def isdigit():
		"""Return whether text is entirely composed of digit characters"""
class ITextIsNumeric( Interface ):
	"""Text providing test whether the text is all-numeric characters"""
	def isdigit():
		"""Return whether text is entirely composed of numeric characters"""
class ITextIsLower( Interface ):
	"""Text providing test whether the text is all-lowercase (and non-null)"""
	def islower():
		"""Return whether len(text) > 0 and text is entirely lowercase"""
class ITextIsSpace( Interface ):
	"""Text providing test whether the text is all-whitespace (and non-null)"""
	def isspace():
		"""Return whether len(text) > 0 and text is entirely whitespace"""
class ITextIsTitleCased( Interface):
	"""Text providing test whether text is in title case format"""
	def istitle():
		"""Return whether text is entirely formatted in title case"""
class ITextIsUpperCased( Interface):
	"""Text providing test whether text is in upper case format"""
	def isupper():
		"""Return whether text is entirely formatted in upper case"""

### Dictionary/mapping protocol
class IMappingClear(Interface):
	"""Mapping object able to clear all subelements"""
	def clear():
		"""Remove all subelements from this object"""
class IMappingCopy(Interface):
	"""Mapping object able to create a shallow copy of itself"""
	def copy():
		"""Return a shallow copy of the mapping"""
class IMappingUpdate(Interface):
	"""Mapping object able to update from another mapping object"""
	def update(other):
		"""Add all keys from other, overriding local key-value combinations"""

class IMappingGet(Interface):
	"""Mapping object providing call to retrieve an item or return default"""
	def get(key, default = None):
		"""Return the item for the giving key, or default"""
class IMappingPopItem(Interface):
	"""Mapping object providing method to retrieve and remove random value"""
	def popitem():
		"""Return some (key,value) pair from the dictionary, KeyError if empty"""
class IMappingSetDefault(Interface):
	"""Mapping object providing method to retrieve or set-default key value"""
	def setdefault(key, default = None):
		"""Retrieve current value, or set default value and return that"""

class IMappingHasKey(Interface):
	"""Mapping object providing call to determine whether key is defined"""
	def has_key(key):
		"""Determine whether the key exists in the mapping"""

class IMappingItems(Interface):
	"""Mapping object able to return all items as a (key, value) list"""
	def items():
		"""Return all items in mapping as a (key, value) list"""
class IMappingIterItems(Interface):
	"""Mapping object able to return all items as a (key, value) iterable"""
	def iteritems():
		"""Return all items in mapping as a (key, value) iterable"""
class IMappingKeys(Interface):
	"""Mapping object able to return all keys as a list"""
	def keys():
		"""Return all keys in mapping as a list"""
class IMappingIterKeys(Interface):
	"""Mapping object able to return all keys as an iterable"""
	def iterkeys():
		"""Return all keys in mapping as an iterable"""
class IMappingValues(Interface):
	"""Mapping object able to return all values as a list"""
	def values():
		"""Return all values in mapping as a list"""
class IMappingIterValues(Interface):
	"""Mapping object able to return all values as an iterable"""
	def itervalues():
		"""Return all values in mapping as an iterable"""


### Stream and file protocols
class IStreamClose(Interface):
	"""Stream providing a close method to release resources"""
	closed = Attribute (
		"closed","""Boolean displaying the current open/closed status""",
	)
	def close():
		"""flush internal buffers, close the stream, and release resources"""
class IStreamFlush(Interface):
	"""Stream providing a flush method to flush internal buffers"""
	def flush():
		"""Flush (write) internal buffers to the stream"""

class IStreamIsTTY(Interface):
	"""Stream allowing query for whether it is a TTY-like device"""
	def isatty():
		"""Return Boolean representing whether is a TTY-like device"""

class IStreamRead(Interface):
	"""Stream providing basic read method"""
	def read(size = None):
		"""read available bytes from stream, limit to size if specified"""
class IStreamWrite(Interface):
	"""Stream providing basic write method"""
	def write(string):
		"""Write the string to the stream"""

class IStreamReadLine(Interface):
	"""Stream providing line-reading method"""
	def readline(size = None):
		"""read a line from stream, limit bytes read to ~ size if specified"""
class IStreamReadLines(Interface):
	"""Stream providing multiple-line-reading method"""
	def readlines(size = None):
		"""read lines from stream, limit bytes read to ~ size if specified"""
class IStreamXReadLines(Interface):
	"""Stream providing optimized multiple-line-reading method

	XXX This probably shouldn't be an interface unto itself,
		or at least it should be a child of IStreamReadLines
	"""
	def xreadlines(size = None):
		"""read lines from stream, limit bytes read to ~ size if specified"""
class IStreamWriteLines(Interface):
	"""Stream providing multiple-line-writing method"""
	def writelines(iterable):
		"""Iterate over the iterable writing each resulting string to stream"""

class IStreamSeek(Interface):
	"""Stream providing random-access seeking to position"""
	def seek(offset, whence):
		"""seek(offset[, whence]) -> None.  Move to new stream position

		Argument offset is a byte count.  Optional argument whence defaults to
		0 (offset from start of file, offset should be >= 0); other values are 1
		(move relative to current position, positive or negative), and 2 (move
		relative to end of file, usually negative, although many platforms allow
		seeking beyond the end of a file).
		"""

class IStreamTell(Interface):
	"""Stream providing feedback regarding current position"""
	def tell():
		"""return current file position (integer or long)"""
class IStreamTruncate(Interface):
	"""Stream providing feedback regarding current position

	XXX Documentation seems to suggest that this interface requires
		IStreamTell, though only in cases where size is not specified
	"""
	def truncate(size = None):
		"""Truncated stream to given size, or current position if not specified"""

class IStreamMode(Interface):
	"""Stream having a mode attribute"""
	mode = Attribute (
		"mode", """The I/O mode for the file""",
	)
class IStreamName(Interface):
	"""Stream having a name attribute"""
	name = Attribute (
		"name", """Filename or data-source description""",
	)

class IStringIOGetValue(Interface):
	"""Provides access to current value of StringIO buffer"""
	def getvalue ():
		"""Retrieve the current value of the string buffer"""

	

### DBM database protocol
class IDBMDatabase(
	IObjectContains,
	IObjectIter,
	IObjectGetItem,
	IObjectSetItem,
	IObjectDelItem,
	IMappingIterKeys,
	IMappingKeys,
	IStreamClose,
	IMappingHasKey,
):
	"""(Dumb/G)DBM Interface

	XXX Note this interface is derived from the DumbDBM
		runtime class, there may be items which are not
		officially considered part of interface.
	"""

class IBSDIteration(Interface):
	"""BSDDB iteration interface

	This is the interface provided by the dbhash module's
	"database" objects (in addition to the IDBMDatabase
	interface).
	"""
	def first():
		"""return the first key in the database"""
	def next(key):
		"""return the key in the database after given key"""
	def last():
		"""return the last key in the database"""
	def previous(key):
		"""return the key in the database before given key"""
	def sync():
		"""synchronize in-memory database with on-disk database"""

class IBSDIterationSetLocation(IBSDIteration):
	"""Adds ability to set database cursor location by key
	"""
	def set_location( key ):
		"""Set cursor to item indicated by key, return (key,value)"""


### Array-specific
class IArrayIOString(Interface):
	"""Array-object to/from string method interfaces"""
	def tostring():
		"""Convert to array of machine values and return as string"""
	def fromstring( string ):
		"""Appends items from string (sequence of machine values)"""
class IArrayIOList(Interface):
	"""Array-object to/from list method interfaces"""
	def tolist():
		"""Convert to list of elements"""
	def fromlist( string ):
		"""Appends items from list"""
class IArrayIOFile(Interface):
	"""Array-object to/from file method interfaces"""
	def tofile():
		"""Write to file as array of machine values"""
	def fromfile( string ):
		"""Appends from file/stream as array of machine values"""
class IArrayMetadata( Interface ):
	"""Array-object providing item-type metadata"""
	typecode = Attribute(
		"typecode", """The typecode character used to create the array""",
	)
	itemsize = Attribute(
		"itemsize", """The length in bytes of one array item in the internal representation""",
	)

class IArrayByteswap( Interface ):
	"""Mutable-array interface"""
	def byteswap( ):
		"""Byte-swap the array data"""
		
list__implements__ = [
	IObjectContains,
	IObjectEq,
	IObjectNe,
	IObjectComparable,
	IObjectLength,
	#IObjectIter, # list doesn't have __iter__

	IPickleable,
	ICopyable,
	IDeepCopyable,

	ISequenceGetItem,
	ISequenceSetItem,
	ISequenceDelItem,
	ISequenceGetSlice,
	ISequenceSetSlice,
	ISequenceDelSlice,
	ISequenceAppend,
	ISequenceCount,
	ISequenceExtend,
	ISequenceIndex,
	ISequenceInsert,
	ISequenceRemove,
	ISequenceReverse,
	ISequenceSort,
	ISequencePopAny,
]
str__implements__= [
	IObjectContains,
	IObjectEq,
	IObjectNe,
	IObjectComparable,
	IObjectLength,
	IObjectHash,
	#IObjectIter, # str doesn't have __iter__ :(

	IPickleable,
	ICopyable,
	IDeepCopyable,

	ISequenceGetItem,
	ISequenceGetSlice,
	ITextCount,
	ITextJoin,
	ITextSplit,
	ITextReplace,
	ITextSplitLines,
	ITextCapitalize,
	ITextCenterAlign,
	ITextRightAlign,
	ITextLeftAlign,
	ITextZeroFill,
	ITextTranslate,
	ITextExpandTabs,
	ITextCaseUpper,
	ITextCaseLower,
	ITextCaseSwap,
	ITextCaseTitle,
	ITextStripLeft,
	ITextStripRight,
	ITextStrip,
	ITextDecode,
	ITextEncode,
	ITextStartsWith,
	ITextEndsWith,
	ITextCount,
	ITextFind,
	ITextIndex,
	ITextFindRight,
	ITextIndexRight,
	ITextIsAlphaNumeric,
	ITextIsAlpha,
	ITextIsDigit,
	ITextIsNumeric,
	ITextIsLower,
	ITextIsSpace,
	ITextIsTitleCased,
	ITextIsUpperCased,
]
unicode__implements__= [
	IObjectContains,
	#IObjectEq, # doesn't implement it :(
	#IObjectNe, # doesn't implement it :(
	IObjectComparable,
	IObjectLength,
	IObjectHash,
	#IObjectIter, # unicode doesn't have __iter__ :(

	IPickleable,
	ICopyable,
	IDeepCopyable,

	ISequenceGetItem,
	ISequenceGetSlice,
	ITextCount,
	ITextJoin,
	ITextSplit,
	ITextReplace,
	ITextSplitLines,
	ITextCapitalize,
	ITextCenterAlign,
	ITextRightAlign,
	ITextLeftAlign,
	ITextZeroFill,
	ITextTranslate,
	ITextExpandTabs,
	ITextCaseUpper,
	ITextCaseLower,
	ITextCaseSwap,
	ITextCaseTitle,
	ITextStripLeft,
	ITextStripRight,
	ITextStrip,
	#ITextDecode,
	ITextEncode,
	ITextStartsWith,
	ITextEndsWith,
	ITextCount,
	ITextFind,
	ITextIndex,
	ITextFindRight,
	ITextIndexRight,
	ITextIsAlphaNumeric,
	ITextIsAlpha,
	ITextIsDigit,
	ITextIsNumeric,
	ITextIsLower,
	ITextIsSpace,
	ITextIsTitleCased,
	ITextIsUpperCased,
]
tuple__implements__= [
	IObjectContains,
	IObjectEq,
	IObjectNe,
	IObjectComparable,
	IObjectLength,
	IObjectHash,

	IPickleable,
	ICopyable,
	IDeepCopyable,

	ISequenceGetItem,
	ISequenceGetSlice,
]
dict__implements__= [
	IObjectContains,
	IObjectEq,
	IObjectNe,
	IObjectComparable,
	IObjectGetItem,
	IObjectSetItem,
	IObjectDelItem,
	IObjectLength,
	IObjectIter,

	IPickleable,
	ICopyable,
	IDeepCopyable,

	IMappingClear,
	IMappingCopy,
	IMappingUpdate,
	IMappingGet,
	IMappingPopItem,
	IMappingSetDefault,
	IMappingHasKey,
	IMappingItems,
	IMappingIterItems,
	IMappingKeys,
	IMappingIterKeys,
	IMappingValues,
	IMappingIterValues,
]

array_ArrayType__implements__= [
	### The array object in Python 2.2.2, although it works
	## as though it had the commented out interfaces doesn't
	## actually provide the interface's signature :(
	## The interface signatures even show up in the ArrayType
	## class, they just aren't showing up in the objects :(
	#IObjectContains,
	#IObjectEq,
	#IObjectNe,
	IObjectComparable,
	#IObjectLength,
	#IObjectIter, # list doesn't have __iter__

	# not sure arrays really are all three of these
	IPickleable,
	ICopyable,
	IDeepCopyable,

	#ISequenceGetItem,
	#ISequenceSetItem,
	#ISequenceDelItem,
	#ISequenceGetSlice,
	#ISequenceSetSlice,
	#ISequenceDelSlice,
	ISequenceAppend,
	ISequenceCount,
	ISequenceExtend,
	ISequenceIndex,
	ISequenceInsert,
	ISequenceRemove,
	ISequenceReverse,
	ISequenceSort,
	ISequencePopAny,
	IArrayIOString,
	IArrayIOList,
	IArrayIOFile,
	IArrayMetadata,
	IArrayByteswap,
]

bsddb__implements__= [
	IDBMDatabase,
	IBSDIterationSetLocation,
]
dbhash__implements__= [
	IDBMDatabase,
	IBSDIteration,
]
dumbdbm__implements__= [
	IDBMDatabase,
]
file__implements__ = [
	IObjectIter,
	IObjectHash,
	IStreamClose,
	IStreamFlush,
	IStreamIsTTY,
	IStreamRead,
	IStreamWrite,
	IStreamReadLine,
	IStreamReadLines,
	IStreamXReadLines,
	IStreamWriteLines,
	IStreamSeek,
	IStreamTell,
	IStreamTruncate,
	IStreamMode,
	IStreamName,
]	
StringIO_StringIO__implements__= file__implements__ + [
	# XXX does it actually support everything the file does?
	IStringIOGetValue,
]
baseTypeImplements = [
	(list, list__implements__),
	(tuple, tuple__implements__),
	(str, str__implements__),
	(unicode, unicode__implements__),
	(dict, dict__implements__),
##	(array.ArrayType, array_ArrayType__implements__),
]	

def register():
	for classObject, interfaceList in baseTypeImplements:
		declareImplementation(
			classObject,
			interfaceList,
		)
register()
