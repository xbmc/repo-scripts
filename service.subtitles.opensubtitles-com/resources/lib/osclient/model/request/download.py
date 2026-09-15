
from resources.lib.osclient.model.request.abstract import OpenSubtitlesRequest
from resources.lib.osclient.model.request.subtitles import _to_int

SUB_FORMAT_LIST = ["srt", "sub", "mpl", "webvtt", "dfxp", "txt"]


def _to_float(value):
    """Coerce to float or None - matches the numeric intake policy of the
    subtitles model; malformed external values must never raise here."""
    try:
        if value is None or value == "":
            return None
        return float(value)
    except (TypeError, ValueError):
        return None



class OpenSubtitlesDownloadRequest(OpenSubtitlesRequest):
    def __init__(self, file_id: int, sub_format="", file_name="", in_fps: float = None, out_fps: float = None,
                 timeshift: float = None, force_download: bool = None, **catch_overflow):
        # file_id arrives from the invocation query string as a string -
        # coerce like every other numeric field so it goes out as an int
        self._file_id = _to_int(file_id)
        self._sub_format = sub_format
        self._file_name = file_name
        self._in_fps = in_fps
        self._out_fps = out_fps
        self._timeshift = timeshift
        self._force_download = force_download

        super().__init__()

        # ordered request params with defaults
        self.DEFAULT_LIST = dict(file_id=None, file_name="", force_download=None, in_fps=None, out_fps=None,
                                 sub_format="", timeshift=None)

    @property
    def file_id(self):
        return self._file_id

    @file_id.setter
    def file_id(self, value):
        value = _to_int(value)
        if value is not None and value <= 0:
            raise ValueError("file_id should be positive integer.")
        self._file_id = value

    @property
    def sub_format(self):
        return self._sub_format

    @sub_format.setter
    def sub_format(self, value):
        if value not in SUB_FORMAT_LIST:
            raise ValueError("sub_format should be one of \'{0}\'.".format("', '".join(SUB_FORMAT_LIST)))
        self._sub_format = value

    @property
    def file_name(self):
        return self._file_name

    @file_name.setter
    def file_name(self, value):
        self._file_name = value

    @property
    def in_fps(self):
        return self._in_fps

    @in_fps.setter
    def in_fps(self, value):
        value = _to_float(value)
        if value is not None and value <= 0:
            raise ValueError("in_fps should be positive number.")
        self._in_fps = value

    @property
    def out_fps(self):
        return self._out_fps

    @out_fps.setter
    def out_fps(self, value):
        value = _to_float(value)
        if value is not None and value <= 0:
            raise ValueError("out_fps should be positive number.")
        self._out_fps = value

    @property
    def timeshift(self):
        return self._timeshift

    @timeshift.setter
    def timeshift(self, value):
        # a NEGATIVE shift is legitimate (subtitles running ahead) - the old
        # check rejected half the valid range; only coerce, never range-limit
        self._timeshift = _to_float(value)

    @property
    def force_download(self):
        return self._force_download

    @force_download.setter
    def force_download(self, value):
        self._force_download = value
