"""Module providing "late-binding" for type specifiers

This is a generically useful utility module, it is
provided here just because this is where it is used
the most.
"""
import sys

def bind( specifier ):
	"""Find the class(es) specified by specifier

	Allows you to pass a type specifier, one of:

		string -> fully-qualified string specifying an importable class
		tuple/list -> list of specifiers
		class/other -> a class or other type (untouched)

	and get back either a single class, or a tuple of
	classes.

	This allows you to specify types like so:

		"wxPython.wx.wxFramePtr"
		(str,unicode,"my.special.StringClass")

	in many places within the basicproperty and wxoo packages
	for use as a sequence of classes without getting messed up
	by mutual-import problems.

	Note: the only time you get back a single class (as opposed to
	a tuple with a single class as it's only item) is when you
	specify a string or class as the root specifier.
	"""
	if isinstance( specifier, unicode ):
		specifier = str(specifier)
	if isinstance( specifier, str):
		return importByName( specifier )
	elif isinstance( specifier, (tuple,list)):
		return tuple(flatten([
			bind(spec)
			for spec in specifier
		]))
	else:
		return specifier

def importByName( fullName ):
	"""Import a class by name"""
	name = fullName.split(".")
	moduleName = name[:-1]
	className = name[-1]
	module = __import__( ".".join(moduleName), {}, {}, moduleName)
	return getattr( module, className )

def flatten(inlist, type=type, ltype=(list,tuple), maxint= sys.maxint):
	"""Flatten out a list, code developed by myself and modified by Tim Peters, then by me again :)"""
	try:
		# for every possible index
		for ind in xrange( maxint):
			# while that index currently holds a list
			while isinstance( inlist[ind], ltype):
				# expand that list into the index (and subsequent indicies)
				inlist[ind:ind+1] = list(inlist[ind])
			#ind = ind+1
	except IndexError:
		pass
	return inlist
	
	
