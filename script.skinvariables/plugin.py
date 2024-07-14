# -*- coding: utf-8 -*-
# Module: default
# Author: jurialmunkey
# License: GPL v.3 https://www.gnu.org/copyleft/gpl.html

if __name__ == '__main__':
    import sys
    from resources.lib.plugin import Plugin
    Plugin(int(sys.argv[1]), sys.argv[2][1:]).run()
