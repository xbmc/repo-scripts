"""Service entry point for script.livetennisscores.

Kodi runs this once per startup or profile login for the ``xbmc.service``
extension point. It is deliberately a shim: the loop, the polling and the
abort handling all live in ``resources/lib/service.py``.
"""

from resources.lib.service import Service

if __name__ == "__main__":
    Service().run()
