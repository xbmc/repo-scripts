import os
import sys

import xbmcaddon

addon_path = xbmcaddon.Addon().getAddonInfo("path")
sys.path.append(os.path.join(addon_path, "resources", "lib"))

from quicksync import main  # noqa: E402

main()
