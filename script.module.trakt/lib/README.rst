trakt.py
========

.. image:: https://img.shields.io/pypi/v/trakt.py.svg?style=flat-square
   :target: https://pypi.python.org/pypi/trakt.py

.. image:: https://img.shields.io/travis/fuzeman/trakt.py.svg?style=flat-square
   :target: https://travis-ci.org/fuzeman/trakt.py

.. image:: https://img.shields.io/codeclimate/github/fuzeman/trakt.py.svg?style=flat-square
   :target: https://codeclimate.com/github/fuzeman/trakt.py

.. image:: https://img.shields.io/coveralls/fuzeman/trakt.py.svg?style=flat-square
   :target: https://coveralls.io/r/fuzeman/trakt.py?branch=master

Python interface for the Trakt.tv API.

Install
-------

.. code-block:: shell

    pip install trakt.py

Examples
--------

**Configure the client**

.. code-block:: python

    from trakt import Trakt


    Trakt.configuration.defaults.client(
        id='<client-id>',
        secret='<client-secret>'
    )


**Scrobble an episode**

.. code-block:: python

    show = {
        'title': 'Community',
        'year': 2009
    }

    episode = {
        'season': 5,
        'number': 13
    }

    # Send "start" event
    Trakt['scrobble'].start(
        show=show,
        episode=episode,

        progress=1
    )

    # [...] (watching episode)

    # Send "stop" event (scrobble)
    Trakt['scrobble'].stop(
        show=show,
        episode=episode,

        progress=93
    )

**Add a movie to your collection**

.. code-block:: python

    Trakt['sync/collection'].add({
        'movies': [
            {
                'title': "Twelve Monkeys",
                'year': 1995,

                'ids': {
                    'imdb': "tt0114746"
                }
            }
        ]
    })

**Retrieve shows that a user has watched**

.. code-block:: python

    # `watched` = {<key>: <Show>} dictionary
    watched = Trakt['sync/watched'].movies()

    for key, show in watched.items():
        print '%s (%s)' % (show.title, show.year)

License
-------

  The MIT License (MIT)

  Copyright (c) 2014 Dean Gardiner

  Permission is hereby granted, free of charge, to any person obtaining a copy
  of this software and associated documentation files (the "Software"), to deal
  in the Software without restriction, including without limitation the rights
  to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
  copies of the Software, and to permit persons to whom the Software is
  furnished to do so, subject to the following conditions:

  The above copyright notice and this permission notice shall be included in
  all copies or substantial portions of the Software.

  THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
  IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
  FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
  AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
  LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
  OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
  THE SOFTWARE.
