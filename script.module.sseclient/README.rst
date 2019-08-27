=================
Python SSE Client
=================

This is a Python client library for iterating over http Server Sent Event (SSE)
streams (also known as EventSource, after the name of the Javascript interface
inside browsers).  The SSEClient class accepts a url on init, and is then an
iterator over messages coming from the server.

Installation
------------

Use pip::

    pip install sseclient

Usage
-----

::

    from sseclient import SSEClient

    messages = SSEClient('http://mysite.com/sse_stream/')
    for msg in messages:
        do_something_useful(msg)

Each message object will have a 'data' attribute, as well as optional 'event',
'id', and 'retry' attributes.

Optional init parameters:

- last_id: If provided, this parameter will be sent to the server to tell it to
  return only messages more recent than this ID.

- retry: Number of milliseconds to wait after disconnects before attempting to
  reconnect.  The server may change this by including a 'retry' line in a
  message.  Retries are handled automatically by the SSEClient object.

You may also provide any additional keyword arguments supported by the
Requests_ library, such as a 'headers' dict and a (username, password) tuple
for 'auth'.

Development
-----------

Install the library in editable mode::

    pip install -e .

Install the test dependencies::

    pip install pytest backports.unittest_mock

Run the tests with py.test::

    (sseclient)vagrant sseclient $ py.test
    ===================== test session starts ======================
    platform linux2 -- Python 2.7.6 -- py-1.4.30 -- pytest-2.7.2
    rootdir: /vagrant/code/sseclient, inifile: 
    plugins: backports.unittest-mock
    collected 11 items 

    test_sseclient.py ...........

    ================== 11 passed in 0.19 seconds ===================

There are a couple TODO items in the code for getting the implementation
completely in line with the finer points of the SSE spec.

Additional Resources
--------------------

- `HTML5Rocks Tutorial`_
- `Official SSE Spec`_

.. _Requests: http://docs.python-requests.org/en/latest/
.. _HTML5Rocks Tutorial: https://www.html5rocks.com/en/tutorials/eventsource/basics/
.. _Official SSE Spec: https://html.spec.whatwg.org/multipage/comms.html#server-sent-events

