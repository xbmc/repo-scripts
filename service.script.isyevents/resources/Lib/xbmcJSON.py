'''
    ISY Event Engine for XBMC (xbmcJSON)
    Copyright (C) 2013 Ryan M. Kraus

    LICENSE:
    This program is free software: you can redistribute it and/or modify
    it under the terms of the GNU General Public License as published by
    the Free Software Foundation, either version 2 of the License, or
    (at your option) any later version.

    This program is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU General Public License for more details.

    You should have received a copy of the GNU General Public License
    along with this program.  If not, see <http://www.gnu.org/licenses/>.
    
    DESCRIPTION:
    This Python Module interacts with XBMC's JSON RPC API through 
    the local Python transport mechanism.
    
    WRITTEN:    4/2013
'''

# imports
import xbmc
import ast

def GetPlayerID():
    request = {"jsonrpc":"2.0","id":0,"method":"Player.GetActivePlayers","params":{}}
    result = _executeJSON(request)
    player_id = result[0]['playerid']
    return player_id
    
def GetPlayerSpeed(player_id=1):
    request = {"jsonrpc":"2.0","id":0,"method":"Player.GetProperties","params":{"playerid":player_id,"properties":["speed"]}}
    result = _executeJSON(request)
    player_speed = result['speed']
    return player_speed


def _executeJSON(request):
    request = str(request).replace("'", '"')
    str_result = xbmc.executeJSONRPC(request)
    result = ast.literal_eval(str_result)['result']
    return result