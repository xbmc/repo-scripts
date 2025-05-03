<img src="https://raw.githubusercontent.com/matthane/script.audiooffsetmanager/refs/heads/main/resources/icon.png" width="256" height="256" alt="Audio Offset Manager">

# Audio Offset Manager

Audio Offset Manager is a utility addon for Kodi (v20.0+) designed to enhance your viewing experience by providing dynamic audio delay adjustments tailored to the content you're watching. This addon intelligently adjusts the audio offset based on the detected HDR type, audio format, and even FPS value according to user-configured settings. 

<img src="https://raw.githubusercontent.com/matthane/script.audiooffsetmanager/refs/heads/main/resources/screenshot-1.jpg" width="100%" alt="Audio Offset Manager screenshot 1">

## Features

- **Dynamic Audio Offset Application**: Automatically sets audio delay based on the HDR type, audio format, and FPS value of the current video, applying user-defined offsets to ensure consistent audio-visual sync without needing repeated manual adjustments.

- **Active Monitoring Mode**: Monitors when users manually adjust audio delay via Kodi's OSD settings, stores those adjustments, and applies them for future playback of similar content. This feature is particularly useful for initial AV calibration, allowing users to fine-tune audio sync and have those settings automatically applied to similar content in the future.

- **Custom Seek-Backs**: Offers user-configurable "seek-back" functionality to rewind a few seconds in specific playback situations to keep audio synchronized, such as:
  - When playback starts or resumes
  - When the audio stream changes during playback
  - When the audio offset is adjusted
  - When the player is unpaused

<img src="https://raw.githubusercontent.com/matthane/script.audiooffsetmanager/refs/heads/main/resources/screenshot-2.jpg" width="100%" alt="Audio Offset Manager screenshot 2">

This addon streamlines your viewing experience by automating the process of audio delay adjustment, ensuring that once you've configured the appropriate offsets, they are dynamically applied for each type of content.

## Supported Formats

### Audio Formats
- Dolby TrueHD*
- Dolby Digital Plus (E-AC-3)*
- Dolby Digital (AC-3)
- DTS-HD MA*
- DTS-HD HRA*
- DTS (DCA)
- Other/PCM 

*These formats can also contain spatial audio encoding such as Dolby Atmos or DTS:X on top of the base audio format

### Video Formats
- Dolby Vision
- HDR10
- HDR10+ (platform/build specific)
- HLG
- SDR

### FPS Types
23.98, 24, 25, 29.97, 30, 50, 59.94, 60

<img src="https://raw.githubusercontent.com/matthane/script.audiooffsetmanager/refs/heads/main/resources/screenshot-3.jpg" width="100%" alt="Audio Offset Manager screenshot 3">

## Installation and Usage

1. Download the addon from the Kodi repository or install it manually.
2. Enable the addon in Kodi's addon settings.
3. Open and briefly play any video to fully initialize and enable all addon settings.
4. Configure your desired audio offsets for different HDR types, audio formats, and FPS types in the addon settings. Enabling FPS based offsets allows different offsets to be applied and saved based on the FPS of the source video, in addition to the HDR type and audio format, allowing for more fine-tuned control.
5. If you want to perform initial AV calibration, enable the active monitoring mode in the addon settings. This will allow the addon to learn and store your manual audio offset adjustments for future use.
6. The addon will run as a background service, automatically applying your configured offsets during playback.

## Compatibility

This addon is designed for Kodi v20.0 and above. It may not function correctly with earlier versions of Kodi.

## Contributing and Reporting Issues

Contributions to improve Audio Offset Manager are welcome. If you encounter any issues or have suggestions for improvements, please open an issue on the [GitHub repository](https://github.com/matthane/script.audiooffsetmanager).

### Attributions

Icon designed by [Freepik](http://www.freepik.com/)
