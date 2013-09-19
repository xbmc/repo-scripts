INTRODUCTION
============
The buggalo script can collect various information about an
exception in a Python script as well as information about the
users system, such as XBMC and Python versions.

The collected information is then posted to the internet at a
predefined URL or Gmail account where the addon author can
investigate the exception.

The script is somewhat similar to posting the xbmc.log to pastebin,
but is more specialised and doesn't contain superfluous information.
It is also better integrated into the user experience, the user only
has to decide if they want to submit the bug report or not.

The user will see a dialog as seen in this screenshot:
http://forum.xbmc.org/showthread.php?tid=121925&pid=1137307#pid1137307


HOW TO USE
==========
To use this script you must do these things besides importing it.

1.  Choose whether to submit the collected data to a Gmail account or
    a private website containing buggalo-web.

    *  To use a Gmail account set the buggalo.GMAIL_RECIPIENT to the full
       gmail.com address of the recipient.

    *  To use a website set buggalo.SUBMIT_URL to a full URL where the
       collected data is submitted.

2.  Surround the code you want to be covered by this script in a
    try..except block, such as:

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

    Optionally, instead of writing the try..except block yourself, you
    can decorate the function with @buggalo_try_except(). Function
    specific extra data may be provide in the decorator:

    ```python
    @buggalo_try_except({'class' : 'MyWindowXML', 'method' : 'onInit', 'other_key' : 'other_value'})
    def onInit(self)
        pass
    ```

3.  If you chose to use a private website in step 1, now is the time to configure that
    - otherwise there is no step 3...

    A good starting point for the website is my buggalo-web module on github:
    https://github.com/twinther/buggalo-web
    If you want to roll your own custom setup then take a look at the submit.php
    file which store the error report in the database.
    https://github.com/twinther/buggalo-web/blob/master/submit.php


NOTES ABOUT GMAIL RECIPIENT
===========================
Gmail has pretty good spam filtering, but there's a good change the error reports
will end up in your spam folder. You will have to tweak your spam settings if that
is the case.

Furthermore all emails are prefixed with [Buggalo] and [addon.id] in the subject,
so you can use that for making filters.


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
*  User flow information
   For plugin-type addons each request is recorded with parameters and timestamp
   For script-type addons the author must record relevant information by invoking
   the trackUserFlow() method

For further details take a look at the code in buggalo_client.py


TRACKING USER FLOW
==================
A new feature in version 1.1.0 is the option to track the users flow when the user navigate through
the addon. This can somewhat be compared to an access log from the apache webserver.

Buggalo will keep track of the userflow for individual addons and store it up to 24 hours.
This also means that when an error report is sent it contains the userflow for the last 24 hours.

```python
buggalo.trackUserFlow('event information')
```

*  For plugin-type addons the userflow is automatically tracked.
   It is possible for the addon author to track additional events by invoking the trackuserFlow() method.

*  For script-type addons the addon author must invoke the trackUserFlow() method with relevant information.
   This could be pretty much anything, it could fx be used to track navigation insde a customer UI.

---------------------------------------------------------------------

The latest code is always available at github:
https://github.com/twinther/script.module.buggalo

The module is named after a creature in my favorite animated show:
http://theinfosphere.org/Where_the_Buggalo_Roam

---------------------------------------------------------------------
2012.09.26 - twinther
