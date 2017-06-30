# script.module.simplecache
A simple object cache for Kodi addons


## Usage

You can use this python library as module within your own Kodi scripts/addons.
Just make sure to import it within your addon.xml:

```xml
<requires>
    <import addon="script.module.simplecache" version="1.0.0" />
</requires>
```

Now, to use it in your Kodi addon/script, make sure to import it and you can access it's methods.

```
import simplecache

#get data from cache
mycache = simplecache.get("MyAddon.MyChunkOfData")
if mycache:
    my_objects = mycache
else:
    #do stuff here
    my_objects = mymethod()
    
    #write results in cache
    simplecache.set( "MyAddon.MyChunkOfData", my_objects, expiration=datetime.timedelta(hours=12))
```

The above example will check the cache for the key "MyAddon.MyChunkOfData". If there is any data (and the cache is not expired) it will be returned as the original object.

If the cache is empty, you perform the usual stuff to get the data and save that to the cache

---------------------------------------------------------------------------

## Available methods

###get( endpoint, checksum="")
```
    Returns the data from the cache for the specified endpoint. Will return None if there is no cache.
    
    parameters:
    endpoint --> Your unique reference/key for the cache object. TIP: To prevent clashes with other addons, prefix with your addon ID.
    checksum --> Optional argument to check for a checksum in the file (Will only work if you store the checksum with the set method). Can be any python object which can be serialized with eval.
    
    
    Example: simplecache.get("MyAddon.MyChunkOfData", checksum=len(myvideos))
    
    This example will return the data in the cache but only if the length of the list myvideos is the same as whatever is stored as checksum in the cache.
    
```

###set( endpoint, data, checksum="", expiration=timedelta(days=30))
```
    Stores the data in the cache for the specified endpoint.
    
    parameters:
    endpoint --> Your unique reference/key for the cache object. TIP: To prevent clashes with other addons, prefix with your addon ID.
    data --> Your objectdata. Can be any python object which can be serialized with eval.
    checksum --> Optional argument to store as checksum in the file. Can be any python object which can be serialized with eval.
    expiration --> Optional argument to specify the amount of time the data may be cached as python timedelta object. Defaults to 30 days if ommitted.
    
    Example: simplecache.set("MyAddon.MyGreatChunkOfData", my_objects, checksum=len(myvideos), expiration=timedelta(hours=1))
    
    This example will store the data in the cache which will expire after 1 hours. Additionally a checksum is stored in the cache object.
    
```

## Notes

1) By default objects will be stored both in memory and on disk, it is however possible to override that:
```
    simplecache.use_memory_cache = False
```
In that case, objects will only be stored on disk (database)


2) Cache objects are auto cleaned from memory after 2 hours to prevent unused objects loaded in memory.


3) Cache objects on disk are stored in a self-maintaining sqllite database. Expired objects will be auto cleaned from the database.

