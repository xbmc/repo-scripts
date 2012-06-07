# -*- coding: utf-8 -*-
# xbmc-json utils

import xbmc, xbmcaddon
import traceback

def retrieve_json_dict(json_query, items='items', force_log=False ):
    """ retrieve_json_dict()
        This function returns the response from a json rpc query in a dict(hash) form

        requirements:
            json_query - a properly formed json rpc request for return
            items - the specific key being looked for, example for VideoLibrary.GetMovies - 'movies' is the key, 'items' is a common response(can be left blank then)
    """
    xbmc.log( "[json_utils.py] - JSONRPC Query -\n%s" % json_query, level=xbmc.LOGDEBUG )
    true = True
    false = False
    null = None
    json_response = xbmc.executeJSONRPC(json_query)
    if force_log: 
        xbmc.log( "[json_utils.py] - retrieve_json_dict - JSONRPC -\n%s" % json_response, level=xbmc.LOGDEBUG )
    response = json_response
    if response.startswith( "{" ):
        response = eval( response )
    try:
        result = response['result']
        json_dict = result[items]
        return json_dict
    except:
        traceback.print_exc()
        xbmc.log( "[json_utils.py] - retrieve_json_dict - Error trying to get json response", level=xbmc.LOGDEBUG )
        return None
