# Radio Paradise addon for Kodi

Plays [Radio Paradise][] music streams, accompanied by the HD slideshow.

[radio paradise]: https://radioparadise.com/

## Features

- Radio Paradise music streams in AAC or FLAC
- HD slideshow (optional)
- Auto Play (optional)

## Requirements

- Kodi [release][] v20 or later

[release]: https://kodi.wiki/view/Releases

## Channel Selection by Script Parameter

In addition to the Auto Play feature, the addon script can be called with a
parameter to start a particular RP channel:

```python
RunScript('script.radioparadise', 1)
```

| Value | Channel |
| --- | --- |
| 0 | Main Mix |
| 1 | Mellow Mix |
| 2 | Rock Mix |
| 3 | Global Mix |
| 5 | Beyond... |
| 42 | Serenity |

This can be used to add shortcuts for RP channels in [favourites.xml][].

[favourites.xml]: https://kodi.wiki/view/Favourites.xml
