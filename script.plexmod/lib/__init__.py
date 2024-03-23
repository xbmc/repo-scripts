from __future__ import absolute_import
import requests

# Disable some warnings. These are not security issue warnings, but alerts to issues that may cause errors
try:
    from requests.packages.urllib3.exceptions import InsecurePlatformWarning
    requests.packages.urllib3.disable_warnings(InsecurePlatformWarning)
except:
    import traceback
    traceback.print_exc()

try:
    from requests.packages.urllib3.exceptions import SNIMissingWarning
    requests.packages.urllib3.disable_warnings(SNIMissingWarning)
except:
    # probably urllib3 >= 2.1.0
    pass

from . import compat
from . import _included_packages
