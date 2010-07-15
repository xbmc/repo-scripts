"""wxPython colour data-type definition
"""
import wx
from basictypes import datatypedefinition, enumeration, registry
##from basictypes.wx import wxcopyreg
from basicproperty import basic

__all__ = ( "wxPen_DT", "PenStyleProperty", "PenCapProperty")

class wxPen(wx.Pen):
	"""A somewhat easier-to-use Pen class for use with basictypes"""
	dataType = "wx.pen"
	coreAttributes = ('colour','width','style','cap','join',)
	extraAttributes = ('stipple','dashes')
	def __init__(
		self,
		colour="BLACK",
		width=1,
		style=wx.SOLID,
		cap=wx.CAP_ROUND,
		join=wx.JOIN_ROUND,
		stipple=None,
		dashes=None,
	):
		"""Initialize the wxPen object

		colour -- wxColour specifier, a wxColour, a named colour
			or a #ffffff formatted string value
		width -- pen-width in pixels
		style -- one of the wxPen style constants
			wxSOLID
			wxVERTICAL_HATCH
			wxUSER_DASH
			wxCROSSDIAG_HATCH
			wxHORIZONTAL_HATCH
			wxSTIPPLE
			wxBDIAGONAL_HATCH
			wxFDIAGONAL_HATCH
			wxDOT_DASH
			wxSHORT_DASH
			wxLONG_DASH
			wxCROSS_HATCH
			wxTRANSPARENT
		cap -- one of the wxPen cap constants
			wxCAP_ROUND
			wxCAP_BUTT
			wxCAP_PROJECTING
		join -- one of the wxPen join constants
			wxJOIN_BEVEL
			wxJOIN_MITER
			wxJOIN_ROUND
		stipple -- when style == wxSTIPPLE, a bitmap used to
			control the drawing style
		dashes -- when style == wxUSER_DASH, an array used to
			control the drawing style
			XXX what is the array of? lengths? I assume it's
				just a python list of something, but I don't
				know what.
		"""
		if isinstance( style, enumeration.Enumeration ):
			style = style.value()
		wx.Pen.__init__( self, colour, width, style )
		if isinstance( join, enumeration.Enumeration ):
			join = join.value()
		self.SetJoin( join )
		if isinstance( cap, enumeration.Enumeration ):
			cap = cap.value()
		self.SetCap( cap )
		if style == wx.STIPPLE and stipple is not None:
			self.SetStipple( stipple )
		elif style == wx.USER_DASH and dashes is not None:
			self.SetDashes( dashes )
	def coreValues( self ):
		"""Get the core values for this instance"""
		return dict([
			(attr,getattr(self,'Get%s'%attr.capitalize())())
			for attr in self.coreAttributes
		])
	def __repr__( self ):
		"""Get a nice debugging representation of this object"""
		v = self.coreValues()
		v = ", ".join([
			'%s=%r'%(attr,v.get(attr))
			for attr in self.coreAttributes
			if v.get(attr) is not None
		])
		return "%s(%s)"%( self.__class__.__name__, v)


	def __eq__( self, other ):
		"""Compare our core values to pen defined in other"""
		if not isinstance( other, wx.Pen):
			other = self.__class__.coerce( other )
		a,b = self.coreValues(), other.coreValues()
		if a != b:
			return 0
		# possibility of a stipple or dashes type diff
		if a['style'] == wx.STIPPLE:
			return self.GetStipple() == other.GetStipple()
		elif a['style'] == wx.USER_DASH:
			return self.GetDashes() == other.GetDashes()
		else:
			return 1

	
	def check( cls, value ):
		"""Check that value is a wxPen instance"""
		return isinstance( value, cls )
	check = classmethod( check )
	
	def coerce( cls, value ):
		"""Coerce value to an instance of baseType

		Accepted:
			object: w/ style, colour and width props (cap, join, and stipple optional)
			tuple (colour,width,style,cap,join,stipple)
			dict w/ names
		"""
		if cls.check( value ):
			return value
		if isinstance( value, (tuple,list)):
			return cls( *value )
		elif isinstance( value, dict ):
			return cls( **value )
		else:
			set = {}
			for attribute in cls.coreAttributes+cls.extraAttributes:
				method = 'Get%s'%(attribute.capitalize())
				if hasattr( value, attribute ):
					set[attribute] = getattr(value,attribute)
				elif hasattr( value, method):
					set[attribute] = getattr(value,method)()
			return cls( **set )
	coerce = classmethod( coerce )
		
registry.registerDT( wx.PenPtr, wxPen)

def defaultPen( ):
	return wx.BLACK_PEN

PenStyleSet = enumeration.EnumerationSet()
PenStyleSet.new(name='wxSHORT_DASH',value=wx.SHORT_DASH,friendlyName='Short Dash')
PenStyleSet.new(name='wxSOLID',value=wx.SOLID,friendlyName='Solid ')
PenStyleSet.new(name='wxCROSS_HATCH',value=wx.CROSS_HATCH,friendlyName='Cross-Hatching')
PenStyleSet.new(name='wxVERTICAL_HATCH',value=wx.VERTICAL_HATCH,friendlyName='Vertical Hatching')
PenStyleSet.new(name='wxFDIAGONAL_HATCH',value=wx.FDIAGONAL_HATCH,friendlyName='Forward Diagonal Hatching')
PenStyleSet.new(name='wxLONG_DASH',value=wx.LONG_DASH,friendlyName='Long Dash')
PenStyleSet.new(name='wxUSER_DASH',value=wx.USER_DASH,friendlyName='User Defined Dash')
PenStyleSet.new(name='wxCROSSDIAG_HATCH',value=wx.CROSSDIAG_HATCH,friendlyName='Cross-Diagonal Hatching')
PenStyleSet.new(name='wxHORIZONTAL_HATCH',value=wx.HORIZONTAL_HATCH,friendlyName='Horizontal Hatching')
PenStyleSet.new(name='wxSTIPPLE',value=wx.STIPPLE,friendlyName='Stippled')
PenStyleSet.new(name='wxBDIAGONAL_HATCH',value=wx.BDIAGONAL_HATCH,friendlyName='Diagonal Hatching')
PenStyleSet.new(name='wxTRANSPARENT',value=wx.TRANSPARENT,friendlyName='Transparent')
PenStyleSet.new(name='wxDOT_DASH',value=wx.DOT_DASH,friendlyName='Dot Dash')
PenCapSet = enumeration.EnumerationSet()
PenCapSet.new(name='wxCAP_BUTT',value=wx.CAP_BUTT,friendlyName='Flat')
PenCapSet.new(name='wxCAP_PROJECTING',value=wx.CAP_PROJECTING,friendlyName='Projecting')
PenCapSet.new(name='wxCAP_ROUND',value=wx.CAP_ROUND,friendlyName='Rounded')
PenJoinSet = enumeration.EnumerationSet()
PenJoinSet.new(name='wxJOIN_BEVEL',value=wx.JOIN_BEVEL,friendlyName='Bevel')
PenJoinSet.new(name='wxJOIN_MITER',value=wx.JOIN_MITER,friendlyName='Miter')
PenJoinSet.new(name='wxJOIN_ROUND',value=wx.JOIN_ROUND,friendlyName='Round')

class PenStyle(enumeration.Enumeration):
	"""Enumeration representing a pen-drawing style"""
	set = PenStyleSet
	dataType = enumeration.Enumeration.dataType+'.penstyle'

class PenCap(enumeration.Enumeration):
	"""Enumeration representing a pen-cap style"""
	set = PenCapSet
	dataType = enumeration.Enumeration.dataType+'.pencap'

class PenJoin(enumeration.Enumeration):
	"""Enumeration representing a pen-join style"""
	set = PenJoinSet
	dataType = enumeration.Enumeration.dataType+'.penjoin'


##class PenStandIn( propertied.Propertied ):
##	"""Stand-in object for editing (immutable) wxPen values"""
##	style = basic.BasicProperty(
##		'style', """The line style for the pen""",
##		friendlyName = """Line Style""",
##		baseType = PenStyle,
##		defaultValue = 'wxSOLID',
##	)
##	cap = basic.BasicProperty(
##		'cap', """The cap (end-of-line) style for the pen""",
##		friendlyName = """Cap Style""",
##		baseType = PenCap,
##		defaultValue = 'wxCAP_ROUND',
##	)
##	join = basic.BasicProperty(
##		'join', """The cap (end-of-line) style for the pen""",
##		friendlyName = """Join Style""",
##		baseType = PenJoin,
##		defaultValue = 'wxJOIN_ROUND',
##	)
##	colour = common.ColourProperty(
##		"colour", """The pen colour""",
##		friendlyName = "Colour",
##		defaultValue = (0,0,0),
##	)
##	width = common.IntegerProperty(
##		"width", """The line width of the pen""",
##		defaultValue = 1,
##	)
	

	
	