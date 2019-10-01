#
#       Copyright (C) 2018
#       John Moore (jmooremcc@hotmail.com)
#
#  This Program is free software; you can redistribute it and/or modify
#  it under the terms of the GNU General Public License as published by
#  the Free Software Foundation; either version 2, or (at your option)
#  any later version.
#
#  This Program is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with XBMC; see the file COPYING.  If not, write to
#  the Free Software Foundation, 675 Mass Ave, Cambridge, MA 02139, USA.
#  http://www.gnu.org/copyleft/gpl.html
#

import json
from datetime import datetime, date

from resources.lib.Utilities.Messaging import Cmd

__Version__ = "1.0.0"

"""
This module uses decorators to serialize date objects using json
The filename is PL_json.py
In another module you add the following import statement:
    from PL_json import json

json.dumps and json.dump will correctly serialize datetime and date objects
"""

def json_serial(obj):
    """JSON serializer for objects not serializable by default json code"""

    if isinstance(obj, (datetime, date)):
        serial = str(obj)
        return serial
    elif isinstance(obj,Cmd):
        serial=repr(obj)
        print("Serializing {}".format(serial))
        return serial

    raise TypeError ("Type {} not serializable".format(type(obj)))


def FixDumps(fn):
    def hook(obj):
        return fn(obj, default=json_serial)

    return hook

def FixDump(fn):
    def hook2(obj, fp):
        return fn(obj,fp, default=json_serial)

    return hook2
    

json.dumps=FixDumps(json.dumps)
json.dump=FixDump(json.dump)
    

