# -*- coding: utf-8 -*-
# xbmc-json utils

import traceback

import xbmc


def retrieve_json_dict(json_query, items='items', force_log=False):
    """ retrieve_json_dict()
        This function returns the response from a json rpc query in a dict(hash) form

        requirements:
            json_query - a properly formed json rpc request for return
            items - the specific key being looked for, example for VideoLibrary.GetMovies - 'movies' is the key, 'items' is a common response(can be left blank then)
    """
    empty = []
    xbmc.log("[json_utils.py] - JSONRPC Query -\n%s" % json_query, level=xbmc.LOGDEBUG)
    true = True
    false = False
    null = None
    response = xbmc.executeJSONRPC(json_query)
    if force_log:
        xbmc.log("[json_utils.py] - retrieve_json_dict - JSONRPC -\n%s" % response, level=xbmc.LOGDEBUG)
    if response.startswith("{"):
        response = eval(response)
        try:
            if response.has_key('result'):
                result = response['result']
                json_dict = result[items]
                return json_dict
            else:
                xbmc.log("[json_utils.py] - retrieve_json_dict - No response from XBMC", level=xbmc.LOGNOTICE)
                xbmc.log(response, level=xbmc.LOGDEBUG)
                return None
        except:
            traceback.print_exc()
            xbmc.log("[json_utils.py] - retrieve_json_dict - JSONRPC -\n%s" % response, level=xbmc.LOGNOTICE)
            xbmc.log("[json_utils.py] - retrieve_json_dict - Error trying to get json response", level=xbmc.LOGNOTICE)
            return empty
    else:
        return empty
