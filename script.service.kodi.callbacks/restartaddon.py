#!/usr/bin/python
# -*- coding: utf-8 -*-
#
#     Copyright (C) 2016 KenV99
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
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
import xbmc
import sys

addonid = sys.argv[1]

xbmc.executeJSONRPC('{"jsonrpc":"2.0","method":"Addons.SetAddonEnabled", "params":{"addonid":"%s","enabled":"toggle"},"id":1}' % addonid)
xbmc.log(msg='***** Toggling addon enabled 1: %s' % addonid)
xbmc.sleep(1000)
xbmc.executeJSONRPC('{"jsonrpc":"2.0","method":"Addons.SetAddonEnabled", "params":{"addonid":"%s","enabled":"toggle"},"id":1}' % addonid)
xbmc.log(msg='***** Toggling addon enabled 2: %s' % addonid)
