from .. import Schema, Invalid
from ._base import ValidatorBase


class Any(ValidatorBase):
    """ Try the provided schemas in order and use the first one that succeeds.

    This is the *OR* condition predicate: any of the schemas should match.

    ```python
    from good import Schema, Any

    schema = Schema(Any(
        # allowed string constants
        'true', 'false',
        # otherwise coerce as a bool
        lambda v: 'true' if v else 'false'
    ))
    schema('true')  #-> 'true'
    schema(0)  #-> 'false'
    ```

    :param schemas: List of schemas to try.
    """

    def __init__(self, *schemas):
        # Compile
        self.compiled = tuple(Schema(schema) for schema in schemas)

        # Name
        self.name = _(u'Any({})').format(_(u'|'.join(x.name for x in self.compiled)))

    def __call__(self, v):
        # Try schemas in order
        for schema in self.compiled:
            try:
                return schema(v)
            except Invalid:
                pass

        # Nothing worked
        raise Invalid(_(u'Invalid value'), self.name, validator=self)


class All(ValidatorBase):
    """ Value must pass all validators wrapped with `All()` predicate.

    This is the *AND* condition predicate: all of the schemas should match in order,
    which is in fact a composition of validators: `All(f,g)(value) = g(f(value))`.

    ```python
    from good import Schema, All, Range

    schema = Schema(All(
        # Must be an integer ..
        int,
        # .. and in the allowed range
        Range(0, 10)
    ))

    schema(1)  #-> 1
    schema(99)
    #-> Invalid: Not in range: expected 0..10, got 99
    ```

    :param schemas: List of schemas to apply.
    """

    def __init__(self, *schemas):
        # Compile
        self.compiled = tuple(Schema(schema) for schema in schemas)

        # Name
        self.name = _(u'All({})').format(_(u' & '.join(x.name for x in self.compiled)))

    def __call__(self, v):
        # Apply schemas in order and transform the value iteratively
        for schema in self.compiled:
            # Any failing schema will immediately throw an error
            v = schema(v)
        # Finished
        return v


class Neither(ValidatorBase):
    """ Value must not match any of the schemas.

    This is the *NOT* condition predicate: a value is considered valid if each schema has raised an error.

    ```python
    from good import Schema, Neither

    schema = Schema(All(
        # Integer
        int,
        # But not zero
        Neither(0)
    ))

    schema(1)  #-> 1
    schema(0)
    #-> Invalid:
    ```

    :param schemas: List of schemas to check against.
    """

    def __init__(self, *schemas):
        # Compile
        self.compiled = tuple(Schema(schema) for schema in schemas)

        # Name
        self.name = _(u'Neither({})').format(_(u','.join(x.name for x in self.compiled)))

    def __call__(self, v):
        # Try schemas in order
        for schema in self.compiled:
            try:
                schema(v)
            except Invalid:
                pass  # error is okay
            else:
                raise Invalid(_(u'Value not allowed'), _(u'Not({})').format(schema.name), validator=schema.compiled.schema)

        # All ok
        return v


__all__ = ('Any', 'All', 'Neither')
