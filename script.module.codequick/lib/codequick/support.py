# -*- coding: utf-8 -*-
from __future__ import absolute_import

# Standard Library Imports
import importlib
import binascii
import inspect
import logging
import time
import sys
import re

# Kodi imports
import xbmcaddon
import xbmcgui
import xbmc

# Package imports
from codequick.utils import parse_qs, ensure_native_str, urlparse, PY3, unicode_type

try:
    # noinspection PyPep8Naming
    import cPickle as pickle
except ImportError:  # pragma: no cover
    import pickle

if PY3:
    from inspect import getfullargspec
    PICKLE_PROTOCOL = 4
else:
    # noinspection PyDeprecation
    from inspect import getargspec as getfullargspec
    PICKLE_PROTOCOL = 2

script_data = xbmcaddon.Addon("script.module.codequick")
addon_data = xbmcaddon.Addon()

plugin_id = addon_data.getAddonInfo("id")
logger_id = re.sub("[ .]", "-", addon_data.getAddonInfo("name"))

# Logger specific to this module
logger = logging.getLogger("%s.support" % logger_id)

# Listitem auto sort methods
auto_sort = set()

logging_map = {
    10: xbmc.LOGDEBUG,
    20: xbmc.LOGINFO if PY3 else xbmc.LOGNOTICE,
    30: xbmc.LOGWARNING,
    40: xbmc.LOGERROR,
    50: xbmc.LOGFATAL,
}


class RouteMissing(KeyError):
    """
    Exception class that is raisd when no
    route is found in the registered routes.
    """


class KodiLogHandler(logging.Handler):
    """
    Custom Logger Handler to forward logs to Kodi.

    Log records will automatically be converted from unicode to utf8 encoded strings.
    All debug messages will be stored locally and outputed as warning messages if a critical error occurred.
    This is done so that debug messages will appear on the normal kodi log file without having to enable debug logging.

    :ivar debug_msgs: Local store of degub messages.
    """
    def __init__(self):
        super(KodiLogHandler, self).__init__()
        self.setFormatter(logging.Formatter("[%(name)s] %(message)s"))
        self.debug_msgs = []

    def emit(self, record):  # type: (logging.LogRecord) -> None
        """Forward the log record to kodi, lets kodi handle the logging."""
        formatted_msg = ensure_native_str(self.format(record))
        log_level = record.levelno

        # Forward the log record to kodi with translated log level
        xbmc.log(formatted_msg, logging_map.get(log_level, 10))

        # Keep a history of all debug records so they can be logged later if a critical error occurred
        # Kodi by default, won't show debug messages unless debug logging is enabled
        if log_level == 10:
            self.debug_msgs.append(formatted_msg)

        # If a critical error occurred, log all debug messages as warnings
        elif log_level == 50 and self.debug_msgs:
            xbmc.log("###### debug ######", xbmc.LOGWARNING)
            for msg in self.debug_msgs:
                xbmc.log(msg, xbmc.LOGWARNING)
            xbmc.log("###### debug ######", xbmc.LOGWARNING)


class CallbackRef(object):
    __slots__ = ("path", "parent", "is_playable", "is_folder")

    def __init__(self, path, parent):
        self.path = path.rstrip("/").replace(":", "/")
        self.is_playable = parent.is_playable
        self.is_folder = parent.is_folder
        self.parent = parent

    def __eq__(self, other):
        return self.path == other.path


class Route(CallbackRef):
    """
    Handle callback route data.

    :param callback: The callable callback function.
    :param parent: The parent class that will handle the response from callback.
    :param str path: The route path to func/class.
    :param dict parameters: Dict of parameters to pass to plugin instance.
    """
    __slots__ = ("function", "callback", "parameters")

    def __init__(self, callback, parent, path, parameters):
        # Register a class callback
        if inspect.isclass(callback):
            msg = "Use of class based callbacks are Deprecated, please use function callbacks"
            logger.warning("DeprecationWarning: " + msg)
            if hasattr(callback, "run"):
                parent = callback
                self.function = callback.run
                callback.test = staticmethod(self.unittest_caller)
            else:
                raise NameError("missing required 'run' method for class: '{}'".format(callback.__name__))
        else:
            # Register a function callback
            callback.test = self.unittest_caller
            self.parameters = parameters
            self.function = callback

        super(Route, self).__init__(path, parent)
        self.callback = callback

    def unittest_caller(self, *args, **kwargs):
        """
        Function to allow callbacks to be easily called from unittests.
        Parent argument will be auto instantiated and passed to callback.
        This basically acts as a constructor to callback.

        Test specific Keyword args:
        execute_delayed: Execute any registered delayed callbacks.

        :param args: Positional arguments to pass to callback.
        :param kwargs: Keyword arguments to pass to callback.
        :returns: The response from the callback function.
        """
        execute_delayed = kwargs.pop("execute_delayed", False)

        # Change the selector to match callback route been tested
        # This will ensure that the plugin paths are currect
        dispatcher.selector = self.path

        # Update support params with the params
        # that are to be passed to callback
        if args:
            dispatcher.params["_args_"] = args

        if kwargs:
            dispatcher.params.update(kwargs)

        # Instantiate the parent
        parent_ins = self.parent()

        try:
            # Now we are ready to call the callback function and return its results
            results = self.function(parent_ins, *args, **kwargs)
            if inspect.isgenerator(results):
                results = list(results)

        except Exception:
            raise

        else:
            # Execute Delated callback functions if any
            if execute_delayed:
                dispatcher.run_delayed()

            return results

        finally:
            # Reset global datasets
            dispatcher.reset()
            auto_sort.clear()


class Dispatcher(object):
    """Class to handle registering and dispatching of callback functions."""

    def __init__(self):
        self.registered_delayed = []
        self.registered_routes = {}
        self.callback_params = {}
        self.selector = "root"
        self.params = {}
        self.handle = -1

    def reset(self):
        """Reset session parameters."""
        self.registered_delayed[:] = []
        self.callback_params.clear()
        kodi_logger.debug_msgs = []
        self.selector = "root"
        self.params.clear()
        auto_sort.clear()

    def parse_args(self, redirect=None):
        """Extract arguments given by Kodi"""
        _, _, route, raw_params, _ = urlparse.urlsplit(redirect if redirect else sys.argv[0] + sys.argv[2])
        self.selector = route if len(route) > 1 else "root"
        self.handle = int(sys.argv[1])

        if raw_params:
            params = parse_qs(raw_params)
            self.params.update(params)

            # Unpickle pickled data
            if "_pickle_" in params:
                unpickled = pickle.loads(binascii.unhexlify(self.params.pop("_pickle_")))
                self.params.update(unpickled)

            # Construct a separate dictionary for callback specific parameters
            self.callback_params = {key: value for key, value in self.params.items()
                                    if not (key.startswith(u"_") and key.endswith(u"_"))}

    def get_route(self, path=None):  # type: (str) -> Route
        """
        Return the given route callback.

        :param str path: The route path, if not given defaults to current callback
        """
        path = path.rstrip("/") if path else self.selector.rstrip("/")

        # Attempt to import the module where the route
        # is located if it's not already registered
        if path not in self.registered_routes:
            module_path = "resources.lib.main" if path == "root" else ".".join(path.strip("/").split("/")[:-1])
            logger.debug("Attempting to import route: %s", module_path)
            try:
                importlib.import_module(module_path)
            except ImportError:
                raise RouteMissing("unable to import route module: %s" % module_path)
        try:
            return self.registered_routes[path]
        except KeyError:
            raise RouteMissing(path)

    def register_callback(self, callback, parent, parameters):
        """Register route callback function"""
        # Construct route path
        path = callback.__name__.lower()
        if path != "root":
            path = "/{}/{}".format(callback.__module__.strip("_").replace(".", "/"), callback.__name__).lower()

        # Register callback
        if path in self.registered_routes:
            logger.debug("encountered duplicate route: '%s'", path)

        self.registered_routes[path] = route = Route(callback, parent, path, parameters)
        callback.route = route
        return callback

    def register_delayed(self, *callback):
        """Register a function that will be called later, after content has been listed."""
        self.registered_delayed.append(callback)

    # noinspection PyIncorrectDocstring
    def run_callback(self, process_errors=True, redirect=None):
        """
        The starting point of the add-on.

        This function will handle the execution of the "callback" functions.
        The callback function that will be executed, will be auto selected.

        The "root" callback, is the callback that will be the initial
        starting point for the add-on.

        :param bool process_errors: Enable/Disable internal error handler. (default => True)
        :returns: Returns None if no errors were raised, or if errors were raised and process_errors is
                  True (default) then the error Exception that was raised will be returned.

        returns the error Exception if an error ocurred.
        :rtype: Exception or None
        """
        self.reset()
        self.parse_args(redirect)
        logger.debug("Dispatching to route: '%s'", self.selector)
        logger.debug("Callback parameters: '%s'", self.callback_params)

        try:
            # Fetch the controling class and callback function/method
            route = self.get_route(self.selector)
            execute_time = time.time()

            # Initialize controller and execute callback
            parent_ins = route.parent()
            arg_params = self.params.get("_args_", [])
            redirect = parent_ins(route, arg_params, self.callback_params)

        except Exception as e:
            self.run_delayed(e)
            # Don't do anything with the error
            # if process_errors is disabled
            if not process_errors:
                raise

            try:
                msg = str(e)
            except UnicodeEncodeError:
                # This is python 2 only code
                # We only use unicode to fetch message when we
                # know that we are dealing with unicode data
                msg = unicode_type(e).encode("utf8")

            # Log the error in both the gui and the kodi log file
            logger.exception(msg)
            dialog = xbmcgui.Dialog()
            dialog.notification(e.__class__.__name__, msg, addon_data.getAddonInfo("icon"))
            return e

        else:
            logger.debug("Route Execution Time: %ims", (time.time() - execute_time) * 1000)
            self.run_delayed()
            if redirect:
                self.run_callback(process_errors, redirect)

    def run_delayed(self, exception=None):
        """Execute all delayed callbacks, if any."""
        if self.registered_delayed:
            # Time before executing callbacks
            start_time = time.time()

            # Execute in order of last in first out (LIFO).
            while self.registered_delayed:
                func, args, kwargs, function_type = self.registered_delayed.pop()
                if function_type == 2 or bool(exception) == function_type:
                    # Add raised exception to callback if requested
                    if "exception" in getfullargspec(func).args:
                        kwargs["exception"] = exception

                    try:
                        func(*args, **kwargs)
                    except Exception as e:
                        logger.exception(str(e))

            # Log execution time of callbacks
            logger.debug("Callbacks Execution Time: %ims", (time.time() - start_time) * 1000)


def build_path(callback=None, args=None, query=None, **extra_query):
    """
    Build addon url that can be passed to kodi for kodi to use when calling listitems.

    :param callback: [opt] The route selector path referencing the callback object. (default => current route selector)
    :param tuple args: [opt] Positional arguments that will be add to plugin path.
    :param dict query: [opt] A set of query key/value pairs to add to plugin path.
    :param extra_query: [opt] Keyword arguments if given will be added to the current set of querys.

    :return: Plugin url for kodi.
    :rtype: str
    """

    # Set callback to current callback if not given
    if callback and hasattr(callback, "route"):
        route = callback.route
    elif isinstance(callback, CallbackRef):
        route = callback
    elif callback:
        msg = "passing in callback path is deprecated, use callback reference 'Route.ref' instead"
        logger.warning("DeprecationWarning: " + msg)
        route = dispatcher.get_route(callback)
    else:
        route = dispatcher.get_route()

    # Convert args to keyword args if required
    if args:
        query["_args_"] = args

    # If extra querys are given then append the
    # extra querys to the current set of querys
    if extra_query:
        query = dispatcher.params.copy()
        query.update(extra_query)

    # Encode the query parameters using json
    if query:
        pickled = binascii.hexlify(pickle.dumps(query, protocol=PICKLE_PROTOCOL))
        query = "_pickle_={}".format(pickled.decode("ascii") if PY3 else pickled)

    # Build kodi url with new path and query parameters
    # NOTE: Kodi really needs a trailing '/'
    return urlparse.urlunsplit(("plugin", plugin_id, route.path + "/", query, ""))


# Setup kodi logging
kodi_logger = KodiLogHandler()
base_logger = logging.getLogger()
base_logger.addHandler(kodi_logger)
base_logger.setLevel(logging.DEBUG)
base_logger.propagate = False

# Dispatcher to manage route callbacks
dispatcher = Dispatcher()
run = dispatcher.run_callback
get_route = dispatcher.get_route
