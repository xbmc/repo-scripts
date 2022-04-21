# Using Qhue for Remote Access

Please make sure you're familiar with the main [README](README.md) before continuing!

Qhue is a handy way to interact with a Hue lighting system on your own network.  But suppose you wish to run Qhue-based software from somewhere else?  After all, the Hue app on your phone works when you're away from home, if you've enabled 'Out-of-home control' on your bridge.  Could your Python code do the same thing?

Remote access depends on you being authenticated via the Philips servers, and the good news is that, as ever, Philips have done [a good job in documenting this](https://developers.meethue.com/develop/hue-api/remote-api-quick-start-guide/).

Qhue version 2.0 and later includes a wrapper in the `qhue_remote.py` file to make this process easy.  This functionality has  deliberately been put in a separate file, partly to keep the main `qhue.py` nice and clean for those who don't need the remote aspects, but also because this is only a first version. Suggestions for improvements are welcome, or you may want to use qhue_remote just as an example for your own code.


## What's needed for remote access?

* You should get a username from the bridge as described in the main [README](README.md).  It's possible to do this remotely, but we haven't implemented that yet.  Save the username somewhere: you'll need it later.  In the remote access documentation this username is also known as a 'whitelist identifier' -- they're basically the same thing -- and it will typically be a 40-character string.

* You'll need the 'Out-of-home control' option turned on for your bridge.  In the Hue app, go to *Settings > Hue Bridges > your bridge* and check that it's enabled.

* You'll need a free [Hue developer's account](https://developers.meethue.com). As well as giving you access to all the relevant documentation,  this will allow you to register your app on the [My Apps page](https://developers.meethue.com/my-apps/).  This will give you a 'ClientId' and a 'ClientSecret' that represent your app.

* Remote access is authenticated via the widely-used OAuth 2 system.  The Hue-specific details are documented [here](https://developers.meethue.com/develop/hue-api/remote-authentication-oauth/).  We use Kenneth Reitz's excellent [requests-oauthlib](https://requests-oauthlib.readthedocs.io) library for Python, which is much nicer than doing it all ourselves.  We'll come back to how the authorisation works in a minute.

## What does it look like?

If you were using Qhue on your *local* network, you might make the initial connection to your bridge as follows:

```python
    from qhue import Bridge
    b = Bridge("192.168.0.45", username)
```

To make a remote connection, you would do the following instead:

```python
    from qhue import RemoteBridge
    b = RemoteBridge(username)
    token = b.authorize(app_client_id, app_client_secret)
```

Once the authorisation process has completed, you can use the Bridge reference `b` in just the same way as if it were local.

If you save the token you got back from the `authorize()` method, you can use it next time to avoid authorising manually again:

```python
    token = b.authorize(app_client_id, app_client_secret, token=token)
```

## How does the authorisation work?

The OAuth2 procedure is commonly used between two web services, e.g. to allow a plugin on your blog to have access to your Twitter feed.  In that scenario, the plugin would send you to Twitter,  you would approve the request for access to your tweets, and you would then be redirected back to your blog site via a 'Callback URL' that included the necessary credentials for the plugin to use.

The same thing happens here: when you go to the Hue Developers' Site to register your app, as mentioned above, you need to specify what this 'Callback URL' will be.   Then when you make the `b.authorize()` call, it will open your browser on the necessary Philips web page, you can authorise your app, and it will redirect you to your Callback URL with the appropriate authorisation information.

But what if you're using Qhue as part of a command-line application, or something else that can't easily listen on a URL for the credentials that will be sent back?

Well, then you have a couple of options.  (We'll assume here that you're running a Qhue-based utility on the command line.)  They're both slightly awkward, but you shouldn't need to do them often if you save the token you get back.  You could come up with other ways of doing this yourself.

The key thing to know is that *the URL itself isn't very important*: all that matters is that you capture the information in it and give it to the Qhue RemoteBridge so it can do the last stage of getting the access token it needs.


### Option 1: Manually copying the URL

You can set the Callback URL to pretty much anything that handles HTTPS.  For example, you could set it to `https://google.com`, or your own website. Using the Google example, once you've been authenticated, you would then be redirected to a URL that might look like this:

`https://www.google.com/?pkce=0&code=mod6jErp&state=NzLj5g6PQggn9cXpvDpZSD9OiahfmB`

Google won't know what to do with that, but it doesn't matter:  it's the bit beginning `?pkce...` that contains the necessary info.  You just need to copy the entire URL (including https://) from your browser address bar and paste it into the prompt that QHue gives you.


### Option 2: Redirecting to a local URL

When you call `b.authorize()`, you can add an argument of `use_local_server=True`.  Qhue will then run a small local webserver on your machine, which listens on port 8584, and on the Hue website you can specify the callback URL for your app as `https://localhost:8584`.  This little server (defined in `oauth_receiver.py`) will just listen for one connection.  When your browser comes in with the credentials in a URL like this:

`https://localhost:8584/?pkce=0&code=mod6jErp&state=NzLj5g6PQggn9cXpvDpZSD9OiahfmB`,

it will close down and hand that information on to Qhue.  Neat, eh?

Yes... except there's a small complication.

*OAuth 2 requires the Callback URL to be HTTPS, not HTTP.*  That means that this little server needs to have a certificate and private key to be able to serve up an HTTPS connection, and because it's a self-signed certificate, your browser will warn you and you'll need to authorize it to make the connection.

You'll need to generate the certificate and key.  It will look for them as files 'cert.pem' and 'key.pem' in the local directory, and you can create suitable files using:

```
openssl req -x509 -nodes -newkey rsa:2048 -subj '/CN=localhost' -keyout key.pem -out cert.pem -days 365
```


## Can you give me a more complete example?

Assuming you've created the key and certificate as described above, you could do something like this:

```python

import json
import os

from qhue import RemoteBridge

# Replace these with your real values:
# Username from the bridge:
USER_ID = "3q5-IVI73-tTBom-Litr3x8E0CP1viIzhxwyP8Sf"
# Client ID and secret from your app registration:
CLIENT_ID = "TSztodTUx5KCi5O4qJKePGIY52uCKKuP"
CLIENT_SECRET = "BBJvGhDmlsDbBHci"

# Where to save the token after you've authenticated
TOKEN_FILENAME = "access_token.json"

b = RemoteBridge(USER_ID)

if os.path.exists(TOKEN_FILENAME):
    # Load an existing token if we already have one
    with open(TOKEN_FILENAME) as f:
        token = json.load(f)
    b.authorize(CLIENT_ID, CLIENT_SECRET, token=token)

else:
    # Otherwise, open a browser to authenticate and run a server to
    # receive the callback credentials.
    token = b.authorize(
        CLIENT_ID, CLIENT_SECRET,
        open_browser=True, use_local_server=True
    )
    # Save the token for next time:
    with open(TOKEN_FILENAME, "wt") as f:
        json.dump(token, f, indent=2)

# Now we should be able interact with the bridge as normal:
print(b.lights())

```

## Notes

If you don't want Qhue to try opening your browser for you to do the authentication -- something that only makes sense anyway if it's running on your local machine -- you can specify `open_browser=False` when calling the `authorize` method and it will then print out the URL you need to open.

If you don't want to run a local server for receiving the credentials back, you can specify `use_local_server=False` (or omit it completely) and `authorize` will then prompt you on the command line to paste in the Callback URL with its arguments.

