Notify
===========

Notify is a android app which allows you to forward events like notifications and phone-calls to selected clients.

This is a client-implementation for <a href="http://kodi.tv/">Kodi</a>

## Features

- Display a QR-Code for easy setup
- Display notifications of your phone right in Kodi
- On incoming-/outgoing calls pause or mute the playback or simply lower the volume


## Installation

- <a href="https://github.com/linuxwhatelse/notify-kodi/archive/master.zip">Download</a> this project<br>
- In Kodi go to System -> Settings -> Add-ons -> Install from zip file
- Select the previously downloaded .zip
- Disable and enable the addon (This has to be done only after installing the addon because Kodi doesn't start the service after the installation)


Once installed, you can change some configurations (like enabling basic-authorization, change the port and the behaviour<br>
for calls). Just make sure to disable and enable the addon for the changes to take effect.<br>

You can also launch the addon to shows a QR-Code which you can scan via the app to quickly add this client


## Credits
Lincoln Loop for the python <a href="https://github.com/lincolnloop/python-qrcode">qrcode module</a>