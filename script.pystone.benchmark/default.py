#   Copyright (C) 2025 Lunatixz
#
#
# This file is part of CPU Benchmark.
#
# CPU Benchmark is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# CPU Benchmark is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with CPU Benchmark.  If not, see <http://www.gnu.org/licenses/>.

# -*- coding: utf-8 -*-

#entrypoint
import os, json
from resources.lib import cpubenchmark

if __name__ == '__main__': 
    DEBUG_ENABLED = json.loads(xbmc.executeJSONRPC(json.dumps({"jsonrpc":"2.0","id":"script.pystone.benchmark","method":"Settings.GetSettingValue","params":{"setting":"debug.showloginfo"}}))).get('result',{}).get('value',False) 
    if not DEBUG_ENABLED: xbmc.executeJSONRPC(json.dumps({"jsonrpc":"2.0","id":"script.pystone.benchmark","method":"Settings.SetSettingValue","params":{"setting":"debug.showloginfo","value":True}}))
    try: cpubenchmark.TEXTVIEW("DialogTextViewer.xml", os.getcwd(), "Default")
    except: pass
    if not DEBUG_ENABLED: xbmc.executeJSONRPC(json.dumps({"jsonrpc":"2.0","id":"script.pystone.benchmark","method":"Settings.SetSettingValue","params":{"setting":"debug.showloginfo","value":False}}))
    
    
    