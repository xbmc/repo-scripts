# script.module.musicbrainz
Kodi module library for the Python bindings for Musicbrainz' NGS webservice developed by alastair

Usage:

You can use this python library as module within your own Kodi scripts/addons.
Just make sure to import it within your addon.xml:

```xml
<requires>
    <import addon="script.module.musicbrainz" version="0.0.1" />
</requires>
```

Now, to use it in your Kodi addon/script, make sure to import it and you can access it's methods:

```
# Import the module
import musicbrainzngs

# If you plan to submit data, authenticate
musicbrainzngs.auth("user", "password")

# Tell musicbrainz what your app is, and how to contact you
# (this step is required, as per the webservice access rules
# at http://wiki.musicbrainz.org/XML_Web_Service/Rate_Limiting )
musicbrainzngs.set_useragent("Example music app", "0.1", "http://example.com/music")

# If you are connecting to a different server
musicbrainzngs.set_hostname("beta.musicbrainz.org")
```

For the complete reference see the original project:

https://github.com/alastair/python-musicbrainzngs

and the complete README:

https://python-musicbrainzngs.readthedocs.io/en/v0.6/