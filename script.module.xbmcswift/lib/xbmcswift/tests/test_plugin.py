#!/usr/bin/env python
from unittest import TestCase
from xbmcswift.plugin import Plugin
from xbmcswift.module import Module
from xbmcswift.urls import AmbiguousUrlException
import sys

class TestPlugiFromXBMC(TestCase):
    def setUp(self):
        sys.argv = ['special://my.plugin.id/', '0', '?foo=bar'] 

    def test_init(self):
        plugin = Plugin('My Plugin', 'my.plugin.id')
        self.assertEqual(plugin._name, 'My Plugin')
        self.assertEqual(plugin._plugin_id, 'my.plugin.id')
        self.assertEqual(plugin._argv0, 'special://my.plugin.id/')
        self.assertEqual(plugin._argv1, '0')
        self.assertEqual(plugin._argv2, '?foo=bar')
        self.assertEqual(plugin.qs_args, {'foo': 'bar'})
        self.assertEqual(plugin.handle, 0)
        self.assertEqual(plugin.scheme, 'special')
        self.assertEqual(plugin.netloc, plugin._plugin_id)
        self.assertEqual(plugin.path, '/')

class TestPluginCLIArgs(TestCase):
    def test_init_2_args(self):
        sys.argv = ['doesnotmatter.py', 'interactive']
        plugin = Plugin('My Plugin', 'my.plugin.id')
        self.assertEqual(plugin._name, 'My Plugin')
        self.assertEqual(plugin._plugin_id, 'my.plugin.id')
        self.assertEqual(plugin._argv0, 'special://my.plugin.id/')
        self.assertEqual(plugin._argv1, '0')
        self.assertEqual(plugin._argv2, '?')
        self.assertEqual(plugin.qs_args, {})
        self.assertEqual(plugin.handle, 0)
        self.assertEqual(plugin.scheme, 'special')
        self.assertEqual(plugin.netloc, plugin._plugin_id)
        self.assertEqual(plugin.path, '/')

    def test_init_3_args(self):
        sys.argv = ['doesnotmatter.py', 'interactive', 'special://my.plugin.id/testpath/']
        plugin = Plugin('My Plugin', 'my.plugin.id')
        self.assertEqual(plugin._name, 'My Plugin')
        self.assertEqual(plugin._plugin_id, 'my.plugin.id')
        self.assertEqual(plugin._argv0, 'special://my.plugin.id/testpath/')
        self.assertEqual(plugin._argv1, '0')
        self.assertEqual(plugin._argv2, '?')
        self.assertEqual(plugin.qs_args, {})
        self.assertEqual(plugin.handle, 0)
        self.assertEqual(plugin.scheme, 'special')
        self.assertEqual(plugin.netloc, plugin._plugin_id)
        self.assertEqual(plugin.path, '/testpath/')

    def test_init_4_args(self):
        sys.argv = ['doesnotmatter.py', 'interactive', 'special://my.plugin.id/', '?foo=bar'] 
        plugin = Plugin('My Plugin', 'my.plugin.id')
        self.assertEqual(plugin._name, 'My Plugin')
        self.assertEqual(plugin._plugin_id, 'my.plugin.id')
        self.assertEqual(plugin._argv0, 'special://my.plugin.id/')
        self.assertEqual(plugin._argv1, '0')
        self.assertEqual(plugin._argv2, '?foo=bar')
        self.assertEqual(plugin.qs_args, {'foo': 'bar'})
        self.assertEqual(plugin.handle, 0)
        self.assertEqual(plugin.scheme, 'special')
        self.assertEqual(plugin.netloc, plugin._plugin_id)
        self.assertEqual(plugin.path, '/')

class TestPluginRoutes(TestCase):
    def setUp(self):
        self.plugin = Plugin('My Plugin', 'my.plugin.id')

    def test_single_route(self):
        @self.plugin.route('/') 
        def mock_view():
            return 'foo'
        self.assertEqual(self.plugin.dispatch('/'), 'foo')
        self.assertEqual(self.plugin.url_for('mock_view'), 'special://my.plugin.id/')

    def test_multi_routes(self):
        @self.plugin.route('/') 
        def mock_view():
            return 'foo'
        @self.plugin.route('/bar')
        def mock_view2():
            return 'bar'

        self.assertEqual(self.plugin.dispatch('/'), 'foo')
        self.assertEqual(self.plugin.url_for('mock_view'), 'special://my.plugin.id/')
        self.assertEqual(self.plugin.dispatch('/bar'), 'bar')
        self.assertEqual(self.plugin.url_for('mock_view2'), 'special://my.plugin.id/bar')

    def test_multi_route_view(self):
        @self.plugin.route('/') 
        @self.plugin.route('/bar')
        def mock_view():
            return 'foo'

        self.assertEqual(self.plugin.dispatch('/'), 'foo')
        self.assertEqual(self.plugin.dispatch('/bar'), 'foo')
        self.assertRaises(AmbiguousUrlException, self.plugin.url_for, 'mock_view')

    def test_multi_route_view_names(self):
        @self.plugin.route('/foo', name='foo') 
        @self.plugin.route('/bar', name='bar')
        def mock_view():
            return 'baz'

        self.assertEqual(self.plugin.dispatch('/foo'), 'baz')
        self.assertEqual(self.plugin.dispatch('/bar'), 'baz')
        self.assertEqual(self.plugin.url_for('foo'), 'special://my.plugin.id/foo')
        self.assertEqual(self.plugin.url_for('bar'), 'special://my.plugin.id/bar')

    def test_multi_route_keywords(self):
        @self.plugin.route('/foo/<var1>')
        def mock_view(var1):
            return var1
        @self.plugin.route('/bar/', var2='bar')
        def mock_view2(var2):
            return var2

        self.assertEqual(self.plugin.dispatch('/foo/baz'), 'baz')
        self.assertEqual(self.plugin.url_for('mock_view', var1='baz'), 'special://my.plugin.id/foo/baz')
        self.assertEqual(self.plugin.dispatch('/bar/'), 'bar')
        self.assertEqual(self.plugin.url_for('mock_view2'), 'special://my.plugin.id/bar/')

    def test_optional_keyword_routes(self):
        @self.plugin.route('/foo/', name='noarg', var1='bar')
        @self.plugin.route('/foo/<var1>', name='1arg')
        def mock_view(var1):
            return var1

        self.assertEqual(self.plugin.dispatch('/foo/'), 'bar')
        self.assertEqual(self.plugin.url_for('noarg'), 'special://my.plugin.id/foo/')
        self.assertEqual(self.plugin.dispatch('/foo/biz'), 'biz')
        self.assertEqual(self.plugin.url_for('1arg', var1='biz'), 'special://my.plugin.id/foo/biz')

class TestPluginModuleRoutes(TestCase):
    def setUp(self):
        self.plugin = Plugin('My Plugin', 'my.plugin.id')
        self.module = Module('mymodule')

    def test_routes(self):
        @self.module.route('/')
        def mock_view():
            return 'foo'

        @self.plugin.route('/')
        def mock_view2():
            return 'bar'

        self.plugin.register_module(self.module, '/module')

        self.assertEqual(self.plugin.dispatch('/'), 'bar')
        self.assertEqual(self.plugin.dispatch('/module/'), 'foo')
        self.assertEqual(self.plugin.url_for('mock_view2'), 'special://my.plugin.id/')
        self.assertEqual(self.plugin.url_for('mymodule.mock_view'), 'special://my.plugin.id/module/')
        self.assertEqual(self.module.url_for('mock_view'), 'special://my.plugin.id/module/')
        print 'here?'


class TestPluginMakeListitem(TestCase):
    def setUp(self):
        sys.argv = ['doesnotmatter.py', 'interactive', 'special://my.plugin.id/testpath/']
        self.plugin = Plugin('My Plugin', 'my.plugin.id')
        @self.plugin.route('/videos/')
        def show_videos():
            return 'videos'

    def test_1_item(self):
        item = {'label': 'My video',
                'url': self.plugin.url_for('show_videos'),
                }
        url, li, is_folder = self.plugin._make_listitem(**item)
        self.assertEqual(url, 'special://my.plugin.id/videos/')
        #import xbmcgui
        #self.assertEqual(li, xbmcgui.ListItem('My video'))
        self.assertEqual(is_folder, True)

class TestAddItems(TestCase):
    def setUp(self):
        sys.argv = ['doesnotmatter.py', 'interactive', 'special://my.plugin.id/testpath/']
        self.plugin = Plugin('My Plugin', 'my.plugin.id')
        @self.plugin.route('/videos/')
        def show_videos():
            return 'videos'

    def test_1_item(self):
        items = [
            {'label': 'My video', 'url': self.plugin.url_for('show_videos'), },
            {'label': 'My video2', 'url': self.plugin.url_for('show_videos'), },
        ]
        urls = self.plugin.add_items(items)
        self.assertEqual(urls, ['special://my.plugin.id/videos/', 'special://my.plugin.id/videos/'])
        





