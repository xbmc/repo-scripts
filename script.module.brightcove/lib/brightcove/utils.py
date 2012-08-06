def validate_params(**kwargs):
    exclude = ['self', 'kwargs']
    # First remove self from the dict and any values that are None
    params = {}
    # update kwargs with the nested kwargs
    #kwargs.update(kwargs['kwargs'])

    for key, val in kwargs.items():
        # if none or self continue
        if val is None or key  in exclude:
            continue

        # If we have a validator, validate the param, otherwise just add to
        # return dict
        if hasattr(Validators, key):
            params[key] = getattr(Validators, key)(val)
        else:
            params[key] = val

    return params


class Validators(object):
    @staticmethod
    def _search_criteria(dct):
        '''Accepts a mapping, or a string.'''
        # http://support.brightcove.com/en/docs/searching-videos-media-api
        valid_search_fields = ['display_name', 'reference_id', 'tag',
                               'custom_fields', 'search_text']

        try:
            assert all(key in valid_search_fields for key in dct.keys()), (
                       '%s is not a valid search field.' % key)
            return ','.join('%s:%s' % (key, val) for key, val in dct.items())
        except AttributeError:
            # We were not given a mapping, so just return the value
            return dct

    @staticmethod
    def sort_by(dct):
        valid_sort_fields = ['DISPLAY_NAME', 'REFERENCE_ID', 'PUBLISH_DATE',
                             'CREATION_DATE', 'MODIFIED_DATE', 'START_DATE',
                             'PLAYS_TRAILING_WEEK', 'PLAYS_TOTAL']
        try:
            for key, val in dct.items():
                assert(key) in valid_sort_fields, 'Invalid sort field %s' % key
                assert(val) in SortOrderType._fields, (
                    'Invalid sort direction %s' % val)
            return ','.join('%s:%s' % (key, val) for key, val in dct.items())
        except AttributeError:
            # Not given a mapping
            return ','.join(dct)
            # Doesn't currently check if we pass a single string here, we will
            # end up joining every letter with a comma

    @staticmethod
    def all(dct):
        return Validators._search_criteria(dct)

    @staticmethod
    def any(dct):
        return Validators._search_criteria(dct)

    @staticmethod
    def none(dct):
        return Validators._search_criteria(dct)

    @staticmethod
    def fields(fields):
        for field in fields:
            assert field in Video._fields, (
                '%s is not a valid Video field.' % field)
        return ','.join(fields)

    @staticmethod
    def video_ids(ids):
        return ','.join(str(_id) for _id in ids)

    @staticmethod
    def playlist_ids(ids):
        return ','.join(str(_id) for _id in ids)

    @staticmethod
    def reference_ids(ids):
        return ','.join(str(_id) for _id in ids)


def requires_or(*_args):
    '''This decorator annotes functions where at least one of a set of
    arguments is required.
    '''
    def requires_or_decorator(f):
        def wrapper(*args, **kwargs):
            assert any(name in kwargs for name in _args), (
                '%s requires at least one of the following arguments: %s' %
                (f.__name__, ', '.join(_args)))
            return f(*args, **kwargs)
        return wrapper
    return requires_or_decorator
