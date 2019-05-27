# -*- coding: utf-8 -*-
# Copyright (c) 2015,2018 Fredrik Eriksson <git@wb9.se>
# This file is covered by the BSD-3-Clause license, read LICENSE for details.

"""High level commands that can be used on the projectors"""
import multiprocessing
import os

import serial

import xbmc
import xbmcaddon

import lib
import lib.epson
import lib.infocus
import lib.errors
import lib.helpers

__addon__ =  xbmcaddon.Addon()
__cmd_lock__ = multiprocessing.Lock()

def _get_proj_module_():
    manufacturer = __addon__.getSetting("manufacturer")
    if manufacturer == "Epson":
        return lib.epson
    if manufacturer == "InFocus":
        return lib.infocus
    else:
        raise lib.errors.ConfigurationError("Manufacturer {} is not supported".format(manufacturer))

def _get_configured_model_():
    manufacturer = __addon__.getSetting("manufacturer")
    if manufacturer == "Epson":
        model = __addon__.getSetting("epson_model")
    elif manufacturer == "InFocus":
        model = __addon__.getSetting("infocus_model")
    else:
        raise lib.errors.ConfigurationError("Manufacturer {} is not supported".format(manufacturer))
    return model


def open_proj():
    """Open the serial device, only intended to be used from do_cmd()
    
    :return: a file descriptor or None
    """
    try:
        mod = _get_proj_module_()
    except lib.errors.ConfigurationError as e:
        lib.helpers.display_error_message(32203)
        return None
    
    kwargs = mod.get_serial_options()
    
    try:
        s = serial.Serial( __addon__.getSetting("device"), **kwargs)
        return s
    except (OSError, serial.SerialException) as e:
        lib.helpers.display_error_message(32204)
        return None

def do_cmd(command, **kwargs):
    """Execute a command to the projector and return any output.

    :param command: one of the commands from lib
    :param **kwargs: optional arguments to command

    :return: output from projector or None
    """
    res = None
    with __cmd_lock__:
        ser = open_proj()
        if ser:
            try:
                mod = _get_proj_module_()
                model = _get_configured_model_()
                proj = mod.ProjectorInstance(
                        model,
                        ser, 
                        int(__addon__.getSetting("timeout")))
            except lib.errors.ProjectorError as pe:
                lib.helpers.display_error_message(32205)
                lib.helpers.log("Failed to open projector: {}".format(pe))
                ser.close()
                return res

            try:
                res = proj.send_command(command, **kwargs)
            except lib.errors.ProjectorError as pe:
                lib.helpers.display_error_message(32206)
                lib.helpers.log("Failed to send command to projector: {}".format(pe))
            ser.close()
    lib.helpers.log("do_cmd returns: {}".format(res))
    return res

def start():
    """Start the projector"""
    do_cmd(lib.CMD_PWR_ON)
    if __addon__.getSetting("set_input") == "true":
        set_source(__addon__.getSetting("input_source"))

def stop(final_shutdown=False):
    """Shut down the projector"""
    do_cmd(lib.CMD_PWR_OFF)
    if __addon__.getSetting("lib_update") == "true" and not final_shutdown:
        if __addon__.getSetting("update_music") == "true":
            xbmc.executebuiltin('UpdateLibrary(music)')
        if __addon__.getSetting("update_video") == "true":
            xbmc.executebuiltin('UpdateLibrary(video)')

def toggle_power():
    """Toggle the power to the projector"""
    if do_cmd(lib.CMD_PWR_QUERY):
        stop()
    else:
        start()

def report():
    """Report current power status and used source.
    
    :return: a dict containing 'power' and 'source' entries.
    """

    pwr = do_cmd(lib.CMD_PWR_QUERY)
    src = do_cmd(lib.CMD_SRC_QUERY)
    return {"power": pwr, "source": src}

def set_source(source):
    """Set input source for projector. To get a list of valid source strings,
    use GET on /source or call get_available_sources().

    :param source: valid input source string
    """
    mod = _get_proj_module_()
    model = _get_configured_model_()
    src_id = mod.get_source_id(model, source)
    if not src_id:
        lib.helpers.display_error_message(32207, ": {}".format(source))
        return False
    do_cmd(lib.CMD_SRC_SET, source_id=src_id)
    return True

def get_available_sources():
    """Return a list valid sources for the configured projector."""
    mod = _get_proj_module_()
    model = _get_configured_model_()
    return mod.get_valid_sources(model)
