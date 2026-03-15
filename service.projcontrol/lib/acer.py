# -*- coding: utf-8 -*-
# Copyright (c) 2015,2018 Fredrik Eriksson <git@wb9.se>
#               2018 Petter Reinholdtsen <pere@hungry.com>
#               2022 Michael Spreng <code@m.spreng.ch>
# This file is covered by the MIT license, read LICENSE for details.

"""Module for communicating with Acer projectors supporting RS232
serial interface.

Parameter Rs232 : 9600 / 8 / N / 1

1 OKOKOKOKOK\r Power On
2 * 0 IR 001\r Power On
3 * 0 IR 002\r Power Off
4 * 0 IR 004\r Keystone
5 * 0 IR 006\r Mute
6 * 0 IR 007\r Freeze
7 * 0 IR 008\r Menu
8 * 0 IR 009\r Up
9 * 0 IR 010\r Down
10 * 0 IR 011\r Right
11 * 0 IR 012\r Left
12 * 0 IR 013\r Enter
13 * 0 IR 014\r Re-Sync
14 * 0 IR 015\r Source Analog RGB for D-sub
15 * 0 IR 016\r Source Digital RGB
16 * 0 IR 017\r Source PbPr for D-sub
17 * 0 IR 018\r Source S-Video
18 * 0 IR 019\r Source Composite Video
19 * 0 IR 020\r Source Component Video
20 * 0 IR 021\r Aspect ratio 16:9
21 * 0 IR 022\r Aspect ratio 4:3
22 * 0 IR 023\r Volume +
23 * 0 IR 024\r Volume –
24 * 0 IR 025\r Brightness
25 * 0 IR 026\r Contrast
26 * 0 IR 027\r Color Temperature
27 * 0 IR 028\r Source Analog RGB for DVI Port
28 * 0 IR 029\r Source Analog YPbPr for DVI Port
29 * 0 IR 030\r Hide
30 * 0 IR 031\r Source
31 * 0 IR 032\r Video: Color saturation adjustment
32 * 0 IR 033\r Video: Hue adjustment
33 * 0 IR 034\r Video: Sharpness adjustment
34 * 0 IR 035\r Query Model name
35 * 0 IR 036\r Query Native display resolution
36 * 0 IR 037\r Query company name
37 * 0 IR 040\r Aspect ratioL.Box
38 * 0 IR 041\r Aspect ratio 1:1
39 * 0 IR 042\r Keystone Up
40 * 0 IR 043\r Keystone Down
41 * 0 IR 044\r Keystone Left
42 * 0 IR 045\r Keystone Right
43 * 0 IR 046\r Zoom
44 * 0 IR 047\r e-Key
45 * 0 IR 048\r Color RGB
46 * 0 IR 049\r Language
47 * 0 IR 050\r Source HDMI

   * 0 Src ?\r  Get current source
Answer: Src 0   no signal on currently selected input (does not tell which one is selected)
        Src 1   VGA
        Src 8   HDMI

   * 0 Lamp\r   Lamp operation hours
Answer: 0001    four digit number (hours)

OK:    in case command was understood, projector answers with *000
Error: in case of error, projector answers with *001
"""

import os
import time
import re
import select

import serial

import lib.commands
import lib.errors
from lib.helpers import log

# List of all valid models and their input sources
# Remember to add new models to the settings.xml-file as well
_valid_sources_ = {
        "generic/X1373WH": {
            "VGA":       ("Src 1", "015"),
            "S-Video":   ("Src ?", "018"), # don't know response
            "Composite": ("Src ?", "019"), # don't know response
            "HDMI":      ("Src 8", "050"),
            },
        "V7500": {
            "VGA - RGB":  ("Src 1", "015"),
            "VGA - PbPr": ("Src ?", "017"), # don't know response
            "Composite":  ("Src ?", "019"), # don't know response
            "Component":  ("Src ?", "020"), # don't know response
            "HDMI":       ("Src 8", "050"),
            }
        }

# map the generic commands to ESC/VP21 commands
_command_mapping_ = {
        lib.CMD_PWR_ON: "* 0 IR 001",
        lib.CMD_PWR_OFF: "* 0 IR 002",
        lib.CMD_PWR_QUERY: "* 0 IR 037",

        lib.CMD_SRC_QUERY: "* 0 Src ?",
        lib.CMD_SRC_SET: "* 0 IR {source_id}",
        }

_serial_options_ = {
        "baudrate": 9600,
        "bytesize": serial.EIGHTBITS,
        "parity": serial.PARITY_NONE,
        "stopbits": serial.STOPBITS_ONE
}

def get_valid_sources(model):
    """Return all valid source strings for this model"""
    if model in _valid_sources_:
        return list(_valid_sources_[model].keys())
    return None

def get_serial_options():
    return _serial_options_

def get_source_id(model, source):
    """Return the "real" source ID based on projector model and human readable
    source string"""
    if model in _valid_sources_ and source in _valid_sources_[model]:
        return _valid_sources_[model][source]
    return None

class ProjectorInstance:

    def __init__(self, model, ser, timeout=5):
        """Class for managing Acer projectors

        :param model: projector model
        :param ser: open Serial port for the serial console
        :param timeout: time to wait for response from projector
        """
        self.serial = ser
        self.timeout = timeout
        self.model = model
        res = self._verify_connection()
        if not res:
            raise lib.errors.ProjectorError(
                    "Could not verify ready-state of projector"
                    #"Verify returned {}".format(res)
                    )


    def _verify_connection(self):
        """Verify that the projecor is ready to receive commands.  Use the
        name command to see if we get a valid response.

        """

        return True

        # projector is quite slow to react to rs232 commands.
        # no good command found for checking so often

        log("start verify with: '{}'".format(_command_mapping_[lib.CMD_PWR_QUERY]))
        res = self._send_command(_command_mapping_[lib.CMD_PWR_QUERY], for_verify=True)
        if res == "*001":
            # in case the projector is off
            return True
        elif res:
            # in case the projector is on, it will also send the name. Discard it:
            self._read_response()
            return True
        return False

    def _read_response(self):
        """Read response from projector"""
        read = ""
        res = ""
        time.sleep(0.5)
        while not read.endswith("\r"):
            r, w, x = select.select([self.serial.fileno()], [], [], self.timeout)
            if len(r) == 0:
                raise lib.errors.ProjectorError(
                        "Timeout when reading response from projector"
                        )
            for f in r:
                try:
                    read = os.read(f, 1).decode('utf-8')
                    res += read
                except OSError as e:
                    raise lib.errors.ProjectorError(
                            "Error when reading response from projector: {}".format(e),
                            )
                    return None

        part = res.strip('\r')
        log("projector responded: '{}'".format(part))
        return part


    def _send_command(self, cmd_str, for_verify = False):
        """Send command to the projector.

        :param cmd_str: Full raw command string to send to the projector
        """
        log("sending command '{}'".format(cmd_str))
        ret = None
        try:
            self.serial.write("{}\r\n".format(cmd_str).encode('utf-8'))
        except OSError as e:
            raise lib.errors.ProjectorError(
                    "Error when Sending command '{}' to projector: {}".\
                        format(cmd_str, e)
                    )
            return ret

        ret = self._read_response()

        if for_verify:
            return ret
        else:
            return ret == "*000"

    def _power_on(self):
        if self._power_query():
            log("PWR_ON: Projector already turned on")
            return True
        else:
            res = self._send_command("* 0 IR 001")
            # wait 10 seconds. The projector needs some time to start up.
            # For some time commands are ignored and it acts like it is still off.
            # So wait long enough until things ares settled.
            time.sleep(10)
            return res

    def _power_off(self):
        return self._send_command("* 0 IR 002")

    def _power_query(self):
        res = self._send_command("* 0 IR 037")
        # If turned on, projector returns Name Acer. Consume that part as well.
        if res:
            self._read_response()
        return res

    def _source_query(self):
        res = self._send_command("* 0 Src ?")
        if not res:
            raise lib.errors.InvalidCommandError("Get source command failed")
        res = self._read_response()
        log("query source returned {}".format(res))
        return res

    def _source_set(self, source_id):
        source = self._source_query()
        if source == source_id[0]:
            log("SRC_SET: Correct source already set")
            return True
        cmd_str = "* 0 IR {}".format(source_id[1])
        res = self._send_command(cmd_str)
        # Switching the source takes quite some time. During that time
        # the source_query command returns "Src 0" for no signal.
        # Wait long enough, so it will return the correct source after
        # this command has completed
        time.sleep(10)
        # for debugging: check which source is now active
        self._source_query()
        return res

    def send_command(self, command, source_id = "undefined", **kwargs):
        """Send command to the projector.

        :param command: A valid command from lib
        :param **kwargs: Optional parameters to the command. For Acer the
            valid keyword is "source_id" on CMD_SRC_SET

        :return: True or False on CMD_PWR_QUERY, a source string on
            CMD_SRC_QUER, otherwise None.
        """

        if   command == lib.CMD_PWR_ON:
            res = self._power_on()
        elif command == lib.CMD_PWR_OFF:
            res = self._power_off()
        elif command == lib.CMD_PWR_QUERY:
            res = self._power_query()
        elif command == lib.CMD_SRC_SET:
            res = self._source_set(source_id)
        elif command == lib.CMD_SRC_QUERY:
            internal = self._source_query()
            res = ""
            for source in _valid_sources_[self.model]:
                if _valid_sources_[self.model][source][0] == internal:
                    res = source
                    break
            if res == "":
                raise lib.errors.InvalidCommandError(
                    "Command get source returned unexpected result {}".format(internal)
                    )
        else:
            raise lib.errors.InvalidCommandError(
                    "Command {} not supported".format(command)
                    )

        return res
