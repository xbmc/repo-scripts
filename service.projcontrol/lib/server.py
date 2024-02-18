# -*- coding: utf-8 -*-
# Copyright (c) 2015,2018 Fredrik Eriksson <git@wb9.se>
# This file is covered by the BSD-3-Clause license, read LICENSE for details.

import json
import logging

import bottle
import wsgiref.simple_server

import lib.commands


class StoppableWSGIRefServer(bottle.ServerAdapter):
    server = None

    def run(self, handler):
        self.server = wsgiref.simple_server.make_server(self.host, self.port, handler, **self.options)
        self.server.serve_forever()

    def stop(self):
        self.server.shutdown()


app = bottle.Bottle()

@app.get('/')
def start():
    bottle.response.content_type = "application/json"
    return json.dumps([ "power", "source"])

@app.get('/power')
def power():
    bottle.response.content_type = "application/json"
    return json.dumps(lib.commands.report())

@app.post('/power')
def power_req():
    bottle.response.content_type = "application/json"
    ret = {'success': False}

    try:
        data = bottle.request.json
    except ValueError as e:
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

@app.get('/source')
def source():
    bottle.response.content_type = "application/json"
    valid_sources = lib.commands.get_available_sources()
    return json.dumps({'sources': valid_sources})

@app.post('/source')
def source_req():
    bottle.response.content_type = "application/json"
    valid_sources = lib.commands.get_available_sources()
    ret = {'success': False}
    try:
        data = bottle.request.json
    except ValueError as e:
        return json.dumps(ret)

    if data in valid_sources:
        ret['success'] = lib.commands.set_source(data)
    return json.dumps(ret)

_server_ = None

def init_server(port, address):
    """Start the bottle web server.

    :param port: port to listen on
    :param address: address to bind to
    """
    global _server_
    if _server_:
        stop_server()

    _server_ = StoppableWSGIRefServer(host=address, port=port)
    app.run(server=_server_)

def stop_server():
    _server_.stop()
