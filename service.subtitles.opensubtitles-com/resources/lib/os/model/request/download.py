
from __future__ import absolute_import
from resources.lib.os.model.request.abstract import OpenSubtitlesRequest

SUB_FORMAT_LIST = [u"srt", u"sub", u"mpl", u"webvtt", u"dfxp", u"txt"]


class OpenSubtitlesDownloadRequest(OpenSubtitlesRequest):
    def __init__(self, file_id, sub_format=u"", file_name=u"", in_fps = None, out_fps = None,
                 timeshift = None, force_download = None, **catch_overflow):
        self._file_id = file_id
        self._sub_format = sub_format
        self._file_name = file_name
        self._in_fps = in_fps
        self._out_fps = out_fps
        self._timeshift = timeshift
        self._force_download = force_download

        super(OpenSubtitlesDownloadRequest, self).__init__()

        # ordered request params with defaults
        self.DEFAULT_LIST = dict(file_id=None, file_name=u"", force_download=None, in_fps=None, out_fps=None,
                                 sub_format=u"", timeshift=None)

    @property
    def file_id(self):
        return self._file_id

    @file_id.setter
    def file_id(self, value):
        if value <= 0:
            raise ValueError(u"file_id should be positive integer.")
        self._file_id = value

    @property
    def sub_format(self):
        return self._sub_format

    @sub_format.setter
    def sub_format(self, value):
        if value not in SUB_FORMAT_LIST:
            raise ValueError(u"sub_format should be one of \'{0}\'.".format(u"', '".join(SUB_FORMAT_LIST)))
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
        if value <= 0:
            raise ValueError(u"in_fps should be positive number.")
        self._in_fps = value

    @property
    def out_fps(self):
        return self._out_fps

    @out_fps.setter
    def out_fps(self, value):
        if value <= 0:
            raise ValueError(u"out_fps should be positive number.")
        self._out_fps = value

    @property
    def timeshift(self):
        return self._timeshift

    @timeshift.setter
    def timeshift(self, value):
        if value <= 0:
            raise ValueError(u"timeshift should be positive number.")
        self._timeshift = value

    @property
    def force_download(self):
        return self._force_download

    @force_download.setter
    def force_download(self, value):
        self._force_download = value
