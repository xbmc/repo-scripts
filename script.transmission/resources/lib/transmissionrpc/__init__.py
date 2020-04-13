# -*- coding: utf-8 -*-
# Copyright (c) 2008-2013 Erik Svensson <erik.public@gmail.com>
# Licensed under the MIT license.

from resources.lib.transmissionrpc.constants import DEFAULT_PORT, DEFAULT_TIMEOUT, PRIORITY, RATIO_LIMIT, LOGGER
from resources.lib.transmissionrpc.error import TransmissionError, HTTPHandlerError
from resources.lib.transmissionrpc.httphandler import HTTPHandler, DefaultHTTPHandler
from resources.lib.transmissionrpc.torrent import Torrent
from resources.lib.transmissionrpc.session import Session
from resources.lib.transmissionrpc.client import Client
from resources.lib.transmissionrpc.utils import add_stdout_logger, add_file_logger

__author__    		= 'Erik Svensson <erik.public@gmail.com>'
__version_major__   = 0
__version_minor__   = 11
__version__   		= '{0}.{1}'.format(__version_major__, __version_minor__)
__copyright__ 		= 'Copyright (c) 2008-2013 Erik Svensson'
__license__   		= 'MIT'
