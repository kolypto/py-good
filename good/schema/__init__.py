import six

from .compiler import CompiledSchema
from . import markers


class Schema(object):
    """ Validation schema.

    A schema is a Python structure where nodes are pattern-matched against the corresponding values.
    It leverages the full flexibility of Python, allowing you to match values, types, data sctructures and much more.

    When a schema is created, it's compiled into a callable function which does the validation, hence it does not need
    to analyze the schema every time.

    Once the Schema is defined, validation can be triggered by calling it:

    ```python
    from good import Schema

    schema = Schema({ 'a': str })
    # Test
    schema({ 'a': 'i am a valid string' })
    ```

    The following rules exist:

    1. **Literal**: plain value is validated with direct comparison (equality check):

        ```python
        Schema(1)(1)  #-> 1
        Schema(1)(2)  #-> Invalid: Invalid value: expected 1, got 2
        ```

    2. **Type**: type schema produces an `instanceof()` check on the input value:

        ```python
        Schema(int)(1)    #-> 1
        Schema(int)('1')
        #-> Invalid: Wrong type: expected Integer number, got Binary String
        ```

    3. **Callable**: is applied to the value and the result is used as the final value.
       Any errors raised by the callable are treated as validation errors.

       In addition, validators are allowed to transform a value to the required form.
       For instance, [`Coerce(int)`](#coerce) returns a callable which will convert input values into `int` or fail.

       ```python
       def CoerceInt(v):  # naive Coerce(int) implementation
           return int(v)

       Schema(CoerceInt)(1)    #-> 1
       Schema(CoerceInt)('1')  #-> 1
       Schema(CoerceInt)('a')
       #-> Invalid: ValueError: invalid literal for int(): expected CoerceInt(), got a
       ```

    4. **`Schema`**: a schema may contain sub-schemas:

        ```python
        sub_schema = Schema(int)
        schema = Schema([None, sub_schema])

        schema([None, 1, 2])  #-> [None, 1, 2]
        schema([None, '1'])  #-> Invalid: invalid value
        ```

        Since `Schema` is callable, validation transparently by just calling it :)

    Moreover, instances of the following types are converted to callables on the compilation phase:

    1. **Iterables** (`list`, `tuple`, `set`, custom iterables):

        Iterables are treated as a set of valid values,
        where each value in the input is compared against each value in the schema.

        In order for the input to be valid, it needs to have the same iterable type, and all of its
        values should have at least one matching value in the schema.

        ```python
        schema = Schema([1, 2, 3])  # List of valid values

        schema([1, 2, 2])  #-> [1, 2, 2]
        schema([1, 2, 4])  #-> Invalid: Invalid value @ [2]: expected List[1|2|3], got 4
        schema((1, 2, 2))  #-> Invalid: Wrong value type: expected List, got Tuple
        ```

        Each value within the iterable is a schema as well, and validation requires that
        each member of the input value matches *any* of the schemas.
        Thus, an iterable is a way to define *OR* validation rule for every member of the iterable:

        ```python
        Schema([ # All values should be
            # .. int ..
            int,
            # .. or a string, casted to int ..
            lambda v: int(v)
        ])([ 1, 2, '3' ])  #-> [ 1, 2, 3 ]
        ```

        This example works like this:

        1. Validate that the input value has the matching type: `list` in this case
        2. For every member of the list, test that there is a matching value in the schema.

            E.g. for value `1` -- `int` matches (immediate `instanceof()` check).
            However, for value `'3'` -- `int` fails, but the callable manages to do it with no errors,
            and transforms the value as well.

            Since lists are ordered, the first schema that didn't fail is used.

    2. **Mappings** (`dict`, custom mappings):

        Each key-value pair in the input mapping is validated against the corresponding schema pair:

        ```python
        Schema({
            'name': str,
            'age': lambda v: int(v)
        })({
            'name': 'Alex',
            'age': '18',
        })  #-> {'name': 'Alex', 'age': 18}
        ```

        When validating, *both* keys and values are schemas, which allows to use nested schemas and interesting validation rules.
        For instance, let's use [`In`](#in) validator to match certain keys:

        ```python
        from good import Schema, In

        Schema({
            # These two keys should have integer values
            In('age', 'height'): int,
            # All other keys should have string values
            str: str,
        })({
            'age': 18,
            'height': 173,
            'name': 'Alex',
        })
        ```

        This works like this:

        1. Test that the input has a matching type (`dict`)
        2. For each key in the input mapping, matching keys are selected from the schema
        3. Validate input values with the corresponding value in the schema.

        In addition, certain keys can be marked as [`Required`](#required) and [`Optional`](#optional).
        The default behavior is to have all keys required, but this can be changed by providing
        `default_keys=Optional` argument to the Schema.

        Finally, a mapping does not allow any extra keys (keys not defined in the schema). To change this, provide
        `extra_keys=Allow` to the `Schema` constructor.

    These are just the basic rules, and for sure `Schema` can do much more than that!
    Additional logic is implemented through [Markers](#markers) and [Validators](#validators),
    which are described in the following chapters.

    ## Callables

    Finally, here are the things to consider when using custom callables for validation:

    * Throwing errors.

        If the callable throws [`Invalid`](#invalid) exception, it's used as is with all the rich info it provides.
        Schema is smart enough to fill into most of the arguments (see [`Invalid.enrich`](#invalidenrich)),
        so it's enough to use a custom message, and probably, set a human-friendly `expected` field.

        If the callable throws anything else (e.g. `ValueError`), these are wrapped into `Invalid`.
        Schema tries to do its best, but such messages will probably be cryptic for the user.
        Hence, always raise meaningful errors when creating custom validators.

    * Naming.

        If the provided callable does not specify `Invalid.expected` expected value,
        the `__name__` of the callable is be used instead.
        E.g. `def intify(v):pass` becomes `'intify()'` in reported errors.

        If a custom name is desired on the callable -- set the `name` attribute on the callable object.
        This works best with classes, however a function can accept `name` attribute as well.

    * Signals.

        A callable may decide that the value is soooo invalid that it should be dropped from the sanitized output.
        In this case, the callable should raise `good.schema.signals.RemoveValue`.

        This is used by the `Remove()` marker, but can be leveraged by other callables as well.

    ## Priorities

    Every schema type has a priority ([source](good/schema/util.py)),
    which define the sequence for matching keys in a mapping schema:

    1. Literals have highest priority
    2. Types has lower priorities than literals, hence schemas can define specific rules for individual keys,
        and then declare general rules by type-matching:

        ```python
        Schema({
            'name': str,  # Specific rule with a literal
            str: int,     # General rule with a type
        })
        ```
    3. Callables, iterables, mappings -- have lower priorities.

    In addition, [Markers](#markers) have individual priorities,
    which can be higher that literals ([`Remove()`](#remove) marker) or lower than callables ([`Extra`](#extra) marker).
    """

    compiled_schema_cls = CompiledSchema

    def __init__(self, schema, default_keys=markers.Required, extra_keys=markers.Reject):
        """ Creates a compiled `Schema` object from the given schema definition.

        Under the hood, it uses `SchemaCompiler`: see the [source](good/schema/compiler.py) if interested.

        :param schema: Schema definition
        :type schema: *
        :param default_keys: Default mapping keys behavior:
            a [`Marker`](#markers) class used as a default on mapping keys which are not Marker()ed with anything
        :type default_keys: type
        :param extra_keys: Default extra keys behavior: sub-schema, or a [`Marker`](#markers) class
        :type extra_keys: *
        :raises SchemaError: Schema compilation error
        """
        self._schema = self.compiled_schema_cls(schema, [], default_keys, extra_keys)

    def __repr__(self):
        return repr(self._schema)

    def __unicode__(self):
        return six.text_type(self._schema)

    if six.PY3:
        __str__ = __unicode__

    def __call__(self, value):
        """ Having a [`Schema`](#schema), user input can be validated by calling the Schema on the input value.

        When called, the Schema will return sanitized value, or raise exceptions.

        :param value: Input value to validate
        :return: Sanitized value
        :raises good.Invalid: Validation error on a single value. See [`Invalid`](#invalid).
        :raises good.MultipleInvalid: Validation error on multiple values. See [`MultipleInvalid`](#multipleinvalid).
        """
        return self._schema(value)
