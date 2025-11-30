#! /usr/bin/env python

import logging
import os
import sys
import tempfile
from six import reraise


if sys.platform != "win32":
    import fcntl


class SingleInstanceException(BaseException):
    pass


class SingleInstance:

    """Class that can be instantiated only once per machine.

    If you want to prevent your script from running in parallel just instantiate SingleInstance() class. If is there another instance already running it will throw a `SingleInstanceException`.

    >>> import tendo
    ... me = SingleInstance()

    This option is very useful if you have scripts executed by crontab at small amounts of time.

    Remember that this works by creating a lock file with a filename based on the full path to the script file.

    Providing a flavor_id will augment the filename with the provided flavor_id, allowing you to create multiple singleton instances from the same file. This is particularly useful if you want specific functions to have their own singleton instances.
    """

    def __init__(self, flavor_id="", lockfile=""):
        self.initialized = False
        if lockfile:
            self.lockfile = lockfile
        else:
            basename = (
                os.path.splitext(os.path.abspath(sys.argv[0]))[0]
                .replace("/", "-")
                .replace(":", "")
                .replace("\\", "-")
                + "-%s" % flavor_id
                + ".lock"
            )
            self.lockfile = os.path.normpath(tempfile.gettempdir() + "/" + basename)

        logger.debug("SingleInstance lockfile: {}".format(self.lockfile))

    def __enter__(self):
        if sys.platform == "win32":
            try:
                # file already exists, we try to remove (in case previous
                # execution was interrupted)
                if os.path.exists(self.lockfile):
                    os.unlink(self.lockfile)
                self.fd = os.open(self.lockfile, os.O_CREAT | os.O_EXCL | os.O_RDWR)
            except OSError:
                type, e, tb = sys.exc_info()
                if e.errno == 13:
                    logger.error("Another instance is already running, quitting.")
                    raise SingleInstanceException()
                print(e.errno)
                raise
        else:  # non Windows
            self.fp = open(self.lockfile, "w")
            self.fp.flush()
            try:
                fcntl.lockf(self.fp, fcntl.LOCK_EX | fcntl.LOCK_NB)
            except IOError:
                logger.warning("Another instance is already running, quitting.")
                raise SingleInstanceException()
        self.initialized = True
        return self

    def __exit__(self, exc_type, exc_value, exc_tb):
        if not self.initialized:
            return
        if exc_value is not None:
            logger.warning("Error: %s" % exc_value, exc_info=True)
        try:
            if sys.platform == "win32":
                if hasattr(self, "fd"):
                    os.close(self.fd)
                    os.unlink(self.lockfile)
            else:
                fcntl.lockf(self.fp, fcntl.LOCK_UN)
                # os.close(self.fp)
                if os.path.isfile(self.lockfile):
                    os.unlink(self.lockfile)
        except Exception as e:
            if logger:
                logger.warning(e)
            else:
                print("Unloggable error: {}".format(e))
            if exc_value is not None:
                reraise(type(e), exc_value)
            sys.exit(-1)


logger = logging.getLogger("tendo.singleton")
