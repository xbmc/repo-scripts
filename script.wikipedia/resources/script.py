# -*- coding: utf-8 -*-
# Module: default
# Author: jurialmunkey
# License: GPL v.3 https://www.gnu.org/copyleft/gpl.html
if __name__ == '__main__':
    import sys
    from lib.script import Script
    Script(*sys.argv[1:]).router()
