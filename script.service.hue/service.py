#      Copyright (C) 2019-2021 Kodi Hue Service (script.service.hue)
#      This file is part of script.service.hue
#      SPDX-License-Identifier: MIT
#      See LICENSE.TXT for more information.

import xbmc

from resources.lib import core, reporting

try:
    core.core()
except Exception as exc:
    xbmc.log(f"[script.service.hue][EXCEPTION] Service exception: {exc}")
    reporting.process_exception(exc)
