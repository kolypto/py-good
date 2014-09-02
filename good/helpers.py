""" Collection of miscellaneous helpers to alter the validation process. """

import six
import collections
from functools import wraps, update_wrapper

from .schema.util import const, get_callable_name
from . import Schema, SchemaError, Invalid


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


def Object(schema, cls=None):
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
    :type schema: Mapping
    :param cls: Require instances of a specific class. If `None`, allows all classes.
    :type cls: None|type|tuple[type]
    :return: Validator
    :rtype: callable
    """
    # Input validation
    if not isinstance(schema, collections.Mapping):
        raise SchemaError('Object() argument must be a mapping, {} given'.format(type(schema)))

    # Prepare
    format_cls_name = lambda c: _(u'Object({cls})').format(cls=c.__name__ if c else u'*')
    format_value_type = lambda v: format_cls_name(type(v)) if isinstance(v, object) else six.text_type(type(v).__name__)

    cls_name = format_cls_name(cls)
    if cls is None:
        cls = object

    # Compile schema
    compiled = Schema(schema)

    # Validator
    def object_validator(v):
        # Check type
        if not isinstance(v, cls):
            raise Invalid(_(u'Wrong value type'), cls_name, format_value_type(v))

        # Validate using ObjectProxy and unwrap
        return compiled(ObjectProxy(v)).obj
    object_validator.name = cls_name

    return object_validator


def Msg(schema, message):
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
    :return: Wrapped schema callable
    :rtype: callable
    """
    assert isinstance(message, six.text_type), 'Msg() message must be a unicode string'

    # Compile schema
    compiled = Schema(schema)

    # Wrapper
    def message_override(v):
        try:
            return compiled(v)
        except Invalid as e:
            # Override message
            e.message = message
            # Raise again
            raise
        except const.transformed_exceptions:
            raise Invalid(message or _(u'Invalid value'))

    # inherit name from the wrapped schema
    message_override.name = compiled.name

    return message_override


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
    :return: Validator callable
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
    #-> Invalid: ValueError: invalid literal for int() with base 10: 'a': expected <lambda>(), got
    Schema(name('int()', lambda x: int(x))('a')
    #-> Invalid: ValueError: invalid literal for int() with base 10: 'a': expected int(), got a
    ```

    Note that it is only useful with lambdas, since function name is used if available:
    see notes on [Schema Callables](#callables).

    :param name: Name to assign on the validator callable
    :type name: unicode
    :param validator: Validator callable. If not provided -- a decorator is returned instead:

        ```python
        @name(u'int()')
        def int(v):
            return int(v)
        ```

    :type validator: callable
    :return: The same validator callable
    :rtype: callable
    """
    validator.name = name
    return validator


def truth(message, expected=None):
    """ Convenience decorator that converts a boolean function into a validator.

    ```python
    import os.path
    from good import Schema, truth

    @truth(u'Must be an existing directory')
    def isDir(v):
        return os.path.isdir(v)

    schema = Schema(isDir)
    schema('/')  #-> '/'
    schema('/404')
    #-> Invalid: Must be an existing directory: expected isDir(), got /404
    ```

    :param message: Validation error message
    :type message: unicode
    :param expected: Expected value string representation, or `None` to get it from the wrapped callable
    :type expected: None|str|unicode
    :return: Validator callable
    :rtype: callable
    """
    assert isinstance(message, six.text_type), '@truth() message must be a unicode string'
    assert isinstance(expected, six.text_type) or expected is None, '@truth() expected must be a unicode string'

    def decorator(func):
        @wraps(func)
        def wrapper(v):
            # Test with the boolean function
            if func(v):
                # Return the value as is
                return v
            else:
                # If the boolean function reported False -- raise Invalid
                raise Invalid(message, expected)
        wrapper.name = get_callable_name(func)  # set a meaningful `name`, which is then used by CompiledSchema
        return wrapper
    return decorator

__all__ = ('Object', 'Msg', 'message', 'name', 'truth')
