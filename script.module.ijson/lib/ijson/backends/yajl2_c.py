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

from ijson import common, compat
from . import _yajl2 # @UnresolvedImport

def basic_parse(file, **kwargs):
    f = compat.bytes_reader(file)
    return _yajl2.basic_parse(f.read, decimal.Decimal, common.JSONError, common.IncompleteJSONError, **kwargs)

def parse(file, **kwargs):
    f = compat.bytes_reader(file)
    return _yajl2.parse(f.read, decimal.Decimal, common.JSONError, common.IncompleteJSONError, **kwargs)

def items(file, prefix, map_type=None, **kwargs):
    f = compat.bytes_reader(file)
    return _yajl2.items(prefix, f.read, decimal.Decimal, common.JSONError, common.IncompleteJSONError, map_type, **kwargs)

def kvitems(file, prefix, map_type=None, **kwargs):
    f = compat.bytes_reader(file)
    return _yajl2.kvitems(prefix, f.read, decimal.Decimal, common.JSONError, common.IncompleteJSONError, map_type, **kwargs)
