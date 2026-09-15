
from resources.lib.utilities import log


def logging(msg):
    log(__name__, msg)


class OpenSubtitlesRequest:
    def __init__(self):
        self._instance = True

        # ordered request params with defaults
        self.DEFAULT_LIST = dict()

    def request_params(self):
        if not self._instance:
            raise ReferenceError("Should pass params to the class by initiating it first.")
        request_params = {}
        for key, default_value in list(self.DEFAULT_LIST.items()):
            current_value = getattr(self, key)
            # 0 is a real value (season 0 = specials) - only None and empty
            # string mean "not set", plain truthiness dropped it from requests
            if current_value not in (None, "") and current_value != default_value:
                request_params[key] = current_value

        # keys only: values include the playback-derived query/title
        logging(f"request params built: {sorted(request_params.keys())}")
        return request_params
