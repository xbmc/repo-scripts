from resources.lib import common
from resources.lib import gui

class Main():
    def __init__(self):
         w = gui.TransmissionGUI("script-Transmission-main.xml",
                                common.get_addon_info('path'),
                                "Default")
         w.doModal()
         del w
