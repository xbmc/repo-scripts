from rollbar.lib import events
from rollbar.lib.filters.basic import filter_rollbar_ignored_exceptions, filter_by_level


def add_builtin_filters(settings):
    # exc_info filters
    events.add_exception_info_handler(filter_rollbar_ignored_exceptions)
    events.add_exception_info_handler(filter_by_level)

    # message filters
    events.add_message_handler(filter_by_level)
