import re
import xbmcaddon
from subtitleline import SubtitleLine
import xbmcgui

ADDON = xbmcaddon.Addon()
__addon__     = xbmcaddon.Addon()
_  = __addon__.getLocalizedString

class SrtSubtitleCreator:
    def __init__(self, subtitlefile):
        self.subtitlefile = subtitlefile
        self.subtitlelines = []
        self.skipped_lines = []

    def preliminary_test(self):
        pattern = "\d\d:\d\d:\d\d,\d\d\d --> \d\d:\d\d:\d\d,\d\d\d"
        for line in self.subtitlefile:
            if re.match(pattern, line.strip()):
                return True
        return False

    def create_decimal_times(self, line):
        time = (3600000 * int(line[:2]) + 60000
            * int(line[3:5]) + 1000 * int(line[6:8]) + int(line[9:12]))
        return time

    def load_subtitle(self):
        if not self.preliminary_test():
            # raise TypeError("This file doesnt seem to be an valid .srt file")
            raise TypeError(_(35037))
        self.skipped_lines = list(range(len(self.subtitlefile)))
        for index, line in enumerate(self.subtitlefile):
            if len(line) == 29 or len(line) == 30 or len(line) == 31:
                if line.find("-->") == 13:
                    # try:
                    self.create_subtitleline(index)
                    for j in list(range(index-1, index +4)):
                        self.skipped_lines[j] = False
                    # except:
                        # pass


    def create_subtitleline(self, index):
        current_line = SubtitleLine()
        start = self.create_decimal_times(self.subtitlefile[index][:12])
        end = self.create_decimal_times(self.subtitlefile[index][17:29])
        current_line.startingtime = start
        current_line.endingtime = end
        current_line.textlines.append(self.subtitlefile[index+1].strip())
        current_line.textlines.append(self.subtitlefile[index+2].strip())
        rest_line = self.subtitlefile[index+3]
        if not rest_line.strip().isdigit() and len(rest_line) > 2:
            current_line.textlines.append(self.subtitlefile[index+3].strip())
        self.subtitlelines.append(current_line)
