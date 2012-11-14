"""wxcopyreg -- functions for storing/restoring simple wxPython data types to pickle-friendly formats

importing this module installs the functions automatically!
"""
import pickle, zlib
from wxPython.wx import *

##


def bind( classObject, outFunction, inFunction ):
	"""Bind get and set state for the classObject"""
	classObject.__getstate__ = outFunction
	classObject.__setstate__ = inFunction
	


def wxColourOut( value ):
	return value.Red(), value.Green(), value.Blue()
def wxColourIn( self, args ):
	self.this = apply(gdic.new_wxColour,args)
	self.thisown = 1

bind( wxColourPtr, wxColourOut, wxColourIn )


def wxFontOut( value ):
	return (
		value.GetPointSize(),
		value.GetFamily(),
		value.GetStyle(),
		value.GetWeight(),
		value.GetUnderlined(),
		value.GetFaceName(),
		# note that encoding is missing...
	)
def wxFontIn( self, args ):
	self.this = apply(fontsc.new_wxFont,args)
	self.thisown = 1

bind( wxFontPtr, wxFontOut, wxFontIn )


def wxPenOut( value ):
	colour = value.GetColour()
	return (
		(
			colour.Red(),
			colour.Green(),
			colour.Blue()
		),
		(
			value.GetWidth(),
			value.GetStyle(),
		),
		(
			#stipple is a bitmap, we don't currently have
			#mechanisms for storing/restoring it, so ignore it
##              value.GetStipple(),
			value.GetJoin(),
			# missing in the current wxPython pre-release
			# should be available in wxPython 2.3.3 final
##              value.GetDashes(),
			value.GetCap(),
		),
	)
def wxPenIn( self, (colour, init, props) ):
	colour = wxColour( *colour )
	self.this = apply(gdic.new_wxPen,(colour,)+init)
	self.thisown = 1
	for prop, function in map( None, props, (
			#stipple is a bitmap, we don't currently have
			#mechanisms for storing/restoring it, so ignore it
##          self.SetStipple,
			self.SetJoin,
			# missing in the current wxPython pre-release
			# should be available in wxPython 2.3.3 final
##          self.SetDashes,
		self.SetCap
	)):
		function( prop )


def wxPyPenIn( self, (colour, init, props) ):
	colour = wxColour( *colour )
	self.this = apply(gdic.new_wxPyPen,(colour,)+init)
	self.thisown = 1
	for prop, function in map( None, props, (
			#stipple is a bitmap, we don't currently have
			#mechanisms for storing/restoring it, so ignore it
##          self.SetStipple,
			self.SetJoin,
			# missing in the current wxPython pre-release
			# should be available in wxPython 2.3.3 final
##          self.SetDashes,
		self.SetCap
	)):
		function( prop )
		

bind( wxPenPtr, wxPenOut, wxPenIn )
bind( wxPyPenPtr, wxPenOut, wxPyPenIn )


def wxImageOut( value ):
	width,height = value.GetWidth(), value.GetHeight()
	data = value.GetData()
	data = zlib.compress( data )
	return ( width, height, data )
def wxImageIn( self, (width, height, data) ):
	self.this = apply(imagec.wxEmptyImage,(width,height))
	self.thisown = 1
	self.SetData( zlib.decompress( data) )

bind( wxImagePtr, wxImageOut, wxImageIn )



def test():
	for o in [
		wxColour( 23,23,23),
		wxFont( 12, wxMODERN, wxNORMAL, wxNORMAL ),
		wxPen(wxColour( 23,23,23),1,wxSOLID),
		wxImage( 'test.jpg', wxBITMAP_TYPE_ANY ),
	]:
		o2 = pickle.loads(pickle.dumps(o))
		print o2
		
if __name__ == "__main__":
	wxInitAllImageHandlers()
	test()