# script.module.metahandler
Fork of Eldorado's script.module.metahandler

# Developers
  Import this module and include your own themoviedb.org API key from within your addon.
  
  ```
  from metahandler import metahandlers 
  metaget = metahandlers.MetaData(preparezip=False, tmdb_api_key=YOURKEY)
  ```
 
# End Users
  Enter your own themoviedb.org API key from within the module's settings and enable the "Override TMDB keys from all addons" option.
