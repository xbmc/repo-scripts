# Qhue

Qhue (pronounced 'Q') is an exceedingly thin Python wrapper for the Philips Hue API.

I wrote it because some of the other (excellent) frameworks out there weren't quite keeping up with developments in the API.  Because Qhue encodes almost none of the underlying models - it's really just a way of constructing URLs and HTTP calls - it should inherit any new API features automatically.  The aim of Qhue is not to create another Python API for the Hue system, so much as to turn the existing API *into* Python, with minimal interference.

## Understanding Qhue

Philips, to their credit, created a beautiful RESTful API for the Hue system.  It may not yet have all the features we'd like, but what does exist is very elegantly designed.  

You can (and should) read [the full documentation here](http://www.developers.meethue.com/philips-hue-api), but a quick summary is that resources like lights, scenes and so forth each have a URL, that might look like this:

    http://[myhub]/api/<username>/lights/1

You can read information about light 1 by doing an HTTP GET of this URL, and modify it by doing an HTTP PUT.

In the `qhue` module we have a Resource class, which represents *something that has a URL*. By calling an instance of this class, you'll make an HTTP request to the hub on that URL.  

It also has a Bridge class, which is a handy starting point for building Resources (and is itself a Resource).  If that seems a bit abstract, don't worry - all will be made clear below.

## Installing Qhue

That's easy.

    pip install qhue

You may want to check [GitHub](https://github.com/quentinsf/qhue) for the  latest version of the module, and of this documentation.  The very latest code is likely to be on [the 'develop' branch](https://github.com/quentinsf/qhue/tree/develop).

## Examples

Note: These examples assume you know the IP address of your bridge.  See [the 'Getting Started' section of the API docs](http://www.developers.meethue.com/documentation/getting-started) if you need help in finding it.  I've assigned mine a static address of 192.168.0.45, so that's what you'll see below.

They also assume you have experimented with the API before, and so have a user account set up on the bridge, and the username stored somewhere.  If not, see the section below entitled 'Creating a user'.

OK.  Now those preliminaries are out of the way...

First, let's create a Bridge, which will be your top-level Resource.

    # Connect to the bridge with a particular username
    from qhue import Bridge
    b = Bridge("192.168.0.45", username)

You can see the URL of any Resource:

    # This should give you something familiar from the API docs:
    print b.url

By requesting most other attributes of a Resource object, you will construct a new Resource with the attribute name added to the URL of the original one:

    lights = b.lights   # Creates a new Resource with its own URL
    print lights.url    # Should have '/lights' on the end

Now, these Resources are, at this stage, simply *references* to entities on the bridge: they haven't communicated with it yet.  To make an actual API call to the bridge, we simply *call* the Resource as if it were a function:

    # Let's actually call the API and print the results
    print lights()

Qhue takes the JSON that is returned by the API and turns it back into Python objects, typically a dictionary, so you can access its parts easily, for example:

    # Get the bridge's configuration info as a dict,
    # and print the ethernet MAC address
    print b.config()['mac']

Now, ideally, we'd like to be able to construct all of our URLs the same way, so we would refer to light 1 as `b.lights.1`, for example, but you can't use numbers as attribute names in Python.  Nor can you use variables.  As an alternative, therefore, you can use dictionary key syntax - for example, `b.lights[1]`.

    # Get information about light 1
    print b.lights[1]()

    # or, to do the same thing another way:
    print b['lights'][1]()

Alternatively, when you *call* a resource, you can give it arguments, which will be added to its URL when making the call:

    # This is the same as the last examples:
    print b('lights', 1)

So there are several ways to express the same thing, and you can choose the one which fits most elegantly into your code.

### Making changes

Now, to make a change to a value, you also call the resource, but you add keyword arguments to specify the properties you want to change.  You can change the brightness and hue of a light by setting properties on its *state*, for example:

    b.lights[1].state(bri=128, hue=9000)

and you can mix URL-constructing positional arguments with value-setting keyword arguments, if you like:

    # Positional arguments are added to the URL.
    # Keyword arguments change values.
    # So these are equivalent to the previous example:

    b.lights(1, 'state', bri=128, hue=9000)
    b('lights', 1, 'state', bri=128, hue=9000)

When you need to specify boolean true/false values, you should use the native Python True and False.

As a more complex example, if you want to set the brightness and colour temperature of a light in a given scene, you might use a call like this:

    bridge.scenes[scene].lightstates[light](on=True, bri=bri, ct=ct)

This covers most simple cases.  If you don't have any keyword arguments, the HTTP request will be a GET, and will tell you about the current status.  If you do have keyword arguments, it will be a PUT, and will change the current status.

Sometimes, though, you need to specify a POST or a DELETE, and you can do so with the special *http_method* argument, which will override the above rule:

    # Delete rule 1
    b('rules', 1, http_method='delete')

If you need to specify a keyword argument that would conflict with a Python keyword, such as `class`, simply append an underscore to it, like this:

    # Set property "class" to "Hallway".
    # The trailing underscore will automatically be removed
    # in the property name sent to the bridge.

    b.groups[19](class_='Hallway')

Finally, for certain operations, like schedules and rules, you'll want to know the 'address' of a resource, which is the absolute URL path - the bit after the IP address, or, more recently, the bit after the username.  You can get these with the `address` and `short_address` attributes:

    >>> b.groups[1].url
    'http://192.168.0.45/api/ac594202624a7211ac44615430a461/groups/1'
    >>> b.groups[1].address
    '/api/ac594202624a7211ac44615430a461/groups/1'
    >>> b.groups[1].short_address
    '/groups/1'

See the API docs for more information about when you need this.

And, at present, that's about it.


## A couple of hints:

* Some of the requests can return large amounts of information.  A handy way to make it more readable is to format it as YAML.  You may need to `pip install PyYAML`, then try the following:

        import yaml  
        print(yaml.safe_dump(bridge.groups(), indent=4))

* The Bridge generally returns items in a reasonably logical order. The order is not actually important, but if you wish to preserve it, then you probably *don't* want the JSON structures turned into Python dicts, since these do not generally preserve ordering.  When you construct the Bridge object, you can tell it to use another function to turn JSON dictionaries into Python structures, for example by specifying `object_pairs_hook=collections.OrderedDict`. This will give you OrderedDicts instead of dicts, which is a benefit in almost every way, except that any YAML output you create from it won't look so nice.

* If you're familiar with the Jupyter (iPython) Notebook system, it can be a fun way to explore the API.  See the [Qhue Playground example notebook](Qhue%20playground.ipynb).


## Creating a user

If you haven't used the API before, you'll need to create a user account on the bridge.

    from qhue import create_new_username
    username = create_new_username("192.168.0.45")

You'll get a prompt saying that the link button on the bridge needs to be pressed.  Go and press it, and you should get a generated username. You can now get a new Bridge object as shown in the examples above, passing this username as the second argument.

Please have a look at the examples directory for a method to store the username for future sessions.


## Usage notes

Please note that qhue won't do any local checking of any method calls or arguments - it just packages up what you give it and sends it to the bridge.

An important example of this is that the bridge is expecting integer values for things like colour temperature and brightness. If, say, you do a calculation for your colour which returns a float, you need to convert that to an int before sending or it will be ignored.  (Sending a string returns an error, but sending a float does not.)


## Prerequisites

This works under Python 2 and Python 3.  It uses Kenneth Reitz's excellent [requests](http://docs.python-requests.org/en/latest/) module, so you'll need to do:

    pip install requests

or something similar before using Qhue.  If you installed Qhue itself using pip, this shouldn't be necessary.


## Licence

This little snippet is distributed under the GPL v2. See the LICENSE file. (They spell it that way on the other side of the pond.) It comes with no warranties, express or implied, but just with the hope that it may be useful to someone.


## Contributing

Suggestions, patches, pull requests welcome.  There are many ways this could be improved.

If you can do so in a general way, without adding too many lines, that would be even better!  Brevity, as Polonius said, is the soul of wit.

Many thanks to David Coles, Chris Macklin, Andrea Jemmett, Martin Paulus, Ryan Turner, Matthew Clapp, Marcus Klaas de Vries and Richard Morrison, amongst others, for their contributions!

[Quentin Stafford-Fraser](http://quentinsf.com)


