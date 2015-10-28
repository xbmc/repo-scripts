script.module.pydevd
==================

Kodi support for PyDev debugging in Eclipse/Aptana.

How to use:
-----------

 * Add script.module.pydevd as a requirement to the module under test:

    ```xml
    <!-- addon.xml -->
    <addon id="your.addon">
        <requires>
            <import addon="script.module.pydevd" version="4.4.0"/>
        </requires>
    </addon>
    ```
 * Start the debug server in Eclipse.

    If the debug server is not running when you call settrace then you'll encounter:

    ```python
    Error Type: <class 'socket.error'>
    Error Contents: [Errno 111] Connection refused
    ```
    
 * Then in the code under test:

    ```python
    import pydevd
    pydevd.settrace(stdoutToServer=True, stderrToServer=True)
    ```
 * Use Eclipse debug perspective to move through code.

See http://pydev.org/ for details.

Known Issues:
-------------

When attempting to exit or shutdown, Kodi will often freeze after a debug session
has been initiated.

Images in Kodi skins often fail to render during a debug session. If you want to
verify that images are being rendered then do not run under a pydev debug session.

Trademarks:
----------

"Python" is a registered trademark of the PSF. The Python logos (in several variants) are trademarks of the PSF as well. The logos are not registered, but registration does not equal ownership of trademarks.

www.python.org/psf/trademarks/
