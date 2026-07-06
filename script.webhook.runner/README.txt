Webhook Runner Add-on for Kodi 21+

Trigger Home Assistant (or any) webhooks from Kodi, either by pressing a
mapped remote/keyboard button, or automatically when a Kodi event fires.

Features:
 - Configurable webhooks, each with a name and URL
 - Optional default URL prefix in settings - prefilled when adding
   a webhook so you only type the webhook name at the end (e.g.
   http://homeassistant.local:8123/api/webhook/)
 - Optional notification toggle
 - Two ways to fire a webhook:
     1. Button mapping via Keymap Editor (one button per webhook)
     2. Event triggers - automatic firing on Kodi events
 - Per-event mapping: pick which webhook (if any) fires on each event
 - Global on/off toggle for event triggers in settings

Supported events (configure from main menu → Event Triggers):
 - Playback started / stopped / paused / resumed
 - Screensaver activated / deactivated
 - Kodi started / stopping

Typical use case - HA-connected IR blaster:
 - Create HA automations that call remote.send_command for your IR
   commands (receiver on / off, input switch, etc.) and expose each
   as a webhook.
 - Add one Webhook Runner entry per HA webhook URL.
 - In Event Triggers, map "Playback started" -> Receiver On and
   "Playback stopped" -> Receiver Off. Done; runs in the background.

To launch from remote (manual webhook fire by id):
  RunScript("script.webhook.runner", id=1)

To launch the GUI:
  Add-ons -> Program Add-ons -> Webhook Runner

Notes:
 - "Playback stopped" fires for both stopped and ended playback.
 - "Kodi started" fires when the background service loads, which is
   typically slightly before the UI is fully ready.
 - There is no debounce; rapid pause/resume will fire the webhook
   each time.
