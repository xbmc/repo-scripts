History
=======

2.1.4 (2017-06-01)
------------------

- Fix broken match function when using `rebulk>=0.9.0`.

2.1.3 (2017-05-31)
------------------

- Add `nzb` as new `container` possible value
- Add `EAC3` as new `audio_codec` possible value
- Add `FullHD` as new `other` possible value
- Added python 3.6 support
- Dropped python 2.6 support
- Make `container` values consistent and always lowercase
- Fix `--type movie` being ignored for movies that starts with numbers
- Fix invalid `language` detection due the common words `audio`, `true` and `unknown`
- Fix `episode` type detection when series name contains `year` followed by SEE pattern

2.1.2 (2017-04-03)
------------------

- Many fixes, additions and improvements (thanks to @ratoaq2).

2.1.1 (2016-12-04)
------------------

- Add `~` to episode/season separators.
- Add `AHDTV`, `HDTC`, `SATRip` as new `format` possible values.
- Add `streaming_service` property.
- Add `DDP` pattern as `audio_codec`=`DolbyDigital`.
- Add `LDTV` as possible tag for `other`=`LD`.
- Add `StripSeparators` Post Processor to strip separators from all matches.
- Fix invalid guess `1 x 2` with `--type episode`.
- Fix `part` property.
- Fix `cd_count` issue with `x264-CD`.
- Fix `HDD` group detected as `DolbyDigital`.
- Fix invalid comparator in `audio_codec` conflict solver.
- Fix validation of `film` property.
- Fix `date` followed by `screen_size` invalid guess.
- Fix `episode` not detected when smaller filepart repeats the `season` and uses `SSEE` pattern.
- Enhance `season`/`episode` conflict solver to keep most specific value.
- Enhance `video_profile` detection.
- Enhance `episode`/`season` range and sequence guessing.
- Enhance performance with rebulk upgrade to `0.8.2`.
- Enhance `season`/`episode`.
- Enhance `other`=`Complete` guessing.
- Enhance `release_group` guessing.
- Enhance command line options parsing related to unicode.
- Ensure roman numbers are surrounded with separators to be guessed as numbers.

2.1.0 (2016-09-08)
------------------

- Drop support for `regex` native module.
- Remove dependency constraint on `python-dateutil`.
- Enhance langage/country guessing in edge cases.
- Enhance rule to guess `release_group` in more file templates.
- Fix edge cases for subtitle language detection.
- Fix invalid conflict solving in `season`/`episode` occuring between `SssEee` and `ssXee` pattern.
- Fix issue when running guessit in non-interactive shell with python 2
- Guess Dolby keyword as DolbyDigital in `audio_codec`.
- Avoid `title` to be guessed as `website` (Dark.Net)
- Avoid `season`/`episode` to be guessed when pattern is included inside words.
- Enhance `screen_size` to detect `720pHD` and `1080pHD`
- Add support for `format` and `video_codec` when no separators between themselves. (HDTVx264, PDTVx264, ...)
- Add rebulk version in `--version` option.
- Upgrade rebulk to `0.7.3`.

2.0.5 (2016-04-10)
------------------

- Fix inconsistent properties returned by guessit -p.
- Add support for titles containing dots.
- Lock python-dateutil dependency to <2.5.2.

2.0.4 (2016-02-03)
------------------

- Add an Exception Report when an unexpected exception occurs.


2.0.3 (2016-01-30)
------------------

- Something goes wrong with 2.0.2 release ...


2.0.2 (2016-01-30)
------------------

- Fix possible issue with unicode characters encoding/decoding.
- Pypy is now supported.


2.0.1 (2016-01-28)
------------------

- Add support for any type of string with python 2 and python 3 (binary, str, unicode).


2.0.0 (2016-01-27)
------------------

- Final release.


2.0rc8 (2016-01-26)
-------------------

- Remove regex native module from required dependencies. It will now be used only if present.


2.0rc7 (2016-01-18)
-------------------

- Fix packaging issues on Python 2.7.


2.0rc6 (2016-01-18)
-------------------

- Fix packaging issues.


2.0rc5 (2016-01-18)
-------------------

- Guessit isĂÂ now available as a docker container on Docker Hub (https://hub.docker.com/r/toilal/guessit).
- `country` 2-letter code is not added to `title` value anymore.
- All `container` values are now capitalized.
- `alternativeTitle` has been renamed to `alternative_title` and added to the docs.
- `mimetype` property is now in the docs.
- Add more excluded words for `language` property.
- Add more possible values for `other` property.
- Fix an issue occuring with `title` values starting with `Scr`.
- `film` property is now guessed only if less than `100` to avoid possible conflicts with `crc32`.


2.0rc4 (2015-12-03)
-------------------

- Add docs.
- Add exotic `screen_size` patterns support like `720hd` and `720p50`.
- Rename `audio_codec` value `true-HD` to `trueHD`.


2.0rc3 (2015-11-29)
-------------------

- Add ``__version__`` to main module.


2.0rc2 (2015-11-28)
-------------------

- Single digit episodes are now guessed for ``--type episode`` instead of ``--episode-prefer-number``.
- Fix separators that could cause some titles to be splited with & and ;.
- Avoid possible ``NoneType`` error.


2.0rc1 (2015-11-27)
-------------------

- Fallback to default title guessing when ``expected-title`` is not found.


2.0b4 (2015-11-24)
------------------

- Add ``expected-group`` option.
- Add validation rule for single digit ``episode`` to avoid false positives.
- Add ``verbose`` option.
- Fix ``expected-title`` option.
- Better unicode support in ``expected-group``/``expected-title`` option.


2.0b3 (2015-11-15)
------------------

- Add support for ``part`` with no space before number.
- Avoid ``uuid`` and ``crc32`` collision with ``season``/``episode`` properties.
- Add better space support for ``season``/``episode`` properties.
- Ensure ``date`` property is found when conflicting with ``season``/``episode`` properties.
- Fix ``IndexError`` when input has a closing group character with no opening one before.
- Add ``--type`` option.
- Add rebulk implicit option support.

2.0b2 (2015-11-14)
------------------

- Add python 2.6 support.


2.0b1 (2015-11-11)
------------------

- Enhance title guessing.
- Upgrade rebulk to ``0.6.1``.
- Rename ``properCount`` to ``proper_count``
- Avoid crash when using ``-p``/``-V`` option with ``--yaml`` and ``yaml`` module is not available.

2.0a4 (2015-11-09)
------------------

- Add ``-p``/``-V`` options to display properties and values that can be guessed.


2.0a3 (2015-11-08)
------------------

- Allow rebulk customization in API module.

2.0a2 (2015-11-07)
------------------

- Raise TypeError instead of AssertionError when non text is given to guessit API.
- Fix packaging issues with previous release blocking installation.

2.0a1 (2015-11-07)
------------------

- Rewrite from scratch using Rebulk.
- Read MIGRATION.rst for migration guidelines.
