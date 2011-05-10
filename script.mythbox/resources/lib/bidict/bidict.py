#!/usr/bin/env python

# Copyright (c) 2009 Josh Bronson and contributors
# 
# Permission is hereby granted, free of charge, to any person
# obtaining a copy of this software and associated documentation
# files (the "Software"), to deal in the Software without
# restriction, including without limitation the rights to use,
# copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the
# Software is furnished to do so, subject to the following
# conditions:
# 
# The above copyright notice and this permission notice shall be
# included in all copies or substantial portions of the Software.
# 
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
# EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES
# OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND
# NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT
# HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY,
# WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING
# FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR
# OTHER DEALINGS IN THE SOFTWARE.

"""
--------
Overview
--------

``bidict`` provides a bidirectional mapping data structure and related
utilities (``namedbidict``, ``inverted``) to naturally model one-to-one
relations in Python. To keep the learning curve low, it introduces no new
functions to the ``dict`` API you're already familiar with. It owes its
simplicity to Python's slice syntax, which provides a handy and natural way
of expressing the inverse mapping in a ``bidict``::
    
    >>> husbands2wives = bidict({'john': 'jackie'})
    >>> husbands2wives['john'] # the forward mapping is just like with dict
    'jackie'
    >>> husbands2wives[:'jackie'] # use slice for the inverse mapping
    'john'

You can also use the unary inverse operator ``~`` on a bidict to get the
inverse mapping::

    >>> ~husbands2wives
    bidict({'jackie': 'john'})


--------------------------
Motivation & More Examples
--------------------------

Python's built-in ``dict`` lets us associate unique keys with arbitrary values.
Because keys must be hashable, values can be looked up by key in constant time.
Different keys can map to the same value, but a single key cannot map to two
different values. For instance, ``{-1: 1, 0: 0, 1: 1}`` is a ``dict`` with
three unique keys and two unique values, because the keys -1 and 1 both map to
1. If you try to write its inverse ``{1: -1, 0: 0, 1: 1}``, the ``dict`` that
comes out has only two mappings, one for key 1 and one for key 0; since key 1
is not allowed to map to both -1 and 1, one of these mappings is discarded.

Sometimes the relation we're modeling will only ever have a single key mapping
to a single value, as in the relation of husbands to wives (assuming monogamy).
This is called a one-to-one (or injective) mapping (see
http://en.wikipedia.org/wiki/Injective_mapping).

In this case we can be sure that the inverse mapping has the same number of
items as the forward mapping, and moreover that if key k maps to value v in the
forward mapping, value v maps to key k in the inverse. It would be useful then
to be able to look up keys by value in constant time in addition to being able
to look up values by key. With the additional constraint that values must be
hashable as well as keys, just such a bidirectional dictionary is possible:
enter ``bidict``.

``bidict`` provides a bidirectional mapping data structure which offers
constant-time forward and inverse lookups in a syntax which builds naturally
on what we're already used to from regular dicts. Consider the following
one-to-one mapping::

    >>> h2w = bidict({'bill': 'hillary', 'barack': 'michelle'})

To look up a wife by husband, use the familiar subscript syntax as with a dict::

    >>> h2w['bill']
    'hillary'

Or, by analogy to array slicing, you can optionally provide a trailing colon to
emphasize that you're talking about a forward mapping::

    >>> h2w['bill':]
    'hillary'

And now you can guess how to spell the inverse mapping (i.e. to look up a
husband by wife)::

    >>> h2w[:'hillary']
    'bill'

The slice syntax works for setting and deleting items in either direction too::

    >>> h2w['bill':] = 'melinda'
    >>> h2w[:'cher'] = 'sonny'
    >>> del h2w[:'michelle']

The ``namedbidict`` class factory can be used to create a bidirectional mapping
with customized names for the forward and the inverse mappings accessible via
attributes.

A real-world example can be found in the ``htmlentitydefs`` module, which
maintains a ``name2codepoint`` dict and an inverse ``codepoint2name`` dict
separately. This could instead be modeled with a single ``bidict``::

    >>> HTMLEntities = namedbidict('HTMLEntities', 'names', 'codepoints')
    >>> entities = HTMLEntities({'lt': 60, 'gt': 62, 'amp': 38}) # etc
    >>> entities.names['lt']
    60
    >>> entities.codepoints[38]
    'amp'

See the ``bidict`` class for more examples.

Note: ``bidict`` does not subclass ``dict``, but its API is a superset of the
``dict`` API minus the ``fromkeys`` method, which does not make sense in the
context of an injective mapping. ``bidict`` implements the ``MutableMapping``
interface.

This module also provides an ``inverted`` iterator in the spirit of the built-in
``reversed``. Pass in a mapping to get the inverse mapping, an iterable of pairs
to get the pairs' inverses, or any object implementing an ``__inverted__``
method. See the ``inverted`` class for examples.

Note: "inverse" rather than "reverse" is used because it's the term used in
mathematics and its meaning is more specific, and because "reversed" already
means something different in Python (reversing the order of the items in a
sequence versus inverting the (k, v) pairs in a mapping).

"""

try:
    # HACK: Force odict to be used as bidict's internal delegate to make it ordered
    import odict
    dict = odict.odict
except:
    pass

import re
try:
    from collections import MutableMapping
except:
    # WORKAROUND: MutableMapping not available in Python 2.4
    pass

try:
    from functools import wraps
except:
    # WORKAROUND: functools not available in Python 2.4
    WRAPPER_ASSIGNMENTS = ('__module__', '__name__', '__doc__')
    WRAPPER_UPDATES = ('__dict__',)
    
    def partial(func, *args, **keywords):
            def newfunc(*fargs, **fkeywords):
                newkeywords = keywords.copy()
                newkeywords.update(fkeywords)
                return func(*(args + fargs), **newkeywords)
            newfunc.func = func
            newfunc.args = args
            newfunc.keywords = keywords
            return newfunc    

    def update_wrapper(wrapper,
                       wrapped,
                       assigned = WRAPPER_ASSIGNMENTS,
                       updated = WRAPPER_UPDATES):
        """Update a wrapper function to look like the wrapped function
    
           wrapper is the function to be updated
           wrapped is the original function
           assigned is a tuple naming the attributes assigned directly
           from the wrapped function to the wrapper function (defaults to
           functools.WRAPPER_ASSIGNMENTS)
           updated is a tuple naming the attributes of the wrapper that
           are updated with the corresponding attribute from the wrapped
           function (defaults to functools.WRAPPER_UPDATES)
        """
        for attr in assigned:
            setattr(wrapper, attr, getattr(wrapped, attr))
        for attr in updated:
            getattr(wrapper, attr).update(getattr(wrapped, attr, {}))
        # Return the wrapper so this can be used as a decorator via partial()
        return wrapper
    
    def wraps(wrapped,
              assigned = WRAPPER_ASSIGNMENTS,
              updated = WRAPPER_UPDATES):
        """Decorator factory to apply update_wrapper() to a wrapper function
    
           Returns a decorator that invokes update_wrapper() with the decorated
           function as the wrapper argument and the arguments to wraps() as the
           remaining arguments. Default arguments are as for update_wrapper().
           This is a convenience function to simplify applying partial() to
           update_wrapper().
        """
        return partial(update_wrapper, wrapped=wrapped,
                       assigned=assigned, updated=updated)
        

class inverted(object):
    """
    An iterator in the spirit of ``reversed``. Useful for inverting a mapping::

        >>> keys = (1, 2, 3)
        >>> vals = ('one', 'two', 'three')
        >>> fwd = dict(zip(keys, vals))
        >>> inv = dict(inverted(fwd))
        >>> inv == dict(zip(vals, keys))
        True

    Passing an iterable of pairs produces an iterable of the pairs' inverses::
        
        >>> seq = [(1, 'one'), (2, 'two'), (3, 'three')]
        >>> list(inverted(seq))
        [('one', 1), ('two', 2), ('three', 3)]

    Under the covers, ``inverted`` first tries to call ``__inverted__`` on the
    wrapped object and returns an iterator over the result if the call
    succeeds. If the call fails, ``inverted`` next tries to call ``items`` on
    the wrapped object, returning the inverses of the resulting pairs if the
    call succeeds. Finally, if the ``items`` call fails, ``inverted`` falls
    back on unpacking pairs from the wrapped object directly.

    This allows for passing an ``inverted`` object back into ``inverted`` to
    to get the original sequence of pairs back out::

        >>> seq == list(inverted(inverted(seq)))
        True

    Be careful with passing the inverse of a non-injective mapping into
    ``dict``; mappings for like values with differing keys will be lost:: 

        >>> squares = {-2: 4, -1: 1, 0: 0, 1: 1, 2: 4}
        >>> len(squares)
        5
        >>> len(dict(inverted(squares)))
        3

    """
    def __init__(self, data):
        self._data = data

    def __iter__(self):
        data = self._data
        try:
            return iter(data.__inverted__())
        except AttributeError:
            return self.__next__() # return next(self) requires python 3

    def __next__(self):
        data = self._data
        try:
            for k, v in data.items():
                yield v, k
        except AttributeError:
            for k, v in data:
                yield v, k


class bidict(object):
    """
    Bidirectional mapping implementing the ``MutableMapping`` interface, with
    additional facilities for retrieving inverse mappings. The API is a
    superset of the ``dict`` API (minus the ``fromkeys`` method, which doesn't
    make sense for a bidirectional mapping because keys *and* values must be
    unique).

    To demonstrate::

        >>> keys = (1, 2, 3)
        >>> vals = ('one', 'two', 'three')
        >>> bi = bidict(zip(keys, vals))
        >>> bi == bidict({1: 'one', 2: 'two', 3: 'three'})
        True
        >>> bidict(inverted(bi)) == bidict(zip(vals, keys))
        True

    You can use standard subscripting syntax with a key to get or set a forward
    mapping::

        >>> bi[2]
        'two'
        >>> bi[2] = 'twain'
        >>> bi[2]
        'twain'
        >>> bi[4]
        Traceback (most recent call last):
            ...
        KeyError: 4

    Or use a slice with only a ``start``::

        >>> bi[2:]
        'twain'
        >>> bi[0:] = 'naught'
        >>> bi[0:]
        'naught'

    Use a slice with only a ``stop`` to get or set an inverse mapping::

        >>> bi[:'one']
        1
        >>> bi[:'aught'] = 1
        >>> bi[:'aught']
        1
        >>> bi[1]
        'aught'
        >>> bi[:'one']
        Traceback (most recent call last):
            ...
        KeyError: 'one'

    Deleting items from the bidict works the same way::

        >>> del bi[0]
        >>> del bi[2:]
        >>> del bi[:'three']
        >>> bi
        bidict({1: 'aught'})

    ``bidict``s maintain references to their inverses via the ``inv`` property,
    which can also be used to access or modify them::

        >>> bi.inv
        bidict({'aught': 1})
        >>> bi.inv['aught']
        1
        >>> bi.inv[:1]
        'aught'
        >>> bi.inv[:1] = 'one'
        >>> bi.inv
        bidict({'one': 1})
        >>> bi
        bidict({1: 'one'})
        >>> bi.inv.inv is bi
        True
        >>> bi.inv.inv.inv is bi.inv
        True

    A ``bidict``'s inverse can also be accessed via the unary ~ operator, by
    analogy to the unary bitwise inverse operator::

        >>> ~bi
        bidict({'one': 1})
        >>> ~bi is bi.inv
        True

    Because ~ binds less tightly than brackets, parentheses are necessary for
    something like::
        
        >>> (~bi)['one']
        1
    
    ``bidict``s work with ``inverted`` as expected::

        >>> biinv = bidict(inverted(bi))
        >>> biinv
        bidict({'one': 1})

    This of course creates a new object (equivalent but not identical)::
        
        >>> biinv == bi.inv
        True
        >>> biinv is bi.inv
        False

    This just demonstrated that ``__eq__`` has been implemented to work as
    expected. ``__neq__`` has too::

        >>> bi != biinv
        True
    
    ``bidict``s should compare as expected to instances of other mapping types::

        >>> bi == dict([(1, 'one')])
        True

    Inverting the inverse should round trip::

        >>> bi == bidict(inverted(inverted(bi)))
        True

    Use ``invert`` to invert the mapping in place::

        >>> bi.invert()
        >>> bi
        bidict({'one': 1})

    The rest of the MutableMapping interface is supported too::

        >>> bi.get('one')
        1
        >>> bi.setdefault('one', 2)
        1
        >>> bi.setdefault('two', 2)
        2
        >>> len(bi) # calls __len__
        2
        >>> bi.pop('one')
        1
        >>> bi.popitem()
        ('two', 2)
        >>> bi.inv.setdefault(3, 'three')
        'three'
        >>> bi
        bidict({'three': 3})
        >>> [key for key in bi] # calls __iter__, returns keys like dict
        ['three']
        >>> 'three' in bi # calls __contains__
        True
        >>> list(bi.keys())
        ['three']
        >>> list(bi.values())
        [3]
        >>> bi.update([('four', 4)])
        >>> bi.update({'five': 5}, six=6, seven=7)
        >>> sorted(bi.items(), key=lambda x: x[1])
        [('three', 3), ('four', 4), ('five', 5), ('six', 6), ('seven', 7)]

    When instantiating or updating a ``bidict``, remember that mappings for
    like values with differing keys will be lost, otherwise the map would not
    be bidirectional::

        >>> nil = bidict({'zero': 0, 'zilch': 0, 'zip': 0})
        >>> len(nil)
        1
        >>> nil.update(nix=0, nada=0)
        >>> len(nil)
        1

    One other gotcha: when mapping the key of one existing mapping to the value
    of another (or vice versa), the two mappings collapse into one::

        >>> b = bidict({1: 'one', 2: 'two'})
        >>> b[1] = 'two'
        >>> b
        bidict({1: 'two'})
        >>> b = bidict({1: 'one', 2: 'two'})
        >>> b[:'two'] = 1
        >>> b
        bidict({1: 'two'})

    """
    def __init__(self, *args, **kwds):
        # using dict and inverted together like this guarantees one-to-one-ness
        # by discarding any non-one-to-one mappings:
        bwd = dict(inverted(dict(*args, **kwds)))
        fwd = dict(inverted(bwd))
        # thanks to Francis Carr for the idea for storing the inverse bidict
        inv = object.__new__(self.__class__)
        inv._fwd = bwd
        inv._bwd = fwd
        inv._inv = self
        self._fwd = fwd
        self._bwd = bwd
        self._inv = inv
    
    def __invert__(self):
        """
        Called when unary ~ operator is applied.
        """
        return self._inv

    inv = property(__invert__)

    def __inverted__(self):
        try:
            return self._bwd.iteritems()
        except AttributeError: # python 3
            return self._bwd.items()

    def __repr__(self):
        return '%s(%r)' % (self.__class__.__name__, self._fwd)
    __str__ = __repr__

    def __eq__(self, other):
        return dict(self) == dict(other)

    def __neq__(self, other):
        return dict(self) != dict(other)

    # thanks to Terry Reedy for the idea for the slice syntax!

    def __getitem__(self, keyorslice):
        try:
            start, stop, step = keyorslice.start, keyorslice.stop, keyorslice.step
        except AttributeError:
            # keyorslice is a key, e.g. b[key]
            return self._fwd[keyorslice]

        # keyorslice is a slice
        if (not ((start is None) ^ (stop is None))) or step is not None:
            raise TypeError('Slice must specify only either start or stop')

        if start is not None: # forward lookup (by key), e.g. b[key:]
            return self._fwd[start]

        # inverse lookup (by val), e.g. b[:val]
        assert stop is not None
        return self._bwd[stop]

    def __delitem__(self, keyorslice):
        def _del(key):
            val = self._fwd[key]
            del self._fwd[key]
            del self._bwd[val]

        try:
            start, stop, step = keyorslice.start, keyorslice.stop, keyorslice.step
        except AttributeError:
            # keyorslice is a key, e.g. del b[key]
            _del(keyorslice)
        else: # keyorslice is a slice
            if (not ((start is None) ^ (stop is None))) or step is not None:
                raise TypeError('Slice must specify only either start or stop')

            if start is not None: # delete by key, e.g. del b[key:]
                _del(start)
                return

            # delete by value, e.g. del b[:val]
            assert stop is not None
            _del(self._bwd[stop])

    def __setitem__(self, keyorslice, keyorval):
        def _set(key, val):
            try:
                oldkey = self._bwd[val]
            except KeyError:
                pass
            else:
                del self._fwd[oldkey]
            try:
                oldval = self._fwd[key]
            except KeyError:
                pass
            else:
                del self._bwd[oldval]
            self._fwd[key] = val
            self._bwd[val] = key

        try:
            start, stop, step = keyorslice.start, keyorslice.stop, keyorslice.step
        except AttributeError:
            # keyorslice is a key, keyorval is a val, e.g. b[key] = val
            _set(keyorslice, keyorval)
        else: # keyorslice is a slice
            if (not ((start is None) ^ (stop is None))) or step is not None:
                raise TypeError('Slice must specify only either start or stop')

            if start is not None: # start is key, keyorval is val, e.g. b[key:] = val
                _set(start, keyorval)
                return

            # keyorval is key, stop is val, e.g. b[:val] = key
            assert stop is not None
            _set(keyorval, stop)

    def clear(self):
        self._fwd.clear()
        self._bwd.clear()

    def copy(self):
        return self.__class__(self._fwd)

    def invert(self):
        self._fwd, self._bwd = self._bwd, self._fwd
        self._inv._fwd, self._inv._bwd = self._inv._bwd, self._inv._fwd

    def pop(self, key, *args):
        val = self._fwd.pop(key, *args)
        del self._bwd[val]
        return val

    def popitem(self):
        if not self._fwd:
            raise KeyError
        key, val = self._fwd.popitem()
        del self._bwd[val]
        return key, val

    def setdefault(self, key, default=None):
        val = self._fwd.setdefault(key, default)
        self._bwd[val] = key
        return val
    
    def update(self, *args, **kwds):
        merged = dict(*args, **kwds)
        merged.update(self._fwd)
        merged = bidict(merged)
        self._fwd = merged._fwd
        self._bwd = merged._bwd

    def _proxied_to_fwd(method):
        """
        Decorator which proxies calls to the given bidict method on to the
        self._fwd dict.
        """
        @wraps(method, ('__name__', '__doc__'))
        def wrapper(self, *args, **kwds):
            return method(self._fwd, *args, **kwds)
        return wrapper

    for methodname in '__contains__ __iter__ __len__ get keys items values'.split():
        locals()[methodname] = _proxied_to_fwd(getattr(dict, methodname))

# BACKPORT: Python 2.4
#MutableMapping.register(bidict)


# thanks to Raymond Hettinger for the idea for namedbidict

_LEGALNAMEPAT = '^[a-zA-Z][a-zA-Z0-9_]*$'
_LEGALNAMERE = re.compile(_LEGALNAMEPAT)

def namedbidict(mapname, fwdname, invname):
    """
    Generate a custom bidict class in the spirit of ``namedtuple`` with
    custom attribute-based access to forward and inverse mappings::

        >>> CoupleMap = namedbidict('CoupleMap', 'husbands', 'wives')
        >>> famous = CoupleMap({'bill': 'hillary'})
        >>> famous.husbands['bill']
        'hillary'
        >>> famous.wives['hillary']
        'bill'
        >>> famous.husbands['barack'] = 'michelle'
        >>> del famous.wives['hillary']
        >>> famous
        CoupleMap({'barack': 'michelle'})
    """
    for name in mapname, fwdname, invname:
        if _LEGALNAMERE.match(name) is None:
            raise ValueError('"%s" does not match pattern %s' %
                (name, _LEGALNAMEPAT))

    class custombidict(bidict):
        locals()[fwdname] = property(lambda self: self)
        locals()[invname] = bidict.inv

    custombidict.__name__ = mapname
    return custombidict

if __name__ == '__main__':
    import doctest
    doctest.testmod(optionflags=doctest.ELLIPSIS)
