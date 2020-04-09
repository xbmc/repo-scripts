# -*- coding: utf-8 -*-
import ast
import logging
import re
from collections import namedtuple

from resources.lib.kodi import kodilogging
from resources.lib.kodi.utils import get_setting_as_bool

logger = kodilogging.get_logger()

Command = namedtuple("Command", ("code", "name", "data"))


def _command_from_match(match):
    code = int(match.group("code"))
    name = match.group("cmd")
    raw_data = match.group("data")
    if raw_data:
        data = ast.literal_eval(raw_data)
    else:
        data = None

    return Command(code, name, data)


CMD_PATTERN = re.compile(r"\[(?P<code>\d+),\[\"(?P<cmd>.+?)\"(?:,(?P<data>.*?))?\]\]")


class CommandParser:
    """Buffering stream parser for YouTube Cast commands.

    Warnings: This class isn't thread-safe!
    """

    def __init__(self, buf=None):
        self.pending = ""

        if buf:
            self.write(buf)

    def __iter__(self):
        return self._parse_pending()

    def _parse_pending(self):
        if not self.pending:
            return

        debug_cmds = logger.isEnabledFor(logging.DEBUG) and get_setting_as_bool("debug-cmd")

        end_index = 0
        try:
            for match in CMD_PATTERN.finditer(self.pending):
                if debug_cmds:
                    skipped = self.pending[end_index:match.start()]
                    if skipped:
                        logger.debug("command parser skipped: %r", skipped)

                end_index = match.end()
                try:
                    cmd = _command_from_match(match)
                except SyntaxError:
                    logger.exception("unable to parse command")
                else:
                    yield cmd
        finally:
            self.pending = self.pending[end_index:]

    def write(self, s):  # type: (str) -> None
        for line in s.splitlines():
            self.pending += line

    def get_commands(self):  # type: () -> Tuple[Command, ...]
        return tuple(self)


def get_video_list(data):
    videos = []
    if "videos" in list(data.keys()):
        videos = data["videos"]
    return videos
