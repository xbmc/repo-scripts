# NapiProjekt for Kodi

[English](#english) | [Polski](#polski)

Original add-on by **CaTz**. Version **2.0** updated to **3.0** by **Codex**.

## English

Kodi add-on for searching and downloading Polish subtitles from
[NapiProjekt.pl](https://napiprojekt.pl/).

The add-on calculates the NapiProjekt MD5 hash from the first 10 MiB of the
playing video and downloads subtitles matched to that exact file release.
Returned SubRip and MicroDVD subtitles are detected automatically and saved as
UTF-8 `.srt` or `.sub` files for Kodi.

### Version history

#### 2.0 — CaTz

The original add-on:

- calculated an MD5 hash from the first 10 MiB of the playing video;
- supported local files, SMB paths, RAR archives and Kodi stacks;
- checked subtitle availability through NapiProjekt's legacy endpoint;
- downloaded subtitle content through the XML API;
- used the subtitle languages provided by Kodi;
- supported `xbmc.python` 3.0.0.

#### 3.0 — Codex update

Changes and improvements since version 2.0:

- fixed writing byte data through the text-based `xbmcvfs.File` API under
  Kodi and Python 3;
- fixed Base64, UTF-8 and CP1250 decoding;
- added automatic detection of SubRip and both common MicroDVD variants:
  `[start][end]` and `{start}{end}`;
- subtitles are saved with the correct `.srt` or `.sub` extension;
- searches now make one request for Polish subtitles, independently of Kodi's
  configured language list;
- reduced search and download parameters to fields verified against the
  current API;
- switched both NapiProjekt endpoints from HTTP to HTTPS;
- added a persistent minimum two-second interval between requests, including
  separate Kodi add-on invocations;
- added HTTP 429 handling and a cooldown based on the `Retry-After` header,
  with a ten-second fallback;
- added timeouts, a `User-Agent` header and handling for network errors and
  invalid API responses;
- added distinct Kodi notifications for missing subtitles, missing files,
  hash failures, API limits, network failures and invalid responses;
- diagnostics, including the MD5 hash and operation result, use the
  official-repository-compatible `LOGDEBUG` level;
- protected invocation without an `action` parameter and improved hash
  calculation timeout handling;
- reorganized the Kodi entry point and added repository-compliant artwork;
- corrected add-on metadata while preserving credit for the original author,
  CaTz.

## Polski

Dodatek Kodi do wyszukiwania i pobierania polskich napisów z serwisu
[NapiProjekt.pl](https://napiprojekt.pl/).

Dodatek oblicza hash MD5 NapiProjektu z pierwszych 10 MiB odtwarzanego pliku i
pobiera napisy dopasowane do dokładnie tego wydania filmu. Zwrócone napisy
SubRip i MicroDVD są automatycznie rozpoznawane i zapisywane dla Kodi jako
pliki UTF-8 `.srt` lub `.sub`.

### Historia wersji

#### 2.0 — CaTz

Oryginalna wersja dodatku:

- obliczała hash MD5 z pierwszych 10 MiB odtwarzanego pliku;
- obsługiwała lokalne pliki, ścieżki SMB, archiwa RAR i stosy Kodi;
- sprawdzała dostępność napisów przez starszy endpoint NapiProjektu;
- pobierała treść napisów przez XML API;
- obsługiwała języki przekazane przez ustawienia napisów Kodi;
- była przystosowana do `xbmc.python` 3.0.0.

#### 3.0 — aktualizacja Codex

Naprawy i usprawnienia względem wersji 2.0:

- naprawiono zapis danych typu `bytes` przez tekstowy `xbmcvfs.File` w Kodi i
  Pythonie 3;
- poprawiono dekodowanie Base64 oraz tekstu UTF-8/CP1250;
- dodano automatyczne wykrywanie SubRip i obu spotykanych wariantów MicroDVD:
  `[start][koniec]` oraz `{start}{koniec}`;
- napisy są zapisywane z właściwym rozszerzeniem `.srt` albo `.sub`;
- wyszukiwanie wykonuje jedno zapytanie wyłącznie dla polskich napisów,
  niezależnie od listy języków Kodi;
- ograniczono parametry wyszukiwania i pobierania do pól potwierdzonych
  testami aktualnego API;
- oba endpointy NapiProjektu zostały przełączone z HTTP na HTTPS;
- dodano trwały limit minimum dwóch sekund pomiędzy requestami, działający
  także pomiędzy osobnymi wywołaniami dodatku przez Kodi;
- dodano obsługę HTTP 429 i cooldown zgodny z nagłówkiem `Retry-After`, z
  wartością zapasową dziesięciu sekund;
- dodano timeouty, nagłówek `User-Agent` oraz obsługę błędów sieciowych i
  nieprawidłowych odpowiedzi API;
- Kodi pokazuje osobne komunikaty dla braku napisów, braku pliku, problemu z
  obliczeniem hasha, limitu API, awarii sieci i błędnej odpowiedzi;
- diagnostyka, w tym MD5 i wynik operacji, korzysta z wymaganego przez
  oficjalne repo poziomu `LOGDEBUG`;
- zabezpieczono uruchomienie bez parametru `action` i poprawiono obsługę
  timeoutu obliczania hasha;
- uporządkowano entrypoint Kodi i dodano grafikę zgodną z wymaganiami repo;
- poprawiono metadane dodatku i zachowano creditsy oryginalnego autora CaTz.
