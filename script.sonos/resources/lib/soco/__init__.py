# -*- coding: utf-8 -*-

"""SoCo (Sonos Controller) is a simple library to control Sonos speakers."""

# There is no need for all strings here to be unicode, and Py2 cannot import
# modules with unicode names so do not use from __future__ import
# unicode_literals
# https://github.com/SoCo/SoCo/issues/98
#

import logging

from .compat import NullHandler
from .core import SoCo
from .discovery import discover
from .exceptions import SoCoException, UnknownSoCoException

# Will be parsed by setup.py to determine package metadata
__author__ = 'The SoCo-Team <python-soco@googlegroups.com>'
__version__ = '0.11.1'
__website__ = 'https://github.com/SoCo/SoCo'
__license__ = 'MIT License'

#####################################
# Actual version: 3rd August 2016 (9bb5f0c3461e877d4252fd0009fd7e972ded0781)
#####################################
# Also added fixes for:
# #409 Event bugfixes.
# #383 Added support for getting Sonos Favorites. Fixed some bugs with getting Radio Shows
# #413 Add sleep timer


# You really should not `import *` - it is poor practice
# but if you do, here is what you get:
__all__ = [
    'discover',
    'SoCo',
    'SoCoException',
    'UnknownSoCoException',
]

# http://docs.python.org/2/howto/logging.html#library-config
# Avoids spurious error messages if no logger is configured by the user

logging.getLogger(__name__).addHandler(NullHandler())
