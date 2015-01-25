Notify
===========

Notify is a android app which allows you to forward events like notifications and phone-calls to selected clients.

This is a client-implementation for <a href="http://kodi.tv/">Kodi</a>

## Features

- Display a QR-Code for easy setup (Go to Programs and launch Notify)
- Display notifications of your phone right in Kodi
- On incoming-/outgoing calls pause or mute the playback or simply lower the volume


## Installation

- <a href="https://github.com/linuxwhatelse/notify-kodi/archive/master.zip">Download</a> this project<br>
- In Kodi go to System -> Settings -> Add-ons -> Install from zip file
- Select the previously downloaded .zip
- Disable and enable the addon once (This has to be done only after installing the addon because Kodi doesn't start the service after installation)


Once installed, you can change some configurations (like enabling basic-authorization, change the port and the behaviour<br>
for calls). Those changes should immediately take effect. If you encounter any problems try restarting Kodi once.<br>
If this doesn't help, feel free to open an issue ;)<br>


## Credits
Lincoln Loop for the python <a href="https://github.com/lincolnloop/python-qrcode">qrcode module</a>