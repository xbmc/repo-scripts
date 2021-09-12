# script.module.utils
Helper module for Kodi development.

Imports a number of common dependencies and provides useful utilities for performing
frequently used operations.

Written by Philipp Temminghoff (phil65) (https://github.com/phil65/script.module.kodi65).

Scott967 (https://github.com/scott967/script.module.kodi65) Finished
migration to Python 3 and added api_key argument to youtube calls.

Maintenance assumed by Frank Feuerbacher (https://github.com/fbacher/script.module.kutils)
Updated Dependencies and renamed add-on to conform with Kodi naming rules.

Changes:
1.3.0
Hard-coded Youtube API key eliminated. Add-ons must supply their own api-key as
an argument. Impacts youtube.py

Fixed issues identified during addon review, particularly changes required by
Kodi API changes (including renaming addon). Also renamed imported lib to 
match new addon name. Also changed several file names to be all lower case
(kodi standard).

Resolved issue with Kodi crashing due to a numpy limitation: numpy can only 
be initialized once in a sub-interpreter environment. Resolved by forcing
numpy to NOT be loaded, even if present. Kutils had a soft dependency on
numpy.
