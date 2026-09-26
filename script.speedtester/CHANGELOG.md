# Changelog

All notable changes to **script.speedtester** are documented here.
This project adheres to [Semantic Versioning](https://semver.org/).

## v2.0.0 (2026-07-26)
- Modern Ookla server discovery (`api/js/servers`) replacing the deprecated `speedtest-servers-static.php` list (@TomSzo_HUN)
- Automatic nearest-server selection worldwide, plus optional city/country search or a specific server ID (@TomSzo_HUN)
- Prefer-HTTPS server option and configurable connection timeout (@TomSzo_HUN)
- Optional download-only mode and optional result submission, off by default (@TomSzo_HUN)
- Modern settings format (`settings version="1"`) with dependency-driven visibility (@TomSzo_HUN)
- Localization for 11 languages: en, hu, de, fr, es, it, pt-BR, nl, pl, ru, zh-CN (@TomSzo_HUN)
- Python 3.9-3.12 compatibility (`threading.Event.is_set`) and `xbmc.python` 3.0.0 for Kodi 19-21 Omega (@TomSzo_HUN)
- Resilient configuration fetch with graceful fallback when legacy endpoints are unavailable (@TomSzo_HUN)

## v1.1.3 (2022-01-26)
- Add support for Python 3.9 and later (@dobo90)
- Add Dutch translations (@dagwieers)

## v1.1.2 (2020-10-10)
- Fix issues for Kodi repo review (@dagwieers)

## v1.1.1 (2020-10-10)
- Add localization (@dagwieers)

## v1.1.0 (2020-09-26)
- Move add-on to Add-ons project (@dagwieers)
- Fix typos and structure of standard output (@dagwieers)

## v1.0.1 (2019-08-06)
- Initial release (@Dr0idGuy)
