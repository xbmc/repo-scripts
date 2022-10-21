This is a script plugin to improve add skipping behaviour in Kodi.

This addon borrows ideas originally found in the SkipIt Tap (Topfield Application Program) for the Topfield 5000 series PVR

This addon when launched will skip forward 180 seconds. If 'Forward' is pressed again it will skip forward 
another 180 seconds and continue this way until 'Backward' is pressed, it will then skip back 90 seconds. The next movements 
'Forwards' or 'Backwards' will skip 45 seconds, then 22, 11, 6, 3 seconds. 'Up' and 'Down' will skip 180 seconds forwards or backwards. 

Using this binary seek method it is very quick to accurately bypass the introduction or an ad break.

============
Installation
============

1/ Launch Kodi >> Add-ons >> Get More >> .. >> Install from repository

2/ When installed, this addon binds the 'Right Arrow' key to load the addon when watching a video.
   If you wish to use a different key you can either modify the file .kodi/userdata/keymaps/skipit.xml 
   or
   Remove the content from .kodi/userdata/keymaps/skipit.xml (do not delete the file) 
   and use the keymap editor plugin to define the new key to use. 
    
=============
Configuration
=============

Via the standard KODI add-on configuration, you can configure:
  * The number of seconds initially skipped
  * The timeout, after which if no key is pressed the add-on terminates. It will restart when needed next time.
  * Drift correction seconds. A small adjustment factor to make up for the time the user takes to make the next action.
    If you find, you can't quite return to the exact position in the video, you might adjust this setting.        


