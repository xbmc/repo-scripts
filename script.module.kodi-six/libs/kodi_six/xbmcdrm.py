# coding: utf-8
# Created on: 20.01.2019
# Author: Roman Miroshnychenko aka Roman V.M. (roman1972@gmail.com)
"""
A class for working with DRM
"""

from __future__ import absolute_import
import sys as _sys
from xbmcdrm import *
from .utils import PY2 as _PY2, patch_module as _patch_module

if _PY2:
    _patch_module(_sys.modules[__name__])
