import re
import xbmcaddon
from subtitleline import SubtitleLine

ADDON = xbmcaddon.Addon()
__addon__     = xbmcaddon.Addon()
_  = __addon__.getLocalizedString

class SubSubtitleCreator:
    def __init__(self, subtitlefile, frame_rate):
        self.subtitlefile = subtitlefile
        self.frame_rate = frame_rate
        self.subtitlelines = []
        self.skipped_lines = []

    def create_subtitleline(self, line):
        new_line = SubtitleLine()
        startline_index = line.find("{")
        midline_index = line.find("}{")
        endline_index = line.find("}", midline_index+1)
        start_time = line[startline_index+1:midline_index]
        end_time = line[midline_index+2:endline_index]

        new_line.startingtime = int(start_time)/self.frame_rate*1000
        new_line.endingtime = int(end_time)/self.frame_rate*1000
        new_line.textlines = [x.strip() for x in line[endline_index+1:len(line)].split("|")]
        self.subtitlelines.append(new_line)

    def load_subtitle(self):
        self.skipped_lines = list(range(len(self.subtitlefile)))
        if not self.preliminary_test():
            # raise TypeError("This does not seem to be a valid .sub file.")
            raise TypeError(_(35036))
        for index, line in enumerate(self.subtitlefile, 1):
            try:
                self.create_subtitleline(line)
                for j in list(range(index-1, index +4)):
                    self.skipped_lines[j] = False
            except:
                pass
        # self.set_times()

    def preliminary_test(self):
        pattern = "^{[0-9]+}{[0-9]+}"
        for line in self.subtitlefile:
            if re.match(pattern, line.strip()):
                return True
        return False
