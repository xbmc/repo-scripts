import sys
import pickle
import os
from common import urlparse
from common import parse_qs, clean_dict
from urls import UrlRule, NotFoundException, AmbiguousUrlException
from urllib import urlencode

#from . import xbmc
#from . import xbmcgui
#from . import xbmcplugin
#from . import xbmcaddon
from xbmcswift import xbmc, xbmcgui, xbmcplugin, xbmcaddon
#import xbmc
#import xbmcgui
#import xbmcplugin
#import xbmcaddon

debug_modes = ['test', 'interactive', 'crawl']

class Plugin(object):
    def __init__(self, name, plugin_id, filepath=None, debug=False):
        '''Initialize a plugin object for an XBMC addon.'''
        self._name = name
        self._filepath = filepath
        self._plugin_id = plugin_id

        # Keeps track of url routes
        self._routes = []
        self._view_functions = {}

        args = self.parse_commandline(sys.argv)

        self._plugin = xbmcaddon.Addon(id=self._plugin_id)
        if self._mode in debug_modes:
            self._plugin._setup(os.path.dirname(self._filepath))

        self._argv0, self._argv1, self._argv2 = args
        self.handle = int(self._argv1)

        self.qs_args = parse_qs(self._argv2.lstrip('?'))

        self.scheme, self.netloc, self.path = urlparse(self._argv0)

        self._cache_path = xbmc.translatePath('special://profile/addon_data/%s/.cache' % self._plugin_id)


    def parse_commandline(self, args):
        '''Used to set up a plugin's values to the same state whether
        we are called from XBMC or from the command line.

        Check if we are being run from the command line.
        If the second argument to the script is 'test', 'interactive', or
        'crawl', we are on the command line.
         
        If we are in debug mode, accept 2 extra optional arguments,
        (1) The url to use to jump into the plugin
        (2) A query string to go along with the url
        '''
        # Choose 'interactive' as the default case if no args provided.
        if len(args) < 2:
            args.append('interactive')

        if args[1] in ['test', 'interactive', 'crawl']:
            self._mode = args[1]
            # Default url and qs if none is provided
            url = 'plugin://%s/' % self._plugin_id
            qs = '?'
            # If we are given a url
            if len(args) >= 3:
                url = args[2]

            # If we are given a query string
            if len(args) == 4:
                qs = args[3]

            return [url, '0', qs]
        else:
            # We are being run from XBMC
            self._mode = 'xbmc'
            return args

    ## URL routing and module code --------------------------------------------

    def register_module(self, module, url_prefix):
        '''Registers a module with a plugin. Requires a url_prefix that
        will then enable calls to url_for.'''
        module._plugin = self
        for func in module._register_funcs:
            func(self, url_prefix)

    def route(self, url_rule, default=False, name=None, **options):
        '''A decorator to add a route to a view. name is used to
        differentiate when there are multiple routes for a given view.'''
        def decorator(f):
            view_name = name or f.__name__
            self.add_url_rule(url_rule, f, name=view_name, default=default, **options)
            return f
        return decorator

    def add_url_rule(self, url_rule, view_func, name, default=False, **options):
        rule = UrlRule(url_rule, view_func, name, **options)
        # Protect against multiple routes on a single name. If we are attempting to add another
        # route, set the value to None. Then when url_for is called, we can check and raise an error
        # if resolving is ambiguous.
        if name in self._view_functions.keys():
            self._view_functions[name] = None
        else:
            self._view_functions[name] = rule
        self._routes.append(rule)

    def url_for(self, endpoint, **items):
        if endpoint not in self._view_functions.keys():
            raise NotFoundException, '%s doesn\'t match any known patterns.' % endpoint

        rule = self._view_functions[endpoint]
        if not rule:
            raise AmbiguousUrlException

        pathqs = rule.make_path_qs(items)
        return 'plugin://%s%s' % (self._plugin_id, pathqs)

    def dispatch(self, path):
        for rule in self._routes:
            try:
                view_func, items = rule.match(path)
            except NotFoundException:
                continue
            return view_func(**items)
        raise NotFoundException

    ## XBMC stuff -------------------------------------------------------------
    def cache_fn(self, path):
        #if not os.path.exists(self._cache_path):
            #os.mkdir(self._cache_path)
        return os.path.join(self._cache_path, path)

    def temp_fn(self, path):
        return os.path.join(xbmc.translatePath('special://temp'), path)

    def get_string(self, stringid):
        return self._plugin.getLocalizedString(stringid)

    def set_content(self, content):
        contents = ['files', 'songs', 'artists', 'albums', 'movies', 'tvshows', 'episodes', 'musicvideos']
        assert content in contents, 'Content type not recognized.'
        xbmcplugin.setContent(self.handle, content)

    def get_setting(self, key):
        #if pickled_value:
            #return pickle.loads(self._plugin.getSetting(key))
        return self._plugin.getSetting(id=key)

    #def set_setting(self, key, val, pickled_value=False):
    def set_setting(self, key, val):
        #if pickled_value:
            #return self._plugin.setSetting(key, pickle.dumps(val))
        return self._plugin.setSetting(id=key, value=val)

    def open_settings(self):
        '''Opens the settings dialog within XBMC'''
        self._plugin.openSettings()

    def _make_listitem(self, label, label2='', iconImage='', thumbnail='',
                       path='', **options):
        li = xbmcgui.ListItem(label, label2=label2, iconImage=iconImage, thumbnailImage=thumbnail, path=path)

        cleaned_info = clean_dict(options.get('info'))
        if cleaned_info:
            li.setInfo('video', cleaned_info)

        if options.get('is_playable'):
            li.setProperty('IsPlayable', 'true')

        if options.get('context_menu'):
            li.addContextMenuItems(options['context_menu'])

            #endpoint = options['context_menu'].get('add_to_playlist')
            #if endpoint:
                #keys = ['label', 'label2', 'icon', 'thumbnail', 'path', 'info']

                # need the url for calling add_to_playlist this is thwat gets added to the context menu
                # need the current url for the item, it will be encoded in teh url for calling add_to_playlist
                # also other info in [keys] will be added to teh add_to_playlist url's qs so we can recreate the listitem
                # perhaps try pickling the listitem?
                #current_url = options.get('url')
                #context_menu_url = self.url_for(endpoint, url=options.get('url'), label=label, label2=label2, iconImage=iconImage, thumbnail=thumbnail) 
                #li.addContextMenuItems([('Add to Playlist', 'XBMC.RunPlugin(%s)' % context_menu_url)])

        #return li
        return options['url'], li, options.get('is_folder', True)

    def add_items(self, iterable):
        # If we are in debug mode, do not make the call to xbmc
        # for each item
        #   if in debug mode, print it to command line
        #   make a list item
        #   if, set is_playable
        #   if, set context_menu
        #   append to new list
        #
        #   add the items
        #   call end of directory
        #   return the urls of each of the items

        #items = [self._make_list_item(**li_info) for li_info in iterable]

        items = [] # Keeps track of the list of tuples (url, list_item, is_folder) to pass to xbmcplugin.addDirectoryItems
        urls = [] # Keeps track of the XBMC urls for all of the list items
        for i, li_info in enumerate(iterable):
            items.append(self._make_listitem(**li_info))
            if self._mode in ['crawl', 'interactive', 'test']:
                #print '[%d] %s%s%s (%s)' % (i + 1, C.blue, li_info.get('label'), C.end, li_info.get('url'))
                print '[%d] %s%s%s (%s)' % (i + 1, '', li_info.get('label'), '', li_info.get('url'))
                urls.append(li_info.get('url'))

        if self._mode is 'xbmc':
            if not xbmcplugin.addDirectoryItems(self.handle, items, len(items)):
                raise Exception, 'problem?'
            xbmcplugin.endOfDirectory(self.handle)

        return urls

    def add_to_playlist(self, items, playlist='video'):
        playlists = {'music': 0, 'video': 1}
        selected_playlist = xbmc.PlayList(playlists[playlist])

        for li_info in items:
            url, li, is_folder = self._make_listitem(**li_info)
            li.setProperty('IsPlayable', 'true')
            selected_playlist.add(url, li)

    def make_url_with_options(self, url, **options):
        optionstring = ' '.join('%s=%s' % (key, val) for key, val in options.items())
        return ' '.join([url, optionstring])

    def set_resolved_url(self, url):
        if self._mode in ['crawl', 'interactive', 'test']:
            print 'ListItem resolved to %s' % url

        li = xbmcgui.ListItem(path=url)
        xbmcplugin.setResolvedUrl(self.handle, True, li)

        # CLI modes expect a list to be returned.
        if self._mode in ['interactive', 'crawl', 'test']:
            return []

    ### Run modes -------------------------------------------------------------
    def _fake_run(self, url):
        '''Manually sets some vars on the current instance. Used instead of
        calling __init__ on an instance.'''
        # Manually forge some properties since we aren't reinitializing our plugin.
        # no partition in python 2.4
        #self._argv0, _, self._argv2 = url.partition('?')
        parts = url.split('?', 1)
        self._argv0 = parts[0]
        if len(parts) == 2:
            self._argv2 = parts[1]
        else:
            self._argv2 = ''

        self.qs_args = parse_qs(self._argv2.lstrip('?'))
        self.scheme, self.netloc, self.path = urlparse(self._argv0)

        # Now run the actual selection's view
        return self.dispatch(self.path)


    def interactive(self):
        '''Provides an interactive menu from the command line that emulates the
        simple list-like interface within XBMC.'''
        # First run the starting path
        urls = self.dispatch(self.path)

        # Now loop while the user doesn't quit
        inp = raw_input('Choose an item or "q" to quit: ')
        while inp != 'q':
            # Choose the selected url
            try:
                url = urls[int(inp) - 1]
            except ValueError:
                # Passed something that cound't be converted with int()
                inp = raw_input('You entered a non-integer. Choice must be an integer or "q": ')
            except IndexError:
                # Passed an integer that was out of range of the list of urls
                inp = raw_input('You entered an invalid integer. Choice must be from above url list or "q": ')
            else:
                print '--\n' 
                urls = self._fake_run(url)
                inp = raw_input('Choose an item or "q" to quit: ')

    def crawl(self):
        '''Performs a breadth-first crawl of all possible routes from the
        starting path. Will only visit a URL once, even if it is referenced
        multiple times in a plugin. Requires user interaction in between each
        fetch.'''
        # Prime the queue with the starting path's result
        to_visit = self.dispatch(self.path)
        visited = []

        while to_visit:
            url = to_visit.pop(0)
            visited.append(url)

            print '--'
            print 'Next url to resolve: %s' % url
            raw_input('Continue?')

            urls = self._fake_run(url)

            # Filter new urls by checking against urls_visited and urls_tovisit sets
            urls = filter(lambda u: u not in visited and u not in to_visit, urls)
            to_visit.extend(urls)

    def redirect(self, url):
        '''Used when you need to redirect to another view, and you only have the final
        plugin:// url.'''
        return self._fake_run(url)

    def run(self):
        '''The main entry point for a plugin. Will route to the proper view
        based on the path parsed from the command line arguments.'''
        debug_modes = {
            'interactive': self.interactive,
            'crawl': self.crawl,
        }
        if self._mode in debug_modes.keys():
            debug_modes[self._mode]()
        else:
            self.dispatch(self.path)










