# coding: utf-8
# (c) 2018, Roman Miroshnychenko <roman1972@gmail.com>
# License: GPL v.3

import sys
from libs.utils import sync_library, login

if __name__ == '__main__':
    if sys.argv[1] == 'sync_library':
        sync_library()
    elif sys.argv[1] == 'login':
        login()
