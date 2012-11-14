"""Restrictive-List base class"""

class rlist( list ):
	"""Sub-class of list that calls a method before insertion allowed
	"""
	def __init__(self, value= None):
		"""Initialize the restricted list object"""
		if value is not None:
			value = self.beforeMultipleAdd([ self.beforeAdd(item) for item in value ])
		else:
			value = []
		super (rlist, self).__init__(value)
	def __setslice__( self, start, stop, value ):
		"""__setslice__ with value checking"""
		value = self.beforeMultipleAdd([ self.beforeAdd(item) for item in value ])
		return super(rlist,self).__setslice__( start, stop, value )
	def extend( self, value ):
		"""extend with value checking"""
		value = self.beforeMultipleAdd([ self.beforeAdd(item) for item in value ])
		return super(rlist,self).extend( value )
	__iadd__ = extend
	def append( self, value ):
		"""append with value checking"""
		value = self.beforeAdd( value )
		return super(rlist,self).append( value )
	def insert( self, index, value ):
		"""insert with value checking"""
		value = self.beforeAdd( value )
		return super(rlist,self).insert( index, value )
	def __setitem__( self, index, value ):
		"""__setitem__ with value checking"""
		value = self.beforeAdd( value )
		return super(rlist,self).__setitem__( index, value )
	def beforeAdd( self, value ):
		"""Called before all attempts to add an item"""
		return value
	def beforeMultipleAdd( self, value ):
		"""Called before attempts to add more than one item (beforeAdd has already be called for each item)"""
		return value

if __name__ == "__main__":
	a = rlist( [1,2,3,4,5] )
	print a
	print a[:].__class__
	m = rlist( [1,2,3,4,5] )
	m.append( 's' )
	
	