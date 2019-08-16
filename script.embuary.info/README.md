# script.embuary.info

Script to provide skinners the option to call The Movie DB for actor and video infos.
Unlike ExtendedInfo it requires a skin integration and it does not include a browser and it only crawls for the most basic and required information.

## Search by string

Some examples
*  ```RunScript(script.embuary.info,call=person,query='"Bruce Willis"')```
*  ```RunScript(script.embuary.info,call=tv,query='"Californication"')```
*  ```RunScript(script.embuary.info,call=movie,query='"Iron Man"')```
*  ```RunScript(script.embuary.info,call=movie,query='"Iron Man"',year=2008)```

`'" "'` is not required, but useful if a string contains special characters. which needs to be escaped.

*Multiple results*
The script provides a selection dialog if multiple results were returned.

## Search by The Movie DB, IMBDb or TVDb ID

*  ```RunScript(script.embuary.info,call=person,tmbd_id=65)```
*  ```RunScript(script.embuary.info,call=tv,tmbd_id=65)```
*  ```RunScript(script.embuary.info,call=tv,external_id=70559)```
*  ```RunScript(script.embuary.info,call=movie,tmbd_id=65)```
*  ```RunScript(script.embuary.info,call=movie,external_id=tt0371746)```

## Options

* An TMDb API key is already shipped but can be replaced in the add-on settings
* To get support for Rotten Tomatoes or IMDb ratings it's required to add a own OMDb key in the settings
* EN is used as default language. It can be changed in the add-on settings, but will still be used if important informations are missing from the result (The Movie DB doesn't have a own fallback logic).
* US is used as default country locale for certifications. Other supported locales can be set in the add-on settings.

## Required windows and reserved IDs
*Important*
* I hate it if a script takes control about the focus. Because of that it's up to the skinner to add a `<defaultcontrol>` tag.
* `ListItem.DBID` is filled if the found item is part of the local library.
* All actions on the control IDs below are controlled by the script.
* The script doesn't set any window property for the called item. You have to call it from the main container. Examples: `$INFO[Container(10051).ListItem.Directors]`, `$INFO[Container(10051).ListItem.Rating]`, `$INFO[Container(10051).ListItem.Art(thumb)]`

*script-embuary-person.xml*
* List control ID `10051` = All available information of the called person.
* List control ID `10052` = All movies starring with actor xyz
* List control ID `10053` = All shows starring with actor xyz
* List control ID `10054` = Actor portraits

*script-embuary-video.xml*
* List control ID `10051` = All available information of the called item.
* List control ID `10052` = Cast
* List control ID `10053` = Similar titles
* List control ID `10054` = YouTube results
* List control ID `10055` = Backdrop images
* List control ID `10056` = Crew

*script-embuary-image.xml*
* List control ID `1` = Is used to display a portrait/backdrop images in fullscreen.
* Scrollbar control ID `2` = Will be the focused on window init.


