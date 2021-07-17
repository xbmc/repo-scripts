# Qhue change log

By its very nature, the core of Qhue doesn't change very much!  Most recent updates are primarily about documentation.

## 1.0.12 - 2019-01-04

* No functional changes, just packaging tweaks to include the README as the package description.

## 1.0.11 - 2019-01-04

* If keyword argument names end with an underscore, it is removed before sending to the Bridge.  This means you can use, for example, 'class_', and not clash with Python keywords. 

## 1.0.10 - 2018-11-15

* Add the object_pairs_hook option to the Bridge constructor.  This controls how JSON structures returned by the API are converted into Python, so you can use OrderedDicts instead of dicts if you want to preserve the (generally logical) ordering used by the bridge. (This does make dumping the structures as YAML more messy, though.)

## 1.0.9 - 2017-12-10

* Demonstration notebook is more Python3-compatible.
* qhue_example.py will run under Python 2 or 3.
* create_new_username now takes note of devicetype argument if specified.

## 1.0.8 - 2017-06-05

* Creation of the short_address attribute would fail when a username was not yet assigned.  Fixed.

## 1.0.7 - 2017-05-14

* README tweaks
* Example Jupyter notebook has python3-type print statements and tidier example output.

## 1.0.6 - 2017-05-14

* README updates
* Addition of short_address attribute

## 1.0.5 - 2016-11-16 

* Updates to documentation
* Inclusion of an example iPython Notebook



