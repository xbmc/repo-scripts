"""
Created on 1/11/22

@author: Frank Feuerbacher
"""
import datetime
import time


class StripTimePatch:
    """
    Contains a work around for a complex bug in datetime.strptime that only
    impacts embedded Python, which Kodi uses. For more info on the defect,
    see: : https://bugs.python.org/issue27400

    One option is for you to replace every reference to datetime.strptime to use
    strptime_patch here. This is less voodoo, but there is always the possibility
    that some library code uses strptime and there will still be potential for
    incorrect results or a Kodi crash.

    The other option is to call patch_strptime at your addon's startup. This
    will Monkey-Patch striptime with the version here. It is voodoo like,
    but that is done a bit in Python.
    """

    @staticmethod
    def monkey_patch_strptime():
        # Check if problem exists (don't want to stomp on patch applied earlier)
        try:
            datetime.datetime.strptime('0', '%H')
        except TypeError:
            # Globally replace Python's datetime.datetime.strptime with
            # the version here.

            datetime.datetime = StripTimePatch.strptime

    @staticmethod
    def strptime(date_string: str, date_format: str) -> datetime.datetime:
        """
        Monkey-Patch dattime.strptime with time.strptime in order to
        work around a known embedded python problem.

        The patch works fairly well, as long as the format does not try
        to parse sub-second values. Since Python's datetime.strptime and
        time.strptime sit on top of libc's strptime.

        From Python documentation on datetime.strptime
        (https://docs.python.org/3/library/datetime.html#strftime-strptime-behavior):

            classmethod datetime.strptime(date_string, format)

            Return a datetime corresponding to date_string, parsed according
            to format.

            Using datetime.strptime(date_string, format) is equivalent to:

            datetime(*(time.strptime(date_string, format)[0:6]))

            except when the format includes sub-second components or timezone
            offset information, which are supported in datetime.strptime but
            are discarded by time.strptime.

            ValueError is raised if the date_string and format can’t be parsed
            by time.strptime() or if it returns a value which isn’t a time
            tuple. For a complete list of formatting directives, see
            strftime() and strptime() Behavior.


        This Python bug has been around a long time, but not fixed due to
        lack of funding for embedded systems. For more info on the defect,
        see: : https://bugs.python.org/issue27400

        :param date_string:
        :param date_format:
        :return:
        """
        result: datetime.datetime
        result = datetime.datetime(*(time.strptime(date_string,
                                                   date_format)[0:6]))
        return result
