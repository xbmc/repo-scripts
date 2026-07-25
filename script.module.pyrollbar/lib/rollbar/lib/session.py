from __future__ import annotations

import random
import threading
from contextvars import ContextVar
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from rollbar.lib.payload import Attribute

_context_session: ContextVar[list[Attribute]|None] = ContextVar('rollbar-session', default=None)
_thread_session: threading.local = threading.local()


def set_current_session(headers: dict[str, str]) -> None:
    """
    Set current session data.

    The session data should be a dictionary with string keys and string values.
    """
    session_data = parse_session_request_baggage_headers(headers, generate_missing=True)
    _context_session.set(session_data)
    _thread_session.data = session_data


def get_current_session() -> list[Attribute]:
    """
    Return current session data.

    Do NOT modify the returned session data.
    """
    session_data = _context_session.get()
    if session_data is not None:
        return session_data

    # Fallback to thread local storage for non-async contexts.
    return getattr(_thread_session, 'data', None) or []


def reset_current_session() -> None:
    """
    Reset current session data.
    """
    _context_session.set(None)
    _thread_session.data = None


def parse_session_request_baggage_headers(headers: dict, generate_missing: bool = False) -> list[Attribute]:
    """
    Parse the 'baggage' header from the request headers to extract session information. If the 'baggage' header is not
    present or does not contain the expected keys, a new execution scope ID will be generated and returned as part of
    the session attributes.

    :param headers: The request headers as a dictionary.
    :param generate_missing: If True, generates a new execution scope ID if it's missing from the baggage header. If
                             False, it is not generated. This should only be set to True when the session data is being
                             stored for the first time in the request context. Generally, `set_current_session()`, and
                             `get_current_session()` should be used instead.
    """
    if not headers:
        if generate_missing:
            return _build_new_scope_attributes()
        return []

    baggage_header = None

    # Make sure to handle case-insensitive header keys.
    for key in headers.keys():
        if key.lower() == 'baggage':
            baggage_header = headers[key]
            break

    if not baggage_header:
        if generate_missing:
            return _build_new_scope_attributes()
        return []

    baggage_items = baggage_header.split(',')
    baggage_data: list[Attribute] = []
    has_scope_id = False
    for item in baggage_items:
        if '=' not in item:
            continue
        key, value = item.split('=', 1)
        key = key.strip()
        if key == 'rollbar.session.id':
            baggage_data.append({'key': 'session_id', 'value': value.strip()})
        if key == 'rollbar.execution.scope.id':
            has_scope_id = True
            baggage_data.append({'key': 'execution_scope_id', 'value': value.strip()})

    if not baggage_data:
        if generate_missing:
            return _build_new_scope_attributes()
        return []

    # Always ensure we have an execution scope ID, even if the baggage header is present but doesn't contain it.
    if not has_scope_id and generate_missing:
        baggage_data.extend(_build_new_scope_attributes())

    return baggage_data


def _build_new_scope_attributes() -> list[Attribute]:
    """
    Generates a new value for the `rollbar.execution.scope.id` attribute.
    """
    new_id = _new_scope_id()
    if new_id is None:
        return []
    return [{'key': 'execution_scope_id', 'value': new_id}]


def _new_scope_id() -> str | None:
    """
    Generate a new random ID with 128 bits of randomness, formatted as a 32-character hexadecimal string. To be used as
    an execution scope ID.
    """
    try:
        # Generate a random integer with exactly 128 random bits
        num = random.getrandbits(128)
    except Exception as e:
        return None
    return format(num, "032x")
