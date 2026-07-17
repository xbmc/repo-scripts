from jurialmunkey.plugin import KodiPlugin
from jurialmunkey.parser import reconfigure_legacy_params
from lib.api import WikipediaGUI


KODIPLUGIN = KodiPlugin('script.wikipedia')
ADDONPATH = KODIPLUGIN._addon_path


def do_wikipedia_gui(wikipedia, tmdb_type=None, xml_file=None, language=None, **kwargs):
    if not wikipedia:
        return
    ui = WikipediaGUI(
        xml_file or 'script-wikipedia.xml', ADDONPATH, 'default', '1080i',
        query=wikipedia, tmdb_type=tmdb_type, language=language)
    ui.doModal()
    del ui


class Script():
    def __init__(self, *args):
        self.params = {}
        for arg in args:
            if '=' in arg:
                key, value = arg.split('=', 1)
                self.params[key] = value.strip('\'').strip('"') if value else None
            else:
                self.params[arg] = True
        self.params = reconfigure_legacy_params(**self.params)

    routing_table = {
        'wikipedia':
            lambda **kwargs: do_wikipedia_gui(**kwargs)}

    def router(self):
        if not self.params.get('wikipedia'):
            import xbmcgui
            self.params['wikipedia'] = xbmcgui.Dialog().input(heading='Wikipedia')
        routes_available = set(self.routing_table.keys())
        params_given = set(self.params.keys())
        route_taken = set.intersection(routes_available, params_given).pop()
        return self.routing_table[route_taken](**self.params)
