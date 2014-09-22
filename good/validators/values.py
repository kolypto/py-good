import collections

from .base import ValidatorBase
from .. import Invalid
from ..schema.util import get_literal_name, get_type_name, get_primitive_name, const

# Try to load Enum type (if supported)
try:
    from enum import EnumMeta as _EnumMeta
except ImportError:
    _EnumMeta = None


class In(ValidatorBase):
    """ Validate that a value is in a collection.

    This is a plain simple `value in container` check, where `container` is a collection of literals.

    In contrast to [`Any`](#any), it does not compile its arguments into schemas,
    and hence achieves better performance.

    ```python
    from good import Schema, In

    schema = Schema(In({1, 2, 3}))

    schema(1)  #-> 1
    schema(99)
    #-> Invalid: Unsupported value: expected In(1,2,3), got 99
    ```

    The same example will work with [`Any`](#any), but slower :-)

    :param container: Collection of allowed values.

        In addition to naive tuple/list/set/dict, this can be any object that supports `in` operation.
    :type container: collections.Container
    """

    def __init__(self, container):
        assert isinstance(container, collections.Container), '`container` must support `in` operation'
        self.container = container

        # Name
        if isinstance(self.container, Map):
            self.name = self.container.name  # Inherit name
        else:
            # Format
            if isinstance(self.container, collections.Iterable):
                cs = _(u',').join(map(get_literal_name, self.container))
            else:
                cs = get_primitive_name(self.container)
            self.name = _(u'In({container})').format(container=cs)

    def __call__(self, v):
        # Test
        if v not in self.container:
            raise Invalid(_(u'Unsupported value'))

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
    schema([1,2,3,4])
    #-> Invalid: Too long (3 is the most): expected Length(..3), got 4
    ```

    :param min: Minimal allowed length, or `None` to impose no limits.
    :type min: int|None
    :param max: Maximal allowed length, or `None` to impose no limits.
    :type max: int|None
    """

    def __init__(self, min=None, max=None):
        # `min` validator
        self.min_error = lambda length: Invalid(_(u'Too short ({min} is the least)').format(min=min),
                                                get_literal_name(min), get_literal_name(length))
        self.min = min

        # `max` validator
        self.max_error = lambda length: Invalid(_(u'Too long ({max} is the most)').format(max=max),
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
        raise Invalid(_(u'Invalid value'))


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


class Map(ValidatorBase):
    """ Convert Enumerations that map names to values.

    Supports three kinds of enumerations:

    1. Mapping.

        Provided a mapping from names to values,
        converts the input to values by mapping key:

        ```python
        from good import Schema, Map
        schema = Schema(Map({
            'RED': 0xFF0000,
            'GREEN': 0x00FF00,
            'BLUE': 0x0000FF
        }))

        schema('RED')  #-> 0xFF0000
        schema('BLACK')
        #-> Invalid: Unsupported value: expected Constant, provided BLACK
        ```

    2. Class.

        Provided a class with attributes (names) initialized with values,
        converts the input to values matching by attribute name:

        ```python
        class Colors:
            RED = 0xFF0000
            GREEN = 0x00FF00
            BLUE = 0x0000FF

        schema = Schema(Map(Colors))

        schema('RED')  #-> 0xFF0000
        schema('BLACK')
        #-> Invalid: Unsupported value: expected Colors, provided BLACK
        ```

        Note that all attributes of the class are used, except for protected (`_name`) and callables.

    3. Enum.

        Supports [Python 3.4 Enums](https://docs.python.org/3/library/enum.html)
        and the backported [enum34](https://pypi.python.org/pypi/enum34).

        Provided an enumeration, converts the input to values by name.
        In addition, enumeration value can pass through safely:

        ```python
        from enum import Enum

        class Colors(Enum):
            RED = 0xFF0000
            GREEN = 0x00FF00
            BLUE = 0x0000FF

        schema = Schema(Map(Colors))
        schema('RED')  #-> <Colors.RED: 0xFF0000>
        schema('BLACK')
        #-> Invalid: Unsupported value: expected Colors, provided BLACK
        ```

        Note that in `mode=Map.VAL` it works precisely like `Schema(Enum)`.

    In addition to the "straignt" mode (lookup by key), it supports reverse matching:

    * When `mode=Map.KEY`, does only forward matching (by key) -- the default
    * When `mode=Map.VAL`, does only reverse matching (by value)
    * When `mode=Map.BOTH`, does bidirectional matching (by key first, then by value)

    Another neat feature is that `Map` supports `in` containment checks,
    which works great together with [`In`](#in): `In(Map(enum-value))` will test if a value is convertible, but won't
    actually do the convertion.

    ```python
    from good import Schema, Map, In

    schema = Schema(In(Map(Colors)))

    schema('RED') #-> 'RED'
    schema('BLACK')
    #-> Invalid: Unsupported value, expected Colors, got BLACK
    ```

    :param enum: Enumeration: dict, object, of Enum
    :type enum: dict|type|enum.EnumMeta
    :param mode: Matching mode: one of Map.KEY, Map.VAL, Map.BOTH
    """

    KEY = 1
    VAL = 2
    BOTH = KEY|VAL

    def __init__(self, enum, mode=KEY):
        assert mode in (self.KEY, self.VAL, self.BOTH), 'Mode must be: KEY|VAL|BOTH'

        self.enum = None
        self.mode = mode
        self.name = _(u'Constant')

        self.mapping = None
        self.mapping_rev = None

        self.lookup = None
        self.rlookup = None

        # Enum (if supported)
        if _EnumMeta is not None and isinstance(enum, _EnumMeta):
            # Enum
            self.enum = enum
            self.name = enum.__name__

            # Lookups
            if self.mode & self.KEY:
                self.lookup = lambda k: k if isinstance(k, enum) else self.enum[k]
            if self.mode & self.VAL:
                self.rlookup = lambda v: self.enum(v)
        else:
            # Object?
            if not isinstance(enum, collections.Mapping):
                # Convert scalar public attributes to mapping
                self.name = enum.__name__
                enum = {k: v
                        for k, v in vars(enum).items()
                        if not (k.startswith('_') or callable(v))}

            # Mapping
            self.mapping = enum

            # Lookups
            if self.mode & self.KEY:
                self.lookup = lambda k: self.mapping[k]
            if self.mode & self.VAL:
                self.mapping_rev = {v: k for k, v in self.mapping.items()}
                self.rlookup = lambda v: self.mapping_rev[v]

    def __getitem__(self, v):
        # Try both forward and reverse lookups
        for lookup in (self.lookup, self.rlookup):
            # If enabled
            if lookup:
                try:
                    # Try to get the mapped value
                    return lookup(v)
                except Exception as e:
                    # Ok, try again
                    pass

        # Nothing worked
        raise KeyError(v)

    def __contains__(self, v):
        try:
            self[v]
        except KeyError:
            return False
        else:
            return True

    def __call__(self, v):
        try:
            return self[v]
        except KeyError:
            raise Invalid(_(u'Unsupported value'))


__all__ = ('In', 'Length', 'Default', 'Fallback', 'Map')
