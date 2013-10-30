""" Custom Exceptions """

__author__ = "Alastair Tse <alastair@tse.id.au>"
__license__ = "BSD"
__copyright__ = "Copyright (c) 2004, Alastair Tse" 

__revision__ = "$Id: exceptions.py,v 1.2 2004/05/04 12:18:21 acnt2 Exp $"

class ID3Exception(Exception):
	"""General ID3Exception"""
	pass

class ID3EncodingException(ID3Exception):
	"""Encoding Exception"""
	pass

class ID3VersionMismatchException(ID3Exception):
	"""Version Mismatch problems"""
	pass

class ID3HeaderInvalidException(ID3Exception):
	"""Header is malformed or none existant"""
	pass

class ID3ParameterException(ID3Exception):
	"""Parameters are missing or malformed"""
	pass

class ID3FrameException(ID3Exception):
	"""Frame is malformed or missing"""
	pass

class ID3NotImplementedException(ID3Exception):
	"""This function isn't implemented"""
	pass

