# -*- coding: utf-8 -*-


from resources.lib import core, logger, ADDONVERSION, KODIVERSION
from resources.lib import reporting

logger.debug("Starting service.py, version {}, Kodi: {}".format(ADDONVERSION, KODIVERSION))
try:
    core.core() #Run Hue service
except Exception as exc:
    logger.debug("Core service exception")
    reporting.process_exception(exc)

logger.debug("Shutting down service.py, version {}, Kodi: {}".format(ADDONVERSION, KODIVERSION))
