script.colorbox


- Available operations:

  twotone: will grayscale the image then replace black and white with colors of choice (or default grayscale if none supplied)
  
  posterize: will downgrade image to bit level of choice
  
  pixelate: will bulk up pixels to size requested and add black border round each pixel block
  
  distort: will fuzzy spread image using two deltas, x & y.
  
  blur: will return a guassian blurred image dependant on radius supplied, larger radius means larger blur + color match
  
  bluronly: will return a guassian blurred image dependant on radius supplied, larger radius means larger blur - no color match
  
  randomcolor: will return a random color

  daemon for lisitem fanart, to ignore in viewmodes set window property true (see below)

  daemon for music player fanart


- Notes:

  On start up you will need to check and make addon cache dir. For this to happen please add this to top of Startup.xml for example, on a button or anywhere it can be run from to start before colorbox is needed.

	RunScript(script.colorbox,info=firstrun)


- Usage:

  RunScript(script.colorbox,info=twotone,id='"IMAGE_TO_USE"',black='"1ST_COLOR"',white='"2ND_COLOR"',prefix=RETURN_IMAGE_ID)

  RunScript(script.colorbox,info=posterize,id='"IMAGE_TO_USE"',bits=BIT_SIZE,prefix=RETURN_IMAGE_ID)

  RunScript(script.colorbox,info=pixelate,id='"IMAGE_TO_USE"',pixels=PIXELATION_SIZE,prefix=RETURN_IMAGE_ID)
  
  RunScript(script.colorbox,info=distort,id='"IMAGE_TO_USE"',delta_x=DELTA_X,delta_y=DELTA_Y,prefix=RETURN_IMAGE_ID)

  RunScript(script.colorbox,info=blur,id='"IMAGE_TO_USE"',radius=RADIUS_SIZE,prefix=RETURN_IMAGE_ID)

  RunScript(script.colorbox,info=bluronly,id='"IMAGE_TO_USE"',radius=RADIUS_SIZE,prefix=RETURN_IMAGE_ID)

  RunScript(script.colorbox,info=randomcolor,prefix=RETURN_IMAGE_ID)


- Vars:

  IMAGE_TO_USE        Image to be manipulated

  RETURN_IMAGE_ID     Image returned will be available as a window property (see below)

  1ST_COLOR           Color to replace the black pixels in format #000000

  2ND_COLOR           Color to replace the white pixels in format #000000

  BIT_SIZE            1,2,3,4,5,6,7,8

  PIXELATION_SIZE     1-infinity, though 1 will return a 1:1 copy!

  RADIUS_SIZE         The larger the more blurred the returned image
  
  DELTA_X/Y           Lower the delta for high distortion, higher delta for low distortion


- Window properties:

  Window(home).Property(RETURN_IMAGE_ID.Image)
  
  Window(home).Property(RETURN_IMAGE_ID.ImageColor) <- only available with 'blur' and 'randomcolor'

  Window(home).Property(RETURN_IMAGE_ID.ImageUpdating) <- this will be set to '1' when all operations are finished and image is ready. It will be set to '0' whle image is being rendered.
  
  Window(home).Property(ImageColor1|2|3) <- available when music playing, 1 is color from art other two are random
  
  Window(home).Property(ImageFilter1|2|3) <- available when music playing, 1 is blur, 2 pixel, 3 posterize
  
  Window(home).Property(ImageColorfa1|2|3) <- available when music playing, 1 is color from art other two are random
  
  Window(home).Property(ImageFilterfa1|2|3) <- available when music playing, 1 is blur, 2 pixel, 3 posterize
  
  Window(home).Property(ImageColorcfa1|2|3|4) <- available current list item fanart, 1 is color from art other three are random
  
  Window(home).Property(ImageFiltercfa1|2|3|4) <- available current list item fanart, 1 is blur, 2 pixel, 3 posterize & 4 distort

  Window(home).Property(cfa_ignore_set) <- set True for daemon to ignore listitem fanart (remember to clear if needed!)
  
  
- Daemon:

  In say startup.xml use below code to start daemon (pixels etc will default if not set). This will process 'Player.Art(thumb)', 'MusicPlayer.Property(Fanart_Image)' & current 'Listitem.Fanart'. See above 'cfa_ignore_set' to disable the current fanart option.

  RunScript(script.colorbox,daemon=True,pixels=20,bits=2,radius=10,delta_x=40,delta_y=90)

  To speed up daemon and not to process all types off effects, use:
  
  SetProperty(cfa_daemon_set,Blur,home)
  
  SetProperty(cfa_daemon_set,Pixelate,home)
  
  SetProperty(cfa_daemon_set,Posterize,home)
  
  SetProperty(cfa_daemon_set,Distort,home)
  
  This MUST be used as of now.
  NONE will be processed if not set.
  Next version will default to ALL being processed if not set!
