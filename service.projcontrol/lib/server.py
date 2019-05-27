# -*- coding: utf-8 -*-
# Copyright (c) 2015,2018 Fredrik Eriksson <git@wb9.se>
# This file is covered by the BSD-3-Clause license, read LICENSE for details.

import json
import logging

import bottle
from bottle import get, post, request, response, run
import simplejson

import lib.commands

@get('/')
def start():
    response.content_type = "application/json"
    return json.dumps([ "power", "source"])

@get('/power')
def power():
    response.content_type = "application/json"
    return json.dumps(lib.commands.report())

@post('/power')
def power_req():
    response.content_type = "application/json"
    ret = {'success': False}
    
    try:
        data = request.json
    except (simplejson.JSONDecodeError, ValueError) as e:
        return json.dumps(ret)

    if data == 'on':
        lib.commands.start()
        ret['success'] = True
    elif data == 'off':
        lib.commands.stop()
        ret['success'] = True
    elif data == 'toggle':
        lib.commands.toggle_power()
        ret['success'] = True
    return json.dumps(ret)

@get('/source')
def source():
    response.content_type = "application/json"
    valid_sources = lib.commands.get_available_sources()
    return json.dumps({'sources': valid_sources})

@post('/source')
def source_req():
    response.content_type = "application/json"
    valid_sources = lib.commands.get_available_sources()
    ret = {'success': False}
    try:
        data = request.json
    except (simplejson.JSONDecodeError, ValueError) as e:
        return json.dumps(ret)

    if data in valid_sources:
        ret['success'] = lib.commands.set_source(data)
    return json.dumps(ret)


def init_server(port, address):
    """Start the bottle web server.
    
    :param port: port to listen on
    :param address: address to bind to
    """
    run(host=address, port=port)
