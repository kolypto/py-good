""" A *Marker* is a proxy class which wraps some schema.

Immediately, the example is:

```python
from good import Schema, Required

Schema({
    'name': str,  # required key
    Optional('age'): int,  # optional key
}, default_keys=Required)
```

This way, keys marked with `Required()` will report errors if no value if provided.

Typically, a marker "decorates" a mapping key, but some of them can be "standalone":

```python
from good import Schema, Extra
Schema({
    'name': str,
    Extra: int  # allow any keys, provided their values are integer
})
```

Each marker can have it's own unique behavior since nothing is hardcoded into the core [`Schema`](#schema).
Keep on reading to learn how markers perform.
"""


import six
from .signals import RemoveValue
from .errors import Invalid, MultipleInvalid
from .util import const, get_type_name, get_literal_name


class Marker(object):
    """ A Marker is a class that decorates a mapping key.

    Its compilation goes in 3 phases:

    1. Marker.key is set by the user: `Required('name')`
    2. Marker.key is compiled into a schema, and notified with `Marker.on_compiled(name, key_schema)`
    3. Marker receives a value schema, through `Marker.on_compiled(value_schema=value_schema)`

    Note that if a marker is used as a mapping key, its `key_schema` is compiled as a matcher for performance.

    When CompiledSchema performs matching, it collects input values that match the marker
    (using `priority` to decide which of the markers will actually get the duck)
    and then calls execute() on the Marker so it can implement its logic.

    Note that `execute()` is always called, regardless of whether the marker has matched anything:
    this gives markers a chance to modify the input to its taste.
    This opens the possibilities of implementing custom markers which validate the whole schema!

    Finally, note that a marker does not necessarily decorate something: it can be used as a class:

    ```python
    Schema({
        'name': str,
        Extra: Reject
    })
    ```

    In this case, a Marker class is automatically instantiated
    with an identity function (which matches any value): `Extra(lambda x: x)`.
    """

    #: Marker priority
    #: This defines matching order for mapping keys
    priority = 0

    #: The default marker error message
    #: Stored here just for convenience
    error_message = None

    def __init__(self, key):
        #: The original key
        self.key = key
        #: Human-readable marker representation
        self.name = None
        #: CompiledSchema for the key
        self.key_schema = None
        #: CompiledSchema for value (if the Marker was used as a key in a mapping)
        self.value_schema = None

        #: Whether the marker is used as a mapping key
        self.as_mapping_key = False

    def on_compiled(self, name=None, key_schema=None, value_schema=None, as_mapping_key=None):
        """ When CompiledSchema compiles this marker, it sets informational values onto it.

        Note that arguments may be provided in two incomplete sets,
        e.g. (name, key_schema, None) and then (None, None, value_schema).
        Thus, all assignments must be handled individually.

        It is possible that a marker may have no `value_schema` at all:
        e.g. in the case of { Extra: Reject } -- `Reject` will have no value schema,
        but `Extra` will have compiled `Reject` as the value.

        :param key_schema: Compiled key schema
        :type key_schema: CompiledSchema|None
        :param value_schema: Compiled value schema
        :type value_schema: CompiledSchema|None
        :param name: Human-friendly marker name
        :type name: unicode|None
        :param as_mapping_key: Whether it's used as a mapping key?
        :type as_mapping_key: bool|None
        :rtype: Marker
        """
        if self.name is None:
            self.name = name
        if self.key_schema is None:
            self.key_schema = key_schema
        if self.value_schema is None:
            self.value_schema = value_schema
        if as_mapping_key:
            self.as_mapping_key = True
        return self

    def __repr__(self):
        return '{cls}({0})'.format(
            self.name or self.key,
            cls=type(self).__name__)

    #region Marker is a Proxy

    def __hash__(self):
        return hash(self.key)

    def __eq__(self, other):
        # Marker equality comparison:
        #  key == key | key == Marker.key | key is Marker
        return self.key == (other.key if isinstance(other, Marker) else other) or other is type(self)

    def __str__(self):
        return six.binary_type(self.key)

    def __unicode__(self):
        return get_literal_name(self.key)

    if six.PY3:
        __bytes__, __str__ = __str__, __unicode__

    #endregion

    def __call__(self, v):
        """ Validate a key using this Marker's schema """
        return self.key_schema(v)

    def execute(self, d, matches):
        """ Execute the marker against the the matching values from the input.

        Note that `execute()` is called precisely once, and even if there are no matches for the marker.

        :param d: The original user input
        :type d: dict
        :param matches: List of (input-key, sanitized-input-key, input-value) triples that matched the given marker
        :type matches: list[tuple]
        :returns: The list of matches, potentially modified
        :rtype: list[tuple]
        :raises: Invalid|MultipleInvalid
        """
        return matches  # No-op by default


class Required(Marker):
    """ `Required(key)` is used to decorate mapping keys and hence specify that these keys must always be present in
    the input mapping.

    When compiled, [`Schema`](#schema) uses `default_keys` as the default marker:

    ```python
    from good import Schema, Required

    schema = Schema({
        'name': str,
        'age': int
    }, default_keys=Required)  # wrap with Required() by default

    schema({'name': 'Mark'})
    #-> Invalid: Required key not provided @ ['age']: expected age, got -none-
    ```

    Remember that mapping keys are schemas as well, and `Require` will expect to always have a match:

    ```python
    schema = Schema({
        Required(str): int,
    })

    schema({})  # no `str` keys provided
    #-> Invalid: Required key not provided: expected String, got -none-
    ```

    In addition, the `Required` marker has special behavior with [`Default`](#default) that allows to set the key
    to a default value if the key was not provided. More details in the docs for [`Default`](#default).
    """
    priority = 0
    error_message = _(u'Required key not provided')

    def execute(self, d, matches):
        # If a Required() key is present -- it expects to ALWAYS have one or more matches

        # When Required() has no matches...
        if not matches:
            # Last chance: value_schema supports Undefined, and the key is a literal
            if self.value_schema.supports_undefined:
                # Schema supports `Undefined`, then use it!
                v = self.value_schema(const.UNDEFINED)
                matches.append((self.key_schema.schema, self.key_schema.schema, v))
                return matches
            else:
                # Invalid
                path = [self.key] if self.key_schema.compiled_type == const.COMPILED_TYPE.LITERAL else []
                raise Invalid(self.error_message, self.name, _(u'-none-'), path)
        return matches


class Optional(Marker):
    """ `Optional(key)` is controversial to [`Required(key)`](#required): specified that the mapping key is not required.

    This only has meaning when a [`Schema`](#schema) has `default_keys=Required`:
    then, it decorates all keys with `Required()`, unless a key is already decorated with some Marker.
    `Optional()` steps in: those keys are already decorated and hence are not wrapped with `Required()`.

    So, it's only used to prevent `Schema` from putting `Required()` on a key.
    In all other senses, it has absolutely no special behavior.

    As a result, optional key can be missing, but if it was provided -- its value must match the value schema.

    Example: use as `default_keys`:

    ```python
    schema = Schema({
        'name': str,
        'age': int
    }, default_keys=Optional)  # Make all keys optional by default

    schema({})  #-> {} -- okay
    schema({'name': None})
    #->  Invalid: Wrong type @ ['name']: expected String, got None
    ```

    Example: use to mark specific keys are not required:

    ```python
    schema = Schema({
        'name': str,
        Optional(str): int  # key is optional
    })

    schema({'name': 'Mark'})  # valid
    schema({'name': 'Mark', 'age': 10})  # valid
    schema({'name': 'Mark', 'age': 'X'})
    #-> Invalid: Wrong type @ ['age']: expected Integer number, got Binary String
    ```
    """

    priority = 0

    pass  # no-op


class Remove(Marker):
    """ `Remove(key)` marker is used to declare that the key, if encountered,
    should be removed, without validating the value.

    `Remove` has highest priority, so it operates before everything else in the schema.

    Example:

    ```python
    schema = Schema({
        Remove('name'): str, # `str` does not mean anything since the key is removed anyway
        'age': int
    })

    schema({'name': 111, 'age': 18})  #-> {'age': 18}
    ```

    However, it's more natural to use `Remove()` on values.
    Remember that in this case `'name'` will become [`Required()`](#required),
    if not decorated with [`Optional()`](#optional):

    ```python
    schema = Schema({
        Optional('name'): Remove
    })

    schema({'name': 111, 'age': 18})  #-> {'age': 18}
    ```

    **Bonus**: `Remove()` can be used in iterables as well:

    ```python
    schema = Schema([str, Remove(int)])
    schema(['a', 'b', 1, 2])  #-> ['a', 'b']
    ```
    """

    priority = 1000  # We always want to remove keys prior to any other actions

    def execute(self, d, matches):
        # Remove all matching keys from the input
        for k, sanitized_k, v in matches:
            d.pop(k)

        # Clean the list of matches so further processing does not assign them again
        return []

    def __call__(self, v):
        if not self.as_mapping_key:
            # When used on a value -- drop it
            raise RemoveValue()
        return super(Remove, self).__call__(v)


class Reject(Marker):
    """ `Reject(key)` marker is used to report [`Invalid`](#invalid) errors every time is matches something in the input.

    It has lower priority than most of other schemas, so rejection will only happen
    if no other schemas has matched this value.

    Example:

    ```python
    schema = Schema({
        Reject('name'): None,  # Reject by key
        Optional('age'): Msg(Reject, u"Field is not supported anymore"), # alternative form
    })

    schema({'name': 111})
    #-> Invalid: Field is not supported anymore @ ['name']: expected -none-, got name
    ```
    """

    priority = -50
    error_message = _(u'Value rejected')

    def __call__(self, v):
        if not self.as_mapping_key:
            # When used on a value -- complain
            raise Invalid(self.error_message, _(u'-none-'), get_literal_name(v), validator=self)
        return super(Reject, self).__call__(v)

    def execute(self, d, matches):
        # Complain on all values it gets
        if matches:
            errors = []
            for k, sanitized_k, v in matches:
                errors.append(Invalid(self.error_message, _(u'-none-'), get_literal_name(k), [k]))
            raise MultipleInvalid.if_multiple(errors)
        return matches


class Allow(Marker):
    """ `Allow(key)` is a no-op marker that never complains on anything.

    Designed to be used with [`Extra`](#extra).
    """
    priority = 0

    pass  # no-op


class Extra(Marker):
    """ `Extra` is a catch-all marker to define the behavior for mapping keys not defined in the schema.

    It has the lowest priority, and delegates its function to its value, which can be a schema, or another marker.

    Given without argument, it's compiled with an identity function `lambda x:x` which is a catch-all:
    it matches any value. Together with lowest priority, `Extra` will only catch values which did not match anything else.

    Every mapping has an `Extra` implicitly, and `extra_keys` argument controls the default behavior.

    Example with `Extra: <schema>`:

    ```python
    schema = Schema({
        'name': str,
        Extra: int  # this will allow extra keys provided they're int
    })

    schema({'name': 'Alex', 'age': 18'})  #-> ok
    schema({'name': 'Alex', 'age': 'X'})
    #-> Invalid: Wrong type @ ['age']: expected Integer number, got Binary String
    ```

    Example with `Extra: Reject`: reject all extra values:

    ```python
    schema = Schema({
        'name': str,
        Extra: Reject
    })

    schema({'name': 'Alex', 'age': 'X'})
    #-> Invalid: Extra keys not allowed @ ['age']: expected -none-, got age
    ```

    Example with `Extra: Remove`: silently discard all extra values:

    ```python
    schema = Schema({'name': str}, extra_keys=Remove)
    schema({'name': 'Alex', 'age': 'X'})  #-> {'name': 'Alex'}
    ```

    Example with `Extra: Allow`: allow any extra values:

    ```python
    schema = Schema({'name': str}, extra_keys=Allow)
    schema({'name': 'Alex', 'age': 'X'})  #-> {'name': 'Alex', 'age': 'X'}
    ```
    """
    priority = -1000  # Extra should match last

    error_message = _(u'Extra keys not allowed')

    def on_compiled(self, name=None, key_schema=None, value_schema=None, as_mapping_key=None):
        # Special case
        # When { Extra: Reject }, use a customized error message
        if value_schema and isinstance(value_schema.compiled, Reject):
            value_schema.compiled.error_message = self.error_message
        return super(Extra, self).on_compiled(name, key_schema, value_schema, as_mapping_key)

    def execute(self, d, matches):
        # Delegate the decision to the value.

        # If the value is a marker -- call execute() on it
        # This is for the cases when `Extra` is mapped to a marker
        if isinstance(self.value_schema.compiled, Marker):
            return self.value_schema.compiled.execute(d, matches)

        # Otherwise, it's a schema, which must be called on every value to validate it.
        # However, CompiledSchema does this anyway at the next step, so doing nothing here
        return matches


class Entire(Optional):
    """ `Entire` is a convenience marker that validates the entire mapping using validators provided as a value.

    It has absolutely lowest priority, lower than `Extra`, hence it never matches any keys, but is still executed to
    validate the mapping itself.

    This opens the possibilities to define rules on multiple fields.
    This feature is leveraged by the [`Inclusive`](#inclusive) and [`Exclusive`](#exclusive) group validators.

    For example, let's require the mapping to have no more than 3 keys:

    ```python
    from good import Schema, Entire

    def maxkeys(n):
        # Return a validator function
        def validator(d):
            # `d` is the dictionary.
            # Validate it
            assert len(d) <= 3, 'Dict size should be <= 3'
            # Return the value since all callable schemas should do that
            return d
        return validator

    schema = Schema({
        str: int,
        Entire: maxkeys(3)
    })
    ```

    In this example, `Entire` is executed for every input dictionary, and magically calls the schema it's mapped to.
    The `maxkeys(n)` schema is a validator that complains on the dictionary size if it's too huge.
    `Schema` catches the `AssertionError` thrown by it and converts it to [`Invalid`](#invalid).

    Note that the schema this marker is mapped to can't replace the mapping object, but it can mutate the given mapping.
    """

    priority = -2000  # Should never match anything

    def execute(self, d, matches):
        # Ignore `matches`, since it's always empty.
        # Instead, pass the mapping `d` to the schema it's mapped to: `value_schema`
        try:
            self.value_schema(d)
        except Invalid as e:
            e.enrich(
                expected=self.value_schema.name,
                provided=get_type_name(type(d)),
                validator=self.value_schema.schema
            )
            raise

        # Still return the same `matches` list
        return matches


__all__ = ('Required', 'Optional', 'Remove', 'Reject', 'Allow', 'Extra', 'Entire')
