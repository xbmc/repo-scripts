service.tvh.manager
===================

Addon for 'PVR Timer- and Powermanagement' for XBMC/Kodi. This addon turns your vanilla Kodi on a Linux installation (pure Linux, Kodibuntu, Open-/LibreELEC) into a full featured video recorder.

This addon handles poweroff management for current active recordings and wakeup procedures for future schedules using the XML-Interface of TVHeadend. This plugin starts and shut down the htpc if a recording is scheduled. It delivers optional Emails via SMTP if an automatic scheduled Recording ended successfully. 

The plugin starts the system periodically on an user defined cycle and time for e.g. EPG-Updates too if there is a longer inactivity time of the system or user.


Some installation notes
-----------------------

1.	YOU KNOW WHAT A TERMINAL CONSOLE IS AND YOU ARE ABLE TO USE IT.

2.	THIS ADDON USE ACPI-WAKEUP OVER RTC. YOUR MAINBOARD MUST SUPPORT THIS PROPERLY. NOTE THAT IN YOUR APM-SETTINGS OF YOUR BOARD THE RTC WAKEUP SHOULD BE SET TO ‘by OS’ OR ‘disabled’.

3.	THIS README USES kodi AS THE DEFAULT USER. IF KODI IS RUNNING WITH A DIFFERENT USERNAME, CHANGE ALL OCCURENCES OF '/home/kodi/' TO '/home/yourusername/' IN YOUR PATHNAMES/NAMES.

Installation
------------

1.	Install this Addon from ZIP or from Repository

2.	If You are using OpenELEC/LibreELEC, the following step isn’t necessary. Skip to step 3.

    All others: As the shellscript ‘shutdown.sh’ is a wrapper to poweroff the system, it needs root privileges. We make it possible that ‘shutdown.sh’ runs under root/sudo privileges without needing to type in a password:

	    sudo visudo

    add below:
	
        Cmnd_Alias PVR_CMDS = /home/kodi/.kodi/addons/service.tvh.manager/resources/lib/shutdown.sh
        kodi ALL=NOPASSWD: PVR_CMDS

    Store your changes (CTRL+O, CTRL+X)

3.	Change your remote.xml to point the pvrmanager-addon when "Power" on remote is pressed. If you don't have a remote control you can also define a special key on your keyboard as power button (here as example F12).

    Create a remote.xml if it doesn't exists (Gotham and up):

        nano ~/.kodi/userdata/keymaps/remote.xml
        
    or (OpenELEC/LibreELEC):
        
        nano /storage/.kodi/userdata/keymaps/remote.xml

    and copy/paste following code into the editor: 

        <keymap>
            <global>
                <!-- This is the keyboard section -->
                <keyboard>
                    <f12>XBMC.RunScript(service.tvh.manager,poweroff)</f12>
                </keyboard>
                <!-- This is the remote section -->
                <remote>
                    <power>XBMC.RunScript(service.tvh.manager,poweroff)</power>
                </remote>
            </global>
        </keymap>

4.	Store (CTRL+O, CTRL+X), restart Kodi and enjoy!

ADDITIONAL FOR EXPERTS
----------------------

If you want to add a hook to the shutdown menu of kodi (this changes the behaviour of the power button), edit the ‘DialogButtonMenu.xml’ (or similar) in the xml part of the skin addon and look for a xml tag like (note the &lt;onclick&gt;Powerdown()&lt;/onclick&gt; inside here):

        <item>
            <label>$LOCALIZE[13016]</label>
            <onclick>Powerdown()</onclick>
            <visible>System.CanPowerDown</visible>
        </item>

and change this to:

        <item>
            <label>$LOCALIZE[13016]</label>
            <onclick>Powerdown()</onclick>
            <visible>System.CanPowerDown + !System.HasAddon(service.tvh.manager)</visible>
        </item>
        <item>
            <label>$LOCALIZE[13016]</label>
            <onclick>RunScript(service.tvh.manager,poweroff</onclick>
            <visible>System.CanPowerDown + System.HasAddon(service.tvh.manager)</visible>
        </item>

Don’t forget to store. Remember that you have to repeat this when the skin has updated.

Please send Comments and Bugreports to birger.jesch@gmail.com

HINT: If your OS is OpenELEC/LibreELEC you have to turn off ‘Shutdown requires admin privileges’ as OpenELEC/LibreELEC doesn’t need sudo! This should be done automatically in most cases.
