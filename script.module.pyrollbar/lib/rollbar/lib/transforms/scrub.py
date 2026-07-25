import random

from rollbar.lib import build_key_matcher
from rollbar.lib.transform import Transform


class ScrubTransform(Transform):
    suffix_matcher = None
    priority = 40
    def __init__(self, suffixes=None, redact_char='*', randomize_len=True):
        super(ScrubTransform, self).__init__()
        if suffixes is not None and len(suffixes) > 0:
            self.suffix_matcher = build_key_matcher(suffixes, type='suffix')
        self.redact_char = redact_char
        self.randomize_len = randomize_len

    def in_scrub_fields(self, key):
        if self.suffix_matcher is None:
            return False
        return self.suffix_matcher(key)

    def redact(self, val):
        if self.randomize_len:
            _len = random.randint(3, 20)
        else:
            try:
                _len = len(val)
            except:
                _len = len(str(val))

        return self.redact_char * _len

    def default(self, o, key=None):
        if self.in_scrub_fields(key):
            return self.redact(o)

        return o


__all__ = ['ScrubTransform']
