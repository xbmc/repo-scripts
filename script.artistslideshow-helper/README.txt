Artist Slideshow Helper provides a list artist names matched to their hash directory in your Artist Slideshow image directory to make things a little easier to manage.  It also allows you to migrate images out of the cache directory into a local directory structure.

AS Helper has no GUI, but it will give you some feedback via XBMC notifications.

You MUST go into the settings and set some options or the script won't do anything but complain that you haven't set any options.

Options to set:
---Create artist hash mapping file (boolean: default false)
This tells the script whether or not to generate a file that lists all artists in alphabetical order with the name of the hash directory Artist Slideshow generates.  You can use this if all you want to do is know in what directory to look for a specific artist's information.
---Output directory (folder path: default blank)
The directory in which the file will be placed.

---Migrate images ((boolean: default false)
This tells the script to migrate images from the Artist Slideshow cache directory to somewhere else.
---Output directory (folder path: default blank)
The directory to which the files will be migrated.
---Migration Type (list: default TEST)
There are three types of migrations.
1- Test
This generates a text file in the output directory that shows you everything that would have been moved.
2- Copy
This copies the files from the Artist Slideshow cache to the output directory.  The originals are left in place.  Please note that if there is a file with the same name in the source and destination directory, the source file will overwrite the destination.  Given that the source files are all hashed names, that shouldn't happen, but you have been warned.
3- Move
This moves the files from the Artist Slideshow cache to the output directory.  The originals are deleted after they are moved.  In some cases the Artist Slideshow cache directories can't be deleted, but at least all the files are deleted.  Please note that if there is a file with the same name in the source and destination directory, the source file will overwrite the destination.  Given that the source files are all hashed names, that shouldn't happen, but you have been warned.
