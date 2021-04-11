EXCEPTION_INFO = 'exception_info'
MESSAGE = 'message'
PAYLOAD = 'payload'

_event_handlers = {
    EXCEPTION_INFO: [],
    MESSAGE: [],
    PAYLOAD: []
}


def _check_type(typ):
    if typ not in _event_handlers:
        raise ValueError('Unknown type: %s. Must be one of %s' % (typ, _event_handlers.keys()))


def _add_handler(typ, handler_fn, pos):
    _check_type(typ)

    pos = pos if pos is not None else -1
    handlers = _event_handlers[typ]

    try:
        handlers.index(handler_fn)
    except ValueError:
        handlers.insert(pos, handler_fn)


def _remove_handler(typ, handler_fn):
    _check_type(typ)

    handlers = _event_handlers[typ]

    try:
        index = handlers.index(handler_fn)
        handlers.pop(index)
    except ValueError:
        pass


def _on_event(typ, target, **kw):
    _check_type(typ)

    ref = target
    for handler in _event_handlers[typ]:
        result = handler(ref, **kw)
        if result is False:
            return False

        ref = result

    return ref


# Add/remove event handlers

def add_exception_info_handler(handler_fn, pos=None):
    _add_handler(EXCEPTION_INFO, handler_fn, pos)


def remove_exception_info_handler(handler_fn):
    _remove_handler(EXCEPTION_INFO, handler_fn)


def add_message_handler(handler_fn, pos=None):
    _add_handler(MESSAGE, handler_fn, pos)


def remove_message_handler(handler_fn):
    _remove_handler(MESSAGE, handler_fn)


def add_payload_handler(handler_fn, pos=None):
    _add_handler(PAYLOAD, handler_fn, pos)


def remove_payload_handler(handler_fn):
    _remove_handler(PAYLOAD, handler_fn)


# Event handler processing

def on_exception_info(exc_info, **kw):
    return _on_event(EXCEPTION_INFO, exc_info, **kw)


def on_message(message, **kw):
    return _on_event(MESSAGE, message, **kw)


def on_payload(payload, **kw):
    return _on_event(PAYLOAD, payload, **kw)


# Misc

def reset():
    for handlers in _event_handlers.values():
        del handlers[:]
