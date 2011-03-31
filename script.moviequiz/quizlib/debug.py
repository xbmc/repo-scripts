import os
import sys

#
# Import this file to enable PyCharm debugging.
#

PYCHARM_DEBUG_EGG = '/opt/pycharm-1.2/pycharm-debug.egg'

if os.path.exists(PYCHARM_DEBUG_EGG):
    print "Enabling PyCharm debugging..."
    try:
        sys.path.append(PYCHARM_DEBUG_EGG)
        from pydev import pydevd
        pydevd.settrace('localhost', port=50000, suspend=False)
        print "Connected to PyCharm"
    except SystemExit:
        print "Unable to connect to PyCharm"
