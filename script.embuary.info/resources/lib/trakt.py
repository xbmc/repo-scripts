#!/usr/bin/python
# coding: utf-8

########################

import xbmc
import requests

from resources.lib.helper import *

########################

def trakt_api(call=None):
    headers = {
              'Content-Type': 'application/json',
              'trakt-api-version': '2',
              'trakt-api-key': 'db17981042166c60e1642c483f5be54b12ec86e3401cd67c2514fdf6843a110f'
              }

    request_url = 'https://api.trakt.tv' + call

    for i in range(1,4): # loop if heavy server load
        try:
            request = requests.get(request_url, timeout=5, headers=headers)

            if not request.ok:
                raise Exception(str(request.status_code))

        except Exception as error:
            log('Trakt server error: Code ' + str(error), ERROR)
            xbmc.sleep(500)

        else:
            return request.json()