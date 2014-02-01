xbmc-alarm-clock
================

The add-on provides five individual alarms for XBMC playing either a file 
or an URL on repeat.

#Features
  - Up to five individual alarms
  - Scheduling for a week day, every day or Monday to Friday
  - Plays either a file or a custom path may be set which may point to any
      media type supported by XBMC including for example web radio URLs

#Notes
  - If the duration is over, XBMC will stop playing regardless of what is
    being played at the moment. This means a) alarm 1 could disable
    alarm 2 if alarm 2 starts before alarm 1 start time plus duration 1
    is over and b) it may stop something you were playing intentionally
    in the meantime.
  - The overflow over to the next day is not considered. You should make
    sure the start time of any alarm plus its duration is before 0:00.

#Credits
  - Cron-like helper classes CronTab and Event inspired by an answer by
    Brian on
    http://stackoverflow.com/questions/373335/suggestions-for-a-cron-like-scheduler-in-python/374207#374207

  - Clock clip art https://openclipart.org/detail/12591/alarm-clock-by-anonymous-12591

  - fanart.jpg: a blend of
    http://commons.wikimedia.org/wiki/File:Sunrise_DUS.JPG
    and
    http://colouringbook.org/art/svg/coloring-book/orologio-clock-alarm-icon-coloring-book-colouring-coloring-book-colouring-book-colouringbook-org-art-clip-art-clipart-clipartist-net-openclipart-org-scalable-vector-graphics-svg/
   
