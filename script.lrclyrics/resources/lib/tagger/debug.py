"""
Debugging Functions
"""
__author__ = "Alastair Tse <alastair@tse.id.au>"
__license__ = "BSD"
__copyright__ = "Copyright (c) 2004, Alastair Tse" 
__revision__ = "$Id: debug.py,v 1.3 2004/12/21 12:02:06 acnt2 Exp $"

ID3V2_DEBUG = 0

def debug(args):
	if ID3V2_DEBUG > 1: print args
def warn(args):
	if ID3V2_DEBUG > 0: print args
def error(args):
	print args
