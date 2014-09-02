""" Collection of miscellaneous helpers to alter the validation process. """

import collections
import six

from .schema.errors import SchemaError, Invalid
from . import Schema


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

    ```python,
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
            raise Invalid(_(u'Wrong value type'), cls_name, format_value_type(v), validator=Object)

        # Validate using ObjectProxy and unwrap
        return compiled(ObjectProxy(v)).obj
    object_validator.name = cls_name

    return object_validator

# TODO: Msg
# TODO: message
# TODO: truth

__all__ = ('Object',)
