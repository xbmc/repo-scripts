#!/usr/bin/python
# -*- coding: utf-8 -*-

from utils import ADDON, translate
from xbmcgui import Dialog


def reset_exclusions():
    """
    Reset all user-set exclusion paths to blanks.
    :return:
    """
    if Dialog().yesno(translate(32604), translate(32610), translate(32607)):
        ADDON.setSetting(id="exclusion1", value="")
        ADDON.setSetting(id="exclusion2", value="")
        ADDON.setSetting(id="exclusion3", value="")
        ADDON.setSetting(id="exclusion4", value="")
        ADDON.setSetting(id="exclusion5", value="")

if __name__ == "__main__":
    reset_exclusions()
