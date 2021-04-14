from rollbar.lib.transforms.scrub import ScrubTransform


class RedactRef(object):
    pass


REDACT_REF = RedactRef()


class ScrubRedactTransform(ScrubTransform):
    def default(self, o, key=None):
        if o is REDACT_REF:
            return self.redact(o)

        return super(ScrubRedactTransform, self).default(o, key=key)


__all__ = ['ScrubRedactTransform']
