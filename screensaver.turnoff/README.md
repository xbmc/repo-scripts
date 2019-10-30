[![GitHub release](https://img.shields.io/github/release/dagwieers/screensaver.turnoff.svg)](https://github.com/dagwieers/screensaver.turnoff/releases)
[![Build Status](https://travis-ci.org/dagwieers/screensaver.turnoff.svg?branch=master)](https://travis-ci.org/dagwieers/screensaver.turnoff)
[![Codecov status](https://img.shields.io/codecov/c/github/dagwieers/screensaver.turnoff/master)](https://codecov.io/gh/dagwieers/screensaver.turnoff/branch/master)
[![License: GPLv3](https://img.shields.io/badge/License-GPLv3-yellow.svg)](https://opensource.org/licenses/GPL-3.0)
[![Contributors](https://img.shields.io/github/contributors/dagwieers/screensaver.turnoff.svg)](https://github.com/dagwieers/screensaver.turnoff/graphs/contributors)

# Kodi screensaver that turns your screen off to save power

This Kodi screensaver turns your TV, projector or monitor off, so it can actually "save your screen".


## How does it work ?

It supports the following methods:

- **CEC (built-in)**
  - The screensaver forces the display to go into Standby using internal CEC controls.

- **No Signal on Raspberry Pi (using vcgencmd)**
  - The screensaver causes 'no signal' using the vcgencmd utility. This only works on Raspberry Pi.

- **DPMS (built-in)**
  - The screensaver immediately forces the display off using internal DPMS (Energy Star) controls.

- **DPMS (using xset)**
  - The screensaver immediately forces the display off using the `xset` utility to set DPMS off state.

- **DPMS (using vbetool)**
  - The screensaver immediately forces the display off using the `vbetool` utility to set DPMS off state.

- **DPMS (using xrandr)**
  - The screensaver immediately forces the display off using the `xrandr` utility to set DPMS off state.

- **CEC on Android (kernel)**
  - The screensaver immediately forces the display off using kernel CEC controls and turns off device.

- **Backlight on Raspberry Pi (kernel)**
  - The screensaver turns off the backlight of the display. This only works on Raspberry Pi.

- **HDMI on Raspberry Pi (tvservice)**
  - The screensaver turns off the HDMI output using the 'tvservice' utility. This only works on Raspberry Pi, or possible other similar Broadcom chipsets.


Optionally it also can put your system to sleep or power it off.

Or log off your user or mute audio.

One can press the `HOME` key to deactivate the screensaver, depending on the method used and the state of the display it may turn your display back on.


## Related
A collection of related links:

- [Hardware hack for turning RPi on over CEC](https://forum.kodi.tv/showthread.php?tid=174315&pid=2651811#pid2651811)


## Reporting issues
You can report issues at [our GitHub project](https://github.com/dagwieers/screensaver.turnoff).


## Releases
### v0.10.1 (2019-10-30)
- Add sanity tests, unit tests and coverage support
- Use JSON-RPC for all built-ins
- Improvements for Python 3
- Support Odroid-C2 display method

### v0.10.0 (2019-03-13)
- Support RPi touchscreen display method
- Improve mute and unmuting audio using JSON-RPC

### v0.9.2 (2018-06-07)
- Fix translations
- Fix an issue when stopping the screensaver

### v0.9.1 (2018-04-14)
- Improve documentation
- Don't log when no action was taken
- Fix sanity issues

### v0.9.0 (2018-04-13)
- Improve help in add-on settings
- Improve add-on logging
- Add icon and title to pop-ups

### v0.8.1 (2018-04-12)
- Renamed add-on from 'No Signal' to 'Turn Off'
- Support vbetool and xrandr display methods
- Support Android CEC display method
- Support built-in and Android power methods
- Support Mute built-in
- Show a pop-up when errors are detected

### v0.8.0 (2018-04-12)
- Support built-in DPMS and CEC display methods
- Improve add-on settings

### v0.7.4 (2018-04-12)
- Support RPi and X11 xset DPMS display methods
- Support System.LogOff built-in
- Initial release
