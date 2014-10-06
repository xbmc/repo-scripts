import os
import sys
import lib.common

# add ./lib/external to PYTHONPATH
__addonpath__    = lib.common.__addonpath__

sys.path.append(os.path.join(__addonpath__, 'lib', 'external'))