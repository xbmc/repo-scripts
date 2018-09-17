Changelog
=========

0.5.5
-----
**release date:** 2015-10-31

* Fix hasattr on Country object when called with an invalid attribute

0.5.4
-----
**release date:** 2015-01-24

* Fix setuptools deprecation warning

0.5.3
-----
**release date:** 2014-06-22

* Better equality semantics for Language, Country, Script

0.5.2
-----
**release date:** 2014-05-25

* Babelfish objects (Language, Country, Script) are now picklable
* Added support for Python 3.4


0.5.1
-----
**release date:** 2014-01-26

* Add a register method to ConverterManager to register without loading


0.5.0
-----
**release date:** 2014-01-25

**WARNING:** Backward incompatible changes

* Simplify converter management with ConverterManager class
* Make babelfish usable in place
* Add Python 2.6 / 3.2 compatibility


0.4.0
-----
**release date:** 2013-11-21

**WARNING:** Backward incompatible changes

* Add converter support for Country
* Language/country reverse name detection is now case-insensitive
* Add alpha3t, scope and type converters
* Use lazy loading of converters


0.3.0
-----
**release date:** 2013-11-09

* Add support for scripts
* Improve built-in converters
* Add support for ietf


0.2.1
-----
**release date:** 2013-11-03

* Fix reading of data files


0.2.0
-----
**release date:** 2013-10-31

* Add str method
* More explicit exceptions
* Change repr format to use ascii only


0.1.5
-----
**release date:** 2013-10-21

* Add a fromcode method on Language class
* Add a codes attribute on converters


0.1.4
-----
**release date:** 2013-10-20

* Fix converters not raising NoConversionError


0.1.3
-----
**release date:** 2013-09-29

* Fix source distribution


0.1.2
-----
**release date:** 2013-09-29

* Add missing files to source distribution


0.1.1
-----
**release date:** 2013-09-28

* Fix python3 support


0.1
---
**release date:** 2013-09-28

* Initial version
