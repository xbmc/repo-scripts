from contextlib import closing
import xbmcvfs
import xbmcgui
import chardet
import xbmcaddon

ADDON = xbmcaddon.Addon()
__addon__     = xbmcaddon.Addon()
_  = __addon__.getLocalizedString

class FileLoader:
    def __init__(self, filename):
        self.filename = filename
        self.encodingfound = None
        self.subtitlefile = None

    def standard_reader(self, filename):
        with closing(xbmcvfs.File(filename)) as file:
            lines = file.read().split("\n")
        return lines, "utf-8"

    def chardet_reader(self, filename):
        with closing(xbmcvfs.File(filename)) as file:
            encoding_progress = xbmcgui.DialogProgress()
            encoding_progress.create(_(35034), _(35035))
            byte_string = bytes(file.readBytes())
            result = chardet.detect(byte_string)
            text_string = byte_string.decode(result["encoding"])
            encoding_progress.close()
        return text_string.split("\n"), result["encoding"]

    def read_with_replaced_errors(self, filename):
        with closing(xbmcvfs.File(filename)) as file:
            byte_string = bytes(file.readBytes())
            text_string = byte_string.decode("utf-8", errors="replace")
            return text_string.split("\n"), None

    def read_file_sequence(self):
        options = [self.standard_reader,
                   self.chardet_reader,
                   self.read_with_replaced_errors]
        for read in options:
            try:
                sub, encodingfound = read(self.filename)
                return sub, encodingfound
            except:
                continue
        return None

    def read_file(self):
        self.subtitlefile, self.encodingfound = self.read_file_sequence()
