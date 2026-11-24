# Entry point for the "Back up / Restore thumbnails" buttons in the settings:
# RunScript(special://home/addons/context.thumbnailfromvideo/tools.py,backup|restore)
import sys

from resources.lib import backup

backup.run(sys.argv[1] if len(sys.argv) > 1 else '')
