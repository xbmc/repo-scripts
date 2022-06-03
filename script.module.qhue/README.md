# Qhue

Qhue (pronounced 'Q') is an exceedingly thin Python wrapper for the Philips Hue API.

I wrote it because some of the other (excellent) frameworks out there weren't quite keeping up with developments in the API.  Because Qhue encodes almost none of the underlying models - it's really just a way of constructing URLs and HTTP calls - it should inherit any new API features automatically.  The aim of Qhue is not to create another Python API for the Hue system, so much as to turn the existing API *into* Python, with minimal interference.

## Understanding Qhue

Philips, to their credit, created a beautiful RESTful API for the Hue system, documented it and made it available from very early on.   If only more manufacturers follwed their example!

You can (and should) read [the full documentation here](http://www.developers.meethue.com/philips-hue-api), but a quick summary is that resources like lights, scenes and so forth each have a URL, that might look like this:

    http://[myhub]/api/<username>/lights/1

You can read information about light 1 by doing an HTTP GET of this URL, and modify it by doing an HTTP PUT.

In the `qhue` module we have a Resource class, which represents *something that has a URL*. By calling an instance of this class, you'll make an HTTP request to the hub on that URL.

It also has a Bridge class, which is a handy starting point for building Resources (and is itself a Resource).  If that seems a bit abstract, don't worry - all will be made clear below.

## Installing Qhue

That's easy.

    pip install qhue

or, more correctly these days:

    python3 -m pip install qhue

You may want to check [GitHub](https://github.com/quentinsf/qhue) for the latest version of the module, and of this documentation.  The very latest code is likely to be on [the 'develop' branch](https://github.com/quentinsf/qhue/tree/develop).

Please note that Qhue, from version 2.0 onwards, expects Python 3 or later.  If you still need to support Python 2, you should use an earlier version of Qhue.

## Examples

Note: These examples assume you know the IP address of your bridge.  See [the 'Getting Started' section of the API docs](http://www.developers.meethue.com/documentation/getting-started) if you need help in finding it.  I've assigned mine a static address of 192.168.0.45, so that's what you'll see below.

They also assume you have experimented with the API before, and so have a user account set up on the bridge, and the username stored somewhere.  This is easy to do, but you will need to read the section below entitled 'Creating a user' before actually trying any of the following.

OK.  Now those preliminaries are out of the way...

First, let's create a Bridge, which will be your top-level Resource.

```python
    # Connect to the bridge with a particular username
    from qhue import Bridge
    b = Bridge("192.168.0.45", username)
```

You can see the URL of any Resource:

```python
    # This should give you something familiar from the API docs:
    # the base URL for API calls to your Bridge.
    print(b.url)
```

By requesting most *other* attributes of a Resource object, you will construct a new Resource with the attribute name added to the URL of the original one:

```python
    lights = b.lights   # Creates a new Resource with its own URL
    print(lights.url)    # Should have '/lights' on the end

Or, to show it another way, here's what these look like on my system:

    >>> b.url
    'http://192.168.0.45/api/sQCpOqFjZT2uYlFa2TNKXFbX0RZ6OhBjlYeUo-8F'
    >>> b.lights.url
    'http://192.168.0.45/api/sQCpOqFjZT2uYlFa2TNKXFbX0RZ6OhBjlYeUo-8F/lights'

Now, these Resources are, at this stage, simply *references* to entities on the bridge: they haven't communicated with it yet.  So far, it's just a way of constructing URLs, and you can construct ones which wouldn't actually do anything for you if you tried to use them!

     # Not actually included with my bridge, but I can still get a URL for it:
    >>> b.phaser_bank.url
    'http://192.168.0.45/api/sQCpOqFjZT1uYlFa2TNKXFbX0RZ6OhDjlYeUo-8F/phaser_bank'

To make an actual API call to the bridge, we simply *call* the Resource as if it were a function:

```python
    # Let's actually call the API and print the results
    print(b.lights())
```

Qhue takes the JSON that is returned by the API and turns it back into Python objects, typically a dictionary, so you can access its parts easily, for example:

```python
    # Get the bridge's configuration info as a dict,
    # and print the ethernet MAC address
    print(b.config()['mac'])
```

So we've seen that you can call `b.lights()` and `b.config()`. What other calls can you make to the bridge?

Well, you can actually call the bridge itself, and you get back a great big dictionary with everything in it.  It's a bit slow, so if you know what you want, it's better to focus on that specific call.  But by looking at the keys of that dictionary, you can see what the top-level groups are:

```python
    >>> for k in b(): print(k)
    lights
    groups
    config
    schedules
    scenes
    rules
    sensors
    resourcelinks
```

and you can explore within these lower levels too:

```python
    >>> for k in b.sensors(): print (k)
    1
    2
    4
    5
    8
    ...
```

OK, let's think about URLs again.

Ideally, we'd like to be able to construct all of our URLs the same way we did above, so we would refer to light 1 as `b.lights.1`, for example. But this bumps up against a limitation of Python: you can't use numbers as attribute names.  Nor can you use variables.  So we couldn't get light *n* by requesting `b.lights.n` either.

As an alternative, therefore, Qhue will also let you use dictionary key syntax - for example, `b.lights[1]` or `b.lights[n]`.

```python
    # Get information about light 1
    print(b.lights[1]())

    # or, to do the same thing another way:
    print(b['lights'][1]())
```

Alternatively, when you *call* a resource, you can give it arguments, which will be added to its URL when making the call:

```python
    # This is the same as the last examples:
    print(b('lights', 1))
```

So there are several ways to express the same thing, and you can choose the one which fits most elegantly into your code.

Here's another example, and instead of lights, we'll use sensors (switches, motion sensors etc). This one-liner will tell you where people are moving about:

    >>> [s['name'] for s in b.sensors().values() if s['state'].get('presence')]
    ["Quentin's study", "Hall", "Kitchen"]

Let's explain that one-liner, by way of revision:

`b.sensors` is a Resource representing your sensors, so `b.sensors()` will make an API call and get back a dict of information about all your sensors, indexed by their ID.  We don't care about the ID keys here, so we use `b.sensors().values()` to get a list containing just the data about each sensor.

Each item in this list is a dict which will include a 'name' and a 'state', and if the state includes a 'presence' with a true value, then it is a motion sensor which is detecting movement.


### Making changes

Now, to make a change to a value, such as the brightness of a bulb, you also call the resource, but you add keyword arguments to specify the properties you want to change.  You can change the brightness and hue of a light by setting properties on its *state*, for example:

```python
    b.lights[1].state(bri=128, hue=9000)
```

and you can mix URL-constructing positional arguments with value-setting keyword arguments, if you like:

```python
    # Positional arguments are added to the URL.
    # Keyword arguments change values.
    # So these are equivalent to the previous example:

    b.lights(1, 'state', bri=128, hue=9000)
    b('lights', 1, 'state', bri=128, hue=9000)
```

When you need to specify boolean true/false values, you should use the native Python True and False.

As a more complex example, if you want to set the brightness and colour temperature of a light in a given scene, you might use a call like this:

```python
    bridge.scenes[scene].lightstates[light](on=True, bri=bri, ct=ct)
```

The above examples cover most simple cases.

**If you don't have any keyword arguments, the HTTP request will be a GET, and will tell you about the current status.  If you do have keyword arguments, it will become a PUT, and it will change the current status.**

Sometimes, though, you need to specify a POST or a DELETE, and you can do so with the special *http_method* argument, which will override the above rule:

```python
    # Delete rule 1
    b('rules', 1, http_method='delete')
```

If you need to specify a keyword argument that would conflict with a Python keyword, such as `class`, simply append an underscore to it, like this:


```python
    # Set property "class" to "Hallway".
    # The trailing underscore will automatically be removed
    # in the property name sent to the bridge.

    b.groups[19](class_='Hallway')
```

Finally, for certain operations, like schedules and rules, you'll want to know the 'address' of a resource, which is the absolute URL path - the bit after the IP address, or, more recently, the bit after the username.  You can get these with the `address` and `short_address` attributes:

```python
    >>> b.groups[1].url
    'http://192.168.0.45/api/ac594202624a7211ac44615430a461/groups/1'
    >>> b.groups[1].address
    '/api/ac594202624a7211ac44615430a461/groups/1'
    >>> b.groups[1].short_address
    '/groups/1'
```

See the API docs for more information about when you need this.

And, at present, that's about it.


## A couple of hints

* Some of the requests can return large amounts of information.  A handy way to make it more readable is to format it as YAML.  You may need to `pip install PyYAML`, then try the following:

```python
    import yaml
    print(yaml.safe_dump(bridge.groups(), indent=4))
```

* The Bridge generally returns items in a reasonably logical order. The order is not actually important, but if you wish to preserve it, then you probably *don't* want the JSON structures turned into Python dicts, since these do not generally preserve ordering.  When you construct the Bridge object, you can tell it to use another function to turn JSON dictionaries into Python structures, for example by specifying `object_pairs_hook=collections.OrderedDict`. This will give you OrderedDicts instead of dicts, which is a benefit in almost every way, except that any YAML output you create from it won't look so nice.

* If you're familiar with the Jupyter (iPython) Notebook system, it can be a fun way to explore the API.  See the [Qhue Playground example notebook](Qhue%20playground.ipynb).

* If there is an error, a `QhueException` will be raised.  If the error was returned from the API call, as described in [the documentation](https://developers.meethue.com/develop/hue-api/error-messages/), it will have a type and address field as well as the human-readable message, making it easier, for example, to ignore certain types of error.

## Creating a user

If you haven't used the API before, you'll need to create a user account on the bridge.

```python
    from qhue import create_new_username
    username = create_new_username("192.168.0.45")
```

You'll get a prompt saying that the link button on the bridge needs to be pressed.  Go and press it, and you should get a generated username. You can now get a new Bridge object as shown in the examples above, passing this username as the second argument.

Please have a look at the examples directory for a method to store the username for future sessions.


## Usage notes

Please note that qhue won't do any local checking of any method calls or arguments - it just packages up what you give it and sends it to the bridge.

An important example of this is that the bridge is expecting integer values for things like colour temperature and brightness. If, say, you do a calculation for your colour which returns a float, you need to convert that to an int before sending or it will be ignored.  (Sending a string returns an error, but sending a float does not.)


## Prerequisites

This requires Python 3.  It uses Kenneth Reitz's excellent [requests](http://docs.python-requests.org/en/latest/) module, so you'll need to do:

    pip install requests

or something similar before using Qhue.  If you installed Qhue itself using pip, this shouldn't be necessary.


## Remote access

Starting with version 2, Qhue has a wrapper to support remote access: interacting with your Hue hub via the Philips servers when you are at a remote location, in the same way that a phone app might do when you are away from home.

For more information see [[README-remote.md]].

## Licence

This little snippet is distributed under the GPL v2. See the LICENSE file. (They spell it that way on the other side of the pond.) It comes with no warranties, express or implied, but just with the hope that it may be useful to someone.


## Contributing

Suggestions, patches, pull requests welcome.  There are many ways this could be improved.

If you can do so in a general way, without adding too many lines, that would be even better!  Brevity, as Polonius said, is the soul of wit.

Many thanks to John Bond, Sander Johansson, Travis Evans, David Coles, Chris Macklin, Andrea Jemmett, Martin Paulus, Ryan Turner, Matthew Clapp, Marcus Klaas de Vries and Richard Morrison, amongst others, for their contributions!

[Quentin Stafford-Fraser](http://quentinsf.com)


