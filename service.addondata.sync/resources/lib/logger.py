import os
import sys
import traceback
import time
import datetime


class Logger:
    """Logger class that is used for logging to a certain file. It's faster
    than the normal Python logging class and has more custom options.

    It appears as a default Python logger and has these log methods:
    * trace    : In depth variable information, timing information and other development
                 related information. Usually too many lines to be meaningful for a
                 non-developer.
    * debug    : Detailed information on the state of the script including trouble
                 shooting information. Should now be spawned too often.
    * info     : Generic information on the state of the script.
    * warning  : Log line that indicates a error that was recovered.
    * error    : Log line that indicates a error that should not have occurred but
                 did not break the execution of the script.
    * critical : Log line that indicates a problem that prevent correct execution
                 of the script.

    Has a subclass __Write that
    does the work!

    """

    CRITICAL = 50
    FATAL = CRITICAL
    ERROR = 40
    WARNING = 30
    WARN = WARNING
    INFO = 20
    DEBUG = 10
    TRACE = 0

    __logger = None

    @staticmethod
    def create_logger(log_file_name, application_name, min_log_level=10, append=False, dual_logger=None):
        """ Initialises the Logger Instance and opens it for writing

        :param log_file_name:          Path of the log file to write to
        :param application_name:       Name of the application
        :param min_log_level:          Minimum log level to log. Levels equal or higher are logged.
        :param append:                 If set to True, the current log file is not deleted. Default value is False.
        :param dual_logger:            If set to True, exceptions are also written to the standard out.

        :return: A single instance of a Logger
        """

        if Logger.__logger is None:
            Logger.__logger = Logger(log_file_name, application_name, min_log_level, append, dual_logger)
        else:
            Logger.__logger.warning("Cannot create a second logger instance!")
        return Logger.__logger

    def __init__(self, log_file_name, application_name, min_log_level=10, append=False, dual_logger=None):
        """ Initialises the Logger Instance and opens it for writing

        :param log_file_name:          Path of the log file to write to
        :param application_name:       Name of the application
        :param min_log_level:          Minimum log level to log. Levels equal or higher are logged.
        :param append:                 If set to True, the current log file is not deleted. Default value is False.
        :param dual_logger:            If set to True, exceptions are also written to the standard out.

        """

        self.logFileName = os.path.abspath(log_file_name)
        self.fileMode = "a"
        self.fileFlags = os.O_WRONLY | os.O_APPEND | os.O_CREAT

        self.minLogLevel = min_log_level
        self.dualLog = dual_logger
        self.logDual = dual_logger is not None
        self.logEntryCount = 0
        self.flushInterval = 5
        self.encoding = 'cp1252'
        self.applicationName = application_name

        # self.logHandle = -1
        self.id = int(time.time())
        self.timeFormat = "%Y%m%d %H:%M:%S"
        self.logFormat = '%s - [%-8s] - %-20s - %-4d - %s\n'

        self.logLevelNames = {
            Logger.CRITICAL: 'CRITICAL',
            Logger.ERROR: 'ERROR',
            Logger.WARNING: 'WARNING',
            Logger.INFO: 'INFO',
            Logger.DEBUG: 'DEBUG',
            Logger.TRACE: 'TRACE',
            'CRITICAL': Logger.CRITICAL,
            'ERROR': Logger.ERROR,
            'WARN': Logger.WARNING,
            'WARNING': Logger.WARNING,
            'INFO': Logger.INFO,
            'DEBUG': Logger.DEBUG,
            'TRACE': Logger.TRACE,
        }

        if not append:
            self.clean_up_log()

        # now open the file
        self.__open_log()

        self.__write("%s :: Log file opened at %s.", self.applicationName, self.logFileName, level=Logger.INFO)
        return

    @staticmethod
    def get_instance():
        return Logger.__logger

    @staticmethod
    def trace(msg, *args, **kwargs):
        """Logs an trace message (with log level 0)

        Arguments:
        msg    : string - The message to log
        args   : list   - List of arguments

        Keyword Arguments:
        kwargs : list - List of keyword arguments

        The arguments and keyword arguments are used in a string format way
        so and will replace the parameters in the message.

        """

        Logger.__logger.__write(msg, level=Logger.TRACE, *args, **kwargs)
        return

    @staticmethod
    def debug(msg, *args, **kwargs):
        """Logs an debug message (with log level 10)

        Arguments:
        msg    : string - The message to log
        args   : list   - List of arguments

        Keyword Arguments:
        kwargs : list - List of keyword arguments

        The arguments and keyword arguments are used in a string format way
        so and will replace the parameters in the message.

        """

        Logger.__logger.__write(msg, level=Logger.DEBUG, *args, **kwargs)
        return

    @staticmethod
    def info(msg, *args, **kwargs):
        """Logs an informational message (with log level 20)

        Arguments:
        msg    : string - The message to log
        args   : list   - List of arguments

        Keyword Arguments:
        kwargs : list - List of keyword arguments

        The arguments and keyword arguments are used in a string format way
        so and will replace the parameters in the message.

        """

        Logger.__logger.__write(msg, level=Logger.INFO, *args, **kwargs)
        return

    @staticmethod
    def error(msg, *args, **kwargs):
        """Logs an error message (with log level 40)

        Arguments:
        msg    : string - The message to log
        args   : list   - List of arguments

        Keyword Arguments:
        kwargs : list - List of keyword arguments

        The arguments and keyword arguments are used in a string format way
        so and will replace the parameters in the message.

        """

        Logger.__logger.__write(msg, level=Logger.ERROR, *args, **kwargs)
        return

    @staticmethod
    def warning(msg, *args, **kwargs):
        """Logs an warning message (with log level 30)

        Arguments:
        msg    : string - The message to log
        args   : list   - List of arguments

        Keyword Arguments:
        kwargs : list - List of keyword arguments

        The arguments and keyword arguments are used in a string format way
        so and will replace the parameters in the message.

        """

        Logger.__logger.__write(msg, level=Logger.WARNING, *args, **kwargs)
        return

    @staticmethod
    def critical(msg, *args, **kwargs):
        """Logs an critical message (with log level 50)

        Arguments:
        msg    : string - The message to log
        args   : list   - List of arguments

        Keyword Arguments:
        kwargs : list - List of keyword arguments

        The arguments and keyword arguments are used in a string format way
        so and will replace the parameters in the message.

        """

        Logger.__logger.__write(msg, level=Logger.CRITICAL, *args, **kwargs)
        return

    def close_log(self, log_closing=True):
        """Close the logfile.

        Calling close() on a file handle also closes the FileDescriptor

        Keyword Arguments:
        logClosing : boolean - indicates whether a log line is written on closure.

        """

        if log_closing:
            self.info("%s :: Flushing and closing log file.", self.applicationName)

        self.logHandle.flush()
        self.logHandle.close()

    def flush(self):
        self.logHandle.flush()

    def set_log_level(self, log_level):
        if log_level == self.minLogLevel:
            return

        previous_value = self.minLogLevel
        self.minLogLevel = log_level
        Logger.info("Changed log level from '%s' to '%s'",
                    self.logLevelNames[previous_value], self.logLevelNames[log_level])
        return

    def clean_up_log(self):
        """Closes an old log file and creates a new one.

        This method renames the current log file to .old.log and creates a
        new log file with the .log filename.

        If the original file was open for writing/appending, the new file
        will also be open for writing/appending

        """

        # create old.log file
        print "%s :: Cleaning up log file: %s" % (self.applicationName, self.logFileName)
        try:
            was_open = True
            self.close_log(log_closing=False)
        except:
            was_open = False

        (fileName, extension) = os.path.splitext(self.logFileName)
        old_file_name = "%s.old%s" % (fileName, extension)
        if os.path.exists(self.logFileName):
            if os.path.exists(old_file_name):
                os.remove(old_file_name)
            os.rename(self.logFileName, old_file_name)

        if was_open:
            self.__open_log()
        return

    def __write(self, msg, *args, **kwargs):
        """Writes the message to the log file taking into account
        the given arguments and keyword arguments.

        Arguments:
        msg    : string - The message to log
        args   : list   - List of arguments

        Keyword Arguments:
        kwargs : list - List of keyword arguments

        The arguments and keyword arguments are used in a string format way
        so and will replace the parameters in the message.

        """

        try:
            formatted_message = ""
            log_level = kwargs["level"]

            # determine if write is needed:
            if log_level < self.minLogLevel:
                return

            # convert possible tuple to string:
            msg = str(msg)

            # Fill the message with it's content
            if len(args) > 0:
                # print "# of args: %s" % (len(args[0]))
                msg = msg % args
            else:
                msg = msg

            # get frame information
            (source_file, source_line_number) = self.__find_caller()

            # get time information
            timestamp = datetime.datetime.today().strftime(self.timeFormat)

            # check for exception info, if present, add to end of string:
            if "exc_info" in kwargs:
                if self.logDual:
                    self.dualLog(traceback.format_exc())
                msg = "%s\n%s" % (msg, traceback.format_exc())

            # now split lines and write every ine into the logfile:
            lines = msg.splitlines()

            try:
                # check if multi-line
                if len(lines) > 1:
                    for i in range(0, len(lines)):
                        # for line in lines:
                        line = lines[i]
                        if len(line) > 0:
                            # if last line:
                            if i == 0:
                                line = line
                            elif i == len(lines) - 1:
                                line = '+ %s' % (line, )
                            else:
                                line = '| %s' % (line, )
                            formatted_message = self.logFormat % (timestamp, self.logLevelNames.get(log_level),
                                                                  source_file, source_line_number, line)
                            self.logHandle.write(formatted_message)
                else:
                    formatted_message = self.logFormat % (timestamp, self.logLevelNames.get(log_level), source_file,
                                                          source_line_number, msg)
                    self.logHandle.write(formatted_message)
            except UnicodeEncodeError:
                # self.Error("Unicode logging error", exc_info=True)
                formatted_message = formatted_message.encode('raw_unicode_escape')
                self.logHandle.write(formatted_message)
                raise

            # Finally close the file handle
            self.logEntryCount += 1
            if self.logEntryCount % self.flushInterval == 0:
                # self.logHandle.write("Saving")
                self.logEntryCount = 0
                self.logHandle.flush()
            return
        except:
            if self.logDual:
                self.dualLog("Retrospect Logger :: Error logging in Logger.py:")
                self.dualLog("---------------------------")
                self.dualLog(traceback.format_exc())
                self.dualLog("---------------------------")
                self.dualLog(repr(msg))
                self.dualLog(repr(args))
                # noinspection PyUnboundLocalVariable
                self.dualLog(repr(formatted_message))
                self.dualLog("---------------------------")
            else:
                traceback.print_exc()

    @staticmethod
    def __find_caller():
        """Find the stack frame of the caller.

        Find the stack frame of the caller so that we can note the source
        file name, line number and function name.

        """
        return_value = ("Unknown", 0)

        # get the current frame and descent down until the correct one is found
        # noinspection PyProtectedMember,SpellCheckingInspection
        current_frame = sys._getframe(3)  # could be _getframe(#) and (3)
        while hasattr(current_frame, "f_code"):
            co = current_frame.f_code
            source_file = os.path.normcase(co.co_filename)
            method_name = co.co_name
            # if currentFrame belongs to this logger.py, equals <string> or equals a private log
            # method (_log or __Log) continue searching.
            if source_file == "<string>" or source_file in os.path.normcase(__file__) \
                    or "stopwatch.py" in source_file \
                    or method_name in ("_Log", "__Log"):
                current_frame = current_frame.f_back
                continue
            else:
                # get the sourcePath and sourceFile
                (source_path, source_file) = os.path.split(source_file)
                return_value = (source_file, current_frame.f_lineno)
                break

        return return_value

    def __open_log(self):
        """Opens the log file for appending

        This method opens a logfile for writing. If one already exists, it will
        be appended. If it does not exist, a new one is created.

        Problem:
        If we would use open(self.logFileName, "a") we would get an invalid
        file descriptor error in Linux!

        Possible fixes:
        1 - Modding the flags to only have os.O_CREATE if the file does not exists
            works, but then the file is appended at position 0 instead of the end!

        2 - Using a custom file descriptor. This works, but now the file just keeps
            getting overwritten.

        3 - OR: why not do a manual append: first read the complete file into a
            string. Then do an open(self.logFileName, "w"), write the previous
            content and then just continue!

        Finally: stick to the basic open(file, mode) and changes modes depending on
        the available files.

        """

        if os.path.exists(self.logFileName):
            # the file already exists. Now to prevent errors in Linux
            # we will open a file in Read + (Read and Update) mode
            # and set the pointer to the end.
            self.logHandle = open(self.logFileName, "r+")
            self.logHandle.seek(0, 2)
            self.info("XOT Logger :: Appending Existing log file")
        else:
            log_dir = os.path.dirname(self.logFileName)
            if not os.path.isdir(log_dir):
                os.makedirs(log_dir)
            # no file exists, so just create a new one for writing
            self.logHandle = open(self.logFileName, "w")

        return
