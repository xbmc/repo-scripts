#
# Contributed by Rodrigo Tobar <rtobar@icrar.org>
#
# ICRAR - International Centre for Radio Astronomy Research
# (c) UWA - The University of Western Australia, 2016
# Copyright by UWA (in the framework of the ICRAR)
#
'''
Wrapper for _yajl2 C extension module
'''
import decimal

from ijson import common
from . import _yajl2 # @UnresolvedImport

def basic_parse(file, **kwargs):
    return _yajl2.basic_parse(file.read, decimal.Decimal, common.JSONError, common.IncompleteJSONError, **kwargs)

def parse(file, **kwargs):
    return _yajl2.parse(file.read, decimal.Decimal, common.JSONError, common.IncompleteJSONError, **kwargs)

def items(file, prefix):
    return _yajl2.items(prefix, file.read, decimal.Decimal, common.JSONError, common.IncompleteJSONError)
