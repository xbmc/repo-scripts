"""Data-type definition for wxPython font class"""
from wxPython.wx import *
from basictypes import datatypedefinition, registry
##from basictypes.wx import wxcopyreg

__all__ = ( "wxFont_DT", )

class wxFont_DT( datatypedefinition.BaseType_DT ):
	"""Data-type definition for wxPython font class"""
	dataType = "wx.font"
	baseType = wxFontPtr
registry.registerDT( wxFontPtr, wxFont_DT)
registry.registerDT( wxFont, wxFont_DT)
