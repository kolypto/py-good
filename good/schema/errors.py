"""
Source: [good/schema/errors.py](good/schema/errors.py)

When [validating user input](#validating), [`Schema`](#schema) collects all errors and throws these
after the whole input value is validated. This makes sure that you can report *all* errors at once.

With simple schemas, like `Schema(int)`, only a single error is available: e.g. wrong value type.
In this case, [`Invalid`](#invalid) error is raised.

However, with complex schemas with embedded structures and such, multiple errors can occur:
then [`MultipleInvalid`] is reported.

All errors are available right at the top-level:

```python
from good import Invalid, MultipleInvalid
```
"""

import six


class BaseError(Exception):
    """ Base validation exception """


class SchemaError(BaseError):
    """ Schema error (e.g. malformed) """


class Invalid(BaseError):
    """ Validation error for a single value.

    This exception is guaranteed to contain text values which are meaningful for the user.

    :param message: Validation error message.
    :type message: unicode
    :param expected: Expected value: info about the value the validator was expecting.

        If validator does not specify it -- the name of the validator is used.

    :type expected: unicode
    :param provided: Provided value: info about the value that was actually supplied by the user

        If validator does not specify it -- the input value is typecasted to string and stored here.

    :param provided: unicode
    :param path: Path to the error value.

        E.g. if an invalid value was encountered at ['a'].b[1], then path=['a', 'b', 1].

    :type path: list
    :param validator: The validator that has failed: a schema item
    :type validator: *
    :param info: Custom values that might be provided by the validator. No built-in validator uses this.
    :type info: dict
    """

    def __init__(self, message, expected=None, provided=None, path=None, validator=None, **info):
        super(Invalid, self).__init__(message, expected, provided, path, validator)
        self.message = message
        self.expected = expected
        self.provided = provided
        self.path = path or []
        self.validator = validator
        self.info = info

    def __iter__(self):
        """ Iterate over container errors.

        For `Invalid`, just yields self, however for `MultipleInvalid` it yields every contained errors.

        Hence, it allows to iterate all errors without checking whether it's a multi-error or not.
        """
        yield self

    def __repr__(self):
        return '{cls}({0.message!r}, ' \
               'expected={0.expected!r}, ' \
               'provided={0.provided!r}, ' \
               'path={0.path!r}, ' \
               'validator={0.validator!r}, ' \
               'info={0.info!r})' \
            .format(self, cls=type(self).__name__,)

    def __str__(self):
        return six.text_type(self).encode('utf8')

    def __unicode__(self):
        return u'{message}: expected {0.expected}, got {0.provided}'.format(
            self,
            message=self.message if not self.path else u'{} @ {}'.format(
                self.message,
                u''.join(map(
                    lambda v: u'[{!r}]'.format(v),
                    self.path
                ))
            )
        )

    def enrich(self, expected=None, provided=None, path=None, validator=None):
        """ Enrich this error with additional information.

        This works with both Invalid and MultipleInvalid (thanks to `Invalid` being iterable):
        in the latter case, the defaults are applied to all collected errors.

        The specified arguments are only set on `Invalid` errors which do not have any value on the property.

        One exclusion is `path`: if provided, it is prepended to `Invalid.path`.
        This feature is especially useful when validating the whole input with multiple different schemas:

        ```python
        from good import Schema, Invalid

        schema = Schema(int)
        input = {
            'user': {
                'age': 10,
            }
        }

        try:
            schema(input['user']['age'])
        except Invalid as e:
            e.enrich(path=['user', 'age'])  # Make the path reflect the reality
            raise  # re-raise the error with updated fields
        ```

        This is used when validating a value within a container.

        :param expected: Invalid.expected default
        :type expected: unicode|None
        :param provided: Invalid.provided default
        :type provided: unicode|None
        :param path: Prefix to prepend to Invalid.path
        :type path: list|None
        :param validator: Invalid.validator default
        :rtype: Invalid|MultipleInvalid
        """
        for e in self:
            # defaults on fields
            if e.expected is None and expected is not None:
                e.expected = expected
            if e.provided is None and provided is not None:
                e.provided = provided
            if e.validator is None and validator is not None:
                e.validator = validator
            # path prefix
            e.path = (path or []) + e.path
        return self

    if six.PY3:
        __bytes__, __str__ = __str__, __unicode__


class MultipleInvalid(Invalid):
    """ Validation errors for multiple values.

    This error is raised when the [`Schema`](#schema) has reported multiple errors, e.g. for several dictionary keys.

    `MultipleInvalid` has the same attributes as [`Invalid`](#invalid),
    but the values are taken from the first error in the list.

    In addition, it has the `errors` attribute, which is a list of [`Invalid`](#invalid) errors collected by the schema.
    The list is guaranteed to be plain: e.g. there will be no underlying hierarchy of `MultipleInvalid`.

    Note that both `Invalid` and `MultipleInvalid` are iterable, which allows to process them in singularity:

    ```python
    try:
        schema(input_value)
    except Invalid as ee:
        reported_problems = {}
        for e in ee:  # Iterate over `Invalid`
            path_str = u'.'.join(e.path)  # 'a.b.c.d', JavaScript-friendly :)
            reported_problems[path_str] = e.message
        #.. send reported_problems to the user
    ```

    In this example, we create a dictionary of paths (as strings) mapped to error strings for the user.

    :param errors: The reported errors.

        If it contains `MultipleInvalid` errors -- the list is recursively flattened
        so all of them are guaranteed to be instances of [`Invalid`](#invalid).

    :type errors: list[Invalid]
    """

    def __init__(self, errors):
        # Flatten errors
        errors = self.flatten(errors)

        # Create from errors
        e = errors[0]
        super(MultipleInvalid, self).__init__(e.message, e.expected, e.provided, e.path, e.validator, **e.info)

        #: The collected errors
        self.errors = errors

    def __iter__(self):
        return iter(self.errors)

    def __repr__(self):
        return '{cls}({0!r})'.format(self.errors, cls=type(self).__name__)

    @classmethod
    def flatten(cls, errors):
        """ Unwind `MultipleErrors` to have a plain list of `Invalid`

        :type errors: list[Invalid|MultipleInvalid]
        :rtype: list[Invalid]
        """
        ers = []
        for e in errors:
            if isinstance(e, MultipleInvalid):
                ers.extend(cls.flatten(e.errors))
            else:
                ers.append(e)
        return ers

    @classmethod
    def if_multiple(cls, errors):
        """ Provided a list of errors, choose which one to throw: `Invalid` or `MultipleInvalid`.

        `MultipleInvalid` is only used for multiple errors.

        :param errors: The list of collected errors
        :type errors: list[Invalid]
        :rtype: Invalid|MultipleInvalid
        """
        assert errors, 'Errors list is empty'
        return errors[0] if len(errors) == 1 else MultipleInvalid(errors)
