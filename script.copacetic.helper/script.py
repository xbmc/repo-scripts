# author: realcopacetic

from resources.lib.script.actions import *
from resources.lib.utilities import clear_cache, sys, urllib


class Main:
    def __init__(self, *args):
        try:
            self.params = dict(arg.split('=', 1) for arg in args)
            self._parse_params()
        except:
            self.params = {}
        function = eval(self.params['action'])
        function(**self.params)
    
    def _parse_params(self):
        try:
            for key, value in self.params.items():
                if ('\'\"' and '\"\'') in value:
                    start_pos = value.find('\'\"')
                    end_pos = value.find('\"\'')
                    clean_title = value[start_pos+2:end_pos]
                    self.params[key] = clean_title
        except Exception:
            self.params = {}

if __name__ == '__main__':
    Main(*sys.argv[1:])
