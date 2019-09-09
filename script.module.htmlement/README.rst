.. image:: https://badge.fury.io/py/htmlement.svg
    :target: https://pypi.python.org/pypi/htmlement

.. image:: https://readthedocs.org/projects/python-htmlement/badge/?version=stable
    :target: http://python-htmlement.readthedocs.io/en/stable/?badge=stable

.. image:: https://travis-ci.org/willforde/python-htmlement.svg?branch=master
    :target: https://travis-ci.org/willforde/python-htmlement

.. image:: https://coveralls.io/repos/github/willforde/python-htmlement/badge.svg?branch=master
    :target: https://coveralls.io/github/willforde/python-htmlement?branch=master

.. image:: https://api.codacy.com/project/badge/Grade/6b46406e1aa24b95947b3da6c09a4ab5
    :target: https://www.codacy.com/app/willforde/python-htmlement?utm_source=github.com&amp;utm_medium=referral&amp;utm_content=willforde/python-htmlement&amp;utm_campaign=Badge_Grade

.. image:: https://img.shields.io/pypi/pyversions/htmlement.svg
    :target: https://pypi.python.org/pypi/htmlement

.. image:: https://img.shields.io/badge/Say%20Thanks-!-1EAEDB.svg
    :target: https://saythanks.io/to/willforde

HTMLement
---------

HTMLement is a pure Python HTML Parser.

The object of this project is to be a "pure-python HTML parser" which is also "faster" than "beautifulsoup".
And like "beautifulsoup", will also parse invalid html.

The most simple way to do this is to use ElementTree `XPath expressions`__.
Python does support a simple (read limited) XPath engine inside its "ElementTree" module.
A benefit of using "ElementTree" is that it can use a "C implementation" whenever available.

This "HTML Parser" extends `html.parser.HTMLParser`_ to build a tree of `ElementTree.Element`_ instances.

Install
-------
Run ::

    pip install htmlement

-or- ::

    pip install git+https://github.com/willforde/python-htmlement.git

Parsing HTML
------------
Here I’ll be using a sample "HTML document" that will be "parsed" using "htmlement": ::

    html = """
    <html>
      <head>
        <title>GitHub</title>
      </head>
      <body>
        <a href="https://github.com/marmelo">GitHub</a>
        <a href="https://github.com/marmelo/python-htmlparser">GitHub Project</a>
      </body>
    </html>
    """

    # Parse the document
    import htmlement
    root = htmlement.fromstring(html)

Root is an ElementTree.Element_ and supports the ElementTree API
with XPath expressions. With this I'm easily able to get both the title and all anchors in the document. ::

    # Get title
    title = root.find("head/title").text
    print("Parsing: %s" % title)

    # Get all anchors
    for a in root.iterfind(".//a"):
        print(a.get("href"))

And the output is as follows: ::

    Parsing: GitHub
    https://github.com/willforde
    https://github.com/willforde/python-htmlement


Parsing HTML with a filter
--------------------------
Here I’ll be using a slightly more complex "HTML document" that will be "parsed" using "htmlement with a filter" to fetch
only the menu items. This can be very useful when dealing with large "HTML documents" since it can be a lot faster to
only "parse the required section" and to ignore everything else. ::

    html = """
    <html>
      <head>
        <title>Coffee shop</title>
      </head>
      <body>
        <ul class="menu">
          <li>Coffee</li>
          <li>Tea</li>
          <li>Milk</li>
        </ul>
        <ul class="extras">
          <li>Sugar</li>
          <li>Cream</li>
        </ul>
      </body>
    </html>
    """

    # Parse the document
    import htmlement
    root = htmlement.fromstring(html, "ul", attrs={"class": "menu"})

In this case I'm not unable to get the title, since all elements outside the filter were ignored.
But this allows me to be able to extract all "list_item elements" within the menu list and nothing else. ::

    # Get all listitems
    for item in root.iterfind(".//li"):
        # Get text from listitem
        print(item.text)

And the output is as follows: ::

    Coffee
    Tea
    Milk

.. _html.parser.HTMLParser: https://docs.python.org/3.6/library/html.parser.html#html.parser.HTMLParser
.. _ElementTree.Element: https://docs.python.org/3.6/library/xml.etree.elementtree.html#xml.etree.ElementTree.Element
.. _Xpath: https://docs.python.org/3.6/library/xml.etree.elementtree.html#xpath-support
__ XPath_
