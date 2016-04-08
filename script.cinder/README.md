###
### Cinder - Instructions
###

Cinder is a free plug-in script for KODI that allows you to play random TV Episodes from a list of SMB shares.
It is meant to be highly configurable and provide you a customized level of randomness that fits your taste.

------------------------------------------------------------------------------------------------------------

--= How to Configure Cinder =-- 

-- Prerequisites --

There are a few prerequisites that Cinder requires to function. 
The following sections will provide a basic description of how you would setup Cinder to work on the 
Windows 7 operating system. You can of course use any other operating system and can find specific details
by searching the internet. Though the details will vary the concepts described below will be the same. 


- Static IP Address -

Cinder is designed to pull files from SMB shares that contain your media (more on that later). 
The SMB shares need to be provided by a computer that resides on somewhere on your local network.
We will call that system your media server for lack of a better term. Your media server can also run KODI.
KODI instances running on other systems need to be able to find your media server over the network. 
A common network configuration uses a service called DHCP which gives your computer a new IP address 
every time it powers on. You want to avoid this since every time your media server restarts it will have
a new address and the KODI clients running Cinder will not be able to find your media server.

To avoid getting a new IP address each time your media server restarts it needs to be configured with a
Static IP address that doesn't change. This is configured in:

Control Panel\Network and Internet\Network Connections 

Find your network adapter usually called "Local Area Connection" or "Wireless Network Connection"
Double-click on your connection and select "Internet Protocol Version 4(TCP/IPv4)". 
Next click the "Properties" button.
In the pop-up click the "Use the following IP address" radio button and fill in your static IP address.

The IP Address must be matching what is configured by your Router/WAP. For this example my WAP address is
192.168.1.1 and I fill in the following Static IP address

IP address: 192.168.1.10
Subnet mask: 255.255.255.0
Default gateway: 192.168.1.1

This is a one time operation and only the media server needs a Static IP Address. The clients can use DHCP.


- SMB Shares -

A SMB Share is a fancy name for a shared folder in Windows 7. By setting up SMB Shares on your media server
KODI clients will be able to access your TV Shows over your network. Your media server will stream the file
content over your network.

So to set one up locate the folder using windows explorer. For this example I have a folder called "TV Shows". 
Inside of that folder I have a bunch of folders; one for each TV show. Inside of each show folder I have
a bunch of folders for each season (i.e. "Season1", "Season2", etc.). Inside of each season folder I have
the actual episode mp4 files.

To setup a share called "TV Shows" right click on the "TV Shows" folder. Click Properties and then click on
the Sharing tab. Next click Advanced Sharing. Click the "Share this folder" check box. In the Share name
field I type in "TV Shows". You can password protect your share here if you wish. When you are done click OK.
All done on the media server. Your SMB share is setup.

Now on the KODI clients that run Cinder you want to test your share and store passwords if appropriate.
In windows explorer type in your share address. In this example I type in the address bar at the top of the
window \\192.168.1.10\TV Shows then hit enter. If you see your TV show folders in the explorer you are
done with the setting up your SMB shares. You can make multiple shared folders if you wish. 
You only need to do this once.


------------------------------------------------------------------------------------------------------------


-- Configuring the Cinder Plug-in --

- Making a big Cinder Button -

I'm lazy.. If your anything like me you want a big button called Cinder that you click on once 
to do everything and start playing TV episodes. Here is how to do that.

On the KODI client that has Cinder installed hover over "SYSTEM" and click "Settings". Next click "Appearance".
Hover over "Skin" on the left then click "Settings". Next hover over "Add-on Shortcuts" and click "Add-on 1" 
under the Home page Videos submenu. Click on the Cinder plug-in. All done, you now have your big button.
You'll find it when you hover over "TV SHOWS" on the main screen.


- Configuring Cinder -

Cinder is extremely flexible which we will see as we configure the plug-in. To get to the Cinder configuration

On the KODI client that has Cinder installed hover over "SYSTEM" and click "Settings". Next click "Add-ons". 
You will find Cinder under "My add-ons" -> "All". Click on "Cinder" once you find it then click the 
"Configure" button. Here is where you will configure Cinder.

  - General Tab -

  The General tab contains overall settings.

  Select episodes from - you can pick one of All videos / Watched / Unwatched
            All videos - Cinder will pick any episode regardless of it being watched or not
               Watched - Cinder will only pick episodes that you have previously watched
             Unwatched - Cinder will only pick episodes that you have not previously watched

  Queue length - You can pick how many random TV episodes that Cinder will queue up and play every time
                 you click your big Cinder button

  Shuffle episodes - If enabled Cinder will play the episodes in random order if not they will be in order
                     of your SMB shares.

  Can skip sources - If enabled Cinder will randomly skip SMB shares. This will increase randomness more
                     since there is a 50% chance that a given SMB share will be skipped.

  Bootstrap playback - If enabled Cinder will start playing an episode as soon as it finds one. It will
                       continue to randomly populate your playlist in the background. This allows you to
                       start watching something while you wait. I'm impatiently lazy and this helps.
                       A queue of 100 episodes can take around 8 minutes to fully populate. 
                       10 episodes usually takes 45 seconds to populate. One caveat is that you cannot
                       skip forward to the next random episode until Cinder is done completely populating 
                       your playlist. But hey, at least you won't be sitting there for 45 seconds staring
                       at an empty screen waiting.


  - Sources / More Sources Tab -

  In the Sources tabs you can specify up to 20 SMB shares to pick episodes from. The reasoning here is that
  not all TV shows are equal. You probably just want to pick from your favorites and not queue up stuff from
  all your shows.  You can specify individual folders in your "TV Shows" SMB share that you want to pick 
  random episodes from. If you want to go nuts and add more than 20 shares you can modify the script.py
  file by writing some simple python to add to 2 lists. There are comments in that script that give an
  example for how to do it.

  Source folder - Here you add your smb share address. For example I have a folder "Rick and Morty" in my
                  "TV Shows" shared folder. Recall my media server Static IP Address is 192.168.1.10
                  I would type in smb://192.168.1.10/TV Shows/Rick and Morty 

  Source weight - Suppose that there are shows that would be nice to see once in a while and others that
                  are your favorites and would like to see much more. Here is where the source weight
                  slider comes in handy. You can pick the percentage of time a show would be picked from
                  the given source. 1 means 1% and 100 means 100%. Now you can weight your sources and
                  still maintain complete randomness.



--= Extra Stuff =-- 

-- What is Cinder doing under the hood? --

It's randomly populating KODI's native playlist with files from your SMB share(s) and starting it. 
Nothing more nothing less.


-- For the Brave --

One nice thing about using SMB shares is that you can play anything think: Movies, concerts, music videos,
home videos, mp3's, etc.

If you want to throw in the occasional movie between your TV Episodes you can do that. You can drill down
to specific shows or movies by adding more to your Source folder. i.e. smb://192.168.1.10/Movies/The Matrix 
with a Source weight of 1 would occasionally toss in movie The Matrix (1% chance). 

Your mileage may vary when you specify a folder with a lot of folders in it 
i.e. smb://192.168.1.10/Movies may be really slow and is probably not going to work well. 
specify a folder with a lot of folders in it i.e. smb://192.168.1.10/Movies may be really slow.

On the bright side you can get really creative with your sources. Have fun!



------------------------------------------------------------------------------------------------------------

Author: Justin Rush
e-mail: cinder.kodi@gmail.com

