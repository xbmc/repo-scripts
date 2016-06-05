from lib import tablo
import xbmcgui


def dialogFunction(f):
    def wrap(self, *args, **kwargs):
        self._showingDialog = True
        f(self, *args, **kwargs)
        self._showingDialog = False
    return wrap


def tabloErrorHandler(f):
    def wrap(self, *args, **kwargs):
        try:
            return f(self, *args, **kwargs)
        except tablo.APIError, e:
            if e.code != 503:
                raise
            xbmcgui.Dialog().ok('Unavailable', e.message.get('description', 'Unknown'))

    return wrap
