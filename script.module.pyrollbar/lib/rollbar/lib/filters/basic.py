def filter_rollbar_ignored_exceptions(exc_info, **kw):
    _, exc, _ = exc_info
    if getattr(exc, '_rollbar_ignore', False):
        return False

    return exc_info


def filter_by_level(target, **kw):
    if 'level' in kw and kw['level'] == 'ignored':
        return False

    return target
