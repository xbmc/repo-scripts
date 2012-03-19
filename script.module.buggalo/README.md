INTRODUCTION
============
The buggalo script can collect various information about an
exception in a Python script as well as information about the
users system, such as XBMC and Python versions.

The collected information is then posted to the internet at a
predefined URL where the addon author can investigate the exception.

The script is somewhat similar to posting the xbmc.log to pastebin,
but is more specialised and doesn't contain superfluous information.
It is also better integrated into the user experience, the user only
has to decide if they want to submit the bug report or not.

The user will see a dialog as seen in this screenshot:
http://tommy.winther.nu/files/2011/12/script_error.png

HOW TO USE
==========
To use this script you must do these things besides importing it.

1.  Set buggalo.SUBMIT_URL to a full URL where the collected data is submitted.

2.  Surround the code you want to be covered by this script in a try..except block, such as:

    ```python
    try
        # addon logic
    except Exception:
        buggalo.onExceptionRaised()
    ```

    For plugin type addons, it is a good idea to include pretty much
    everything inside the try..except block.
    See this link for an example:
    https://github.com/xbmc-danish-addons/plugin.video.news.tv2.dk/blob/master/addon.py#L124

    For script type addons, besides the rule above, each event in
    your UI should include the try..except block as well.
    See this link for an example:
    https://github.com/twinther/script.tvguide/blob/master/gui.py#L140

    Optionally, instead of writing the try..except block yourself, you can decorate the function
    with @buggalo_try_except(). Function specific may be provide in the decorator:

    ```python
    @buggalo_try_except({'class' : 'MyWindowXML', 'method' : 'onInit', 'other_key' : 'other_value'})
    def onInit(self)
        pass
    ```

3.  Finally you must setup the website where the error report is submitted.
    A good starting point is my buggalo-web module on github:
    https://github.com/twinther/buggalo-web
    If you want to roll your own custom setup then take a look at the submit.php
    file which store the error report in the database.
    https://github.com/twinther/buggalo-web/blob/master/submit.php

    If you don't want to or can't setup your own website you can use the shared site at:
    http://buggalo.xbmc.info/
    In this case buggalo.SUBMIT_URL must be set to:
    http://buggalo.xbmc.info/submit.php

WHAT IS COLLECTED
=================
Five groups of information is collected beyond basic information
such as date and time.

*  System information
   OS name and version, kernel version, etc.
*  Addon information
   Addon id, name, version, path, etc.
*  XBMC Information
   Build version and date, the current skin and language
*  Execution information
   Python version and sys.argv
*  Exception information
   Type of exception, message and full stack trace

For further details take a look at the code in buggalo.py

---------------------------------------------------------------------

The latest code is always available at github:
https://github.com/twinther/script.module.buggalo

The module is named after a creature in my favorite animated show:
http://theinfosphere.org/Where_the_Buggalo_Roam

---------------------------------------------------------------------
                                               2012.02.18 - twinther
