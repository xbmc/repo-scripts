"""
Hooks for integrating with the python logging framework.

Usage:
    import logging
    from rollbar.logger import RollbarHandler

    rollbar.init('ACCESS_TOKEN', 'ENVIRONMENT')

    logger = logging.getLogger(__name__)
    logger.setLevel(logging.DEBUG)

    # report ERROR and above to Rollbar
    rollbar_handler = RollbarHandler()
    rollbar_handler.setLevel(logging.ERROR)

    # attach the handlers to the root logger
    logger.addHandler(rollbar_handler)

"""
import logging
import threading

from logging.config import ConvertingDict, ConvertingList, ConvertingTuple

import rollbar

# hack to fix backward compatibility in Python3
try:
    from logging import _checkLevel
except ImportError:
    _checkLevel = lambda lvl: lvl


def resolve_logging_types(obj):
    if isinstance(obj, (dict, ConvertingDict)):
        return {k: resolve_logging_types(v) for k, v in obj.items()}
    elif isinstance(obj, (list, ConvertingList)):
        return [resolve_logging_types(i) for i in obj]
    elif isinstance(obj, (tuple, ConvertingTuple)):
        return tuple(resolve_logging_types(i) for i in obj)

    return obj


class RollbarHandler(logging.Handler):
    SUPPORTED_LEVELS = set(('debug', 'info', 'warning', 'error', 'critical'))

    _history = threading.local()

    def __init__(self,
                 access_token=None,
                 environment=None,
                 level=logging.INFO,
                 history_size=10,
                 history_level=logging.DEBUG,
                 **kw):

        logging.Handler.__init__(self)

        if access_token is not None:
            rollbar.init(
                access_token, environment,
                allow_logging_basic_config=False,   # a handler shouldn't configure the root logger
                **resolve_logging_types(kw))

        self.notify_level = _checkLevel(level)

        self.history_size = history_size
        if history_size > 0:
            self._history.records = []

        self.setHistoryLevel(history_level)

    def setLevel(self, level):
        """
        Override so we set the effective level for which
        log records we notify Rollbar about instead of which
        records we save to the history.
        """
        self.notify_level = _checkLevel(level)

    def setHistoryLevel(self, level):
        """
        Use this method to determine which records we record history
        for. Use setLevel() to determine which level we report records
        to Rollbar for.
        """
        logging.Handler.setLevel(self, level)

    def emit(self, record):
        # If the record came from Rollbar's own logger don't report it
        # to Rollbar
        if record.name == rollbar.__log_name__:
            return

        level = record.levelname.lower()

        if level not in self.SUPPORTED_LEVELS:
            return

        exc_info = record.exc_info

        extra_data = {
            'args': record.args,
            'record': {
                'created': record.created,
                'funcName': record.funcName,
                'lineno': record.lineno,
                'module': record.module,
                'name': record.name,
                'pathname': record.pathname,
                'process': record.process,
                'processName': record.processName,
                'relativeCreated': record.relativeCreated,
                'thread': record.thread,
                'threadName': record.threadName
            }
        }

        extra_data.update(getattr(record, 'extra_data', {}))

        payload_data = getattr(record, 'payload_data', {})

        self._add_history(record, payload_data)

        # after we've added the history data, check to see if the
        # notify level is satisfied
        if record.levelno < self.notify_level:
            return

        # Wait until we know we're going to send a report before trying to
        # load the request
        request = getattr(record, "request", None) or rollbar.get_request()

        uuid = None
        try:
            # when not in an exception handler, exc_info == (None, None, None)
            if exc_info and exc_info[0]:
                if record.msg:
                    message_template = {
                        'body': {
                            'trace': {
                                'exception': {
                                    'description': record.getMessage()
                                }
                            }
                        }
                    }
                    payload_data = rollbar.dict_merge(
                        payload_data, message_template, silence_errors=True)

                uuid = rollbar.report_exc_info(exc_info,
                                               level=level,
                                               request=request,
                                               extra_data=extra_data,
                                               payload_data=payload_data)
            else:
                uuid = rollbar.report_message(record.getMessage(),
                                              level=level,
                                              request=request,
                                              extra_data=extra_data,
                                              payload_data=payload_data)
        except:
            self.handleError(record)
        else:
            if uuid:
                record.rollbar_uuid = uuid

    def _add_history(self, record, payload_data):
        if hasattr(self._history, 'records'):
            records = self._history.records
            history = list(records[-self.history_size:])

            if history:
                history_data = [self._build_history_data(r) for r in history]
                payload_data.setdefault('server', {})['history'] = history_data

            records.append(record)

            # prune the messages if we have too many
            self._history.records = list(records[-self.history_size:])

    def _build_history_data(self, record):
        data = {'timestamp': record.created,
                'format': record.msg,
                'args': record.args}

        if hasattr(record, 'rollbar_uuid'):
            data['uuid'] = record.rollbar_uuid

        return data
