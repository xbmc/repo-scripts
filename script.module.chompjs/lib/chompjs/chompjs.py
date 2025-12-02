# -*- coding: utf-8 -*-

import json
import sys

from _chompjs import parse


def parse_js_object(string, unicode_escape=False, jsonlines=False, json_params=None):
    if not string:
        raise ValueError('Invalid input')
    if unicode_escape:
        string = string.encode().decode('unicode_escape')
    if sys.version_info[0] < 3:
        string = string.encode('utf-8')

    if not json_params:
        json_params = {}

    parsed_data = parse(string, jsonlines)

    if jsonlines:
        return [json.loads(j, **json_params) for j in parsed_data.split('\0')]
    else:
        return json.loads(parsed_data, **json_params)
