import six

from .compiler import CompiledSchema
from . import markers


class Schema(object):
    """ Validation schema.

    A schema is a Python structure where nodes are pattern-matched against the corresponding values.

    Once the Schema is defined, validation can be triggered by calling it:

    ```python
    schema = Schema({ 'a': str })
    # Test
    schema({ 'a': 'i am a valid string' })
    ```

    The following rules exist:

    1. **Literal**: plain value is validated with direct comparison (equality check):

        ```python
        Schema(1)(1)  #-> 1
        Schema(1)(2)  #-> Incorrect value
        ```

    2. **Type**: is tested with `instanceof()` check:

        ```python
        Schema(int)(1)    #-> 1
        Schema(int)('1')  #-> Invalid: expecting an integer, string given
        ```

    3. **Callable**: is applied to the value and the result is used as the final value.
       Any errors raised by the callable are treated as validation errors.

       In addition, validators are allowed to mutate a value to a given form.
       For instance, [`Coerce(int)`](#coerce) returns a callable which will convert input values into `int` or fail.

       ```python
       CoerceInt = lambda v: int(v)  # naive Coerce(int) implementation

       Schema(CoerceInt)(1)    #-> 2
       Schema(CoerceInt)('1')  # Invalid: invalid value
       ```

       If the callable trows [`Invalid`](#invalid) exception, it's used as is.
       Other exceptions are wrapped into `Invalid` and re-raised (with poor explanations).

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
        where each value in the input is compared against the given set of valid values.

        In addition, the input iterable must have the given type:

        ```python
        schema = Schema([1, 2, 3])

        schema([1, 2, 2])  #-> [1]
        schema([1, 2, 4])  #-> Invalid: invalid list value @ [2]
        schema((1, 2, 2))  #-> Invalid: expecting a list, tuple given
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

        Since lists are ordered, the first schema that didn't fail is used.

        E.g. for value `1` -- `int` matches (immediate `instanceof()` check). However, for value `'3'` -- `int` fails,
        but the callable manages to do it with no errors.

    2. **Mappings** (`dict`, custom mappings):

        Each key-value pair in the input mapping is validated against the corresponding schema pair:

        ```python
        Schema({
            'name': str,
            'age': lambda v: int(v)
        })({
            'name':  'Alex',
            'age': '18',
        })  #-> {'name': 'Alex', 'age': 18}
        ```

        When validating, *both* keys and values are schemas, which allows to use nested schemas and interesting validation rules.
        For instance, let's use [`In`](#in) validator to match certain keys:

        ```python
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
        `extra_keys=Anything` to the `Schema` constructor.

    These are just the basic rules, and for sure `Schema` can do much more than that!
    Additional logic is implemented through [Markers](#markers) and [Validators](#validators),
    which are described in the next chapters.
    """

    compiled_schema_cls = CompiledSchema

    def __init__(self, schema, default_keys=markers.Required, extra_keys=markers.Reject):
        """ Create a `Schema` object from the given schema.

        :param schema: Schema to use for validation
        :param default_keys: Default dictionary keys behavior (a Marker class)
        :type default_keys: type
        :param extra_keys: Default extra keys behavior (schema, or a Marker class)
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
        """ Validate the given input value against the schema

        :param value: Input value to validate
        :return: Sanitized value
        :raises good.Invalid: Validation error on a single value
        :raises good.MultipleInvalid: Validation error on multiple values
        """
        return self._schema(value)
