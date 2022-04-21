from subtitleline import SubtitleLine
from fileloading import FileLoader
from subtitle import Subtitle
from srt_subtitle_creator import SrtSubtitleCreator
from sub_subtitle_creator import SubSubtitleCreator

class Controller:
    def __init__(self, filename):
        self.filename = filename
        self.load_file()

    def load_file(self):
        self.fileloader = FileLoader(self.filename)
        self.fileloader.read_file()
        self.encodingfound = self.fileloader.encodingfound
        self.subtitlefile = self.fileloader.subtitlefile + ["", ""]

    def create_srt_subtitle(self):
        self.subtitlefilecreator = SrtSubtitleCreator(self.subtitlefile)
        self.subtitlefilecreator.load_subtitle()
        self.subtitlelines = self.subtitlefilecreator.subtitlelines

    def create_sub_subtitle(self, frame_rate):
        self.subtitlefilecreator = SubSubtitleCreator(self.subtitlefile, frame_rate)
        self.subtitlefilecreator.load_subtitle()
        self.subtitlelines = self.subtitlefilecreator.subtitlelines
        
    def get_subtitle(self):
        self.subtitle = Subtitle(self.filename, self.subtitlelines, self.encodingfound)
        self.subtitle.skipped_lines = self.subtitlefilecreator.skipped_lines
        self.subtitle.subtitlefile = self.subtitlefile
        return self.subtitle
