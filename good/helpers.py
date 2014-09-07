""" Collection of miscellaneous helpers to alter the validation process. """

import six
import collections
from functools import update_wrapper

from .schema.util import const, get_literal_name, get_callable_name
from . import Schema, SchemaError, Invalid
from .validators.base import ValidatorBase
from .validators.boolean import Check


class ObjectProxy(collections.Mapping, dict):
    """ Proxy object attributes as dictionary keys.

    Used with Object() validator
    """

    def __new__(cls, obj):
        """ Factory for object proxies """
        # Use a different class for slots
        if hasattr(obj, '__slots__'):
            cls = SlotsObjectProxy
        # Instantiate
        return super(ObjectProxy, cls).__new__(cls, obj)

    def __init__(self, obj):
        self.obj = obj
        super(ObjectProxy, self).__init__()

    def __len__(self):
        return 0  # we don't care about the length

    def __iter__(self):
        """ Get an iterator for the object attribute names """
        return iter(vars(self.obj))

    def __contains__(self, key):
        return hasattr(self.obj, six.text_type(key))

    def __getitem__(self, key):
        return getattr(self.obj, six.text_type(key))

    def __setitem__(self, key, value):
        return setattr(self.obj, six.text_type(key), value)

    def __delitem__(self, key):
        return delattr(self.obj, six.text_type(key))


class SlotsObjectProxy(ObjectProxy):
    """ Proxy for objects with __slots__ """

    def __iter__(self):
        # Named tuple?
        if isinstance(self.obj, tuple) and hasattr(self.obj, '_fields'):
            return iter(self.obj._fields)
        # Just Slots
        else:
            return iter(self.obj.__slots__)

    def __setitem__(self, key, value):
        try:
            return super(SlotsObjectProxy, self).__setitem__(key, value)
        except AttributeError:
            # Type does not support assignments (e.g. immutable containers)

            # If the value did not change -- okay, let it be
            if value == self[key]:
                return

            # Otherwise -- fail
            raise


class Object(ValidatorBase):
    """ Specify that the provided mapping should validate an object.

    This uses the same mapping validation rules, but works with attributes instead:

    ```python
    from good import Schema, Object

    intify = lambda v: int(v)  # Naive Coerce(int) implementation

    # Define a class to play with
    class Person(object):
        category = u'Something'  # Not validated

        def __init__(self, name, age):
            self.name = name
            self.age = age

    # Schema
    schema = Schema(Object({
        'name': str,
        'age': intify,
    }))

    # Validate
    schema(Person(name=u'Alex', age='18'))  #-> Girl(name=u'Alex', age=18)
    ```

    Internally, it validates the object's `__dict__`: hence, class attributes are excluded from validation.
    Validation is performed with the help of a wrapper class which proxies object attributes as mapping keys,
    and then Schema validates it as a mapping.

    This inherits the default required/extra keys behavior of the Schema.
    To override, use [`Optional()`](#optional) and [`Extra`](#extra) markers.

    :param schema: Object schema, given as a mapping
    :type schema: Mapping|Callable
    :param cls: Require instances of a specific class. If `None`, allows all classes.
    :type cls: None|type|tuple[type]
    """

    def __init__(self, schema, cls=None):
        # Prepare
        self.name = self._format_cls_name(cls)
        self.cls = object if cls is None else cls

        # Compile schema
        self.compiled = Schema(schema)

    @staticmethod
    def _format_cls_name(c):
        return _(u'Object({cls})').format(cls=c.__name__ if c else u'*')

    def _format_value_type(self, v):
        return self._format_cls_name(type(v)) if isinstance(v, object) else get_literal_name

    def __call__(self, v):
        # Check type
        if not isinstance(v, self.cls):
            raise Invalid(_(u'Wrong value type'), provided=self._format_value_type(v))

        # Validate using ObjectProxy and unwrap
        return self.compiled(ObjectProxy(v)).obj


class Msg(ValidatorBase):
    """ Override the error message reported by the wrapped schema in case of validation errors.

    On validation, if the schema throws [`Invalid`](#invalid) -- the message is overridden with `msg`.

    Some other error types are converted to `Invalid`: see notes on [Schema Callables](#callables).

    ```python
    from good import Schema, Msg

    intify = lambda v: int(v)  # Naive Coerce(int) implementation
    intify.name = u'Number'

    schema = Schema(Msg(intify, u'Need a number'))
    schema(1)  #-> 1
    schema('a')
    #-> Invalid: Need a number: expected Number, got a
    ```

    :param schema: The wrapped schema to modify the error for
    :param message: Error message to use instead of the one that's reported by the underlying schema
    :type message: unicode
    """

    def __init__(self, schema, message):
        assert isinstance(message, six.text_type), 'Msg() message must be a unicode string'
        self.message = message
        self.compiled = Schema(schema).compiled
        self.name = self.compiled.name

    def __getattr__(self, attr):
        """ Inherit all attributes from the wrapped schema """
        return getattr(self.compiled, attr)

    def __call__(self, v):
        try:
            return self.compiled(v)
        except Invalid as ee:
            # Override message
            for e in ee:
                e.message = self.message
            # Raise again
            raise
        except const.transformed_exceptions:
            raise Invalid(self.message or _(u'Invalid value'))


class Test(ValidatorBase):
    """ Test the value with the provided function, expecting that it won't throw errors.

    If no errors were thrown -- the value is valid and *the original input value is used*.
    If any error was thrown -- the value is considered invalid.

    This is especially useful to discard tranformations made by the wrapped validator:

    ```python
    from good import Schema, Coerce

    schema = Schema(Coerce(int))

    schema(123)  #-> 123
    schema('123')  #-> '123' -- still string
    schema('abc')
    #-> Invalid: Invalid value, expected *Integer number, got abc
    ```

    :param fun: Callable to test the value with, or a validator function.

        Note that this won't work with mutable input values since they're modified in-place!

    :type fun: callable|ValidatorBase
    """

    def __init__(self, fun):
        self.fun = fun
        self.name = get_callable_name(fun)

    def __call__(self, v):
        try:
            self.fun(v)
        except Invalid:
            raise
        except Exception:
            raise Invalid(_(u'Invalid value'))
        else:
            return v


def message(message, name=None):
    """ Convenience decorator that applies [`Msg()`](#msg) to a callable.

    ```python
    from good import Schema, message

    @message(u'Need a number')
    def intify(v):
        return int(v)
    ```

    :param message: Error message to use instead
    :type message: unicode
    :param name: Override schema name as well. See [`name`](#name).
    :type name: None|unicode
    :return: decorator
    :rtype: callable
    """
    def decorator(func):
        wf = update_wrapper(Msg(func, message), func)
        if name:
            wf.name = name
        return wf
    return decorator


def name(name, validator=None):
    """ Set a name on a validator callable.

    Useful for user-friendly reporting when using lambdas to populate the [`Invalid.expected`](#invalid) field:

    ```python
    from good import Schema, name

    Schema(lambda x: int(x))('a')
    #-> Invalid: invalid literal for int(): expected <lambda>(), got
    Schema(name('int()', lambda x: int(x))('a')
    #-> Invalid: invalid literal for int(): expected int(), got a
    ```

    Note that it is only useful with lambdas, since function name is used if available:
    see notes on [Schema Callables](#callables).

    :param name: Name to assign on the validator callable
    :type name: unicode
    :param validator: Validator callable. If not provided -- a decorator is returned instead:

        ```python
        from good import name

        @name(u'int()')
        def int(v):
            return int(v)
        ```

    :type validator: callable
    :return: The same validator callable
    :rtype: callable
    """
    # Decorator mode
    if validator is None:
        def decorator(f):
            f.name = name
            return f
        return decorator

    # Direct mode
    validator.name = name
    return validator


def truth(message, expected=None):
    """ Convenience decorator that applies [`Check`](#check) to a callable.

    ```python
    from good import truth

    @truth(u'Must be an existing directory')
    def isDir(v):
        return os.path.isdir(v)
    ```

    :param message: Validation error message
    :type message: unicode
    :param expected: Expected value string representation, or `None` to get it from the wrapped callable
    :type expected: None|str|unicode
    :return: decorator
    :rtype: callable
    """
    def decorator(func):
        return update_wrapper(Check(func, message, expected), func)
    return decorator

__all__ = ('Object', 'Msg', 'Test', 'message', 'name', 'truth')
