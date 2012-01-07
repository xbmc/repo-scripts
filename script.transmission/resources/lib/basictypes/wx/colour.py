"""wxPython colour data-type definition
"""
import wx
from basictypes import datatypedefinition, registry
#from basictypes.wxtypes import wxcopyreg

from wxPython.lib import colourdb
COLOUR_DB_INITIALISED = 0

__all__ = ( "wxColour_DT", )

class wxColour_DT( datatypedefinition.BaseType_DT ):
	"""Colour data-modelling type stand-in"""
	dataType = "wx.colour"
	baseType = wx.Colour
	def coerce(cls, value):
		"""Attempt to convert the given value to a wx.Colour

		Accepted Values:
			wx.Colour(Ptr)
			'#FFFFFF' style strings
			'black' string colour names
			3-tuple or 3-list of 0-255 integers
			None -- (gives black)
		"""
		if cls.check( value ):
			return value
		elif isinstance( value, (str,unicode) ):
			if value and value[0] == '#':
				rest = value[1:]
				if rest:
					value = int( rest, 16)
					return wx.Colour( value >> 16  & 255, value >> 8  & 255, value & 255 )
				else:
					return wx.Colour( 0,0,0)
			else:
				try:
					obj = wx.Colour( value )
				except (ValueError,TypeError):
					global COLOUR_DB_INITIALISED
					if not COLOUR_DB_INITIALISED:
						COLOUR_DB_INITIALISED = 1
						colourdb.updateColourDB()
					obj = wx.NamedColour( value )
					if not obj.Ok():
						raise ValueError( """Unrecognised string value %r for Colour value"""%(value))
		elif isinstance( value, (tuple,list) ):
			if len(value) == 3:
				obj = wx.Colour( *value )
			else:
				raise ValueError( """Unable to create wx.Colour from %r, incorrect length"""%( value ))
		elif value is None:
			return wx.Colour( 0,0,0)
		else:
			raise TypeError( """Unable to convert value %r (type %s) to wx.Colour object"""%( value, type(value)))
		return obj
	coerce = classmethod( coerce )
registry.registerDT( wx.Colour, wxColour_DT)
registry.registerDT( wx.ColourPtr, wxColour_DT)
