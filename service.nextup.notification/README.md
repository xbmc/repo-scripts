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
           - Window.getProperty('background') - tvshow fanart
           - Window.getProperty('clearlogo') - tvshow clearlogo
           - Window.getProperty('next.poster') - next episode tvshow poster
           - Window.getProperty('next.thumb') - next episode thumb
           - Window.getProperty('next.clearart') - next episode tvshow clearart
           - Window.getProperty('next.landscape') - next episode landscape
           - Window.getProperty('next.plot') - next episode plot
           - Window.getProperty('next.tvshowtitle') - next episode tvshow title
           - Window.getProperty('next.title') - next episode title
           - Window.getProperty('next.season') - next episode season number
           - Window.getProperty('next.episode') - next episode episode number
           - Window.getProperty('next.year') - next episode preimiered year
           - Window.getProperty('next.rating') - next episode rating
           - Window.getProperty('next.duration') - next episode duration
           - Window.getProperty('previous.poster') - previous episode tvshow poster
           - Window.getProperty('previous.thumb') - previous episode thumb
           - Window.getProperty('previous.clearart') - previous episode tvshow clearart
           - Window.getProperty('previous.landscape') - previous episode landscape
           - Window.getProperty('previous.plot') - previous episode plot
           - Window.getProperty('previous.tvshowtitle') - previous episode tvshow title
           - Window.getProperty('previous.title') - previous episode title
           - Window.getProperty('previous.season') - previous episode season number
           - Window.getProperty('previous.episode') - previous episode episode number
           - Window.getProperty('previous.year') - previous episode preimiered year
           - Window.getProperty('previous.rating') - previous episode rating
           - Window.getProperty('previous.duration') - previous episode duration
           - Window.getProperty('showplot') - not empy when should show plot
           - Window.getProperty('stillwatching') - not empty when entered still watching mode                                        

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