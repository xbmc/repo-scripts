
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
        logging("DEFAULT_LIST: ")
        logging(self.DEFAULT_LIST)
        for key, default_value in list(self.DEFAULT_LIST.items()):
            current_value = getattr(self, key)
            logging(f"Some property {key}: {default_value}, {current_value}")
            if current_value and current_value != default_value:
                request_params[key] = current_value

        return request_params
