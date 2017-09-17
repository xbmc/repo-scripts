class Event:
    """Event class that implements .NET like event handling"""

    def __init__(self):
        """Initialises a new Event Class object"""

        self.__eventHandlers = set()

    def __add_event_handler(self, handler):
        """Adds an event handler to the collection of events

        Arguments:
        handler : method - The event handler to add

        Returns:
        the current event object.

        When the event is triggered, it will
        be called with the *args and **kwargs arguments.

        """

        self.__eventHandlers.add(handler)
        return self

    def __remove_event_handler(self, handler):
        """Removes an event handler from the event handler collection

        Arguments:
        handler : method - The handler that should be removed

        Returns:
        the current event object.

        """
        try:
            self.__eventHandlers.remove(handler)
        except:
            raise ValueError("This event is not handled by the event handler (handler).")
        return self

    def __trigger_event(self, *args, **kwargs):
        """Triggers all event handlers with the given arguments:

        Arguments:
        args   : list - List of arguments

        Keyword Arguments:
        kwargs : list - List of keyword arguments

        """

        for handler in self.__eventHandlers:
            handler(*args, **kwargs)

    def __get_number_of_handlers(self):
        """Returns the number of registered handlers"""

        return len(self.__eventHandlers)

    # define the short-hand methods. Only these are needed for the rest of the code
    __iadd__ = __add_event_handler  #: Implements the Event += EventHandler
    __isub__ = __remove_event_handler  #: Implements for Event -= EventHandler
    __call__ = __trigger_event  #: Trigger the Event by calling it.
    __len__ = __get_number_of_handlers  #: Implements len(Event)
