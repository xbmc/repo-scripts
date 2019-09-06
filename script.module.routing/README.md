[![GitHub release](https://img.shields.io/github/release/tamland/kodi-plugin-routing.svg)](https://github.com/tamland/kodi-plugin-routing/releases)
[![Build Status](https://travis-ci.org/tamland/kodi-plugin-routing.svg?branch=master)](https://travis-ci.org/tamland/kodi-plugin-routing)
[![License: GPLv3](https://img.shields.io/badge/License-GPLv3-yellow.svg)](https://opensource.org/licenses/GPL-3.0)
[![Contributors](https://img.shields.io/github/contributors/tamland/kodi-plugin-routing.svg)](https://github.com/tamland/kodi-plugin-routing/graphs/contributors)

# Plugin routing

Library for building and parsing URLs in [Kodi](http://kodi.tv) plugins.


## Example

```python
import routing
from xbmcgui import ListItem
from xbmcplugin import addDirectoryItem, endOfDirectory

plugin = routing.Plugin()

@plugin.route('/')
def index():
    addDirectoryItem(plugin.handle, plugin.url_for(show_category, "one"), ListItem("Category One"), True)
    addDirectoryItem(plugin.handle, plugin.url_for(show_category, "two"), ListItem("Category Two"), True)
    addDirectoryItem(plugin.handle, plugin.url_for(show_directory, "/dir/one"), ListItem("Directory One"), True)
    addDirectoryItem(plugin.handle, plugin.url_for(show_directory, "/dir/two"), ListItem("Directory Two"), True)
    endOfDirectory(plugin.handle)

@plugin.route('/category/<category_id>')
def show_category(category_id):
    addDirectoryItem(plugin.handle, "", ListItem("Hello category %s!" % category_id))
    endOfDirectory(plugin.handle)

@plugin.route('/directory/<path:dir>')
def show_directory(dir):
    addDirectoryItem(plugin.handle, "", ListItem("List directory %s!" % dir))
    endOfDirectory(plugin.handle)

if __name__ == '__main__':
    plugin.run()
```


## Creating rules

The `route()` decorator binds a function to an URL pattern. The pattern is a
path expression consisting of static parts and variable parts of an URL.
Variables are enclosed in angle brackets as `<variable_name>` and will be passed
to the function as keyword arguments.

For example:

```python
@plugin.route('/hello/<what>')
def hello(what):
    # will be called for all incoming URLs like "/hello/world", "/hello/123" etc.
    # 'what' will contain "world", "123" etc. depending on the URL.
    pass
```

In case your variable contains slashes (i.e. is a path or URL) and you want
to match this, you can use the `path` identifier in the patern.

```python
@plugin.route('/url/<path:url>')
def parse_url(url):
    # will be called for all incoming URLs like "/url/https://foo.bar/baz" etc.
    # 'url' can be any string with slashes.
    pass
```

Routes can also be registered manually with the `add_route` method. 


## Building URLs

`url_for()` can be used to build URLs for registered functions. It takes a
reference to a function and a number of arguments that corresponds to variables
in the URL rule.

For example:

```python
plugin.url_for(hello, what="world")
```

will read the rule for `hello`, fill in the variable parts and return a final URL:

```
plugin://my.addon.id/hello/world
```

which can be passed to `xbmcplugin.addDirectoryItem()`. All variable parts must
be passed to `url_for` either as ordered arguments or keyword arguments.

Keywords that does not occur in the function/pattern will be added as query string in the returned URL.

Alternatively, URLs can be created directly from a path with `url_for_path`. For
example `url_for_path('/foo/bar')` will return `plugin://my.addon.id/foo/bar`.
Unlike `url_for` this method will not check that the path is valid.


## Query string

The query string part of the URL is parsed with `urlparse.parse_qs` and is
accessible via the `plugin.args` attribute. The dictionary keys corresponds to
query variables and values to lists of query values.

Example:

```python
@plugin.route('/')
def index():
    url = plugin.url_for(search, query="hello world")
    addDirectoryItem(plugin.handle, url, ListItem("Search"))
    # ...


@plugin.route('/search')
def search():
    query = plugin.args['query'][0]
    addDirectoryItem(plugin.handle, "", ListItem("You searched for '%s'" % query))
    # ...
```


## Creating a dependency in your addon

To get kodi to install this dependency you will have to add a command to your `addons.xml`.
```xml
    <requires>
        <import addon="xbmc.python" version="2.25.0" />
        <import addon="script.module.routing" version="0.2.0"/>
    </requires>
```
