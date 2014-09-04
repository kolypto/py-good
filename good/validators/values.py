import collections

from ._base import ValidatorBase
from .. import Invalid
from ..schema.util import get_literal_name, get_type_name, get_primitive_name, const


class In(ValidatorBase):
    """ Validate that a value is in a collection.

    This is a plain simple `value in container` check, where `container` is a collection of literals.

    In constast to [`Any`](#any), it does not compile its arguments into schemas,
    and hence achieves better performance.

    ```python
    from good import Schema, In

    schema = Schema(In({1, 2, 3}))

    schema(1)  #-> 1
    schema(99)
    #-> Invalid: Value not allowed: expected In(1,2,3), got 99
    ```

    The same example will work with [`Any`](#any), but slower :-)

    :param container: Collection of allowed values.

        In addition to naive tuple/list/set/dict, this can be any object that supports `in` operation.
    :type container: collections.Container
    """

    def __init__(self, container):
        assert isinstance(container, collections.Container), '`container` must support `in` operation'
        self.container = container

        self.name = _(u'In({container})').format(
            container=
                _(u',').join(map(get_literal_name, self.container))  # iterable
                if isinstance(container, collections.Iterable) else
                get_primitive_name(self.container)  # not iterable
        )

    def __call__(self, v):
        # Test
        if v not in self.container:
            raise Invalid(_(u'Value not allowed'), self.name, get_literal_name(v))

        # Okay
        return v


class Length(ValidatorBase):
    """ Validate that the provided collection has length in a certain range.

    ```python
    from good import Schema, Length

    schema = Schema(All(
        # Ensure it's a list (and not any other iterable type)
        list,
        # Validate length
        Length(max=3),
    ))
    ```

    Since mappings also have length, they can be validated as well:

    ```python
    schema = Schema({
        # Strings mapped to integers
        str: int,
        # Size = 1..3
        # Empty dicts are not allowed since `str` is implicitly `Required(str)`
        Entire: Length(max=3)
    })

    schema([1])  #-> ok
    schemma([1,2,3,4])
    #-> Invalid: Too many values (3 is the most): expected Length(..3), got 4
    ```

    :param min: Minimal allowed length, or `None` to impose no limits.
    :type min: int|None
    :param max: Maximal allowed length, or `None` to impose no limits.
    :type max: int|None
    """

    def __init__(self, min=None, max=None):
        # `min` validator
        self.min_error = lambda length: Invalid(_(u'Too few values ({min} is the least)').format(min=min),
                                                get_literal_name(min), get_literal_name(length))
        self.min = min

        # `max` validator
        self.max_error = lambda length: Invalid(_(u'Too many values ({max} is the most)').format(max=max),
                                                get_literal_name(max), get_literal_name(length))
        self.max = max

        # Name
        self.name = _(u'Length({min}..{max})').format(
            min=_(u'') if min is None else min,
            max=_(u'') if max is None else max
        )

    def __call__(self, v):
        if not isinstance(v, collections.Sized):
            raise Invalid(_(u'Input is not a collection'), u'Collection', get_type_name(type(v)))

        length = len(v)

        # Validate
        if self.min is not None and length < self.min:
            raise self.min_error(length)
        if self.max is not None and length > self.max:
            raise self.max_error(length)

        # Ok
        return v


class Default(ValidatorBase):
    """ Initialize a value to a default if it's not provided.

    "Not provided" means `None`, so basically it replaces `None`s with the default:

    ```python
    from good import Schema, Any, Default

    schema = Schema(Any(
        # Accept ints
        int,
        # Replace `None` with 0
        Default(0)
    ))

    schema(1)  #-> 1
    schema(None)  #-> 0
    ```

    It raises [`Invalid`](#invalid) on all values except for `None` and `default`:

    ```python
    schema = Schema(Default(42))

    schema(42)  #-> 42
    schema(None)  #-> 42
    schema(1)
    #-> Invalid: Invalid value
    ```

    In addition, `Default` has special behavior with `Required` marker which is built into it:
    if a required key was not provided -- it's created with the default value:

    ```python
    from good import Schema, Default

    schema = Schema({
        # remember that keys are implicitly required
        'name': str,
        'age': Any(int, Default(0))
    })

    schema({'name': 'Alex'})  #-> {'name': 'Alex', 'age': 0}
    ```

    :param default: The default value to use
    """
    def __init__(self, default):
        self.default = default
        self.name = _(u'Default={default}').format(default=default)

    def __call__(self, v):
        if v is None or v is const.UNDEFINED or v == self.default:
            return self.default
        raise Invalid(_(u'Invalid value'), self.name, get_literal_name(v))


class Fallback(Default):
    """ Always returns the default value.

    Works like [`Default`](#default), but does not fail on any values.

    Typical usage is to terminate [`Any`](#any) chain in case nothing worked:

    ```python
    from good import Schema, Any, Fallback

    schema = Schema(Any(
        int,
        # All non-integer numbers are replaced with `None`
        Fallback(None)
    ))
    ```

    Like [`Default`](#default), it also works with mappings.

    Internally, `Default` and `Fallback` work by feeding the schema with a special [`Undefined`](good/schema/util.py) value:
    if the schema manages to return some value without errors -- then it has the named "default behavior",
    and this validator just leverages the feature.

    A "fallback value" may be provided manually, and will work absolutely the same
    (since value schema manages to succeed even though `Undefined` was given):

    ```python
    schema = Schema({
        'name': str,
        'age': Any(int, lambda v: 42)
    })
    ```

    :param default: The value that's always returned
    """

    def __call__(self, v):
        return self.default


__all__ = ('In', 'Length', 'Default', 'Fallback')
