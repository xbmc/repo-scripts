## 2.2.0 (2025-10-02)

### Bug Fixes
- **Issue #40**: Clarified license statements - now consistently states "Artistic-1.0 OR GPL-1.0-or-later"
- **Issue #24**: Changed "Marker scan hit start of image data" to INFO level when `force=True` is used
- **Issue #32**: Fixed charset recognition for ISO 2022 escape sequences (UTF-8 as `\x1b%G`)
- **Issue #26**: Added validation for float/NaN values in `packedIIMData()` to prevent TypeError

### New Features
- **Issue #35**: Added 'credit line' field support per IPTC Core 1.1 (backward compatible with 'credit')
- **Issue #42**: Added 'destination' field as alias for 'original transmission reference'

### Improvements
- **Issue #15**: Enhanced IPTC tag collection with better field mappings
- **Issue #38**: Verified backup file behavior (use `options={'overwrite': True}` to avoid ~ files)
- Better error handling and logging throughout

### Notes
- **Issue #39, #41**: Ready for PyPI release with all fixes from master branch

---

Updating builds to target 3.9.7

2.1: Fixes merged to save modified IPTC info images

1.9.5-8: https://bitbucket.org/gthomas/iptcinfo/issue/4/file-permissions-for-changed-files-are-not - copy original file's permission bits on save/saveAs

1.9.5-7: https://bitbucket.org/gthomas/iptcinfo/issue/3/images-w-o-iptc-data-should-not-log-errors - have silencable parse errors.

1.9.5-6: to have a nice new upload (seems easy_install grabs an old version).

1.9.5-5: fix some issues with "super"

1.9.5-3: use logging module.

1.9.5-2: Emil Stenström pinpointed some bugs/misleading (un)comments
    Also a new (mis)feature is implemented: if you don't specify inp_charset
    (and the image misses such information, too) than no conversion is made
    to unicode, everything stays bytestring!
    This way you don't need to deal with charsets, BUT it is your risk to make
    the modifications with the SAME charset as it is in the image!

1.9.5-1: getting in sync with the Perl version 1.9.5

1.9.2-rc8:
    charset recognition loosened (failed with some image out of
    Adobe Lightroom).

1.9.2-rc7: NOT READY
    IPTCInfo now accepts 'inp_charset' keyword for setting input charset.

1.9.2-rc6: just PyLint-ed out some errors.

1.9.2-rc5: Amos Latteier sent me a patch which releases the requirement of the
    file objects to be file objects (he uses this on jpeg files stored in
    databases as strings).
        It modifies the module in order to look for a read method on the file
        object. If one exists it assumes the argument is a file object, otherwise it
        assumes it's a filename.

1.9.2-rc4: on Windows systems, tmpfile may not work correctly - now I use
    cStringIO on file save (to save the file without truncating it on Exception).

1.9.2-rc3: some little bug fixes, some safety enhancements (now iptcinfo.py
    will overwrite the original image file (info.save()) only if everything goes
    fine (so if an exception is thrown at writing, it won't cut your original
    file).

    This is a pre-release version: needs some testing, and has an unfound bug
    (yet): some pictures can be enhanced with iptc data, and iptcinfo.py is able
    to read them, but some other iptc data readers will spit on it.

1.9.1: a first release with some little encoding support

    The class IPTCInfo now has an inp_charset and an out_charset attribute - the
    first is the read image's charset (defaults to the system default charset),
    the second is the charset the writer will use (defaults to inp_charset).

    Reader will find the charset included in IPTC data (if any, defaults to the
    system's default charset), and use it to read to unicode strings. Writer will
    write using IPTCinfo.out_charset (if it is not set, will not write charset
    IPTC record).

    With this, it is possible to read and write i18n strings correctly.

    I haven't tested this functionality thoroughly, and that little test was only
    on my WinXP box only, with the only other IPTC reader: IrfanView.
