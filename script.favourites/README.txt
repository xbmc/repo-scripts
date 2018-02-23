INFO FOR SKINNERS - How to use this addon in your skin:


1) RunScript(script.favourites,property=CustomFavourite.1)

   If you run the script like this, it will open a select dialog with all existing favourites. After selecting one,
   the script will set the following skin strings based on the provided property:

   CustomFavourite.1.Label
   CustomFavourite.1.Icon
   CustomFavourite.1.Path
   CustomFavourite.1.List (the absolute path without the 'Activate.Window()' part)

   Additionally you can pass 'changetitle=true' to the script, this will allow the user to change the name of the label.

   The first item in the list (none) can be used to remove the current favourite from a button.
   The last item in the list (no action) can be used to change the label of a button without asigning an action to it.

2) RunScript(script.favourites)

   If you run the script like this, it will set the following home window properties:
   favourite.%d.path
   favourite.%d.name
   favourite.%d.thumb
   favourite.count

   Additionally you can pass 'playlists=play' to make sure xbmc will play the playlist instead of opening it.
