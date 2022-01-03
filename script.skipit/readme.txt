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

2/ This addon needs to be bound to a key to launch its functionality while watching a video. Typically this is the "Right Arrow" key 
   on your keyboard or remote control.
   * Use the Keymap Editor plugin to bind the "Right Arrow" key to this addon in Fullscreen Video and Fullscreen Live TV Windows
   --->  Addon 
      ---> Keymap Editor
         ---> Edit
            ---> Window - Fullscreen Video   (repeat for Fullscreen Live TV)
               ---> Category - Add-ons
                  ---> Action - Launch SkipIt
                     ---> Edit 
                        ---> Press the 'Right Arrow' key when prompted or the right arrow on the remote control
    --- Cancel your way back through the screens, remembering to save as the final step.
    
=============
Configuration
=============

Via the standard KODI add-on configuration, you can configure:
  * The number of seconds initially skipped
  * The timeout, after which if no key is pressed the add-on terminates. It will restart when needed next time.
  * Drift correction seconds. A small adjustment factor to make up for the time the user takes to make the next action.
    If you find, you can't quite return to the exact position in the video, you might adjust this setting.        


