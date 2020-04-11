# -*- coding: utf-8 -*-

import os
from io import FileIO

from resources.lib.utils import decode

SEPARATOR = b"\n"


class LogReader(object):
    def __init__(self, filename, buf_size=8192):
        self._filename = filename
        self._buf_size = buf_size
        self._offset = 0

    def tail(self):
        file_size = self.file_size()
        if file_size < self._offset:
            self._offset = 0
        if file_size == self._offset:
            return ""

        with FileIO(self._filename, "rb") as fh:
            fh.seek(self._offset)
            self._offset = file_size
            return decode(fh.read())

    def set_offset(self, offset):
        self._offset = offset

    def get_offset(self):
        return self._offset

    def read(self, invert=False, lines_number=0):
        return "\n".join(line for line in self.read_lines(invert, lines_number))

    def read_lines(self, invert=False, lines_number=0):
        if invert:
            return self.reverse_read_lines(lines_number)
        else:
            return self.normal_read_lines(lines_number)

    def normal_read_lines(self, lines_number=0):
        """a generator that returns the lines of a file"""
        with FileIO(self._filename, "rb") as fh:
            segment = None
            total = 0
            remaining_size = self.file_size()
            while remaining_size > 0 and (lines_number == 0 or total < lines_number):
                buf_size = self._buf_size if self._buf_size < remaining_size else remaining_size
                buf = fh.read(buf_size)
                remaining_size -= buf_size
                lines = buf.split(SEPARATOR)
                start = 0
                # the last line of the buffer is probably not a complete line so
                # we'll save it and prepend it to the first line of the next buffer
                # we read
                if segment:
                    # if the previous chunk starts right from the beginning of line
                    # do not concat the segment to the first line of new chunk
                    # instead, yield the segment first
                    if buf.startswith(SEPARATOR):
                        start = 1
                        total += 1
                        yield decode(segment)
                    else:
                        lines[0] = segment + lines[0]
                segment = lines[-1]
                for index in range(start, len(lines) - 1):
                    if lines_number == 0 or total < lines_number:
                        total += 1
                        yield decode(lines[index])
            # Don't yield None if the file was empty
            if segment is not None and (lines_number == 0 or total < lines_number):
                yield decode(segment)

    def reverse_read_lines(self, lines_number=0):
        """a generator that returns the lines of a file in reverse order"""
        with FileIO(self._filename, "rb") as fh:
            segment = None
            total = offset = 0
            file_size = remaining_size = self.file_size()
            while remaining_size > 0 and (lines_number == 0 or total < lines_number):
                buf_size = self._buf_size if self._buf_size < remaining_size else remaining_size
                offset += buf_size
                fh.seek(file_size - offset)
                buf = fh.read(buf_size)
                remaining_size -= buf_size
                lines = buf.split(SEPARATOR)
                start = len(lines) - 1
                # the first line of the buffer is probably not a complete line so
                # we'll save it and append it to the last line of the next buffer
                # we read
                if segment:
                    # if the previous chunk starts right from the beginning of line
                    # do not concat the segment to the last line of new chunk
                    # instead, yield the segment first
                    if buf.endswith(SEPARATOR):
                        start -= 1
                        total += 1
                        yield decode(segment)
                    else:
                        lines[-1] += segment
                segment = lines[0]
                for index in range(start, 0, -1):
                    if lines_number == 0 or total < lines_number:
                        total += 1
                        yield decode(lines[index])
            # Don't yield None if the file was empty
            if segment is not None and (lines_number == 0 or total < lines_number):
                yield decode(segment)

    def file_size(self):
        return os.path.getsize(self._filename)
