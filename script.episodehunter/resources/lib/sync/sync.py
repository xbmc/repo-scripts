import xbmc

import resources.lib.gui.dialog as dialog
import resources.lib.gui.progress as progress
import resources.lib.helper as helper
from resources.exceptions import UserAbortExceptions


class Sync(object):
    """ Abstract baseclass for sync """

    def __init__(self, connection):
        super(Sync, self).__init__()
        self.progress = None
        self.connection = connection

    @staticmethod
    def ask_user_yes_or_no(*lines):
        return dialog.create_yes_no(*lines)

    @staticmethod
    def create_ok_dialog(msg):
        dialog.create_ok(msg)

    @staticmethod
    def create_error_dialog(*msg):
        dialog.create_error_dialog(*msg)

    def create_progress(self, msg):
        self.progress = progress.create(msg)
        return self.progress

    def progress_update(self, percent, line=None):
        if line is None:
            self.progress.update(percent)
        else:
            self.progress.update(percent, line)

    def is_canceled(self):
        if xbmc.abortRequested:
            raise SystemExit()
        if self.progress.iscanceled():
            raise UserAbortExceptions()

    def quit(self):
        self.progress.close()