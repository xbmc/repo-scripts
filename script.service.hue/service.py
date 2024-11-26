#      Copyright (C) 2019 Kodi Hue Service (script.service.hue)
#      This file is part of script.service.hue
#      SPDX-License-Identifier: MIT
#      See LICENSE.TXT for more information.

from resources.lib import core, reporting

try:
    core.core_dispatcher()
except Exception as exc:
    reporting.process_exception(exc)
