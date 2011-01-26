#
#  MythBox for XBMC - http://mythbox.googlecode.com
#  Copyright (C) 2011 analogue@yahoo.com
# 
#  This program is free software; you can redistribute it and/or
#  modify it under the terms of the GNU General Public License
#  as published by the Free Software Foundation; either version 2
#  of the License, or (at your option) any later version.
#
#  This program is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with this program; if not, write to the Free Software
#  Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301, USA.
#
import logging
from mythbox.util import safe_str

#class SafeLogger(logging.LoggerAdapter):
#    '''ConsoleLogger cannot handle non-ascii chars and it is a 
#    PITA when the app fails because a log message was not
#    sanitized with util.safe_str(...) before being passed on.
#    Just decorate an existing logger and sanitize before passing
#    on up the chain...
#    '''
#    
#    def __init__(self, logger):
#        logging.LoggerAdapter.__init__(self, logger, None)
#
#    def debug(self, msg, *args, **kwargs):
#        logging.LoggerAdapter.debug(self, safe_str(msg), *args, **kwargs)
#        
#    def info(self, msg, *args, **kwargs):
#        logging.LoggerAdapter.info(self, safe_str(msg), *args, **kwargs)
#
#    def warning(self, msg, *args, **kwargs):
#        logging.LoggerAdapter.warning(self, safe_str(msg), *args, **kwargs)
#
#    def error(self, msg, *args, **kwargs):
#        logging.LoggerAdapter.error(self, safe_str(msg), *args, **kwargs)
#
#    def exception(self, msg, *args, **kwargs):
#        logging.LoggerAdapter.exception(self, safe_str(msg), *args, **kwargs)
