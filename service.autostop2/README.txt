This is a simple Kodi service addon which monitors video and music playback.  It allows users 
to selectively stop paused or current playback after a certain amount of time.  

The sleep timer to stop current playback can be incremented by calling the addon from either
favourites.xml or keyboard.xml .  This will increment through the sleep timer settings to 
allow quick adjustment of the timer without going into the autostop addon settings

Here's a favourites example:

<favourites>
    <favourite name="Autostop Sleep Timer">RunScript("service.autostop")</favourite>
</favourites>

A popup window will appear for 3 seconds to let you know the new sleep timer value.  