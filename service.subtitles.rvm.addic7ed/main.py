# -*- coding: utf-8 -*-
# Licence: GPL v.3 http://www.gnu.org/licenses/gpl.html
# The main script contains minimum code to speed up launching on slower systems

import sys
from addic7ed.actions import router
from addic7ed.exception_logger import log_exception

if __name__ == '__main__':
    with log_exception():
        router(sys.argv[2][1:])
