This addon has two modes, the default is to show a post play screen or it can be configured to show a popup next up notification automatically to prompt for playing the next unwatched episode.

Configuration:

  - The addon is found in the services section and allows the notification time to be adjusted (default 30 seconds before the end) - only for non postplay mode
  - The default action (ie Play/Do not Play) when nothing is pressed can also be configured
  - The number of episodes played in a row with no intervention to bring up the still watching window can be adjusted.
 

Skinners (PostPlayMode):
  
  - There is a script-nextup-notification-PostPlayInfo.xml located in default/1080i/ simply copy this to your skin folder and adjust it how you like it. 
  
      - script-nextup-notification-PostPlayInfo.xml
         - 101 - Previous Episode Button
         - 102 - Next Episode Button
         - 400 - Next Up List 
         - 201 - Home Button
         - 202 - Spoilers Button
         
         - Various Window Propertys are available including
           - Window.Property(background) - tvshow fanart
           - Window.Property(clearlogo) - tvshow clearlogo
           - Window.Property(banner) - tvshow banner
           - Window.Property(characterart) - tvshow characterart
           - Window.Property(next.poster) - next episode tvshow poster
           - Window.Property(next.thumb) - next episode thumb
           - Window.Property(next.clearart) - next episode tvshow clearart
           - Window.Property(next.landscape) - next episode landscape
           - Window.Property(next.plot) - next episode plot
           - Window.Property(next.tvshowtitle) - next episode tvshow title
           - Window.Property(next.title) - next episode title
           - Window.Property(next.season) - next episode season number
           - Window.Property(next.episode) - next episode episode number
           - Window.Property(next.year) - next episode preimiered year
           - Window.Property(next.rating) - next episode rating
           - Window.Property(next.duration) - next episode duration
           - Window.Property(previous.poster) - previous episode tvshow poster
           - Window.Property(previous.thumb) - previous episode thumb
           - Window.Property(previous.clearart) - previous episode tvshow clearart
           - Window.Property(previous.landscape) - previous episode landscape
           - Window.Property(previous.plot) - previous episode plot
           - Window.Property(previous.tvshowtitle) - previous episode tvshow title
           - Window.Property(previous.title) - previous episode title
           - Window.Property(previous.season) - previous episode season number
           - Window.Property(previous.episode) - previous episode episode number
           - Window.Property(previous.year) - previous episode preimiered year
           - Window.Property(previous.rating) - previous episode rating
           - Window.Property(previous.duration) - previous episode duration
           - Window.Property(showplot) - not empy when should show plot
           - Window.Property(stillwatching) - not empty when entered still watching mode                                        

Skinners (Non PostPlayMode):
  
  - There is a script-nextup-notification-NextUpInfo.xml and script-nextup-notification-StillWatchingInfo.xml file located in default/1080i/ simply copy this to your skin folder and adjust it how you like it. 
  - There is now script-nextup-notification-UnwatchedInfo.xml which by default shows a logo of an unwatched episode after 10 minutes for 10 seconds
      Controls Available:
  
      - script-nextup-notification-NextUpInfo.xml
          - 3000 - Title
          - 3001 - Plot
          - 3002 - Season/Episode
          - 3003 - Rating
          - 3004 - First Aired
          - 3005 - TV Show Fanart 
          - 3006 - TV Show ClearArt
          - 3007 - TV Show Title
          - 3008 - Episode Thumb
          - 3009 - TV Show Poster
          - 3010 - TV Show Landscape
          - 3011 - Video Resolution
          - 3012 - Watch Now Button
          - 3013 - Cancel Button
          - 3015 - Season Number
          - 3016 - Episode Number
          - 3018 - Play Count
          
      - script-nextup-notification-StillWatchingInfo.xml
          - 4000 - Label
          - 4001 - TV Show Poster
          - 4002 - Episode Thumb
          - 4003 - Rating
          - 4004 - First Aired
          - 4005 - TV Show Landscape
          - 4006 - Plot
          - 4007 - TV Show Fanart
          - 4008 - Season Number
          - 4009 - Episode Number
          - 4010 - Title
          - 4011 - Video Resolution
          - 4012 - Continue Watching Button
          - 4013 - Cancel Button
          - 4014 - TV Show ClearArt
          - 4018 - Play Count

      - script-nextup-notification-UnwatchedInfo.xml
          - 5000 - Label
          - 5001 - Plot
          - 5002 - Season/Episode
          - 5003 - Rating
          - 5004 - Clear Logo
