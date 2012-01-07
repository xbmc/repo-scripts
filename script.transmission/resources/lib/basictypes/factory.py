"""(preliminary) Model of a Factory Callable object"""
from basicproperty import propertied, basic, common
from basictypes import list_types, callable

class Factory( callable.Callable ):
	"""An object intended to create instances of a type

	The factory allows you to create instances of a type
	through the GUI.  Most factories will allow for
	entirely-default calling (i.e. Factory() creates a
	new, valid instance).  Others may require interactive
	definition of certain parameters.
	"""

listof_Factories = list_types.listof(
	Factory,
	name = "listof_Factories",
	dataType = 'list.Factories',
)
	