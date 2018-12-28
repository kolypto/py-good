from .. import Schema, Invalid, MultipleInvalid, Required, Optional
from .base import ValidatorBase
from ..schema.util import get_literal_name, const, commajoin_as_strings


class Maybe(ValidatorBase):
    """ Validate the the value either matches the given schema or is None.

    This supports *nullable* values and gives them a good representation.

    ```python
    from good import Schema, Maybe, Email

    schema = Schema(Maybe(Email))

    schema(None)  #-> None
    schema('user@example.com')  #-> 'user@example.com'
    scheam('blahblah')
    #-> Invalid: Wrong E-Mail: expected E-Mail?, got blahblah
    ```

    Note that it also have the [`Default`-like behavior](#default)
    that initializes the missing [`Required()`](#required) keys:

    ```python
    schema = Schema({
        'email': Maybe(Email)
    })

    schema({})  #-> {'email': None}
    ```

    :param schema: Schema for a provided value
    :type schema: object
    :param none: Empty value literal
    :type none: object
    """

    def __init__(self, schema, none=None):
        # Flatten (for the sake of friendlier error messages)
        if type(schema) == Maybe and schema.none == none:
            schema = schema.schema

        # Init
        self.schema = Schema(schema)
        self.none = none
        self.name = _(u'{schema}?').format(schema=self.schema.name)

    def __call__(self, v):
        # Empty & Default behavior
        if v == self.none or v is const.UNDEFINED:
            return self.none

        # Validate
        try:
            return self.schema(v)
        except Invalid as ee:
            # Add the "optional" mark "...?"
            for e in ee:
                e.expected += _(u'?')
            # Reraise
            raise


class Any(ValidatorBase):
    """ Try the provided schemas in order and use the first one that succeeds.

    This is the *OR* condition predicate: any of the schemas should match.
    [`Invalid`](#invalid) error is reported if neither of the schemas has matched.

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
        # Flatten (for the sake of friendlier error messages)
        schemas = sum(tuple(s.compiled if type(s) == Any else (s,)
                            for s in schemas), ())

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
        raise Invalid(_(u'Invalid value'))


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
        # Flatten (for the sake of friendlier error messages)
        schemas = sum(tuple(s.compiled if type(s) == All else (s,)
                            for s in schemas), ())

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
    from good import Schema, All, Neither

    schema = Schema(All(
        # Integer
        int,
        # But not zero
        Neither(0)
    ))

    schema(1)  #-> 1
    schema(0)
    #-> Invalid: Value not allowed: expected Not(0), got 0
    ```

    :param schemas: List of schemas to check against.
    """

    def __init__(self, *schemas):
        # Flatten (for the sake of friendlier error messages)
        schemas = sum(tuple(s.compiled if type(s) == Neither else (s,)
                            for s in schemas), ())

        # Compile
        self.compiled = tuple(Schema(schema) for schema in schemas)

        # Name
        self.name = (
            _(u'Not({})')
            if len(self.compiled) == 1 else
            _(u'None({})')
        ).format(_(u','.join(x.name for x in self.compiled)))

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


class Inclusive(ValidatorBase):
    """ `Inclusive` validates the defined inclusive group of mapping keys:
    if any of them was provided -- then all of them become required.

    This exists to support "sub-structures" within the mapping which only make sense if specified together.
    Since this validator works on the entire mapping, the best way is to use it together with the [`Entire`](#entire)
    marker:

    ```python
    from good import Schema, Entire, Inclusive

    schema = Schema({
        # Fields for all files
        'name': str,
        # Fields for images only
        Optional('width'): int,
        Optional('height'): int,
        # Now put a validator on the entire mapping
        Entire: Inclusive('width', 'height')
    })

    schema({'name': 'monica.jpg'})  #-> ok
    schema({'name': 'monica.jpg', 'width': 800, 'height': 600})  #-> ok
    schema({'name': 'monica.jpg', 'width': 800})
    #-> Invalid: Required key not provided: expected height, got -none-
    ```

    Note that `Inclusive` only supports literals.

    :param keys: List of mutually inclusive keys (literals).
    """

    def __init__(self, *keys):
        self.keys = set(keys)
        self.name = _(u'Inclusive({})').format(commajoin_as_strings(keys))

    def __call__(self, d):
        # Check which keys are missing in the input mapping
        missing_keys = self.keys - set(d)

        # If none of the keys is specified in the input -- that's ok
        if missing_keys == self.keys:
            return d

        # If all keys were provided -- that's okay as well
        if not missing_keys:
            return d

        # Otherwise, we complain on every single key
        raise MultipleInvalid.if_multiple([
            Invalid(_(u'Required key not provided'), get_literal_name(key), _(u'-none-'), [key])
            for key in missing_keys
        ])


class Exclusive(ValidatorBase):
    """ `Exclusive` validates the defined exclusive group of mapping keys:
    if any of them was provided -- then none of the remaining keys can be used.

    This supports "sub-structures" with choice: if the user chooses a field from one of them --
    then he cannot use others.
    It works on the entire mapping and hence best to use with the [`Entire`](#entire) marker.

    By default, `Exclusive` requires the user to choose one of the options,
    but this can be overridden with [`Optional`](#optional) marker class given as an argument:

    ```python
    from good import Exclusive, Required, Optional

    # Requires either of them
    Exclusive('login', 'password')
    Exclusive(Required, 'login', 'password')  # the default

    # Requires either of them, or none
    Exclusive(Optional, 'login', 'password')
    ```

    Let's demonstrate with the API that supports multiple types of authentication,
    but requires the user to choose just one:

    ```python
    from good import Schema, Entire, Exclusive

    schema = Schema({
        # Authentication types: login+password | email+password
        Optional('login'): str,
        Optional('email'): str,
        'password': str,
        # Now put a validator on the entire mapping
        # that forces the user to choose
        Entire: Msg(  # also override the message
            Exclusive('login', 'email'),
            u'Choose one'
        )
    })

    schema({'login': 'kolypto', 'password': 'qwerty'})  #-> ok
    schema({'email': 'kolypto', 'password': 'qwerty'})  #-> ok
    schema({'login': 'a', 'email': 'b', 'password': 'c'})
    #-> MultipleInvalid:
    #->     Invalid: Choose one @ [login]: expected login|email, got login
    #->     Invalid: Choose one @ [email]: expected login|email, got email
    ```

    Note that `Exclusive` only supports literals.

    :param keys: List of mutually exclusive keys (literals).

        Can contain [`Required`](#required) or [`Optional`](#optional) marker classes,
        which defines the behavior when no keys are provided. Default is `Required`.
    """

    def __init__(self, *keys):
        keys = set(keys)

        # Required or Optional?
        try:
            # Optional
            keys.remove(Optional)
            self.require_mode = False
        except KeyError:
            # Required
            keys.discard(Required)
            self.require_mode = True

        # Name
        self.keys = set(keys)
        self.name = _(u'Exclusive({})').format(commajoin_as_strings(sorted(self.keys)))

    def __call__(self, d):
        # Check which of the keys are provided
        provided_keys = self.keys & set(d)

        # None used
        if not provided_keys:
            if self.require_mode:
                # Required mode: fail
                raise Invalid(_(u'Choose one of the options'), provided=_(u'-none-'))
            else:
                # Optional mode: ok
                return d

        # One used: ok
        if len(provided_keys) == 1:
            return d

        # Multiple used
        raise Invalid(_(u'Choose one of the options, not multiple'), provided=commajoin_as_strings(sorted(provided_keys)))



__all__ = ('Maybe', 'Any', 'All', 'Neither', 'Inclusive', 'Exclusive')
