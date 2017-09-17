import sys

import xbmc


class LockWithDialog(object):
    """ Decorator Class that locks a method using a busy dialog """

    def __init__(self, logger=None):
        """ Initializes the decorator with a specific method.

        We need to use the Decorator as a function @LockWithDialog() to get the
        'self' parameter passed on.

        """

        self.logger = logger
        return

    def __call__(self, wrapped_function):
        """ When the method is called this is executed. """

        def __inner_wrapped_function(*args, **kwargs):
            """ Function that get's called instead of the decorated function """

            # show the busy dialog
            if self.logger:
                self.logger.debug("Locking interface and showing BusyDialog")

            xbmc.executebuiltin("ActivateWindow(busydialog)")
            try:
                response = wrapped_function(*args, **kwargs)
                # time.sleep(2)
            except Exception:
                # Hide the busy Dialog
                if self.logger:
                    self.logger.debug("Un-locking interface and hiding BusyDialog")
                xbmc.executebuiltin("Dialog.Close(busydialog)")

                # re-raise the exception with the original traceback info
                # see http://nedbatchelder.com/blog/200711/rethrowing_exceptions_in_python.html
                error_info = sys.exc_info()
                raise error_info[1], None, error_info[2]

            # Hide the busy Dialog
            if self.logger:
                self.logger.debug("Un-locking interface and hiding BusyDialog")
            xbmc.executebuiltin("Dialog.Close(busydialog)")
            return response

        return __inner_wrapped_function
