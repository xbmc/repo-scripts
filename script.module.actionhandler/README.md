script.module.actionhandler

Module containing a decorator factory which allows assigning click/focus/action events to methods in your WindowXML class via decorators.


Usage:

1) import the module into the module containing your WindowXML class:

from ActionHandler import ActionHandler
ch = ActionHandler()


2) forward onClick / onAction / onfocus events to ActionHandler

    def onClick(self, control_id):
        ch.serve(control_id, self)

    def onFocus(self, control_id):
        ch.serve_focus(control_id, self)

    def onAction(self, action):
        ch.serve_action(action, self.getFocusId(), self)

3) you can now use decorators to map events to methods

Examples:

- for click events:

    @ch.click(1000)
    @ch.click(2000)
    def some_method(self):
        ...

    @ch.click([1000,2000])
    def some_method(self):
        ...


- for focus events:

    @ch.focus(1000)
    def some_method(self):
        ...


- for action events:

    @ch.action("number9", "*")
    def some_method(self):
        ...

    @ch.action("contextmenu", 150)
    def some_method(self):
        ...

--> first parameter is name of action id,
    second parameter is id of button ("*" = all controls)



To save some boilerplate when dealing with controls and listitems, this module will also set some attributes for the Window class you use it for:

self.control: actual focused control
self.listitem: actual focused listitem (in case a list is focused)

 These attributes get updated everytime one of the events takes place and can be used within the decorated methods.
