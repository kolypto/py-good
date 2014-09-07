""" Despite Good is modelled after Voluptuous and is highly compatible,
there still are differences that would definitely break your project.

If you're not ready for such a change -- `good.voluptuous` is the solution:
compatibility layer for switching from [voluptuous 0.8.5](https://github.com/alecthomas/voluptuous)
with 100% compatibility.

This is a drop-in replacement that passes all voluptuous unit-tests and hence should work perfectly.
Here's how to use it

```python
#from voluptuous import *  # no more
from good.voluptuous import *  # replacement

# .. and use it like before
```

Includes all the features and is absolutely compatible, except for the error message texts,
which became much more user-friendly :)

Migration steps:

1. Replace `voluptuous` imports with `good.voluptuous`
2. Run your application tests and see how it behaves
3. Module by module, replace `good.voluptuous` with just `good`, keeping the differences in mind.

Also note the small differences that are still present:

* Settings for `required` and `extra` are not inherited by embedded mappings.

    If your top-level schema defines `required=False`, embedded mappings will still have the default `required=True`!
    And same with `extra`.

* Different error message texts, which are easier to understand :)
* Raises `Invalid` rather than `MultipleInvalid` for rejected extra mapping keys (see [`Extra`](#extra))

Good luck! :)
"""

import good
import six
import os
from functools import wraps

def _convert_errors(func):
    """ Decorator to convert throws errors to Voluptuous format."""
    cast_Invalid = lambda e: Invalid(
        u"{message}, expected {expected}".format(
            message=e.message,
            expected=e.expected)
        if e.expected != u'-none-' else e.message,
        e.path,
        six.text_type(e))

    @wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except good.SchemaError as e:
            raise SchemaError(six.text_type(e))
        except good.MultipleInvalid as ee:
            raise MultipleInvalid([cast_Invalid(e) for e in ee])
        except good.Invalid as e:
            # Since voluptuous throws MultipleInvalid almost always -- we follow the same pattern...
            raise MultipleInvalid([cast_Invalid(e)])
    return wrapper

from good.schema.util import Undefined  # it's not internal
UNDEFINED = Undefined()

# options for extra keys
PREVENT_EXTRA = 0
ALLOW_EXTRA = 1
REMOVE_EXTRA = 2

#region Errors

class Error(Exception): pass

class SchemaError(Error): pass

class Invalid(Error):
    def __init__(self, message, path=None, error_message=None):
        Error.__init__(self,  message)
        self.msg = message
        self.path = path or []
        self.error_message = error_message or message

    def __str__(self):
        path = ' @ data[%s]' % ']['.join(map(repr, self.path)) if self.path else ''
        return self.msg + path


class MultipleInvalid(Invalid):
    def __init__(self, errors=None):
        self.errors = errors[:] if errors else []
        e = errors[0]
        super(MultipleInvalid, self).__init__(e.msg, e.path, e.error_message)

    def __repr__(self):
        return 'MultipleInvalid(%r)' % self.errors

    def __str__(self):
        return str(self.errors[0])

#endregion


#region Markers

class Optional(good.Optional):
    def __init__(self, schema, msg=None):
        super(Optional, self).__init__(schema)

class Required(good.Required):
    def __init__(self, schema, msg=None, default=UNDEFINED):
        super(Required, self).__init__(schema)
        self.msg = msg
        # Voluptuous has `default` keyword here, but we use good.Default instead, so have to simulate
        self.default = default

    def execute(self, d, matches):
        # Simulate voluptuous `default=`
        if not matches and self.default is not UNDEFINED:
            return [(self.key_schema.schema, self.key_schema.schema, self.default)]

        try:
            return super(Required, self).execute(d, matches)
        except good.Invalid as e:
            # Replace the message (if required)
            if self.msg:
                e.message = self.msg
            raise e

from good import Extra
extra = Extra  # alias

#endregion

#region Schema

class Schema(object):
    #: Value conversion map for the `required` argument
    _required_arg_map = {
        True: Required,
        False: Optional
    }
    #: Value conversion map for the `extra` argument
    _extra_arg_map = {
        False: good.Reject,
        True: good.Allow,
        PREVENT_EXTRA: good.Reject,
        ALLOW_EXTRA: good.Allow,
        REMOVE_EXTRA: good.Remove,
    }

    @_convert_errors
    def __init__(self, schema, required=False, extra=PREVENT_EXTRA):
        self.schema = schema
        self.required = required
        self.extra = extra

        try:
            # It's a callable anyway, let it be here
            self._compiled = good.Schema(schema,
                                         default_keys=self._required_arg_map[required],
                                         extra_keys=self._extra_arg_map[extra])
        except good.SchemaError as e:
            raise SchemaError(e.message)

    @_convert_errors
    def __call__(self, data):
        return self._compiled(data)


#endregion

#region Helpers

class Object(good.Object):
    def __init__(self, schema, cls=UNDEFINED):
        # Convert argument
        if cls is UNDEFINED:
            cls = None
        # Proceed
        super(Object, self).__init__(schema, cls)

    def __call__(self, v):
        return super(Object, self).__call__(v)


def Msg(schema, msg):
    return good.Msg(schema, six.text_type(msg))

def message(default=None):
    message_decorator = good.message(six.text_type(default or u'invalid value'))
    # voluptuous produces a 2nd-level decorator which allows to override the message, good only allows Msg()
    def decorator(func):
        return lambda msg=None: _wrapMsg(message_decorator(func), msg)
    return decorator

def truth(f):
    return good.truth(u'not a valid value')(f)

#endregion

#region Validators

def _wrapMsg(v, msg=None):
    """ Wrap a validator in Msg, if `msg` was provided """
    return v if not msg else Msg(v, msg)

def Coerce(type, msg=None):
    return _wrapMsg(good.Coerce(type), msg)

def IsTrue():
    return good.Truthy()

def IsFalse():
    return good.Falsy()

def Boolean():
    return good.Boolean()

def Any(*validators, **kwargs):
    msg = kwargs.pop('msg', None)
    assert not kwargs, 'Sorry, Any() does not support Schema keyword arguments anymore'
    return _wrapMsg(good.Any(*validators), msg)

def All(*validators, **kwargs):
    msg = kwargs.pop('msg', None)
    assert not kwargs, 'Sorry, All() does not support Schema keyword arguments anymore'
    return _wrapMsg(good.All(*validators), msg)

def Match(pattern, msg=None):
    return good.Match(pattern, msg)

def Replace(pattern, substitution, msg=None):
    return good.Replace(pattern, substitution, msg)

def Url():
    return good.Url(['http', 'https', 'ftp'])

@message(u'not a file')
@truth
def IsFile(v):
    return os.path.isfile(v)

@message(u'not a directory')
@truth
def IsDir(v):
    return os.path.isdir(v)

@message(u'path does not exist')
@truth
def PathExists(v):
    return os.path.exists(v)

def Range(min=None, max=None, min_included=True, max_included=True, msg=None):
    # Alter min, max when the range is not inclusive
    if min is not None and not min_included:
        min += 1
    if max is not None and not max_included:
        max -= 1
    # Finish
    return _wrapMsg(good.Range(min, max), msg)

def Clamp(min=None, max=None, msg=None):
    return _wrapMsg(good.Clamp(min, max), msg)

def Length(min=None, max=None, msg=None):
    return _wrapMsg(good.Length(min, max), msg)

def In(container, msg=None):
    return _wrapMsg(good.In(container), msg)

# These are not callable in voluptuous
Lower = good.Lower()
Upper = good.Upper()
Capitalize = good.Capitalize()
Title = good.Title()

def DefaultTo(default_value, msg=None):
    # Completely useless!
    @wraps(DefaultTo)
    def f(v):
        if v is None:
            v = default_value
        return v
    return f

#endregion
