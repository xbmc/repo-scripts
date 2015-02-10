import xbmc
import ast


def GetPlayerID():
    request = {"jsonrpc": "2.0", "id": 0, "method": "Player.GetActivePlayers",
               "params": {}}
    try:
        result = _executeJSON(request)
        player_id = result[0]['playerid']
        return player_id
    except:
        pass


def GetPlayerSpeed(player_id=1):
    request = {"jsonrpc": "2.0", "id": 0, "method": "Player.GetProperties",
               "params": {"playerid": player_id, "properties": ["speed"]}}
    try:
        result = _executeJSON(request)
        player_speed = result['speed']
        return player_speed
    except:
        pass


def _executeJSON(request):
    request = str(request).replace("'", '"')
    str_result = xbmc.executeJSONRPC(request)
    result = ast.literal_eval(str_result)['result']
    return result
