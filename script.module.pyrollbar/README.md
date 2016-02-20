# Rollbar notifier for Python [![Build Status](https://travis-ci.org/rollbar/pyrollbar.png?branch=v0.11.0)](https://travis-ci.org/rollbar/pyrollbar)

<!-- RemoveNext -->
Python notifier for reporting exceptions, errors, and log messages to [Rollbar](https://rollbar.com).

<!-- Sub:[TOC] -->

## Quick start

Install using pip:

```bash
pip install rollbar
```

```python
import rollbar
rollbar.init('POST_SERVER_ITEM_ACCESS_TOKEN', 'production')  # access_token, environment

try:
    main_app_loop()
except IOError:
    rollbar.report_message('Got an IOError in the main loop', 'warning')
except:
    # catch-all
    rollbar.report_exc_info()
```

## Requirements

- Python 2.6, 2.7, 3.2, 3.3, 3.4, or 3.5
- requests 0.12+
- A Rollbar account

## Configuration

### Django

In your ``settings.py``, add ``'rollbar.contrib.django.middleware.RollbarNotifierMiddleware'`` as the last item in ``MIDDLEWARE_CLASSES``:

```python
MIDDLEWARE_CLASSES = (
    # ... other middleware classes ...
    'rollbar.contrib.django.middleware.RollbarNotifierMiddleware',
)
```

Add these configuration variables in ``settings.py``:

```python
ROLLBAR = {
    'access_token': 'POST_SERVER_ITEM_ACCESS_TOKEN',
    'environment': 'development' if DEBUG else 'production',
    'branch': 'master',
    'root': '/absolute/path/to/code/root',
}
```

<!-- RemoveNextIfProject -->
Be sure to replace ```POST_SERVER_ITEM_ACCESS_TOKEN``` with your project's ```post_server_item``` access token, which you can find in the Rollbar.com interface.

Check out the [Django example](https://github.com/rollbar/pyrollbar/tree/master/rollbar/examples/django).

### Pyramid

In your ``ini`` file (e.g. ``production.ini``), add ``rollbar.contrib.pyramid`` to the end of your ``pyramid.includes``:

```ini
[app:main]
pyramid.includes =
    pyramid_debugtoolbar
    rollbar.contrib.pyramid
```
  
And add these rollbar configuration variables:

```ini
[app:main]
rollbar.access_token = POST_SERVER_ITEM_ACCESS_TOKEN
rollbar.environment = production
rollbar.branch = master
rollbar.root = %(here)s
```
<!-- RemoveNextIfProject -->
Be sure to replace ```POST_SERVER_ITEM_ACCESS_TOKEN``` with your project's ```post_server_item``` access token, which you can find in the Rollbar.com interface.

The above will configure Rollbar to catch and report all exceptions that occur inside your Pyramid app. However, in order to catch exceptions in middlewares or in Pyramid itself, you will also need to wrap your app inside a ```pipeline``` with Rollbar as a ```filter```.

To do this, first change your ```ini``` file to use a ```pipeline```. Change this:

```ini
[app:main]
#...
```

To:

```ini
[pipeline:main]
pipeline =
    rollbar
    YOUR_APP_NAME

[app:YOUR_APP_NAME]
pyramid.includes =
    pyramid_debugtoolbar
    rollbar.contrib.pyramid

rollbar.access_token = POST_SERVER_ITEM_ACCESS_TOKEN
rollbar.environment = production
rollbar.branch = master
rollbar.root = %(here)s

[filter:rollbar]
use = egg:rollbar#pyramid
access_token = POST_SERVER_ITEM_ACCESS_TOKEN
environment = production
branch = master
root = %(here)s
```

Note that the access_token, environment, and other Rollbar config params do need to be present in both the ```app``` section and the ```filter``` section.


### Flask

Check out [rollbar-flask-example](https://github.com/rollbar/rollbar-flask-example).


### Bottle

Import the plugin and install!
Can be installed globally or on a per route basis.

```python
import bottle
from rollbar.contrib.bottle import RollbarBottleReporter

rbr = RollbarBottleReporter(access_token='POST_SERVER_ITEM_ACCESS_TOKEN', environment='production') #setup rollbar

bottle.install(rbr) #install globally

@bottle.get('/')
def raise_error():
  '''
  When navigating to /, we'll get a regular 500 page from bottle, 
  as well as have the error below listed on Rollbar.
  '''
  raise Exception('Hello, Rollbar!')

if __name__ == '__main__':
    bottle.run(host='localhost', port=8080)
```

<!-- RemoveNextIfProject -->
Be sure to replace ```POST_SERVER_ITEM_ACCESS_TOKEN``` with your project's ```post_server_item``` access token, which you can find in the Rollbar.com interface.


### Twisted

Check out the [Twisted example](https://github.com/rollbar/pyrollbar/tree/master/rollbar/examples/twisted).


### Other

For generic Python or a non-Django/non-Pyramid framework just initialize the Rollbar library with your access token and environment.

```python
rollbar.init('POST_SERVER_ITEM_ACCESS_TOKEN', environment='production', **other_config_params)
```

Other options can be passed as keyword arguments. See the reference below for all options.

### Command-line usage

pyrollbar comes with a command-line tool that can be used with other UNIX utilities to create an ad-hoc monitoring solution.

e.g. Report all 5xx haproxy requests as ```warning```

```bash
tail -f /var/log/haproxy.log | awk '{print $11,$0}' | grep '^5' | awk '{$1="";print "warning",$0}' | rollbar -t POST_SERVER_ITEM_ACCESS_TOKEN -e production -v
```

e.g. Test an access token

```bash
rollbar -t POST_SERVER_ITEM_ACCESS_TOKEN -e test debug testing access token
```

#### Reference

```
$ rollbar --help
Usage: rollbar [options]

Options:
  --version             show program's version number and exit
  -h, --help            show this help message and exit
  -t ACCESS_TOKEN, --access_token=ACCESS_TOKEN
                        You project's access token from rollbar.com.
  -e ENVIRONMENT, --environment=ENVIRONMENT
                        The environment to report errors and messages to.
  -u ENDPOINT_URL, --url=ENDPOINT_URL
                        The Rollbar API endpoint url to send data to.
  -m HANDLER, --handler=HANDLER
                        The method in which to report errors.
  -v, --verbose         Print verbose output.
```

## Usage

The Django, Pyramid, Flask, and Bottle integrations will automatically report uncaught exceptions to Rollbar.

### Exceptions

To report a caught exception to Rollbar, use ```rollbar.report_exc_info()```:

```python
try:
    do_something()
except:
    rollbar.report_exc_info(sys.exc_info())
    # or if you have a webob-like request object, pass that as well:
    # rollbar.report_exc_info(sys.exc_info(), request)
```

### Logging

You can also send any other log messages you want, using ```rollbar.report_message()```:

```python
try:
    do_something()
except IOError:
    rollbar.report_message('Got an IOError while trying to do_something()', 'warning')
    # report_message() also accepts a request object:
    #rollbar.report_message('message here', 'warning', request)
```

### Examples

Here's a full example, integrating into a simple Gevent app.

```python
"""
Sample Gevent application with Rollbar integration.
"""
import sys
import logging

from gevent.pywsgi import WSGIServer
import rollbar
import webob

# configure logging so that rollbar's log messages will appear
logging.basicConfig()

def application(environ, start_response):
    request = webob.Request(environ)
    status = '200 OK'
    headers = [('Content-Type', 'text/html')]
    start_response(status, headers)

    yield '<p>Hello world</p>'

    # extra fields we'd like to send along to rollbar (optional)
    extra_data = {'datacenter': 'us1', 'app' : {'version': '1.1'}}

    try:
        # will raise a NameError about 'bar' not being defined
        foo = bar
    except:
        # report full exception info
        rollbar.report_exc_info(sys.exc_info(), request, extra_data=extra_data)

        # and/or, just send a string message with a level
        rollbar.report_message("Here's a message", 'info', request, extra_data=extra_data)

        yield '<p>Caught an exception</p>'

# initialize rollbar with an access token and environment name
rollbar.init('POST_SERVER_ITEM_ACCESS_TOKEN', 'development')

# now start the wsgi server
WSGIServer(('', 8000), application).serve_forever()
```

## Configuration reference

  <dl>
  <dt>access_token</dt>
  <dd>Access token from your Rollbar project
  </dd>
  <dt>agent.log_file</dt>
  <dd>If ```handler``` is ```agent```, the path to the log file. Filename must end in ```.rollbar```
  </dd>
  <dt>branch</dt>
  <dd>Name of the checked-out branch.

Default: ```master```

  </dd>
  <dt>code_version</dt>
  <dd>A string describing the current code revision/version (i.e. a git sha). Max 40 characters. Default `None`</dd>
  <dt>enabled</dt>
  <dd>Controls whether or not Rollbar will report any data

Default: ```True```

  </dd>
  <dt>endpoint</dt>
  <dd>URL items are posted to.
    
Default: ```https://api.rollbar.com/api/1/item/```

  </dd>
  <dt>environment</dt>
  <dd>Environment name. Any string up to 255 chars is OK. For best results, use "production" for your production environment.
  </dd>
  <dt>exception_level_filters</dt>
  <dd>List of tuples in the form ```(class, level)``` where ```class``` is an Exception class you want to always filter to the respective ```level```. Any subclasses of the given ```class``` will also be matched.

Valid levels: ```'critical'```, ```'error'```, ```'warning'```, ```'info'```, ```'debug'``` and ```'ignored'```.

Use ```'ignored'``` if you want an Exception (sub)class to never be reported to Rollbar.
    
Any exceptions not found in this configuration setting will default to ```'error'```.

Django ```settings.py``` example (and Django default):
        
```python
from django.http import Http404

ROLLBAR = {
    ...
    'exception_level_filters': [
        (Http404, 'warning')
    ]
}
```

In a Pyramid ``ini`` file, define each tuple as an individual whitespace delimited line, for example:
        
```
rollbar.exception_level_filters =
    pyramid.exceptions.ConfigurationError critical
    #...
```
   
  </dd>
  <dt>handler</dt>
  <dd>The method for reporting rollbar items to api.rollbar.com
  
One of:

- blocking -- runs in main thread
- thread -- spawns a new thread
- agent -- writes messages to a log file for consumption by rollbar-agent
- tornado -- uses the Tornado async library to send the payload
- gae -- uses the Google AppEngineFetch library to send the payload
- twisted -- uses the Twisted event-driven networking library to send the payload

Default: ```thread```

  </dd>
  <dt>locals</dt>
  <dd>Configuration for collecting local variables. A dictionary:
    <dl>
      <dt>enabled</dt>
      <dd>If `True`, variable values will be collected for stack traces. Default `True`.</dd>
      <dt>safe_repr</dt>
      <dd>If `True`, non-built-in objects will be serialized into just their class name. If `False` `repr(obj)`
      will be used for serialization. Default `True`.</dd>
      <dt>sizes</dt>
      <dd>Dictionary of configuration describing the max size to repr() for each type.
        <dl>
          <dt>maxdict</dt>
          <dd>Default 10</dd>
          <dt>maxarray</dt>
          <dd>Default 10</dd>
          <dt>maxlist</dt>
          <dd>Default 10</dd>
          <dt>maxtuple</dt>
          <dd>Default 10</dd>
          <dt>maxset</dt>
          <dd>Default 10</dd>
          <dt>maxfrozenset</dt>
          <dd>Default 10</dd>
          <dt>maxdeque</dt>
          <dd>Default 10</dt>
          <dt>maxstring</dt>
          <dd>Default 100</dd>
          <dt>maxlong</dt>
          <dd>Default 40</dd>
          <dt>maxother</dt>
          <dd>Default 100</dd>
        </dl>
      </dd>
      <dt>whitelisted_types</dt>
      <dd>A list of `type` objects, (e.g. `type(my_class_instance)` or `MyClass`) that will be serialized using
      `repr()`. Default `[]`</dd>
    </dl>
  </dd>
  <dt>root</dt>
  <dd>Absolute path to the root of your application, not including the final ```/```. 
  </dd>
  <dt>scrub_fields</dt>
  <dd>List of sensitive field names to scrub out of request params and locals. Values will be replaced with asterisks. If overriding, make sure to list all fields you want to scrub, not just fields you want to add to the default. Param names are converted to lowercase before comparing against the scrub list.

Default: ```['pw', 'passwd', 'password', 'secret', 'confirm_password', 'confirmPassword', 'password_confirmation', 'passwordConfirmation', 'access_token', 'auth', 'authentication']```

  </dd>
  <dt>timeout</dt>
  <dd>Timeout for any HTTP requests made to the Rollbar API (in seconds).

Default: ```3```

  </dd>
  <dt>allow_logging_basic_config</dt>
  <dd>When True, ```logging.basicConfig()``` will be called to set up the logging system. Set to False to skip this call. If using Flask, you'll want to set to ```False```. If using Pyramid or Django, ```True``` should be fine.

Default: ```True```

  </dd>
  </dl>


## Help / Support

If you run into any issues, please email us at [support@rollbar.com](mailto:support@rollbar.com)

You can also find us in IRC: [#rollbar on chat.freenode.net](irc://chat.freenode.net/rollbar)

For bug reports, please [open an issue on GitHub](https://github.com/rollbar/pyrollbar/issues/new).


## Contributing

1. Fork it
2. Create your feature branch (```git checkout -b my-new-feature```).
3. Commit your changes (```git commit -am 'Added some feature'```)
4. Push to the branch (```git push origin my-new-feature```)
5. Create new Pull Request

Tests are in `rollbar/test`. To run the tests: `python setup.py test`
