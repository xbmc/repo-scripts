**Version 0.1.1 - 2017-09-17**

* Fixed: Typoos
* Changed: pass the sync back-end client to the constructor of the sync_client

**Version 0.1.0 - 2017-09-10**

* Updated: readme.md
* Changed: renamed Selective Sync to Sync Mode
* Updated: readme.md to reflect the Selective Sync changes
* Fixed: logging typoo
* Moved: Add-on settings into own object (makes reloading easier) Added: selective sync feature (Fixes #6)

**Version 0.0.9 - 2017-09-05**

* Added: A bit more logging
* Fixed: don't include deleted files by default when listing content of remote folders
* Added: refactor syncing into separated sync clients (allows adding other back-ends)

**Version 0.0.8 - 2017-09-02**

* Added: DNS kill-switch to stop syncing in case of problems (Fixes #5)
* Added: Version object
* Added: simple DNS query options

**Version 0.0.7 - 2017-08-30**

* Added: display add-on version in log
* Updated: add-on logo
* Fixed: Logging if error occurs before logging initialization

**Version 0.0.6 - 2017-08-27**

* Split add-on Python code from development tools and created a separate repository
* Fixed: some weird dropbox related imports

**Version 0.0.5 - 2017-08-25**

This is the first version in the new repository 

* Renamed add-on: make sure to set all configuration values again!