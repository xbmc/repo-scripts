The player scans defined sources for media, thus sources must be created first.
Press 'stop+forward' to enter the button assignment mode.

This script helps using xbmc as music player only, without the need for display usage.
Script mainly works for music files, when started without parameters or with the 'music' parameter.
It might plays also audio track from videos, when started with the 'video' parameter.
On startup script scans all media mentioned in the sources.xml file, creating a scan list.
If the list already exists if will be reused. To rescan press 'Rescan' button.

Script works in three modes, NORMAL, PROGRAM and ALBUM.
NORMAL and PROGRAM modes have their own playlists. These playlists are mutually exclusive and together
consists of all tracks from the scan list.
The ALBUM mode uses a subset of NORMAL mode playlist, playing only tracks within current album.
On startup, the NORMAL mode is active and its playlist is composed from the whole scan list
(thus the program playlist is empty).
While in any normal playlist mode (NORMAL/ALBUM), to move the current track to the program playlist press 'select'.
And vice versa, pressing OK while in PROGRAM mode will move the current track to the normal playlist.
To switch to the PROGRAM mode press 'Normal mode' button, it will also disable any repeat mode.
To switch to the ALBUM mode press 'Progrem mode' button, it will also disable any repeat mode.

There are three repeat modes:
one - plays repeatedly current track, activate it with 'Repeat one' button.
all - plays repeatedly current playlist (or limited to single album if in ALBUM mode), activate it with 'Repeat all' button.
A-B - plays repeatedly selected part of a track, activate it with 'Repeat A-B' button
To switch off any repeat mode press any of 'Normal/Program/Album mode' buttons.

Current playlist can be saved with index 1..9 (press 'Save playlist' button and then 1..9).
Saved playlist can be loaded as the new current mode playlist (press 'Load playlist' and then 1..9).
Only the tracks that exist on the scan list will be loaded.
The opposite playlist (so program list if in NORMAL mode or Normal list if in PROGRAM mode)
will be automatically composed to contain only remaining files, which are on the scan list
but not on the newly composed current mode playlist.

The numbered keys usage:
- starting from non-0: select track number within album to be played, where the number is the scan list position.
- starting from 0: select album and its first available track, where the album number is the scan list position.

There is a hot key that can be assigned and used to start the script with a remote button press.
A hot key can be used when in VIDEOS or MUSIC menu, starting script in adequate mode.
Only standard remote buttons can be defined and a restart is required.
To use other buttons add the following calls in keymap.xml file:
XBMC.RunScript(script.xbmc.blindplayer, "music") or
XBMC.RunScript(script.xbmc.blindplayer, "video")

For example:
<keymap>
  <MyMusicFiles>
    <remote>
      <subtitle>XBMC.RunScript(script.xbmc.blindplayer, "music")</subtitle>
    </remote>
  </MyMusicFiles>
  <MyMusicLibrary>
    <remote>
      <subtitle>XBMC.RunScript(script.xbmc.blindplayer, "music")</subtitle>
    </remote>
  </MyMusicLibrary>
  <MyVideoLibrary>
    <remote>
      <subtitle>XBMC.RunScript(script.xbmc.blindplayer, "video")</subtitle>
    </remote>
  </MyVideoLibrary>
  <MyVideoFiles>
    <remote>
      <subtitle>XBMC.RunScript(script.xbmc.blindplayer, "video")</subtitle>
    </remote>
  </MyVideoFiles>
</keymap>
