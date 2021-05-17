#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
    unmanic

    Written by:               Josh.5 <jsunnex@gmail.com>
    Date:                     07 Dec 2020, (21:07 PM)

    Copyright:
        Copyright (C) 2021 Josh Sunnex

        This program is free software: you can redistribute it and/or modify it under the terms of the GNU General
        Public License as published by the Free Software Foundation, version 3.

        This program is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY; without even the
        implied warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU General Public License
        for more details.

        You should have received a copy of the GNU General Public License along with this program.
        If not, see <https://www.gnu.org/licenses/>.

"""

import os
import xbmc
import threading


class KodiLogPipe(threading.Thread):
    def __init__(self, level):
        threading.Thread.__init__(self)
        self.daemon = False
        self.level = level
        self.fd_read, self.fd_write = os.pipe()
        self.pipe_reader = os.fdopen(self.fd_read)
        self.start()

    def fileno(self):
        """
        Return the pipe's write file descriptor

        :return:
        """
        return self.fd_write

    def run(self):
        """
        Run the thread and log everything

        :return:
        """
        for line in iter(self.pipe_reader.readline, ''):
            xbmc.log(line.strip('\n'), level=self.level)

        self.pipe_reader.close()

    def close(self):
        """
        Close the write end of the pipe

        :return:
        """
        os.close(self.fd_write)
