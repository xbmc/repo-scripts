"""
Pure-Python binding for D-Bus <https://www.freedesktop.org/wiki/Software/dbus/>,
built around libdbus <https://dbus.freedesktop.org/doc/api/html/index.html>.

This Python binding supports hooking into event loops via Python’s standard
asyncio module.
"""
#+
# Copyright 2017-2020 Lawrence D'Oliveiro <ldo@geek-central.gen.nz>.
# Licensed under the GNU Lesser General Public License v2.1 or later.
#-

import os
import builtins
import operator
import array
import enum
import ctypes as ct
from weakref import \
    ref as weak_ref, \
    WeakValueDictionary
import threading
import io
import atexit
import asyncio
from xml.etree import \
    ElementTree as XMLElementTree
from xml.sax.saxutils import \
    quoteattr as quote_xml_attr

dbus = ct.cdll.LoadLibrary("libdbus-1.so.3")

class DBUS :
    "useful definitions adapted from the D-Bus includes. You will need to use the" \
    " constants, but apart from that, see the more Pythonic wrappers defined outside" \
    " this class in preference to accessing low-level structures directly."

    # General ctypes gotcha: when passing addresses of ctypes-constructed objects
    # to routine calls, do not construct the objects directly in the call. Otherwise
    # the refcount goes to 0 before the routine is actually entered, and the object
    # can get prematurely disposed. Always store the object reference into a local
    # variable, and pass the value of the variable instead.

    # from dbus-protocol.h:
    # Message byte order
    LITTLE_ENDIAN = 'l'
    BIG_ENDIAN = 'B'

    # Protocol version.
    MAJOR_PROTOCOL_VERSION = 1

    # Type code that is never equal to a legitimate type code
    TYPE_INVALID = 0

    # Primitive types
    TYPE_BYTE = ord('y') # 8-bit unsigned integer
    TYPE_BOOLEAN = ord('b') # boolean
    TYPE_INT16 = ord('n') # 16-bit signed integer
    TYPE_UINT16 = ord('q') # 16-bit unsigned integer
    TYPE_INT32 = ord('i') # 32-bit signed integer
    TYPE_UINT32 = ord('u') # 32-bit unsigned integer
    TYPE_INT64 = ord('x') # 64-bit signed integer
    TYPE_UINT64 = ord('t') # 64-bit unsigned integer
    TYPE_DOUBLE = ord('d') # 8-byte double in IEEE 754 format
    TYPE_STRING = ord('s') # UTF-8 encoded, nul-terminated Unicode string
    TYPE_OBJECT_PATH = ord('o') # D-Bus object path
    TYPE_SIGNATURE = ord('g') # D-Bus type signature
    TYPE_UNIX_FD = ord('h') # unix file descriptor

    basic_to_ctypes = \
        { # ctypes objects suitable for holding values of D-Bus types
            TYPE_BYTE : ct.c_ubyte,
            TYPE_BOOLEAN : ct.c_ubyte,
            TYPE_INT16 : ct.c_short,
            TYPE_UINT16 : ct.c_ushort,
            TYPE_INT32 : ct.c_int,
            TYPE_UINT32 : ct.c_uint,
            TYPE_INT64 : ct.c_longlong,
            TYPE_UINT64 : ct.c_ulonglong,
            TYPE_DOUBLE : ct.c_double,
            TYPE_STRING : ct.c_char_p,
            TYPE_OBJECT_PATH : ct.c_char_p,
            TYPE_SIGNATURE : ct.c_char_p,
            TYPE_UNIX_FD : ct.c_int,
        }

    def int_subtype(i, bits, signed) :
        "returns integer i after checking that it fits in the given number of bits."
        if not isinstance(i, int) :
            raise TypeError("value is not int: %s" % repr(i))
        #end if
        if signed :
            lo = - 1 << bits - 1
            hi = (1 << bits - 1) - 1
        else :
            lo = 0
            hi = (1 << bits) - 1
        #end if
        if i < lo or i > hi :
            raise ValueError \
              (
                "%d not in range of %s %d-bit value" % (i, ("unsigned", "signed")[signed], bits)
              )
        #end if
        return \
            i
    #end int_subtype

    subtype_boolean = lambda i : DBUS.int_subtype(i, 1, False)
    subtype_byte = lambda i : DBUS.int_subtype(i, 8, False)
    subtype_int16 = lambda i : DBUS.int_subtype(i, 16, True)
    subtype_uint16 = lambda i : DBUS.int_subtype(i, 16, False)
    subtype_int32 = lambda i : DBUS.int_subtype(i, 32, True)
    subtype_uint32 = lambda i : DBUS.int_subtype(i, 32, False)
    subtype_int64 = lambda i : DBUS.int_subtype(i, 64, True)
    subtype_uint64 = lambda i : DBUS.int_subtype(i, 64, False)

    int_convert = \
        { # range checks for the various D-Bus integer types
            TYPE_BOOLEAN : subtype_boolean,
            TYPE_BYTE : subtype_byte,
            TYPE_INT16 : subtype_int16,
            TYPE_UINT16 : subtype_uint16,
            TYPE_INT32 : subtype_int32,
            TYPE_UINT32 : subtype_uint32,
            TYPE_INT64 : subtype_int64,
            TYPE_UINT64 : subtype_uint64,
        }

    # subclasses for distinguishing various special kinds of D-Bus values:
    class ObjectPath(str) :
        "an object path string."

        def __repr__(self) :
            return \
                "%s(%s)" % (self.__class__.__name__, super().__repr__())
        #end __repr__

    #end ObjectPath

    class Signature(str) :
        "a type-signature string."

        def __repr__(self) :
            return \
                "%s(%s)" % (self.__class__.__name__, super().__repr__())
        #end __repr__

    #end Signature

    class UnixFD(int) :
        "a file-descriptor integer."

        def __repr__(self) :
            return \
                "%s(%s)" % (self.__class__.__name__, super().__repr__())
        #end __repr__

    #end UnixFD

    basic_subclasses = \
        {
            TYPE_BOOLEAN : bool,
            TYPE_OBJECT_PATH : ObjectPath,
            TYPE_SIGNATURE : Signature,
            TYPE_UNIX_FD : UnixFD,
        }

    # Compound types
    TYPE_ARRAY = ord('a') # D-Bus array type
    TYPE_VARIANT = ord('v') # D-Bus variant type

    TYPE_STRUCT = ord('r') # a struct; however, type signatures use STRUCT_BEGIN/END_CHAR
    TYPE_DICT_ENTRY = ord('e') # a dict entry; however, type signatures use DICT_ENTRY_BEGIN/END_CHAR
    NUMBER_OF_TYPES = 16 # does not include TYPE_INVALID or STRUCT/DICT_ENTRY_BEGIN/END_CHAR

    # characters other than typecodes that appear in type signatures
    STRUCT_BEGIN_CHAR = ord('(') # start of a struct type in a type signature
    STRUCT_END_CHAR = ord(')') # end of a struct type in a type signature
    DICT_ENTRY_BEGIN_CHAR = ord('{') # start of a dict entry type in a type signature
    DICT_ENTRY_END_CHAR = ord('}') # end of a dict entry type in a type signature

    MAXIMUM_NAME_LENGTH = 255 # max length in bytes of a bus name, interface or member (object paths are unlimited)

    MAXIMUM_SIGNATURE_LENGTH = 255 # fits in a byte

    MAXIMUM_MATCH_RULE_LENGTH = 1024

    MAXIMUM_MATCH_RULE_ARG_NUMBER = 63

    MAXIMUM_ARRAY_LENGTH = 67108864 # 2 * 26
    MAXIMUM_ARRAY_LENGTH_BITS = 26 # to store the max array size

    MAXIMUM_MESSAGE_LENGTH = MAXIMUM_ARRAY_LENGTH * 2
    MAXIMUM_MESSAGE_LENGTH_BITS = 27

    MAXIMUM_MESSAGE_UNIX_FDS = MAXIMUM_MESSAGE_LENGTH // 4 # FDs are at least 32 bits
    MAXIMUM_MESSAGE_UNIX_FDS_BITS = MAXIMUM_MESSAGE_LENGTH_BITS - 2

    MAXIMUM_TYPE_RECURSION_DEPTH = 32

    # Types of message

    MESSAGE_TYPE_INVALID = 0 # never a valid message type
    MESSAGE_TYPE_METHOD_CALL = 1
    MESSAGE_TYPE_METHOD_RETURN = 2
    MESSAGE_TYPE_ERROR = 3
    MESSAGE_TYPE_SIGNAL = 4

    NUM_MESSAGE_TYPES = 5

    # Header flags

    HEADER_FLAG_NO_REPLY_EXPECTED = 0x1
    HEADER_FLAG_NO_AUTO_START = 0x2
    HEADER_FLAG_ALLOW_INTERACTIVE_AUTHORIZATION = 0x4

    # Header fields

    HEADER_FIELD_INVALID = 0
    HEADER_FIELD_PATH = 1
    HEADER_FIELD_INTERFACE = 2
    HEADER_FIELD_MEMBER = 3
    HEADER_FIELD_ERROR_NAME = 4
    HEADER_FIELD_REPLY_SERIAL = 5
    HEADER_FIELD_DESTINATION = 6
    HEADER_FIELD_SENDER = 7
    HEADER_FIELD_SIGNATURE = 8
    HEADER_FIELD_UNIX_FDS = 9

    HEADER_FIELD_LAST = HEADER_FIELD_UNIX_FDS

    HEADER_SIGNATURE = bytes \
      ((
        TYPE_BYTE,
        TYPE_BYTE,
        TYPE_BYTE,
        TYPE_BYTE,
        TYPE_UINT32,
        TYPE_UINT32,
        TYPE_ARRAY,
        STRUCT_BEGIN_CHAR,
        TYPE_BYTE,
        TYPE_VARIANT,
        STRUCT_END_CHAR,
      ))
    MINIMUM_HEADER_SIZE = 16 # smallest header size that can occur (missing required fields, though)

    # Errors
    ERROR_FAILED = "org.freedesktop.DBus.Error.Failed" # generic error
    ERROR_NO_MEMORY = "org.freedesktop.DBus.Error.NoMemory"
    ERROR_SERVICE_UNKNOWN = "org.freedesktop.DBus.Error.ServiceUnknown"
    ERROR_NAME_HAS_NO_OWNER = "org.freedesktop.DBus.Error.NameHasNoOwner"
    ERROR_NO_REPLY = "org.freedesktop.DBus.Error.NoReply"
    ERROR_IO_ERROR = "org.freedesktop.DBus.Error.IOError"
    ERROR_BAD_ADDRESS = "org.freedesktop.DBus.Error.BadAddress"
    ERROR_NOT_SUPPORTED = "org.freedesktop.DBus.Error.NotSupported"
    ERROR_LIMITS_EXCEEDED = "org.freedesktop.DBus.Error.LimitsExceeded"
    ERROR_ACCESS_DENIED = "org.freedesktop.DBus.Error.AccessDenied"
    ERROR_AUTH_FAILED = "org.freedesktop.DBus.Error.AuthFailed"
    ERROR_NO_SERVER = "org.freedesktop.DBus.Error.NoServer"
    ERROR_TIMEOUT = "org.freedesktop.DBus.Error.Timeout"
    ERROR_NO_NETWORK = "org.freedesktop.DBus.Error.NoNetwork"
    ERROR_ADDRESS_IN_USE = "org.freedesktop.DBus.Error.AddressInUse"
    ERROR_DISCONNECTED = "org.freedesktop.DBus.Error.Disconnected"
    ERROR_INVALID_ARGS = "org.freedesktop.DBus.Error.InvalidArgs"
    ERROR_FILE_NOT_FOUND = "org.freedesktop.DBus.Error.FileNotFound"
    ERROR_FILE_EXISTS = "org.freedesktop.DBus.Error.FileExists"
    ERROR_UNKNOWN_METHOD = "org.freedesktop.DBus.Error.UnknownMethod"
    ERROR_UNKNOWN_OBJECT = "org.freedesktop.DBus.Error.UnknownObject"
    ERROR_UNKNOWN_INTERFACE = "org.freedesktop.DBus.Error.UnknownInterface"
    ERROR_UNKNOWN_PROPERTY = "org.freedesktop.DBus.Error.UnknownProperty"
    ERROR_PROPERTY_READ_ONLY = "org.freedesktop.DBus.Error.PropertyReadOnly"
    ERROR_TIMED_OUT = "org.freedesktop.DBus.Error.TimedOut"
    ERROR_MATCH_RULE_NOT_FOUND = "org.freedesktop.DBus.Error.MatchRuleNotFound"
    ERROR_MATCH_RULE_INVALID = "org.freedesktop.DBus.Error.MatchRuleInvalid"
    ERROR_SPAWN_EXEC_FAILED = "org.freedesktop.DBus.Error.Spawn.ExecFailed"
    ERROR_SPAWN_FORK_FAILED = "org.freedesktop.DBus.Error.Spawn.ForkFailed"
    ERROR_SPAWN_CHILD_EXITED = "org.freedesktop.DBus.Error.Spawn.ChildExited"
    ERROR_SPAWN_CHILD_SIGNALED = "org.freedesktop.DBus.Error.Spawn.ChildSignaled"
    ERROR_SPAWN_FAILED = "org.freedesktop.DBus.Error.Spawn.Failed"
    ERROR_SPAWN_SETUP_FAILED = "org.freedesktop.DBus.Error.Spawn.FailedToSetup"
    ERROR_SPAWN_CONFIG_INVALID = "org.freedesktop.DBus.Error.Spawn.ConfigInvalid"
    ERROR_SPAWN_SERVICE_INVALID = "org.freedesktop.DBus.Error.Spawn.ServiceNotValid"
    ERROR_SPAWN_SERVICE_NOT_FOUND = "org.freedesktop.DBus.Error.Spawn.ServiceNotFound"
    ERROR_SPAWN_PERMISSIONS_INVALID = "org.freedesktop.DBus.Error.Spawn.PermissionsInvalid"
    ERROR_SPAWN_FILE_INVALID = "org.freedesktop.DBus.Error.Spawn.FileInvalid"
    ERROR_SPAWN_NO_MEMORY = "org.freedesktop.DBus.Error.Spawn.NoMemory"
    ERROR_UNIX_PROCESS_ID_UNKNOWN = "org.freedesktop.DBus.Error.UnixProcessIdUnknown"
    ERROR_INVALID_SIGNATURE = "org.freedesktop.DBus.Error.InvalidSignature"
    ERROR_INVALID_FILE_CONTENT = "org.freedesktop.DBus.Error.InvalidFileContent"
    ERROR_SELINUX_SECURITY_CONTEXT_UNKNOWN = "org.freedesktop.DBus.Error.SELinuxSecurityContextUnknown"
    ERROR_ADT_AUDIT_DATA_UNKNOWN = "org.freedesktop.DBus.Error.AdtAuditDataUnknown"
    ERROR_OBJECT_PATH_IN_USE = "org.freedesktop.DBus.Error.ObjectPathInUse"
    ERROR_INCONSISTENT_MESSAGE = "org.freedesktop.DBus.Error.InconsistentMessage"
    ERROR_INTERACTIVE_AUTHORIZATION_REQUIRED = "org.freedesktop.DBus.Error.InteractiveAuthorizationRequired"

    # XML introspection format
    INTROSPECT_1_0_XML_NAMESPACE = "http://www.freedesktop.org/standards/dbus"
    INTROSPECT_1_0_XML_PUBLIC_IDENTIFIER = "-//freedesktop//DTD D-BUS Object Introspection 1.0//EN"
    INTROSPECT_1_0_XML_SYSTEM_IDENTIFIER = "http://www.freedesktop.org/standards/dbus/1.0/introspect.dtd"
    INTROSPECT_1_0_XML_DOCTYPE_DECL_NODE = \
        (
            "<!DOCTYPE node PUBLIC \""
        +
            INTROSPECT_1_0_XML_PUBLIC_IDENTIFIER
        +
            "\"\n\"" + INTROSPECT_1_0_XML_SYSTEM_IDENTIFIER
        +
            "\">\n"
        )

    # from dbus-shared.h:
    # well-known bus types
    BusType = ct.c_uint
    BUS_SESSION = 0
    BUS_SYSTEM = 1
    BUS_STARTER = 2

    # results that a message handler can return
    BusHandlerResult = ct.c_uint
    HANDLER_RESULT_HANDLED = 0 # no need to try more handlers
    HANDLER_RESULT_NOT_YET_HANDLED = 1 # see if other handlers want it
    HANDLER_RESULT_NEED_MEMORY = 2 # try again later with more memory

    # Bus names
    SERVICE_DBUS = "org.freedesktop.DBus" # used to talk to the bus itself

    # Paths
    PATH_DBUS = "/org/freedesktop/DBus" # object path used to talk to the bus itself
    PATH_LOCAL = "/org/freedesktop/DBus/Local" # path used in local/in-process-generated messages

    # Interfaces
    INTERFACE_DBUS = "org.freedesktop.DBus" # interface exported by the object with SERVICE_DBUS and PATH_DBUS
    INTERFACE_MONITORING = "org.freedesktop.DBus.Monitoring" # monitoring interface exported by the dbus-daemon
    INTERFACE_VERBOSE = "org.freedesktop.DBus.Verbose" # verbose interface exported by the dbus-daemon
    INTERFACE_INTROSPECTABLE = "org.freedesktop.DBus.Introspectable" # interface supported by introspectable objects
    INTERFACE_PROPERTIES = "org.freedesktop.DBus.Properties" # interface supported by objects with properties
    INTERFACE_PEER = "org.freedesktop.DBus.Peer" # interface supported by most dbus peers
    INTERFACE_LOCAL = "org.freedesktop.DBus.Local" # methods can only be invoked locally

    # Owner flags for request_name
    NAME_FLAG_ALLOW_REPLACEMENT = 0x1
    NAME_FLAG_REPLACE_EXISTING = 0x2
    NAME_FLAG_DO_NOT_QUEUE = 0x4

    # Replies to request for a name
    REQUEST_NAME_REPLY_PRIMARY_OWNER = 1
    REQUEST_NAME_REPLY_IN_QUEUE = 2
    REQUEST_NAME_REPLY_EXISTS = 3
    REQUEST_NAME_REPLY_ALREADY_OWNER = 4

    # Replies to releasing a name
    RELEASE_NAME_REPLY_RELEASED = 1
    RELEASE_NAME_REPLY_NON_EXISTENT = 2
    RELEASE_NAME_REPLY_NOT_OWNER = 3

    # Replies to service starts
    START_REPLY_SUCCESS = 1
    START_REPLY_ALREADY_RUNNING = 2

    # from dbus-types.h:
    bool_t = ct.c_uint

    # from dbus-memory.h:
    FreeFunction = ct.CFUNCTYPE(None, ct.c_void_p)

    # from dbus-connection.h:
    HandlerResult = ct.c_uint

    class Error(ct.Structure) :
        _fields_ = \
            [
                ("name", ct.c_char_p),
                ("message", ct.c_char_p),
                ("padding", 2 * ct.c_void_p),
            ]
    #end Error
    ErrorPtr = ct.POINTER(Error)

    WatchFlags = ct.c_uint
    WATCH_READABLE = 1 << 0
    WATCH_WRITABLE = 1 << 1
    WATCH_ERROR = 1 << 2
    WATCH_HANGUP = 1 << 3

    DispatchStatus = ct.c_uint
    DISPATCH_DATA_REMAINS = 0 # more data available
    DISPATCH_COMPLETE = 1 # all available data has been processed
    DISPATCH_NEED_MEMORY = 2 # not enough memory to continue

    AddWatchFunction = ct.CFUNCTYPE(bool_t, ct.c_void_p, ct.c_void_p)
      # add_watch(DBusWatch, user_data) returns success/failure
    WatchToggledFunction = ct.CFUNCTYPE(None, ct.c_void_p, ct.c_void_p)
      # watch_toggled(DBusWatch, user_data)
    RemoveWatchFunction = ct.CFUNCTYPE(None, ct.c_void_p, ct.c_void_p)
      # remove_watch(DBusWatch, user_data)

    AddTimeoutFunction = ct.CFUNCTYPE(bool_t, ct.c_void_p, ct.c_void_p)
      # add_timeout(DBusTimeout, user_data) returns success/failure
    TimeoutToggledFunction = ct.CFUNCTYPE(None, ct.c_void_p, ct.c_void_p)
      # timeout_toggled(DBusTimeout, user_data)
    RemoveTimeoutFunction = ct.CFUNCTYPE(None, ct.c_void_p, ct.c_void_p)
      # remove_timeout(DBusTimeout, user_data)

    DispatchStatusFunction = ct.CFUNCTYPE(None, ct.c_void_p, ct.POINTER(DispatchStatus), ct.c_void_p)
      # dispatch_status(DBusConnection, DBusDispatchStatus, user_data)
    WakeupMainFunction = ct.CFUNCTYPE(None, ct.c_void_p)
      # wakeup_main(user_data)

    AllowUnixUserFunction = ct.CFUNCTYPE(bool_t, ct.c_void_p, ct.c_ulong, ct.c_void_p)
      # allow_unix_user(DBusConnection, uid, user_data) returns success/failure
    AllowWindowsUserFunction = ct.CFUNCTYPE(bool_t, ct.c_void_p, ct.c_void_p, ct.c_void_p)
      # allow_windows_user(DBusConnection, user_sid, user_data)returns success/failure

    PendingCallNotifyFunction = ct.CFUNCTYPE(None, ct.c_void_p, ct.c_void_p)
      # notify(DBusPendingCall, user_data)

    HandleMessageFunction = ct.CFUNCTYPE(HandlerResult, ct.c_void_p, ct.c_void_p, ct.c_void_p)
      # handle_message(DBusConnection, DBusMessage, user_data)

    ObjectPathUnregisterFunction = ct.CFUNCTYPE(None, ct.c_void_p, ct.c_void_p)
      # unregister(DBusConnection, user_data)
    ObjectPathMessageFunction = ct.CFUNCTYPE(HandlerResult, ct.c_void_p, ct.c_void_p, ct.c_void_p)
      # handle_message(DBusConnection, DBusMessage, user_data)

    class ObjectPathVTable(ct.Structure) :
        pass
    #end ObjectPathVTable
    ObjectPathVTable._fields_ = \
        [
            ("unregister_function", ObjectPathUnregisterFunction),
            ("message_function", ObjectPathMessageFunction),
            ("internal_pad1", ct.CFUNCTYPE(None, ct.c_void_p)),
            ("internal_pad2", ct.CFUNCTYPE(None, ct.c_void_p)),
            ("internal_pad3", ct.CFUNCTYPE(None, ct.c_void_p)),
            ("internal_pad4", ct.CFUNCTYPE(None, ct.c_void_p)),
        ]
    ObjectPathVTablePtr = ct.POINTER(ObjectPathVTable)

    # from dbus-pending-call.h:
    TIMEOUT_INFINITE = 0x7fffffff
    TIMEOUT_USE_DEFAULT = -1

    # from dbus-message.h:
    class MessageIter(ct.Structure) :
        "contains no public fields."
        _fields_ = \
            [
                ("dummy1", ct.c_void_p),
                ("dummy2", ct.c_void_p),
                ("dummy3", ct.c_uint),
                ("dummy4", ct.c_int),
                ("dummy5", ct.c_int),
                ("dummy6", ct.c_int),
                ("dummy7", ct.c_int),
                ("dummy8", ct.c_int),
                ("dummy9", ct.c_int),
                ("dummy10", ct.c_int),
                ("dummy11", ct.c_int),
                ("pad1", ct.c_int),
                ("pad2", ct.c_void_p),
                ("pad3", ct.c_void_p),
            ]
    #end MessageIter
    MessageIterPtr = ct.POINTER(MessageIter)

    # from dbus-server.h:
    NewConnectionFunction = ct.CFUNCTYPE(None, ct.c_void_p, ct.c_void_p, ct.c_void_p)
      # new_connection(DBusServer, DBusConnection, user_data)

    # from dbus-signature.h:
    class SignatureIter(ct.Structure) :
        "contains no public fields."
        _fields_ = \
            [
                ("dummy1", ct.c_void_p),
                ("dummy2", ct.c_void_p),
                ("dummy8", ct.c_uint),
                ("dummy12", ct.c_int),
                ("dummy17", ct.c_int),
            ]
    #end SignatureIter
    SignatureIterPtr = ct.POINTER(SignatureIter)

#end DBUS

class DBUSX:
    "additional definitions not part of the official interfaces"

    DEFAULT_TIMEOUT = 25 # seconds, from dbus-connection-internal.h in libdbus source

    # For reference implementation for how to connect to daemon,
    # see libdbus sources, dbus/dbus-bus.c (internal_bus_get routine
    # and stuff that it calls)

    # environment variables used to find addresses of bus daemons
    SESSION_BUS_ADDRESS_VAR = "DBUS_SESSION_BUS_ADDRESS"
    SYSTEM_BUS_ADDRESS_VAR = "DBUS_SYSTEM_BUS_ADDRESS"
    STARTER_BUS_ADDRESS_VAR = "DBUS_STARTER_ADDRESS"
    STARTER_BUS_ADDRESS_TYPE = "DBUS_STARTER_BUS_TYPE"

    # values for value of STARTER_BUS_ADDRESS_TYPE
    # If cannot determine type, then default to session bus
    BUS_TYPE_SESSION = "session"
    BUS_TYPE_SYSTEM = "system"

    SYSTEM_BUS_ADDRESS = "unix:path=/var/run/dbus/system_bus_socket"
      # default system bus daemon address if value of SYSTEM_BUS_ADDRESS_VAR is not defined
    SESSION_BUS_ADDRESS = "autolaunch:"
      # default session bus daemon address if value of SESSION_BUS_ADDRESS_VAR is not defined

    INTERFACE_OBJECT_MANAGER = "org.freedesktop.DBus.ObjectManager"
      # no symbolic name for this in standard headers as yet

#end DBUSX

#+
# Useful stuff
#-

def _wderef(w_self, parent) :
    self = w_self()
    assert self  is not None, "%s has gone away" % parent
    return \
        self
#end _wderef

def call_async(func, funcargs = (), timeout = None, abort = None, loop = None) :
    "invokes func on a separate temporary thread and returns a Future that" \
    " can be used to wait for its completion and obtain its result. If timeout" \
    " is not None, then waiters on the Future will get a TimeoutError exception" \
    " if the function has not completed execution after that number of seconds." \
    " This allows easy invocation of blocking I/O functions in an asyncio-" \
    "compatible fashion. But note that the operation cannot be cancelled" \
    " if the timeout elapses; instead, you can specify an abort callback" \
    " which will be invoked with whatever result is eventually returned from" \
    " func."

    if loop  is None :
        loop = asyncio.get_event_loop()
    #end if

    timeout_task = None

    def func_done(ref_awaiting, result) :
        awaiting = ref_awaiting()
        if awaiting  is not None :
            if not awaiting.done() :
                awaiting.set_result(result)
                if timeout_task  is not None :
                    timeout_task.cancel()
                #end if
            else :
                if abort  is not None :
                    abort(result)
                #end if
            #end if
        #end if
    #end func_done

    def do_func_timedout(ref_awaiting) :
        awaiting = ref_awaiting()
        if awaiting  is not None :
            if not awaiting.done() :
                awaiting.set_exception(TimeoutError())
                # Python doesn’t give me any (easy) way to cancel the thread running the
                # do_func() call, so just let it run to completion, whereupon func_done()
                # will get rid of the result. Even if I could delete the thread, can I be sure
                # that would clean up memory and OS/library resources properly?
            #end if
        #end if
    #end do_func_timedout

    def do_func(ref_awaiting) :
        # makes the blocking call on a separate thread.
        result = func(*funcargs)
        # A Future is not itself threadsafe, but I can thread-safely
        # run a callback on the main thread to set it.
        loop.call_soon_threadsafe(func_done, ref_awaiting, result)
    #end do_func

#begin call_async
    awaiting = loop.create_future()
    ref_awaiting = weak_ref(awaiting)
      # weak ref to avoid circular refs with loop
    subthread = threading.Thread(target = do_func, args = (ref_awaiting,))
    subthread.start()
    if timeout  is not None :
        timeout_task = loop.call_later(timeout, do_func_timedout, ref_awaiting)
    #end if
    return \
        awaiting
#end call_async

#+
# Higher-level interface to type system
#-

class TYPE(enum.Enum) :
    "D-Bus type codes wrapped up in an enumeration."

    BYTE = ord('y') # 8-bit unsigned integer
    BOOLEAN = ord('b') # boolean
    INT16 = ord('n') # 16-bit signed integer
    UINT16 = ord('q') # 16-bit unsigned integer
    INT32 = ord('i') # 32-bit signed integer
    UINT32 = ord('u') # 32-bit unsigned integer
    INT64 = ord('x') # 64-bit signed integer
    UINT64 = ord('t') # 64-bit unsigned integer
    DOUBLE = ord('d') # 8-byte double in IEEE 754 format
    STRING = ord('s') # UTF-8 encoded, nul-terminated Unicode string
    OBJECT_PATH = ord('o') # D-Bus object path
    SIGNATURE = ord('g') # D-Bus type signature
    UNIX_FD = ord('h') # unix file descriptor

    ARRAY = ord('a') # array of elements all of same type, or possibly dict
    STRUCT = ord('r') # sequence of elements of arbitrary types
    VARIANT = ord('v') # a single element of dynamic type

    @property
    def is_basic(self) :
        "does this code represent a basic (non-container) type."
        return \
            self.value in DBUS.basic_to_ctypes
    #end is_basic

#end TYPE

class Type :
    "base class for all Types. The “signature” property returns the fully-encoded" \
    " signature string for the entire Type."

    __slots__ = ("code",)

    def __init__(self, code) :
        if not isinstance(code, TYPE) :
            raise TypeError("only TYPE.xxx values allowed")
        #end if
        self.code = code
    #end __init__

    @property
    def signature(self) :
        raise NotImplementedError("subclass forgot to override signature property")
    #end signature

    def __eq__(t1, t2) :
        raise NotImplementedError("subclass forgot to override __eq__ method")
    #end __eq__

    def validate(self, val) :
        "returns val if it is an acceptable value of this Type, else raises" \
        " TypeError or ValueError."
        raise NotImplementedError("subclass forgot to override validate method")
    #end validate

    def __repr__(self) :
        return \
            "%s(sig = %s)" % (type(self).__name__, repr(self.signature))
    #end __repr__

#end Type

class BasicType(Type) :
    "a basic (non-container) type."

    __slots__ = ()

    def __init__(self, code) :
        if not isinstance(code, TYPE) or not code.is_basic :
            raise TypeError("only basic TYPE.xxx values allowed")
        #end if
        super().__init__(code)
    #end __init__

    def __repr__(self) :
        return \
            "%s(%s)" % (type(self).__name__, repr(self.code))
    #end __repr__

    @property
    def signature(self) :
        return \
            chr(self.code.value)
    #end signature

    def __eq__(t1, t2) :
        return \
            isinstance(t2, BasicType) and t1.code == t2.code
    #end __eq__

    def validate(self, val) :
        if self.code.value in DBUS.int_convert :
            val = DBUS.int_convert[self.code.value](val)
        elif self.code == TYPE.DOUBLE :
            if not isinstance(val, float) :
                raise TypeError("expecting a float, not %s: %s" % (type(val).__name__, repr(val)))
            #end if
        elif self.code == TYPE.UNIX_FD :
            val = DBUS.subtype_uint32(val)
        elif DBUS.basic_to_ctypes[self.code.value] == ct.c_char_p :
            if not isinstance(val, str) :
                raise TypeError("expecting a string, not %s: %s" % (type(val).__name__, repr(val)))
            #end if
        else :
            raise RuntimeError("unknown basic type %s" % repr(self.code))
        #end if
        return \
            val
    #end validate

#end BasicType

class VariantType(Type) :
    "the variant type--a single element of a type determined at run-time."

    def __init__(self) :
        super().__init__(TYPE.VARIANT)
    #end __init__

    @property
    def signature(self) :
        return \
            chr(TYPE.VARIANT.value)
    #end signature

    def __repr__(self) :
        return \
            "%s()" % type(self).__name__
    #end __repr__

    def __eq__(t1, t2) :
        return \
            isinstance(t2, VariantType)
    #end __eq__

    def validate(self, val) :
        if not isinstance(val, (tuple, list)) or len(val) != 2 :
            raise ValueError("expecting a (type, value) pair")
        #end if
        valtype, val = val
        valtype = parse_single_signature(valtype)
        return \
            (valtype, valtype.validate(val))
    #end validate

#end VariantType

class StructType(Type) :
    "a sequence of one or more arbitrary types (empty structs are not allowed)."

    __slots__ = ("elttypes",)

    def __init__(self, *types) :
        if len(types) == 0 :
            raise TypeError("must have at least one element type")
        #end if
        if not all(isinstance(t, Type) for t in types) :
            raise TypeError("struct elements must be Types")
        #end if
        super().__init__(TYPE.STRUCT)
        self.elttypes = tuple(types)
    #end __init__

    def __repr__(self) :
        return \
            "%s(%s)" % (type(self).__name__, repr(self.elttypes))
    #end __repr__

    @property
    def signature(self) :
        return \
            "(%s)" % "".join(t.signature for t in self.elttypes)
    #end signature

    def __eq__(t1, t2) :
        return \
            (
                    isinstance(t2, StructType)
                and
                    len(t1.elttypes) == len(t2.elttypes)
                and
                    all(e1 == e2 for e1, e2 in zip(t1.elttypes, t2.elttypes))
            )
    #end __eq__

    def validate(self, val) :
        if not isinstance(val, (tuple, list)) or len(val) != len(self.elttypes) :
            raise TypeError \
              (
                "need a list or tuple of %d elements, not %s" % (len(self.elttypes), repr(val))
              )
        #end if
        return \
            type(val)(elttype.validate(elt) for elttype, elt in zip(self.elttypes, val))
    #end validate

#end StructType

class ArrayType(Type) :
    "an array of zero or more elements all of the same type."

    __slots__ = ("elttype",)

    def __init__(self, elttype) :
        if not isinstance(elttype, Type) :
            raise TypeError("invalid array element type")
        #end if
        super().__init__(TYPE.ARRAY)
        self.elttype = elttype
    #end __init__

    def __repr__(self) :
        return \
            "%s[%s]" % (type(self).__name__, repr(self.elttype))
    #end __repr__

    @property
    def signature(self) :
        return \
            chr(TYPE.ARRAY.value) + self.elttype.signature
    #end signature

    def __eq__(t1, t2) :
        return \
            isinstance(t2, ArrayType) and t1.elttype == t2.elttype
    #end __eq__

    def validate(self, val) :
        if not isinstance(val, (tuple, list)) :
            raise TypeError("need a tuple or list, not %s: %s" % (type(val).__name__, repr(val)))
        #end if
        return \
            type(val)(self.elttype.validate(elt) for elt in val)
    #end validate

#end ArrayType

class DictType(Type) :
    "a dictionary mapping zero or more keys to values."

    __slots__ = ("keytype", "valuetype")

    def __init__(self, keytype, valuetype) :
        if not isinstance(keytype, BasicType) or not isinstance(valuetype, Type) :
            raise TypeError("invalid dict key/value type")
        #end if
        self.keytype = keytype
        self.valuetype = valuetype
    #end keytype

    def __repr__(self) :
        return \
            "%s[%s : %s]" % (type(self).__name__, repr(self.keytype), repr(self.valuetype))
    #end __repr__

    @property
    def signature(self) :
        return \
            "%s{%s%s}" % (chr(TYPE.ARRAY.value), self.keytype.signature, self.valuetype.signature)
    #end signature

    @property
    def entry_signature(self) :
        "signature for a dict entry."
        return \
            "{%s%s}" % (self.keytype.signature, self.valuetype.signature)
    #end entry_signature

    def __eq__(t1, t2) :
        return \
            isinstance(t2, DictType) and t1.keytype == t2.keytype and t1.valuetype == t2.valuetype
    #end __eq__

    def validate(self, val) :
        if not isinstance(val, dict) :
            raise TypeError("need a dict, not %s: %s" % (type(val).__name__, repr(val)))
        #end if
        return \
            type(val) \
              (
                (self.keytype.validate(key), self.valuetype.validate(val[key]))
                for key in val
              )
    #end validate

#end DictType

def data_key(data) :
    "returns a unique value that allows data to be used as a dict/set key."
    if isinstance(data, (bytes, float, frozenset, int, str, tuple)) :
        result = data
    else :
        # data itself is non-hashable
        result = id(data)
    #end if
    return \
        result
#end data_key

#+
# Library prototypes
#-

# from dbus-connection.h:
dbus.dbus_connection_open.restype = ct.c_void_p
dbus.dbus_connection_open.argtypes = (ct.c_char_p, DBUS.ErrorPtr)
dbus.dbus_connection_open_private.restype = ct.c_void_p
dbus.dbus_connection_open_private.argtypes = (ct.c_char_p, DBUS.ErrorPtr)
dbus.dbus_connection_ref.restype = ct.c_void_p
dbus.dbus_connection_ref.argtypes = (ct.c_void_p,)
dbus.dbus_connection_unref.restype = None
dbus.dbus_connection_unref.argtypes = (ct.c_void_p,)
dbus.dbus_connection_close.restype = None
dbus.dbus_connection_close.argtypes = (ct.c_void_p,)
dbus.dbus_connection_get_is_connected.restype = DBUS.bool_t
dbus.dbus_connection_get_is_connected.argtypes = (ct.c_void_p,)
dbus.dbus_connection_get_is_authenticated.restype = DBUS.bool_t
dbus.dbus_connection_get_is_authenticated.argtypes = (ct.c_void_p,)
dbus.dbus_connection_get_is_anonymous.restype = DBUS.bool_t
dbus.dbus_connection_get_is_anonymous.argtypes = (ct.c_void_p,)
dbus.dbus_connection_get_server_id.restype = ct.c_void_p
dbus.dbus_connection_get_server_id.argtypes = (ct.c_void_p,)
dbus.dbus_connection_can_send_type.restype = DBUS.bool_t
dbus.dbus_connection_can_send_type.argtypes = (ct.c_void_p, ct.c_int)
dbus.dbus_connection_set_exit_on_disconnect.restype = None
dbus.dbus_connection_set_exit_on_disconnect.argtypes = (ct.c_void_p, DBUS.bool_t)
dbus.dbus_connection_preallocate_send.restype = ct.c_void_p
dbus.dbus_connection_preallocate_send.argtypes = (ct.c_void_p,)
dbus.dbus_connection_free_preallocated_send.restype = None
dbus.dbus_connection_free_preallocated_send.argtypes = (ct.c_void_p, ct.c_void_p)
dbus.dbus_connection_send_preallocated.restype = None
dbus.dbus_connection_send_preallocated.argtypes = (ct.c_void_p, ct.c_void_p, ct.c_void_p, ct.POINTER(ct.c_uint))
dbus.dbus_connection_has_messages_to_send.restype = DBUS.bool_t
dbus.dbus_connection_has_messages_to_send.argtypes = (ct.c_void_p,)
dbus.dbus_connection_send.restype = DBUS.bool_t
dbus.dbus_connection_send.argtypes = (ct.c_void_p, ct.c_void_p, ct.POINTER(ct.c_uint))
dbus.dbus_connection_send_with_reply.restype = DBUS.bool_t
dbus.dbus_connection_send_with_reply.argtypes = (ct.c_void_p, ct.c_void_p, ct.c_void_p, ct.c_int)
dbus.dbus_connection_send_with_reply_and_block.restype = ct.c_void_p
dbus.dbus_connection_send_with_reply_and_block.argtypes = (ct.c_void_p, ct.c_void_p, ct.c_int, DBUS.ErrorPtr)
dbus.dbus_connection_flush.restype = None
dbus.dbus_connection_flush.argtypes = (ct.c_void_p,)
dbus.dbus_connection_read_write_dispatch.restype = DBUS.bool_t
dbus.dbus_connection_read_write_dispatch.argtypes = (ct.c_void_p, ct.c_int)
dbus.dbus_connection_read_write.restype = DBUS.bool_t
dbus.dbus_connection_read_write.argtypes = (ct.c_void_p, ct.c_int)
dbus.dbus_connection_borrow_message.restype = ct.c_void_p
dbus.dbus_connection_borrow_message.argtypes = (ct.c_void_p,)
dbus.dbus_connection_return_message.restype = None
dbus.dbus_connection_return_message.argtypes = (ct.c_void_p, ct.c_void_p)
dbus.dbus_connection_steal_borrowed_message.restype = None
dbus.dbus_connection_steal_borrowed_message.argtypes = (ct.c_void_p, ct.c_void_p)
dbus.dbus_connection_pop_message.restype = ct.c_void_p
dbus.dbus_connection_pop_message.argtypes = (ct.c_void_p,)
dbus.dbus_connection_get_dispatch_status.restype = ct.c_uint
dbus.dbus_connection_get_dispatch_status.argtypes = (ct.c_void_p,)
dbus.dbus_connection_dispatch.restype = ct.c_uint
dbus.dbus_connection_dispatch.argtypes = (ct.c_void_p,)
dbus.dbus_connection_set_watch_functions.restype = DBUS.bool_t
dbus.dbus_connection_set_watch_functions.argtypes = (ct.c_void_p, ct.c_void_p, ct.c_void_p, ct.c_void_p, ct.c_void_p, ct.c_void_p)
dbus.dbus_connection_set_timeout_functions.restype = DBUS.bool_t
dbus.dbus_connection_set_timeout_functions.argtypes = (ct.c_void_p, ct.c_void_p, ct.c_void_p, ct.c_void_p, ct.c_void_p, ct.c_void_p)
dbus.dbus_connection_set_wakeup_main_function.restype = None
dbus.dbus_connection_set_wakeup_main_function.argtypes = (ct.c_void_p, ct.c_void_p, ct.c_void_p, ct.c_void_p)
dbus.dbus_connection_set_dispatch_status_function.restype = None
dbus.dbus_connection_set_dispatch_status_function.argtypes = (ct.c_void_p, ct.c_void_p, ct.c_void_p, ct.c_void_p)
dbus.dbus_connection_get_unix_user.restype = DBUS.bool_t
dbus.dbus_connection_get_unix_user.argtypes = (ct.c_void_p, ct.POINTER(ct.c_ulong))
dbus.dbus_connection_get_unix_process_id.restype = DBUS.bool_t
dbus.dbus_connection_get_unix_process_id.argtypes = (ct.c_void_p, ct.POINTER(ct.c_ulong))
dbus.dbus_connection_get_adt_audit_session_data.restype = DBUS.bool_t
dbus.dbus_connection_get_adt_audit_session_data.argtypes = (ct.c_void_p, ct.c_void_p, ct.POINTER(ct.c_uint))
dbus.dbus_connection_set_unix_user_function.restype = None
dbus.dbus_connection_set_unix_user_function.argtypes = (ct.c_void_p, ct.c_void_p, ct.c_void_p, ct.c_void_p)
dbus.dbus_connection_get_windows_user.restype = DBUS.bool_t
dbus.dbus_connection_get_windows_user.argtypes = (ct.c_void_p, ct.c_void_p)
dbus.dbus_connection_set_windows_user_function.restype = None
dbus.dbus_connection_set_windows_user_function.argtypes = (ct.c_void_p, ct.c_void_p, ct.c_void_p, ct.c_void_p)
dbus.dbus_connection_set_allow_anonymous.restype = None
dbus.dbus_connection_set_allow_anonymous.argtypes = (ct.c_void_p, DBUS.bool_t)
dbus.dbus_connection_set_route_peer_messages.restype = None
dbus.dbus_connection_set_route_peer_messages.argtypes = (ct.c_void_p, DBUS.bool_t)

dbus.dbus_connection_add_filter.restype = DBUS.bool_t
dbus.dbus_connection_add_filter.argtypes = (ct.c_void_p, ct.c_void_p, ct.c_void_p, ct.c_void_p)
dbus.dbus_connection_remove_filter.restype = None
dbus.dbus_connection_remove_filter.argtypes = (ct.c_void_p, ct.c_void_p, ct.c_void_p)

dbus.dbus_connection_allocate_data_slot.restype = DBUS.bool_t
dbus.dbus_connection_allocate_data_slot.argtypes = (ct.POINTER(ct.c_uint),)
dbus.dbus_connection_free_data_slot.restype = None
dbus.dbus_connection_free_data_slot.argtypes = (ct.c_uint,)
dbus.dbus_connection_set_data.restype = DBUS.bool_t
dbus.dbus_connection_set_data.argtypes = (ct.c_void_p, ct.c_uint, ct.c_void_p, ct.c_void_p)
dbus.dbus_connection_get_data.restype = ct.c_void_p
dbus.dbus_connection_get_data.argtypes = (ct.c_void_p, ct.c_uint)
dbus.dbus_connection_set_change_sigpipe.restype = None
dbus.dbus_connection_set_change_sigpipe.argtypes = (DBUS.bool_t,)
dbus.dbus_connection_set_max_message_size.restype = None
dbus.dbus_connection_set_max_message_size.argtypes = (ct.c_void_p, ct.c_long)
dbus.dbus_connection_get_max_message_size.restype = ct.c_long
dbus.dbus_connection_get_max_message_size.argtypes = (ct.c_void_p,)
dbus.dbus_connection_set_max_received_size.restype = None
dbus.dbus_connection_set_max_received_size.argtypes = (ct.c_void_p, ct.c_long)
dbus.dbus_connection_get_max_received_size.restype = ct.c_long
dbus.dbus_connection_get_max_received_size.argtypes = (ct.c_void_p,)
dbus.dbus_connection_set_max_message_unix_fds.restype = None
dbus.dbus_connection_set_max_message_unix_fds.argtypes = (ct.c_void_p, ct.c_long)
dbus.dbus_connection_get_max_message_unix_fds.restype = ct.c_long
dbus.dbus_connection_get_max_message_unix_fds.argtypes = (ct.c_void_p,)
dbus.dbus_connection_set_max_received_unix_fds.restype = None
dbus.dbus_connection_set_max_received_unix_fds.argtypes = (ct.c_void_p, ct.c_long)
dbus.dbus_connection_get_max_received_unix_fds.restype = ct.c_long
dbus.dbus_connection_get_max_received_unix_fds.argtypes = (ct.c_void_p,)

dbus.dbus_connection_get_outgoing_size.restype = ct.c_long
dbus.dbus_connection_get_outgoing_size.argtypes = (ct.c_void_p,)
dbus.dbus_connection_get_outgoing_unix_fds.restype = ct.c_long
dbus.dbus_connection_get_outgoing_unix_fds.argtypes = (ct.c_void_p,)

dbus.dbus_connection_register_object_path.restype = DBUS.bool_t
dbus.dbus_connection_register_object_path.argtypes = (ct.c_void_p, ct.c_char_p, DBUS.ObjectPathVTablePtr, ct.c_void_p)
dbus.dbus_connection_try_register_object_path.restype = DBUS.bool_t
dbus.dbus_connection_try_register_object_path.argtypes = (ct.c_void_p, ct.c_char_p, DBUS.ObjectPathVTablePtr, ct.c_void_p, DBUS.ErrorPtr)
dbus.dbus_connection_register_fallback.restype = DBUS.bool_t
dbus.dbus_connection_register_fallback.argtypes = (ct.c_void_p, ct.c_char_p, DBUS.ObjectPathVTablePtr, ct.c_void_p)
dbus.dbus_connection_try_register_fallback.restype = DBUS.bool_t
dbus.dbus_connection_try_register_fallback.argtypes = (ct.c_void_p, ct.c_char_p, DBUS.ObjectPathVTablePtr, ct.c_void_p, DBUS.ErrorPtr)
dbus.dbus_connection_get_object_path_data.restype = DBUS.bool_t
dbus.dbus_connection_get_object_path_data.argtypes = (ct.c_void_p, ct.c_char_p, ct.c_void_p)
dbus.dbus_connection_list_registered.restype = DBUS.bool_t
dbus.dbus_connection_list_registered.argtypes = (ct.c_void_p, ct.c_char_p, ct.c_void_p)
dbus.dbus_connection_get_unix_fd.restype = DBUS.bool_t
dbus.dbus_connection_get_unix_fd.argtypes = (ct.c_void_p, ct.POINTER(ct.c_int))
dbus.dbus_connection_get_socket.restype = DBUS.bool_t
dbus.dbus_connection_get_socket.argtypes = (ct.c_void_p, ct.POINTER(ct.c_int))
dbus.dbus_connection_unregister_object_path.restype = DBUS.bool_t
dbus.dbus_connection_unregister_object_path.argtypes = (ct.c_void_p, ct.c_char_p)

dbus.dbus_watch_get_unix_fd.restype = ct.c_int
dbus.dbus_watch_get_unix_fd.argtypes = (ct.c_void_p,)
dbus.dbus_watch_get_socket.restype = ct.c_int
dbus.dbus_watch_get_socket.argtypes = (ct.c_void_p,)
dbus.dbus_watch_get_flags.restype = ct.c_uint
dbus.dbus_watch_get_flags.argtypes = (ct.c_void_p,)
dbus.dbus_watch_get_data.restype = ct.c_void_p
dbus.dbus_watch_get_data.argtypes = (ct.c_void_p,)
dbus.dbus_watch_set_data.restype = None
dbus.dbus_watch_set_data.argtypes = (ct.c_void_p, ct.c_void_p, ct.c_void_p)
dbus.dbus_watch_handle.restype = DBUS.bool_t
dbus.dbus_watch_handle.argtypes = (ct.c_void_p, ct.c_uint)
dbus.dbus_watch_get_enabled.restype = DBUS.bool_t
dbus.dbus_watch_get_enabled.argtypes = (ct.c_void_p,)

dbus.dbus_timeout_get_interval.restype = ct.c_int
dbus.dbus_timeout_get_interval.argtypes = (ct.c_void_p,)
dbus.dbus_timeout_get_data.restype = ct.c_void_p
dbus.dbus_timeout_get_data.argtypes = (ct.c_void_p,)
dbus.dbus_timeout_set_data.restype = None
dbus.dbus_timeout_set_data.argtypes = (ct.c_void_p, ct.c_void_p, ct.c_void_p)
dbus.dbus_timeout_handle.restype = DBUS.bool_t
dbus.dbus_timeout_handle.argtypes = (ct.c_void_p,)
dbus.dbus_timeout_get_enabled.restype = DBUS.bool_t
dbus.dbus_timeout_get_enabled.argtypes = (ct.c_void_p,)

# from dbus-bus.h:
dbus.dbus_bus_get.restype = ct.c_void_p
dbus.dbus_bus_get.argtypes = (ct.c_uint, DBUS.ErrorPtr)
dbus.dbus_bus_get_private.restype = ct.c_void_p
dbus.dbus_bus_get_private.argtypes = (ct.c_uint, DBUS.ErrorPtr)
dbus.dbus_bus_register.restype = DBUS.bool_t
dbus.dbus_bus_register.argtypes = (ct.c_void_p, DBUS.ErrorPtr)
dbus.dbus_bus_set_unique_name.restype = DBUS.bool_t
dbus.dbus_bus_set_unique_name.argtypes = (ct.c_void_p, ct.c_char_p)
dbus.dbus_bus_get_unique_name.restype = ct.c_char_p
dbus.dbus_bus_get_unique_name.argtypes = (ct.c_void_p,)
dbus.dbus_bus_get_unix_user.restype = ct.c_ulong
dbus.dbus_bus_get_unix_user.argtypes = (ct.c_void_p, ct.c_char_p, DBUS.ErrorPtr)
dbus.dbus_bus_get_id.restype = ct.c_void_p
dbus.dbus_bus_get_id.argtypes = (ct.c_void_p, DBUS.ErrorPtr)
dbus.dbus_bus_request_name.restype = ct.c_int
dbus.dbus_bus_request_name.argtypes = (ct.c_void_p, ct.c_char_p, ct.c_uint, DBUS.ErrorPtr)
dbus.dbus_bus_release_name.restype = ct.c_int
dbus.dbus_bus_release_name.argtypes = (ct.c_void_p, ct.c_char_p, DBUS.ErrorPtr)
dbus.dbus_bus_name_has_owner.restype = DBUS.bool_t
dbus.dbus_bus_name_has_owner.argtypes = (ct.c_void_p, ct.c_char_p, DBUS.ErrorPtr)
dbus.dbus_bus_start_service_by_name.restype = DBUS.bool_t
dbus.dbus_bus_start_service_by_name.argtypes = (ct.c_void_p, ct.c_char_p, ct.c_uint, ct.POINTER(ct.c_uint), DBUS.ErrorPtr)
dbus.dbus_bus_add_match.restype = None
dbus.dbus_bus_add_match.argtypes = (ct.c_void_p, ct.c_char_p, DBUS.ErrorPtr)
dbus.dbus_bus_remove_match.restype = None
dbus.dbus_bus_remove_match.argtypes = (ct.c_void_p, ct.c_char_p, DBUS.ErrorPtr)

dbus.dbus_error_init.restype = None
dbus.dbus_error_init.argtypes = (DBUS.ErrorPtr,)
dbus.dbus_error_free.restype = None
dbus.dbus_error_free.argtypes = (DBUS.ErrorPtr,)
dbus.dbus_move_error.restype = None
dbus.dbus_move_error.argtypes = (DBUS.ErrorPtr, DBUS.ErrorPtr)
dbus.dbus_error_has_name.restype = DBUS.bool_t
dbus.dbus_error_has_name.argtypes = (DBUS.ErrorPtr, ct.c_char_p)
dbus.dbus_error_is_set.restype = DBUS.bool_t
dbus.dbus_error_is_set.argtypes = (DBUS.ErrorPtr,)
dbus.dbus_set_error.restype = None
dbus.dbus_set_error.argtypes = (DBUS.ErrorPtr, ct.c_char_p, ct.c_char_p, ct.c_char_p)
  # note I can’t handle varargs

# from dbus-pending-call.h:
dbus.dbus_pending_call_ref.restype = ct.c_void_p
dbus.dbus_pending_call_ref.argtypes = (ct.c_void_p,)
dbus.dbus_pending_call_unref.restype = None
dbus.dbus_pending_call_unref.argtypes = (ct.c_void_p,)
dbus.dbus_pending_call_set_notify.restype = DBUS.bool_t
dbus.dbus_pending_call_set_notify.argtypes = (ct.c_void_p, ct.c_void_p, ct.c_void_p, ct.c_void_p)
dbus.dbus_pending_call_cancel.restype = None
dbus.dbus_pending_call_cancel.argtypes = (ct.c_void_p,)
dbus.dbus_pending_call_get_completed.restype = DBUS.bool_t
dbus.dbus_pending_call_get_completed.argtypes = (ct.c_void_p,)
dbus.dbus_pending_call_steal_reply.restype = ct.c_void_p
dbus.dbus_pending_call_steal_reply.argtypes = (ct.c_void_p,)
dbus.dbus_pending_call_block.restype = None
dbus.dbus_pending_call_block.argtypes = (ct.c_void_p,)
dbus.dbus_pending_call_allocate_data_slot.restype = DBUS.bool_t
dbus.dbus_pending_call_allocate_data_slot.argtypes = (ct.POINTER(ct.c_int),)
dbus.dbus_pending_call_free_data_slot.restype = None
dbus.dbus_pending_call_free_data_slot.argtypes = (ct.c_int,)
dbus.dbus_pending_call_set_data.restype = DBUS.bool_t
dbus.dbus_pending_call_set_data.argtypes = (ct.c_void_p, ct.c_int, ct.c_void_p, ct.c_void_p)
dbus.dbus_pending_call_get_data.restype = ct.c_void_p
dbus.dbus_pending_call_get_data.argtypes = (ct.c_void_p, ct.c_int)

# from dbus-message.h:
dbus.dbus_message_new.restype = ct.c_void_p
dbus.dbus_message_new.argtypes = (ct.c_int,)
dbus.dbus_message_new_method_call.restype = ct.c_void_p
dbus.dbus_message_new_method_call.argtypes = (ct.c_char_p, ct.c_char_p, ct.c_char_p, ct.c_char_p)
dbus.dbus_message_new_method_return.restype = ct.c_void_p
dbus.dbus_message_new_method_return.argtypes = (ct.c_void_p,)
dbus.dbus_message_new_signal.restype = ct.c_void_p
dbus.dbus_message_new_signal.argtypes = (ct.c_char_p, ct.c_char_p, ct.c_char_p)
dbus.dbus_message_new_error.restype = ct.c_void_p
dbus.dbus_message_new_error.argtypes = (ct.c_void_p, ct.c_char_p, ct.c_char_p)
dbus.dbus_message_new_error_printf.restype = ct.c_void_p
dbus.dbus_message_new_error_printf.argtypes = (ct.c_void_p, ct.c_char_p, ct.c_char_p, ct.c_char_p)
  # note I can’t handle varargs
dbus.dbus_message_copy.restype = ct.c_void_p
dbus.dbus_message_copy.argtypes = (ct.c_void_p,)
dbus.dbus_message_ref.restype = ct.c_void_p
dbus.dbus_message_ref.argtypes = (ct.c_void_p,)
dbus.dbus_message_unref.restype = None
dbus.dbus_message_unref.argtypes = (ct.c_void_p,)
dbus.dbus_message_get_type.restype = ct.c_int
dbus.dbus_message_get_type.argtypes = (ct.c_void_p,)
dbus.dbus_message_set_path.restype = DBUS.bool_t
dbus.dbus_message_set_path.argtypes = (ct.c_void_p, ct.c_char_p)
dbus.dbus_message_get_path.restype = ct.c_char_p
dbus.dbus_message_get_path.argtypes = (ct.c_void_p,)
dbus.dbus_message_has_path.restype = DBUS.bool_t
dbus.dbus_message_has_path.argtypes = (ct.c_void_p, ct.c_char_p)
dbus.dbus_message_set_interface.restype = DBUS.bool_t
dbus.dbus_message_set_interface.argtypes = (ct.c_void_p, ct.c_char_p)
dbus.dbus_message_get_interface.restype = ct.c_char_p
dbus.dbus_message_get_interface.argtypes = (ct.c_void_p,)
dbus.dbus_message_has_interface.restype = DBUS.bool_t
dbus.dbus_message_has_interface.argtypes = (ct.c_void_p, ct.c_char_p)
dbus.dbus_message_set_member.restype = DBUS.bool_t
dbus.dbus_message_set_member.argtypes = (ct.c_void_p, ct.c_char_p)
dbus.dbus_message_get_member.restype = ct.c_char_p
dbus.dbus_message_get_member.argtypes = (ct.c_void_p,)
dbus.dbus_message_has_member.restype = DBUS.bool_t
dbus.dbus_message_has_member.argtypes = (ct.c_void_p, ct.c_char_p)
dbus.dbus_message_set_error_name.restype = DBUS.bool_t
dbus.dbus_message_set_error_name.argtypes = (ct.c_void_p, ct.c_char_p)
dbus.dbus_message_get_error_name.restype = ct.c_char_p
dbus.dbus_message_get_error_name.argtypes = (ct.c_void_p,)
dbus.dbus_message_set_destination.restype = DBUS.bool_t
dbus.dbus_message_set_destination.argtypes = (ct.c_void_p, ct.c_char_p)
dbus.dbus_message_get_destination.restype = ct.c_char_p
dbus.dbus_message_get_destination.argtypes = (ct.c_void_p,)
dbus.dbus_message_set_sender.restype = DBUS.bool_t
dbus.dbus_message_set_sender.argtypes = (ct.c_void_p, ct.c_char_p)
dbus.dbus_message_get_sender.restype = ct.c_char_p
dbus.dbus_message_get_sender.argtypes = (ct.c_void_p,)
dbus.dbus_message_get_signature.restype = ct.c_char_p
dbus.dbus_message_get_signature.argtypes = (ct.c_void_p,)
dbus.dbus_message_set_no_reply.restype = None
dbus.dbus_message_set_no_reply.argtypes = (ct.c_void_p, DBUS.bool_t)
dbus.dbus_message_get_no_reply.restype = DBUS.bool_t
dbus.dbus_message_get_no_reply.argtypes = (ct.c_void_p,)
dbus.dbus_message_is_method_call.restype = DBUS.bool_t
dbus.dbus_message_is_method_call.argtypes = (ct.c_void_p, ct.c_char_p, ct.c_char_p)
dbus.dbus_message_is_signal.restype = DBUS.bool_t
dbus.dbus_message_is_signal.argtypes = (ct.c_void_p, ct.c_char_p, ct.c_char_p)
dbus.dbus_message_is_error.restype = DBUS.bool_t
dbus.dbus_message_is_error.argtypes = (ct.c_void_p, ct.c_char_p)
dbus.dbus_message_has_destination.restype = DBUS.bool_t
dbus.dbus_message_has_destination.argtypes = (ct.c_void_p, ct.c_char_p)
dbus.dbus_message_has_sender.restype = DBUS.bool_t
dbus.dbus_message_has_sender.argtypes = (ct.c_void_p, ct.c_char_p)
dbus.dbus_message_has_signature.restype = DBUS.bool_t
dbus.dbus_message_has_signature.argtypes = (ct.c_void_p, ct.c_char_p)
dbus.dbus_message_get_serial.restype = ct.c_uint
dbus.dbus_message_get_serial.argtypes = (ct.c_void_p,)
dbus.dbus_message_set_serial.restype = None
dbus.dbus_message_set_serial.argtypes = (ct.c_void_p, ct.c_uint)
dbus.dbus_message_set_reply_serial.restype = DBUS.bool_t
dbus.dbus_message_set_reply_serial.argtypes = (ct.c_void_p, ct.c_uint)
dbus.dbus_message_get_reply_serial.restype = ct.c_uint
dbus.dbus_message_get_reply_serial.argtypes = (ct.c_void_p,)
dbus.dbus_message_set_auto_start.restype = None
dbus.dbus_message_set_auto_start.argtypes = (ct.c_void_p, DBUS.bool_t)
dbus.dbus_message_get_auto_start.restype = DBUS.bool_t
dbus.dbus_message_get_auto_start.argtypes = (ct.c_void_p,)
dbus.dbus_message_get_path_decomposed.restype = DBUS.bool_t
dbus.dbus_message_get_path_decomposed.argtypes = (ct.c_void_p, ct.c_void_p)
dbus.dbus_message_append_args.restype = DBUS.bool_t
dbus.dbus_message_append_args.argtypes = (ct.c_void_p, ct.c_int, ct.c_void_p, ct.c_int)
  # note I can’t handle varargs
# probably cannot make use of dbus.dbus_message_append_args_valist
dbus.dbus_message_get_args.restype = DBUS.bool_t
dbus.dbus_message_get_args.argtypes = (ct.c_void_p, DBUS.ErrorPtr, ct.c_int, ct.c_void_p, ct.c_int)
  # note I can’t handle varargs
# probably cannot make use of dbus.dbus_message_get_args_valist
dbus.dbus_message_contains_unix_fds.restype = DBUS.bool_t
dbus.dbus_message_contains_unix_fds.argtypes = (ct.c_void_p,)
dbus.dbus_message_iter_init.restype = DBUS.bool_t
dbus.dbus_message_iter_init.argtypes = (ct.c_void_p, DBUS.MessageIterPtr)
dbus.dbus_message_iter_has_next.restype = DBUS.bool_t
dbus.dbus_message_iter_has_next.argtypes = (DBUS.MessageIterPtr,)
dbus.dbus_message_iter_next.restype = DBUS.bool_t
dbus.dbus_message_iter_next.argtypes = (DBUS.MessageIterPtr,)
dbus.dbus_message_iter_get_signature.restype = ct.c_void_p
dbus.dbus_message_iter_next.argtypes = (DBUS.MessageIterPtr,)
dbus.dbus_message_iter_get_signature.restype = ct.c_void_p
dbus.dbus_message_iter_get_signature.argtypes = (DBUS.MessageIterPtr,)
dbus.dbus_message_iter_get_arg_type.restype = ct.c_int
dbus.dbus_message_iter_get_arg_type.argtypes = (DBUS.MessageIterPtr,)
dbus.dbus_message_iter_get_element_type.restype = ct.c_int
dbus.dbus_message_iter_get_element_type.argtypes = (DBUS.MessageIterPtr,)
dbus.dbus_message_iter_recurse.restype = None
dbus.dbus_message_iter_recurse.argtypes = (DBUS.MessageIterPtr, DBUS.MessageIterPtr)
dbus.dbus_message_iter_get_basic.restype = None
dbus.dbus_message_iter_get_basic.argtypes = (DBUS.MessageIterPtr, ct.c_void_p)
if hasattr(dbus, "dbus_message_iter_get_element_count") :
    dbus.dbus_message_iter_get_element_count.restype = ct.c_int
    dbus.dbus_message_iter_get_element_count.argtypes = (DBUS.MessageIterPtr,)
#end if
# dbus_message_iter_get_array_len deprecated
dbus.dbus_message_iter_get_fixed_array.restype = None
dbus.dbus_message_iter_get_fixed_array.argtypes = (DBUS.MessageIterPtr, ct.c_void_p, ct.POINTER(ct.c_int))
dbus.dbus_message_iter_init_append.restype = None
dbus.dbus_message_iter_init_append.argtypes = (ct.c_void_p, DBUS.MessageIterPtr)
dbus.dbus_message_iter_append_basic.restype = DBUS.bool_t
dbus.dbus_message_iter_append_basic.argtypes = (DBUS.MessageIterPtr, ct.c_int, ct.c_void_p)
dbus.dbus_message_iter_append_fixed_array.restype = DBUS.bool_t
dbus.dbus_message_iter_append_fixed_array.argtypes = (DBUS.MessageIterPtr, ct.c_int, ct.c_void_p, ct.c_int)
dbus.dbus_message_iter_open_container.restype = DBUS.bool_t
dbus.dbus_message_iter_open_container.argtypes = (DBUS.MessageIterPtr, ct.c_int, ct.c_char_p, DBUS.MessageIterPtr)
dbus.dbus_message_iter_close_container.restype = DBUS.bool_t
dbus.dbus_message_iter_close_container.argtypes = (DBUS.MessageIterPtr, DBUS.MessageIterPtr)
dbus.dbus_message_iter_abandon_container.restype = None
dbus.dbus_message_iter_abandon_container.argtypes = (DBUS.MessageIterPtr, DBUS.MessageIterPtr)
dbus.dbus_message_lock.restype = None
dbus.dbus_message_lock.argtypes = (DBUS.MessageIterPtr,)
dbus.dbus_set_error_from_message.restype = DBUS.bool_t
dbus.dbus_set_error_from_message.argtypes = (DBUS.ErrorPtr, ct.c_void_p)
dbus.dbus_message_allocate_data_slot.restype = DBUS.bool_t
dbus.dbus_message_allocate_data_slot.argtypes = (ct.POINTER(ct.c_int),)
dbus.dbus_message_free_data_slot.restype = None
dbus.dbus_message_free_data_slot.argtypes = (ct.POINTER(ct.c_int),)
dbus.dbus_message_set_data.restype = DBUS.bool_t
dbus.dbus_message_set_data.argtypes = (ct.c_void_p, ct.c_int, ct.c_void_p, ct.c_void_p)
dbus.dbus_message_get_data.restype = ct.c_void_p
dbus.dbus_message_get_data.argtypes = (ct.c_void_p, ct.c_int)
dbus.dbus_message_type_from_string.restype = ct.c_int
dbus.dbus_message_type_from_string.argtypes = (ct.c_char_p,)
dbus.dbus_message_type_to_string.restype = ct.c_char_p
dbus.dbus_message_type_to_string.argtypes = (ct.c_int,)
dbus.dbus_message_marshal.restype = DBUS.bool_t
dbus.dbus_message_marshal.argtypes = (ct.c_void_p, ct.c_void_p, ct.POINTER(ct.c_int))
dbus.dbus_message_demarshal.restype = ct.c_void_p
dbus.dbus_message_demarshal.argtypes = (ct.c_void_p, ct.c_int, DBUS.ErrorPtr)
dbus.dbus_message_demarshal_bytes_needed.restype = ct.c_int
dbus.dbus_message_demarshal_bytes_needed.argtypes = (ct.c_void_p, ct.c_int)
if hasattr(dbus, "dbus_message_set_allow_interactive_authorization") :
    dbus.dbus_message_set_allow_interactive_authorization.restype = None
    dbus.dbus_message_set_allow_interactive_authorization.argtypes = (ct.c_void_p, DBUS.bool_t)
#end if
if hasattr(dbus, "dbus_message_get_allow_interactive_authorization") :
    dbus.dbus_message_get_allow_interactive_authorization.restype = DBUS.bool_t
    dbus.dbus_message_get_allow_interactive_authorization.argtypes = (ct.c_void_p,)
#end if

# from dbus-memory.h:
dbus.dbus_malloc.restype = ct.c_void_p
dbus.dbus_malloc.argtypes = (ct.c_size_t,)
dbus.dbus_malloc0.restype = ct.c_void_p
dbus.dbus_malloc0.argtypes = (ct.c_size_t,)
dbus.dbus_realloc.restype = ct.c_void_p
dbus.dbus_realloc.argtypes = (ct.c_void_p, ct.c_size_t)
dbus.dbus_free.restype = None
dbus.dbus_free.argtypes = (ct.c_void_p,)
dbus.dbus_free_string_array.restype = None
dbus.dbus_free_string_array.argtypes = (ct.c_void_p,)

# from dbus-misc.h:
dbus.dbus_get_local_machine_id.restype = ct.c_void_p
dbus.dbus_get_local_machine_id.argtypes = ()
dbus.dbus_get_version.restype = None
dbus.dbus_get_version.argtypes = (ct.POINTER(ct.c_int), ct.POINTER(ct.c_int), ct.POINTER(ct.c_int))
dbus.dbus_setenv.restype = DBUS.bool_t
dbus.dbus_setenv.argtypes = (ct.c_char_p, ct.c_char_p)

# from dbus-address.h:
dbus.dbus_parse_address.restype = DBUS.bool_t
dbus.dbus_parse_address.argtypes = (ct.c_char_p, ct.c_void_p, ct.POINTER(ct.c_int), DBUS.ErrorPtr)
dbus.dbus_address_entry_get_value.restype = ct.c_char_p
dbus.dbus_address_entry_get_value.argtypes = (ct.c_void_p, ct.c_char_p)
dbus.dbus_address_entry_get_method.restype = ct.c_char_p
dbus.dbus_address_entry_get_method.argtypes = (ct.c_void_p,)
dbus.dbus_address_entries_free.restype = None
dbus.dbus_address_entries_free.argtypes = (ct.c_void_p,)
dbus.dbus_address_escape_value.restype = ct.c_void_p
dbus.dbus_address_escape_value.argtypes = (ct.c_char_p,)
dbus.dbus_address_unescape_value.restype = ct.c_void_p
dbus.dbus_address_unescape_value.argtypes = (ct.c_char_p, DBUS.ErrorPtr)

# from dbus-signature.h:
dbus.dbus_signature_iter_init.restype = None
dbus.dbus_signature_iter_init.argtypes = (DBUS.SignatureIterPtr, ct.c_char_p)
dbus.dbus_signature_iter_get_current_type.restype = ct.c_int
dbus.dbus_signature_iter_get_current_type.argtypes = (DBUS.SignatureIterPtr,)
dbus.dbus_signature_iter_get_signature.restype = ct.c_void_p
dbus.dbus_signature_iter_get_signature.argtypes = (DBUS.SignatureIterPtr,)
dbus.dbus_signature_iter_get_element_type.restype = ct.c_int
dbus.dbus_signature_iter_get_element_type.argtypes = (DBUS.SignatureIterPtr,)
dbus.dbus_signature_iter_next.restype = DBUS.bool_t
dbus.dbus_signature_iter_next.argtypes = (DBUS.SignatureIterPtr,)
dbus.dbus_signature_iter_recurse.restype = None
dbus.dbus_signature_iter_recurse.argtypes = (DBUS.SignatureIterPtr, DBUS.SignatureIterPtr)
dbus.dbus_signature_validate.restype = DBUS.bool_t
dbus.dbus_signature_validate.argtypes = (ct.c_char_p, DBUS.ErrorPtr)
dbus.dbus_signature_validate_single.restype = DBUS.bool_t
dbus.dbus_signature_validate_single.argtypes = (ct.c_char_p, DBUS.ErrorPtr)
dbus.dbus_type_is_valid.restype = DBUS.bool_t
dbus.dbus_type_is_valid.argtypes = (ct.c_int,)
dbus.dbus_type_is_basic.restype = DBUS.bool_t
dbus.dbus_type_is_basic.argtypes = (ct.c_int,)
dbus.dbus_type_is_container.restype = DBUS.bool_t
dbus.dbus_type_is_container.argtypes = (ct.c_int,)
dbus.dbus_type_is_fixed.restype = DBUS.bool_t
dbus.dbus_type_is_fixed.argtypes = (ct.c_int,)

# from dbus-syntax.h:
dbus.dbus_validate_path.restype = DBUS.bool_t
dbus.dbus_validate_path.argtypes = (ct.c_char_p, DBUS.ErrorPtr)
dbus.dbus_validate_interface.restype = DBUS.bool_t
dbus.dbus_validate_interface.argtypes = (ct.c_char_p, DBUS.ErrorPtr)
dbus.dbus_validate_member.restype = DBUS.bool_t
dbus.dbus_validate_member.argtypes = (ct.c_char_p, DBUS.ErrorPtr)
dbus.dbus_validate_error_name.restype = DBUS.bool_t
dbus.dbus_validate_error_name.argtypes = (ct.c_char_p, DBUS.ErrorPtr)
dbus.dbus_validate_bus_name.restype = DBUS.bool_t
dbus.dbus_validate_bus_name.argtypes = (ct.c_char_p, DBUS.ErrorPtr)
dbus.dbus_validate_utf8.restype = DBUS.bool_t
dbus.dbus_validate_utf8.argtypes = (ct.c_char_p, DBUS.ErrorPtr)

# from dbus-server.h:
dbus.dbus_server_listen.restype = ct.c_void_p
dbus.dbus_server_listen.argtypes = (ct.c_char_p, DBUS.ErrorPtr)
dbus.dbus_server_ref.restype = ct.c_void_p
dbus.dbus_server_ref.argtypes = (ct.c_void_p,)
dbus.dbus_server_unref.restype = ct.c_void_p
dbus.dbus_server_unref.argtypes = (ct.c_void_p,)
dbus.dbus_server_disconnect.restype = None
dbus.dbus_server_disconnect.argtypes = (ct.c_void_p,)
dbus.dbus_server_get_is_connected.restype = DBUS.bool_t
dbus.dbus_server_get_is_connected.argtypes = (ct.c_void_p,)
dbus.dbus_server_get_address.restype = ct.c_void_p
dbus.dbus_server_get_address.argtypes = (ct.c_void_p,)
dbus.dbus_server_get_id.restype = ct.c_void_p
dbus.dbus_server_get_id.argtypes = (ct.c_void_p,)
dbus.dbus_server_set_new_connection_function.restype = None
dbus.dbus_server_set_new_connection_function.argtypes = (ct.c_void_p, ct.c_void_p, ct.c_void_p, ct.c_void_p)
dbus.dbus_server_set_watch_functions.restype = DBUS.bool_t
dbus.dbus_server_set_watch_functions.argtypes = (ct.c_void_p, ct.c_void_p, ct.c_void_p, ct.c_void_p, ct.c_void_p, ct.c_void_p)
dbus.dbus_server_set_timeout_functions.restype = DBUS.bool_t
dbus.dbus_server_set_timeout_functions.argtypes = (ct.c_void_p, ct.c_void_p, ct.c_void_p, ct.c_void_p, ct.c_void_p, ct.c_void_p)
dbus.dbus_server_set_auth_mechanisms.restype = DBUS.bool_t
dbus.dbus_server_set_auth_mechanisms.argtypes = (ct.c_void_p, ct.c_void_p)
dbus.dbus_server_allocate_data_slot.restype = DBUS.bool_t
dbus.dbus_server_allocate_data_slot.argtypes = (ct.POINTER(ct.c_int),)
dbus.dbus_server_free_data_slot.restype = DBUS.bool_t
dbus.dbus_server_free_data_slot.argtypes = (ct.POINTER(ct.c_int),)
dbus.dbus_server_set_data.restype = DBUS.bool_t
dbus.dbus_server_set_data.argtypes = (ct.c_void_p, ct.c_int, ct.c_void_p, ct.c_void_p)
dbus.dbus_server_set_data.restype = ct.c_void_p
dbus.dbus_server_set_data.argtypes = (ct.c_void_p, ct.c_int)

# TODO dbus-threads.h <https://dbus.freedesktop.org/doc/api/html/group__DBusThreads.html>
# Seems like the only call worth making is dbus_threads_init_default.

#+
# High-level stuff follows
#-

class DBusError(Exception) :
    "for raising an exception that reports a D-Bus error name and accompanying message."

    __slots__ = ("name", "message")

    def __init__(self, name, message) :
        self.args = ("%s -- %s" % (name, message),)
        self.name = name
        self.message = message
    #end __init__

#end DBusError

class CallFailed(Exception) :
    "used internally for reporting general failure from calling a libdbus routine."

    __slots__ = ("funcname",)

    def __init__(self, funcname) :
        self.args = ("%s failed" % funcname,)
        self.funcname = funcname
    #end __init__

#end CallFailed

class _Abort(Exception) :
    pass
#end _Abort

class TaskKeeper :
    "Base class for classes that need to call EventLoop.create_task() to" \
    " schedule caller-created coroutines for execution. asyncio only keeps" \
    " weak references to Task objects when they are not being scheduled," \
    " so to keep them from disappearing unexpectedly, I maintain a list of" \
    " strong references here, and periodically clean them out as they end" \
    " execution."

    __slots__ = ("__weakref__", "loop", "_cur_tasks")

    def _init(self) :
        # avoid __init__ so I don't get passed spurious args
        self.loop = None
        self._cur_tasks = []
    #end _init

    def create_task(self, coro) :
        assert self.loop  is not None, "no event loop to attach coroutine to"
        task = self.loop.create_task(coro)
        if len(self._cur_tasks) == 0 :
            self.loop.call_soon(self._reaper, weak_ref(self))
        #end if
        self._cur_tasks.append(task)
    #end create_task

    @staticmethod
    def _reaper(self) :
        self = self() # avoid reference circularity
        old_tasks = self._cur_tasks[:]
        new_tasks = self._cur_tasks
        new_tasks[:] = []
        for task in old_tasks :
            if not task.done() :
                new_tasks.append(task)
            #end if
        #end for
        if len(new_tasks) != 0 :
            self.loop.call_soon(self._reaper, weak_ref(self))
        #end if
    #end _reaper

#end TaskKeeper

# Misc: <https://dbus.freedesktop.org/doc/api/html/group__DBusMisc.html>

def get_local_machine_id() :
    "returns a systemwide unique ID that is supposed to remain constant at least" \
    " until the next reboot. Two processes seeing the same value for this can assume" \
    " they are on the same machine."
    c_result = dbus.dbus_get_local_machine_id()
    if c_result  is None :
        raise CallFailed("dbus_get_local_machine_id")
    #end if
    result = ct.cast(c_result, ct.c_char_p).value.decode()
    dbus.dbus_free(c_result)
    return \
        result
#end get_local_machine_id

def get_version() :
    "returns the libdbus library version as a tuple of integers (major, minor, micro)."
    major = ct.c_int()
    minor = ct.c_int()
    micro = ct.c_int()
    dbus.dbus_get_version(ct.byref(major), ct.byref(minor), ct.byref(micro))
    return \
        (major.value, minor.value, micro.value)
#end get_version

def setenv(key, value) :
    key = key.encode()
    if value  is not None :
        value = value.encode()
    #end if
    if not dbus.dbus_setenv(key, value) :
        raise CallFailed("dbus_setenv")
    #end if
#end setenv

def unsetenv(key) :
    setenv(key, None)
#end unsetenv

class Watch :
    "wrapper around a DBusWatch object. Do not instantiate directly; they" \
    " are created and destroyed by libdbus.\n" \
    "\n" \
    "A Watch is the basic mechanism for plugging libdbus-created file descriptors" \
    " into your event loop. When created, they are passed to your add-watch callback" \
    " to manage; and conversely, when deleted, your remove-watch callback is notified." \
    " (These callbacks are ones you attach to Server and Connection objects.)\n" \
    "\n" \
    "Check the enabled property to decide if you need to pay attention to this Watch, and" \
    " look at the flags to see if you need to check for pending reads, or writes, or both." \
    " Call the handle() method with the appropriate flags when you see that reads or writes" \
    " are pending."
    # <https://dbus.freedesktop.org/doc/api/html/group__DBusWatch.html>

    __slots__ = ("__weakref__", "_dbobj",) # to forestall typos

    _instances = WeakValueDictionary()

    def __new__(celf, _dbobj) :
        self = celf._instances.get(_dbobj)
        if self  is None :
            self = super().__new__(celf)
            self._dbobj = _dbobj
            celf._instances[_dbobj] = self
        #end if
        return \
            self
    #end __new__

    # no __del__ method -- no underlying dispose API call

    @property
    def unix_fd(self) :
        "the underlying file descriptor for this Watch."
        return \
            dbus.dbus_watch_get_unix_fd(self._dbobj)
    #end unix_fd

    def fileno(self) :
        "for use with Python’s “select” functions."
        return \
            self.unix_fd
    #end fileno

    @property
    def socket(self) :
        return \
            dbus.dbus_watch_get_socket(self._dbobj)
    #end socket

    @property
    def flags(self) :
        "returns WATCH_READABLE and/or WATCH_WRITABLE, indicating what to watch for."
        return \
            dbus.dbus_watch_get_flags(self._dbobj)
    #end flags

    # TODO: get/set data

    def handle(self, flags) :
        "tells libdbus that there is something to be read or written." \
        " flags are a combination of WATCH_xxx values."
        return \
            dbus.dbus_watch_handle(self._dbobj, flags) != 0
    #end handle

    @property
    def enabled(self) :
        "does libdbus want you to actually watch this Watch."
        return \
            dbus.dbus_watch_get_enabled(self._dbobj) != 0
    #end enabled

#end Watch

class Timeout :
    "wrapper around a DBusTimeout object. Do not instantiate directly; they" \
    " are created and destroyed by libdbus.\n" \
    "\n" \
    " A Timeout is the basic mechanism for plugging libdbus-created timeouts" \
    " into your event loop. When created, they are passed to your add-timeout" \
    " callback to manage; and conversely, when deleted, your remove-timeout" \
    " callback is notified. (These callbacks are ones you attach to Server and" \
    " Connection objects.)\n" \
    "\n" \
    "Check the enabled property to decide if you need to pay attention to this" \
    " Timeout. Call the handle() method when the timeout becomes due, as measured" \
    " from when it was initially created or most recently enabled, whichever" \
    " happened last."
    # <https://dbus.freedesktop.org/doc/api/html/group__DBusTimeout.html>

    __slots__ = ("__weakref__", "_dbobj",) # to forestall typos

    _instances = WeakValueDictionary()

    def __new__(celf, _dbobj) :
        self = celf._instances.get(_dbobj)
        if self  is None :
            self = super().__new__(celf)
            self._dbobj = _dbobj
            celf._instances[_dbobj] = self
        #end if
        return \
            self
    #end __new__

    # no __del__ method -- no underlying dispose API call

    @property
    def interval(self) :
        "how long in float seconds until the timeout should fire."
        return \
            dbus.dbus_timeout_get_interval(self._dbobj) / 1000
    #end interval

    # TODO: get/set data

    def handle(self) :
        "tells libdbus the timeout has fired."
        return \
            dbus.dbus_timeout_handle(self._dbobj)
    #end handle

    @property
    def enabled(self) :
        "does libdbus want you to actually schedule this Timeout."
        return \
            dbus.dbus_timeout_get_enabled(self._dbobj) != 0
    #end enabled

#end Timeout

class ObjectPathVTable(TaskKeeper) :
    "wrapper around an ObjectPathVTable struct. You can instantiate directly, or call" \
    " the init method. An additional feature beyond the underlying libdbus capabilities" \
    " is the option to specify an asyncio event loop. If the message handler returns" \
    " a coroutine, then an asyncio task is created to run it, and a result of" \
    " DBUS.HANDLER_RESULT_HANDLED is returned on behalf of the message handler;" \
    " that way, the message function can do the minimum beyond some initial filtering of" \
    " the message, leaving the time-consuming part of the work to the coroutine."

    __slots__ = \
      (
        "_dbobj",
        # need to keep references to ctypes-wrapped functions
        # so they don't disappear prematurely:
        "_wrap_unregister_func",
        "_wrap_message_func",
      ) # to forestall typos

    def __init__(self, *, loop = None, unregister = None, message = None) :
        super().__init__()
        super()._init()
        self._dbobj = DBUS.ObjectPathVTable()
        self.loop = loop
        self._wrap_unregister_func = None
        self._wrap_message_func = None
        if unregister  is not None :
            self.set_unregister(unregister)
        #end if
        if message  is not None :
            self.set_message(message)
        #end if
    #end __init__

    @classmethod
    def init(celf, *, loop = None, unregister = None, message = None) :
        "for consistency with other classes that don’t want caller to instantiate directly."
        return \
            celf \
              (
                loop = loop,
                unregister = unregister,
                message = message,
              )
    #end init

    def set_unregister(self, unregister) :
        def wrap_unregister(c_conn, c_user_data) :
            conn = Connection(dbus.dbus_connection_ref(c_conn))
            unregister(conn, conn._user_data.get(c_user_data))
        #end wrap_unregister

    #begin set_unregister
        if unregister  is not None :
            self._wrap_unregister_func = DBUS.ObjectPathUnregisterFunction(wrap_unregister)
        else :
            self._wrap_unregister_func = None
        #end if
        self._dbobj.unregister_function = self._wrap_unregister_func
        return \
            self
    #end set_unregister

    def set_message(self, message) :
        w_self = weak_ref(self)

        def wrap_message(c_conn, c_message, c_user_data) :
            self = _wderef(w_self, "vtable")
            conn = Connection(dbus.dbus_connection_ref(c_conn))
            msg = Message(dbus.dbus_message_ref(c_message))
            user_data = conn._user_data.get(c_user_data)
            result = message(conn, msg, user_data)
            if asyncio.iscoroutine(result) :
                self.create_task(result)
                result = DBUS.HANDLER_RESULT_HANDLED
            #end if
            return \
                result
        #end wrap_message

    #begin set_message
        if message  is not None :
            self._wrap_message_func = DBUS.ObjectPathMessageFunction(wrap_message)
        else :
            self._wrap_message_func = None
        #end if
        self._dbobj.message_function = self._wrap_message_func
        return \
            self
    #end set_message

#end ObjectPathVTable

class _DummyError :
    # like an Error, but is never set and so will never raise.

    @property
    def is_set(self) :
        return \
            False
    #end is_set

    def raise_if_set(self) :
        pass
    #end raise_if_set

#end _DummyError

def _get_error(error) :
    # Common routine which processes an optional user-supplied Error
    # argument, and returns 2 Error-like objects: the first a real
    # Error object to be passed to the libdbus call, the second is
    # either the same Error object or a separate _DummyError object
    # on which to call raise_if_set() afterwards. The procedure for
    # using this is
    #
    #     error, my_error = _get_error(error)
    #     ... call libdbus routine, passing error._dbobj ...
    #     my_error.raise_if_set()
    #
    # If the user passes None for error, then an internal Error object
    # is created, and returned as both results. That way, if it is
    # filled in by the libdbus call, calling raise_if_set() will
    # automatically raise the exception.
    # But if the user passed their own Error object, then it is
    # returned as the first result, and a _DummyError as the second
    # result. This means the raise_if_set() call becomes a noop, and
    # it is up to the caller to check if their Error object was filled
    # in or not.
    if error  is not None and not isinstance(error, Error) :
        raise TypeError("error must be an Error")
    #end if
    if error  is not None :
        my_error = _DummyError()
    else :
        my_error = Error()
        error = my_error
    #end if
    return \
        error, my_error
#end _get_error

def _get_timeout(timeout) :
    # accepts a timeout in float seconds and converts it to integer milliseconds
    # as expected by libdbus. Special-cases DBUS.TIMEOUT_INFINITE and DBUS.TIMEOUT_USE_DEFAULT,
    # allowing these to be passed through unchanged.
    if not isinstance(timeout, int) or timeout not in (DBUS.TIMEOUT_INFINITE, DBUS.TIMEOUT_USE_DEFAULT) :
        timeout = round(timeout * 1000)
    #end if
    return \
        timeout
#end _get_timeout

def _loop_attach(self, loop, dispatch) :
    # attaches a Server or Connection object to a given asyncio event loop.
    # If loop is None, then the default asyncio loop is used. The actual loop
    # value is also stored as the loop attribute of the object.

    if loop  is None :
        loop = asyncio.get_event_loop()
    #end if

    watches = [] # do I need to keep track of Watch objects?
    timeouts = []

    def call_dispatch() :
        status = dispatch()
        if status == DBUS.DISPATCH_NEED_MEMORY :
            raise DBusError(DBUS.ERROR_NO_MEMORY, "not enough memory for connection dispatch")
        #end if
        if status == DBUS.DISPATCH_DATA_REMAINS :
            loop.call_soon(call_dispatch)
        #end if
    #end call_dispatch

    def add_remove_watch(watch, add) :
        def handle_watch_event(flags) :
            # seems I need to remove the watch and add it again to
            # avoid an endless stream of notifications that cause
            # excessive CPU usage -- asyncio bug?
            add_remove_watch(watch, False)
            watch.handle(flags)
            if watch.enabled :
                add_remove_watch(watch, True)
             #end if
            if dispatch  is not None :
                call_dispatch()
            #end if
        #end handle_watch_event

    #end add_remove_watch
        if DBUS.WATCH_READABLE & watch.flags != 0 :
            if add :
                loop.add_reader(watch, handle_watch_event, DBUS.WATCH_READABLE)
            else :
                loop.remove_reader(watch)
            #end if
        #end if
        if DBUS.WATCH_WRITABLE & watch.flags != 0 :
            if add :
                loop.add_writer(watch, handle_watch_event, DBUS.WATCH_WRITABLE)
            else :
                loop.remove_writer(watch)
            #end if
        #end if
    #end add_remove_watch

    def handle_add_watch(watch, data) :
        if watch not in watches :
            watches.append(watch)
            add_remove_watch(watch, True)
        #end if
        return \
            True
    #end handle_add_watch

    def handle_watch_toggled(watch, data) :
        add_remove_watch(watch, watch.enabled)
    #end handle_watch_toggled

    def handle_remove_watch(watch, data) :
        try :
            pos = watches.index(watch)
        except ValueError :
            pos = None
        #end try
        if pos  is not None :
            watches[pos : pos + 1] = []
            add_remove_watch(watch, False)
        #end if
    #end handle_remove_watch

    def handle_timeout(timeout) :
        if timeout["due"]  is not None and timeout["due"] <= loop.time() and timeout["timeout"].enabled :
            timeout["timeout"].handle()
        #end if
    #end handle_timeout

    def handle_add_timeout(timeout, data) :
        if not any(timeout == t["timeout"] for t in timeouts) :
            entry = \
                {
                    "timeout" : timeout,
                    "due" : (lambda : None, lambda : loop.time() + timeout.interval)[timeout.enabled](),
                }
            timeouts.append(entry)
            if timeout.enabled :
                loop.call_later(timeout.interval, handle_timeout, entry)
            #end if
        #end if
        return \
            True
    #end handle_add_timeout

    def handle_timeout_toggled(timeout, data) :
        # not sure what to do if a Timeout gets toggled from enabled to disabled
        # and then to enabled again; effectively I update the due time from
        # the time of re-enabling.
        search = iter(timeouts)
        while True :
            entry = next(search, None)
            if entry  is None :
                break
            #end if
            if entry["timeout"] == timeout :
                if timeout.enabled :
                    entry["due"] = loop.time() + timeout.enterval
                    loop.call_later(timeout.interval, handle_timeout, entry)
                else :
                    entry["due"] = None
                #end if
                break
            #end if
        #end while
    #end handle_timeout_toggled

    def handle_remove_timeout(timeout, data) :
        new_timeouts = []
        for entry in timeouts :
            if entry["timeout"] == timeout :
                entry["due"] = None # in case already queued, avoid segfault in handle_timeout
            else :
                new_timeouts.append(entry)
            #end if
        #end for
        timeouts[:] = new_timeouts
    #end handle_remove_timeout

#begin _loop_attach
    self.set_watch_functions \
      (
        add_function = handle_add_watch,
        remove_function = handle_remove_watch,
        toggled_function = handle_watch_toggled,
        data = None
      )
    self.set_timeout_functions \
      (
        add_function = handle_add_timeout,
        remove_function = handle_remove_timeout,
        toggled_function = handle_timeout_toggled,
        data = None
      )
    self.loop = loop
    self = None # avoid circularity
#end _loop_attach

class _MatchActionEntry :
    __slots__ = ("rule", "actions")

    class _Action :
        __slots__ = ("func", "user_data")

        def __init__(self, func, user_data) :
            self.func = func
            self.user_data = user_data
        #end __init__

        def __eq__(a, b) :
            # needed to allow equality comparison of set entries
            return \
                (
                    a.func == b.func
                and
                    data_key(a.user_data) == data_key(b.user_data)
                )
        #end __eq__

        def __hash__(self) :
            return \
                hash((self.func, data_key(self.user_data)))
        #end __hash__

    #end _Action

    def __init__(self, rule) :
        self.rule = rule
        self.actions = set()
    #end __init__

#end _MatchActionEntry

@enum.unique
class STOP_ON(enum.Enum) :
    "set of conditions on which to raise StopAsyncIteration:\n" \
    "\n" \
    "    TIMEOUT - timeout has elapsed\n" \
    "    CLOSED  - server/connection has closed.\n" \
    "\n" \
    "Otherwise None will be returned on timeout, and the usual BrokenPipeError" \
    " exception will be raised when the connection is closed."
    TIMEOUT = 1
    CLOSED = 2
#end STOP_ON

class Connection(TaskKeeper) :
    "wrapper around a DBusConnection object. Do not instantiate directly; use the open" \
    " or bus_get methods."
    # <https://dbus.freedesktop.org/doc/api/html/group__DBusConnection.html>

    __slots__ = \
      (
        "_dbobj",
        "_filters",
        "_match_actions",
        "_receive_queue",
        "_receive_queue_enabled",
        "_awaiting_receive",
        "_user_data",
        # need to keep references to ctypes-wrapped functions
        # so they don't disappear prematurely:
        "_object_paths",
        "_add_watch_function",
        "_remove_watch_function",
        "_toggled_watch_function",
        "_free_watch_data",
        "_add_timeout_function",
        "_remove_timeout_function",
        "_toggled_timeout_function",
        "_free_timeout_data",
        "_wakeup_main",
        "_free_wakeup_main_data",
        "_dispatch_status",
        "_free_dispatch_status_data",
        "_allow_unix_user",
        "_free_unix_user_data",
      ) # to forestall typos

    _instances = WeakValueDictionary()
    _shared_connections = [None, None]

    def __new__(celf, _dbobj) :
        self = celf._instances.get(_dbobj)
        if self  is None :
            self = super().__new__(celf)
            super()._init(self)
            self._dbobj = _dbobj
            self._user_data = {}
            self._filters = {}
            self._match_actions = {}
            self._receive_queue = None
            self._receive_queue_enabled = set()
            self._awaiting_receive = []
            self._object_paths = {}
            celf._instances[_dbobj] = self
        else :
            dbus.dbus_connection_unref(self._dbobj)
              # lose extra reference created by caller
        #end if
        return \
            self
    #end __new__

    def __del__(self) :
        if self._dbobj  is not None :
            if self.loop  is not None :
                # remove via direct low-level libdbus calls
                dbus.dbus_connection_set_watch_functions(self._dbobj, None, None, None, None, None)
                dbus.dbus_connection_set_timeout_functions(self._dbobj, None, None, None, None, None)
                self.loop = None
            #end if
            # Any entries still in super(TaskKeeper, self)._cur_tasks will be lost
            # at this point. I leave it to asyncio to report them as destroyed
            # while still pending, and the caller to notice this as a program bug.
            dbus.dbus_connection_unref(self._dbobj)
            self._dbobj = None
        #end if
    #end __del__

    @classmethod
    def open(celf, address, private, error = None) :
        "opens a Connection to a specified address, separate from the" \
        " system or session buses."
        error, my_error = _get_error(error)
        result = (dbus.dbus_connection_open, dbus.dbus_connection_open_private)[private](address.encode(), error._dbobj)
        my_error.raise_if_set()
        if result  is not None :
            result = celf(result)
        #end if
        return \
            result
    #end open

    @classmethod
    async def open_async(celf, address, private, error = None, loop = None, timeout = DBUS.TIMEOUT_INFINITE) :
        "opens a Connection to a specified address, separate from the" \
        " system or session buses."
        # There is no nonblocking version of dbus_connection_open/dbus_connection_open_private,
        # so I invoke it in a separate thread.

        if loop  is None :
            loop = asyncio.get_event_loop()
        #end if
        error, my_error = _get_error(error)
        if timeout == DBUS.TIMEOUT_USE_DEFAULT :
            timeout = DBUSX.DEFAULT_TIMEOUT
        elif timeout == DBUS.TIMEOUT_INFINITE :
            timeout = None
        #end if
        try :
            result = await call_async \
              (
                func = (dbus.dbus_connection_open, dbus.dbus_connection_open_private)[private],
                funcargs = (address.encode(), error._dbobj),
                timeout = timeout,
                abort = dbus.dbus_connection_unref,
                loop = loop
              )
        except TimeoutError :
            result = None
            error.set(DBUS.ERROR_TIMEOUT, "connection did not open in time")
        #end try
        my_error.raise_if_set()
        if result  is not None :
            result = celf(result)
            result.attach_asyncio(loop)
        #end if
        return \
            result
    #end open_async

    def _flush_awaiting_receive(self) :
        if self._receive_queue  is not None :
            while len(self._awaiting_receive) != 0 :
                waiting = self._awaiting_receive.pop(0)
                waiting.set_exception(BrokenPipeError("async receives have been disabled"))
            #end while
        #end if
    #end _flush_awaiting_receive

    def close(self) :
        self._flush_awaiting_receive()
        dbus.dbus_connection_close(self._dbobj)
    #end close

    @property
    def is_connected(self) :
        return \
            dbus.dbus_connection_get_is_connected(self._dbobj) != 0
    #end is_connected

    @property
    def is_authenticated(self) :
        return \
            dbus.dbus_connection_get_is_authenticated(self._dbobj) != 0
    #end is_authenticated

    @property
    def is_anonymous(self) :
        return \
            dbus.dbus_connection_get_is_anonymous(self._dbobj) != 0
    #end is_anonymous

    @property
    def server_id(self) :
        "asks the server at the other end for its unique id."
        c_result = dbus.dbus_connection_get_server_id(self._dbobj)
        result = ct.cast(c_result, ct.c_char_p).value.decode()
        dbus.dbus_free(c_result)
        return \
            result
    #end server_id

    def can_send_type(self, type_code) :
        "can this Connection send values of the specified TYPE_XXX code." \
        " Mainly useful for checking if we can send TYPE_UNIX_FD values."
        return \
            dbus.dbus_connection_can_send_type(self._dbobj, type_code) != 0
    #end can_send_type

    def set_exit_on_disconnect(self, exit_on_disconnect) :
        dbus.dbus_connection_set_exit_on_disconnect(self._dbobj, exit_on_disconnect)
    #end set_exit_on_disconnect

    def preallocate_send(self) :
        result = dbus.dbus_connection_preallocate_send(self._dbobj)
        if result  is None :
            raise CallFailed("dbus_connection_preallocate_send")
        #end if
        return \
            PreallocatedSend(result, self)
    #end preallocate_send

    def send_preallocated(self, preallocated, message) :
        if not isinstance(preallocated, PreallocatedSend) or not isinstance(message, Message) :
            raise TypeError("preallocated must be a PreallocatedSend and message must be a Message")
        #end if
        assert not preallocated._sent, "preallocated has already been sent"
        serial = ct.c_uint()
        dbus.dbus_connection_send_preallocated(self._dbobj, preallocated._dbobj, message._dbobj, ct.byref(serial))
        preallocated._sent = True
        return \
            serial.value
    #end send_preallocated

    def send(self, message) :
        "puts a message in the outgoing queue."
        if not isinstance(message, Message) :
            raise TypeError("message must be a Message")
        #end if
        serial = ct.c_uint()
        if not dbus.dbus_connection_send(self._dbobj, message._dbobj, ct.byref(serial)) :
            raise CallFailed("dbus_connection_send")
        #end if
        return \
            serial.value
    #end send

    def send_with_reply(self, message, timeout = DBUS.TIMEOUT_USE_DEFAULT) :
        "puts a message in the outgoing queue and returns a PendingCall" \
        " that you can use to obtain the reply."
        if not isinstance(message, Message) :
            raise TypeError("message must be a Message")
        #end if
        pending_call = ct.c_void_p()
        if not dbus.dbus_connection_send_with_reply(self._dbobj, message._dbobj, ct.byref(pending_call), _get_timeout(timeout)) :
            raise CallFailed("dbus_connection_send_with_reply")
        #end if
        if pending_call.value  is not None :
            result = PendingCall(pending_call.value, self)
        else :
            result = None
        #end if
        return \
            result
    #end send_with_reply

    def send_with_reply_and_block(self, message, timeout = DBUS.TIMEOUT_USE_DEFAULT, error = None) :
        "sends a message, blocks the thread until the reply is available, and returns it."
        if not isinstance(message, Message) :
            raise TypeError("message must be a Message")
        #end if
        error, my_error = _get_error(error)
        reply = dbus.dbus_connection_send_with_reply_and_block(self._dbobj, message._dbobj, _get_timeout(timeout), error._dbobj)
        my_error.raise_if_set()
        if reply  is not None :
            result = Message(reply)
        else :
            result = None
        #end if
        return \
            result
    #end send_with_reply_and_block

    async def send_await_reply(self, message, timeout = DBUS.TIMEOUT_USE_DEFAULT) :
        "queues a message, suspends the coroutine (letting the event loop do" \
        " other things) until the reply is available, and returns it."
        if not isinstance(message, Message) :
            raise TypeError("message must be a Message")
        #end if
        assert self.loop  is not None, "no event loop to attach coroutine to"
        pending_call = ct.c_void_p()
        if not dbus.dbus_connection_send_with_reply(self._dbobj, message._dbobj, ct.byref(pending_call), _get_timeout(timeout)) :
            raise CallFailed("dbus_connection_send_with_reply")
        #end if
        if pending_call.value  is not None :
            pending = PendingCall(pending_call.value, self)
        else :
            pending = None
        #end if
        reply = None # to begin with
        if pending  is not None :
            reply = await pending.await_reply()
        #end if
        return \
            reply
    #end send_await_reply

    def flush(self) :
        "makes sure all queued messages have been sent, blocking" \
        " the thread until this is done."
        dbus.dbus_connection_flush(self._dbobj)
    #end flush

    def read_write_dispatch(self, timeout = DBUS.TIMEOUT_USE_DEFAULT) :
        "dispatches the first available message, if any. Otherwise blocks the" \
        " thread until it can read or write, and does so before returning. Returns" \
        " True as long as the Connection remains connected."
        return \
            dbus.dbus_connection_read_write_dispatch(self._dbobj, _get_timeout(timeout)) != 0
    #end read_write_dispatch

    def read_write(self, timeout = DBUS.TIMEOUT_USE_DEFAULT) :
        "blocks the thread until something can be read or written on the Connection," \
        " and does so, returning True. If the Connection has been disconnected," \
        " immediately returns False."
        return \
            dbus.dbus_connection_read_write(self._dbobj, _get_timeout(timeout)) != 0
    #end read_write

    def borrow_message(self) :
        "tries to peek at the next available message waiting to be read, returning" \
        " None if these isn’t one. Call the Message’s return_borrowed() method" \
        " to return it to the queue, or steal_borrowed() to confirm that you have" \
        " read the message."
        msg = dbus.dbus_connection_borrow_message(self._dbobj)
        if msg  is not None :
            msg = Message(msg)
            msg._conn = self
            msg._borrowed = True
        #end if
        return \
            msg
    #end borrow_message

    # returning/stealing borrowed messages done with
    # Message.return_borrowed and Message.steal_borrowed

    def pop_message(self) :
        "returns the next available incoming Message, if any, otherwise returns None." \
        " Note this bypasses all message filtering/dispatching on this Connection."
        message = dbus.dbus_connection_pop_message(self._dbobj)
        if message  is not None :
            message = Message(message)
        #end if
        return \
            message
    #end pop_message

    @property
    def dispatch_status(self) :
        "checks the state of the incoming message queue; returns a DISPATCH_XXX code."
        return \
            dbus.dbus_connection_get_dispatch_status(self._dbobj)
    #end dispatch_status

    def dispatch(self) :
        "processes any available data, adding messages into the incoming" \
        " queue as appropriate. returns a DISPATCH_XXX code."
        return \
            dbus.dbus_connection_dispatch(self._dbobj)
    #end dispatch

    def set_watch_functions(self, add_function, remove_function, toggled_function, data, free_data = None) :
        "sets the callbacks for libdbus to use to notify you of Watch objects it wants" \
        " you to manage."

        def wrap_add_function(c_watch, _data) :
            return \
                add_function(Watch(c_watch), data)
        #end wrap_add_function

        def wrap_remove_function(c_watch, _data) :
            return \
                remove_function(Watch(c_watch), data)
        #end wrap_remove_function

        def wrap_toggled_function(c_watch, _data) :
            return \
                toggled_function(Watch(c_watch), data)
        #end wrap_toggled_function

        def wrap_free_data(_data) :
            free_data(data)
        #end wrap_free_data

    #begin set_watch_functions
        self._add_watch_function = DBUS.AddWatchFunction(wrap_add_function)
        self._remove_watch_function = DBUS.RemoveWatchFunction(wrap_remove_function)
        if toggled_function  is not None :
            self._toggled_watch_function = DBUS.WatchToggledFunction(wrap_toggled_function)
        else :
            self._toggled_watch_function = None
        #end if
        if free_data  is not None :
            self._free_watch_data = DBUS.FreeFunction(wrap_free_data)
        else :
            self._free_watch_data = None
        #end if
        if not dbus.dbus_connection_set_watch_functions(self._dbobj, self._add_watch_function, self._remove_watch_function, self._toggled_watch_function, None, self._free_watch_data) :
            raise CallFailed("dbus_connection_set_watch_functions")
        #end if
    #end set_watch_functions

    def set_timeout_functions(self, add_function, remove_function, toggled_function, data, free_data = None) :
        "sets the callbacks for libdbus to use to notify you of Timeout objects it wants" \
        " you to manage."

        def wrap_add_function(c_timeout, _data) :
            return \
                add_function(Timeout(c_timeout), data)
        #end wrap_add_function

        def wrap_remove_function(c_timeout, _data) :
            return \
                remove_function(Timeout(c_timeout), data)
        #end wrap_remove_function

        def wrap_toggled_function(c_timeout, _data) :
            return \
                toggled_function(Timeout(c_timeout), data)
        #end wrap_toggled_function

        def wrap_free_data(_data) :
            free_data(data)
        #end wrap_free_data

    #begin set_timeout_functions
        self._add_timeout_function = DBUS.AddTimeoutFunction(wrap_add_function)
        self._remove_timeout_function = DBUS.RemoveTimeoutFunction(wrap_remove_function)
        if toggled_function  is not None :
            self._toggled_timeout_function = DBUS.TimeoutToggledFunction(wrap_toggled_function)
        else :
            self._toggled_timeout_function = None
        #end if
        if free_data  is not None :
            self._free_timeout_data = DBUS.FreeFunction(wrap_free_data)
        else :
            self._free_timeout_data = None
        #end if
        if not dbus.dbus_connection_set_timeout_functions(self._dbobj, self._add_timeout_function, self._remove_timeout_function, self._toggled_timeout_function, None, self._free_timeout_data) :
            raise CallFailed("dbus_connection_set_timeout_functions")
        #end if
    #end set_timeout_functions

    def set_wakeup_main_function(self, wakeup_main, data, free_data = None) :
        "sets the callback to use for libdbus to notify you that something has" \
        " happened requiring processing on the Connection."

        def wrap_wakeup_main(_data) :
            wakeup_main(data)
        #end wrap_wakeup_main

        def wrap_free_data(_data) :
            free_data(data)
        #end wrap_free_data

    #begin set_wakeup_main_function
        if wakeup_main  is not None :
            self._wakeup_main = DBUS.WakeupMainFunction(wrap_wakeup_main)
        else :
            self._wakeup_main = None
        #end if
        if free_data  is not None :
            self._free_wakeup_main_data = DBUS.FreeFunction(wrap_free_data)
        else :
            self._free_wakeup_main_data = None
        #end if
        dbus.dbus_connection_set_wakeup_main_function(self._dbobj, self._wakeup_main, None, self._free_wakeup_main_data)
    #end set_wakeup_main_function

    def set_dispatch_status_function(self, function, data, free_data = None) :
        "sets the callback to use for libdbus to notify you of a change in the" \
        " dispatch status of the Connection."

        w_self = weak_ref(self)

        def wrap_dispatch_status(_conn, status, _data) :
            function(_wderef(w_self, "connection"), status, data)
        #end wrap_dispatch_status

        def wrap_free_data(_data) :
            free_data(data)
        #end wrap_free_data

    #begin set_dispatch_status_function
        self._dispatch_status = DBUS.DispatchStatusFunction(wrap_dispatch_status)
        if free_data  is not None :
            self._free_wakeup_main_data = DBUS.FreeFunction(wrap_free_data)
        else :
            self._free_wakeup_main_data = None
        #end if
        dbus.dbus_connection_set_dispatch_status_function(self._dbobj, self._dispatch_status, None, self._free_wakeup_main_data)
    #end set_dispatch_status_function

    @property
    def unix_fd(self) :
        c_fd = ct.c_int()
        if dbus.dbus_connection_get_unix_fd(self._dbobj, ct.byref(c_fd)) :
            result = c_fd.value
        else :
            result = None
        #end if
        return \
            result
    #end unix_fd

    def fileno(self) :
        "for use with Python’s “select” functions."
        return \
            self.unix_fd
    #end fileno

    @property
    def socket(self) :
        c_fd = ct.c_int()
        if dbus.dbus_connection_get_socket(self._dbobj, ct.byref(c_fd)) :
            result = c_fd.value
        else :
            result = None
        #end if
        return \
            result
    #end socket

    @property
    def unix_process_id(self) :
        c_pid = ct.c_ulong()
        if dbus.dbus_connection_get_unix_process_id(self._dbobj, ct.byref(c_pid)) :
            result = c_pid.value
        else :
            result = None
        #end if
        return \
            result
    #end unix_process_id

    @property
    def unix_user(self) :
        c_uid = ct.c_ulong()
        if dbus.dbus_connection_get_unix_user(self._dbobj, ct.byref(c_uid)) :
            result = c_uid.value
        else :
            result = None
        #end if
        return \
            result
    #end unix_user

    # TODO: get_adt

    def set_unix_user_function(self, allow_unix_user, data, free_data = None) :
        w_self = weak_ref(self)

        def wrap_allow_unix_user(c_conn, uid, c_data) :
            return \
                allow_unix_user(_wderef(w_self, "connection"), uid, data)
        #end wrap_allow_unix_user

        def wrap_free_data(_data) :
            free_data(data)
        #end wrap_free_data

    #begin set_unix_user_function
        if allow_unix_user  is not None :
            self._allow_unix_user = DBUS.AllowUnixUserFunction(wrap_allow_unix_user)
        else :
            self._allow_unix_user = None
        #end if
        if free_data  is not None :
            self._free_unix_user_data = DBUS.FreeFunction(wrap_free_data)
        else :
            self._free_unix_user_data = None
        #end if
        dbus.dbus_connection_set_unix_user_function(self._dbobj, self._allow_unix_user, None, self._free_unix_user_data)
    #end set_unix_user_function

    def set_allow_anonymous(self, allow) :
        dbus.dbus_connection_set_allow_anonymous(self._dbobj, allow)
    #end set_allow_anonymous

    def set_route_peer_messages(self, enable) :
        dbus.dbus_connection_set_route_peer_messages(self._dbobj, enable)
    #end set_route_peer_messages

    def add_filter(self, function, user_data, free_data = None) :
        "adds a filter callback that gets to look at all incoming messages" \
        " before they get to the dispatch system. The same function can be added" \
        " multiple times as long as the user_data is different."

        w_self = weak_ref(self)

        def wrap_function(c_conn, c_message, _data) :
            self = _wderef(w_self, "connection")
            message = Message(dbus.dbus_message_ref(c_message))
            result = function(self, message, user_data)
            if asyncio.iscoroutine(result) :
                self.create_task(result)
                result = DBUS.HANDLER_RESULT_HANDLED
            #end if
            return \
                result
        #end wrap_function

        def wrap_free_data(_data) :
            free_data(user_data)
        #end wrap_free_data

    #begin add_filter
        filter_key = (function, data_key(user_data))
        filter_value = \
            {
                "function" : DBUS.HandleMessageFunction(wrap_function),
                "free_data" : (lambda : None, lambda : DBUS.FreeFunction(wrap_free_data))[free_data  is not None](),
            }
        # pass user_data id because libdbus identifies filter entry by both function address and user data address
        if not dbus.dbus_connection_add_filter(self._dbobj, filter_value["function"], filter_key[1], filter_value["free_data"]) :
            raise CallFailed("dbus_connection_add_filter")
        #end if
        self._filters[filter_key] = filter_value
          # need to ensure wrapped functions don’t disappear prematurely
    #end add_filter

    def remove_filter(self, function, user_data) :
        "removes a message filter added by add_filter. The filter is identified" \
        " by both the function object and the user_data that was passed."
        filter_key = (function, data_key(user_data))
        if filter_key not in self._filters :
            raise KeyError("removing nonexistent Connection filter")
        #end if
        filter_value = self._filters[filter_key]
        # pass user_data id because libdbus identifies filter entry by both function address and user data address
        dbus.dbus_connection_remove_filter(self._dbobj, filter_value["function"], filter_key[1])
        del self._filters[filter_key]
    #end remove_filter

    def register_object_path(self, path, vtable, user_data, error = None) :
        "registers an ObjectPathVTable as a dispatch handler for a specified" \
        " path within your object hierarchy."
        if not isinstance(vtable, ObjectPathVTable) :
            raise TypeError("vtable must be an ObjectPathVTable")
        #end if
        self._object_paths[path] = {"vtable" : vtable, "user_data" : user_data} # ensure it doesn’t disappear prematurely
        error, my_error = _get_error(error)
        if user_data  is not None :
            c_user_data = id(user_data)
            self._user_data[c_user_data] = user_data
        else :
            c_user_data = None
        #end if
        dbus.dbus_connection_try_register_object_path(self._dbobj, path.encode(), vtable._dbobj, c_user_data, error._dbobj)
        my_error.raise_if_set()
    #end register_object_path

    def register_fallback(self, path, vtable, user_data, error = None) :
        "registers an ObjectPathVTable as a dispatch handler for an entire specified" \
        " subtree within your object hierarchy."
        if not isinstance(vtable, ObjectPathVTable) :
            raise TypeError("vtable must be an ObjectPathVTable")
        #end if
        self._object_paths[path] = {"vtable" : vtable, "user_data" : user_data} # ensure it doesn’t disappear prematurely
        error, my_error = _get_error(error)
        if user_data  is not None :
            c_user_data = id(user_data)
            self._user_data[c_user_data] = user_data
        else :
            c_user_data = None
        #end if
        dbus.dbus_connection_try_register_fallback(self._dbobj, path.encode(), vtable._dbobj, c_user_data, error._dbobj)
        my_error.raise_if_set()
    #end register_fallback

    def unregister_object_path(self, path) :
        "removes a previously-registered ObjectPathVTable handler at a specified" \
        " point (single object or entire subtree) within your object hierarchy."
        if path not in self._object_paths :
            raise KeyError("unregistering unregistered path")
        #end if
        if not dbus.dbus_connection_unregister_object_path(self._dbobj, path.encode()) :
            raise CallFailed("dbus_connection_unregister_object_path")
        #end if
        user_data = self._object_paths[path]["user_data"]
        c_user_data = id(user_data)
        nr_remaining_refs = sum(int(self._object_paths[p]["user_data"] == user_data) for p in self._object_paths if p != path)
        if nr_remaining_refs == 0 :
            try :
                del self._user_data[c_user_data]
            except KeyError :
                pass
            #end try
        #end if
        del self._object_paths[path]
    #end unregister_object_path

    def get_object_path_data(self, path) :
        "returns the user_data you passed when previously registering an ObjectPathVTable" \
        " that covers this path in your object hierarchy, or None if no suitable match" \
        " could be found."
        c_data_p = ct.c_void_p()
        if not dbus.dbus_connection_get_object_path_data(self._dbobj, path.encode(), ct.byref(c_data_p)) :
            raise CallFailed("dbus_connection_get_object_path_data")
        #end if
        return \
            self._user_data.get(c_data_p.value)
    #end get_object_path_data

    def list_registered(self, parent_path) :
        "lists all the object paths for which you have ObjectPathVTable handlers registered."
        child_entries = ct.POINTER(ct.c_char_p)()
        if not dbus.dbus_connection_list_registered(self._dbobj, parent_path.encode(), ct.byref(child_entries)) :
            raise CallFailed("dbus_connection_list_registered")
        #end if
        result = []
        i = 0
        while True :
            entry = child_entries[i]
            if entry  is None :
                break
            result.append(entry.decode())
            i += 1
        #end while
        dbus.dbus_free_string_array(child_entries)
        return \
            result
    #end list_registered

    @staticmethod
    def _queue_received_message(self, message, _) :
        # message filter which queues messages as appropriate for receive_message_async.
        # Must be static so same function object can be passed to all add_filter/remove_filter
        # calls.
        queueit = message.type in self._receive_queue_enabled
        if queueit :
            self._receive_queue.append(message)
            while len(self._awaiting_receive) != 0 :
                # wake them all up, because I don’t know what message types
                # each might be waiting for
                waiting = self._awaiting_receive.pop(0)
                waiting.set_result(True) # result actually ignored
            #end while
        #end if
        return \
            (DBUS.HANDLER_RESULT_NOT_YET_HANDLED, DBUS.HANDLER_RESULT_HANDLED)[queueit]
    #end _queue_received_message

    def enable_receive_message(self, queue_types) :
        "enables/disables message types for reception via receive_message_async." \
        " queue_types is a set or sequence of DBUS.MESSAGE_TYPE_XXX values for" \
        " the types of messages to be put into the receive queue, or None to" \
        " disable all message types; this replaces queue_types passed to" \
        " any prior enable_receive_message_async call on this Connection."
        assert self.loop  is not None, "no event loop to attach coroutines to"
        enable = queue_types  is not None and len(queue_types) != 0
        if (
                enable
            and
                not all
                  (
                        m
                    in
                        (
                            DBUS.MESSAGE_TYPE_METHOD_CALL,
                            DBUS.MESSAGE_TYPE_METHOD_RETURN,
                            DBUS.MESSAGE_TYPE_ERROR,
                            DBUS.MESSAGE_TYPE_SIGNAL,
                        )
                    for m in queue_types
                  )
        ) :
            raise TypeError("invalid message type in queue_types: %s" % repr(queue_types))
        #end if
        if enable :
            if self._receive_queue  is None :
                self.add_filter(self._queue_received_message, None)
                self._receive_queue = []
            #end if
            self._receive_queue_enabled.clear()
            self._receive_queue_enabled.update(queue_types)
        else :
            if self._receive_queue  is not None :
                self._flush_awaiting_receive()
                self.remove_filter(self._queue_received_message, None)
                self._receive_queue = None
            #end if
        #end if
    #end enable_receive_message

    async def receive_message_async(self, want_types = None, timeout = DBUS.TIMEOUT_INFINITE) :
        "receives the first available queued message of an appropriate type, blocking" \
        " if none is available and timeout is nonzero. Returns None if the timeout" \
        " elapses without a suitable message becoming available. want_types can be" \
        " None to receive any of the previously-enabled message types, or a set or" \
        " sequence of DBUS.MESSAGE_TYPE_XXX values to look only for messages of those" \
        " types.\n" \
        "\n" \
        "You must have previously made a call to enable_receive_message to enable" \
        " queueing of one or more message types on this Connection."
        assert self._receive_queue  is not None, "receive_message_async not enabled"
        # should I check if want_types contains anything not in self._receive_queue_enabled?
        if timeout == DBUS.TIMEOUT_USE_DEFAULT :
            timeout = DBUSX.DEFAULT_TIMEOUT
        #end if
        if timeout != DBUS.TIMEOUT_INFINITE :
            finish_time = self.loop.time() + timeout
        else :
            finish_time = None
        #end if
        result = ... # indicates “watch this space”
        while True :
            # keep rescanning queue until got something or timeout
            index = 0 # start next queue scan
            while True :
                if index == len(self._receive_queue) :
                    # nothing currently suitable on queue
                    if (
                            timeout == 0
                        or
                                finish_time  is not None
                            and
                                self.loop.time() > finish_time
                    ) :
                        # waited too long, give up
                        result = None
                        break
                    #end if
                    if not self.is_connected :
                        raise BrokenPipeError("Connection has been disconnected")
                    #end if
                    # wait and see if something turns up
                    awaiting = self.loop.create_future()
                    self._awaiting_receive.append(awaiting)
                    if finish_time  is not None :
                        wait_timeout = finish_time - self.loop.time()
                    else :
                        wait_timeout = None
                    #end if
                    await asyncio.wait \
                      (
                        (awaiting,),
                        loop = self.loop,
                        timeout = wait_timeout
                      )
                        # ignore done & pending results because they
                        # don’t match up with future I’m waiting for
                    try :
                        self._awaiting_receive.remove(awaiting)
                    except ValueError :
                        pass
                    #end try
                    awaiting.cancel()
                      # just to avoid “Future exception was never retrieved” message
                    break # start new queue scan
                #end if
                # check next queue item
                msg = self._receive_queue[index]
                if want_types  is None or msg.type in want_types :
                    # caller wants this one
                    result = msg
                    self._receive_queue.pop(index) # remove msg from queue
                    break
                #end if
                index += 1
            #end while
            if result != ... :
                # either got something or given up
                break
        #end while
        return \
            result
    #end receive_message_async

    def iter_messages_async(self, want_types = None, stop_on = None, timeout = DBUS.TIMEOUT_INFINITE) :
        "wrapper around receive_message_async() to allow use with an async-for statement." \
        " Lets you write\n" \
        "\n" \
        "    async for message in «conn».iter_messages_async(«want_types», «stop_on», «timeout») :" \
        "        «process message»\n" \
        "    #end for\n" \
        "\n" \
        "to receive and process messages in a loop. stop_on is an optional set of" \
        " STOP_ON.xxx values indicating the conditions under which the iterator will" \
        " raise StopAsyncIteration to terminate the loop."
        if stop_on  is None :
            stop_on = frozenset()
        elif (
                not isinstance(stop_on, (set, frozenset))
            or
                not all(isinstance(elt, STOP_ON) for elt in stop_on)
        ) :
            raise TypeError("stop_on must be None or set of STOP_ON")
        #end if
        assert self._receive_queue  is not None, "receive_message_async not enabled"
        return \
            _MsgAiter(self, want_types, stop_on, timeout)
    #end iter_messages_async

    # TODO: allocate/free data slot -- staticmethods
    # TODO: get/set data

    def set_change_sigpipe(self, will_modify_sigpipe) :
        dbus.dbus_connection_set_change_sigpipe(self._dbobj, will_modify_sigpipe)
    #end set_change_sigpipe

    @property
    def max_message_size(self) :
        return \
            dbus.dbus_connection_get_max_message_size(self._dbobj)
    #end max_message_size

    @max_message_size.setter
    def max_message_size(self, size) :
        dbus.dbus_connection_set_max_message_size(self._dbobj, size)
    #end max_message_size

    @property
    def max_received_size(self) :
        return \
            dbus.dbus_connection_get_max_received_size(self._dbobj)
    #end max_received_size

    @max_received_size.setter
    def max_received_size(self, size) :
        dbus.dbus_connection_set_max_received_size(self._dbobj, size)
    #end max_received_size

    @property
    def max_message_unix_fds(self) :
        return \
            dbus.dbus_connection_get_max_message_unix_fds(self._dbobj)
    #end max_message_unix_fds

    @max_message_unix_fds.setter
    def max_message_unix_fds(self, size) :
        dbus.dbus_connection_set_max_message_unix_fds(self._dbobj, size)
    #end max_message_unix_fds

    @property
    def max_received_unix_fds(self) :
        return \
            dbus.dbus_connection_get_max_received_unix_fds(self._dbobj)
    #end max_received_unix_fds

    @max_received_unix_fds.setter
    def max_received_unix_fds(self, size) :
        dbus.dbus_connection_set_max_received_unix_fds(self._dbobj, size)
    #end max_received_unix_fds

    @property
    def outgoing_size(self) :
        return \
            dbus.dbus_connection_get_outgoing_size(self._dbobj)
    #end outgoing_size

    @property
    def outgoing_unix_fds(self) :
        return \
            dbus.dbus_connection_get_outgoing_unix_fds(self._dbobj)
    #end outgoing_unix_fds

    @property
    def has_messages_to_send(self) :
        return \
            dbus.dbus_connection_has_messages_to_send(self._dbobj) != 0
    #end has_messages_to_send

    # message bus APIs
    # <https://dbus.freedesktop.org/doc/api/html/group__DBusBus.html>

    @classmethod
    def bus_get(celf, type, private, error = None) :
        "returns a Connection to one of the predefined D-Bus buses; type is a BUS_xxx value."
        error, my_error = _get_error(error)
        result = (dbus.dbus_bus_get, dbus.dbus_bus_get_private)[private](type, error._dbobj)
        my_error.raise_if_set()
        if result  is not None :
            result = celf(result)
        #end if
        return \
            result
    #end bus_get

    @classmethod
    async def bus_get_async(celf, type, private, error = None, loop = None, timeout = DBUS.TIMEOUT_USE_DEFAULT) :
        if loop  is None :
            loop = asyncio.get_event_loop()
        #end if
        assert type in (DBUS.BUS_SESSION, DBUS.BUS_SYSTEM, DBUS.BUS_STARTER), \
            "bus type must be BUS_SESSION, BUS_SYSTEM or BUS_STARTER"
        if type == DBUS.BUS_STARTER :
            starter_type = os.environ.get(DBUSX.STARTER_BUS_ADDRESS_TYPE)
            is_system_bus = starter_type  is not None and starter_type == DBUSX.BUS_TYPE_SYSTEM
            addr = os.environ.get(DBUSX.STARTER_BUS_ADDRESS_VAR)
        else :
            is_system_bus = type == DBUS.BUS_SYSTEM
            addr = os.environ.get \
              (
                (DBUSX.SESSION_BUS_ADDRESS_VAR, DBUSX.SYSTEM_BUS_ADDRESS_VAR)[is_system_bus]
              )
        #end if
        if not private and celf._shared_connections[is_system_bus]  is not None :
            result = celf._shared_connections[is_system_bus]
        else :
            if addr  is None :
                addr = (DBUSX.SESSION_BUS_ADDRESS, DBUSX.SYSTEM_BUS_ADDRESS)[is_system_bus]
            #end if
            try :
                result = await celf.open_async(addr, private, error, loop, timeout)
                if error  is not None and error.is_set :
                    raise _Abort
                #end if
                await result.bus_register_async(error = error, timeout = timeout)
                if error  is not None and error.is_set :
                    raise _Abort
                #end if
                if not private :
                    celf._shared_connections[is_system_bus] = result
                #end if
            except _Abort :
                result = None
            #end try
        #end if
        return \
            result
    #end bus_get_async

    def bus_register(self, error = None) :
        "Only to be used if you created the Connection with open() instead of bus_get();" \
        " sends a “Hello” message to the D-Bus daemon to get a unique name assigned." \
        " Can only be called once."
        error, my_error = _get_error(error)
        dbus.dbus_bus_register(self._dbobj, error._dbobj)
        my_error.raise_if_set()
    #end bus_register

    async def bus_register_async(self, error = None, timeout = DBUS.TIMEOUT_USE_DEFAULT) :
        "Only to be used if you created the Connection with open() instead of bus_get();" \
        " sends a “Hello” message to the D-Bus daemon to get a unique name assigned." \
        " Can only be called once."
        assert self.loop  is not None, "no event loop to attach coroutine to"
        assert self.bus_unique_name  is None, "bus already registered"
        message = Message.new_method_call \
          (
            destination = DBUS.SERVICE_DBUS,
            path = DBUS.PATH_DBUS,
            iface = DBUS.INTERFACE_DBUS,
            method = "Hello"
          )
        reply = await self.send_await_reply(message, timeout = timeout)
        if error  is not None and reply.type == DBUS.MESSAGE_TYPE_ERROR :
            reply.set_error(error)
        else :
            self.bus_unique_name = reply.expect_return_objects("s")[0]
        #end if
    #end bus_register_async

    @property
    def bus_unique_name(self) :
        "returns None if the bus connection has not been registered. Note that the" \
        " unique_name can only be set once."
        result = dbus.dbus_bus_get_unique_name(self._dbobj)
        if result  is not None :
            result = result.decode()
        #end if
        return \
            result
    #end bus_unique_name

    @bus_unique_name.setter
    def bus_unique_name(self, unique_name) :
        if not dbus.dbus_bus_set_unique_name(self._dbobj, unique_name.encode()) :
            raise CallFailed("dbus_bus_set_unique_name")
        #end if
    #end bus_unique_name

    #+
    # Calls to D-Bus Daemon
    #-

    @property
    def bus_id(self) :
        my_error = Error()
        c_result = dbus.dbus_bus_get_id(self._dbobj, my_error._dbobj)
        my_error.raise_if_set()
        result = ct.cast(c_result, ct.c_char_p).value.decode()
        dbus.dbus_free(c_result)
        return \
            result
    #end bus_id

    @property
    async def bus_id_async(self) :
        message = Message.new_method_call \
          (
            destination = DBUS.SERVICE_DBUS,
            path = DBUS.PATH_DBUS,
            iface = DBUS.INTERFACE_DBUS,
            method = "GetId"
          )
        reply = await self.send_await_reply(message)
        return \
            reply.expect_return_objects("s")[0]
    #end bus_id_async

    def bus_get_unix_user(self, name, error = None) :
        error, my_error = _get_error(error)
        result = dbus.dbus_bus_get_unix_user(self._dbobj, name.encode(), error._dbobj)
        my_error.raise_if_set()
        return \
            result
    #end bus_get_unix_user

    async def bus_get_unix_user_async(self, name, error = None, timeout = DBUS.TIMEOUT_USE_DEFAULT) :
        message = Message.new_method_call \
          (
            destination = DBUS.SERVICE_DBUS,
            path = DBUS.PATH_DBUS,
            iface = DBUS.INTERFACE_DBUS,
            method = "GetConnectionUnixUser"
          )
        message.append_objects("s", name)
        reply = await self.send_await_reply(message, timeout = timeout)
        if error  is not None and reply.type == DBUS.MESSAGE_TYPE_ERROR :
            reply.set_error(error)
            result = None
        else :
            result = reply.expect_return_objects("u")[0]
        #end if
        return \
            result
    #end bus_get_unix_user_async

    def bus_request_name(self, name, flags, error = None) :
        "asks the D-Bus daemon to register the specified bus name on your behalf," \
        " blocking the thread until the reply is received. flags is a combination of" \
        " NAME_FLAG_xxx bits. Result will be a REQUEST_NAME_REPLY_xxx value or -1 on error."
        error, my_error = _get_error(error)
        result = dbus.dbus_bus_request_name(self._dbobj, name.encode(), flags, error._dbobj)
        my_error.raise_if_set()
        return \
            result
    #end bus_request_name

    async def bus_request_name_async(self, name, flags, error = None, timeout = DBUS.TIMEOUT_USE_DEFAULT) :
        "asks the D-Bus daemon to register the specified bus name on your behalf. flags is" \
        " a combination of NAME_FLAG_xxx bits. Result will be a REQUEST_NAME_REPLY_xxx value" \
        " or None on error."
        message = Message.new_method_call \
          (
            destination = DBUS.SERVICE_DBUS,
            path = DBUS.PATH_DBUS,
            iface = DBUS.INTERFACE_DBUS,
            method = "RequestName"
          )
        message.append_objects("su", name, flags)
        reply = await self.send_await_reply(message, timeout = timeout)
        if error  is not None and reply.type == DBUS.MESSAGE_TYPE_ERROR :
            reply.set_error(error)
            result = None
        else :
            result = reply.expect_return_objects("u")[0]
        #end if
        return \
            result
    #end bus_request_name_async

    def bus_release_name(self, name, error = None) :
        "asks the D-Bus daemon to release your registration of the specified bus name," \
        " blocking the thread until the reply is received."
        error, my_error = _get_error(error)
        result = dbus.dbus_bus_release_name(self._dbobj, name.encode(), error._dbobj)
        my_error.raise_if_set()
        return \
            result
    #end bus_release_name

    async def bus_release_name_async(self, name, error = None, timeout = DBUS.TIMEOUT_USE_DEFAULT) :
        "asks the D-Bus daemon to release your registration of the specified bus name."
        message = Message.new_method_call \
          (
            destination = DBUS.SERVICE_DBUS,
            path = DBUS.PATH_DBUS,
            iface = DBUS.INTERFACE_DBUS,
            method = "ReleaseName"
          )
        message.append_objects("s", name)
        reply = await self.send_await_reply(message, timeout = timeout)
        if error  is not None and reply.type == DBUS.MESSAGE_TYPE_ERROR :
            reply.set_error(error)
            result = None
        else :
            result = reply.expect_return_objects("u")[0]
        #end if
        return \
            result
    #end bus_release_name_async

    def bus_name_has_owner(self, name, error = None) :
        "asks the D-Bus daemon if anybody has claimed the specified bus name, blocking" \
        " the thread until the reply is received."
        error, my_error = _get_error(error)
        result = dbus.dbus_bus_name_has_owner(self._dbobj, name.encode(), error._dbobj)
        my_error.raise_if_set()
        return \
            result
    #end bus_name_has_owner

    async def bus_name_has_owner_async(self, name, error = None, timeout = DBUS.TIMEOUT_USE_DEFAULT) :
        "asks the D-Bus daemon if anybody has claimed the specified bus name."
        message = Message.new_method_call \
          (
            destination = DBUS.SERVICE_DBUS,
            path = DBUS.PATH_DBUS,
            iface = DBUS.INTERFACE_DBUS,
            method = "NameHasOwner"
          )
        message.append_objects("s", name)
        reply = await self.send_await_reply(message, timeout = timeout)
        if error  is not None and reply.type == DBUS.MESSAGE_TYPE_ERROR :
            reply.set_error(error)
            result = None
        else :
            result = reply.expect_return_objects("b")[0]
        #end if
        return \
            result
    #end bus_name_has_owner_async

    def bus_start_service_by_name(self, name, flags = 0, error = None) :
        error, my_error = _get_error(error)
        outflags = ct.c_uint()
        success = dbus.dbus_bus_start_service_by_name(self._dbobj, name.encode(), flags, ct.byref(outflags), error._dbobj)
        my_error.raise_if_set()
        return \
            outflags.value
    #end bus_start_service_by_name

    async def bus_start_service_by_name_async(self, name, flags = 0, error = None, timeout = DBUS.TIMEOUT_USE_DEFAULT) :
        message = Message.new_method_call \
          (
            destination = DBUS.SERVICE_DBUS,
            path = DBUS.PATH_DBUS,
            iface = DBUS.INTERFACE_DBUS,
            method = "StartServiceByName"
          )
        message.append_objects("su", name, flags)
        reply = await self.send_await_reply(message, timeout = timeout)
        if error  is not None and reply.type == DBUS.MESSAGE_TYPE_ERROR :
            reply.set_error(error)
            result = None
        else :
            result = reply.expect_return_objects("u")[0]
        #end if
        return \
            result
    #end bus_start_service_by_name

    def bus_add_match(self, rule, error = None) :
        "adds a match rule for messages you want to receive. By default you get all" \
        " messages addressed to your bus name(s); but you can use this, for example," \
        " to request notification of signals indicating useful events on the system."
        error, my_error = _get_error(error)
        dbus.dbus_bus_add_match(self._dbobj, format_rule(rule).encode(), error._dbobj)
        my_error.raise_if_set()
    #end bus_add_match

    async def bus_add_match_async(self, rule, error = None, timeout = DBUS.TIMEOUT_USE_DEFAULT) :
        "adds a match rule for messages you want to receive. By default you get all" \
        " messages addressed to your bus name(s); but you can use this, for example," \
        " to request notification of signals indicating useful events on the system."
        message = Message.new_method_call \
          (
            destination = DBUS.SERVICE_DBUS,
            path = DBUS.PATH_DBUS,
            iface = DBUS.INTERFACE_DBUS,
            method = "AddMatch"
          )
        message.append_objects("s", format_rule(rule))
        reply = await self.send_await_reply(message, timeout = timeout)
        if error  is not None and reply.type == DBUS.MESSAGE_TYPE_ERROR :
            reply.set_error(error)
        else :
            reply.expect_return_objects("")
        #end if
    #end bus_add_match_async

    def bus_remove_match(self, rule, error = None) :
        "removes a previously-added match rule for messages you previously wanted" \
        " to receive."
        error, my_error = _get_error(error)
        dbus.dbus_bus_remove_match(self._dbobj, format_rule(rule).encode(), error._dbobj)
        my_error.raise_if_set()
    #end bus_remove_match

    async def bus_remove_match_async(self, rule, error = None, timeout = DBUS.TIMEOUT_USE_DEFAULT) :
        "removes a previously-added match rule for messages you previously wanted" \
        " to receive."
        message = Message.new_method_call \
          (
            destination = DBUS.SERVICE_DBUS,
            path = DBUS.PATH_DBUS,
            iface = DBUS.INTERFACE_DBUS,
            method = "RemoveMatch"
          )
        message.append_objects("s", format_rule(rule))
        reply = await self.send_await_reply(message, timeout = timeout)
        if error  is not None and reply.type == DBUS.MESSAGE_TYPE_ERROR :
            reply.set_error(error)
        else :
            reply.expect_return_objects("")
        #end if
    #end bus_remove_match_async

    @staticmethod
    def _rule_action_match(self, message, _) :
        # installed as a message filter to invoke actions corresponding to rules
        # that the message matches. To avoid spurious method-not-handled errors
        # from eavesdropping on method calls not addressed to me, this routine
        # always returns a “handled” status. That means this same Connection
        # object should not be used for both eavesdropping and for normal
        # method calls.
        handled = False
        for entry in self._match_actions.values() :
            if matches_rule(message, entry.rule) :
                for action in entry.actions :
                    result = action.func(self, message, action.user_data)
                    if asyncio.iscoroutine(result) :
                        self.create_task(result)
                    #end if
                #end for
                handled = True # passed to at least one handler
            #end if
        #end for
        return \
            (DBUS.HANDLER_RESULT_NOT_YET_HANDLED, DBUS.HANDLER_RESULT_HANDLED)[handled]
    #end _rule_action_match

    def bus_add_match_action(self, rule, func, user_data, error = None) :
        "adds a message filter that invokes func(conn, message, user_data)" \
        " for each incoming message that matches the specified rule. Unlike" \
        " the underlying add_filter and bus_add_match calls, this allows you" \
        " to associate the action with the particular matching rule.\n" \
        "\n" \
        "Note that the message filter installed to process these rules always" \
        " returns a DBUS.HANDLER_RESULT_HANDLED status; so either only use this" \
        " to listen for signals, or do not use the same Connection object to" \
        " handle normal method calls."
        rulekey = format_rule(rule)
        rule = unformat_rule(rule)
        if rulekey not in self._match_actions :
            self.bus_add_match(rulekey, error) # could fail here with bad rule
            if error  is None or not error.is_set :
                if len(self._match_actions) == 0 :
                    self.add_filter(self._rule_action_match, None)
                #end if
                self._match_actions[rulekey] = _MatchActionEntry(rule)
            #end if
        #end if
        if error  is None or not error.is_set :
            self._match_actions[rulekey].actions.add(_MatchActionEntry._Action(func, user_data))
        #end if
    #end bus_add_match_action

    def bus_remove_match_action(self, rule, func, user_data, error = None) :
        "removes a message filter previously installed with bus_add_match_action."
        rulekey = format_rule(rule)
        rule = unformat_rule(rule)
        self._match_actions[rulekey].actions.remove(_MatchActionEntry._Action(func, user_data))
        if len(self._match_actions[rulekey].actions) == 0 :
            self.bus_remove_match(rulekey, error) # shouldn’t fail!
            del self._match_actions[rulekey]
            if len(self._match_actions) == 0 :
                self.remove_filter(self._rule_action_match, None)
            #end if
        #end if
    #end bus_remove_match_action

    async def bus_add_match_action_async(self, rule, func, user_data, error = None, timeout = DBUS.TIMEOUT_USE_DEFAULT) :
        "adds a message filter that invokes func(conn, message, user_data)" \
        " for each incoming message that matches the specified rule. Unlike" \
        " the underlying add_filter and bus_add_match calls, this allows you" \
        " to associate the action with the particular matching rule.\n" \
        "\n" \
        "Note that the message filter installed to process these rules always" \
        " returns a DBUS.HANDLER_RESULT_HANDLED status; so either only use this" \
        " to listen for signals, or do not use the same Connection object to" \
        " handle normal method calls."
        rulekey = format_rule(rule)
        rule = unformat_rule(rule)
        if rulekey not in self._match_actions :
            await self.bus_add_match_async(rulekey, error, timeout) # could fail here with bad rule
            if error  is None or not error.is_set :
                if len(self._match_actions) == 0 :
                    self.add_filter(self._rule_action_match, None)
                #end if
                self._match_actions[rulekey] = _MatchActionEntry(rule)
            #end if
        #end if
        if error  is None or not error.is_set :
            self._match_actions[rulekey].actions.add(_MatchActionEntry._Action(func, user_data))
        #end if
    #end bus_add_match_action_async

    async def bus_remove_match_action_async(self, rule, func, user_data, error = None, timeout = DBUS.TIMEOUT_USE_DEFAULT) :
        "removes a message filter previously installed with bus_add_match_action."
        rulekey = format_rule(rule)
        rule = unformat_rule(rule)
        self._match_actions[rulekey].actions.remove(_MatchActionEntry._Action(func, user_data))
        if len(self._match_actions[rulekey].actions) == 0 :
            await self.bus_remove_match_async(rulekey, error, timeout) # shouldn’t fail!
            del self._match_actions[rulekey]
            if len(self._match_actions) == 0 :
                self.remove_filter(self._rule_action_match, None)
            #end if
        #end if
    #end bus_remove_match_action_async

    def become_monitor(self, rules) :
        "turns the connection into one that can only receive monitoring messages."
        message = Message.new_method_call \
          (
            destination = DBUS.SERVICE_DBUS,
            path = DBUS.PATH_DBUS,
            iface = DBUS.INTERFACE_MONITORING,
            method = "BecomeMonitor"
          )
        message.append_objects("asu", (list(format_rule(rule) for rule in rules)), 0)
        self.send(message)
    #end become_monitor

    #+
    # End calls to D-Bus Daemon
    #-

    def attach_asyncio(self, loop = None) :
        "attaches this Connection object to an asyncio event loop. If none is" \
        " specified, the default event loop (as returned from asyncio.get_event_loop()" \
        " is used."

        w_self = weak_ref(self)
          # to avoid a reference cycle

        def dispatch() :
            return \
                _wderef(w_self, "connection").dispatch()
        #end dispatch

    #begin attach_asyncio
        assert self.loop  is None, "already attached to an event loop"
        _loop_attach(self, loop, dispatch)
    #end attach_asyncio

#end Connection

class _MsgAiter :
    # internal class for use by Connection.iter_messages_async (above).

    def __init__(self, conn, want_types, stop_on, timeout) :
        self.conn = conn
        self.want_types = want_types
        self.stop_on = stop_on
        self.timeout = timeout
    #end __init__

    def __aiter__(self) :
        # I’m my own iterator.
        return \
            self
    #end __aiter__

    async def __anext__(self) :
        stop_iter = False
        try :
            result = await self.conn.receive_message_async(self.want_types, self.timeout)
            if result  is None and STOP_ON.TIMEOUT in self.stop_on :
                stop_iter = True
            #end if
        except BrokenPipeError :
            if STOP_ON.CLOSED not in self.stop_on :
                raise
            #end if
            stop_iter = True
        #end try
        if stop_iter :
            raise StopAsyncIteration("Connection.receive_message_async terminating")
        #end if
        return \
            result
    #end __anext__

#end _MsgAiter

class Server(TaskKeeper) :
    "wrapper around a DBusServer object. Do not instantiate directly; use" \
    " the listen method.\n" \
    "\n" \
    "You only need this if you want to use D-Bus as a communication mechanism" \
    " separate from the system/session buses provided by the D-Bus daemon: you" \
    " create a Server object listening on a specified address, and clients can" \
    " use Connection.open() to connect to you on that address."
    # <https://dbus.freedesktop.org/doc/api/html/group__DBusServer.html>

    # Doesn’t really need services of TaskKeeper for now, but might be
    # useful in future

    __slots__ = \
      (
        "_dbobj",
        "_new_connections",
        "_await_new_connections",
        "max_new_connections",
        "autoattach_new_connections",
        # need to keep references to ctypes-wrapped functions
        # so they don't disappear prematurely:
        "_new_connection_function",
        "_free_new_connection_data",
        "_add_watch_function",
        "_remove_watch_function",
        "_toggled_watch_function",
        "_free_watch_data",
        "_add_timeout_function",
        "_remove_timeout_function",
        "_toggled_timeout_function",
        "_free_timeout_data",
      ) # to forestall typos

    _instances = WeakValueDictionary()

    def __new__(celf, _dbobj) :
        self = celf._instances.get(_dbobj)
        if self  is None :
            self = super().__new__(celf)
            super()._init(self)
            self._dbobj = _dbobj
            self._new_connections = None
            self._await_new_connections = None
            self.max_new_connections = None
            self.autoattach_new_connections = True
            self._new_connection_function = None
            self._free_new_connection_data = None
            self._add_watch_function = None
            self._remove_watch_function = None
            self._toggled_watch_function = None
            self._free_watch_data = None
            self._add_timeout_function = None
            self._remove_timeout_function = None
            self._toggled_timeout_function = None
            self._free_timeout_data = None
            celf._instances[_dbobj] = self
        else :
            dbus.dbus_server_unref(self._dbobj)
              # lose extra reference created by caller
        #end if
        return \
            self
    #end __new__

    def __del__(self) :
        if self._dbobj  is not None :
            if self.loop  is not None :
                # remove via direct low-level libdbus calls
                dbus.dbus_server_set_watch_functions(self._dbobj, None, None, None, None, None)
                dbus.dbus_server_set_timeout_functions(self._dbobj, None, None, None, None, None)
                self.loop = None
            #end if
            dbus.dbus_server_unref(self._dbobj)
            self._dbobj = None
        #end if
    #end __del__

    @classmethod
    def listen(celf, address, error = None) :
        error, my_error = _get_error(error)
        result = dbus.dbus_server_listen(address.encode(), error._dbobj)
        my_error.raise_if_set()
        if result  is not None :
            result = celf(result)
        #end if
        return \
            result
    #end listen

    def _flush_awaiting_connect(self) :
        if self._await_new_connections  is not None :
            while len(self._await_new_connections) != 0 :
                waiting = self._await_new_connections.pop(0)
                waiting.set_exception(BrokenPipeError("async listens have been disabled"))
            #end while
        #end if
    #end _flush_awaiting_connect

    def disconnect(self) :
        self._flush_awaiting_connect()
        dbus.dbus_server_disconnect(self._dbobj)
    #end disconnect

    @property
    def is_connected(self) :
        return \
            dbus.dbus_server_get_is_connected(self._dbobj) != 0
    #end is_connected

    @property
    def address(self) :
        c_result = dbus.dbus_server_get_address(self._dbobj)
        if c_result  is None :
            raise CallFailed("dbus_server_get_address")
        #end if
        result = ct.cast(c_result, ct.c_char_p).value.decode()
        dbus.dbus_free(c_result)
        return \
            result
    #end address

    @property
    def id(self) :
        c_result = dbus.dbus_server_get_id(self._dbobj)
        if c_result  is None :
            raise CallFailed("dbus_server_get_id")
        #end if
        result = ct.cast(c_result, ct.c_char_p).value.decode()
        dbus.dbus_free(c_result)
        return \
            result
    #end id

    def set_new_connection_function(self, function, data, free_data = None) :
        "sets the callback for libdbus to notify you of a new incoming connection." \
        " It is up to you to save the Connection object for later processing of" \
        " messages, or close it to reject the connection attempt."

        w_self = weak_ref(self)

        def wrap_function(c_self, c_conn, _data) :
            function(_wderef(w_self, "server"), Connection(dbus.dbus_connection_ref(c_conn)), data)
              # even though this is a new connection, I still have to reference it
        #end wrap_function

        def wrap_free_data(_data) :
            free_data(data)
        #end wrap_free_data

    #begin set_new_connection_function
        assert self.loop  is None, "new connections are being managed by an event loop"
        self._new_connection_function = DBUS.NewConnectionFunction(wrap_function)
        if free_data  is not None :
            self._free_new_connection_data = DBUS.FreeFunction(wrap_free_data)
        else :
            self._free_new_connection_data = None
        #end if
        dbus.dbus_server_set_new_connection_function(self._dbobj, self._new_connection_function, None, self._free_new_connection_data)
    #end set_new_connection_function

    def set_watch_functions(self, add_function, remove_function, toggled_function, data, free_data = None) :
        "sets the callbacks for libdbus to use to notify you of Watch objects it wants" \
        " you to manage."

        def wrap_add_function(c_watch, _data) :
            return \
                add_function(Watch(c_watch), data)
        #end wrap_add_function

        def wrap_remove_function(c_watch, _data) :
            return \
                remove_function(Watch(c_watch), data)
        #end wrap_remove_function

        def wrap_toggled_function(c_watch, _data) :
            return \
                toggled_function(Watch(c_watch), data)
        #end wrap_toggled_function

        def wrap_free_data(_data) :
            free_data(data)
        #end wrap_free_data

    #begin set_watch_functions
        self._add_watch_function = DBUS.AddWatchFunction(wrap_add_function)
        self._remove_watch_function = DBUS.RemoveWatchFunction(wrap_remove_function)
        if toggled_function  is not None :
            self._toggled_watch_function = DBUS.WatchToggledFunction(wrap_toggled_function)
        else :
            self._toggled_watch_function = None
        #end if
        if free_data  is not None :
            self._free_watch_data = DBUS.FreeFunction(wrap_free_data)
        else :
            self._free_watch_data = None
        #end if
        if not dbus.dbus_server_set_watch_functions(self._dbobj, self._add_watch_function, self._remove_watch_function, self._toggled_watch_function, None, self._free_watch_data) :
            raise CallFailed("dbus_server_set_watch_functions")
        #end if
    #end set_watch_functions

    def set_timeout_functions(self, add_function, remove_function, toggled_function, data, free_data = None) :
        "sets the callbacks for libdbus to use to notify you of Timeout objects it wants" \
        " you to manage."

        def wrap_add_function(c_timeout, _data) :
            return \
                add_function(Timeout(c_timeout), data)
        #end wrap_add_function

        def wrap_remove_function(c_timeout, _data) :
            return \
                remove_function(Timeout(c_timeout), data)
        #end wrap_remove_function

        def wrap_toggled_function(c_timeout, _data) :
            return \
                toggled_function(Timeout(c_timeout), data)
        #end wrap_toggled_function

        def wrap_free_data(_data) :
            free_data(data)
        #end wrap_free_data

    #begin set_timeout_functions
        self._add_timeout_function = DBUS.AddTimeoutFunction(wrap_add_function)
        self._remove_timeout_function = DBUS.RemoveTimeoutFunction(wrap_remove_function)
        if toggled_function  is not None :
            self._toggled_timeout_function = DBUS.TimeoutToggledFunction(wrap_toggled_function)
        else :
            self._toggled_timeout_function = None
        #end if
        if free_data  is not None :
            self._free_timeout_data = DBUS.FreeFunction(wrap_free_data)
        else :
            self._free_timeout_data = None
        #end if
        if not dbus.dbus_server_set_timeout_functions(self._dbobj, self._add_timeout_function, self._remove_timeout_function, self._toggled_timeout_function, None, self._free_timeout_data) :
            raise CallFailed("dbus_server_set_timeout_functions")
        #end if
    #end set_timeout_functions

    def set_auth_mechanisms(self, mechanisms) :
        nr_mechanisms = len(mechanisms)
        c_mechanisms = (ct.c_char_p * (nr_mechanisms + 1))()
        for i in range(nr_mechanisms) :
            c_mechanisms[i] = mechanisms[i].encode()
        #end if
        c_mechanisms[nr_mechanisms] = None # marks end of array
        if not dbus.dbus_server_set_auth_mechanisms(self._dbobj, c_mechanisms) :
            raise CallFailed("dbus_server_set_auth_mechanisms")
        #end if
    #end set_auth_mechanisms

    # TODO: allocate/free slot (static methods)
    # TODO: get/set/data

    def attach_asyncio(self, loop = None) :
        "attaches this Server object to an asyncio event loop. If none is" \
        " specified, the default event loop (as returned from asyncio.get_event_loop()" \
        " is used.\n" \
        "\n" \
        "This call will also automatically attach a new_connection callback. You then use" \
        " the await_new_connection coroutine to obtain new connections. If" \
        " self.autoattach_new_connections, then Connection.attach_asyncio() will" \
        " automatically be called to handle events for the new connection."

        def new_connection(self, conn, user_data) :
            if len(self._await_new_connections) != 0 :
                awaiting = self._await_new_connections.pop(0)
                awaiting.set_result(conn)
            else :
                # put it in _new_connections queue
                if (
                        self.max_new_connections  is not None
                    and
                        len(self._new_connections) >= self.max_new_connections
                ) :
                    # too many connections pending, reject
                    conn.close()
                else :
                    self._new_connections.append(conn)
                #end if
            #end if
        #end new_connection

    #begin attach_asyncio
        assert self.loop  is None, "already attached to an event loop"
        assert self._new_connection_function  is None, "already set a new-connection function"
        self._new_connections = []
        self._await_new_connections = []
        self.set_new_connection_function(new_connection, None)
        _loop_attach(self, loop, None)
    #end attach_asyncio

    async def await_new_connection(self, timeout = DBUS.TIMEOUT_INFINITE) :
        "retrieves the next new Connection, if there is one available, otherwise" \
        " suspends the current coroutine for up to the specified timeout duration" \
        " while waiting for one to appear. Returns None if there is no new connection" \
        " within that time."
        assert self.loop  is not None, "no event loop to attach coroutine to"
        if len(self._new_connections) != 0 :
            result = self._new_connections.pop(0)
        else :
            if not self.is_connected :
                raise BrokenPipeError("Server has been disconnected")
            #end if
            if timeout == 0 :
                # might as well short-circuit the whole waiting process
                result = None
            else :
                awaiting = self.loop.create_future()
                self._await_new_connections.append(awaiting)
                if timeout == DBUS.TIMEOUT_INFINITE :
                    timeout = None
                else :
                    if timeout == DBUS.TIMEOUT_USE_DEFAULT :
                        timeout = DBUSX.DEFAULT_TIMEOUT
                    #end if
                #end if
                await asyncio.wait \
                  (
                    (awaiting,),
                    loop = self.loop,
                    timeout = timeout
                  )
                    # ignore done & pending results because they
                    # don’t match up with future I’m waiting for
                if awaiting.done() :
                    result = awaiting.result()
                else :
                    self._await_new_connections.pop(self._await_new_connections.index(awaiting))
                    result = None
                #end if
            #end if
        #end if
        if result  is not None and self.autoattach_new_connections :
            result.attach_asyncio(self.loop)
        #end if
        return \
            result
    #end await_new_connection

    def iter_connections_async(self, stop_on = None, timeout = DBUS.TIMEOUT_INFINITE) :
        "wrapper around await_new_connection() to allow use with an async-for" \
        " statement. Lets you write\n" \
        "\n" \
        "    async for conn in «server».iter_connections_async(«timeout») :" \
        "        «accept conn»\n" \
        "    #end for\n" \
        "\n" \
        "to receive and process incoming connections in a loop. stop_on is an optional set of" \
        " STOP_ON.xxx values indicating the conditions under which the iterator will" \
        " raise StopAsyncIteration to terminate the loop."
        assert self.loop  is not None, "no event loop to attach coroutine to"
        if stop_on  is None :
            stop_on = frozenset()
        elif (
                not isinstance(stop_on, (set, frozenset))
            or
                not all(isinstance(elt, STOP_ON) for elt in stop_on)
        ) :
            raise TypeError("stop_on must be None or set of STOP_ON")
        #end if
        return \
            _SrvAiter(self, stop_on, timeout)
    #end iter_connections_async

#end Server

class _SrvAiter :
    # internal class for use by Server.iter_connections_async (above).

    def __init__(self, srv, stop_on, timeout) :
        self.srv = srv
        self.stop_on = stop_on
        self.timeout = timeout
    #end __init__

    def __aiter__(self) :
        # I’m my own iterator.
        return \
            self
    #end __aiter__

    async def __anext__(self) :
        stop_iter = False
        try :
            result = await self.srv.await_new_connection(self.timeout)
            if result  is None and STOP_ON.TIMEOUT in self.stop_on :
                stop_iter = True
            #end if
        except BrokenPipeError :
            if STOP_ON.CLOSED not in self.stop_on :
                raise
            #end if
            stop_iter = True
        #end try
        if stop_iter :
            raise StopAsyncIteration("Server.iter_connections_async terminating")
        #end if
        return \
            result
    #end __anext__

#end _SrvAiter

class PreallocatedSend :
    "wrapper around a DBusPreallocatedSend object. Do not instantiate directly;" \
    " get from Connection.preallocate_send method."
    # <https://dbus.freedesktop.org/doc/api/html/group__DBusConnection.html>

    __slots__ = ("__weakref__", "_dbobj", "_w_parent", "_sent") # to forestall typos

    _instances = WeakValueDictionary()

    def __new__(celf, _dbobj, _parent) :
        self = celf._instances.get(_dbobj)
        if self  is None :
            self = super().__new__(celf)
            self._dbobj = _dbobj
            self._w_parent = weak_ref(_parent)
            self._sent = False
            celf._instances[_dbobj] = self
        else :
            assert self._w_parent() == _parent
        #end if
        return \
            self
    #end __new__

    def __del__(self) :
        if self._dbobj  is not None :
            parent = self._w_parent()
            if parent  is not None and not self._sent :
                dbus.dbus_connection_free_preallocated_send(parent._dbobj, self._dbobj)
            #end if
            self._dbobj = None
        #end if
    #end __del__

    def send(self, message) :
        "alternative to Connection.send_preallocated."
        if not isinstance(message, Message) :
            raise TypeError("message must be a Message")
        #end if
        assert not self._sent, "preallocated has already been sent"
        parent = self._w_parent()
        assert parent  is not None, "parent Connection has gone away"
        serial = ct.c_uint()
        dbus.dbus_connection_send_preallocated(parent._dbobj, self._dbobj, message._dbobj, ct.byref(serial))
        self._sent = True
        return \
            serial.value
    #end send

#end PreallocatedSend

class Message :
    "wrapper around a DBusMessage object. Do not instantiate directly; use one of the" \
    " new_xxx or copy methods, or Connection.pop_message or Connection.borrow_message."
    # <https://dbus.freedesktop.org/doc/api/html/group__DBusMessage.html>

    __slots__ = ("__weakref__", "_dbobj", "_conn", "_borrowed") # to forestall typos

    _instances = WeakValueDictionary()

    def __new__(celf, _dbobj) :
        self = celf._instances.get(_dbobj)
        if self  is None :
            self = super().__new__(celf)
            self._dbobj = _dbobj
            self._conn = None
            self._borrowed = False
            celf._instances[_dbobj] = self
        else :
            dbus.dbus_message_unref(self._dbobj)
              # lose extra reference created by caller
        #end if
        return \
            self
    #end __new__

    def __del__(self) :
        if self._dbobj  is not None :
            assert not self._borrowed, "trying to dispose of borrowed message"
            dbus.dbus_message_unref(self._dbobj)
            self._dbobj = None
        #end if
    #end __del__

    @classmethod
    def new(celf, type) :
        "type is one of the DBUS.MESSAGE_TYPE_xxx codes. Using one of the type-specific" \
        " calls--new_error, new_method_call, new_method_return, new_signal--is probably" \
        " more convenient."
        result = dbus.dbus_message_new(type)
        if result  is None :
            raise CallFailed("dbus_message_new")
        #end if
        return \
            celf(result)
    #end new

    def new_error(self, name, message) :
        "creates a new DBUS.MESSAGE_TYPE_ERROR message that is a reply to this Message."
        result = dbus.dbus_message_new_error(self._dbobj, name.encode(), (lambda : None, lambda : message.encode())[message  is not None]())
        if result  is None :
            raise CallFailed("dbus_message_new_error")
        #end if
        return \
            type(self)(result)
    #end new_error

    # probably not much point trying to use new_error_printf

    @classmethod
    def new_method_call(celf, destination, path, iface, method) :
        "creates a new DBUS.MESSAGE_TYPE_METHOD_CALL message."
        result = dbus.dbus_message_new_method_call \
          (
            (lambda : None, lambda : destination.encode())[destination  is not None](),
            path.encode(),
            (lambda : None, lambda : iface.encode())[iface  is not None](),
            method.encode(),
          )
        if result  is None :
            raise CallFailed("dbus_message_new_method_call")
        #end if
        return \
            celf(result)
    #end new_method_call

    def new_method_return(self) :
        "creates a new DBUS.MESSAGE_TYPE_METHOD_RETURN that is a reply to this Message."
        result = dbus.dbus_message_new_method_return(self._dbobj)
        if result  is None :
            raise CallFailed("dbus_message_new_method_return")
        #end if
        return \
            type(self)(result)
    #end new_method_return

    @classmethod
    def new_signal(celf, path, iface, name) :
        "creates a new DBUS.MESSAGE_TYPE_SIGNAL message."
        result = dbus.dbus_message_new_signal(path.encode(), iface.encode(), name.encode())
        if result  is None :
            raise CallFailed("dbus_message_new_signal")
        #end if
        return \
            celf(result)
    #end new_signal

    def copy(self) :
        "creates a copy of this Message."
        result = dbus.dbus_message_copy(self._dbobj)
        if result  is None :
            raise CallFailed("dbus_message_copy")
        #end if
        return \
            type(self)(result)
    #end copy

    @property
    def type(self) :
        "returns the DBUS.MESSAGE_TYPE_XXX code for this Message."
        return \
            dbus.dbus_message_get_type(self._dbobj)
    #end type

    # NYI append_args, get_args -- probably not useful, use my
    # objects and append_objects convenience methods (below) instead

    class ExtractIter :
        "for iterating over the arguments in a Message for reading. Do not" \
        " instantiate directly; get from Message.iter_init or ExtractIter.recurse.\n" \
        "\n" \
        "You can use this as a Python iterator, in a for-loop, passing" \
        " it to the next() built-in function etc. Do not mix such usage with calls to" \
        " the has_next() and next() methods."

        __slots__ = ("_dbobj", "_parent", "_nulliter", "_startiter") # to forestall typos

        def __init__(self, _parent) :
            self._dbobj = DBUS.MessageIter()
            self._parent = _parent
            self._nulliter = False
            self._startiter = True
        #end __init__

        @property
        def has_next(self) :
            return \
                dbus.dbus_message_iter_has_next(self._dbobj)
        #end has_next

        def next(self) :
            if self._nulliter or not dbus.dbus_message_iter_next(self._dbobj) :
                raise StopIteration("end of message iterator")
            #end if
            self._startiter = False
            return \
                self
        #end next

        def __iter__(self) :
            return \
                self
        #end __iter__

        def __next__(self) :
            if self._nulliter :
                raise StopIteration("empty message iterator")
            else :
                if self._startiter :
                    self._startiter = False
                else :
                    self.next()
                #end if
            #end if
            return \
                self
        #end __next__

        @property
        def arg_type(self) :
            "the type code for this argument."
            return \
                dbus.dbus_message_iter_get_arg_type(self._dbobj)
        #end arg_type

        @property
        def element_type(self) :
            "the contained element type of this argument, assuming it is of a container type."
            return \
                dbus.dbus_message_iter_get_element_type(self._dbobj)
        #end element_type

        def recurse(self) :
            "creates a sub-iterator for recursing into a container argument."
            subiter = type(self)(self)
            dbus.dbus_message_iter_recurse(self._dbobj, subiter._dbobj)
            return \
                subiter
        #end recurse

        @property
        def signature(self) :
            c_result = dbus.dbus_message_iter_get_signature(self._dbobj)
            if c_result  is None :
                raise CallFailed("dbus_message_iter_get_signature")
            #end if
            result = ct.cast(c_result, ct.c_char_p).value.decode()
            dbus.dbus_free(c_result)
            return \
                result
        #end signature

        @property
        def basic(self) :
            "returns the argument value, assuming it is of a non-container type."
            argtype = self.arg_type
            c_result_type = DBUS.basic_to_ctypes[argtype]
            c_result = c_result_type()
            dbus.dbus_message_iter_get_basic(self._dbobj, ct.byref(c_result))
            if c_result_type == ct.c_char_p :
                result = c_result.value.decode()
            else :
                result = c_result.value
            #end if
            if argtype in DBUS.basic_subclasses :
                result = DBUS.basic_subclasses[argtype](result)
            #end if
            return \
                result
        #end basic

        @property
        def object(self) :
            "returns the current iterator item as a Python object. Will recursively" \
            " process container objects."
            argtype = self.arg_type
            if argtype in DBUS.basic_to_ctypes :
                result = self.basic
            elif argtype == DBUS.TYPE_ARRAY :
                if self.element_type == DBUS.TYPE_DICT_ENTRY :
                    result = {}
                    subiter = self.recurse()
                    while True :
                        entry = next(subiter, None)
                        if entry  is None or entry.arg_type == DBUS.TYPE_INVALID :
                          # TYPE_INVALID can be returned for an empty dict
                            break
                        if entry.arg_type != DBUS.TYPE_DICT_ENTRY :
                            raise RuntimeError("invalid dict entry type %d" % entry.arg_type)
                        #end if
                        key, value = tuple(x.object for x in entry.recurse())
                        result[key] = value
                    #end while
                elif type_is_fixed_array_elttype(self.element_type) :
                    result = self.fixed_array
                else :
                    result = list(x.object for x in self.recurse())
                    if len(result) != 0 and result[-1]  is None :
                        # fudge for iterating into an empty array
                        result = result[:-1]
                    #end if
                #end if
            elif argtype == DBUS.TYPE_STRUCT :
                result = list(x.object for x in self.recurse())
            elif argtype == DBUS.TYPE_VARIANT :
                subiter = self.recurse()
                subiter = next(subiter)
                result = (DBUS.Signature(subiter.signature), subiter.object)
            elif argtype == DBUS.TYPE_INVALID :
                # fudge for iterating into an empty array
                result = None
            else :
                raise RuntimeError("unrecognized argtype %d" % argtype)
            #end if
            return \
                result
        #end object

        if hasattr(dbus, "dbus_message_iter_get_element_count") :
            @property
            def element_count(self) :
                "returns the count of contained elements, assuming the current argument" \
                " is of a container type."
                return \
                    dbus.dbus_message_iter_get_element_count(self._dbobj)
            #end element_count

        #end if

        @property
        def fixed_array(self) :
            "returns the array elements, assuming the current argument is an array" \
            " with a non-container element type."
            c_element_type = DBUS.basic_to_ctypes[self.element_type]
            c_result = ct.POINTER(c_element_type)()
            c_nr_elts = ct.c_int()
            subiter = self.recurse()
            dbus.dbus_message_iter_get_fixed_array(subiter._dbobj, ct.byref(c_result), ct.byref(c_nr_elts))
            result = []
            for i in range(c_nr_elts.value) :
                elt = c_result[i]
                if c_element_type == ct.c_char_p :
                    elt = elt.value.decode()
                #end if
                result.append(elt)
            #end for
            return \
                result
        #end fixed_array

    #end ExtractIter

    class AppendIter :
        "for iterating over the arguments in a Message for appending." \
        " Do not instantiate directly; get from Message.iter_init_append or" \
        " AppendIter.open_container."

        __slots__ = ("_dbobj", "_parent") # to forestall typos

        def __init__(self, _parent) :
            self._dbobj = DBUS.MessageIter()
            self._parent = _parent
        #end __init__

        def append_basic(self, type, value) :
            "appends a single value of a non-container type."
            if type in DBUS.int_convert :
                value = DBUS.int_convert[type](value)
            #end if
            c_type = DBUS.basic_to_ctypes[type]
            if c_type == ct.c_char_p :
                if not isinstance(value, str) :
                    raise TypeError \
                      (
                        "expecting type %s, got %s" % (TYPE(type), builtins.type(value).__name__)
                      )
                #end if
                value = value.encode()
            #end if
            c_value = c_type(value)
            if not dbus.dbus_message_iter_append_basic(self._dbobj, type, ct.byref(c_value)) :
                raise CallFailed("dbus_message_iter_append_basic")
            #end if
            return \
                self
        #end append_basic

        def append_fixed_array(self, element_type, values) :
            "appends an array of elements of a non-container type."
            c_elt_type = DBUS.basic_to_ctypes[element_type]
            nr_elts = len(values)
            c_arr = (nr_elts * c_elt_type)()
            for i in range(nr_elts) :
                if c_elt_type == ct.c_char_p :
                    c_arr[i] = values[i].encode()
                else :
                    c_arr[i] = values[i]
                #end if
            #end for
            c_arr_ptr = ct.pointer(c_arr)
            if not dbus.dbus_message_iter_append_fixed_array(self._dbobj, element_type, ct.byref(c_arr_ptr), nr_elts) :
                raise CallFailed("dbus_message_iter_append_fixed_array")
            #end if
            return \
                self
        #end append_fixed_array

        def open_container(self, type, contained_signature) :
            "starts appending an argument of a container type, returning a sub-iterator" \
            " for appending the contents of the argument. Can be called recursively for" \
            " containers of containers etc."
            if contained_signature  is not None :
                c_sig = contained_signature.encode()
            else :
                c_sig = None
            #end if
            subiter = builtins.type(self)(self)
            if not dbus.dbus_message_iter_open_container(self._dbobj, type, c_sig, subiter._dbobj) :
                raise CallFailed("dbus_message_iter_open_container")
            #end if
            return \
                subiter
        #end open_container

        def close(self) :
            "closes a sub-iterator, indicating the completion of construction" \
            " of a container value."
            assert self._parent  is not None, "cannot close top-level iterator"
            if not dbus.dbus_message_iter_close_container(self._parent._dbobj, self._dbobj) :
                raise CallFailed("dbus_message_iter_close_container")
            #end if
            return \
                self._parent
        #end close

        def abandon(self) :
            "closes a sub-iterator, indicating the abandonment of construction" \
            " of a container value. The Message object is effectively unusable" \
            " after this point and should be discarded."
            assert self._parent  is not None, "cannot abandon top-level iterator"
            dbus.dbus_message_iter_abandon_container(self._parent._dbobj, self._dbobj)
            return \
                self._parent
        #end abandon

    #end AppendIter

    def iter_init(self) :
        "creates an iterator for extracting the arguments of the Message."
        iter = self.ExtractIter(None)
        if dbus.dbus_message_iter_init(self._dbobj, iter._dbobj) == 0 :
            iter._nulliter = True
        #end if
        return \
             iter
    #end iter_init

    @property
    def objects(self) :
        "yields the arguments of the Message as Python objects."
        for iter in self.iter_init() :
            yield iter.object
        #end for
    #end objects

    @property
    def all_objects(self) :
        "all the arguments of the Message as a list of Python objects."
        return \
            list(self.objects)
    #end all_objects

    def expect_objects(self, signature) :
        "expects the arguments of the Message to conform to the given signature," \
        " raising a TypeError if not. If they match, returns them as a list."
        signature = unparse_signature(signature)
        if self.signature != signature :
            raise TypeError("message args don’t match: expected “%s”, got “%s”" % (signature, self.signature))
        #end if
        return \
            self.all_objects
    #end expect_objects

    def expect_return_objects(self, signature) :
        "expects the Message to be of type DBUS.MESSAGE_TYPE_METHOD_RETURN and its" \
        " arguments to conform to the given signature. Raises the appropriate DBusError" \
        " if the Message is of type DBUS.MESSAGE_TYPE_ERROR."
        if self.type == DBUS.MESSAGE_TYPE_METHOD_RETURN :
            result = self.expect_objects(signature)
        elif self.type == DBUS.MESSAGE_TYPE_ERROR :
            raise DBusError(self.error_name, self.expect_objects("s")[0])
        else :
            raise ValueError("unexpected message type %d" % self.type)
        #end if
        return \
            result
    #end expect_return_objects

    def iter_init_append(self) :
        "creates a Message.AppendIter for appending arguments to the Message."
        iter = self.AppendIter(None)
        dbus.dbus_message_iter_init_append(self._dbobj, iter._dbobj)
        return \
            iter
    #end iter_init_append

    def append_objects(self, signature, *args) :
        "interprets Python values args according to signature and appends" \
        " converted item(s) to the message args."

        def append_sub(siglist, eltlist, appenditer) :
            if len(siglist) != len(eltlist) :
                raise ValueError \
                  (
                        "mismatch between signature entries %s and number of sequence elements %s"
                    %
                        (repr(siglist), repr(eltlist))
                  )
            #end if
            for elttype, elt in zip(siglist, eltlist) :
                if isinstance(elttype, BasicType) :
                    appenditer.append_basic(elttype.code.value, elt)
                elif isinstance(elttype, DictType) :
                    if not isinstance(elt, dict) :
                        raise TypeError("dict expected for %s" % repr(elttype))
                    #end if
                    subiter = appenditer.open_container(DBUS.TYPE_ARRAY, elttype.entry_signature)
                    for key in sorted(elt) : # might as well insert in some kind of predictable order
                        value = elt[key]
                        subsubiter = subiter.open_container(DBUS.TYPE_DICT_ENTRY, None)
                        append_sub([elttype.keytype, elttype.valuetype], [key, value], subsubiter)
                        subsubiter.close()
                    #end for
                    subiter.close()
                elif isinstance(elttype, ArrayType) :
                    # append 0 or more elements matching elttype.elttype
                    arrelttype = elttype.elttype
                    if type_is_fixed_array_elttype(arrelttype.code.value) :
                        subiter = appenditer.open_container(DBUS.TYPE_ARRAY, arrelttype.signature)
                        subiter.append_fixed_array(arrelttype.code.value, elt)
                        subiter.close()
                    else :
                        subiter = appenditer.open_container(DBUS.TYPE_ARRAY, arrelttype.signature)
                        if not isinstance(elt, (tuple, list)) :
                            raise TypeError("expecting sequence of values for array")
                        #end if
                        for subval in elt :
                            append_sub([arrelttype], [subval], subiter)
                        #end for
                        subiter.close()
                    #end if
                elif isinstance(elttype, StructType) :
                    if not isinstance(elt, (tuple, list)) :
                        raise TypeError("expecting sequence of values for struct")
                    #end if
                    subiter = appenditer.open_container(DBUS.TYPE_STRUCT, None)
                    append_sub(elttype.elttypes, elt, subiter)
                    subiter.close()
                elif isinstance(elttype, VariantType) :
                    if not isinstance(elt, (list, tuple)) or len(elt) != 2 :
                        raise TypeError("sequence of 2 elements expected for variant: %s" % repr(elt))
                    #end if
                    actual_type = parse_single_signature(elt[0])
                    subiter = appenditer.open_container(DBUS.TYPE_VARIANT, actual_type.signature)
                    append_sub([actual_type], [elt[1]], subiter)
                    subiter.close()
                else :
                    raise RuntimeError("unrecognized type %s" % repr(elttype))
                #end if
            #end for
        #end append_sub

    #begin append_objects
        append_sub(parse_signature(signature), args, self.iter_init_append())
        return \
            self
    #end append_objects

    @property
    def no_reply(self) :
        "whether the Message is not expecting a reply."
        return \
            dbus.dbus_message_get_no_reply(self._dbobj) != 0
    #end no_reply

    @no_reply.setter
    def no_reply(self, no_reply) :
        dbus.dbus_message_set_no_reply(self._dbobj, no_reply)
    #end no_reply

    @property
    def auto_start(self) :
        return \
            dbus.dbus_message_get_auto_start(self._dbobj) != 0
    #end auto_start

    @auto_start.setter
    def auto_start(self, auto_start) :
        dbus.dbus_message_set_auto_start(self._dbobj, auto_start)
    #end auto_start

    @property
    def path(self) :
        "the object path for a DBUS.MESSAGE_TYPE_METHOD_CALL or DBUS.DBUS.MESSAGE_TYPE_SIGNAL" \
        " message."
        result = dbus.dbus_message_get_path(self._dbobj)
        if result  is not None :
            result = DBUS.ObjectPath(result.decode())
        #end if
        return \
            result
    #end path

    @path.setter
    def path(self, object_path) :
        if not dbus.dbus_message_set_path(self._dbobj, (lambda : None, lambda : object_path.encode())[object_path  is not None]()) :
            raise CallFailed("dbus_message_set_path")
        #end if
    #end path

    @property
    def path_decomposed(self) :
        "the object path for a DBUS.MESSAGE_TYPE_METHOD_CALL or DBUS.DBUS.MESSAGE_TYPE_SIGNAL" \
        " message, decomposed into a list of the slash-separated components without the slashes."
        path = ct.POINTER(ct.c_char_p)()
        if not dbus.dbus_message_get_path_decomposed(self._dbobj, ct.byref(path)) :
            raise CallFailed("dbus_message_get_path_decomposed")
        #end if
        if bool(path) :
            result = []
            i = 0
            while True :
                entry = path[i]
                if entry  is None :
                    break
                result.append(entry.decode())
                i += 1
            #end while
            dbus.dbus_free_string_array(path)
        else :
            result = None
        #end if
        return \
            result
    #end path_decomposed

    @property
    def interface(self) :
        "the interface name for a DBUS.MESSAGE_TYPE_METHOD_CALL or DBUS.MESSAGE_TYPE_SIGNAL" \
        " message."
        result = dbus.dbus_message_get_interface(self._dbobj)
        if result  is not None :
            result = result.decode()
        #end if
        return \
            result
    #end interface

    @interface.setter
    def interface(self, iface) :
        if not dbus.dbus_message_set_interface(self._dbobj, (lambda : None, lambda : iface.encode())[iface  is not None]()) :
            raise CallFailed("dbus_message_set_interface")
        #end if
    #end interface

    def has_interface(self, iface) :
        return \
            dbus.dbus_message_has_interface(self._dbobj, iface.encode()) != 0
    #end has_interface

    @property
    def member(self) :
        "the method name for a DBUS.MESSAGE_TYPE_METHOD_CALL message or the signal" \
        " name for DBUS.MESSAGE_TYPE_SIGNAL."
        result = dbus.dbus_message_get_member(self._dbobj)
        if result  is not None :
            result = result.decode()
        #end if
        return \
            result
    #end member

    @member.setter
    def member(self, member) :
        if not dbus.dbus_message_set_member(self._dbobj, (lambda : None, lambda : member.encode())[member  is not None]()) :
            raise CallFailed("dbus_message_set_member")
        #end if
    #end member

    def has_member(self, member) :
        return \
            dbus.dbus_message_has_member(self._dbobj, member.encode()) != 0
    #end has_member

    @property
    def error_name(self) :
        "the error name for a DBUS.MESSAGE_TYPE_ERROR message."
        result = dbus.dbus_message_get_error_name(self._dbobj)
        if result  is not None :
            result = result.decode()
        #end if
        return \
            result
    #end error_name

    @error_name.setter
    def error_name(self, error_name) :
        if not dbus.dbus_message_set_error_name(self._dbobj, (lambda : None, lambda : error_name.encode())[error_name  is not None]()) :
            raise CallFailed("dbus_message_set_error_name")
        #end if
    #end error_name

    @property
    def destination(self) :
        "the bus name that the message is to be sent to."
        result = dbus.dbus_message_get_destination(self._dbobj)
        if result  is not None :
            result = result.decode()
        #end if
        return \
            result
    #end destination

    @destination.setter
    def destination(self, destination) :
        if not dbus.dbus_message_set_destination(self._dbobj, (lambda : None, lambda : destination.encode())[destination  is not None]()) :
            raise CallFailed("dbus_message_set_destination")
        #end if
    #end destination

    @property
    def sender(self) :
        result = dbus.dbus_message_get_sender(self._dbobj)
        if result  is not None :
            result = result.decode()
        #end if
        return \
            result
    #end sender

    @sender.setter
    def sender(self, sender) :
        if not dbus.dbus_message_set_sender(self._dbobj, (lambda : None, lambda : sender.encode())[sender  is not None]()) :
            raise CallFailed("dbus_message_set_sender")
        #end if
    #end sender

    @property
    def signature(self) :
        result = dbus.dbus_message_get_signature(self._dbobj)
        if result  is not None :
            result = DBUS.Signature(result.decode())
        #end if
        return \
            result
    #end signature

    def is_method_call(self, iface, method) :
        return \
            dbus.dbus_message_is_method_call(self._dbobj, iface.encode(), method.encode()) != 0
    #end is_method_call

    def is_signal(self, iface, signal_name) :
        return \
            dbus.dbus_message_is_signal(self._dbobj, iface.encode(), signal_name.encode()) != 0
    #end is_signal

    def is_error(self, iface, error_name) :
        return \
            dbus.dbus_message_is_error(self._dbobj, error_name.encode()) != 0
    #end is_error

    def has_destination(self, iface, destination) :
        return \
            dbus.dbus_message_has_destination(self._dbobj, destination.encode()) != 0
    #end has_destination

    def has_sender(self, iface, sender) :
        return \
            dbus.dbus_message_has_sender(self._dbobj, sender.encode()) != 0
    #end has_sender

    def has_signature(self, iface, signature) :
        return \
            dbus.dbus_message_has_signature(self._dbobj, signature.encode()) != 0
    #end has_signature

    def set_error(self, error) :
        "fills in error if this is an error message, else does nothing. Returns" \
        " whether it was an error message or not."
        if not isinstance(error, Error) :
            raise TypeError("error must be an Error")
        #end if
        return \
            dbus.dbus_set_error_from_message(error._dbobj, self._dbobj) != 0
    #end set_error

    @property
    def contains_unix_fds(self) :
        return \
            dbus.dbus_message_contains_unix_fds(self._dbobj) != 0
    #end contains_unix_fds

    @property
    def serial(self) :
        "the serial number of the Message, to be referenced in replies."
        return \
            dbus.dbus_message_get_serial(self._dbobj)
    #end serial

    @serial.setter
    def serial(self, serial) :
        dbus.dbus_message_set_serial(self._dbobj, serial)
    #end serial

    @property
    def reply_serial(self) :
        "the serial number of the original Message that that this" \
        " DBUS.MESSAGE_TYPE_METHOD_RETURN message is a reply to."
        return \
            dbus.dbus_message_get_reply_serial(self._dbobj)
    #end reply_serial

    @reply_serial.setter
    def reply_serial(self, serial) :
        if not dbus.dbus_message_set_reply_serial(self._dbobj, serial) :
            raise CallFailed("dbus_message_set_reply_serial")
        #end if
    #end serial

    def lock(self) :
        dbus.dbus_message_lock(self._dbobj)
    #end lock

    def return_borrowed(self) :
        assert self._borrowed and self._conn  is not None
        dbus.dbus_connection_return_message(self._conn._dbobj, self._dbobj)
        self._borrowed = False
    #end return_borrowed

    def steal_borrowed(self) :
        assert self._borrowed and self._conn  is not None
        dbus.dbus_connection_steal_borrowed_message(self._conn._dbobj, self._dbobj)
        self._borrowed = False
        return \
            self
    #end steal_borrowed

    # TODO: allocate/free data slot -- static methods
    #    (freeing slot can set passed-in var to -1 on actual free; do I care?)
    # TODO: set/get data

    @staticmethod
    def type_from_string(type_str) :
        "returns a MESSAGE_TYPE_xxx value."
        return \
            dbus.dbus_message_type_from_string(type_str.encode())
    #end type_from_string

    @staticmethod
    def type_to_string(type) :
        "type is a MESSAGE_TYPE_xxx value."
        return \
            dbus.dbus_message_type_to_string(type).decode()
    #end type_to_string

    def marshal(self) :
        "serializes this Message into the wire protocol format and returns a bytes object."
        buf = ct.POINTER(ct.c_ubyte)()
        nr_bytes = ct.c_int()
        if not dbus.dbus_message_marshal(self._dbobj, ct.byref(buf), ct.byref(nr_bytes)) :
            raise CallFailed("dbus_message_marshal")
        #end if
        result = bytearray(nr_bytes.value)
        ct.memmove \
          (
            ct.addressof((ct.c_ubyte * nr_bytes.value).from_buffer(result)),
            buf,
            nr_bytes.value
          )
        dbus.dbus_free(buf)
        return \
            result
    #end marshal

    @classmethod
    def demarshal(celf, buf, error = None) :
        "deserializes a bytes or array-of-bytes object from the wire protocol" \
        " format into a Message object."
        error, my_error = _get_error(error)
        if isinstance(buf, bytes) :
            baseadr = ct.cast(buf, ct.c_void_p).value
        elif isinstance(buf, bytearray) :
            baseadr = ct.addressof((ct.c_ubyte * len(buf)).from_buffer(buf))
        elif isinstance(buf, array.array) and buf.typecode == "B" :
            baseadr = buf.buffer_info()[0]
        else :
            raise TypeError("buf is not bytes, bytearray or array.array of bytes")
        #end if
        msg = dbus.dbus_message_demarshal(baseadr, len(buf), error._dbobj)
        my_error.raise_if_set()
        if msg  is not None :
            msg = celf(msg)
        #end if
        return \
            msg
    #end demarshal

    @classmethod
    def demarshal_bytes_needed(celf, buf) :
        "the number of bytes needed to deserialize a bytes or array-of-bytes" \
        " object from the wire protocol format."
        if isinstance(buf, bytes) :
            baseadr = ct.cast(buf, ct.c_void_p).value
        elif isinstance(buf, bytearray) :
            baseadr = ct.addressof((ct.c_ubyte * len(buf)).from_buffer(buf))
        elif isinstance(buf, array.array) and buf.typecode == "B" :
            baseadr = buf.buffer_info()[0]
        else :
            raise TypeError("buf is not bytes, bytearray or array.array of bytes")
        #end if
        return \
            dbus.dbus_message_demarshal_bytes_needed(baseadr, len(buf))
    #end demarshal_bytes_needed

    @property
    def interactive_authorization(self) :
        return \
            dbus.dbus_message_get_interactive_authorization(self._dbobj)
    #end interactive_authorization

    @interactive_authorization.setter
    def interactive_authorization(self, allow) :
        dbus.dbus_message_set_interactive_authorization(self._dbobj, allow)
    #end interactive_authorization

#end Message

class PendingCall :
    "wrapper around a DBusPendingCall object. This represents a pending reply" \
    " message that hasn’t been received yet. Do not instantiate directly; libdbus" \
    " creates these as the result from calling send_with_reply() on a Message."
    # <https://dbus.freedesktop.org/doc/api/html/group__DBusPendingCall.html>

    __slots__ = \
      (
        "__weakref__",
        "_dbobj",
        "_w_conn",
        "_wrap_notify",
        "_wrap_free",
        "_awaiting",
      ) # to forestall typos

    _instances = WeakValueDictionary()

    def __new__(celf, _dbobj, _conn) :
        self = celf._instances.get(_dbobj)
        if self  is None :
            self = super().__new__(celf)
            self._dbobj = _dbobj
            self._w_conn = weak_ref(_conn)
            self._wrap_notify = None
            self._wrap_free = None
            self._awaiting = None
            celf._instances[_dbobj] = self
        else :
            dbus.dbus_pending_call_unref(self._dbobj)
              # lose extra reference created by caller
        #end if
        return \
            self
    #end __new__

    def __del__(self) :
        if self._dbobj  is not None :
            dbus.dbus_pending_call_unref(self._dbobj)
            self._dbobj = None
        #end if
    #end __del__

    def set_notify(self, function, user_data, free_user_data = None) :
        "sets the callback for libdbus to notify you that the pending message" \
        " has become available. Note: it appears to be possible for your notifier" \
        " to be called spuriously before the message is actually available."

        w_self = weak_ref(self)

        def wrap_notify(c_pending, c_user_data) :
            function(_wderef(w_self, "pending call"), user_data)
        #end _wrap_notify

        def wrap_free(c_user_data) :
            free_user_data(user_data)
        #end _wrap_free

    #begin set_notify
        if function  is not None :
            self._wrap_notify = DBUS.PendingCallNotifyFunction(wrap_notify)
        else :
            self._wrap_notify = None
        #end if
        if free_user_data  is not None :
            self._wrap_free = DBUS.FreeFunction(wrap_free)
        else :
            self._wrap_free = None
        #end if
        if not dbus.dbus_pending_call_set_notify(self._dbobj, self._wrap_notify, None, self._wrap_free) :
            raise CallFailed("dbus_pending_call_set_notify")
        #end if
    #end set_notify

    def cancel(self) :
        "tells libdbus you no longer care about the pending incoming message."
        dbus.dbus_pending_call_cancel(self._dbobj)
        if self._awaiting  is not None :
            # This probably shouldn’t occur. Looking at the source of libdbus,
            # it doesn’t keep track of any “cancelled” state for the PendingCall,
            # it just detaches it from any notifications about an incoming reply.
            self._awaiting.cancel()
        #end if
    #end cancel

    @property
    def completed(self) :
        "checks whether the pending message is available."
        return \
            dbus.dbus_pending_call_get_completed(self._dbobj) != 0
    #end completed

    def steal_reply(self) :
        "retrieves the Message, assuming it is actually available." \
        " You should check PendingCall.completed returns True first."
        result = dbus.dbus_pending_call_steal_reply(self._dbobj)
        if result  is not None :
            result = Message(result)
        #end if
        return \
            result
    #end steal_reply

    async def await_reply(self) :
        "retrieves the Message. If it is not yet available, suspends the" \
        " coroutine (letting the event loop do other things) until it becomes" \
        " available. On a timeout, libdbus will construct and return an error" \
        " return message."
        conn = self._w_conn()
        assert conn  is not None, "parent Connection has gone away"
        assert conn.loop  is not None, "no event loop on parent Connection to attach coroutine to"
        if self._wrap_notify  is not None or self._awaiting  is not None :
            raise asyncio.InvalidStateError("there is already a notify set on this PendingCall")
        #end if
        done = conn.loop.create_future()
        self._awaiting = done

        def pending_done(pending, wself) :
            if not done.done() : # just in case of self.cancel() being called
                self = wself()
                # Note it seems to be possible for callback to be triggered spuriously
                if self  is not None and self.completed :
                    done.set_result(self.steal_reply())
                #end if
            #end if
        #end pending_done

        self.set_notify(pending_done, weak_ref(self))
          # avoid reference circularity self → pending_done → self
        reply = await done
        return \
            reply
    #end await_reply

    def block(self) :
        "blocks the current thread until the pending message has become available."
        dbus.dbus_pending_call_block(self._dbobj)
    #end block

    # TODO: data slots (static methods), get/set data

#end PendingCall

class Error :
    "wrapper around a DBusError object. You can create one by calling the init method."
    # <https://dbus.freedesktop.org/doc/api/html/group__DBusErrors.html>

    __slots__ = ("_dbobj",) # to forestall typos

    def __init__(self) :
        dbobj = DBUS.Error()
        dbus.dbus_error_init(dbobj)
        self._dbobj = dbobj
    #end __init__

    def __del__(self) :
        if self._dbobj  is not None :
            dbus.dbus_error_free(self._dbobj)
            self._dbobj = None
        #end if
    #end __del__

    @classmethod
    def init(celf) :
        "for consistency with other classes that don’t want caller to instantiate directly."
        return \
            celf()
    #end init

    def set(self, name, msg) :
        "fills in the error name and message."
        dbus.dbus_set_error(self._dbobj, name.encode(), b"%s", msg.encode())
    #end set

    @property
    def is_set(self) :
        "has the Error been filled in."
        return \
            dbus.dbus_error_is_set(self._dbobj) != 0
    #end is_set

    def has_name(self, name) :
        "has the Error got the specified name."
        return \
            dbus.dbus_error_has_name(self._dbobj, name.encode()) != 0
    #end has_name

    @property
    def name(self) :
        "the name of the Error, if it has been filled in."
        return \
            (lambda : None, lambda : self._dbobj.name.decode())[self._dbobj.name  is not None]()
    #end name

    @property
    def message(self) :
        "the message string for the Error, if it has been filled in."
        return \
            (lambda : None, lambda : self._dbobj.message.decode())[self._dbobj.message  is not None]()
    #end message

    def raise_if_set(self) :
        "raises a DBusError exception if this Error has been filled in."
        if self.is_set :
            raise DBusError(self.name, self.message)
        #end if
    #end raise_if_set

    def set_from_message(self, message) :
        "fills in this Error object from message if it is an error message." \
        " Returns whether it was or not."
        if not isinstance(message, Message) :
            raise TypeError("message must be a Message")
        #end if
        return \
            dbus.dbus_set_error_from_message(self._dbobj, message._dbobj) != 0
    #end set_from_message

#end Error

class AddressEntries :
    "wrapper for arrays of DBusAddressEntry values. Do not instantiate directly;" \
    " get from AddressEntries.parse. This object behaves like an array; you can obtain" \
    " the number of elements with len(), and use array subscripting to access the elements."
    # <https://dbus.freedesktop.org/doc/api/html/group__DBusAddress.html>

    __slots__ = ("__weakref__", "_dbobj", "_nrelts") # to forestall typos

    def __init__(self, _dbobj, _nrelts) :
        self._dbobj = _dbobj
        self._nrelts = _nrelts
    #end __init__

    def __del__(self) :
        if self._dbobj  is not None :
            dbus.dbus_address_entries_free(self._dbobj)
            self._dbobj = None
        #end if
    #end __del__

    class Entry :
        "a single AddressEntry. Do not instantiate directly; get from AddressEntries[]." \
        " This object behaves like a dictionary in that you can use keys to get values;" \
        " however, there is no libdbus API to check what keys are present; unrecognized" \
        " keys return a value of None."

        __slots__ = ("_dbobj", "_parent", "_index") # to forestall typos

        def __init__(self, _parent, _index) :
            self._dbobj = _parent._dbobj
            self._parent = weak_ref(_parent)
            self._index = _index
        #end __init__

        @property
        def method(self) :
            assert self._parent()  is not None, "AddressEntries object has gone"
            result = dbus.dbus_address_entry_get_method(self._dbobj[self._index])
            if result  is not None :
                result = result.decode()
            #end if
            return \
                result
        #end method

        def get_value(self, key) :
            assert self._parent()  is not None, "AddressEntries object has gone"
            c_result = dbus.dbus_address_entry_get_value(self._dbobj[self._index], key.encode())
            if c_result  is not None :
                result = c_result.decode()
            else :
                result = None
            #end if
            return \
                result
        #end get_value
        __getitem__ = get_value

    #end Entry

    @classmethod
    def parse(celf, address, error = None) :
        error, my_error = _get_error(error)
        c_result = ct.POINTER(ct.c_void_p)()
        nr_elts = ct.c_int()
        if not dbus.dbus_parse_address(address.encode(), ct.byref(c_result), ct.byref(nr_elts), error._dbobj) :
            c_result.contents = None
            nr_elts.value = 0
        #end if
        my_error.raise_if_set()
        if c_result.contents  is not None :
            result = celf(c_result, nr_elts.value)
        else :
            result = None
        #end if
        return \
            result
    #end parse

    def __len__(self) :
        return \
            self._nrelts
    #end __len__

    def __getitem__(self, index) :
        if not isinstance(index, int) or index < 0 or index >= self._nrelts :
            raise IndexError("AddressEntries[%d] out of range" % index)
        #end if
        return \
            type(self).Entry(self, index)
    #end __getitem__

#end AddressEntries

def address_escape_value(value) :
    c_result = dbus.dbus_address_escape_value(value.encode())
    if c_result  is None :
        raise CallFailed("dbus_address_escape_value")
    #end if
    result = ct.cast(c_result, ct.c_char_p).value.decode()
    dbus.dbus_free(c_result)
    return \
        result
#end address_escape_value

def address_unescape_value(value, error = None) :
    error, my_error = _get_error(error)
    c_result = dbus.dbus_address_unescape_value(value.encode(), error._dbobj)
    my_error.raise_if_set()
    if c_result  is not None :
        result = ct.cast(c_result, ct.c_char_p).value.decode()
        dbus.dbus_free(c_result)
    elif not error.is_set :
        raise CallFailed("dbus_address_unescape_value")
    else :
        result = None
    #end if
    return \
        result
#end address_unescape_value

def format_rule(rule) :
    "convenience routine to allow a match rule to be expressed as either" \
    " a dict of {key : value} or the usual string \"key='value'\", automatically" \
    " converting the former to the latter."

    def escape_val(val) :
        if "," in val :
            if "'" in val :
                out = "'"
                in_quotes = True
                for ch in val :
                    if ch == "'" :
                        if in_quotes :
                            out += "'"
                            in_quotes = False
                        #end if
                        out += "\\'"
                    else :
                        if not in_quotes :
                            out += "'"
                            in_quotes = True
                        #end if
                        out += ch
                    #end if
                #end for
                if in_quotes :
                    out += "'"
                #end if
            else :
                out = "'" + val + "'"
            #end if
        else :
            out = ""
            for ch in val :
                if ch in ("\\", "'") :
                    out += "\\"
                #end if
                out += ch
            #end for
        #end if
        return \
            out
    #end escape_val

#begin format_rule
    if isinstance(rule, str) :
        pass
    elif isinstance(rule, dict) :
        rule = ",".join("%s=%s" % (k, escape_val(rule[k])) for k in sorted(rule))
          # sort to ensure some kind of consistent ordering, just for
          # appearance’s sake
    else :
        raise TypeError("rule “%s” must be a dict or string" % repr(rule))
    #end if
    return \
        rule
#end format_rule

class _RuleParser :
    # internal definitions for rule parsing.

    class PARSE(enum.Enum) :
        EXPECT_NAME = 1
        EXPECT_UNQUOTED_VALUE = 2
        EXPECT_ESCAPED = 3
        EXPECT_QUOTED_VALUE = 4
    #end PARSE

    @classmethod
    def unformat_rule(celf, rule) :
        "converts a match rule string from the standard syntax to a dict of {key : value} entries."
        if isinstance(rule, dict) :
            pass
        elif isinstance(rule, str) :
            PARSE = celf.PARSE
            parsed = {}
            chars = iter(rule)
            state = PARSE.EXPECT_NAME
            curname = None
            curval = None
            while True :
                ch = next(chars, None)
                if ch  is None :
                    if state == PARSE.EXPECT_ESCAPED :
                        raise SyntaxError("missing character after backslash")
                    elif state == PARSE.EXPECT_QUOTED_VALUE :
                        raise SyntaxError("missing closing apostrophe")
                    else : # state in (PARSE.EXPECT_NAME, PARSE.EXPECT_UNQUOTED_VALUE)
                        if curname  is not None :
                            if curval  is not None :
                                if curname in parsed :
                                    raise SyntaxError("duplicated attribute “%s”" % curname)
                                #end if
                                parsed[curname] = curval
                            else :
                                raise SyntaxError("missing value for attribute “%s”" % curname)
                            #end if
                        #end if
                    #end if
                    break
                #end if
                if state == PARSE.EXPECT_ESCAPED :
                    if ch == "'" :
                        usech = ch
                        nextch = None
                    else :
                        usech = "\\"
                        nextch = ch
                    #end if
                    ch = usech
                    if curval  is None :
                        curval = ch
                    else :
                        curval += ch
                    #end if
                    ch = nextch # None indicates already processed
                    state = PARSE.EXPECT_UNQUOTED_VALUE
                #end if
                if ch  is not None :
                    if ch == "," and state != PARSE.EXPECT_QUOTED_VALUE :
                        if state == PARSE.EXPECT_UNQUOTED_VALUE :
                            if curname in parsed :
                                raise SyntaxError("duplicated attribute “%s”" % curname)
                            #end if
                            if curval  is None :
                                curval = ""
                            #end if
                            parsed[curname] = curval
                            curname = None
                            curval = None
                            state = PARSE.EXPECT_NAME
                        else :
                            raise SyntaxError("unexpected comma")
                        #end if
                    elif ch == "\\" and state != PARSE.EXPECT_QUOTED_VALUE :
                        if state == PARSE.EXPECT_UNQUOTED_VALUE :
                            state = PARSE.EXPECT_ESCAPED
                        else :
                            raise SyntaxError("unexpected backslash")
                        #end if
                    elif ch == "=" and state != PARSE.EXPECT_QUOTED_VALUE :
                        if curname  is None :
                            raise SyntaxError("empty attribute name")
                        #end if
                        if state == PARSE.EXPECT_NAME :
                            state = PARSE.EXPECT_UNQUOTED_VALUE
                        else :
                            raise SyntaxError("unexpected equals sign")
                        #end if
                    elif ch == "'" :
                        if state == PARSE.EXPECT_UNQUOTED_VALUE :
                            state = PARSE.EXPECT_QUOTED_VALUE
                        elif state == PARSE.EXPECT_QUOTED_VALUE :
                            state = PARSE.EXPECT_UNQUOTED_VALUE
                        else :
                            raise SyntaxError("unexpected apostrophe")
                        #end if
                    else :
                        if state == PARSE.EXPECT_NAME :
                            if curname  is None :
                                curname = ch
                            else :
                                curname += ch
                            #end if
                        elif state in (PARSE.EXPECT_QUOTED_VALUE, PARSE.EXPECT_UNQUOTED_VALUE) :
                            if curval  is None :
                                curval = ch
                            else :
                                curval += ch
                            #end if
                        else :
                            raise AssertionError("shouldn’t occur: parse state %s" % repr(state))
                        #end if
                    #end if
                #end if
            #end while
            rule = parsed
        else :
            raise TypeError("rule “%s” must be a dict or string" % repr(rule))
        #end if
        return \
            rule
    #end unformat_rule

#end _RuleParser

unformat_rule = _RuleParser.unformat_rule
del _RuleParser

def matches_rule(message, rule, destinations = None) :
    "does Message message match against the specified rule."
    if not isinstance(message, Message) :
        raise TypeError("message must be a Message")
    #end if
    rule = unformat_rule(rule)
    eavesdrop = rule.get("eavesdrop", "false") == "true"

    def match_message_type(expect, actual) :
        return \
            actual == Message.type_from_string(expect)
    #end match_message_type

    def match_path_namespace(expect, actual) :
        return \
            (
                actual  is not None
            and
                (
                    expect == actual
                or
                    actual.startswith(expect) and (expect == "/" or actual[len(expect)] == "/")
                )
            )
    #end match_path_namespace

    def match_dotted_namespace(expect, actual) :
        return \
            (
                actual  is not None
            and
                (
                    expect == actual
                or
                    actual.startswith(expect) and actual[len(expect)] == "."
                )
            )
    #end match_dotted_namespace

    def get_nth_arg(msg, n, expect_types) :
        msg_signature = parse_signature(msg.signature)
        if n >= len(msg_signature) :
            raise IndexError("arg nr %d beyond nr args %d" % (n, len(msg_signature)))
        #end if
        val = msg.all_objects[n]
        valtype = msg_signature[n]
        if valtype not in expect_types :
            if False :
                raise TypeError \
                  (
                        "expecting one of types %s, not %s for arg %d val %s"
                    %
                        ((repr(expect_types), repr(valtype), n, repr(val)))
                  )
            #end if
            val = None # never match
        #end if
        return \
            val
    #end get_nth_arg

    def get_arg_0_str(message) :
        return \
            get_nth_arg(message, 0, [BasicType(TYPE.STRING)])
    #end get_arg_0_str

    def match_arg_paths(expect, actual) :
        return \
            (
                actual  is not None
            and
                (
                    expect == actual
                or
                    expect.endswith("/") and actual.startswith(expect)
                or
                    actual.endswith("/") and expect.startswith(actual)
                )
            )
    #end match_arg_paths

    match_types = \
        ( # note that message attribute value of None will fail to match
          # any expected string value, which is exactly what we want
            ("type", None, match_message_type, None),
            ("sender", None, operator.eq, None),
            ("interface", None, operator.eq, None),
            ("member", None, operator.eq, None),
            ("path", None, operator.eq, None),
            ("destination", None, operator.eq, None),
            ("path_namespace", "path", match_path_namespace, None),
            ("arg0namespace", None, match_dotted_namespace, get_arg_0_str),
            # “arg«n»path” handled specially below
        )

#begin matches_rule
    keys_used = set(rule.keys()) - {"eavesdrop"}
    matches = \
        (
            eavesdrop
        or
            destinations  is None
        or
            message.destination  is None
        or
            message.destination in destinations
        )
    if matches :
        try_matching = iter(match_types)
        while True :
            try_rule = next(try_matching, None)
            if try_rule  is None :
                break
            rulekey, attrname, action, accessor = try_rule
            if attrname  is None :
                attrname = rulekey
            #end if
            if rulekey in rule :
                if accessor  is not None :
                    val = accessor(message)
                else :
                    val = getattr(message, attrname)
                #end if
                keys_used.remove(rulekey)
                if not action(rule[rulekey], val) :
                    matches = False
                    break
                #end if
            #end if
        #end while
    #end if
    if matches :
        try_matching = iter(rule.keys())
        while True :
            try_key = next(try_matching, None)
            if try_key  is None :
                break
            if try_key.startswith("arg") and not try_key.endswith("namespace") :
                argnr = try_key[3:]
                is_path = argnr.endswith("path")
                if is_path :
                    argnr = argnr[:-4]
                #end if
                argnr = int(argnr)
                if not (0 <= argnr < 64) :
                    raise ValueError("argnr %d out of range" % argnr)
                #end if
                argval = get_nth_arg \
                  (
                    message,
                    argnr,
                    [BasicType(TYPE.STRING)] + ([], [BasicType(TYPE.OBJECT_PATH)])[is_path]
                  )
                keys_used.remove(try_key)
                if not (operator.eq, match_arg_paths)[is_path](rule[try_key], argval) :
                    matches = False
                    break
                #end if
            #end if
        #end while
    #end if
    if matches and len(keys_used) != 0 :
        # fixme: not checking for unrecognized rule keys if I didn’t try matching them all
        raise KeyError("unrecognized rule keywords: %s" % ", ".join(sorted(keys_used)))
    #end if
    return \
        matches
#end matches_rule

class SignatureIter :
    "wraps a DBusSignatureIter object. Do not instantiate directly; use the init" \
    " and recurse methods."
    # <https://dbus.freedesktop.org/doc/api/html/group__DBusSignature.html>

    __slots__ = ("_dbobj", "_signature", "_startiter") # to forestall typos

    @classmethod
    def init(celf, signature) :
        self = celf()
        self._signature = ct.c_char_p(signature.encode()) # need to ensure storage stays valid
        dbus.dbus_signature_iter_init(self._dbobj, self._signature)
        return \
            self
    #end init

    def __init__(self) :
        self._dbobj = DBUS.SignatureIter()
        self._signature = None # caller will set as necessary
        self._startiter = True
    #end __init__

    def __iter__(self) :
        return \
            self
    #end __iter__

    def __next__(self) :
        if self._startiter :
            self._startiter = False
        else :
            self.next()
        #end if
        return \
            self
    #end __next__

    def next(self) :
        if dbus.dbus_signature_iter_next(self._dbobj) == 0 :
            raise StopIteration("end of signature iterator")
        #end if
        self._startiter = False
        return \
            self
    #end next

    def recurse(self) :
        subiter = type(self)()
        dbus.dbus_signature_iter_recurse(self._dbobj, subiter._dbobj)
        return \
            subiter
    #end recurse

    @property
    def current_type(self) :
        return \
            dbus.dbus_signature_iter_get_current_type(self._dbobj)
    #end current_type

    @property
    def signature(self) :
        c_result = dbus.dbus_signature_iter_get_signature(self._dbobj)
        result = ct.cast(c_result, ct.c_char_p).value.decode()
        dbus.dbus_free(c_result)
        return \
            result
    #end signature

    @property
    def parsed_signature(self) :
        return \
            parse_single_signature(self.signature)
    #end parsed_signature

    @property
    def element_type(self) :
        return \
            dbus.dbus_signature_iter_get_element_type(self._dbobj)
    #end element_type

#end SignatureIter

def signature_validate(signature, error = None) :
    "is signature a valid sequence of zero or more complete types."
    error, my_error = _get_error(error)
    result = dbus.dbus_signature_validate(signature.encode(), error._dbobj) != 0
    my_error.raise_if_set()
    return \
        result
#end signature_validate

def parse_signature(signature) :
    "convenience routine for parsing a signature string into a list of Type()" \
    " instances."

    def process_subsig(sigelt) :
        elttype = sigelt.current_type
        if elttype in DBUS.basic_to_ctypes :
            result = BasicType(TYPE(elttype))
        elif elttype == DBUS.TYPE_ARRAY :
            if sigelt.element_type == DBUS.TYPE_DICT_ENTRY :
                subsig = sigelt.recurse()
                subsubsig = subsig.recurse()
                keytype = process_subsig(next(subsubsig))
                valuetype = process_subsig(next(subsubsig))
                result = DictType(keytype, valuetype)
            else :
                subsig = sigelt.recurse()
                result = ArrayType(process_subsig(next(subsig)))
            #end if
        elif elttype == DBUS.TYPE_STRUCT :
            result = []
            subsig = sigelt.recurse()
            for subelt in subsig :
                result.append(process_subsig(subelt))
            #end for
            result = StructType(*result)
        elif elttype == DBUS.TYPE_VARIANT :
            result = VariantType()
        else :
            raise RuntimeError("unrecognized type %s" % bytes((elttype,)))
        #end if
        return \
            result
    #end process_subsig

#begin parse_signature
    if isinstance(signature, (tuple, list)) :
        if not all(isinstance(t, Type) for t in signature) :
            raise TypeError("signature is list containing non-Type objects")
        #end if
        result = signature
    elif isinstance(signature, Type) :
        result = [signature]
    elif isinstance(signature, str) :
        signature_validate(signature)
        result = []
        if len(signature) != 0 :
            sigiter = SignatureIter.init(signature)
            for elt in sigiter :
                result.append(process_subsig(elt))
            #end for
        #end if
    else :
        raise TypeError("signature must be list or str")
    #end if
    return \
        result
#end parse_signature

def parse_single_signature(signature) :
    result = parse_signature(signature)
    if len(result) != 1 :
        raise ValueError("only single type expected")
    #end if
    return \
        result[0]
#end parse_single_signature

def unparse_signature(signature) :
    "converts a signature from parsed form to string form."
    signature = parse_signature(signature)
    if not isinstance(signature, (tuple, list)) :
        signature = [signature]
    #end if
    return \
        DBUS.Signature("".join(t.signature for t in signature))
#end unparse_signature

def signature_validate_single(signature, error = None) :
    "is signature a single valid type."
    error, my_error = _get_error(error)
    result = dbus.dbus_signature_validate_single(signature.encode(), error._dbobj) != 0
    my_error.raise_if_set()
    return \
        result
#end signature_validate_single

def type_is_valid(typecode) :
    return \
        dbus.dbus_type_is_valid(typecode) != 0
#end type_is_valid

def type_is_basic(typecode) :
    return \
        dbus.dbus_type_is_basic(typecode) != 0
#end type_is_basic

def type_is_container(typecode) :
    return \
        dbus.dbus_type_is_container(typecode) != 0
#end type_is_container

def type_is_fixed(typecode) :
    return \
        dbus.dbus_type_is_fixed(typecode) != 0
#end type_is_fixed

def type_is_fixed_array_elttype(typecode) :
    "is typecode suitable as the element type of a fixed_array."
    return \
        type_is_fixed(typecode) and typecode != DBUS.TYPE_UNIX_FD
#end type_is_fixed_array_elttype

# syntax validation <https://dbus.freedesktop.org/doc/api/html/group__DBusSyntax.html>

def validate_path(path, error = None) :
    error, my_error = _get_error(error)
    result = dbus.dbus_validate_path(path.encode(), error._dbobj) != 0
    my_error.raise_if_set()
    return \
        result
#end validate_path

def valid_path(path) :
    "returns path if valid, raising appropriate exception if not."
    validate_path(path)
    return \
        path
#end valid_path

def split_path(path) :
    "convenience routine for splitting a path into a list of components."
    if isinstance(path, (tuple, list)) :
        result = path # assume already split
    elif path == "/" :
        result = []
    else :
        if not path.startswith("/") or path.endswith("/") :
            raise DBusError(DBUS.ERROR_INVALID_ARGS, "invalid path %s" % repr(path))
        #end if
        result = path.split("/")[1:]
    #end if
    return \
        result
#end split_path

def unsplit_path(path) :
    path = split_path(path)
    if len(path) != 0 :
        result = DBUS.ObjectPath("".join("/" + component for component in path))
    else :
        result = "/"
    #end if
    return \
        result
#end unsplit_path

def validate_interface(name, error = None) :
    error, my_error = _get_error(error)
    result = dbus.dbus_validate_interface(name.encode(), error._dbobj) != 0
    my_error.raise_if_set()
    return \
        result
#end validate_interface

def valid_interface(name) :
    "returns name if it is a valid interface name, raising appropriate exception if not."
    validate_interface(name)
    return \
        name
#end valid_interface

def validate_member(name, error = None) :
    error, my_error = _get_error(error)
    result = dbus.dbus_validate_member(name.encode(), error._dbobj) != 0
    my_error.raise_if_set()
    return \
        result
#end validate_member

def valid_member(name) :
    "returns name if it is a valid member name, raising appropriate exception if not."
    validate_member(name)
    return \
        name
#end valid_member

def validate_error_name(name, error = None) :
    error, my_error = _get_error(error)
    result = dbus.dbus_validate_error_name(name.encode(), error._dbobj) != 0
    my_error.raise_if_set()
    return \
        result
#end validate_error_name

def valid_error_name(name) :
    "returns name if it is a valid error name, raising appropriate exception if not."
    validate_error_name(name)
    return \
        name
#end valid_error_name

def validate_bus_name(name, error = None) :
    error, my_error = _get_error(error)
    result = dbus.dbus_validate_bus_name(name.encode(), error._dbobj) != 0
    my_error.raise_if_set()
    return \
        result
#end validate_bus_name

def valid_bus_name(name) :
    "returns name if it is a valid bus name, raising appropriate exception if not."
    validate_bus_name(name)
    return \
        name
#end valid_bus_name

def validate_utf8(alleged_utf8, error = None) :
    "alleged_utf8 must be null-terminated bytes."
    error, my_error = _get_error(error)
    result = dbus.dbus_validate_utf8(alleged_utf8, error._dbobj) != 0
    my_error.raise_if_set()
    return \
        result
#end validate_utf8

def valid_utf8(alleged_utf8) :
    "returns alleged_utf8 if it is a valid utf-8 bytes value, raising" \
    " appropriate exception if not."
    validate_utf8(alleged_utf8)
    return \
        alleged_utf8
#end valid_utf8

#+
# Introspection representation
#-

class _TagCommon :
    def get_annotation(self, name) :
        "returns the value of the annotation with the specified name, or None" \
        " if none could be found"
        annots = iter(self.annotations)
        while True :
            annot = next(annots, None)
            if annot  is None :
                result = None
                break
            #end if
            if annot.name == name :
                result = annot.value
                break
            #end if
        #end while
        return \
            result
    #end get_annotation

    @property
    def is_deprecated(self) :
        "is this interface/method/signal etc deprecated."
        return \
            self.get_annotation("org.freedesktop.DBus.Deprecated") == "true"
    #end is_deprecated

    def __repr__(self) :
        celf = type(self)
        return \
            (
                    "%s(%s)"
                %
                    (
                        celf.__name__,
                        ", ".join
                          (
                                "%s = %s"
                            %
                                (name, repr(getattr(self, name)))
                            for name in celf.__slots__
                          ),
                    )
            )
    #end __repr__

#end _TagCommon

class Introspection(_TagCommon) :
    "high-level wrapper for the DBUS.INTERFACE_INTROSPECTABLE interface."

    __slots__ = ("name", "interfaces", "nodes", "annotations")

    tag_name = "node"
    tag_attrs = ("name",)
    tag_attrs_optional = {"name"}

    class DIRECTION(enum.Enum) :
        "argument direction."
        IN = "in" # client to server
        OUT = "out" # server to client
    #end DIRECTION

    class ACCESS(enum.Enum) :
        "property access."
        READ = "read"
        WRITE = "write"
        READWRITE = "readwrite"
    #end ACCESS

    class PROP_CHANGE_NOTIFICATION(enum.Enum) :
        "how/if a changed property emits a notification signal."
        NEW_VALUE = "true" # notification includes new value
        INVALIDATES = "invalidates" # notification does not include new value
        CONST = "const" # property shouldn’t change
        NONE = "false" # does not notify changes
    #end PROP_CHANGE_NOTIFICATION

    class Annotation(_TagCommon) :
        __slots__ = ("name", "value")
        tag_name = "annotation"
        tag_attrs = ("name", "value")
        tag_elts = {}

        def __init__(self, name, value) :
            self.name = name
            self.value = value
        #end __init__

    #end Annotation

    def _get_annotations(annotations) :
        # common validation of annotations arguments.
        if not all(isinstance(a, Introspection.Annotation) for a in annotations) :
            raise TypeError("annotations must be Annotation instances")
        #end if
        return \
            annotations
    #end _get_annotations

    class Interface(_TagCommon) :
        __slots__ = ("name", "methods", "signals", "properties", "annotations")
        tag_name = "interface"
        tag_attrs = ("name",)

        class Method(_TagCommon) :
            __slots__ = ("name", "args", "annotations")
            tag_name = "method"
            tag_attrs = ("name",)

            class Arg(_TagCommon) :
                __slots__ = ("name", "type", "direction", "annotations")
                tag_name = "arg"
                tag_attrs = ("name", "type", "direction")
                tag_attrs_optional = {"name"}
                tag_elts = {}
                attr_convert = {} # {"direction" : Introspection.DIRECTION} assigned below

                def __init__(self, *, name = None, type, direction, annotations = ()) :
                    if not isinstance(direction, Introspection.DIRECTION) :
                        raise TypeError("direction must be an Introspection.DIRECTION.xxx enum")
                    #end if
                    self.name = name
                    self.type = parse_single_signature(type)
                    self.direction = direction
                    self.annotations = Introspection._get_annotations(annotations)
                #end __init__

            #end Arg

            tag_elts = {"args" : Arg}

            def __init__(self, name, args = (), annotations = ()) :
                if not all(isinstance(a, self.Arg) for a in args) :
                    raise TypeError("args must be Arg instances")
                #end if
                self.name = name
                self.args = list(args)
                self.annotations = Introspection._get_annotations(annotations)
            #end __init__

            @property
            def in_signature(self) :
                return \
                    list(a.type for a in self.args if a.direction == Introspection.DIRECTION.IN)
            #end in_signature

            @property
            def out_signature(self) :
                return \
                    list \
                      (a.type for a in self.args if a.direction == Introspection.DIRECTION.OUT)
            #end out_signature

            @property
            def expect_reply(self) :
                "will there be replies to this request method."
                return \
                    self.get_annotation("org.freedesktop.DBus.Method.NoReply") != "true"
            #end expect_reply

        #end Method

        class Signal(_TagCommon) :
            __slots__ = ("name", "args", "annotations")
            tag_name = "signal"
            tag_attrs = ("name",)

            class Arg(_TagCommon) :
                __slots__ = ("name", "type", "direction", "annotations")
                tag_name = "arg"
                tag_attrs = ("name", "type", "direction")
                tag_attrs_optional = {"name", "direction"}
                tag_elts = {}
                attr_convert = {} # {"direction" : Introspection.DIRECTION} assigned below

                def __init__(self, *, name = None, type, direction = None, annotations = ()) :
                    if direction  is not None and direction != Introspection.DIRECTION.OUT :
                        raise ValueError("direction can only be Introspection.DIRECTION.OUT")
                    #end if
                    self.name = name
                    self.type = parse_single_signature(type)
                    self.direction = direction
                    self.annotations = Introspection._get_annotations(annotations)
                #end __init__

            #end Arg

            tag_elts = {"args" : Arg}

            def __init__(self, name, args = (), annotations = ()) :
                if not all(isinstance(a, self.Arg) for a in args) :
                    raise TypeError("args must be Arg instances")
                #end if
                self.name = name
                self.args = list(args)
                self.annotations = Introspection._get_annotations(annotations)
            #end __init__

            @property
            def in_signature(self) :
                return \
                    list(a.type for a in self.args)
            #end in_signature

        #end Signal

        class Property(_TagCommon) :
            __slots__ = ("name", "type", "access", "annotations")
            tag_name = "property"
            tag_attrs = ("name", "type", "access")
            tag_elts = {}
            attr_convert = {} # {"access" : Introspection.ACCESS} assigned below

            def __init__(self, name, type, access, annotations = ()) :
                if not isinstance(access, Introspection.ACCESS) :
                    raise TypeError("access must be an Introspection.ACCESS.xxx enum")
                #end if
                self.name = name
                self.type = parse_single_signature(type)
                self.access = access
                self.annotations = Introspection._get_annotations(annotations)
            #end __init__

        #end Property

        tag_elts = {"methods" : Method, "signals" : Signal, "properties" : Property}

        def __init__(self, name, methods = (), signals = (), properties = (), annotations = ()) :
            if not all(isinstance(m, self.Method) for m in methods) :
                raise TypeError("methods must be Method instances")
            #end if
            if not all(isinstance(s, self.Signal) for s in signals) :
                raise TypeError("signals must be Signal instances")
            #end if
            if not all(isinstance(p, self.Property) for p in properties) :
                raise TypeError("properties must be Property instances")
            #end if
            self.name = name
            self.methods = list(methods)
            self.signals = list(signals)
            self.properties = list(properties)
            self.annotations = Introspection._get_annotations(annotations)
        #end __init__

        @property
        def methods_by_name(self) :
            "returns a dict associating all the methods with their names."
            return \
                dict((method.name, method) for method in self.methods)
        #end methods_by_name

        @property
        def signals_by_name(self) :
            "returns a dict associating all the signals with their names."
            return \
                dict((signal.name, signal) for signal in self.signals)
        #end signals_by_name

        @property
        def properties_by_name(self) :
            "returns a dict associating all the properties with their names."
            return \
                dict((prop.name, prop) for prop in self.properties)
        #end properties_by_name

    #end Interface
    Interface.Method.Arg.attr_convert["direction"] = DIRECTION
    Interface.Signal.Arg.attr_convert["direction"] = lambda x : (lambda : None, lambda : Introspection.DIRECTION(x))[x  is not None]()
    Interface.Property.attr_convert["access"] = ACCESS

    class StubInterface(_TagCommon) :
        "use this as a replacement for an Interface that you don’t want" \
        " to see expanded, e.g. if it has already been seen."

        __slots__ = ("name", "annotations")
        tag_name = "interface"
        tag_attrs = ("name",)
        tag_elts = {}

        def __init__(self, name) :
            self.name = name
            self.annotations = ()
        #end __init__

    #end StubInterface

    class Node(_TagCommon) :
        __slots__ = ("name", "interfaces", "nodes", "annotations")
        tag_name = "node"
        tag_attrs = ("name",)

        def __init__(self, name, interfaces = (), nodes = (), annotations = ()) :
            if not all(isinstance(i, (Introspection.Interface, Introspection.StubInterface)) for i in interfaces) :
                raise TypeError("interfaces must be Interface or StubInterface instances")
            #end if
            if not all(isinstance(n, Introspection.Node) for n in nodes) :
                raise TypeError("nodes must be Node instances")
            #end if
            self.name = name
            self.interfaces = interfaces
            self.nodes = nodes
            self.annotations = Introspection._get_annotations(annotations)
        #end __init__

        @property
        def interfaces_by_name(self) :
            "returns a dict associating all the interfaces with their names."
            return \
                dict((iface.name, iface) for iface in self.interfaces)
        #end interfaces_by_name

        @property
        def nodes_by_name(self) :
            "returns a dict associating all the child nodes with their names."
            return \
                dict((node.name, node) for node in self.nodes)
        #end nodes_by_name

    #end Node
    Node.tag_elts = {"interfaces" : Interface, "nodes" : Node}

    tag_elts = {"interfaces" : Interface, "nodes" : Node}

    def __init__(self, name = None, interfaces = (), nodes = (), annotations = ()) :
        if not all(isinstance(i, self.Interface) for i in interfaces) :
            raise TypeError("interfaces must be Interface instances")
        #end if
        if not all(isinstance(n, self.Node) for n in nodes) :
            raise TypeError("nodes must be Node instances")
        #end if
        self.name = name
        self.interfaces = list(interfaces)
        self.nodes = list(nodes)
        self.annotations = Introspection._get_annotations(annotations)
    #end __init__

    @property
    def interfaces_by_name(self) :
        "returns a dict associating all the interfaces with their names."
        return \
            dict((iface.name, iface) for iface in self.interfaces)
    #end interfaces_by_name

    @property
    def nodes_by_name(self) :
        "returns a dict associating all the nodes with their names."
        return \
            dict((node.name, node) for node in self.nodes)
    #end nodes_by_name

    @classmethod
    def parse(celf, s) :
        "generates an Introspection tree from the given XML string description."

        def from_string_elts(celf, attrs, tree) :
            elts = dict((k, attrs[k]) for k in attrs)
            child_tags = dict \
              (
                (childclass.tag_name, childclass)
                for childclass in tuple(celf.tag_elts.values()) + (Introspection.Annotation,)
              )
            children = []
            for child in tree :
                if child.tag not in child_tags :
                    raise KeyError("unrecognized tag %s" % child.tag)
                #end if
                childclass = child_tags[child.tag]
                childattrs = {}
                for attrname in childclass.tag_attrs :
                    if hasattr(childclass, "tag_attrs_optional") and attrname in childclass.tag_attrs_optional :
                        childattrs[attrname] = child.attrib.get(attrname, None)
                    else :
                        if attrname not in child.attrib :
                            raise ValueError("missing %s attribute for %s tag" % (attrname, child.tag))
                        #end if
                        childattrs[attrname] = child.attrib[attrname]
                    #end if
                #end for
                if hasattr(childclass, "attr_convert") :
                    for attr in childclass.attr_convert :
                        if attr in childattrs :
                            childattrs[attr] = childclass.attr_convert[attr](childattrs[attr])
                        #end if
                    #end for
                #end if
                children.append(from_string_elts(childclass, childattrs, child))
            #end for
            for child_tag, childclass in tuple(celf.tag_elts.items()) + ((), (("annotations", Introspection.Annotation),))[tree.tag != "annotation"] :
                for child in children :
                    if isinstance(child, childclass) :
                        if child_tag not in elts :
                            elts[child_tag] = []
                        #end if
                        elts[child_tag].append(child)
                    #end if
                #end for
            #end for
            return \
                celf(**elts)
        #end from_string_elts

    #begin parse
        tree = XMLElementTree.fromstring(s)
        assert tree.tag == "node", "root of introspection tree must be <node> tag"
        return \
            from_string_elts(Introspection, {}, tree)
    #end parse

    def unparse(self, indent_step = 4, max_linelen = 72) :
        "returns an XML string description of this Introspection tree."

        out = io.StringIO()

        def to_string(obj, indent) :
            tag_name = obj.tag_name
            attrs = []
            for attrname in obj.tag_attrs :
                attr = getattr(obj, attrname)
                if attr  is not None :
                    if isinstance(attr, enum.Enum) :
                        attr = attr.value
                    elif isinstance(attr, Type) :
                        attr = unparse_signature(attr)
                    elif not isinstance(attr, str) :
                        raise TypeError("unexpected attribute type %s for %s" % (type(attr).__name__, repr(attr)))
                    #end if
                    attrs.append("%s=%s" % (attrname, quote_xml_attr(attr)))
                #end if
            #end for
            has_elts = \
              (
                    sum
                      (
                        len(getattr(obj, attrname))
                        for attrname in
                                tuple(obj.tag_elts.keys())
                            +
                                ((), ("annotations",))
                                    [not isinstance(obj, Introspection.Annotation)]
                      )
                !=
                    0
              )
            out.write(" " * indent + "<" + tag_name)
            if (
                    max_linelen  is not None
                and
                            indent
                        +
                            len(tag_name)
                        +
                            sum((len(s) + 1) for s in attrs)
                        +
                            2
                        +
                            int(has_elts)
                    >
                        max_linelen
            ) :
                out.write("\n")
                for attr in attrs :
                    out.write(" " * (indent + indent_step))
                    out.write(attr)
                    out.write("\n")
                #end for
                out.write(" " * indent)
            else :
                for attr in attrs :
                    out.write(" ")
                    out.write(attr)
                #end for
            #end if
            if not has_elts :
                out.write("/")
            #end if
            out.write(">\n")
            if has_elts :
                for attrname in sorted(obj.tag_elts.keys()) + ["annotations"] :
                    for elt in getattr(obj, attrname) :
                        to_string(elt, indent + indent_step)
                    #end for
                #end for
                out.write(" " * indent + "</" + tag_name + ">\n")
            #end if
        #end to_string

    #begin unparse
        out.write(DBUS.INTROSPECT_1_0_XML_DOCTYPE_DECL_NODE)
        out.write("<node")
        if self.name  is not None :
            out.write(" name=%s" % quote_xml_attr(self.name))
        #end if
        out.write(">\n")
        for elt in self.interfaces :
            to_string(elt, indent_step)
        #end for
        for elt in self.nodes :
            to_string(elt, indent_step)
        #end for
        out.write("</node>\n")
        return \
            out.getvalue()
    #end unparse

#end Introspection

del _TagCommon

#+
# Standard interfaces
#-

standard_interfaces = \
    {
        DBUS.INTERFACE_PEER :
            # note implementation of this is hard-coded inside libdbus
            Introspection.Interface
              (
                name = DBUS.INTERFACE_PEER,
                methods =
                    [
                        Introspection.Interface.Method(name = "Ping"),
                        Introspection.Interface.Method
                          (
                            name = "GetMachineId",
                            args =
                                [
                                    Introspection.Interface.Method.Arg
                                      (
                                        name = "machine_uuid",
                                        type = BasicType(TYPE.STRING),
                                        direction = Introspection.DIRECTION.OUT,
                                      ),
                                ]
                          ),
                    ],
              ),
        DBUS.INTERFACE_LOCAL :
            # note implementation of this is hard-coded inside, and specific to, libdbus
            Introspection.Interface
              (
                name = DBUS.INTERFACE_LOCAL,
                signals =
                    [
                        Introspection.Interface.Signal(name = "Disconnected"),
                          # auto-generated by libdbus with path = DBUS.PATH_LOCAL
                          # when connection is closed; cannot be explicitly sent by
                          # clients. Documented here:
                          # <https://lists.freedesktop.org/archives/dbus/2018-October/017587.html>
                    ],
              ),
        DBUS.INTERFACE_DBUS :
            Introspection.Interface
              (
                name = DBUS.INTERFACE_DBUS,
                methods =
                    [
                        Introspection.Interface.Method
                          (
                            name = "Hello",
                            args =
                                [
                                    Introspection.Interface.Method.Arg
                                      (
                                        type = BasicType(TYPE.STRING),
                                        direction = Introspection.DIRECTION.OUT,
                                      ), # returned unique name
                                ]
                          ),
                        Introspection.Interface.Method
                          (
                            name = "RequestName",
                            args =
                                [
                                    Introspection.Interface.Method.Arg
                                      (
                                        type = BasicType(TYPE.STRING),
                                        direction = Introspection.DIRECTION.IN,
                                      ), # name
                                    Introspection.Interface.Method.Arg
                                      (
                                        type = BasicType(TYPE.UINT32),
                                        direction = Introspection.DIRECTION.IN,
                                      ), # flags DBUS.NAME_FLAG_xxx
                                    Introspection.Interface.Method.Arg
                                      (
                                        type = BasicType(TYPE.UINT32),
                                        direction = Introspection.DIRECTION.OUT,
                                      ), # result DBUS.REQUEST_NAME_REPLY_xxx
                                ]
                          ),
                        Introspection.Interface.Method
                          (
                            name = "ReleaseName",
                            args =
                                [
                                    Introspection.Interface.Method.Arg
                                      (
                                        type = BasicType(TYPE.STRING),
                                        direction = Introspection.DIRECTION.IN,
                                      ),
                                    Introspection.Interface.Method.Arg
                                      (
                                        type = BasicType(TYPE.UINT32),
                                        direction = Introspection.DIRECTION.OUT,
                                      ), # result DBUS.RELEASE_NAME_REPLY_xxx
                                ]
                          ),
                        Introspection.Interface.Method
                          (
                            name = "StartServiceByName",
                            args =
                                [
                                    Introspection.Interface.Method.Arg
                                      (
                                        type = BasicType(TYPE.STRING),
                                        direction = Introspection.DIRECTION.IN,
                                      ), # name
                                    Introspection.Interface.Method.Arg
                                      (
                                        type = BasicType(TYPE.UINT32),
                                        direction = Introspection.DIRECTION.IN,
                                      ), # flags (currently unused)
                                    Introspection.Interface.Method.Arg
                                      (
                                        type = BasicType(TYPE.UINT32),
                                        direction = Introspection.DIRECTION.OUT,
                                      ), # result DBUS.START_REPLY_xxx
                                ]
                          ),
                        Introspection.Interface.Method
                          (
                            name = "UpdateActivationEnvironment",
                            args =
                                [
                                    Introspection.Interface.Method.Arg
                                      (
                                        type = DictType
                                          (
                                            keytype = BasicType(TYPE.STRING),
                                            valuetype = BasicType(TYPE.STRING)
                                          ),
                                        direction = Introspection.DIRECTION.IN,
                                      ), # environment
                                ]
                          ),
                        Introspection.Interface.Method
                          (
                            name = "NameHasOwner",
                            args =
                                [
                                    Introspection.Interface.Method.Arg
                                      (
                                        type = BasicType(TYPE.STRING),
                                        direction = Introspection.DIRECTION.IN,
                                      ), # name
                                    Introspection.Interface.Method.Arg
                                      (
                                        type = BasicType(TYPE.BOOLEAN),
                                        direction = Introspection.DIRECTION.OUT,
                                      ),
                                ]
                          ),
                        Introspection.Interface.Method
                          (
                            name = "ListNames",
                            args =
                                [
                                    Introspection.Interface.Method.Arg
                                      (
                                        type = ArrayType(BasicType(TYPE.STRING)),
                                        direction = Introspection.DIRECTION.OUT,
                                      ),
                                ]
                          ),
                        Introspection.Interface.Method
                          (
                            name = "ListActivatableNames",
                            args =
                                [
                                    Introspection.Interface.Method.Arg
                                      (
                                        type = ArrayType(BasicType(TYPE.STRING)),
                                        direction = Introspection.DIRECTION.OUT,
                                      ),
                                ]
                          ),
                        Introspection.Interface.Method
                          (
                            name = "AddMatch",
                            args =
                                [
                                    Introspection.Interface.Method.Arg
                                      (
                                        type = BasicType(TYPE.STRING),
                                        direction = Introspection.DIRECTION.IN,
                                      ),
                                ]
                          ),
                        Introspection.Interface.Method
                          (
                            name = "RemoveMatch",
                            args =
                                [
                                    Introspection.Interface.Method.Arg
                                      (
                                        type = BasicType(TYPE.STRING),
                                        direction = Introspection.DIRECTION.IN,
                                      ),
                                ]
                          ),
                        Introspection.Interface.Method
                          (
                            name = "GetNameOwner",
                            args =
                                [
                                    Introspection.Interface.Method.Arg
                                      (
                                        type = BasicType(TYPE.STRING),
                                        direction = Introspection.DIRECTION.IN,
                                      ),
                                    Introspection.Interface.Method.Arg
                                      (
                                        type = BasicType(TYPE.STRING),
                                        direction = Introspection.DIRECTION.OUT,
                                      ),
                                ]
                          ),
                        Introspection.Interface.Method
                          (
                            name = "ListQueuedOwners",
                            args =
                                [
                                    Introspection.Interface.Method.Arg
                                      (
                                        type = BasicType(TYPE.STRING),
                                        direction = Introspection.DIRECTION.IN,
                                      ),
                                    Introspection.Interface.Method.Arg
                                      (
                                        type = ArrayType(BasicType(TYPE.STRING)),
                                        direction = Introspection.DIRECTION.OUT,
                                      ),
                                ]
                          ),
                        Introspection.Interface.Method
                          (
                            name = "GetConnectionUnixUser",
                            args =
                                [
                                    Introspection.Interface.Method.Arg
                                      (
                                        type = BasicType(TYPE.STRING),
                                        direction = Introspection.DIRECTION.IN,
                                      ),
                                    Introspection.Interface.Method.Arg
                                      (
                                        type = BasicType(TYPE.UINT32),
                                        direction = Introspection.DIRECTION.OUT,
                                      ),
                                ]
                          ),
                        Introspection.Interface.Method
                          (
                            name = "GetConnectionUnixProcessID",
                            args =
                                [
                                    Introspection.Interface.Method.Arg
                                      (
                                        type = BasicType(TYPE.STRING),
                                        direction = Introspection.DIRECTION.IN,
                                      ),
                                    Introspection.Interface.Method.Arg
                                      (
                                        type = BasicType(TYPE.UINT32),
                                        direction = Introspection.DIRECTION.OUT,
                                      ),
                                ]
                          ),
                        Introspection.Interface.Method
                          (
                            name = "GetAdtAuditSessionData",
                            args =
                                [
                                    Introspection.Interface.Method.Arg
                                      (
                                        type = BasicType(TYPE.STRING),
                                        direction = Introspection.DIRECTION.IN,
                                      ),
                                    Introspection.Interface.Method.Arg
                                      (
                                        type = ArrayType(BasicType(TYPE.BYTE)),
                                        direction = Introspection.DIRECTION.OUT,
                                      ),
                                ]
                          ),
                        Introspection.Interface.Method
                          (
                            name = "GetConnectionSELinuxSecurityContext",
                            args =
                                [
                                    Introspection.Interface.Method.Arg
                                      (
                                        type = BasicType(TYPE.STRING),
                                        direction = Introspection.DIRECTION.IN,
                                      ),
                                    Introspection.Interface.Method.Arg
                                      (
                                        type = ArrayType(BasicType(TYPE.BYTE)),
                                        direction = Introspection.DIRECTION.OUT,
                                      ),
                                ]
                          ),
                        Introspection.Interface.Method
                          (
                            name = "ReloadConfig",
                          ),
                        Introspection.Interface.Method
                          (
                            name = "GetId",
                            args =
                                [
                                    Introspection.Interface.Method.Arg
                                      (
                                        type = BasicType(TYPE.STRING),
                                        direction = Introspection.DIRECTION.OUT,
                                      ),
                                ]
                          ),
                        Introspection.Interface.Method
                          (
                            name = "GetConnectionCredentials",
                            args =
                                [
                                    Introspection.Interface.Method.Arg
                                      (
                                        type = BasicType(TYPE.STRING),
                                        direction = Introspection.DIRECTION.IN,
                                      ),
                                    Introspection.Interface.Method.Arg
                                      (
                                        type = DictType(BasicType(TYPE.STRING), VariantType()),
                                        direction = Introspection.DIRECTION.OUT,
                                      ),
                                ]
                          ),
                    ],
                signals =
                    [
                        Introspection.Interface.Signal
                          (
                            name = "NameOwnerChanged",
                            args =
                                [
                                    Introspection.Interface.Signal.Arg
                                      (
                                        type = BasicType(TYPE.STRING),
                                      ), # bus name
                                    Introspection.Interface.Signal.Arg
                                      (
                                        type = BasicType(TYPE.STRING),
                                      ), # old owner, empty if none
                                    Introspection.Interface.Signal.Arg
                                      (
                                        type = BasicType(TYPE.STRING),
                                      ), # new owner, empty if none
                                ]
                          ),
                        Introspection.Interface.Signal
                          (
                            name = "NameLost", # sent to previous owner of name
                            args =
                                [
                                    Introspection.Interface.Signal.Arg
                                      (
                                        type = BasicType(TYPE.STRING),
                                      ),
                                ]
                          ),
                        Introspection.Interface.Signal
                          (
                            name = "NameAcquired", # sent to new owner of name
                            args =
                                [
                                    Introspection.Interface.Signal.Arg
                                      (
                                        type = BasicType(TYPE.STRING),
                                      ),
                                ]
                          ),
                    ],
              ),
        DBUS.INTERFACE_INTROSPECTABLE :
            Introspection.Interface
              (
                name = DBUS.INTERFACE_INTROSPECTABLE,
                methods =
                    [
                        Introspection.Interface.Method
                          (
                            name = "Introspect",
                            args =
                                [
                                    Introspection.Interface.Method.Arg
                                      (
                                        name = "data",
                                        type = BasicType(TYPE.STRING),
                                        direction = Introspection.DIRECTION.OUT,
                                      ),
                                ]
                          ),
                    ],
              ),
        DBUS.INTERFACE_PROPERTIES :
            Introspection.Interface
              (
                name = DBUS.INTERFACE_PROPERTIES,
                methods =
                    [
                        Introspection.Interface.Method
                          (
                            name = "Get",
                            args =
                                [
                                    Introspection.Interface.Method.Arg
                                      (
                                        name = "interface_name",
                                        type = BasicType(TYPE.STRING),
                                        direction = Introspection.DIRECTION.IN,
                                      ),
                                    Introspection.Interface.Method.Arg
                                      (
                                        name = "property_name",
                                        type = BasicType(TYPE.STRING),
                                        direction = Introspection.DIRECTION.IN,
                                      ),
                                    Introspection.Interface.Method.Arg
                                      (
                                        name = "value",
                                        type = VariantType(),
                                        direction = Introspection.DIRECTION.OUT,
                                      ),
                                ],
                          ),
                        Introspection.Interface.Method
                          (
                            name = "Set",
                            args =
                                [
                                    Introspection.Interface.Method.Arg
                                      (
                                        name = "interface_name",
                                        type = BasicType(TYPE.STRING),
                                        direction = Introspection.DIRECTION.IN,
                                      ),
                                    Introspection.Interface.Method.Arg
                                      (
                                        name = "property_name",
                                        type = BasicType(TYPE.STRING),
                                        direction = Introspection.DIRECTION.IN,
                                      ),
                                    Introspection.Interface.Method.Arg
                                      (
                                        name = "value",
                                        type = VariantType(),
                                        direction = Introspection.DIRECTION.IN,
                                      ),
                                ],
                          ),
                        Introspection.Interface.Method
                          (
                            name = "GetAll",
                            args =
                                [
                                    Introspection.Interface.Method.Arg
                                      (
                                        name = "interface_name",
                                        type = BasicType(TYPE.STRING),
                                        direction = Introspection.DIRECTION.IN,
                                      ),
                                    Introspection.Interface.Method.Arg
                                      (
                                        name = "values",
                                        type = DictType(BasicType(TYPE.STRING), VariantType()),
                                        direction = Introspection.DIRECTION.OUT,
                                      ),
                                ],
                          ),
                    ],
                signals =
                    [
                        Introspection.Interface.Signal
                          (
                            name = "PropertiesChanged",
                            args =
                                [
                                    Introspection.Interface.Signal.Arg
                                      (
                                        name = "interface_name",
                                        type = BasicType(TYPE.STRING),
                                      ),
                                    Introspection.Interface.Signal.Arg
                                      (
                                        name = "changed_properties",
                                        type = DictType(BasicType(TYPE.STRING), VariantType()),
                                      ),
                                    Introspection.Interface.Signal.Arg
                                      (
                                        name = "invalidated_properties",
                                        type = ArrayType(BasicType(TYPE.STRING)),
                                      ),
                                ],
                          ),
                    ],
              ),
        DBUS.INTERFACE_MONITORING :
            Introspection.Interface
              (
                name = DBUS.INTERFACE_MONITORING,
                methods =
                    [
                        Introspection.Interface.Method
                          (
                            name = "BecomeMonitor",
                            args =
                                [
                                    Introspection.Interface.Method.Arg
                                      (
                                        type = ArrayType(BasicType(TYPE.STRING)),
                                        direction = Introspection.DIRECTION.IN,
                                      ), # match rules to add to the connection
                                    Introspection.Interface.Method.Arg
                                      (
                                        type = BasicType(TYPE.UINT32),
                                          # match rules to add to the connection
                                        direction = Introspection.DIRECTION.IN,
                                      ), # flags (currently unused)
                                ],
                          ),
                    ],
              ),
        DBUSX.INTERFACE_OBJECT_MANAGER :
            Introspection.Interface
              (
                name = DBUSX.INTERFACE_OBJECT_MANAGER,
                methods =
                    [
                        Introspection.Interface.Method
                          (
                            name = "GetManagedObjects",
                            args =
                                [
                                    Introspection.Interface.Method.Arg
                                      (
                                        name = "objpath_interfaces_and_properties",
                                        type = DictType
                                          (
                                            BasicType(TYPE.OBJECT_PATH),
                                            DictType
                                              (
                                                BasicType(TYPE.STRING), # interface
                                                DictType(BasicType(TYPE.STRING), VariantType())
                                                  # properties and values
                                              )
                                          ),
                                        direction = Introspection.DIRECTION.OUT,
                                      ),
                                ],
                          ),
                    ],
                signals =
                    [
                        Introspection.Interface.Signal
                          (
                            name = "InterfacesAdded",
                            args =
                                [
                                    Introspection.Interface.Signal.Arg
                                      (
                                        name = "object_path",
                                        type = BasicType(TYPE.OBJECT_PATH),
                                      ),
                                    Introspection.Interface.Signal.Arg
                                      (
                                        name = "interfaces_and_properties",
                                        type = DictType
                                          (
                                            BasicType(TYPE.STRING), # interface added/changed
                                            DictType(BasicType(TYPE.STRING), VariantType())
                                              # properties and values added
                                          ),
                                      ),
                                ],
                          ),
                        Introspection.Interface.Signal
                          (
                            name = "InterfacesRemoved",
                            args =
                                [
                                    Introspection.Interface.Signal.Arg
                                      (
                                        name = "object_path",
                                        type = BasicType(TYPE.OBJECT_PATH),
                                      ),
                                    Introspection.Interface.Signal.Arg
                                      (
                                        name = "interfaces",
                                        type = ArrayType(BasicType(TYPE.STRING)),
                                          # interfaces removed
                                      ),
                                ],
                          ),
                    ],
              ),
    }

#+
# Cleanup
#-

def _atexit() :
    # disable all __del__ methods at process termination to avoid segfaults
    for cls in Connection, Server, PreallocatedSend, Message, PendingCall, Error, AddressEntries :
        delattr(cls, "__del__")
    #end for
#end _atexit
atexit.register(_atexit)
del _atexit
