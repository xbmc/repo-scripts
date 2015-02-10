#!/usr/bin/python
# -*- coding: utf-8 -*-
#
#     Copyright (C) 2011-2014 Martijn Kaijser
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 2 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with this program. If not, see <http://www.gnu.org/licenses/>.
#

class BaseError(Exception):
    def __init__(self, value):
        self.value = value
    def __str__(self):
        return repr(self.value)

class CopyError(BaseError): pass
class DownloadError(BaseError): pass
class XmlError(BaseError): pass
class MediatypeError(BaseError): pass
class DeleteError(BaseError): pass
class CreateDirectoryError(BaseError): pass
class HTTP400Error(BaseError): pass
class HTTP404Error(BaseError): pass
class HTTP503Error(BaseError): pass
class HTTPTimeout(BaseError): pass
class NoFanartError(BaseError): pass
class ItemNotFoundError(BaseError): pass
