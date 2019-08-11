# script.module.cache

![foo](resources/icon.png)

Simple Python HTTP Cache using sqlite3

*   Stores cached data in sqlite3.Blobs.
*   Calculates lifetime, freshness as virtual columns.
*   Obeys cache control directives, immutable, no-store, etc.
*   Supports etag, last_modified, etc for conditional requests.
*   Can be used as a generic key/blob data store when used without directives.

By default the Cache (and Store) use a sqlite3 database named "cache.sqlite" located in the add-on profile directory

## Examples

Quick examples of basic usage 

## Request cache

How to use the Cache class with requests

The Cache class allows you to easily store URIs, as keys, along with their response data and headers in a persistent database.

The calculated column "fresh" and the "conditional_headers" method can be used to limit the number of requests made
and the amount of data transferred respectively.
 
~~~~python
import requests
from cache import Cache, conditional_headers
 
  
def get_html(uri):
    # type: (str) -> Union[str, None]
    headers = {
        "Accept": "text/html",
        "Accept-encoding": "gzip"
    }
    with Cache() as c:
        # check if uri is cached
        cached = c.get(uri)
        if cached:
            # if the data is fresh then simply return it
            if cached["fresh"]:
                return cached["blob"]
            # otherwise append applicable "If-None-Match"/"If-Modified-Since" headers
            headers.update(conditional_headers(cached))
        # request a new version of the data
        r = requests.get(uri, headers=headers, timeout=60)
        if 200 == r.status_code:
            # add the new data and headers to the cache 
            c.set(uri, r.content, r.headers)
            return r.content
        if 304 == r.status_code:
            # the data hasn't been modified so just touch the cache with the new headers
            # and return the existing data
            c.touch(uri, r.headers)
            return cached["blob"]
        # perhaps log any other status codes for debugging
        return None
 
~~~~

## Generic string storage

Generic string storage is facilitated by the Store class.

The Store class allows a "key" to be used to append to, remove from or retrieve a set of unique string values.

This is useful for saving things like; a history of searched terms, urls of played films, etc.

~~~~python
from cache import Store
 
 
# key can be anything, app:// prefix isn't required
# the only requirement is that the key be unique with in your add-on
searches = Store("app://user-searches") 
 
# add strings to the store
searches.append("foo")
searches.append("bar")
searches.append("bat")
print(searches.retrieve())  # {'bar', 'bat', 'foo'}
 
# remove a string from the store
searches.remove("bar")  
print(searches.retrieve())  # {'bat', 'foo'}
  
# clear the store
searches.clear()
print(searches.retrieve())  # set()
 
~~~~

## References 

*   [DB-API 2.0 interface for SQLite databases](https://docs.python.org/2/library/sqlite3.html)
*   [RFC7234 - HTTP/1.1 Caching](https://tools.ietf.org/html/rfc7234)
*   [RFC7232 - HTTP/1.1 Conditional Requests](https://tools.ietf.org/html/rfc7232)

[![Codacy Badge](https://api.codacy.com/project/badge/Grade/26afc2828d1e439eafd563967a391f5b)](https://www.codacy.com/app/FraserChapman/script.module.cache?utm_source=github.com&amp;utm_medium=referral&amp;utm_content=FraserChapman/script.module.cache&amp;utm_campaign=Badge_Grade)
