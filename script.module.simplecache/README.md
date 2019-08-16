# script.module.simplecache

[![Codacy Badge](https://api.codacy.com/project/badge/Grade/5e223503667f4a35a791d140f2cb6285)](https://www.codacy.com/app/m-vanderveldt/script-module-simplecache?utm_source=github.com&utm_medium=referral&utm_content=marcelveldt/script.module.simplecache&utm_campaign=badger)

A simple object cache for Kodi addons


## Help needed with maintaining !
I am very busy currently so I do not have a lot of time to work on this project or watch the forums.
Be aware that this is a community driven project, so feel free to submit PR's yourself to improve the code and/or help others with support on the forums etc. If you're willing to really participate in the development, please contact me so I can give you write access to the repo. I do my best to maintain the project every once in a while, when I have some spare time left.
Thanks for understanding!


## Usage

You can use this python library as module within your own Kodi scripts/addons.
Just make sure to import it within your addon.xml:

```xml
<requires>
    <import addon="script.module.simplecache" version="1.0.14" />
</requires>
```

Now, to use it in your Kodi addon/script, make sure to import it and you can access its methods.

```python
import simplecache

# instantiate the cache
_cache = simplecache.SimpleCache()

# get data from cache
mycache = _cache.get("MyAddon.MyChunkOfData")
if mycache:
    my_objects = mycache
else:
    # do stuff here
    my_objects = mymethod()

    # write results in cache
    _cache.set( "MyAddon.MyChunkOfData", my_objects, expiration=datetime.timedelta(hours=12))
```

The above example will check the cache for the key "MyAddon.MyChunkOfData". If there is any data (and the cache is not expired) it will be returned as the original object.

If the cache is empty, you perform the usual stuff to get the data and save that to the cache

---------------------------------------------------------------------------

## Available methods

### get(endpoint, checksum="")
```
    Returns the data from the cache for the specified endpoint. Will return None if there is no cache.

    parameters:
    endpoint --> Your unique reference/key for the cache object. TIP: To prevent clashes with other addons, prefix with your addon ID.
    checksum --> Optional argument to check for a checksum in the file (Will only work if you store the checksum with the set method). Can be any python object which can be serialized with eval.


    Example: _cache.get("MyAddon.MyChunkOfData", checksum=len(myvideos))

    This example will return the data in the cache but only if the length of the list myvideos is the same as whatever is stored as checksum in the cache.

```

### set(endpoint, data, checksum="", expiration=timedelta(days=30))
```
    Stores the data in the cache for the specified endpoint.

    parameters:
    endpoint --> Your unique reference/key for the cache object. TIP: To prevent clashes with other addons, prefix with your addon ID.
    data --> Your objectdata. Can be any python object which can be serialized with eval.
    checksum --> Optional argument to store as checksum in the file. Can be any python object which can be serialized with eval.
    expiration --> Optional argument to specify the amount of time the data may be cached as python timedelta object. Defaults to 30 days if ommitted.

    Example: _cache.set("MyAddon.MyGreatChunkOfData", my_objects, checksum=len(myvideos), expiration=timedelta(hours=1))

    This example will store the data in the cache which will expire after 1 hours. Additionally a checksum is stored in the cache object.

```

## Notes

1) By default objects will be stored both in memory and on disk, it is however possible to override that:
```
    _cache.enable_mem_cache = False
```
In that case, objects will only be stored on disk (database)


2) Cache objects are auto cleaned from memory after 2 hours to prevent unused objects loaded in memory.


3) Cache objects on disk are stored in a self-maintaining sqllite database. Expired objects will be auto cleaned from the database.
