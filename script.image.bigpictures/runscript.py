import os
import sys

# Script constants
__scriptname__ = 'The Big Picture'
__author__ = 'sphere, rwparris2'
__version__ = '1.2.0'

print '[SCRIPT][%s] version %s initialized!' % (__scriptname__, __version__)

if (__name__ == '__main__'):
    import resources.lib.gui as gui
    ui = gui.GUI( 'main.xml', os.getcwd(), 'default' )
    ui.doModal()
    del ui
    sys.modules.clear()
