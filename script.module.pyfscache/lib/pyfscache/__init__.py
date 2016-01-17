#! /usr/bin/env python

'''
pyfscache: A file system cache for python.
Copyright (c) 2013, James C. Stroud; All rights reserved.
'''

from _version import __version__

from pyfscache import *

__all__ = ["FSCache", "make_digest",
           "auto_cache_function", "cache_function", "to_seconds"]
