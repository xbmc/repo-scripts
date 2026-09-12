from typing import Optional


class Transform(object):
    depth_first = True
    priority = 100

    def default(self, o, key=None):
        return o

    def transform_circular_reference(self, o, key=None, ref_key=None):
        # By default, we just perform a no-op for circular references.
        # Subclasses should implement this method to return whatever representation
        # for the circular reference they need.
        return self.default(o, key=key)

    def transform_tuple(self, o, key=None):
        return self.default(o, key=key)

    def transform_namedtuple(self, o, key=None):
        return self.default(o, key=key)

    def transform_list(self, o, key=None):
        return self.default(o, key=key)

    def transform_dict(self, o, key=None):
        return self.default(o, key=key)

    def transform_number(self, o, key=None):
        return self.default(o, key=key)

    def transform_bytes(self, o, key=None):
        return self.default(o, key=key)

    def transform_unicode(self, o, key=None):
        return self.default(o, key=key)

    def transform_boolean(self, o, key=None):
        return self.default(o, key=key)

    def transform_path(self, o, key=None):
        return self.default(str(o), key=key)

    def transform_custom(self, o, key=None):
        return self.default(o, key=key)

    @staticmethod
    def rollbar_repr(obj: object) -> Optional[str]:
        r = None
        if hasattr(obj, '__rollbar_repr__'):
            r = obj.__rollbar_repr__()
            if not isinstance(r, str):
                raise TypeError(f'__rollbar_repr__ returned non-string (type {type(r)})')
        return r
