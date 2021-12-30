# Radio Paradise addon for Kodi

Plays [Radio Paradise][] music mixes, accompanied by the HD slideshow.

[radio paradise]: https://radioparadise.com/

## Features

- Radio Paradise music mixes in AAC or FLAC
- HD slideshow (optional)
- Auto Play (optional)

## Requirements

- Kodi [release][] v19 or later

[release]: https://kodi.wiki/view/Releases

## Mix Selection by Script Parameter

In addition to the Auto Play feature, the addon script can be called with a
parameter to start a particular RP mix:

```python
RunScript('script.radioparadise', 1)
```

Mix parameter:

| Value | Mix |
| --- | --- |
| 0 | RP Main Mix |
| 1 | RP Mellow Mix |
| 2 | RP Rock Mix |
| 3 | RP World/Etc Mix |

This can be used to add shortcuts for RP mixes in [favourites.xml][].

[favourites.xml]: https://kodi.wiki/view/Favourites.xml
