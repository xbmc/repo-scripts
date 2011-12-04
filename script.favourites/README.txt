How to use this addon in your skin:

The script has two modes:

1) RunScript(script.favourites,[playlists=play])

This will set your favourites as properties on the window you run the script. Each favourite will be accessible via

Window(id).property(favourite.%d.*):
name             (favourite name)
thumb            (favourite icon)
path             (favourite path)

If you specify the optional playlists attribute, playlists will play instead of open


2) RunScript(script.favourites,property=CustomFavourite.1)

If you run the script like this, it will open a select dialog with all existing favourites. After selecting one,
the script will set the following strings based on the provided property:

CustomFavourite.1.Label
CustomFavourite.1.Icon
CustomFavourite.1.Path

NOTE: playlists attribute has no effect when property is specified. The script will ask if a playlist should play.